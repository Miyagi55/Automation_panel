from asyncio import sleep
from random import uniform


class Randomizer:
    """Base randomizer"""

    @staticmethod
    def delay(a: float, b: float) -> float:
        return uniform(a, b)

    @staticmethod
    async def sleep(a: float, b: float):
        await sleep(Randomizer.delay(a, b))
