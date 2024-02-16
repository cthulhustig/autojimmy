import common
import construction
import robots
import typing

class AgilityEnhancement(robots.AgilityEnhancementInterface):
    """
    - Requirement: Not compatible with no locomotion for primary locomotion
    type (p22)
    - Requirement: Not compatible with Tactical Speed Reduction (p22) 
    """    
    # NOTE: The requirement that this component isn't compatible with Tactile
    # Speed Reduction is handled by that component as it occurs later in
    # construction
    # NOTE: The rules say "Locomotion modifications alter the performance
    # characteristics of a robot’s primary form of locomotion". Based on this
    # I'm making this component only apply to the primary locomotion type.
    # The logical side effect of this is you won't be able to apply it if you
    # use the rule that Thruster locomotion can be applied as a secondary
    # locomotion with the primary locomotion set to None (p17)
    # TODO: Handle Athletics skill

    def __init__(
            self,
            componentString: str,
            agilityModifier: typing.Union[int, common.ScalarCalculation],
            costPercent: typing.Union[int, common.ScalarCalculation]
            ) -> None:
        super().__init__()

        if not isinstance(agilityModifier, common.ScalarCalculation):
            agilityModifier = common.ScalarCalculation(
                value=agilityModifier,
                name=f'{componentString} Agility Modifier')
            
        if not isinstance(costPercent, common.ScalarCalculation):
            costPercent = common.ScalarCalculation(
                value=costPercent,
                name=f'{componentString} Cost Percentage')

        self._componentString = componentString
        self._agilityModifier = agilityModifier
        self._costPercent = costPercent

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Agility Enhancement'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        # Not compatible with no primary locomotion
        locomotion = context.findFirstComponent(
            componentType=robots.NoPrimaryLocomotion,
            sequence=sequence)
        return locomotion == None
    
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
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())        

        cost = common.Calculator.takePercentage(
            value=context.baseChassisCredits(sequence=sequence),
            percentage=self._costPercent,
            name=f'{self._componentString} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Speed,
            modifier=construction.ConstantModifier(self._agilityModifier)))

        context.applyStep(
            sequence=sequence,
            step=step)

class Plus1Agility(AgilityEnhancement):
    """
    - Speed: +1
    - Skill: Athletics (dexterity) 1
    - Cost: 100% of Base Chassis Cost   
    """
    def __init__(self) -> None:
        super().__init__(
            componentString='Agility +1',
            agilityModifier=1,
            costPercent=100)
        
class Plus2Agility(AgilityEnhancement):
    """
    - Speed: +2
    - Skill Athletics (dexterity) 2
    - Cost: 200% of Base Chassis Cost  
    """    
    def __init__(self) -> None:
        super().__init__(
            componentString='Agility +2',
            agilityModifier=2,
            costPercent=200)

class Plus3Agility(AgilityEnhancement):
    """
    - Speed: +3
    - Skill Athletics (dexterity) 3
    - Cost: 400% of Base Chassis Cost 
    """
    def __init__(self) -> None:
        super().__init__(
            componentString='Agility +3',
            agilityModifier=3,
            costPercent=400)
        
class Plus4Agility(AgilityEnhancement):
    """
    - Speed: +4
    - Skill Athletics (dexterity) 4
    - Cost: 800% of Base Chassis Cost       
    """
    def __init__(self) -> None:
        super().__init__(
            componentString='Agility +4',
            agilityModifier=4,
            costPercent=800)
