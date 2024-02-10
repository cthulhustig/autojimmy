import enum
import construction
import typing

class ConstructionStage(object):
    class RequirementLevel(enum.Enum):
        Mandatory = 0 # Must have a selection for construction to continue
        Desirable = 1 # Must have a selection if any compatible components are available
        Optional = 2 # Completely optional

    def __init__(
            self,
            name: str,
            sequence: typing.Optional[str],
            phase: construction.ConstructionPhase,
            requirement: RequirementLevel,
            singular: bool,
            baseType: typing.Type[construction.ComponentInterface],
            defaultType: typing.Optional[typing.Type[construction.ComponentInterface]] = None
            ) -> None:
        self._name = name
        self._sequence = sequence
        self._phase = phase
        self._requirement = requirement
        self._singular = singular
        self._baseType = baseType
        self._defaultType = defaultType
        self._components: typing.List[construction.ComponentInterface] = []

    def name(self) -> str:
        return self._name

    def sequence(self) -> typing.Optional[str]:
        return self._sequence

    def phase(self) -> construction.ConstructionPhase:
        return self._phase

    def requirement(self) -> RequirementLevel:
        return self._requirement

    def singular(self) -> bool:
        return self._singular

    def baseType(self) -> typing.Type[construction.ComponentInterface]:
        return self._baseType

    def defaultComponent(self) -> typing.Optional[construction.ComponentInterface]:
        return self._defaultType() if self._defaultType else None

    def matchesComponent(
            self,
            component: typing.Type[construction.ComponentInterface]
            ) -> bool:
        if not isinstance(component, type):
            component = type(component)

        return issubclass(component, self._baseType)

    def components(self) -> typing.Collection[construction.ComponentInterface]:
        return self._components

    def setComponents(
            self,
            components: typing.Iterable[construction.ComponentInterface]
            ) -> None:
        self._components = list(components)

    def addComponent(
            self,
            component: construction.ComponentInterface
            ) -> None:
        if self.singular() and len(self._components) > 0:
            self._components[0] = component
        else:
            self._components.append(component)

    def insertComponent(
            self,
            index: int,
            component: construction.ComponentInterface,
            ) -> None:
        if self.singular() and len(self._components) > 0:
            self._components[0] = component
        else:
            self._components.insert(index, component)

    def removeComponent(
            self,
            component: construction.ComponentInterface,
            ) -> int:
        index = self._components.index(component)
        if index >= 0:
            self._components.pop(index)
        return index

    def clearComponents(self) -> None:
        self._components.clear()
