"""Flask entry point — /api/messages endpoint for Teams Bot Service."""

import sys
import asyncio
from aiohttp import web
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity

from src.config import Config
from src.bot.bot_app import RXBot
from src.utils.logger import setup_logging

config = Config()
setup_logging(config.LOG_LEVEL)

# Validate config
missing = config.validate()
if missing:
    print(f"❌ Missing required config: {', '.join(missing)}", file=sys.stderr)
    print("   Copy .env.template → .env and fill in values.", file=sys.stderr)
    sys.exit(1)

# Bot Framework adapter
adapter_settings = BotFrameworkAdapterSettings(
    app_id=config.BOT_APP_ID,
    app_password=config.BOT_APP_PASSWORD,
)
adapter = BotFrameworkAdapter(adapter_settings)

# Error handler
async def on_error(context, error):
    print(f"[on_error] {error}", file=sys.stderr)
    await context.send_activity("Sorry, something went wrong. Please try again.")

adapter.on_turn_error = on_error

# Bot instance
bot = RXBot()


async def messages(req: web.Request) -> web.Response:
    """Main endpoint — receives Activities from Azure Bot Service."""
    if "application/json" not in req.headers.get("Content-Type", ""):
        return web.Response(status=415)

    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    response = await adapter.process_activity(activity, auth_header, bot.on_turn)
    if response:
        return web.json_response(data=response.body, status=response.status)
    return web.Response(status=201)


async def health(req: web.Request) -> web.Response:
    """Health check for Container Apps probes."""
    return web.json_response({"status": "healthy", "service": "rx-coordinator"})


app = web.Application()
app.router.add_post("/api/messages", messages)
app.router.add_get("/health", health)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=config.PORT)
