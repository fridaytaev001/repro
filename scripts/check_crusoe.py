"""Run with python -m scripts.check_crusoe. Prints no credentials or raw errors."""
import asyncio
import json

from app.providers.crusoe import CrusoeClient, ProviderError
from app.settings import Settings


async def main():
    provider = CrusoeClient(Settings.read())
    try:
        result = await provider.smoke_test()
        print(json.dumps(result, indent=2))
    except ProviderError as error:
        print(json.dumps({'ready': False, 'code': error.code, 'message': str(error)}))
        raise SystemExit(1)
    finally:
        await provider.close()


if __name__ == '__main__':
    asyncio.run(main())
