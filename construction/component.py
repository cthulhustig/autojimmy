import construction
import typing

class ComponentInterface(object):
    def componentString(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from ComponentInterface so must implement componentString')

    def instanceString(self) -> str:
        # Use component string for instance string by default
        return self.componentString()

    def typeString(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from ComponentInterface so must implement typeString')

    def isCompatible(
            self,
            sequence: str,
            context: 'construction.ConstructionContext'
            ) -> bool:
        raise RuntimeError(f'{type(self)} is derived from ComponentInterface so must implement isCompatible')
    
    # TODO: This is a hack, this is meant to be an abstract interface so
    # shouldn't have implementations (same applies to instanceString). I need to
    # rework stuff so rather than a RobotComponentInterface there is a
    # RobotComponent base class (same for weapon component). The construction
    # type specific base class would have some base implementations (instanceString,
    # dependencies, options). Note that this could allow a load of boiler plate
    # options implementations that just return an empty list to be removed, but care
    # needs to be taken to only remove it from components and not impls.
    # The current component type specific interfaces should be turned into component
    # base classes and moved into the corresponding .py file. In the majority of cases
    # this should just be a case of either removing the Interface part from the class
    # name and moving the code to the .py file _or_ deleting the interface class if
    # there is already a component type specific base component that is suitable and
    # updating it to inherit from the construction type specific base component (e.g.
    # RobotComponent). There are some complications in around components where there
    # are currently multiple levels of interface inheritance (e.g. how there are
    # primary and secondary locomotion component interfaces that inherit from a base
    # locomotion component interface). This inheritance needs to be preserved but I
    # think it's just a case of moving the code to the respective .py file and removing
    # Interface from all the class names.
    # I don't think this approach will hit problems with dependency loops
    def orderAfter(self) -> typing.List[typing.Type['ComponentInterface']]:
        return []    
    
    def options(self) -> typing.List[construction.ComponentOption]:
        raise RuntimeError(f'{type(self)} is derived from ComponentInterface so must implement options')

    def updateOptions(
            self,
            sequence: str,
            context: 'construction.ConstructionContext'
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from ComponentInterface so must implement updateOptions')

    def createSteps(
            self,
            sequence: str,
            context: 'construction.ConstructionContext'
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from ComponentInterface so must implement createSteps')
