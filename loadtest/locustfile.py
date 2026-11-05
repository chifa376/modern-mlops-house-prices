"""Load test using real house features from the processed dataset."""

import os
import random

import pandas as pd
from locust import HttpUser, between, task

from mlops import settings

HOUSES = pd.read_parquet(
    settings.PROCESSED_PATH,
    columns=settings.FEATURES,
).to_dict("records")


class PredictionUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self) -> None:
        self.client.headers["X-API-Key"] = os.environ["API_KEY"]

    @task
    def predict(self) -> None:
        self.client.post("/predict", json=random.choice(HOUSES))
