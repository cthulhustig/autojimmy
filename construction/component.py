import construction
import typing

class ComponentInterface(object):
    def componentString(self) -> str:
        raise RuntimeError('The componentString method must be implemented by classes derived from ComponentInterface')

    def instanceString(self) -> str:
        # Use component string for instance string by default
        return self.componentString()

    def typeString(self) -> str:
        raise RuntimeError('The typeString method must be implemented by classes derived from ComponentInterface')

    def isCompatible(
            self,
            sequence: str,
            context: 'construction.ConstructionContext'
            ) -> bool:
        raise RuntimeError('The isCompatible method must be implemented by classes derived from ComponentInterface')

    def options(self) -> typing.List[construction.ComponentOption]:
        raise RuntimeError('The options method must be implemented by classes derived from ComponentInterface')

    def updateOptions(
            self,
            sequence: str,
            context: 'construction.ConstructionContext'
            ) -> None:
        raise RuntimeError('The updateOptions method must be implemented by classes derived from ComponentInterface')

    def createSteps(
            self,
            sequence: str,
            context: 'construction.ConstructionContext'
            ) -> None:
        raise RuntimeError('The createSteps method must be implemented by classes derived from ComponentInterface')
