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

    def orderAfter(self) -> typing.List[typing.Type['ComponentInterface']]:
        return []

    def options(self) -> typing.List[construction.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: 'construction.ConstructionContext'
            ) -> None:
        pass

    def createSteps(
            self,
            sequence: str,
            context: 'construction.ConstructionContext'
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from ComponentInterface so must implement createSteps')
