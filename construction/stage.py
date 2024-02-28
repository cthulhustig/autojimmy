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
            baseType: typing.Type[construction.ComponentInterface],
            defaultType: typing.Optional[typing.Type[construction.ComponentInterface]] = None,
            minComponents: typing.Optional[int] = None,
            maxComponents: typing.Optional[int] = None,
            # Forcing a component only makes sense if there is no minimum. It
            # allows the stage to be empty if there are no compatible components
            # but causes construction to force there to be a minimum of one
            # component in the stage if there are any compatible components.
            forceComponent: bool = False
            ) -> None:
        assert((minComponents == None) or (minComponents >= 0))
        assert((maxComponents == None) or (maxComponents > 0))
        assert((minComponents == None or maxComponents == None) or (minComponents <= maxComponents))
        assert((not forceComponent) or (not minComponents))
        self._name = name
        self._sequence = sequence
        self._phase = phase
        self._baseType = baseType
        self._defaultType = defaultType
        self._minComponents = minComponents
        self._maxComponents = maxComponents
        self._forceComponent = forceComponent
        self._components: typing.List[construction.ComponentInterface] = []

    def name(self) -> str:
        return self._name

    def sequence(self) -> typing.Optional[str]:
        return self._sequence

    def phase(self) -> construction.ConstructionPhase:
        return self._phase

    def baseType(self) -> typing.Type[construction.ComponentInterface]:
        return self._baseType

    def defaultComponent(self) -> typing.Optional[construction.ComponentInterface]:
        return self._defaultType() if self._defaultType else None

    def minComponents(self) -> typing.Optional[int]:
        return self._minComponents
    
    def maxComponents(self) -> typing.Optional[int]:
        return self._maxComponents

    def requirement(self) -> RequirementLevel:
        if self._minComponents != None and self._minComponents >= 1:
            return ConstructionStage.RequirementLevel.Mandatory
        elif self._forceComponent:
            return ConstructionStage.RequirementLevel.Desirable
        else:
            return ConstructionStage.RequirementLevel.Optional
    
    def isValid(self) -> bool:
        componentCount = self.componentCount()
        
        if self._minComponents != None and \
            componentCount < self._minComponents:
            return False
        
        if self._maxComponents != None and \
            componentCount > self._maxComponents:
            return False
        
        return True

    def matchesComponent(
            self,
            component: typing.Type[construction.ComponentInterface]
            ) -> bool:
        if not isinstance(component, type):
            component = type(component)

        return issubclass(component, self._baseType)
    
    def componentCount(self) -> int:
        return len(self._components)
    
    def hasFreeCapacity(
            self,
            requiredCapacity: int = 1
            ) -> bool:
        if not self._maxComponents:
            return True # No max capacity
        return (len(self._components) + requiredCapacity) <= self._maxComponents

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
        self._components.append(component)

    def insertComponent(
            self,
            index: int,
            component: construction.ComponentInterface,
            ) -> None:
        self._components.insert(index, component)

    def removeComponent(
            self,
            component: construction.ComponentInterface,
            ) -> int:
        index = self._components.index(component)
        if index >= 0:
            self._components.pop(index)
        return index
    
    def removeComponentAt(
            self,
            index: int
            ) -> typing.Optional[construction.ComponentInterface]:
        if index >= len(self._components):
            return None
        return self._components.pop(index)

    def clearComponents(self) -> None:
        self._components.clear()
