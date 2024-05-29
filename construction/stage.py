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
            forceComponent: bool = False,
            isInternal: bool = False
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
        self._isInternal = isInternal
        self._components: typing.List[construction.ComponentInterface] = []

    def name(self) -> str:
        return self._name

    # Common stages will have a sequence of None
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
    
    def isInternal(self) -> bool:
        return self._isInternal

    def requirement(self) -> RequirementLevel:
        if self._minComponents != None and self._minComponents >= 1:
            return ConstructionStage.RequirementLevel.Mandatory
        elif self._forceComponent:
            return ConstructionStage.RequirementLevel.Desirable
        else:
            return ConstructionStage.RequirementLevel.Optional
    
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

    def components(
            self,
            dependencyOrder: bool = False
            ) -> typing.Collection[construction.ComponentInterface]:
        if not dependencyOrder:
            return self._components
    
        dependencyMap = {}
        for component in self._components:
            dependencies = component.orderAfter()
            if not dependencies:
                continue

            # Find all the components this one is dependant on
            for other in reversed(self._components):
                if type(other) not in dependencies:
                    continue

                dependantComponents = dependencyMap.get(component)
                if dependantComponents == None:
                    dependantComponents = set()
                    dependencyMap[component] = dependantComponents
                dependantComponents.add(other)
        if not dependencyMap:
            # No dependencies so just return standard component list
            return self._components

        components = []

        # Add components that have no dependencies
        for component in self._components:
            if component not in dependencyMap:
                components.append(component)

        # NOTE: Add components that have dependencies directly after the last
        # component they are dependant on. The map is processed in reverse
        # order so that components that are dependant on the same component
        # will be added to the final list of components in the same relative
        # order they had before they were moved position (unless there is also
        # an ordering dependency between the two components).
        # Due to the fact entries are added to the map in the order the appear
        # in the source list of components it means, if the iteration order
        # wasn't reversed, the logically first component would be added directly
        # after the component it's dependant on. However, when the logically
        # second component is added it will also be added directly after the
        # component it's dependant on but _before_ the logically first
        # component. The end result is the construction order between the two
        # components would be the reverse of their logical order.
        # This level of construction order _shouldn't_ be an issue as it would
        # only occur if the components that changed order weren't related.
        # However it seems desirable to avoid the potential for odd bugs by
        # just reversing the order when it's so cheap to do.
        for component, dependencies in reversed(dependencyMap.items()):
            for index in range(len(components) - 1, -1, -1):
                if components[index] in dependencies:
                    components.insert(index + 1, component)
                    break

        assert(len(components) == len(self._components))
        return components

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
        try:
            index = self._components.index(component)
        except ValueError:
            return -1
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

    def containsComponent(
            self,
            component: construction.ComponentInterface
            ) -> bool:
        return component in self._components
