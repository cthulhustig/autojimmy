import common
import construction
import typing

class ManifestEntry(object):
    def __init__(
            self,
            component: str,
            costs: typing.Optional[typing.Mapping[construction.ConstructionCost, construction.NumericModifierInterface]] = None,
            factors: typing.Optional[typing.Iterable[construction.FactorInterface]] = None
            ) -> None:
        self._text = component
        self._costs = dict(costs) if costs else {}
        self._factors = list(factors) if factors else []

    def component(self) -> str:
        return self._text

    def cost(self, costId: construction.ConstructionCost):
        return self._costs.get(costId)

    def factors(self) -> typing.Collection[construction.FactorInterface]:
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
            costs: typing.Optional[typing.Mapping[construction.ConstructionCost, construction.NumericModifierInterface]] = None,
            factors: typing.Optional[typing.Iterable[construction.FactorInterface]] = None
            ) -> None:
        entry = ManifestEntry(
            component=component,
            costs=costs,
            factors=factors)
        self._entries.append(entry)
        return entry

    def totalCost(
            self,
            costId: construction.ConstructionCost
            ) -> common.ScalarCalculation:
        total = construction.calculateNumericModifierSequence(
            modifiers=[entry.cost(costId=costId) for entry in self._entries if entry.cost(costId=costId)])
        if not total:
            raise RuntimeError(
                f'Unable to calculate {costId.value} for manifest section {self._name} as starting modifier is not absolute')
        return common.Calculator.equals(
            value=total,
            name=f'Total {costId.value}')

class Manifest(object):
    def __init__(
            self,
            costsType: typing.Type[construction.ConstructionCost]
            ) -> None:
        self._costsType = costsType
        self._sections: typing.List[ManifestSection] = []

    def costsType(self) -> typing.Type[construction.ConstructionCost]:
        return self._costsType

    def isEmpty(self) -> bool:
        return not self._sections

    def sections(self) -> typing.Collection[ManifestSection]:
        return self._sections

    def createSection(
            self,
            name: str
            ) -> ManifestSection:
        section = ManifestSection(name=name)
        self._sections.append(section)
        return section

    def totalCost(
            self,
            costId: construction.ConstructionCost
            ) -> common.ScalarCalculation:
        costs = []
        for section in self._sections:
            costs.append(section.totalCost(costId=costId))
        return common.Calculator.sum(
            values=costs,
            name=f'Total {costId.value}')

    def clear(self) -> None:
        self._sections.clear()
