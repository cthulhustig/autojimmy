import common
import construction
import gunsmith
import typing

class LoaderQuantity(gunsmith.WeaponComponentInterface):
    """
    - Note: Requires 2 minor actions to load contents into weapon
    - Requirement: Only compatible with Fixed Magazine Feed
    """
    _LoaderNote = 'Requires 2 minor actions to load content into weapon'

    def __init__(
            self,
            componentString: str,
            fixedCost: typing.Optional[typing.Union[int, common.ScalarCalculation]],
            ) -> None:
        super().__init__()

        if not isinstance(fixedCost, common.ScalarCalculation):
            fixedCost = common.ScalarCalculation(
                value=fixedCost,
                name=f'{componentString} Cost')

        self._componentString = componentString
        self._fixedCost = fixedCost

        self._numberOfLoadersOption = construction.IntegerOption(
            id='Quantity',
            name='Quantity',
            value=1,
            minValue=1,
            description='Specify the number of loaders.')

    def componentString(self) -> str:
        return self._componentString

    def instanceString(self) -> str:
        return f'{self.componentString()} x{self._numberOfLoadersOption.value()}'

    def typeString(self) -> str:
        return 'Loader Quantity'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Only compatible with weapons that have a receiver.
        if not context.hasComponent(
                componentType=gunsmith.Receiver,
                sequence=sequence):
            return False

        return context.hasComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence) \
            and context.hasComponent(
                componentType=gunsmith.FixedMagazineFeed,
                sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._numberOfLoadersOption]

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        pass

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        loaderCount = common.ScalarCalculation(
            value=self._numberOfLoadersOption.value(),
            name='Specified Loader Count')
        totalCost = common.Calculator.multiply(
            lhs=self._fixedCost,
            rhs=loaderCount,
            name=f'{self.componentString()} Cost')

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            credits=construction.ConstantModifier(value=totalCost),
            notes=[self._LoaderNote])

        context.applyStep(
            sequence=sequence,
            step=step)

class SpeedLoaderQuantity(LoaderQuantity):
    """
    - Cost: Cr5
    - Requirement: Only compatible with Fixed Magazine Feed
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Speedloader',
            fixedCost=5)

class ClipLoaderQuantity(LoaderQuantity):
    """
    - Cost: Cr5
    - Requirement: Only compatible with Fixed Magazine Feed
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Clip',
            fixedCost=5)

class CassetteLoaderQuantity(LoaderQuantity):
    """
    - Cost: Cr10
    - Requirement: Only compatible with Fixed Magazine Feed
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Cassette',
            fixedCost=10)
