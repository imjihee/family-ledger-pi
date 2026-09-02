"""Application configuration."""

import os


class Config:
    # Set API_BEARER_TOKEN to enable authentication. Never commit the token.
    API_BEARER_TOKEN = os.environ.get("API_BEARER_TOKEN")
    DASHBOARD_USERNAME = os.environ.get("DASHBOARD_USERNAME")
    DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD")

    SECRET_KEY = os.environ.get("SECRET_KEY")
