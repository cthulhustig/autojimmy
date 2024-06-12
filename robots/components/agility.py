import common
import construction
import robots
import traveller
import typing

class AgilityEnhancement(robots.RobotComponentInterface):
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
    # NOTE: It wasn't one of the things that Geir clarified (I forgot to ask
    # him) but I'm working on the assumption the Athletics (Dexterity) given
    # by an Agility Enhancement stacks with any levels from software skill
    # packages or from manipulators (p26)
    # TODO: The book doesn't seem to say if characteristics modifier for DEX
    # applies to checks made with the Athletics (Dexterity) skill this gives.
    # I'd be included to say they don't as that's how all the other skills
    # received from hardware components seem to work.

    def __init__(
            self,
            agilityModifier: int,
            costPercent: int
            ) -> None:
        super().__init__()

        self._componentString = f'Agility +{agilityModifier}'
        self._agilityModifier = common.ScalarCalculation(
            value=agilityModifier,
            name=f'{self._componentString} Agility Modifier')  
        self._costPercent = common.ScalarCalculation(
            value=costPercent,
            name=f'{self._componentString} Cost Percentage')

    def agilityModifier(self) -> int:
        return self._agilityModifier.value()

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
            attributeId=robots.RobotAttributeId.Agility,
            modifier=construction.ConstantModifier(self._agilityModifier)))        

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Speed,
            modifier=construction.ConstantModifier(self._agilityModifier)))
        
        step.addFactor(factor=construction.SetSkillFactor(
            skillDef=traveller.AthleticsSkillDefinition,
            speciality=traveller.AthleticsSkillSpecialities.Dexterity,
            levels=self._agilityModifier,
            flags=construction.SkillFlags(0)))

        context.applyStep(
            sequence=sequence,
            step=step)

class Plus1Agility(AgilityEnhancement):
    """
    - Agility: +1
    - Speed: +1
    - Skill: Athletics (dexterity) 1
    - Cost: 100% of Base Chassis Cost   
    """
    def __init__(self) -> None:
        super().__init__(
            agilityModifier=1,
            costPercent=100)
        
class Plus2Agility(AgilityEnhancement):
    """
    - Agility: +2
    - Speed: +2
    - Skill Athletics (dexterity) 2
    - Cost: 200% of Base Chassis Cost  
    """    
    def __init__(self) -> None:
        super().__init__(
            agilityModifier=2,
            costPercent=200)

class Plus3Agility(AgilityEnhancement):
    """
    - Agility: +3
    - Speed: +3
    - Skill Athletics (dexterity) 3
    - Cost: 400% of Base Chassis Cost 
    """
    def __init__(self) -> None:
        super().__init__(
            agilityModifier=3,
            costPercent=400)
        
class Plus4Agility(AgilityEnhancement):
    """
    - Agility: +4
    - Speed: +4
    - Skill Athletics (dexterity) 4
    - Cost: 800% of Base Chassis Cost       
    """
    def __init__(self) -> None:
        super().__init__(
            agilityModifier=4,
            costPercent=800)
