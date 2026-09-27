# Web App Engineering Patterns

Generalised patterns derived from building Cashflow2.0. Each section is implementation-agnostic — extract and apply to any stack.

---

## 1. Envelope Encryption for Client-Side Storage

**Problem:** You want to store sensitive data in the browser (IndexedDB, localStorage) but a DB dump or stolen device must not reveal the data.

**Pattern:**
- **KEK** (Key Encryption Key) — one master key, lives only in the server environment variable (e.g. `IDB_MASTER_KEY`). Never written to any DB.
- **DEK** (Data Encryption Key) — one random 32-byte key per user, stored in a server DB table as AES-256-GCM ciphertext encrypted with the KEK.
- Server decrypts DEK with KEK at login and returns the **plaintext DEK** to the client over HTTPS.
- Client holds DEK in a JS module variable only — never written to `localStorage`, `sessionStorage`, or IDB itself.
- On logout: null the JS variable. IDB blobs stay on disk but are unreadable without the DEK.
- On next login: same DEK is re-issued from the server — IDB data becomes readable again without re-fetching from the server.

**Why it matters:** A full DB dump exposes only encrypted blobs. Without the KEK (which is never in the DB), no DEK can be recovered. Mirrors the AWS KMS pattern.

**Implementation sketch:**
```python
# Server — Python (cryptography library)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os, base64

KEK = bytes.fromhex(os.environ['MASTER_KEY'])  # fail-fast at startup

def get_or_create_dek(conn, user_id):
    row = db_get(conn, "SELECT enc_dek, iv FROM user_keys WHERE user_id = %s", user_id)
    if row:
        return base64.b64encode(AESGCM(KEK).decrypt(b64d(row.iv), b64d(row.enc_dek), None)).decode()
    dek = os.urandom(32)
    iv  = os.urandom(12)
    enc = AESGCM(KEK).encrypt(iv, dek, None)
    db_insert(conn, "INSERT INTO user_keys (user_id, enc_dek, iv) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
              user_id, b64e(enc), b64e(iv))
    return base64.b64encode(dek).decode()
```

```js
// Client — Web Crypto API
async function importDek(base64Dek) {
  const raw = Uint8Array.from(atob(base64Dek), c => c.charCodeAt(0));
  return crypto.subtle.importKey('raw', raw, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
}

async function encrypt(cryptoKey, plaintext) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, cryptoKey,
    new TextEncoder().encode(plaintext));
  const out = new Uint8Array(12 + ct.byteLength);
  out.set(iv); out.set(new Uint8Array(ct), 12);
  return btoa(String.fromCharCode(...out));
}

async function decrypt(cryptoKey, blob) {
  const buf = Uint8Array.from(atob(blob), c => c.charCodeAt(0));
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: buf.slice(0, 12) }, cryptoKey, buf.slice(12));
  return new TextDecoder().decode(pt);
}
```

**Separate tables for separate user types:** If you have both regular users and admin users in different tables, maintain separate key tables (`user_keys`, `admin_keys`) and separate DB names (`app-db-{userId}`, `app-admin-db-{adminUserId}`).

---

## 2. Encrypted IndexedDB Layer

**Problem:** Server round-trips on every page load hurt perceived performance. You want instant UI from cached data, with server as the authoritative background updater.

**Pattern:**
- One IDB database per user, named `app-db-{userId}`. Multiple accounts on the same browser are fully isolated.
- All values written as encrypted blobs (see §1). Raw values never touch IDB.
- Each store has a companion `_meta` entry: `{ cached_at: Date.now(), version: N }` for staleness tracking.
- **Hydration flow on login:**
  1. Read IDB → populate React state immediately (instant render, no spinner)
  2. Check staleness per store (TTL or version mismatch)
  3. Fetch stale stores from server in background → merge into IDB + state silently
  4. No UI flash — stale data shows first, updates in place
- **Logout:** null the in-memory DEK. Do NOT delete the IDB databases — blobs stay on disk, unreadable until next login, instantly readable again once DEK re-issued.

**Staleness strategies:**
| Store type | Strategy |
|---|---|
| Frequently changing (transactions) | TTL — re-fetch if `cached_at > N minutes` |
| Versioned (categories, config) | Version signal — `SELECT COUNT(*) + COALESCE(MAX(id), 0)` as cheap version hash |
| Always authoritative (preferences) | Fetch once per login; server overwrites IDB |

**DevTools quirk:** IndexedDB DBs only appear in the DevTools Application panel after something is actually written. Eagerly write one entry on key import to force creation:
```js
async function initIdb(userId, cryptoKey) {
  await put(userId, 'meta', 'initialized_at', Date.now(), cryptoKey);
}
```

---

## 3. Write Queue — Optimistic Updates with Rollback

**Problem:** Mutations (categorise, delete, update) should feel instant, but the server might fail.

**Pattern:**
```
enqueue(mutation) → applyOptimisticFn() → persist to IDB write_queue → drain()
drain() → process queue in order → on success: remove from queue
         → on transient failure (429/502/503/504): retry with exponential backoff (3x)
         → on permanent failure: rollbackFn() + dispatch custom event for UI toast
```

- Auto-drain on: `window.focus`, `window.online`, after every enqueue.
- On `beforeunload`: flush remaining via `sendBeacon` (fire-and-forget for page close).
- Queue is persisted in IDB `write_queue` store — survives page refresh, drained on next load.
- On logout: flush queue first, then null DEK. Do not abandon in-flight mutations.

**Transient vs permanent failure:**
```js
const TRANSIENT = new Set([0, 429, 502, 503, 504]);
const isTransient = (status) => TRANSIENT.has(status);
```

---

## 4. React State Anti-Patterns with IDB

**Anti-pattern: wiping state before async refetch**
```js
// BAD — causes chart/table flash on returning users
setData([]);
setLoading(true);
// ...then async IDB read repopulates it
```

**Fix:** Never wipe state at the start of an effect if IDB may have a valid cache. Let IDB hydration overwrite, and let the server merge via functional updates:
```js
// GOOD
setLoading(true);
// IDB read:
if (cached.length > 0) { setData(cached); setLoading(false); }
// Server fetch merges, doesn't replace:
setData(prev => mergeById(prev, fresh));
```

**Anti-pattern: unstable callbacks in useEffect deps**

If a callback from a sibling context is in your `useEffect` dependency array, its reference can change on every re-render of that context, re-triggering the effect mid-load:
```js
// BAD — ProcessingContext re-renders → new reference → effect re-runs → setLoading(true) again
useEffect(() => { ... callbackFromSiblingContext(data); }, [isLoggedIn, callbackFromSiblingContext]);

// GOOD — stable ref wrapper
const callbackRef = useRef(callbackFromSiblingContext);
useEffect(() => { callbackRef.current = callbackFromSiblingContext; }, [callbackFromSiblingContext]);
useEffect(() => { ... callbackRef.current(data); }, [isLoggedIn]); // stable dep array
```

---

## 5. Admin/User Session Isolation

**Problem:** An admin panel on the same backend must be fully isolated from the regular user session — different cookies, different JWT claims, different DB rows.

**Pattern:**
- Separate cookie names: `access_token` / `admin_access_token`, `refresh_token` / `admin_refresh_token`
- Separate JWT claims: regular tokens carry `{ tools: ['appname'] }`, admin tokens carry `{ admin_session: true }`
- Route guards check the claim type — an admin token cannot access user routes and vice versa
- Separate `admin_users` table, separate login endpoint, separate rate limit buckets
- Two-step admin login: Step 1 password → short-lived `admin_pre_auth` temp token → Step 2 TOTP → full session cookies
- Separate IDB databases: `app-db-{userId}` vs `app-admin-db-{adminUserId}`

---

## 6. HMAC Request Signing

**Problem:** CSRF tokens protect against cross-site form submission but not against replay attacks or malicious browser extensions that can read cookies.

**Pattern:**
- Server derives a per-session HMAC signing secret at login: `HMAC-SHA256(user_id + jti, master_signing_key)`
- Client holds secret in JS memory only (same module variable as DEK)
- Each state-changing request includes headers: `X-HMAC-Sig: hex`, `X-HMAC-TS: unix_seconds`
- Server verifies: recomputes signature, checks timestamp within ±30s window
- Secret rotates on token refresh — replayed requests from old sessions fail

```js
async function computeHmacHeaders(method, path) {
  const ts = Math.floor(Date.now() / 1000);
  const msg = new TextEncoder().encode(`${ts}:${method.toUpperCase()}:${path}`);
  const key = await crypto.subtle.importKey('raw',
    hexToBytes(hmacSecret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, msg);
  return { 'X-HMAC-Sig': bytesToHex(new Uint8Array(sig)), 'X-HMAC-TS': String(ts) };
}
```

**Exempt read-only routes** (GET) from HMAC checks — only guard state-changing endpoints.

---

## 7. Geo-Blocking + Impossible Travel Detection

**Problem:** Admin panels are high-value targets. IP-based geo-blocking and travel anomaly detection add a meaningful layer without needing MFA on every request.

**Pattern:**
- Allowlist: `ADMIN_GEO_ALLOWLIST=GB,US` env var — only logins from these countries are accepted
- IP lookup: `ip-api.com` (free tier, batch-friendly) with a cached fallback on failure
- Impossible travel: compute haversine distance between last login location and current; if implausible in the elapsed time, strike the account
- Exponential strike lockout: 1st strike → 15 min lockout, 2nd → 30 min, ..., 5th → permanent
- Log all geo events to a `geo_lookup_log` table for audit

```python
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * asin(sqrt(a))

def is_impossible_travel(km, hours_elapsed, speed_cap_kmh=900):
    return hours_elapsed > 0 and (km / hours_elapsed) > speed_cap_kmh
```

---

## 8. Subscription / Tool-Scoped JWT Claims

**Problem:** One backend serves multiple apps (tools). A token issued for Tool A should not grant access to Tool B routes.

**Pattern:**
- JWT carries `tools: ['tool_a', 'tool_b']` claim set at login
- Backend middleware checks the claim before processing any route: `if tool_name not in get_jwt().get('tools', []): return 403`
- Token refresh carries the claim forward: read from incoming refresh token, re-embed in new access token
- Old tokens (pre-migration, no `tools` claim) correctly receive 403 — intentional; users must re-login

---

## 9. Rate Limiting — Granular + Disableable

**Problem:** A single global rate limit is too blunt. Dev environments need to disable limits without code changes.

**Pattern:**
- One constant per logical action group: `RL_READ_TRANSACTIONS`, `RL_WRITE_CATEGORISE`, etc.
- Per-endpoint disable flags as environment variables: `DISABLE_RL_READ_TRANSACTIONS=true`
- Master kill switch: `DISABLE_ALL_RATE_LIMITS=true`
- Constants are callables so flags are evaluated per-request (not at startup): `lambda: None if os.getenv('DISABLE_RL_READ_TRANSACTIONS') else '100/minute'`
- Admin and user rate limits in separate files — different buckets, different limits

---

## 10. Multi-Account Auth Migration (Username → Email)

**Problem:** App launched with username-only auth. Need to add email without breaking existing accounts.

**Pattern:**
- Add `email` column as **nullable** — existing rows get `NULL`, not a default
- `display_name` backfilled from `username` for all existing rows
- Login endpoint routes by input: if input contains `@` → look up by email; else → look up by username
- Signup: email field optional — existing username-only flow fully preserved
- Never require email from existing users; never block login if email is NULL

---

## 11. Render Cold Start Handling

**Problem:** Free/hobby Render services spin down after inactivity. The first request after spin-down returns a 502/503 or a JSON error body with "starting up".

**Pattern:**
- Detect in `parseJson`: if status 502/503, throw `new Error('Server is starting up — please try again in a few seconds.')`
- In the data-loading effect: catch this specific message → set `initialLoadError` state → show a retry banner, not a crash screen
- User clicks Retry → `loadRetryCount++` → effect re-runs → by then server is warm
- Do not auto-retry in a loop — that hammers a cold server; let the user decide when to retry

---

## 12. Security Headers Checklist

Apply these on every response from any web backend:

```python
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "   # tighten per app
        "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
        "font-src fonts.gstatic.com; "
        "connect-src 'self' <your-api-origin>; "
        "frame-ancestors 'none';"
    )
    return response
```

CORS: lock `origins` to your exact production domain in prod; never `*` with `supports_credentials=True`.

---

## 13. Permission-Derived Role Levels

**Problem:** Hard-coded role hierarchies break when you add roles. Level determines what actions a role can take on other roles.

**Pattern:**
- Each permission has a numeric weight (e.g. `admin.panel.view = 1`, `admin.accounts.manage = 33`)
- A role's effective level = sum of its permission weights
- Hard ceiling: a user can only assign roles/permissions at a strictly lower level than their own
- Level is re-computed at request time from the current permission set — no stored level column needed
- Owner is exempt from ceilings (or has a fixed max level)

---

## 14. Idle Session Timeout (Frontend)

**Problem:** Admin sessions left open on unattended machines are a security risk.

**Pattern:**
```js
const IDLE_MS = 30 * 60 * 1000;
let timer;

function resetTimer() {
    clearTimeout(timer);
    timer = setTimeout(doLogout, IDLE_MS);
}

['mousemove', 'keydown', 'click', 'scroll', 'touchstart']
    .forEach(e => window.addEventListener(e, resetTimer));
resetTimer();
```

Start the timer only when `authState === 'ok'`. Clear it on logout. Don't start it on the login screen.
