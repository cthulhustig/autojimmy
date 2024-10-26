import random
import secrets
import typing

class RandomGenerator(random.Random):
    def __init__(
            self,
            seed: typing.Optional[typing.Union[int, float, str, bytes, bytearray]] = None
            ) -> None:
        if isinstance(seed, bytearray):
            # bytearray is mutable so make a copy as this class holds a copy of
            # the seed used
            seed = seed.copy()
        self._seed = seed if seed != None else RandomGenerator._generateSeed()
        super().__init__(self._seed)

    def seed(
            self,
            seed: typing.Optional[typing.Union[int, float, str, bytes, bytearray]] = None,
            version = 2) -> None:
        if isinstance(seed, bytearray):
            # bytearray is mutable so make a copy as this class holds a copy of
            # the seed used
            seed = seed.copy()
        self._seed = seed if seed != None else RandomGenerator._generateSeed()
        super().seed(self._seed, version)

    def usedSeed(self) -> typing.Union[int, float, str, bytes, bytearray]:
        return self._seed

    @staticmethod
    def _generateSeed() -> int:
        # Use a 64bit cryptographically secure random number
        # to init the pseudo random number generator
        return secrets.randbits(64)
