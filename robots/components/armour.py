import common
import construction
import robots
import typing

class ArmourModification(robots.ArmourModificationInterface):
    def typeString(self) -> str:
        return 'Armour Modification'
    
    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        return context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence)

class IncreaseArmour(ArmourModification):
    """
    - <ALL>
        - Requirement: Androids and BioRobots can only have up to 2 slots of
          armour (p86) 
    - TL6-8
        - Max Addition Armour: 20
        - Slot Cost: 1% of Base Slots rounded up for each additional point of
          armour (minimum of 1 slot)
        - Max Per Slot: 1
        - Cost Per Slot: Cr250
    - TL9-11
        - Max Addition Armour: 30
        - Slot Cost: 0.5% of Base Slots rounded up for each additional point
          of armour (minimum of 1 slot)
        - Max Per Slot: 2
        - Cost Per Slot: Cr1000
    - TL12-14
        - Max Addition Armour: 40
        - Slot Cost: 0.4% of Base Slots rounded up for each additional point
          of armour (minimum of 1 slot)
        - Max Per Slot: 3
        - Cost Per Slot: Cr1500
    - TL15-17
        - Max Addition Armour: 50
        - Slot Cost: 0.3% of Base Slots rounded up for each additional point
          of armour (minimum of 1 slot)
        - Max Per Slot: 4
        - Cost Per Slot: Cr2500   
    - TL18+
        - Max Addition Armour: 60
        - Slot Cost: 0.25% of Base Slots rounded up for each additional point
          of armour (minimum of 1 slot)
        - Max Per Slot: 5
        - Cost Per Slot: Cr5000    
    """
    # NOTE: Base Protection is handled by the Chassis component
    # NOTE: On p19 the rules say "Each point of additional armour, up to the
    # listed maximum, may be obtained for the specified percentage of the
    # robot’s Base Chassis Cost and the allocation of a percentage of Slots
    # as indicated.". This doesn't seem to match up with the table on the
    # same page as it has each armour point costing a percentage of the base
    # slots (which matches the wording) but a fixed credits cost per slot
    # (which doesn't match the wording)
    # NOTE: Although this is an armour component it deals with the the
    # Protection value rather than the Armour trait. See the relevant
    # attributes for more details

    # Data Structure: Min TL, Max TL, Max Addition Armour, Slot Cost Percentage, Max Armour Per Slot, Cost Per Slot
    _ArmourTypeDetails = [
        (6, 8, 20, 1, 1, 250),
        (9, 11, 30, 0.5, 2, 1000),
        (12, 14, 40, 0.4, 3, 1500),
        (15, 17, 50, 0.3, 4, 2500),
        (18, None, 60, 0.25, 5, 5000)
    ]
    _MinTechLevel = 6
    _SyntheticMaxSlots = common.ScalarCalculation(
        value=2,
        name='Android/BioRobot Max Armours Slots')
    
    def __init__(self) -> None:
        super().__init__()
        
        self._armourPointsOption = construction.IntegerOption(
            id='ArmourPoints',
            name='Armour Points',
            value=1,
            minValue=1,
            description='Specify the number of points of armour you want to add.')

    def componentString(self) -> str:
        return 'Armour Increase'
    
    def instanceString(self) -> str:
        return '{component} +{points}'.format(
            component=self.componentString(),
            points=self._armourPointsOption.value()) 

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        
        if context.techLevel() < IncreaseArmour._MinTechLevel:
            return False
        
        maxArmour = self._calculateMaxArmour(
            sequence=sequence,
            context=context)
        return maxArmour and maxArmour.value() >= 1
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._armourPointsOption]

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        maxArmour = self._calculateMaxArmour(
            sequence=sequence,
            context=context)
        if maxArmour and maxArmour.value() <= 1:
            maxArmour = None
        
        self._armourPointsOption.setMin(value=1 if maxArmour != None else 0)
        self._armourPointsOption.setMax(value=maxArmour.value() if maxArmour != None else 0)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        currentTL = context.techLevel()
        foundDetails = False
        for minTL, maxTL, _, slotPercent, maxPerSlot, costPerSlot in IncreaseArmour._ArmourTypeDetails:
            if currentTL >= minTL and ((maxTL == None) or (currentTL <= maxTL)):
                foundDetails = True
                break
        assert(foundDetails)
        tlRangeString = f'TL{minTL}-{maxTL}' if maxTL != None else f'TL{minTL}+'

        baseSlots = context.baseSlots(sequence=sequence)
        assert(isinstance(baseSlots, common.ScalarCalculation))
        slotPercent = common.ScalarCalculation(
            value=slotPercent,
            name=f'{tlRangeString} Armour Base Slot Percentage Per Point')
        maxPerSlot = common.ScalarCalculation(
            value=maxPerSlot,
            name=f'{tlRangeString} Armour Max Points Per Slot')
        costPerSlot = common.ScalarCalculation(
            value=costPerSlot,
            name=f'{tlRangeString} Armour Cost Per Slot')
        armourPoints = common.ScalarCalculation(
            value=self._armourPointsOption.value(),
            name='Specified Armour Increase')

        totalSlotPercent = common.Calculator.multiply(
            lhs=slotPercent,
            rhs=armourPoints,
            name=f'{tlRangeString} Armour Base Slot Percentage For {armourPoints.value()} Points')
        requiredSlots = common.Calculator.ceil(
            value=common.Calculator.takePercentage(
                value=baseSlots,
                percentage=totalSlotPercent),
            name=f'{tlRangeString} Armour Slot Required For {armourPoints.value()} Points')
        
        minSlots = common.Calculator.ceil(
            value=common.Calculator.divideFloat(
                lhs=armourPoints,
                rhs=maxPerSlot),
            name=f'{tlRangeString} Armour Min Slots For {armourPoints.value()} Points')
        if requiredSlots.value() < minSlots.value():
            requiredSlots = common.Calculator.equals(
                value=minSlots,
                name=requiredSlots.name())

        totalCost = common.Calculator.multiply(
            lhs=costPerSlot,
            rhs=requiredSlots,
            name=f'{tlRangeString} Armour Cost For {requiredSlots.value()} Slots')
        
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))
        step.setSlots(slots=construction.ConstantModifier(value=requiredSlots))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Protection,
            modifier=construction.ConstantModifier(value=armourPoints)))        
                        
        context.applyStep(
            sequence=sequence,
            step=step)
        
    def _calculateMaxArmour(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[common.ScalarCalculation]:
        currentTL = context.techLevel()
        foundDetails = False
        for minTL, maxTL, maxArmour, slotPercentage, maxPerSlot, _ in IncreaseArmour._ArmourTypeDetails:
            if currentTL >= minTL and ((maxTL == None) or (currentTL <= maxTL)):
                foundDetails = True
                break
        if not foundDetails:
            return None
        
        tlRangeString = f'TL{minTL}-{maxTL}' if maxTL != None else f'TL{minTL}+'

        maxArmour = common.ScalarCalculation(
            value=maxArmour,
            name=f'{tlRangeString} Max Armour')

        if not context.hasComponent(
            componentType=robots.Synthetic,
            sequence=sequence):
            return maxArmour
        
        slotPercentage = common.ScalarCalculation(
            value=slotPercentage,
            name=f'{tlRangeString} Armour Base Slot Percentage Per Point')
        maxPerSlot = common.ScalarCalculation(
            value=maxPerSlot,
            name=f'{tlRangeString} Armour Max Points Per Slot')
            
        baseSlots = context.baseSlots(sequence=sequence)
        maxSlotPercentage = common.Calculator.multiply(
            lhs=common.Calculator.divideFloat(
                lhs=common.ScalarCalculation(value=100),
                rhs=baseSlots),
            rhs=IncreaseArmour._SyntheticMaxSlots,
            name='Android/BioRobot Max Slot Percentage')
        maxArmourByPercentage = common.Calculator.floor(
            value=common.Calculator.divideFloat(
                lhs=maxSlotPercentage,
                rhs=slotPercentage),
            name='Android/BioRobot Slot Percentage Limited Max Armour')
        
        maxArmourBySlotMax = common.Calculator.multiply(
            lhs=maxPerSlot,
            rhs=IncreaseArmour._SyntheticMaxSlots,
            name='Android/BioRobot Max Per Slot Limited Max Armour')
        
        maxArmour = common.Calculator.min(
            lhs=common.Calculator.min(
                lhs=maxArmourByPercentage,
                rhs=maxArmourBySlotMax),
            rhs=maxArmour,
            name=f'Android/BioRobot {tlRangeString} Max Armour')

        return maxArmour
            
class DecreaseArmour(ArmourModification):
    """
    - Cost: -10% of Base Chassis Cost per point removed
    - Requirement: Removing armour prevents the addition of environmental
    protection (p19)
    - Requirement: Not available on robots with no base armour (p19)
    """
    # NOTE: Although this is an armour component it deals with the the
    # Protection value rather than the Armour trait. See the relevant
    # attributes for more details
    # NOTE: The requirement that removing armour prevents adding environmental
    # protection is handled by the environmental protection components as
    # they're added later

    _CostReductionPercent = common.ScalarCalculation(
        value=-10,
        name='Armour Decrease Per Slot Cost Saving Percentage')

    def __init__(self) -> None:
        super().__init__()
        
        self._armourPointsOption = construction.IntegerOption(
            id='ArmourPoints',
            name='Armour Points',
            value=1,
            minValue=1,
            description='Specify the number of points of armour you want to remove.')

    def componentString(self) -> str:
        return 'Armour Decrease'
    
    def instanceString(self) -> str:
        return '{component} -{points}'.format(
            component=self.componentString(),
            points=self._armourPointsOption.value()) 

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with robots with no base armour
        protection = context.attributeValue(
            attributeId=robots.RobotAttributeId.Protection,
            sequence=sequence)
        if not protection:
            return False
        return protection.value() > 0

    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._armourPointsOption]

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        protection = context.attributeValue(
            attributeId=robots.RobotAttributeId.Protection,
            sequence=sequence)
        if isinstance(protection, common.ScalarCalculation):
            self._armourPointsOption.setMin(1)
            self._armourPointsOption.setMax(protection.value())
        else:
            self._armourPointsOption.setMin(0)
            self._armourPointsOption.setMax(0)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        armourPoints = common.ScalarCalculation(
            value=-self._armourPointsOption.value(), # NOTE: This is negated
            name='Specified Armour Reduction')
        baseChassisCost = context.baseChassisCredits(sequence=sequence)

        totalCost = common.Calculator.takePercentage(
            value=baseChassisCost,
            percentage=common.Calculator.multiply(
                lhs=DecreaseArmour._CostReductionPercent,
                rhs=common.Calculator.absolute(armourPoints)),
            name=f'Armour Decrease Cost Saving For {armourPoints.value()} Points')
        
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Protection,
            modifier=construction.ConstantModifier(value=armourPoints)))
                        
        context.applyStep(
            sequence=sequence,
            step=step)