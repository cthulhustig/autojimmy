import common
import construction
import robots
import typing

class Chassis(robots.RobotComponentInterface):
    """
    - Trait: Large(Attack Roll DM) if Attack Roll DM > 0 (p13)
    - Trait: Small(Attack Roll DM) if Attack Roll DM < 0 (p13)
    - Trait: Protection (p19)
        - TL6-8: Base Protection: 2
        - TL9-11: Base Protection: 3
        - TL12-14: Base Protection: 4
        - TL15-17: Base Protection: 4
        - TL18+: Base Protection: 5
    """

    # List of tuples structured as follows
    # Min TL, Max TL, Base Protection
    _BaseProtectionDetails = [
        (6, 8, 2),
        (9, 11, 3),
        (12, 14, 4),
        (15, 17, 4),
        (18, None, 5)
    ]

    # NOTE: It only seems logical that there must be a min TL for a robot
    # chassis but the rules don't give one. Fair enough, you could probably
    # construct a chassis with only basic metal working skills but for it to
    # be a robot chassis it needs to be part of a robot. As some of the
    # mandatory components for building a robot have a min TL then it implies
    # it can't be robot chassis before the highest of those TL's (earlier than
    # that and it's just a chassis not a robot chassis).
    # From a usability point of view it's desirable to not have the min TL of
    # the chassis lower than the min TL of any of the mandatory components as
    # it would means the user could get part way through creating creating a
    # low TL robot, only to find they can't complete it because a mandatory
    # component is incompatible.
    # - You can't get a Locomotion < TL5, even the 'None' locomotion has a Min
    # TL of 5 in the table on p16
    # - You can't get a Brain < TL7
    _MinTechLevel = 7

    def __init__(
            self,
            size: int,
            baseSlots: int,
            baseHits: int,
            attackDM: int,
            basicCost: int,
            ) -> None:
        super().__init__()

        self._componentString = f'Size {size}'
        self._size = common.ScalarCalculation(
            value=size,
            name=f'Chassis Size')        
        self._baseSlots = common.ScalarCalculation(
            value=baseSlots,
            name=f'{self._componentString} Chassis Base Slots')
        self._baseHits = common.ScalarCalculation(
            value=baseHits,
            name=f'{self._componentString} Chassis Base Hits')
        self._attackDM = common.ScalarCalculation(
            value=attackDM,
            name=f'{self._componentString} Chassis Attack Roll DM')
        self._basicCost = common.ScalarCalculation(
            value=basicCost,
            name=f'{self._componentString} Chassis Basic Cost')

    def size(self) -> int:
        return self._size.value()

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Chassis'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return context.techLevel() >= self._MinTechLevel
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        pass

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        context.applyStep(
            sequence=sequence,
            step=self._createStep(sequence=sequence, context=context))

    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        step.setCredits(
            credits=construction.ConstantModifier(value=self._basicCost))
        
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Size,
            value=self._size))        

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.BaseSlots,
            value=self._baseSlots))
        
        # Init Available Slots to the base slots
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.MaxSlots,
            value=self._baseSlots))
        
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Hits,
            value=self._baseHits))

        if self._attackDM.value() < 0:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=robots.RobotAttributeId.Small,
                value=self._attackDM))
        elif self._attackDM.value() > 0:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=robots.RobotAttributeId.Large,
                value=self._attackDM))
            
        currentTL = context.techLevel()
        for minTL, maxTL, protection in Chassis._BaseProtectionDetails:
            if currentTL >= minTL and ((maxTL == None) or (currentTL <= maxTL)):
                range = f'{minTL}-{maxTL}' if maxTL != None else f'{minTL}+'
                protection = common.ScalarCalculation(
                    value=protection,
                    name=f'TL{range} Chassis Base Protection')
                step.addFactor(factor=construction.SetAttributeFactor(
                    attributeId=robots.RobotAttributeId.BaseProtection,
                    value=protection))                
                step.addFactor(factor=construction.SetAttributeFactor(
                    attributeId=robots.RobotAttributeId.Protection,
                    value=protection))
                break

        return step

class Size1Chassis(Chassis):
    """
    - Base Slots: 1
    - Base Hits: 1
    - Attack Roll DM: -4
    - Basic Cost: Cr100    
    """

    def __init__(self) -> None:
        super().__init__(
            size=1,
            baseSlots=1,
            baseHits=1,
            attackDM=-4,
            basicCost=100)
        
class Size2Chassis(Chassis):
    """
    - Base Slots: 2
    - Base Hits: 4
    - Attack Roll DM: -3
    - Basic Cost: Cr200
    """

    def __init__(self) -> None:
        super().__init__(
            size=2,
            baseSlots=2,
            baseHits=4,
            attackDM=-3,
            basicCost=200)

class Size3Chassis(Chassis):
    """
    - Base Slots: 4
    - Base Hits: 8
    - Attack Roll DM: -2
    - Basic Cost: Cr400
    """

    def __init__(self) -> None:
        super().__init__(
            size=3,
            baseSlots=4,
            baseHits=8,
            attackDM=-2,
            basicCost=400)
        
class Size4Chassis(Chassis):
    """
    - Base Slots: 8
    - Base Hits: 12
    - Attack Roll DM: -1
    - Basic Cost: Cr800
    """

    def __init__(self) -> None:
        super().__init__(
            size=4,
            baseSlots=8,
            baseHits=12,
            attackDM=-1,
            basicCost=800)
        
class Size5Chassis(Chassis):
    """
    - Base Slots: 16
    - Base Hits: 20
    - Attack Roll DM: +0
    - Basic Cost: Cr1000
    """

    def __init__(self) -> None:
        super().__init__(
            size=5,
            baseSlots=16,
            baseHits=20,
            attackDM=+0,
            basicCost=1000)
        
class Size6Chassis(Chassis):
    """
    - Base Slots: 32
    - Base Hits: 32
    - Attack Roll DM: +1
    - Basic Cost: Cr2000
    """

    def __init__(self) -> None:
        super().__init__(
            size=6,
            baseSlots=32,
            baseHits=32,
            attackDM=+1,
            basicCost=2000)
        
class Size7Chassis(Chassis):
    """
    - Base Slots: 64
    - Base Hits: 50
    - Attack Roll DM: +2
    - Basic Cost: Cr4000
    """

    def __init__(self) -> None:
        super().__init__(
            size=7,
            baseSlots=64,
            baseHits=50,
            attackDM=+2,
            basicCost=4000)
        
class Size8Chassis(Chassis):
    """
    - Base Slots: 128
    - Base Hits: 72
    - Attack Roll DM: +3
    - Basic Cost: Cr8000
    """

    def __init__(self) -> None:
        super().__init__(
            size=8,
            baseSlots=128,
            baseHits=72,
            attackDM=+3,
            basicCost=8000)