import common
import construction
import robots
import typing

class Brain(robots.BrainInterface):
    """
    - Slots: The number of slots taken up by a brain works like this (p66)
        - The brain has no slot requirement If the robots Size is greater than
        or equal to:
        (Computer/X - (RobotTL - BrainMinTL))
        - Otherwise the brain costs 1 slot
    """
    # TODO: Do something with Computer/X rating. Could be a note, could be
    # an attribute. Note I don't __think__ this is a skill

    _HighRelativeBrainSizeSlotCost = common.ScalarCalculation(
        name='High Relative Brain Size Required Slots',
        value=1)

    def __init__(
            self,
            componentString: str,
            minTL: typing.Union[int, common.ScalarCalculation],
            cost: typing.Union[int, common.ScalarCalculation],
            intelligence: typing.Union[int, common.ScalarCalculation],
            inherentBandwidth: typing.Union[int, common.ScalarCalculation],
            skillCount: typing.Union[int, common.ScalarCalculation],
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__()

        if not isinstance(minTL, common.ScalarCalculation):
            minTL = common.ScalarCalculation(
                value=minTL,
                name=f'{componentString} Brain Minimum TL') 
            
        if not isinstance(cost, common.ScalarCalculation):
            cost = common.ScalarCalculation(
                value=cost,
                name=f'{componentString} Brain Cost') 
            
        if not isinstance(intelligence, common.ScalarCalculation):
            intelligence = common.ScalarCalculation(
                value=intelligence,
                name=f'{componentString} Brain INT Characteristic')             
            
        if not isinstance(inherentBandwidth, common.ScalarCalculation):
            inherentBandwidth = common.ScalarCalculation(
                value=inherentBandwidth,
                name=f'{componentString} Brain Inherent Bandwidth')
            
        if not isinstance(skillCount, common.ScalarCalculation):
            skillCount = common.ScalarCalculation(
                value=skillCount,
                name=f'{componentString} Brain Base Skill Count')      

        self._componentName = componentString
        self._minTL = minTL
        self._cost = cost
        self._intelligence = intelligence
        self._inherentBandwidth = inherentBandwidth
        self._skillCount = skillCount
        self._notes = list(notes)

    def componentString(self) -> str:
        return self._componentName
    
    def typeString(self) -> str:
        return 'Brain'        

    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        if context.techLevel() < self._minTL.value():
            return False

        return context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence)
    
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
        
        robotTL = common.ScalarCalculation(
            value=context.techLevel(),
            name='Robot TL')
        
        robotSize = context.attributeValue(
            attributeId=robots.RobotAttributeId.Size,
            sequence=sequence)
        assert(isinstance(robotSize, common.ScalarCalculation))
        
        # A brain requires no slots if it's Size is greater than or equal the
        # threshold below, otherwise it requires 1 slot
        # (Computer/X - (RobotTL - BrainMinTL))
        brainSizeThreshold = common.Calculator.subtract(
            lhs=self._inherentBandwidth,
            rhs=common.Calculator.subtract(
                lhs=robotTL,
                rhs=self._minTL),
            name='Brain Size Threshold')
        if robotSize.value() < brainSizeThreshold.value():
            step.setSlots(slots=construction.ConstantModifier(
                value=Brain._HighRelativeBrainSizeSlotCost))
        
        step.setCredits(credits=construction.ConstantModifier(value=self._cost))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Intelligence,
            value=self._intelligence))
        
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.InherentBandwidth,
            value=self._inherentBandwidth))
        
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.MaxSkills,
            value=self._skillCount))               
        
        return step
    
class PrimitiveBrain(Brain):
    """
    - Trait: INT 1
    - Trait: Computer/0
    - Trait: Skill Count -2
    - Trait: Inherent Bandwidth 0    
    - Note: Programmable
    - Requirement: I don't think this is compatible with additional skills  
    """
    # TODO: Handle incompatible with additional skills if that is how it
    # actually works. It seems odd that it would have a skill count (even
    # if it is a negative one, if it isn't compatible with additional skills)
      
    def __init__(
            self,
            minTL: int,
            cost: int
            ) -> None:
        super().__init__(
            componentString=f'Primitive TL {minTL}',
            minTL=minTL,
            cost=cost,
            intelligence=1,
            inherentBandwidth=0,
            skillCount=-2,
            notes=['Programmable']) # TODO: This is a crap note, needs more context#
        
class PrimitiveTL7Brain(PrimitiveBrain):
    """
    - Min TL: 7
    - Cost: Cr10000
    - Trait: INT 1
    - Trait: Computer/0
    - Trait: Skill Count -2
    - Trait: Inherent Bandwidth 0
    - Note: Programmable
    """
      
    def __init__(self) -> None:
        super().__init__(
            minTL=7,
            cost=10000)
        
class PrimitiveTL8Brain(PrimitiveBrain):
    """
    - Min TL: 8
    - Cost: Cr100
    - Trait: INT 1
    - Trait: Computer/0
    - Trait: Skill Count -2
    - Trait: Inherent Bandwidth 0
    - Note: Programmable
    """
      
    def __init__(self) -> None:
        super().__init__(
            minTL=8,
            cost=100)
 
class BasicBrain(Brain):
    """
    - Trait: Computer/1
    - Trait: Skill Count -1
    - Trait: Inherent Bandwidth 1
    - Note: Limited Language, Security/0
    - Requirement: I don't think this is compatible with additional skills  
    """
    # TODO: Handle incompatible with additional skills if that is how it
    # actually works. It seems odd that it would have a skill count (even
    # if it is a negative one, if it isn't compatible with additional skills)
      
    def __init__(
            self,
            minTL: int,
            cost: int,
            intelligence: int
            ) -> None:
        super().__init__(
            componentString=f'Basic TL {minTL}',
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=1,
            skillCount=-1,
            notes=['Limited Language, Security/0']) # TODO: This is a crap note
                
class BasicTL8Brain(BasicBrain):
    """
    - Min TL: 8
    - Cost: Cr20000
    - Trait: INT 3
    - Trait: Computer/1
    - Trait: Skill Count -1
    - Trait: Inherent Bandwidth 1
    - Note: Limited Language, Security/0
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=8,
            cost=20000,
            intelligence=3)
        
class BasicTL10Brain(BasicBrain):
    """
    - Min TL: 10
    - Cost: Cr4000
    - Trait: Computer/1
    - Trait: INT 4
    - Trait: Skill Count -1
    - Trait: Inherent Bandwidth 1
    - Note: Limited Language, Security/0
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=10,
            cost=4000,
            intelligence=4) 
        
class HunterKillerBrain(Brain):
    """
    - Trait: Computer/1
    - Trait: Skill Count -1    
    - Skill: Recon 0
    - Trait: Inherent Bandwidth 1
    - Note: Limited Fried or Foe, Security/1    
    """
    # TODO: Handle incompatible with additional skills if that is how it
    # actually works. It seems odd that it would have a skill count (even
    # if it is a negative one, if it isn't compatible with additional skills)
    # TODO: Handle Recon skill
      
    def __init__(
            self,
            minTL: int,
            cost: int,
            intelligence: int
            ) -> None:
        super().__init__(
            componentString=f'Hunter/Killer TL {minTL}',
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=1,
            skillCount=-1,
            notes=['Limited Fried or Foe, Security/1']) # TODO: This is a crap note
                
class HunterKillerTL8Brain(HunterKillerBrain):
    """
    - Min TL: 8
    - Cost: Cr30000
    - Trait: INT 3
    - Trait: Computer/1
    - Trait: Skill Count -1    
    - Skill: Recon 0
    - Trait: Inherent Bandwidth 1
    - Note: Limited Fried or Foe, Security/1
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=8,
            cost=30000,
            intelligence=3)
        
class HunterKillerTL10Brain(HunterKillerBrain):
    """
    - Min TL: 10
    - Cost: Cr6000
    - Trait: INT 4
    - Trait: Computer/1
    - Trait: Skill Count -1    
    - Skill: Recon 0
    - Trait: Inherent Bandwidth 1
    - Note: Limited Fried or Foe, Security/1
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=10,
            cost=6000,
            intelligence=4)
        
class SkilledBrain(Brain):
    """
    - Skill Count: The robot can have an additional number of zero-level skills
    equal to the Computer/X inherent Bandwidth of the brain
    """
    # TODO: Handle additional skills

    def __init__(
            self,
            componentString: str,
            minTL: typing.Union[int, common.ScalarCalculation],
            cost: typing.Union[int, common.ScalarCalculation],
            intelligence: typing.Union[int, common.ScalarCalculation],
            inherentBandwidth: typing.Union[int, common.ScalarCalculation],
            skillCount: typing.Union[int, common.ScalarCalculation],
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=inherentBandwidth,
            skillCount=skillCount,
            notes=notes)     
        
class AdvancedBrain(SkilledBrain):
    """
    - Trait: Computer/2
    - Trait: Skill Count 0  
    - Trait: Inherent Bandwidth 2
    - Note: Intelligent Interface, Expert/1, Security/1
    - Note: Advanced brains can only attempt tasks up to Difficult (10+)
    """
    # TODO: Handle additional zero level skills
      
    def __init__(
            self,
            minTL: int,
            cost: int,
            intelligence: int
            ) -> None:
        super().__init__(
            componentString=f'Advanced TL {minTL}',
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=2,
            skillCount=0,
            notes=['Limited Fried or Foe, Security/1', # TODO: This is a crap note
                   'Can only attempt tasks up to Difficult (10+)'])
                
class AdvancedTL10Brain(AdvancedBrain):
    """
    - Min TL: 10
    - Cost: Cr100000
    - Trait: INT 6
    - Trait: Computer/2
    - Trait: Skill Count 0  
    - Trait: Inherent Bandwidth 2
    - Note: Intelligent Interface, Expert/1, Security/1
    - Note: Advanced brains can only attempt tasks up to Difficult (10+)  
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=10,
            cost=100000,
            intelligence=6)
        
class AdvancedTL11Brain(AdvancedBrain):
    """
    - Min TL: 11
    - Cost: Cr50000
    - Trait: INT 7
    - Trait: Computer/2
    - Trait: Skill Count 0  
    - Trait: Inherent Bandwidth 2
    - Note: Intelligent Interface, Expert/1, Security/1
    - Note: Advanced brains can only attempt tasks up to Difficult (10+) 
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=11,
            cost=50000,
            intelligence=7) 
        
class AdvancedTL12Brain(AdvancedBrain):
    """
    - Min TL: 12
    - Cost: Cr10000
    - Trait: INT 8
    - Trait: Computer/2
    - Trait: Skill Count 0  
    - Trait: Inherent Bandwidth 2
    - Note: Intelligent Interface, Expert/1, Security/1
    - Note: Advanced brains can only attempt tasks up to Difficult (10+)
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=12,
            cost=10000,
            intelligence=8) 

class VeryAdvancedBrain(SkilledBrain):
    """
    - Trait: Skill Count +1 
    - Note: Intellect Interface, Expert/2, Security/2
    - Note: Advanced brains can only attempt tasks up to Very Difficult (12+)
    """
    # TODO: Handle additional zero level skills
      
    def __init__(
            self,
            minTL: int,
            cost: int,
            intelligence: int,
            inherentBandwidth: int
            ) -> None:
        super().__init__(
            componentString=f'Very Advanced TL {minTL}',
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=inherentBandwidth,
            skillCount=+1,
            notes=['Intellect Interface, Expert/2, Security/2', # TODO: This is a crap note
                   'Can only attempt tasks up to Very Difficult (12+)'])
                
class VeryAdvancedTL12Brain(VeryAdvancedBrain):
    """
    - Min TL: 12
    - Cost: Cr500000
    - Trait: INT 9
    - Trait: Computer/3
    - Trait: Skill Count +1 
    - Trait: Inherent Bandwidth 3
    - Note: Intellect Interface, Expert/2, Security/2
    - Note: Advanced brains can only attempt tasks up to Very Difficult (12+)
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=12,
            cost=500000,
            intelligence=9,
            inherentBandwidth=3)
        
class VeryAdvancedTL13Brain(VeryAdvancedBrain):
    """
    - Min TL: 13
    - Cost: Cr500000
    - Trait: INT 10
    - Trait: Computer/4
    - Trait: Skill Count +1 
    - Trait: Inherent Bandwidth 4
    - Note: Intellect Interface, Expert/2, Security/2
    - Note: Advanced brains can only attempt tasks up to Very Difficult (12+) 
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=13,
            cost=500000,
            intelligence=10,
            inherentBandwidth=4)
        
class VeryAdvancedTL14Brain(VeryAdvancedBrain):
    """
    - Min TL: 14
    - Cost: Cr500000
    - Trait: INT 11
    - Trait: Computer/5
    - Trait: Skill Count +1 
    - Trait: Inherent Bandwidth 5
    - Note: Intellect Interface, Expert/2, Security/2
    - Note: Advanced brains can only attempt tasks up to Very Difficult (12+)
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=14,
            cost=500000,
            intelligence=11,
            inherentBandwidth=5)

class SelfAwareBrain(SkilledBrain):
    """
    - Trait: Skill Count +2
    - Note: Near sentient, Expert/3, Security/3
    - Note: Advanced brains can only attempt tasks up to Formidable (14+)
    """
    # TODO: Handle additional zero level skills
      
    def __init__(
            self,
            minTL: int,
            cost: int,
            intelligence: int,
            inherentBandwidth: int
            ) -> None:
        super().__init__(
            componentString=f'Self-Aware TL {minTL}',
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=inherentBandwidth,
            skillCount=+2,
            notes=['Near sentient, Expert/3, Security/3', # TODO: This is a crap note
                   'Can only attempt tasks up to Formidable (14+)'])
                
class SelfAwareTL15Brain(SelfAwareBrain):
    """
    - Min TL: 15
    - Cost: Cr1000000
    - Trait: INT 12
    - Trait: Computer/10
    - Trait: Skill Count +2
    - Trait: Inherent Bandwidth 10
    - Note: Near sentient, Expert/3, Security/3
    - Note: Advanced brains can only attempt tasks up to Formidable (14+)
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=15,
            cost=1000000,
            intelligence=12,
            inherentBandwidth=10)
        
class SelfAwareTL16Brain(SelfAwareBrain):
    """
    - Min TL: 16
    - Cost: Cr1000000
    - Trait: INT 13
    - Trait: Computer/15
    - Trait: Skill Count +2
    - Trait: Inherent Bandwidth 15
    - Note: Near sentient, Expert/3, Security/3
    - Note: Advanced brains can only attempt tasks up to Formidable (14+)
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=16,
            cost=1000000,
            intelligence=13,
            inherentBandwidth=15)

class ConsciousBrain(SkilledBrain):
    """
    - Trait: Skill Count +3
    - Note: Conscious Intelligence, Security/3   
    """
    # TODO: Handle additional zero level skills
      
    def __init__(
            self,
            minTL: int,
            cost: int,
            intelligence: int,
            inherentBandwidth: int
            ) -> None:
        super().__init__(
            componentString=f'Conscious TL {minTL}',
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=inherentBandwidth,
            skillCount=+3,
            notes=['Conscious Intelligence, Security/3']) # TODO: This is a crap note
                
class ConsciousTL17Brain(ConsciousBrain):
    """
    - Min TL: 17
    - Cost: Cr5000000
    - Trait: INT 15
    - Trait: Computer/20
    - Trait: Skill Count +3
    - Trait: Inherent Bandwidth 20
    - Note: Conscious Intelligence, Security/3
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=17,
            cost=5000000,
            intelligence=15,
            inherentBandwidth=20)
        
class ConsciousTL18Brain(ConsciousBrain):
    """
    - Min TL: 18
    - Cost: Cr1000000
    - Trait: INT 15
    - Trait: Computer/30
    - Trait: Skill Count +3
    - Trait: Inherent Bandwidth 30
    - Note: Conscious Intelligence, Security/3
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=18,
            cost=1000000,
            intelligence=15,
            inherentBandwidth=30)