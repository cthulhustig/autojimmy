import common
import construction
import robots
import typing

class Chassis(robots.ChassisInterface):
    """
    - Trait: Large(Attack Roll DM) if Attack Roll DM > 0 (p13)
    - Trait: Small(Attack Roll DM) if Attack Roll DM < 0 (p13)
    """
    # TODO: I'm really not sure about my my interpretation of the value of
    # the Large/Small traits. The only difference between the Trait and the
    # Attack Roll DM attribute I can see so far is the wording fro the trait
    # says it for ranged attacks (p8). It's probably worth having a look at
    # some of the example robots to see if they give any clues

    # TODO: The chassis description (p13) has the following. It might make a
    # good note. It may need to be added in finalisation if there are any
    # modifiers that can increase the robots hits
    #
    # When a robot’s Hits reach 0, it is inoperable and considered wrecked, or
    # at least cannot be easily repaired; at cumulative damage equal to twice
    # its Hits the robot is irreparably destroyed.

    # TODO: This is just a temporary value I hacked in. There must be an
    # absolute min somewhere in the rules
    # - You can't get a Locomotion < TL5
    _MinTechLevel = 3

    # TODO: It might be worth a note to explain that the attack roll DM is a
    # modifier on the attackers roll

    def __init__(
            self,
            componentString: str,
            baseSlots: typing.Union[int, common.ScalarCalculation],
            baseHits: typing.Union[int, common.ScalarCalculation],
            attackDM: typing.Union[int, common.ScalarCalculation],
            basicCost: typing.Union[int, common.ScalarCalculation],
            ) -> None:
        super().__init__()

        if not isinstance(baseSlots, common.ScalarCalculation):
            baseSlots = common.ScalarCalculation(
                value=baseSlots,
                name=f'{componentString} Chassis Base Slots')
            
        if not isinstance(baseHits, common.ScalarCalculation):
            baseHits = common.ScalarCalculation(
                value=baseHits,
                name=f'{componentString} Chassis Base Hits')
            
        if not isinstance(attackDM, common.ScalarCalculation):
            attackDM = common.ScalarCalculation(
                value=attackDM,
                name=f'{componentString} Chassis Attack Roll DM')

        if not isinstance(basicCost, common.ScalarCalculation):
            basicCost = common.ScalarCalculation(
                value=basicCost,
                name=f'{componentString} Chassis Basic Cost')        

        self._componentString = componentString
        self._baseSlots = baseSlots
        self._baseHits = baseHits
        self._attackDM = attackDM
        self._basicCost = basicCost

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
            attributeId=robots.RobotAttributeId.BaseSlots,
            value=self._baseSlots))
        
        # Init Available Slots to the base slots
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.AvailableSlots,
            value=self._baseSlots))
        
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.BaseHits,
            value=self._baseHits))
        
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.AttackRollDM,
            value=self._attackDM))

        if self._attackDM.value() < 0:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=robots.RobotAttributeId.Small,
                value=self._attackDM))
        elif self._attackDM.value() > 0:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=robots.RobotAttributeId.Large,
                value=self._attackDM))

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
            componentString='Size 1',
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
            componentString='Size 2',
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
            componentString='Size 3',
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
            componentString='Size 4',
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
            componentString='Size 5',
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
            componentString='Size 6',
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
            componentString='Size 7',
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
            componentString='Size 8',
            baseSlots=128,
            baseHits=72,
            attackDM=+3,
            basicCost=8000)