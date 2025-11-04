import asyncio
from pathlib import Path

from ai.intent.engine import IntentEngine
from common.settings import get_settings_manager


async def main() -> None:
    manager = get_settings_manager(Path("settings.json"))
    await manager.load()
    engine = IntentEngine(settings_manager=manager)
    try:
        result = await engine.predict_intent("Play some chill jazz on Jamendo")
        print("Prediction:", result)
        print("Raw response:\n", result.raw_response)
    finally:
        await engine.aclose()


if __name__ == "__main__":
    asyncio.run(main())
