import common
import construction
import robots
import typing

class EnduranceModification(robots.EnduranceModificationInterface):
    def typeString(self) -> str:
        return 'Endurance Modification'
    
    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        return context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence)  

class IncreaseEndurance(EnduranceModification):
    """
    Improved Components (p19)
    - Endurance: +100%
    - Cost: 50% of Base Chassis Cost
    Additional Power Packs (p19)
    - Endurance: +100% per power pack
    - Slots: 10% of Base Slots (rounded up)
    - Cost: Cr500 per slot
    - Skill: Athletics (Power Pack Count)
    - Option: Number of power packs (max 3)    
    """
    # NOTE: The free Endurance increases at TL12/15 are handled by Locomotion
    # NOTE: Order is important, the rules say Improved Components is applied
    # first and then Power Packs
    # TODO: Handle Athletics skill from Power Packs (but not Improved
    # Components)

    _ImprovedComponentsIncreasePercent = common.ScalarCalculation(
        value=100,
        name='Improved Components Endurance Increase Percentage')
    _ImprovedComponentsCostPercent = common.ScalarCalculation(
        value=50,
        name='Improved Components Cost Percentage')
    _ImprovedComponentMinTechLevel = 7

    _PowerPackIncreasePercent = common.ScalarCalculation(
        value=100,
        name='Power Pack Endurance Increase Percentage')
    _PowerPackSlotsPercent = common.ScalarCalculation(
        value=10,
        name='Power Pack Required Slot Percentage')
    _PowerPackPerSlotCost = common.ScalarCalculation(
        value=500,
        name='Power Pack Per Slot Cost'
    )
    _PowerPackMinTechLevel = 8 


    def __init__(self) -> None:
        super().__init__()
        
        self._improvedComponentsOption = construction.BooleanOption(
            id='ImprovedComponents',
            name='Improved Components',
            value=False,
            description='Specify if improved components are used to improve efficiency.')
        
        self._powerPacksOption = construction.IntegerOption(
            id='PowerPacks',
            name='Power Packs',
            value=0,
            minValue=0,
            maxValue=3,
            description='Specify the number of additional power packs.')        

    def componentString(self) -> str:
        return 'Endurance Increase'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return context.techLevel() >= IncreaseEndurance._ImprovedComponentMinTechLevel or \
            context.techLevel() >= IncreaseEndurance._PowerPackMinTechLevel  
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = []
        if self._improvedComponentsOption.isEnabled():
            options.append(self._improvedComponentsOption)
        if self._powerPacksOption.isEnabled():
            options.append(self._powerPacksOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        self._improvedComponentsOption.setEnabled(
            enabled=context.techLevel() >= IncreaseEndurance._ImprovedComponentMinTechLevel)
        self._powerPacksOption.setEnabled(
            enabled=context.techLevel() >= IncreaseEndurance._PowerPackMinTechLevel)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        if self._improvedComponentsOption.value():
            self.createImprovedComponentsStep(
                sequence=sequence,
                context=context)
            
        if self._powerPacksOption.value() > 0:
            self.createPowerPackStep(
                sequence=sequence,
                context=context)                
        
    def createImprovedComponentsStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = robots.RobotStep(
            name='Improved Components',
            type=self.typeString())
        
        baseChassisCost = context.baseChassisCredits(sequence=sequence)
        cost = common.Calculator.takePercentage(
            value=baseChassisCost,
            percentage=IncreaseEndurance._ImprovedComponentsCostPercent,
            name='Improved Components Endurance Increase Cost')
        step.setCredits(credits=construction.ConstantModifier(value=cost))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Endurance,
            modifier=construction.PercentageModifier(
                value=IncreaseEndurance._ImprovedComponentsIncreasePercent)))       
                        
        context.applyStep(
            sequence=sequence,
            step=step)

    def createPowerPackStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        packCount = common.ScalarCalculation(
            value=self._powerPacksOption.value(),
            name='Specified Power Pack Count')        

        step = robots.RobotStep(
            name=f'Power Packs x {packCount.value()}',
            type=self.typeString())
        
        baseSlots = context.baseSlots(sequence=sequence)
        perPackSlots = common.Calculator.ceil(
            value=common.Calculator.takePercentage(
                value=baseSlots,
                percentage=IncreaseEndurance._PowerPackSlotsPercent))
        totalSlots = common.Calculator.multiply(
            lhs=perPackSlots,
            rhs=packCount,
            name='Total Power Pack Slots Required')
        step.setSlots(slots=construction.ConstantModifier(value=totalSlots))        

        totalCost = common.Calculator.multiply(
            lhs=IncreaseEndurance._PowerPackPerSlotCost,
            rhs=totalSlots,
            name='Total Power Pack Cost')
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))

        totalIncreasePercent = common.Calculator.multiply(
            lhs=IncreaseEndurance._PowerPackIncreasePercent,
            rhs=packCount,
            name='Total Power Pack Endurance Increase Percent')
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Endurance,
            modifier=construction.PercentageModifier(
                value=totalIncreasePercent)))       
                        
        context.applyStep(
            sequence=sequence,
            step=step)