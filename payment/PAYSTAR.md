# Paystar integration

Protocol reference: https://docs.paystar.ir/docs/gateway

## Deployment environment (configure manually)

Do not commit `.env` or copy live keys into documentation or tests.

```dotenv
PAYSTAR_GATEWAY_ID=<gateway identifier from your Paystar panel>
PAYSTAR_SIGN_KEY=<payment gateway signing key from your Paystar panel>
PAYSTAR_CALLBACK_URL=https://doctor.gosheshenava.com/payment/result
PAYMENT_FRONTEND_URL=https://<public-frontend-host>
```

New payments return directly to the public HTTP or HTTPS **Vue** page `/payment/result`
via GET (`callback_method=1`). Paystar must authorize the actual callback domain,
including `doctor.gosheshenava.com`; registration of the root domain alone does
not prove that subdomains are accepted. Confirm this with Paystar before release.
The Vue result route must serve `index.html` on direct visits and refreshes.
`PAYMENT_FRONTEND_URL` remains only for legacy backend callbacks; use
`https://doctor.gosheshenava.com` for that compatibility setting.

Configure the frontend environment manually, then rebuild:

```dotenv
VUE_APP_API_BASE_URL=/api-backend/
```

Axios now uses this environment variable, defaulting to `/api-backend/`.
On the HTTPS frontend, an HTTP IP API is blocked as mixed content. Either use
the same-origin reverse proxy below, or set a real HTTPS backend base URL and
allow `https://doctor.gosheshenava.com` in backend CORS. No payment secret belongs
in a `VUE_APP_*` variable. Vue environment variables are embedded at build time.

Example snippets to adapt **manually** inside the existing HTTPS Nginx server
for `doctor.gosheshenava.com` (do not replace the entire server configuration):

```nginx
location ^~ /api-backend/ {
    proxy_pass http://unix:/run/gunicorn.sock:/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 65s;
}

location / {
    try_files $uri $uri/ /index.html;
}
```

This assumes the existing server root points to the Vue `dist` directory and
the upstream socket is the one used by this project. The proxy strips the
`/api-backend/` prefix before passing requests to Django. Include the frontend
host in Django's `ALLOWED_HOSTS` when using this proxy. With a same-origin API,
cross-origin CORS permission is not needed. The user stays on the frontend
domain; API requests are still visible in browser developer tools.
The application permits HTTP callbacks; provider acceptance must be checked
with the actual gateway configuration. HTTPS remains recommended because HTTP
does not encrypt callback metadata or protect the frontend from tampering.
For the current HTTP frontend deployment, set manually:

```dotenv
PAYSTAR_CALLBACK_URL=http://doctor.gosheshenava.com/payment/result
PAYMENT_FRONTEND_URL=http://doctor.gosheshenava.com
```

Do not deploy until callback routing is verified. Restart the application
after configuring its environment; this implementation does not edit it.

Requests use a 20-second timeout and verification may additionally perform an
inquiry after an uncertain result. Configure the application worker and reverse
proxy timeouts accordingly (at least 60 seconds recommended), using the normal
deployment approval process. Database tables must use transactional row locking
(InnoDB on MySQL). No schema change or new dependency is required.

## Amounts

`Transaction.amount` and `User.amount` are **rial**, as are Paystar API amounts.
The existing Vue display divides these amounts by 10 to show toman. For example:

| UI display | Stored amount | Create/verify amount | Wallet credit |
| --- | --- | --- | --- |
| 10,000 toman | 100,000 rial | 100,000 rial | 100,000 rial |

Do not multiply/divide during create, verify or settlement. Paystar's supported
base amount range is 5,000–500,000,000 rial according to the documentation.
`payment_amount` includes payer fees; store it for reconciliation, but never
credit the fee to the wallet. Verify must return the original base `price`.

## Flow and compatibility

- Authenticated POST `/gateway/paystar/create/link/` accepts `order_id` and
  returns the existing `{ "link": "..." }` contract. Only the owner can pay an
  invoice. Repeating creation returns the same pending payment link.
- The old `/gateway/parspal/create/link/` creation URL is an alias to Paystar
  for existing frontends. The old Parspal callback remains for in-flight
  payments; legacy gateway implementations have not been rewritten or audited.
- New provider references are namespaced `paystar:` in `idPay_id`. Existing
  fields store the fee-inclusive total and immutable amount/user snapshot.
- Vue `/payment/result` reads the provider GET parameters and POSTs only the
  allowed fields to `/gateway/paystar/confirm/`. This public endpoint always
  returns JSON, never a redirect: `status=success` includes `amount` (rial),
  `order_id`, `tracking_code`, `authorLink` (local Vue path) and `msg`. Invalid,
  cancelled or failed payments return `status=failed` with an error HTTP code;
  temporary provider errors return `status=error`, `retryable=true` and HTTP 502.
  No session is needed to finish a payment started before login expiry.
- The old backend `/gateway/paystar/verify/` still accepts GET/POST for in-flight
  payments, but must not be the configured callback for new frontend returns.
  Callback status alone does not credit funds. Server-side verification checks
  the original amount and reference. Repeated confirmations do not credit twice.
- The result page shows loading, server-confirmed success, cancellation/failure,
  or a retry action for uncertain network results. It does not automatically
  start another payment. Browser-supplied amount/user/redirect fields are ignored.
  Callback query parameters remain on the result URL to support refresh/retry;
  do not share screenshots or links containing full payment/card metadata.
- Wallet credit and completion are in one database transaction, locking the
  payment and user rows and using an atomic balance increment.
- If verification times out or reports already verified, a server-to-server
  inquiry must report `SUCCEED`, the stored order/reference and exact stored
  fee-inclusive amount before settlement is allowed. Otherwise no credit occurs.
- On a transient callback failure the original callback can be retried; after a
  successful provider verification but local rollback, inquiry recovers the
  settlement on retry. There is no scheduled reconciliation worker in this
  change. Unresolved payments need prompt support review; Paystar documents a
  10-minute verification deadline. Never manually reclassify a failed payment
  as successful based only on browser-supplied fields.

## Safe tests

```bash
python manage.py test payment --settings=payment.test_settings --verbosity 2
```

These settings do **not** import production settings or load `.env`; they use
an in-memory SQLite database and fake credentials. HTTP requests in the tests
are mocked. Tests cover HMAC, rial/toman, fees, invalid inputs/responses,
authentication, ownership, tampering, rollback, duplicate callbacks and inquiry
recovery. SQLite does not prove MySQL concurrent row-lock behavior; concurrency
needs a separate isolated InnoDB environment before production rollout.

Frontend: `npm run test:unit`; production build uses the existing Docker setup.
These tests do not constitute a live Paystar transaction or approval of a real
gateway configuration. A small authorized end-to-end payment and callback test
on the deployed HTTPS domain remains necessary before release.
