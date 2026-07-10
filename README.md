# Tasmania Grid Intelligence & Forecasting Platform

A dashboard and API that turn Tasmania's electricity market data into a plain-language,
36-hour outlook — current demand, renewable generation, price, and supply risk — for
four different audiences: the market operator (AEMO), the generator (Hydro Tasmania),
the network (TasNetworks), and the general public.

**Live site:** https://ddxs97qcou3tz.cloudfront.net
**API:** https://tasmania-grid-intelligence-forecasting-8cre.onrender.com

## How it fits together

```
Open Electricity API ──▶ ETL scripts ──▶ Supabase (Postgres)
                                              │
                        ML models (trained offline, backend/ML) 
                                              │
                          Scheduled job (backend/lambda.py):
                          pulls latest readings, prunes old rows,
                          predicts the next 36 hours, upserts forecasts
                                              │
                                    Supabase: energy_readings, forecasts
                                              │
                              FastAPI (backend/main/api.py)
                                   GET /current /forecasts
                                   GET /summary /health
                                              │
                          React dashboard (frontend/Tasmanian-Grid-Frontend)
                             Dashboard · AEMO · Hydro · TasNetworks · Public · Health
```

- **Data ingestion**: `backend/ETL/` pulls historical and ongoing Tasmania (TAS1) market
  data — demand, price, renewable generation — from the [Open Electricity](https://openelectricity.org.au/)
  API and loads it into the Supabase `energy_readings` table.
- **Model training**: `backend/ML/` trains the demand, renewable, and price models
  (Random Forest / Gradient Boosting via scikit-learn) offline against `energy_readings`,
  saving `.pkl` models plus evaluation figures and reports. This is a one-off/occasional
  step, not something the live API does.
- **Forecast automation**: `backend/lambda.py` is the scheduled job (intended to run as
  an AWS Lambda) that refreshes `energy_readings`, prunes data older than the retention
  window, loads the trained models, predicts the next 36 hours, and upserts the results
  into the Supabase `forecasts` table. The API never generates forecasts itself — it only
  reads what this job has already written.
- **API**: `backend/main/api.py` is a FastAPI service that reads `energy_readings` and
  `forecasts` from Supabase and serves four read-only endpoints, each cached for 5
  minutes (`cachetools.TTLCache`) to avoid hammering Supabase. Deployed on Render.
- **Frontend**: `frontend/Tasmanian-Grid-Frontend` is a React (Vite) dashboard that
  fetches from the API and renders six views behind React Router, styled for a
  non-technical energy-industry audience (no model names, no ML metrics). Deployed as a
  static site to S3, served through CloudFront.
- **Infrastructure**: `backend/terraform/` provisions the frontend's hosting — a private
  S3 bucket plus a CloudFront distribution with Origin Access Control, using an S3-backed
  Terraform state.

## Repository layout

```
backend/
  main/api.py           FastAPI app — the four live endpoints
  lambda.py              Scheduled ETL + forecast-generation job
  ETL/                    One-off / scheduled data ingestion from Open Electricity
  ML/                     Model training scripts, saved models, figures, reports
  terraform/              S3 + CloudFront infrastructure for the frontend
  requirements.txt        Minimal deps to run the API (what Render installs)
  requirements-full.txt   Every dep across API + ETL + ML training + plotting
frontend/Tasmanian-Grid-Frontend/
  src/components/         All pages and shared UI (api.js, Navbar, Dashboard, etc.)
```

## Running the API locally

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt        # API only
# or: pip install -r requirements-full.txt   # if you also want to run ETL/ML scripts
```

Create `backend/.env` with:

```
SUPABASE_URL=...
SUPABASE_KEY=...
OPENELECTRICITY_API_KEY=...   # only needed for backend/ETL and backend/lambda.py
```

Start the server:

```bash
uvicorn main.api:app --reload
```

The API listens on `http://127.0.0.1:8000`. CORS is restricted to the origins listed in
`api.py` (local dev ports plus the deployed CloudFront domain) — add any new frontend
origin there.

### Endpoints

| Method | Path         | Returns                                                        |
|--------|--------------|-----------------------------------------------------------------|
| GET    | `/current`   | Latest actual reading: demand, renewable generation, price, coverage |
| GET    | `/forecasts` | Stored 36-hour forecast, one row per hour                      |
| GET    | `/summary`   | Peak/average demand, renewable, price, coverage, and highest risk over the forecast |
| GET    | `/health`    | API/database status, latest reading and forecast timestamps    |

`POST /generate-forecast`-style forecast generation is **not** exposed by the API — that
logic lives only in `backend/lambda.py`, run on a schedule.

## Running the frontend locally

```bash
cd frontend/Tasmanian-Grid-Frontend
npm install
npm run dev
```

Update `BASE_URL` in `src/components/api.js` if you're pointing at a different API host
(no trailing slash — it's concatenated directly with each endpoint path).

## Deploying

**Backend**: push to `main` — Render auto-deploys `backend/` using `requirements.txt`.

**Frontend**:

```bash
cd frontend/Tasmanian-Grid-Frontend
npm run build

cd ../../backend/terraform
terraform apply

aws cloudfront create-invalidation \
  --distribution-id "$(terraform output -raw cloudfront_distribution_id)" \
  --paths "/*"
```

`terraform apply` uploads the new `dist/` contents to S3; the CloudFront invalidation
forces the new build to serve immediately rather than waiting out the cache TTL.
