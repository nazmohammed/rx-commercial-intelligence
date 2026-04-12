"""Environment configuration loader."""

import os
from dotenv import load_dotenv

load_dotenv(override=False)


class Config:
    """Application configuration — all from environment variables."""

    # Bot
    BOT_APP_ID: str = os.getenv("BOT_APP_ID", "")
    BOT_APP_PASSWORD: str = os.getenv("BOT_APP_PASSWORD", "")
    PORT: int = int(os.getenv("PORT", "3978"))

    # Foundry
    FOUNDRY_PROJECT_ENDPOINT: str = os.getenv("FOUNDRY_PROJECT_ENDPOINT", "")
    FOUNDRY_QUERY_ENGINE_AGENT_ID: str = os.getenv("FOUNDRY_QUERY_ENGINE_AGENT_ID", "")
    FOUNDRY_ANALYST_AGENT_ID: str = os.getenv("FOUNDRY_ANALYST_AGENT_ID", "")

    # Power BI
    PBI_WORKSPACE_ID: str = os.getenv("PBI_WORKSPACE_ID", "")
    PBI_DATASET_ID: str = os.getenv("PBI_DATASET_ID", "")
    PBI_TENANT_ID: str = os.getenv("PBI_TENANT_ID", "")
    PBI_CLIENT_ID: str = os.getenv("PBI_CLIENT_ID", "")
    PBI_CLIENT_SECRET: str = os.getenv("PBI_CLIENT_SECRET", "")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def validate(self) -> list[str]:
        """Return list of missing required config values."""
        required = [
            ("BOT_APP_ID", self.BOT_APP_ID),
            ("BOT_APP_PASSWORD", self.BOT_APP_PASSWORD),
            ("FOUNDRY_PROJECT_ENDPOINT", self.FOUNDRY_PROJECT_ENDPOINT),
            ("FOUNDRY_QUERY_ENGINE_AGENT_ID", self.FOUNDRY_QUERY_ENGINE_AGENT_ID),
            ("FOUNDRY_ANALYST_AGENT_ID", self.FOUNDRY_ANALYST_AGENT_ID),
            ("PBI_TENANT_ID", self.PBI_TENANT_ID),
            ("PBI_CLIENT_ID", self.PBI_CLIENT_ID),
            ("PBI_CLIENT_SECRET", self.PBI_CLIENT_SECRET),
        ]
        return [name for name, val in required if not val]
