# Deploy the personal pilot

The hosted layout is **Vercel Hobby → Render Free → Neon Free**. Use the repository's `AI-UILS` branch. Start with an empty cloud database and test with fictional documents.

## 1. Create the database

1. In [Neon](https://console.neon.tech/), create a project on the Free plan. Use an AWS Singapore region if available so it is close to the Render service.
2. In the connection dialog, turn **Connection pooling** off and use the direct connection string. Keep it for the private `DATABASE_URL` field in Render. The app verifies TLS for Neon hosts and adapts the URL for its async PostgreSQL driver.
3. Keep the project on Free. Current limits include 1 GB of Postgres storage and 100 compute-unit hours per project. [Neon plan details](https://neon.com/docs/introduction/plans)

## 2. Deploy the API

1. In [Render](https://dashboard.render.com/), connect your GitHub account with access to `pramit1506/AI-UILS`. Select **New → Blueprint**, choose the repository and the `AI-UILS` branch, and review the root `render.yaml`.
2. Confirm it creates one **Free** Docker web service in Singapore. Paste the direct Neon connection string into the private `DATABASE_URL` field. Render generates the signing key. Leave payment details unset for a zero-spend pilot. Render can pause services or deployments on hitting included usage. [Render free service limits](https://render.com/docs/free)
3. Add your existing inference keys in the service's **Environment** panel. Keep it in `multi` mode. Enable `GEMINI_FREE_TIER_CONFIRMED` and `GROQ_FREE_TIER_CONFIRMED` only if the uploaded keys belong to the confirmed free projects and organizations. The frontend needs no provider credentials.
4. Wait for the service to become Live. Startup runs the Alembic migrations and listens on Render's assigned port. Render's recurring health check avoids querying the database so Neon can go idle. Visit `https://<assigned-api-host>.onrender.com/api/v1/ready` to check database readiness on demand.

## 3. Deploy the web app

1. On [Vercel](https://vercel.com/new), import the same GitHub repository under a Hobby scope. Set **Root Directory** to `frontend`, **Framework** to Vite, and **Production Branch** to `AI-UILS`.
2. Set the Vercel project variable `RENDER_API_ORIGIN` to the assigned HTTPS Render origin, without an `/api` suffix. The checked-in Vercel configuration forwards same-origin `/api/` requests and serves the React routes. Keep `VITE_API_BASE_URL` unset or use `/api/v1` so the browser can use the session cookies through the Vercel URL.
3. Deploy. Open the assigned `vercel.app` URL. A cold Render instance can take about a minute to wake. If a first click times out while the service wakes, wait for readiness and retry from the same tab. Vercel allows up to 120 seconds for external proxy requests. [Vercel Hobby terms](https://vercel.com/docs/limits/fair-use-guidelines) · [Proxy timeout](https://vercel.com/docs/limits#proxied-request-timeout)

## 4. Verify the release

1. From the Vercel URL, open a sample, register a dummy account, save, and search its exact reference. Reload and confirm it remains in **Saved records**. Open **Settings** and **Saved records** directly to check SPA routing.
2. Upload a fictional document and verify extraction, review, and the saved source. Attempt a second account lookup to confirm records are isolated.
3. Sign out and back in. If recovery mail is configured, request a reset code and verify it arrives before sharing the link.

Saved records and their extracted source text live in Neon. The current upload flow extracts text and does not retain original file bytes on the server, so this deployment needs no file bucket. Render's SQLite checkpoints and unsaved drafts may be lost when the service sleeps or restarts.

Render Free blocks outbound SMTP on ports 25, 465, and 587. To use Mailjet over HTTPS, verify a sender address you control in [Mailjet](https://app.mailjet.com/), then set `SMTP_FROM`, `MAILJET_API_KEY`, and `MAILJET_API_SECRET` in Render. Send a test reset to your own mailbox to confirm delivery. The app shows that recovery is unavailable until a mail transport is configured. [Render networking limits](https://render.com/docs/free#other-limitations) · [Mailjet sender verification](https://documentation.mailjet.com/hc/en-us/articles/360043050493-How-many-senders-can-be-added-to-my-account)
