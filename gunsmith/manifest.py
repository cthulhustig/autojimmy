import common
import gunsmith
import typing

class ManifestEntry(object):
    def __init__(
            self,
            component: str,
            cost: typing.Optional[gunsmith.NumericModifierInterface] = None,
            weight: typing.Optional[gunsmith.NumericModifierInterface] = None,
            factors: typing.Optional[typing.Iterable[gunsmith.FactorInterface]] = None
            ) -> None:
        self._text = component
        self._cost = cost
        self._weight = weight
        self._factors = list(factors) if factors else []

    def component(self) -> str:
        return self._text

    def cost(self) -> typing.Optional[gunsmith.NumericModifierInterface]:
        return self._cost

    def weight(self) -> typing.Optional[gunsmith.NumericModifierInterface]:
        return self._weight

    def factors(self) -> typing.Collection[gunsmith.FactorInterface]:
        return self._factors

class ManifestSection(object):
    def __init__(
            self,
            name: str
            ) -> None:
        self._name = name
        self._entries: typing.List[ManifestEntry] = []

    def name(self) -> str:
        return self._name

    def entries(self) -> typing.Collection[ManifestEntry]:
        return self._entries

    def createEntry(
            self,
            component: str,
            cost: typing.Optional[gunsmith.NumericModifierInterface] = None,
            weight: typing.Optional[gunsmith.NumericModifierInterface] = None,
            factors: typing.Optional[typing.Iterable[gunsmith.FactorInterface]] = None
            ) -> None:
        entry = ManifestEntry(
            component=component,
            cost=cost,
            weight=weight,
            factors=factors)
        self._entries.append(entry)
        return entry

    def totalCost(self) -> common.ScalarCalculation:
        total = gunsmith.calculateNumericModifierSequence(
            modifiers=[entry.cost() for entry in self._entries if entry.cost()])
        if not total:
            raise RuntimeError(
                f'Unable to calculate cost for manifest section {self._name} as starting modifier is not absolute')
        return common.Calculator.equals(
            value=total,
            name='Total Cost')

    def totalWeight(self) -> common.ScalarCalculation:
        total = gunsmith.calculateNumericModifierSequence(
            modifiers=[entry.weight() for entry in self._entries if entry.weight()])
        if not total:
            raise RuntimeError(
                f'Unable to calculate weight for manifest section {self._name} as starting modifier is not absolute')
        return common.Calculator.equals(
            value=total,
            name='Total Weight')

class Manifest(object):
    def __init__(self) -> None:
        self._sections: typing.List[ManifestSection] = []

    def sections(self) -> typing.Collection[ManifestSection]:
        return self._sections

    def createSection(
            self,
            name: str
            ) -> ManifestSection:
        section = ManifestSection(name=name)
        self._sections.append(section)
        return section

    def totalWeight(self) -> common.ScalarCalculation:
        weights = []
        for section in self._sections:
            weights.append(section.totalWeight())
        return common.Calculator.sum(
            values=weights,
            name='Total Weight')

    def totalCost(self) -> common.ScalarCalculation:
        costs = []
        for section in self._sections:
            costs.append(section.totalCost())
        return common.Calculator.sum(
            values=costs,
            name='Total Cost')

    def clear(self) -> None:
        self._sections.clear()
