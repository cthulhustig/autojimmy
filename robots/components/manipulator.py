import common
import construction
import enum
import robots
import typing

class _ManipulatorImpl(object):
    """
    <ALL>
    - Base Str: (2 x Size) - 1
    - Base Dex: (TL / 2) + 1 rounded up
    Base Manipulators x 2
    - Default Size: Robot Size
    - Resizing:
        - Slots:
            - Chassis Size - 3+: 1% of Base Slots rounded up
            - Chassis Size - 2: 2% of Base Slots rounded up
            - Chassis Size - 1: 5% of Base Slots rounded up
            - Chassis Size: 10% of Base Slots rounded up
            - Chassis Size + 1: 20% of Base Slots rounded up
            - Chassis Size + 2: 40% of Base Slots rounded up        
        - Cost: Cr100 * the difference in slots between the robot size and the
        new manipulator size. The reduction in cost is clamped to 20% of the
        Base Chassis Cost
        - Requirement: If the manipulator is smaller than the robot size it
        gains at least one slot to use, if the manipulator is larger than the
        robot size it requires at least one slot to install (p25)
    - Removal:
        - Slot Gain: +10% of Base Slots per Base Manipulator Removed rounded up
        - Cost Saving: Cr100 * Manipulator Size limited to 20% of Base Chassis Cost
    Additional Manipulators
        - Cost: Cr100 * Manipulator Size
        - Slots: This is the same as for Base Manipulator
    Altered Characteristics
        - Strength Increase
            - Cost: Base Manipulator Cost * Increase In STR _Squared_
            - Requirements: Can only increase STR up to 2 times the default STR
        - Dexterity Increase
            - Cost: (2 * Base Manipulator Cost) * Increase In DEX _Squared_
            - Requirement: Can only increase DEX up to TL+3
    Walker Leg Manipulators
        - Cost: Cr100 * Size per leg
        - Requirement: Only compatible with Walker locomotion type
        - Requirement: The rules say walker legs can't have their size modified
        (p26)
    """
    # NOTE: I've added logic to cache the robot TL & size so the option handling
    # code can detect when they've changed. This is done so that the option
    # values can be reset to the default value. This is desirable as it means,
    # when the TL/size are changed, the user doesn't have to reset the options
    # to get them back to the base value. This could be avoided by using enums
    # for the conceptual options (e.g. 'Size -1', 'STR +2') rather than
    # specifying the value. However I think specifying the absolute values is
    # nicer from the users point of view
    # NOTE: Logic to only allow leg manipulators on walkers and limit the number
    # to the number of legs is part of the leg component rather than the this
    # impl as it requires knowledge of the leg component type.
    # NOTE: It's not clear if STR/DEX can be increased for manipulators attached
    # to walker legs. The rules state they can't have their size increased (p26)
    # but don't mention STR/DEX. I've not disabled the controls, so it's left
    # up to the user
    # TODO: The manipulator rules have this regarding the athletics skill (p26)
    #
    # Increased DEX and STR values do not directly grant a skill equivalence of
    # Athletics (dexterity) or Athletics (strength) to the robot unless it has a
    # skill package of Athletics installed in its brain. If such a package is
    # installed, even at skill level zero, then DMs for high STR or DEX are
    # applied to simulate that skill level, although in situations where
    # different manipulators have different DMs, the Referee should determine
    # whether a DM applies. Note that a robot with DEX 15 manipulators and
    # Athletics 0 would be considered to have Athletics (dexterity) 3 for
    # skill recording purposes but would not receive an additional DM+3 to that
    # skill while attempting checks using Athletics (dexterity).
    #
    # I suspect this would need handled as some notes that give the athletics
    # skills for different manipulators and states that you don't get an
    # additional DM+X on top of the DEX modifier when making Athletics checks.
    # It could also check if manipulators have different DMs to add a note about
    # it being at the referees discretion if they apply.
    # Ideally we don't want these notes added if the the robot skill is added as
    # it talks about. I don't think it would be possible to do this check here
    # as, to account for packages that give the skill, it would require checking
    # for the skill rather than existence of a component and the skill won't have
    # been added yet as skills come later in construction.
    # I could add the notes when the skill is being added but that would mean I'd
    # need to do the same thing in all the places that add the Athletics skill.
    # I would probably be better to add it to finalisation.
    class ManipulatorType(enum.Enum):
        Base = 'Base Manipulator'
        Additional = 'Additional Manipulator'
        Leg = 'Leg Manipulator'

    _MaxSizeIncrease = common.ScalarCalculation(
        value=2,
        name='Max Manipulator Size Increase')
    
    _SizeModificationCostIncrement = common.ScalarCalculation(
        value=100,
        name='Manipulator Size Modification Cost Per Increment')
    _SizeModificationCostReductionLimitPercent = common.ScalarCalculation(
        value=20,
        name='Manipulator Size Modification Cost Reduction Limit Percentage')        
    
    _SizeModificationSlotCostMap = {
        +2: common.ScalarCalculation(
            value=40,
            name='Size +2 Manipulator Slot Requirement Percentage'),
        +1: common.ScalarCalculation(
            value=20,
            name='Size +1 Manipulator Slot Requirement Percentage'),
        0: common.ScalarCalculation(
            value=10,
            name='Base Size Manipulator Slot Requirement Percentage'),
        -1: common.ScalarCalculation(
            value=5,
            name='Size -1 Manipulator Slot Requirement Percentage'),
        -2: common.ScalarCalculation(
            value=2,
            name='Size -2 Manipulator Slot Requirement Percentage'),
        -3: common.ScalarCalculation(
            value=1,
            name='Size -3 Manipulator Slot Requirement Percentage'),
        # The rules say -3 (or less) cost 1% of base slots. I've added explicit
        # values for all the possible reductions (size 8 robot with size 1
        # manipulator) as it's a little clearer
        -4: common.ScalarCalculation(
            value=1,
            name='Size -4 Manipulator Slot Requirement Percentage'),
        -5: common.ScalarCalculation(
            value=1,
            name='Size -5 Manipulator Slot Requirement Percentage'),
        -6: common.ScalarCalculation(
            value=1,
            name='Size -6 Manipulator Slot Requirement Percentage'),
        -7: common.ScalarCalculation(
            value=1,
            name='Size -7 Manipulator Slot Requirement Percentage') 
    }

    _MaxStrengthIncreaseMultiplier = common.ScalarCalculation(
        value=2,
        name='Max Manipulator STR Increase Multiplier')
    
    _MaxDexterityTechLevelModifier = common.ScalarCalculation(
        value=3,
        name='Max Manipulator DEX Increase TL Modifier')
    _DexterityModifierCostMultiplier = common.ScalarCalculation(
        value=2,
        name='Manipulator DEX Modification Cost Multiplier')    
    
    _BaseStrengthSizeMultiplier = common.ScalarCalculation(
        value=2,
        name='Manipulator Base STR Size Multiplier')
    _BaseStrengthConstant = common.ScalarCalculation(
        value=-1,
        name='Manipulator Base STR Constant')
    
    _BaseDexterityTechLevelDivisor = common.ScalarCalculation(
        value=2,
        name='Manipulator Base DEX TL Divisor')
    _BaseDexterityConstant = common.ScalarCalculation(
        value=+1,
        name='Manipulator Base DEX Constant')

    def __init__(
            self,
            manipulatorType: ManipulatorType
            ) -> None:
        super().__init__()

        self._manipulatorType = manipulatorType
        self._cachedTechLevel = None
        self._cachedRobotSize = None
        self._cachedManipulatorSize = None
        
        self._sizeOption = construction.IntegerOption(
            id='Size',
            name='Size',
            value=0,
            minValue=0,
            maxValue=0,
            description='Specify the the size of the manipulator.')
        
        self._strengthOption = construction.IntegerOption(
            id='Strength',
            name='STR',
            value=0,
            minValue=0,
            maxValue=0,
            description='Specify the the strength of the manipulator.')
        
        self._dexterityOption = construction.IntegerOption(
            id='Dexterity',
            name='DEX',
            value=0,
            minValue=0,
            maxValue=0,
            description='Specify the the dexterity of the manipulator.')

    def size(self) -> int:
        return self._sizeOption.value()

    def strength(self) -> int:
        return self._strengthOption.value()

    def dexterity(self) -> int:
        return self._dexterityOption.value()

    def instanceString(self) -> str:
        return 'Size {size} (STR: {strength}, DEX: {dexterity})'.format(
            size=self._sizeOption.value(),
            strength=self._strengthOption.value(),
            dexterity=self._dexterityOption.value())

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:       
        return context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = []

        # Size can't be changed for manipulators added to walker legs.
        # The option will default to the size of the robot
        if self._manipulatorType != _ManipulatorImpl.ManipulatorType.Leg:
            options.append(self._sizeOption)

        options.append(self._strengthOption)
        options.append(self._dexterityOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        robotSize = context.attributeValue(
            attributeId=robots.RobotAttributeId.Size,
            sequence=sequence)
        assert(isinstance(robotSize, common.ScalarCalculation))

        self._sizeOption.setMin(value=1)
        self._sizeOption.setMax(
            value=robotSize.value() +  _ManipulatorImpl._MaxSizeIncrease.value())
        if self._cachedRobotSize == None or \
                self._cachedRobotSize.value() != robotSize.value():
            self._sizeOption.setValue(robotSize.value())
            self._cachedRobotSize = robotSize

        baseStrength = self._calcBaseStrength(
            sequence=sequence,
            context=context)
        maxStrength = self._calcMaxStrength(
            sequence=sequence,
            context=context)
        self._strengthOption.setMin(value=baseStrength.value())
        self._strengthOption.setMax(value=maxStrength.value())
        if self._cachedManipulatorSize == None or \
                self._cachedManipulatorSize != self._sizeOption.value():
            self._strengthOption.setValue(value=baseStrength.value())
            self._cachedManipulatorSize = self._sizeOption.value()

        baseDexterity = self._calcBaseDexterity(
            sequence=sequence,
            context=context)
        maxDexterity = self._calcMaxDexterity(
            sequence=sequence,
            context=context)
        self._dexterityOption.setMin(value=baseDexterity.value())
        self._dexterityOption.setMax(value=maxDexterity.value())
        if self._cachedTechLevel == None or \
                self._cachedTechLevel != context.techLevel():
            self._dexterityOption.setValue(baseDexterity.value())
            self._cachedTechLevel = context.techLevel()

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        robotSize = context.attributeValue(
            attributeId=robots.RobotAttributeId.Size,
            sequence=sequence)
        assert(isinstance(robotSize, common.ScalarCalculation))
        manipulatorSize = common.ScalarCalculation(
            value=self._sizeOption.value(),
            name='Specified Manipulator Size')
        sizeDelta = common.Calculator.subtract(
            lhs=manipulatorSize,
            rhs=robotSize,
            name='Base Manipulator Size Delta')
        
        baseCost = common.Calculator.multiply(
            lhs=_ManipulatorImpl._SizeModificationCostIncrement,
            rhs=manipulatorSize,
            name='Manipulator Base Cost')        
        
        baseSlots = context.baseSlots(sequence=sequence)
        costList = []
        slots = None
        if self._manipulatorType == _ManipulatorImpl.ManipulatorType.Base:
            if sizeDelta.value() != 0:
                minCost = common.Calculator.negate(
                    value=common.Calculator.takePercentage(
                        value=context.baseChassisCredits(sequence=sequence),
                        percentage=_ManipulatorImpl._SizeModificationCostReductionLimitPercent),
                    name='Base Manipulator Size Modification Min Cost')
                costList.append(common.Calculator.max(
                    lhs=common.Calculator.multiply(
                        lhs=_ManipulatorImpl._SizeModificationCostIncrement,
                        rhs=sizeDelta),
                    rhs=minCost,
                    name='Base Manipulator Size Modification Cost'))

                originalSlots = common.Calculator.ceil(
                    value=common.Calculator.takePercentage(
                        value=baseSlots,
                        percentage=_ManipulatorImpl._SizeModificationSlotCostMap[0]),
                    name='Base Size Manipulator Slot Requirement')
                modifiedSlots = common.Calculator.ceil(
                    value=common.Calculator.takePercentage(
                        value=baseSlots,
                        percentage=_ManipulatorImpl._SizeModificationSlotCostMap[sizeDelta.value()]),
                    name='Size {modifier} Manipulator Slot Requirement'.format(
                        modifier=common.formatNumber(
                            number=sizeDelta.value(),
                            alwaysIncludeSign=True)))
                slots = common.Calculator.subtract(
                    lhs=modifiedSlots,
                    rhs=originalSlots,
                    name='Base Manipulator Size Modification Slot Requirement')
        elif self._manipulatorType == _ManipulatorImpl.ManipulatorType.Additional:
            costList.append(common.Calculator.equals(
                value=baseCost,
                name='Additional Manipulator Cost'))

            slots = common.Calculator.ceil(
                value=common.Calculator.takePercentage(
                    value=baseSlots,
                    percentage=_ManipulatorImpl._SizeModificationSlotCostMap[sizeDelta.value()]),
                name='Size {modifier} Manipulator Slot Requirement'.format(
                    modifier=common.formatNumber(
                        number=sizeDelta.value(),
                        alwaysIncludeSign=True)))
        elif self._manipulatorType == _ManipulatorImpl.ManipulatorType.Leg:
            costList.append(common.Calculator.equals(
                value=baseCost,
                name='Leg Manipulator Cost'))

        manipulatorStrength = common.ScalarCalculation(
            value=self._strengthOption.value(),
            name='Specified Manipulator STR')
        strengthIncrease = common.Calculator.subtract(
            lhs=manipulatorStrength,
            rhs=self._calcBaseStrength(sequence=sequence, context=context),
            name='Manipulator STR Increase')
        if strengthIncrease.value() > 0:
            costList.append(common.Calculator.multiply(
                lhs=baseCost,
                rhs=common.Calculator.multiply(
                    lhs=strengthIncrease,
                    rhs=strengthIncrease,
                    name='Manipulator STR Increase Squared')))
            
        manipulatorDexterity = common.ScalarCalculation(
            value=self._dexterityOption.value(),
            name='Specified Manipulator DEX')
        dexterityIncrease = common.Calculator.subtract(
            lhs=manipulatorDexterity,
            rhs=self._calcBaseDexterity(sequence=sequence, context=context),
            name='Manipulator DEX Increase')
        if dexterityIncrease.value() > 0:
            costList.append(common.Calculator.multiply(
                lhs=common.Calculator.multiply(
                    lhs=baseCost,
                    rhs=_ManipulatorImpl._DexterityModifierCostMultiplier),
                rhs=common.Calculator.multiply(
                    lhs=dexterityIncrease,
                    rhs=dexterityIncrease,
                    name='Manipulator DEX Increase Squared')))            

        if costList:
            cost = common.Calculator.sum(
                values=costList,
                name='Total Manipulator Cost')
            step.setCredits(credits=construction.ConstantModifier(value=cost))

        if slots:
            step.setSlots(slots=construction.ConstantModifier(value=slots))

    def _calcBaseStrength(
            self,
            sequence: str,
            context: robots.RobotContext            
            ) -> common.ScalarCalculation:
        size = common.ScalarCalculation(
            value=self._sizeOption.value(),
            name='Specified Manipulator Size')
        assert(isinstance(size, common.ScalarCalculation))
        return common.Calculator.add(
            lhs=common.Calculator.multiply(
                lhs=size,
                rhs=_ManipulatorImpl._BaseStrengthSizeMultiplier),
            rhs=_ManipulatorImpl._BaseStrengthConstant,
            name='Base STR')
    
    def _calcMaxStrength(
            self,
            sequence: str,
            context: robots.RobotContext            
            ) -> common.ScalarCalculation:
        return common.Calculator.multiply(
            lhs=self._calcBaseStrength(
                sequence=sequence,
                context=context),
            rhs=_ManipulatorImpl._MaxStrengthIncreaseMultiplier,
            name='Max STR')

    def _calcBaseDexterity(
            self,
            sequence: str,
            context: robots.RobotContext            
            ) -> common.ScalarCalculation:
        techLevel = common.ScalarCalculation(
            value=context.techLevel(),
            name='Robot TL')        
        return common.Calculator.ceil(
            value=common.Calculator.add(
                lhs=common.Calculator.divideFloat(
                    lhs=techLevel,
                    rhs=_ManipulatorImpl._BaseDexterityTechLevelDivisor),
                rhs=_ManipulatorImpl._BaseDexterityConstant),
            name='Base DEX')
    
    def _calcMaxDexterity(
            self,
            sequence: str,
            context: robots.RobotContext            
            ) -> common.ScalarCalculation:
        techLevel = common.ScalarCalculation(
            value=context.techLevel(),
            name='Robot TL')
        return common.Calculator.add(
            lhs=techLevel,
            rhs=_ManipulatorImpl._MaxDexterityTechLevelModifier,
            name='Max DEX')

class BaseManipulator(robots.BaseManipulatorInterface):
    def __init__(self) -> None:
        super().__init__()
        self._impl = _ManipulatorImpl(
            manipulatorType=_ManipulatorImpl.ManipulatorType.Base)
        
    def size(self) -> int:
        return self._impl.size()

    def strength(self) -> int:
        return self._impl.strength()

    def dexterity(self) -> int:
        return self._impl.dexterity()

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def componentString(self) -> str:
        return 'Base Manipulator'
    
    def typeString(self) -> str:
        return 'Base Manipulator'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return self._impl.isCompatible(
            sequence=sequence,
            context=context)
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        return self._impl.updateOptions(
            sequence=sequence,
            context=context)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        self._impl.updateStep(
            sequence=sequence,
            context=context,
            step=step)        
                        
        context.applyStep(
            sequence=sequence,
            step=step)

class RemoveBaseManipulator(robots.BaseManipulatorInterface):
    """
    - Slot Gain: +10% of Base Slots per Base Manipulator Removed rounded up
    - Cost Saving: Cr100 * Manipulator Size limited to 20% of Base Chassis Cost    
    """
    _SlotGainPercent = common.ScalarCalculation(
        value=10,
        name='Base Manipulator Removal Slot Gain Percentage')
    _CostSavingIncrement = common.ScalarCalculation(
        value=100,
        name='Base Manipulator Removal Cost Saving Increment')
    _MaxCostSavingPercent = common.ScalarCalculation(
        value=20,
        name='Base Manipulator Removal Max Cost Saving Percentage')

    def __init__(self) -> None:
        super().__init__()

    def size(self) -> int:
        return 0

    def instanceString(self) -> str:
        return "Removed"

    def componentString(self) -> str:
        return 'Remove Manipulator'
    
    def typeString(self) -> str:
        return 'Base Manipulator'
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return True
    
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
        
        slotGain = common.Calculator.ceil(
            value=common.Calculator.takePercentage(
                value=context.baseSlots(sequence=sequence),
                percentage=RemoveBaseManipulator._SlotGainPercent,
                name='Base Manipulator Removal Slot Gain'))
        slotModifier = common.Calculator.negate(
            value=slotGain,
            name='Base Manipulator Removal Slot Modifier')
        step.setSlots(
            slots=construction.ConstantModifier(value=slotModifier))

        size = context.attributeValue(
            attributeId=robots.RobotAttributeId.Size,
            sequence=sequence)
        maxReduction = common.Calculator.takePercentage(
            value=context.baseChassisCredits(sequence=sequence),
            percentage=RemoveBaseManipulator._MaxCostSavingPercent,
            name='Base Manipulator Removal Max Cost Reduction')
        assert(isinstance(size, common.ScalarCalculation))
        costReduction = common.Calculator.min(
            lhs=common.Calculator.multiply(
                lhs=RemoveBaseManipulator._CostSavingIncrement,
                rhs=size),
            rhs=maxReduction,
            name='Base Manipulator Removal Cost Reduction')
        costModifier = common.Calculator.negate(
            value=costReduction,
            name='Base Manipulator Removal Cost Modifier')
        step.setCredits(
            credits=construction.ConstantModifier(value=costModifier))
                        
        context.applyStep(
            sequence=sequence,
            step=step)
        
class AdditionalManipulator(robots.AdditionalManipulatorInterface):
    def __init__(self) -> None:
        super().__init__()
        self._impl = _ManipulatorImpl(
            manipulatorType=_ManipulatorImpl.ManipulatorType.Additional)

    def size(self) -> int:
        return self._impl.size()     

    def strength(self) -> int:
        return self._impl.strength()

    def dexterity(self) -> int:
        return self._impl.dexterity()

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def componentString(self) -> str:
        return 'Additional Manipulator'
    
    def typeString(self) -> str:
        return 'Additional Manipulator'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return self._impl.isCompatible(
            sequence=sequence,
            context=context)
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        return self._impl.updateOptions(
            sequence=sequence,
            context=context)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        self._impl.updateStep(
            sequence=sequence,
            context=context,
            step=step)        
                        
        context.applyStep(
            sequence=sequence,
            step=step)
        
class LegManipulator(robots.LegManipulatorInterface):
    """
    - Requirement: The number of leg manipulators should be limited by the number
    of legs
    """
    def __init__(self) -> None:
        super().__init__()
        self._impl = _ManipulatorImpl(
            manipulatorType=_ManipulatorImpl.ManipulatorType.Leg)
        
    def size(self) -> int:
        return self._impl.size()        

    def strength(self) -> int:
        return self._impl.strength()

    def dexterity(self) -> int:
        return self._impl.dexterity()        

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def componentString(self) -> str:
        return 'Leg Manipulator'
    
    def typeString(self) -> str:
        return 'Leg Manipulator'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not self._impl.isCompatible(
            sequence=sequence,
            context=context):
            return False

        legCount = self._totalLegCount(sequence=sequence, context=context)
        
        # Leg manipulators can only be used added to robots with legs
        if not legCount:
            return False 
        
        # Further leg manipulators can't be added if there is already one for
        # every leg
        legManipulators = context.findComponents(
            componentType=robots.LegManipulatorInterface,
            sequence=sequence)
        return len(legManipulators) < legCount
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        return self._impl.updateOptions(
            sequence=sequence,
            context=context)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        self._impl.updateStep(
            sequence=sequence,
            context=context,
            step=step)        
                        
        context.applyStep(
            sequence=sequence,
            step=step)                
            
    def _totalLegCount(
            self,
            sequence: str,
            context: robots.RobotContext            
            ) -> int:
        locomotionTypes = [
            robots.WalkerPrimaryLocomotion,
            robots.WalkerSecondaryLocomotion]
        legCount = 0
        for componentType in locomotionTypes:
            components = context.findComponents(
                componentType=componentType,
                sequence=sequence)
            for component in components:
                if isinstance(component, robots.WalkerPrimaryLocomotion):
                    legCount += component.legCount()
                elif isinstance(component, robots.WalkerSecondaryLocomotion):
                    legCount += component.legCount()

        return legCount
