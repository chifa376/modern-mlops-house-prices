# House Price API - Runbook

## Service objectives

| Indicator | Target | Observation |
|---|---|---|
| Availability | At least 99% non-5xx responses over 7 days | Grafana request status |
| Prediction latency | p95 below 200 ms | Grafana and Locust |
| Monitoring freshness | Successful monitoring within 26 hours | Dagster run history |
| Model quality | Live RMSE <= 1.5 x holdout RMSE | Latest monitoring checks |

These are operational targets, not guarantees established by the local demonstration.
The local load tests recorded p95 values of 390 ms and 350 ms: the latency target was not met.

## Start, stop and inspect

Run commands from the project root.

    docker compose up -d --build
    docker compose ps -a
    docker compose exec api mlops-model status
    docker compose logs --tail 100 api

Stop while retaining named volumes:

    docker compose down

Adding -v deletes named volumes, including databases and model artifacts.

## Local interfaces

| Service | URL |
|---|---|
| API documentation | http://localhost:8000/docs |
| API health | http://localhost:8000/health |
| API readiness | http://localhost:8000/ready |
| MLflow | http://localhost:55553 |
| Dagster | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

The MLflow host port was changed because ports 5000 and 5001 were occupied.
Inside Docker, clients still use http://mlflow:5000.
Check the current host mapping with: docker compose port mlflow 5000.

Grafana login: admin. Read GRAFANA_ADMIN_PASSWORD locally from .env.
Never commit .env or include its contents in screenshots.

## Release a model

1. Run training_job in Dagster.
2. Inspect the candidate metrics, model_card.md and gate tags in MLflow.
3. Confirm gate_passed=true and review the comparison with the champion.
4. Promote the reviewed version:

       docker compose exec api mlops-model promote --version VERSION

5. Restart the API:

       docker compose restart api

6. Confirm /ready reports the intended version.
7. Run the smoke test with an API key.
8. Observe requests, latency and storage failures in Grafana.

Passing the gate makes a model eligible for promotion; it does not deploy it automatically.

## Roll back

    docker compose exec api mlops-model rollback
    docker compose restart api

Confirm /ready reports the previous version and run the smoke test.
The first champion has no previous version to restore.

## Smoke test on PowerShell

    $apiKeyLine = Get-Content .env | Where-Object { $_ -match '^API_KEYS=' }
    $apiKey = (($apiKeyLine -split '=', 2)[1] -split ',')[0].Trim()
    uv run python scripts/smoke_test.py --api-key "$apiKey"

All checks must report PASS.

## Alert response

| Signal | Investigate | Response |
|---|---|---|
| ApiDown | API status, startup logs, memory | Resolve the startup error; restart if appropriate |
| ModelNotLoaded | MLflow availability and champion alias | Train/promote if absent, then restart API |
| HighErrorRate | Error logs and recent releases | Fix the cause or roll back a problematic release |
| HighLatency | Resources during load, API durations, database waits | Profile the bottleneck and compare equivalent load tests |
| PredictionLogFailures | PostgreSQL status and logs | Restore database connectivity and verify new writes |
| input_drift failed | Saved Evidently HTML report | Examine changed features before deciding to retrain |
| live_rmse failed | Feedback validity, model version and market changes | Investigate and evaluate a new candidate if warranted |
| Data validation failed | artifacts/reports/validation.json | Correct or restore the source; retain the failed report |

An API /health response of 200 does not imply a model is loaded.
Before the first promotion, /ready returns 503.

During a database outage, predictions remain available but are not stored or replayed later.
Clients cannot attach feedback to a prediction that was never stored.

PredictionLogFailures evaluates a 10-minute window and may remain active after recovery.
Checks with insufficient data have value=null and a skipped reason; they are not measured passes.

## Retraining policy

- Scheduled training: Monday, 06:00 UTC.
- Scheduled monitoring: daily, 07:00 UTC.
- Manual training: after investigating drift or quality degradation.
- Promotion: manual, after reviewing a passing candidate.
- Rollback: after investigating a regression introduced by a release.

The Dagster daemon must be running for schedules to execute.

## Rotate an API key

1. Add a new key to API_KEYS in .env, retaining the old key separated by a comma.
2. Run docker compose up -d api.
3. Update clients to use the new key.
4. Remove the old key and recreate the API again.

## Backup and restore policy

Back up the PostgreSQL databases and the modern-mlops_mlflow-artifacts volume.
Store local backups under artifacts/backups, which is ignored by Git.

Validate restoration in a separate database and a separate volume.
Compare restored table counts and model artifact contents with their sources.
A backup is not considered verified until the restore has succeeded.

## Demonstration data

The quality-failure exercise submitted synthetic actual prices multiplied by 1.6.
Those feedback records remain in PostgreSQL and can affect subsequent live RMSE checks.
Load-test predictions generally have no actual-price feedback.

The invalid-input exercise changed three OverallQual values to 42.
The raw CSV was restored from an exact backup, with matching SHA-256 hashes.
The failed validation report was retained under artifacts/exercises.

## Troubleshooting

- Port occupied: identify the current binding, change only the host port, and update local client URLs.
- Dagster unavailable after recreation: inspect logs and wait for the code server to start.
- Prometheus target DOWN: inspect API logs and /metrics before changing scrape configuration.
- Grafana monitoring table missing: verify database connectivity, table creation and reader privileges.
- PostgreSQL init script: requires LF line endings and runs only on first database initialization.
- Changing passwords in .env does not update passwords in an existing PostgreSQL volume.
- On Windows, run the Spark pipeline and Spark tests inside Linux containers.
