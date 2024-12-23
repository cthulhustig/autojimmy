import numpy
import random
import secrets
import typing

class RandomGenerator(object):
    def __init__(
            self,
            seed: typing.Optional[int] = None,
            legacy: bool = False
            ) -> None:
        super().__init__()
        self.init(seed=seed, legacy=legacy)

    def init(
            self,
            seed: typing.Optional[int] = None,
            legacy: bool = False
            ) -> None:
        self._seed = seed if seed != None else RandomGenerator._randomSeed()
        self._legacy = legacy

        if self._legacy:
            self._rng = random.Random(self._seed)
        else:
            # Use PCG64 rather than the default MT19937 (Mersenne Twister) as it provides
            # better initial diffusion (i.e. more random when first used) and generally
            # better randomness overall. I'm not sure if I was seeing patterns where there
            # were none but I could swear when using MT19937 (or at least the default
            # python random implementation) to generate the result of a 2D6 roll, the
            # chance of the result of both die being the same value was significantly
            # higher than the 1/6 it should be for the first few rolls
            self._rng = numpy.random.RandomState(numpy.random.PCG64(numpy.random.SeedSequence(self._seed)))

    def random(self) -> float:
        return self._rng.random()

    def randint(self, low: int, high: int) -> int:
        if self._legacy:
            return self._rng.randint(low, high)
        else:
            # NOTE: High value is +1 to make interface compatible with the standard
            # python random.randint as Numpy has high as exclusive where as the
            # default python implementation has it as inclusive
            return self._rng.randint(low, high + 1)

    def randbits(self, bits: int) -> int:
        # This overly complicated implementation is because randint is
        # limited to generating signed 32 bit values
        bytes = (bits + 7) // 8
        result = int.from_bytes(
            bytes=self._rng.bytes(bytes),
            byteorder='big')

        # Only return the requested number of bits
        return result & ((1 << bits) - 1)

    # NOTE: This is different to the api for the standard python random where
    # seed sets the new seed rather than retrieving the current seed as it
    # does here
    def seed(self) -> int:
        return self._seed

    # Generate a true random 128 bit seed to init the pseudo random number
    # generator
    @staticmethod
    def _randomSeed() -> int:
        return secrets.randbits(128)
