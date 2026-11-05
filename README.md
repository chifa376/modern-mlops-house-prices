# Production-style MLOps pipeline - House prices

SUPINFO 5LAKE practical project.
Author: Chifa Chouchane.

## Purpose

Predict house sale prices and demonstrate a reproducible model lifecycle:
validated data, tracked experiments, controlled promotion, secured serving,
monitoring, alerts and rollback.

## Architecture

Training:
OpenML CSV -> PySpark validation/preparation -> Feast -> Ridge training -> MLflow registry.

Serving:
Client with X-API-Key -> FastAPI champion model -> PostgreSQL prediction records.
Actual prices are submitted later through /feedback.

Monitoring:
FastAPI /metrics -> Prometheus -> Grafana.
Dagster drift and quality checks -> PostgreSQL -> Grafana.

## Tools

Python 3.11, uv, Docker Compose, Java 17, PySpark, Feast, scikit-learn,
MLflow, Dagster, FastAPI, PostgreSQL, Evidently, Prometheus, Grafana and Locust.

Dependencies are recorded in uv.lock.
The API and pipeline use separate Docker images.

## Model and data

- Dataset: OpenML house_prices, Ames housing sales.
- Features: OverallQual, GrLivArea, GarageCars, TotalBsmtSF, YearBuilt.
- Target: SalePrice, in US dollars.
- Preprocessing: median imputation and standard scaling.
- Estimator: Ridge on log1p(price), with inverse transformation at prediction time.
- Training period observed: January 2006 to June 2009, 1110 sales.
- Test period observed: July 2009 to July 2010, 350 sales.
- Feast retrieves features using point-in-time joins.

The split is chronological; months are not split between training and testing.

## Observed model results

| Metric | Value |
|---|---:|
| MAE | Approximately 21,833.71 USD |
| RMSE | Approximately 31,823.15 USD |
| R2 | Approximately 0.845 |
| MAPE | Approximately 13.4% |

Model versions, data fingerprint, parameters, validation report and model card
are recorded in MLflow.

## Promotion rules

A candidate must:
1. Reach R2 >= 0.70.
2. Pass reference-house behaviour checks.
3. Have RMSE no worse than the champion on the same holdout.

A passing version receives the challenger alias.
A manual command promotes it to champion.
Restarting the API loads the selected champion.

## Setup

1. Install Docker with Linux containers, Git, Python 3.11 and uv.
2. Copy .env.example to .env and replace all change-me values with unique secrets.
3. Use the same app password in APP_DB_PASSWORD and DATABASE_URL.
4. Create data/ and artifacts/ before starting Docker.
5. Install dependencies:

       uv sync --frozen --all-groups

6. Start the stack:

       docker compose up --build -d

7. In Dagster, materialize training_job.
8. Review the candidate in MLflow, promote it, then restart the API.
9. Run the smoke test, replay recent sales, then run monitoring_job.

For Windows, execute Spark workloads in Docker.
See docs/RUNBOOK.md for commands and operational procedures.

## Local interfaces

| Service | Address |
|---|---|
| API docs | http://localhost:8000/docs |
| MLflow | http://localhost:55553 |
| Dagster | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

Host ports may need adjustment if already occupied.
Internal Docker service addresses remain unchanged.

## Verification completed locally

- Ruff lint and formatting checks passed.
- 24 automated tests passed in a Linux container, including Spark validation tests.
- Smoke test passed after release, rollback and database recovery.
- Prometheus target reached UP and collected predicted_sale_price_count.
- Grafana displayed API metrics and measured monitoring results.
- Simulated price increases caused the live quality check to fail.
- A Ridge candidate with alpha=1000 was rejected; explicit promotion was refused.
- Version 4 was promoted, then rolled back to version 1.
- Predictions remained available during a PostgreSQL outage.
- PredictionLogFailures reached FIRING.
- Three invalid OverallQual values stopped the data pipeline.
- Original raw data was restored with matching SHA-256 hashes.

## Load-test results

20 simulated users; startup rate: 5 users/second.
The first HTML report records a measurement window of 1 minute 48 seconds.
The second run was configured for 2 minutes.

| Metric | First run | Second run |
|---|---:|---:|
| Requests | 4861 | 5398 |
| Failures | 0 | 0 |
| Average response time | 130.88 ms | 116.17 ms |
| p95 response time | 390 ms | 350 ms |
| Requests per second | 44.89 | 46.50 |

The p95 target of less than 200 ms was not met under this local load.
The exact bottleneck has not been established.
These short tests do not establish seven-day availability or latency compliance.

Reports and CSV files are stored locally under artifacts/loadtest.

## CI/CD

GitHub Actions definitions include:
- Lint, formatting checks and automated tests.
- Dependency vulnerability audit.
- Docker image builds and Trivy scans.
- API scan blocking on fixable HIGH/CRITICAL vulnerabilities.
- Pipeline scan reporting findings.
- Image publication to GHCR on a pushed v* tag.
- Weekly dependency update checks through Dependabot.

Workflow files have been created and parsed locally.
Successful GitHub execution and security scan results remain to be verified.

## Remaining verification

- Execute CI on GitHub and examine audit/scan results.
- Back up and restore databases and model artifacts in isolated targets.
- Verify stack stop/start preserves data.
- Finalize the evidence package and update this checklist.

## Limitations

Historical sales from one US city do not establish suitability for current
real-estate valuations or other markets.
Only five features are used.
Reference-house behaviour checks are examples, not a global monotonicity guarantee.
Synthetic feedback from exercises remains in the monitoring database.
Secrets, generated data, models and local reports are excluded from Git.
