import common
import gunsmith
import typing

class ManifestEntry(object):
    def __init__(
            self,
            component: str,
            costs: typing.Optional[typing.Mapping[gunsmith.ConstructionCost, gunsmith.NumericModifierInterface]] = None,
            factors: typing.Optional[typing.Iterable[gunsmith.FactorInterface]] = None
            ) -> None:
        self._text = component
        self._costs = dict(costs) if costs else {}
        self._factors = list(factors) if factors else []

    def component(self) -> str:
        return self._text

    def cost(self, costId: gunsmith.ConstructionCost):
        return self._costs.get(costId)

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
            costs: typing.Optional[typing.Mapping[gunsmith.ConstructionCost, gunsmith.NumericModifierInterface]] = None,
            factors: typing.Optional[typing.Iterable[gunsmith.FactorInterface]] = None
            ) -> None:
        entry = ManifestEntry(
            component=component,
            costs=costs,
            factors=factors)
        self._entries.append(entry)
        return entry

    def totalCost(
            self,
            costId: gunsmith.ConstructionCost
            ) -> common.ScalarCalculation:
        total = gunsmith.calculateNumericModifierSequence(
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
            costsType: typing.Type[gunsmith.ConstructionCost]
            ) -> None:
        self._costsType = costsType
        self._sections: typing.List[ManifestSection] = []

    def costsType(self) -> typing.Type[gunsmith.ConstructionCost]:
        return self._costsType

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
            costId: gunsmith.ConstructionCost
            ) -> common.ScalarCalculation:
        costs = []
        for section in self._sections:
            costs.append(section.totalCost(costId=costId))
        return common.Calculator.sum(
            values=costs,
            name=f'Total {costId.value}')

    def clear(self) -> None:
        self._sections.clear()
