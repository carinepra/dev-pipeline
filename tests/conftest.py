"""Pytest configuration and fixtures for dev-pipeline tests."""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def env_setup():
    """Set up test environment variables."""
    os.environ.update(
        {
            "ENV": "test",
            "AWS_REGION": "sa-east-1",
            "JIRA_SERVER": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test_token",
            "JIRA_PROJECT": "TEST",
        }
    )
