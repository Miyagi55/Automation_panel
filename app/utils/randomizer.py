from asyncio import sleep
from random import uniform

from app.utils.logger import logger


class Randomizer:
    """Base randomizer"""

    @staticmethod
    def delay(a: float, b: float) -> float:
        return uniform(a, b)

    @staticmethod
    async def sleep(a: float, b: float):
        delay_val = Randomizer.delay(a, b)
        logger.info(f"Sleeping for {delay_val:.2f} seconds")
        await sleep(delay_val)
