import common
import construction
import robots
import typing

# TODO: It would be nice to have a component that allows
# you to specify the final number of hits. Could possibly
# have it as a single component that allows you to specify
# either the desired final number of hits or the number
# to increase/decrease the number of hits by
class ResiliencyModification(robots.RobotComponentInterface):
    def typeString(self) -> str:
        return 'Resiliency Modification'
    
    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        return context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence)

class IncreaseResiliency(ResiliencyModification):
    """
    - Hits: +1 per slot allocated (p20)
    - Cost: 5% of Base Chassis Cost per slot allocated (p20)
    - Requirement: Max 50% of Base Slots can be allocated (p20)
    - Requirement: Not compatible with robots that only have one slot
    """
    # NOTE: The facts that at most 50% of the robot's slots can be allocated to
    # resiliency _and_ we deal in whole slots imply that robots with only one
    # slot can't have a resiliency increase (as that would require 100% of
    # their slots)
    # NOTE: The rules on p20 just say at most 50% of the robot's Slots can be
    # used. I've made the assumption that it means Base Slots as that's what
    # everything generally seems to be based on

    _PerSlotCostPercent = common.ScalarCalculation(
        value=5,
        name='Resiliency Increase Cost Percentage Per Slot')
    _MaxIncreaseSlotPercent = 50

    def __init__(self) -> None:
        super().__init__()
        
        self._hitsIncreaseOption = construction.IntegerOption(
            id='HitsIncrease',
            name='Hits Increase',
            value=1,
            minValue=1,
            description='Specify the increase in the robot\'s hits.')

    def componentString(self) -> str:
        return 'Resiliency Increase'
    
    def instanceString(self) -> str:
        return '{component} +{increase} Hits'.format(
            component=self.componentString(),
            increase=self._hitsIncreaseOption.value()) 
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with robots that only have one slot
        baseSlots = context.baseSlots(sequence=sequence)
        return baseSlots.value() > 1
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._hitsIncreaseOption]

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        baseSlots = context.baseSlots(sequence=sequence)
        maxIncrease = int(baseSlots.value() *
            (IncreaseResiliency._MaxIncreaseSlotPercent / 100))
        self._hitsIncreaseOption.setMax(
            value=maxIncrease)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        hitsIncrease = common.ScalarCalculation(
            value=self._hitsIncreaseOption.value(),
            name='Specified Hits Increase')
        
        totalCostPercent = common.Calculator.multiply(
            lhs=IncreaseResiliency._PerSlotCostPercent,
            rhs=hitsIncrease,
            name='Total Resiliency Increase Cost Percentage')
        totalCost = common.Calculator.takePercentage(
            value=context.baseChassisCredits(sequence=sequence),
            percentage=totalCostPercent,
            name='Total Resiliency Increase Cost')
        
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))
        step.setSlots(slots=construction.ConstantModifier(value=hitsIncrease))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Hits,
            modifier=construction.ConstantModifier(value=hitsIncrease)))        
                        
        context.applyStep(
            sequence=sequence,
            step=step)

class DecreaseResiliency(ResiliencyModification):
    """
    - Cost Saving: Cr50 * Locomotion Multiplier for each Hit reduced
    - Requirement: Only 50% of the robot's Base Hits can be removed  
    - Requirement: Not compatible with robots that only have one hit  
    """
    # NOTE: The facts that at most 50% of the robot's hits can be reduced
    # _and_ we deal in whole hits imply that robots with only one hit
    # can't have a resiliency decrease (as that would require 100% of
    # their hits)

    _BasePerHitSaving = common.ScalarCalculation(
        value=50,
        name='Resiliency Decrease Base Per Hit Saving')
    _MaxDecreaseHitPercent = 50

    def __init__(self) -> None:
        super().__init__()
        
        self._hitsDecreaseOption = construction.IntegerOption(
            id='HitsDecrease',
            name='Hits Decrease',
            value=1,
            minValue=1,
            description='Specify the decrease in the robot\'s hits.')

    def componentString(self) -> str:
        return 'Resiliency Decrease'
    
    def instanceString(self) -> str:
        return '{component} -{increase} Hits'.format(
            component=self.componentString(),
            increase=self._hitsDecreaseOption.value()) 
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
                
        # Not compatible with robots that only have one hit
        hits = context.attributeValue(
            attributeId=robots.RobotAttributeId.Hits,
            sequence=sequence)
        if not hits:
            return False
        return hits.value() > 1
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._hitsDecreaseOption]

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        hits = context.attributeValue(
            attributeId=robots.RobotAttributeId.Hits,
            sequence=sequence)
        maxDecrease = int(hits.value() *
            (DecreaseResiliency._MaxDecreaseHitPercent / 100))
        self._hitsDecreaseOption.setMax(
            value=maxDecrease)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        hitsDecrease = common.ScalarCalculation(
            value=-self._hitsDecreaseOption.value(), # NOTE: negated
            name='Specified Hits Decrease')
        
        perHitSaving = DecreaseResiliency._BasePerHitSaving
        locomotion = context.findFirstComponent(
            componentType=robots.PrimaryLocomotion,
            sequence=sequence)
        if isinstance(locomotion, robots.PrimaryLocomotion):
            perHitSaving = common.Calculator.multiply(
                lhs=perHitSaving,
                rhs=locomotion.costMultiplier(),
                name='Resiliency Decrease Saving Per Hit Decrease')
        
        totalCostSaving = common.Calculator.multiply(
            lhs=perHitSaving,
            rhs=common.Calculator.absolute(value=hitsDecrease),
            name='Total Resiliency Decrease Cost Saving')
        
        totalCostDecrease = common.Calculator.negate(
            value=totalCostSaving,
            name='Total Resiliency Decrease Cost')
        
        step.setCredits(credits=construction.ConstantModifier(
            value=totalCostDecrease))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Hits,
            modifier=construction.ConstantModifier(value=hitsDecrease)))        
                        
        context.applyStep(
            sequence=sequence,
            step=step)