import common
import construction
import enum
import math
import robots
import typing

class _OptionLevel(enum.Enum):
    Primitive = 'Primitive'
    Basic = 'Basic'
    Improved = 'Improved'
    Enhanced = 'Enhanced'
    Advanced = 'Advanced'
    Superior = 'Superior'

class _OptionSize(enum.Enum):
    Small = 'Small'
    Medium = 'Medium'
    Large = 'Large'

_PredefinedSpecies = [
    'Aslan',
    'Droyne',
    'Hiver',
    'Human',
    'K\'Kree',
    'Vargr',
]

# List of sciences taken from https://wiki.travellerrpg.com/Science with
# some extras added by me
# TODO: Not sure if these should be lower case or camel case
_PredefinedSciences = [
    'archaeology',
    'architecture',
    'artificial intelligence',
    'astrography',
    'astronomy',
    'astrophysics',
    'biochemistry', # Added by me
    'biology',
    'biophysics', # Added by me
    'biotechnology',
    'botany', # Added by me
    'chemistry',
    'cloning',
    'cognitive science',
    'computer technology',
    'cosmology',
    'cosmology',
    'cybertechnology',
    'ecology',
    'economics',
    'engineering',
    'epidemiology',
    'ethology',
    'ethnography',
    'ethnology',
    'eugenics',
    'exobiochemistry',
    'genetic engineering',
    'geology', # Added by me
    'gravitics',
    'information technology',
    'life sciences',
    'linguistics',
    'materials technology',
    'mathematics',
    'metempsychology',
    'microbiology', # Added by me
    'meteorology', # Added by me
    'nano science',
    'nanotechnology',
    'neurotechnology',
    'oceanography', # Added by me
    'physics',
    'physiology',
    'planetology', # Added by me (there is an example of this in the robot rules)
    'pocket universes',
    'psionicology',
    'psychohistory',
    'psychology',
    'robotics',
    'sociology',
    'sophontology',
    'taxonomy',
    'technology',
    'taxonomy',
    'trophics',
    'uplift',
    'vulcanology',
    'xenoarchaeology',
    'xenobiology',
    'xenolinguistics',
    'xenology',
    'zoology', # Added by me
]


#   █████████  ████            █████          ███████               █████     ███                         █████                           ████ 
#  ███░░░░░███░░███           ░░███         ███░░░░░███            ░░███     ░░░                         ░░███                           ░░███ 
# ░███    ░░░  ░███   ██████  ███████      ███     ░░███ ████████  ███████   ████   ██████  ████████      ░███  █████████████   ████████  ░███ 
# ░░█████████  ░███  ███░░███░░░███░      ░███      ░███░░███░░███░░░███░   ░░███  ███░░███░░███░░███     ░███ ░░███░░███░░███ ░░███░░███ ░███ 
#  ░░░░░░░░███ ░███ ░███ ░███  ░███       ░███      ░███ ░███ ░███  ░███     ░███ ░███ ░███ ░███ ░███     ░███  ░███ ░███ ░███  ░███ ░███ ░███ 
#  ███    ░███ ░███ ░███ ░███  ░███ ███   ░░███     ███  ░███ ░███  ░███ ███ ░███ ░███ ░███ ░███ ░███     ░███  ░███ ░███ ░███  ░███ ░███ ░███ 
# ░░█████████  █████░░██████   ░░█████     ░░░███████░   ░███████   ░░█████  █████░░██████  ████ █████    █████ █████░███ █████ ░███████  █████
#  ░░░░░░░░░  ░░░░░  ░░░░░░     ░░░░░        ░░░░░░░     ░███░░░     ░░░░░  ░░░░░  ░░░░░░  ░░░░ ░░░░░    ░░░░░ ░░░░░ ░░░ ░░░░░  ░███░░░  ░░░░░ 
#                                                        ░███                                                                   ░███           
#                                                        █████                                                                  █████          
#                                                       ░░░░░                                                                  ░░░░░                  

class _SlotOptionImpl(object):   
    def __init__(
            self,
            componentString: str,
            minTL: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__()

        if minTL != None and not isinstance(minTL, common.ScalarCalculation):
            minTL = common.ScalarCalculation(
                value=minTL,
                name=f'{componentString} Minimum TL') 

        self._componentString = componentString
        self._minTL = minTL
        self._incompatibleTypes = incompatibleTypes

    def instanceString(self) -> str:
        return self.componentString()

    def componentString(self) -> str:
        return self._componentString

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if self._minTL and \
                context.techLevel() < self._minTL.value():
            return False
        
        if self._incompatibleTypes:
            for componentType in self._incompatibleTypes:
                if context.hasComponent(
                    componentType=componentType,
                    sequence=sequence):
                    return False        

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
            context: robots.RobotContext,
            typeString: str,
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from _SlotOptionImpl so must implement createSteps')

class _SingleStepSlotOptionImpl(_SlotOptionImpl):
    """
    - Zero-Slot
        - Requirement: Up to Size + TL Zero-Slot options can be added at no slot cost,
        additional zero-slot options cost 1 slot    
        - Requirement: Zero slot options should generally be incompatible with their
        default suite counterpart
    """
    # NOTE: Zero slot options being incompatible with their default suite
    # counterpart is handled at the component level rather than the impl (but
    # the impl incompatibleTypes argument is used)

    _DefaultSuiteCount = 5 
   
    def __init__(
            self,
            componentString: str,
            minTL: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            perBaseSlotCost: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            constantCost: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            percentBaseSlots: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            constantSlots: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            notes: typing.Iterable[str] = None,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTL=minTL,
            incompatibleTypes=incompatibleTypes)

        if perBaseSlotCost != None and constantCost != None:
            raise ValueError('A component can\'t have a per slot _and_ constant cost.')
        if perBaseSlotCost != None and not isinstance(perBaseSlotCost, common.ScalarCalculation):
            perBaseSlotCost = common.ScalarCalculation(
                value=perBaseSlotCost,
                name=f'{componentString} Per Base Slot Cost')
        elif constantCost != None and not isinstance(constantCost, common.ScalarCalculation):
            constantCost = common.ScalarCalculation(
                value=constantCost,
                name=f'{componentString} Cost')
            
        if percentBaseSlots != None and constantSlots != None:
            raise ValueError('A component can\'t have a percentage _and_ constant slot requirement.')
        if percentBaseSlots != None and not isinstance(percentBaseSlots, common.ScalarCalculation):
            percentBaseSlots = common.ScalarCalculation(
                value=percentBaseSlots,
                name=f'{componentString} Base Slot Percentage')
        elif constantSlots != None and not isinstance(constantSlots, common.ScalarCalculation):
            constantSlots = common.ScalarCalculation(
                value=constantSlots,
                name=f'{componentString} Slot Requirement')

        self._perBaseSlotCost = perBaseSlotCost
        self._constantCost = constantCost
        self._percentBaseSlots = percentBaseSlots
        self._constantSlots = constantSlots
        self._notes = notes

    def isZeroSlot(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from _SlotOptionImpl so must implement isZeroSlot')

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext,
            typeString: str,
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=typeString)
        
        self.updateStep(
            sequence=sequence,
            context=context,
            step=step)        
                        
        context.applyStep(
            sequence=sequence,
            step=step)  

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        cost = None
        if self._perBaseSlotCost: 
            cost = common.Calculator.multiply(
                lhs=self._perBaseSlotCost,
                rhs=context.baseSlots(sequence=sequence),
                name=f'{self.componentString()} Cost')
        elif self._constantCost:
            cost = self._constantCost
            
        if cost:
            step.setCredits(
                credits=construction.ConstantModifier(value=cost))
            
        slots = None
        if self.isZeroSlot():
            slots = self._calcZeroSlotRequiredSlots(
                sequence=sequence,
                context=context)

            # Increment the zero-slot count, if this is the first zero-slot option
            # it will be set to 1
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=robots.RobotAttributeId.ZeroSlotCount,
                modifier=construction.ConstantModifier(
                    value=SlotOption._ZeroSlotCountIncrement)))
        elif self._percentBaseSlots:
            slots = common.Calculator.ceil(
                value=common.Calculator.takePercentage(
                    value=context.baseSlots(sequence=sequence),
                    percentage=self._percentBaseSlots),
                name=f'{self.componentString()} Required Slots')
        elif self._constantSlots:
            slots = self._constantSlots

        if slots:
            step.setSlots(
                slots=construction.ConstantModifier(value=slots))

        if self._notes:
            for note in self._notes:
                step.addNote(note)

    def _calcZeroSlotRequiredSlots(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[common.ScalarCalculation]:
        robotSize = context.attributeValue(
            attributeId=robots.RobotAttributeId.Size,
            sequence=sequence)
        assert(isinstance(robotSize, common.ScalarCalculation))
       
        limit = robotSize.value() + context.techLevel() + \
            _SingleStepSlotOptionImpl._DefaultSuiteCount
                
        currentCount = context.attributeValue(
            attributeId=robots.RobotAttributeId.ZeroSlotCount,
            sequence=sequence)
        if not currentCount:
            # There have been no zero slot components added yet so we know the
            # limit hasn't been reached so there is no slots required
            return None
        elif isinstance(currentCount, common.ScalarCalculation):
            if currentCount.value() < limit:
                # The zero slot limit hasn't been reached yet so there is no
                # slots required
                return None
        else:
            # TODO: Handle this better
            return None
        
        slots = common.ScalarCalculation(
            value=1,
            name='Slots Required For Zero-Slot Options Over The {limit} Option Threshold')

        # Additional step for clarity
        return common.Calculator.equals(
            value=slots,
            name=f'{self.componentString()} Slot Requirement')

class _EnumSelectSlotOptionImpl(_SingleStepSlotOptionImpl):
    def __init__(
            self,
            componentString: str,
            enumType: typing.Type[enum.Enum],
            optionId: str,
            optionName: str,
            optionDescription: str,
            optionDefault: enum.Enum,
            # If optionChoices is specified then it will be used as the list of
            # enums that the user can select from. If None is specified then
            # all enums of enumType can be selected from
            optionChoices: typing.Optional[typing.Iterable[enum.Enum]] = None,
            # If minTLMap is specified then the list of options that can be
            # selected will be filtered based on the robots TL.
            # NOTE: If specified minTLMap MUST contain an entry for all enums
            # that can be a valid choice. If an enum doesn't have an entry in
            # the map it will never be a possible selection
            minTLMap: typing.Optional[typing.Mapping[enum.Enum, int]] = None,
            # Absolute min TL, if minTLMap is also specified then the maximum
            # of this and the entry from the map will be used
            minTL: typing.Optional[int] = None,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTL=minTL,
            incompatibleTypes=incompatibleTypes)
        
        self._enumType = enumType
        self._selectableEnums = optionChoices
        self._minTLMap = minTLMap

        self._enumOption = construction.EnumOption(
            id=optionId,
            name=optionName,
            type=enumType,
            value=optionDefault,
            description=optionDescription)

    def instanceString(self) -> str:
        value: enum.Enum = self._enumOption.value()
        return f'{self.componentString()} ({value.value})'
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        
        validEnums = self._calcValidEnums(sequence=sequence, context=context)
        return len(validEnums) > 0

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._enumOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        super().updateOptions(
            sequence=sequence,
            context=context)
        
        validEnums = self._calcValidEnums(sequence=sequence, context=context)
        self._enumOption.setOptions(options=validEnums)

    def _calcValidEnums(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[enum.Enum]:
        possibleEnums = self._selectableEnums if self._selectableEnums else self._enumType
        if not self._minTLMap:
            return possibleEnums
        
        robotTL = context.techLevel()
        validEnums = []
        for possibleEnum in possibleEnums:
            minTL = self._minTLMap.get(possibleEnum, None)
            if minTL != None and robotTL >= minTL:
                validEnums.append(possibleEnum)
        return validEnums    

class _VisualConcealmentSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    <ALL>
    - Requirement: Not compatible with Reflect Armour
    - Requirement: Not compatible with Solar Coating
    Primitive
    - Min TL: 1
    - Cost: Cr1 * Base Slots
    - Note: Detection DM -1 at >= 500m
    Basic
    - Min TL: 4
    - Cost: Cr4 * Base Slots
    - Note: Detection DM -2 at >= 250m
    Improved
    - Min TL: 7
    - Cost: Cr40 * Base Slots
    - Note: Detection DM -2 at >= 100m
    Enhanced
    - Min TL: 11
    - Cost: Cr100 * Base Slots
    - Note: Detection DM -3 at >= 50m
    Advanced
    - Min TL: 12
    - Cost: Cr500 * Base Slots
    - Note: Detection DM -4 at >= 10m
    Superior
    - Min TL: 13
    - Cost: Cr2500 * Base Slots
    - Note: Detection DM -4 at >= 1m or over      
    """
    # TODO: I'm not sure if I should include the comments as the values are only
    # values for size 5 robots
    # TODO: Handle comparability with reflect armour and solar coating
    # - This is complicated by the fact zero-slot components will need to be
    #   incompatible with default suite (i.e. zero cost visual concealment is
    #   incompatible with default suite reflect)

    _MinTLMap = {
        _OptionLevel.Primitive: 1,
        _OptionLevel.Basic: 4,
        _OptionLevel.Improved: 7,
        _OptionLevel.Enhanced: 11,
        _OptionLevel.Advanced: 12,
        _OptionLevel.Superior: 13,
    }

    _CostPerSlotMap = {
        _OptionLevel.Primitive: 1,
        _OptionLevel.Basic: 4,
        _OptionLevel.Improved: 40,
        _OptionLevel.Enhanced: 100,
        _OptionLevel.Advanced: 500,
        _OptionLevel.Superior: 2500,
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Visual Concealment',
            enumType=_OptionLevel,
            optionId='Level',
            optionName='Level',
            optionDescription='Specify the concealment level.',
            optionDefault=_OptionLevel.Basic,
            minTLMap=_VisualConcealmentSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        level = self._enumOption.value()
        assert(isinstance(level, _OptionLevel))

        costPerSlot = common.ScalarCalculation(
            value=_VisualConcealmentSlotOptionImpl._CostPerSlotMap[level],
            name=f'{level.value} Visual Concealment Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=costPerSlot,
            rhs=context.baseSlots(sequence=sequence),
            name=f'{self.componentString()} Cost')

        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
class _AudibleConcealmentSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    Basic
    - Min TL: 5
    - Cost: Cr5 * Base Slots
    - Note: Detection DM -1 at >= 50m
    Improved
    - Min TL: 8
    - Cost: Cr10 * Base Slots
    - Note: Detection DM -2 at >= 10m
    Advanced
    - Min TL: 10
    - Cost: Cr50 * Base Slots
    - Note: Detection DM -3 at >= 50m    
    """
    # TODO: I'm not sure if I should include the comments

    _MinTLMap = {
        _OptionLevel.Basic: 5,
        _OptionLevel.Improved: 8,
        _OptionLevel.Advanced: 10,
    }

    _CostPerSlotMap = {
        _OptionLevel.Basic: 5,
        _OptionLevel.Improved: 10,
        _OptionLevel.Advanced: 50,
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Audible Concealment',
            enumType=_OptionLevel,
            optionId='Level',
            optionName='Level',
            optionDescription='Specify the concealment level.',            
            optionDefault=_OptionLevel.Basic,
            minTLMap=_AudibleConcealmentSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        level = self._enumOption.value()
        assert(isinstance(level, _OptionLevel))

        costPerSlot = common.ScalarCalculation(
            value=_AudibleConcealmentSlotOptionImpl._CostPerSlotMap[level],
            name=f'{level.value} {self.componentString()} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=costPerSlot,
            rhs=context.baseSlots(sequence=sequence),
            name=f'{self.componentString()} Cost')

        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
class _OlfactoryConcealmentSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    Basic
    - Min TL: 7
    - Cost: Cr10 * Base Slots
    - Note: Detection DM -1 at >= 100m
    Improved
    - Min TL: 9
    - Cost: Cr20 * Base Slots
    - Note: Detection DM -2 at >= 20m
    Advanced
    - Min TL: 12
    - Cost: Cr100 * Base Slots
    - Note: Detection DM -3 at >= 10m
    """
    # TODO: I'm not sure if I should include the comments

    _MinTLMap = {
        _OptionLevel.Basic: 7,
        _OptionLevel.Improved: 9,
        _OptionLevel.Advanced: 12,
    }

    _CostPerSlotMap = {
        _OptionLevel.Basic: 10,
        _OptionLevel.Improved: 20,
        _OptionLevel.Advanced: 100,
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Olfactory Concealment',
            enumType=_OptionLevel,
            optionId='Level',
            optionName='Level',
            optionDescription='Specify the concealment level.', 
            optionDefault=_OptionLevel.Basic,           
            minTLMap=_OlfactoryConcealmentSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)  
        
    def isZeroSlot(self) -> bool:
        return True        

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        level = self._enumOption.value()
        assert(isinstance(level, _OptionLevel))

        costPerSlot = common.ScalarCalculation(
            value=_OlfactoryConcealmentSlotOptionImpl._CostPerSlotMap[level],
            name=f'{level.value} {self.componentString()} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=costPerSlot,
            rhs=context.baseSlots(sequence=sequence),
            name=f'{self.componentString()} Cost')

        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
class _HostileEnvironmentProtectionSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 6
    Cost: Cr300 * Base Slots
    Trait: Rads +500
    """
    _RadsTrait = common.ScalarCalculation(
        value=+500,
        name='Hostile Environment Protection Rads Modifier')

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Hostile Environment Protection',
            minTL=6,
            perBaseSlotCost=300,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        
        
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(sequence, context, step)

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Rads,
            modifier=construction.ConstantModifier(
                value=_HostileEnvironmentProtectionSlotOptionImpl._RadsTrait)))
        
class _ReflectArmourSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 10
    Cost: Cr100 * Base Slots
    Requirement: Not compatible with Camouflage: Visual Concealment
    Requirement: Not compatible with Solar Coating
    """
    # NOTE: Compatibility with other components is handled by the component
    # class rather than the implementation as it needs component level
    # knowledge
    # TODO: Implement incomparability with other components
    # - This is complicated by the fact zero-slot components will need to be
    #   incompatible with default suite (i.e. zero cost visual concealment is
    #   incompatible with default suite reflect)    

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Reflect Armour',
            minTL=10,
            perBaseSlotCost=100,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        
        
class _SolarCoatingSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    <ALL>
    - Requirement: Not compatible with Camouflage: Visual Concealment
    - Requirement: Not compatible with Reflect Armour
    Basic
    - Min TL: 6
    - Cost: Cr500 * Base Slots
    - Note: Max ground speed of 1m per round when relying on solar coating for power
    - Note: Unable to fly when relying on using solar coating for power
    - Note: Can fully recharge in 4 * Endurance hours if robot is dormant
    Improved
    - Min TL: 8
    - Cost: Cr100 * Base Slots
    - Note: Max ground speed of 2m per round when relying on solar coating for power
    - Note: Unable to fly when relying on using solar coating for power
    - Note: Can fully recharge in Endurance hours if robot is dormant
    - Note: Can fully recharge in 4 * Endurance hours if robot is operational while charging              
    Enhanced
    - Min TL: 10
    - Cost: Cr200 * Base Slots
    - Note: Max ground speed of 4m per round when relying on solar coating for power
    - Note: Max flying speed of 1m per round when relying on solar coating for power
    - Note: Can fully recharge in Endurance hours if robot is dormant 
    - Note: Can fully recharge in 4 * Endurance hours if robot is operational while charging                         
    Advanced
    - Min TL: 12
    - Cost: Cr500 * Base Slots
    - Note: Ground speed is not reduced when relying on solar coating for power
    - Note: Max flying speed of 2m per round when relying on solar coating for power
    - Note: Can fully recharge in Endurance hours if robot is dormant
    - Note: Can fully recharge in 4 * Endurance hours if robot is operational while charging    
    """
    # NOTE: Compatibility with other components is handled by the component
    # class rather than the implementation as it needs component level
    # knowledge
    # TODO: Implement incomparability with other components
    # - This is complicated by the fact zero-slot components will need to be
    #   incompatible with default suite (i.e. zero cost visual concealment is
    #   incompatible with default suite reflect)    
    # TODO: Add notes
    # TODO: Handle notes that use Endurance hours. Ideally they would be filled
    # in to give actual hours rather than the formula. If they can be done here
    # depends on if endurance has been fully calculated yet

    _MinTLMap = {
        _OptionLevel.Basic: 6,
        _OptionLevel.Improved: 8,
        _OptionLevel.Enhanced: 10,
        _OptionLevel.Advanced: 12,
    }

    _CostPerSlotMap = {
        _OptionLevel.Basic: 500,
        _OptionLevel.Improved: 100,
        _OptionLevel.Enhanced: 200,
        _OptionLevel.Advanced: 500,
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Solar Coating',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the solar coating type.',
            optionDefault=_OptionLevel.Basic,            
            minTLMap=_SolarCoatingSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        level = self._enumOption.value()
        assert(isinstance(level, _OptionLevel))

        costPerSlot = common.ScalarCalculation(
            value=_SolarCoatingSlotOptionImpl._CostPerSlotMap[level],
            name=f'{level.value} {self.componentString()} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=costPerSlot,
            rhs=context.baseSlots(sequence=sequence),
            name=f'{self.componentString()} Cost')

        step.setCredits(
            credits=construction.ConstantModifier(value=cost))

class _VacuumEnvironmentProtectionSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    Standard
    - Min TL: 7
    - Cost: Cr600 * Base Slots
    - Requirement: Not compatible with biological robots
    Biological
    - Min TL: 10
    - Cost: Cr50000 * Base Slots 
    - Requirement: Only compatible with biological robots
    """
    # TODO: Handle only compatible with biological robots after I
    # add support for biological

    class _ProtectionType(enum.Enum):
        Standard = 'Standard'
        Biological = 'Biological'

    _MinTLMap = {
        _ProtectionType.Standard: 7,
        _ProtectionType.Biological: 10
    }

    _CostPerSlotMap = {
        _ProtectionType.Standard: 600,
        _ProtectionType.Biological: 50000
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Vacuum Environment Protection',
            enumType=_VacuumEnvironmentProtectionSlotOptionImpl._ProtectionType,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the protection type.',
            optionDefault=_VacuumEnvironmentProtectionSlotOptionImpl._ProtectionType.Standard,      
            minTLMap=_VacuumEnvironmentProtectionSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)  

    def isZeroSlot(self) -> bool:
        return True         

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        protection = self._enumOption.value()
        assert(isinstance(protection, _VacuumEnvironmentProtectionSlotOptionImpl._ProtectionType))

        costPerSlot = common.ScalarCalculation(
            value=_VacuumEnvironmentProtectionSlotOptionImpl._CostPerSlotMap[protection],
            name=f'{protection.value} {self.componentString()} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=costPerSlot,
            rhs=context.baseSlots(sequence=sequence),
            name=f'{self.componentString()} Cost')

        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
class _DroneInterfaceSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 6
    - Cost: Cr100 or free if Default Suite
    - Requirement: A drone interface requires a separate transceiver to be
    installed (p34)
    """

    def __init__(
            self,
            isDefaultSuite: bool,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Drone Interface',
            minTL=6,
            constantCost=None if isDefaultSuite else 100,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        
        if context.findFirstComponent(
            componentType=TransceiverDefaultSuiteOption,
            sequence=sequence):
            return True
        
        if context.findFirstComponent(
            componentType=TransceiverSlotOption,
            sequence=sequence):
            return True        

        return False # No transceiver
        
class _EncryptionModuleSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 6
    - Cost: Cr4000
    """
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Encryption Module',
            minTL=6,
            constantCost=4000)
        
    def isZeroSlot(self) -> bool:
        return True        
        
class _TransceiverSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    Basic 5km
    - Min TL: 7
    - Cost: Cr250 or free if Default Suite
    Basic 50km
    - Min TL: 7
    - Cost: Cr1000
    - Slots: 1
    Basic 500km
    - Min TL: 7
    - Cost: Cr2000
    - Slots: 1
    Basic 5,000km
    - Min TL: 7
    - Cost: Cr10000
    - Slots: 2
    Basic 50,000km
    - Min TL: 8
    - Cost: Cr20000
    - Slots: 4
    Basic 500,000km
    - Min TL: 9
    - Cost: Cr50000
    - Slots: 8        
    Improved 5km:
    - Min TL: 8
    - Cost: Cr100 or free if Default Suite
    Improved 50km:
    - Min TL: 8
    - Cost: Cr500
    Improved 500km
    - Min TL: 9
    - Cost: Cr1000
    Improved 5,000km
    - Min TL: 9
    - Cost: Cr5000
    Improved 50,000km
    - Min TL: 10
    - Cost: Cr10000
    - Slots: 2
    Improved 500,000km
    - Min TL: 11
    - Cost: Cr25000
    - Slots: 4        
    Enhanced 50km
    - Min TL: 10
    - Cost: Cr250
    Enhanced 500km
    - Min TL: 11
    - Cost: Cr500
    Enhanced 5,000km
    - Min TL: 12
    - Cost: Cr1000
    Enhanced 50,000km
    - Min TL: 12
    - Cost: Cr5000
    - Slots: 1
    Enhanced 500,000km
    - Min TL: 13
    - Cost: Cr10000
    - Slots: 2    
    Advanced 50km
    - Min TL: 13
    - Cost: Cr100
    Advanced 500km
    - Min TL: 14
    - Cost: Cr250
    Advanced 5,000km
    - Min TL: 15
    - Cost: Cr500
    Advanced 50,000km
    - Min TL: 15
    - Cost: Cr2500
    - Slots: 1
    Advanced 500,000km
    - Min TL: 16
    - Cost: Cr5000
    - Slots: 1
    """
    # NOTE: Some transceiver types are zero slot options and some are slot
    # cost options
    # TODO: I think there is scope for improving usability by reducing the
    # options that are shown to the user as some options wouldn't make logical
    # sense. For example, if your at designing a TL 14 robot there seems little
    # point giving the user the option to select Enhanced 500km as Advanced
    # 500km is half the price so they would only ever select that. I think it
    # should be possible to just get it down to a drop down where the user
    # selects the range they desired from a list of ranges available at that TL.
    # IMPORTANT: There may be some complexity around the 2 types that are free
    # for default suite
    # TODO: I think it might make sense to make Transceiver something you can
    # select more than one of (a back up or long & short range). This may need
    # updates to other components which check for a Transceiver

    class _TransceiverType(enum.Enum):
        Basic5km = 'Basic 5km'
        Basic50km = 'Basic 50km'
        Basic500km = 'Basic 500km'
        Basic5000km = 'Basic 5,000km'
        Basic50000km = 'Basic 50,000km'
        Basic500000km = 'Basic 500,000km'
        Improved5km = 'Improved 5km'
        Improved50km = 'Improved 50km'
        Improved500km = 'Improved 500km'
        Improved5000km = 'Improved 5,000km'
        Improved50000km = 'Improved 50,000km'
        Improved500000km = 'Improved 500,000km'
        Enhanced50km = 'Enhanced 50km'
        Enhanced500km = 'Enhanced 500km'
        Enhanced5000km = 'Enhanced 5,000km'
        Enhanced50000km = 'Enhanced 50,000km'
        Enhanced500000km = 'Enhanced 500,000km'
        Advanced50km = 'Advanced 50km'
        Advanced500km = 'Advanced 500km'
        Advanced5000km = 'Advanced 5,000km'
        Advanced50000km = 'Advanced 50,000km'
        Advanced500000km = 'Advanced 500,000km'

    _MinTLMap = {
        _TransceiverType.Basic5km: 7,
        _TransceiverType.Basic50km: 7,
        _TransceiverType.Basic500km: 7,
        _TransceiverType.Basic5000km: 7,
        _TransceiverType.Basic50000km: 8,
        _TransceiverType.Basic500000km: 9,
        _TransceiverType.Improved5km: 8,
        _TransceiverType.Improved50km: 8,
        _TransceiverType.Improved500km: 9,
        _TransceiverType.Improved5000km: 9,
        _TransceiverType.Improved50000km: 10,
        _TransceiverType.Improved500000km: 11,
        _TransceiverType.Enhanced50km: 10,
        _TransceiverType.Enhanced500km: 11,
        _TransceiverType.Enhanced5000km: 12,
        _TransceiverType.Enhanced50000km: 12,
        _TransceiverType.Enhanced500000km: 13,
        _TransceiverType.Advanced50km: 13,
        _TransceiverType.Advanced500km: 14,
        _TransceiverType.Advanced5000km: 15,
        _TransceiverType.Advanced50000km: 15,
        _TransceiverType.Advanced500000km: 16
    }

    # Data Structure: Cost, Slots, Range
    _DataMap = {
        _TransceiverType.Basic5km: (250, None, 5),
        _TransceiverType.Basic50km: (1000, 1, 50),
        _TransceiverType.Basic500km: (2000, 1, 500),
        _TransceiverType.Basic5000km: (10000, 2, 5000),
        _TransceiverType.Basic50000km: (20000, 4, 50000),
        _TransceiverType.Basic500000km: (50000, 8, 500000),       
        _TransceiverType.Improved5km: (100, None, 5),
        _TransceiverType.Improved50km: (500, None, 50),
        _TransceiverType.Improved500km: (1000, None, 500),
        _TransceiverType.Improved5000km: (5000, None, 5000),
        _TransceiverType.Improved50000km: (10000, 2, 50000),
        _TransceiverType.Improved500000km: (25000, 4, 500000),
        _TransceiverType.Enhanced50km: (250, None, 50),
        _TransceiverType.Enhanced500km: (500, None, 500),
        _TransceiverType.Enhanced5000km: (1000, None, 5000),
        _TransceiverType.Enhanced50000km: (5000, 1, 50000),
        _TransceiverType.Enhanced500000km: (10000, 2, 500000), 
        _TransceiverType.Advanced50km: (100, None, 50),
        _TransceiverType.Advanced500km: (250, None, 500),
        _TransceiverType.Advanced5000km: (500, None, 5000),
        _TransceiverType.Advanced50000km: (2500, 1, 50000),
        _TransceiverType.Advanced500000km: (5000, 1, 500000)
    }

    _FreeDefaultSuiteTypes = [
        _TransceiverType.Basic5km,
        _TransceiverType.Improved5km
    ]

    _ZeroSlotTypes = [
        _TransceiverType.Basic5km ,
        _TransceiverType.Improved5km,
        _TransceiverType.Improved50km,
        _TransceiverType.Improved500km,
        _TransceiverType.Improved5000km,
        _TransceiverType.Enhanced50km,
        _TransceiverType.Enhanced500km,
        _TransceiverType.Enhanced5000km,
        _TransceiverType.Advanced50km,
        _TransceiverType.Advanced500km,
        _TransceiverType.Advanced5000km,
    ]

    def __init__(
            self,
            isDefaultSuite: bool,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Transceiver',
            enumType=_TransceiverSlotOptionImpl._TransceiverType,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the transceiver type.',
            # NOTE: The default here is important as an Improved 5km Transceiver
            # is part of the canonical default suite for a robot. That means it
            # needs to be the default here so when construction logic creates a
            # Transceiver component for the default suite it will default to the
            # correct type
            optionDefault=_TransceiverSlotOptionImpl._TransceiverType.Improved5km,                  
            minTLMap=_TransceiverSlotOptionImpl._MinTLMap,
            optionChoices=_TransceiverSlotOptionImpl._ZeroSlotTypes if isDefaultSuite else None,
            incompatibleTypes=incompatibleTypes)
        
        self._isDefaultSuite = isDefaultSuite

    def range(self) -> int:
        transceiverType = self._enumOption.value()
        assert(isinstance(transceiverType, _TransceiverSlotOptionImpl._TransceiverType))

        _, _, range = _TransceiverSlotOptionImpl._DataMap[transceiverType]
        return range

    def isZeroSlot(self) -> bool:
        transceiverType = self._enumOption.value()
        return transceiverType in _TransceiverSlotOptionImpl._ZeroSlotTypes

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        transceiverType = self._enumOption.value()
        assert(isinstance(transceiverType, _TransceiverSlotOptionImpl._TransceiverType))

        cost, slots, _ = _TransceiverSlotOptionImpl._DataMap[transceiverType]

        ignoreCost = self._isDefaultSuite and \
            (transceiverType in _TransceiverSlotOptionImpl._FreeDefaultSuiteTypes)

        if cost and not ignoreCost:
            cost = common.ScalarCalculation(
                value=cost,
                name=f'{transceiverType.value} {self.componentString()} Cost')

            step.setCredits(
                credits=construction.ConstantModifier(value=cost))
            
        if slots:
            slots = common.ScalarCalculation(
                value=slots,
                name=f'{transceiverType.value} {self.componentString()} Required Slots')

            step.setSlots(
                slots=construction.ConstantModifier(value=slots))
            
class _VideoScreenSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    Basic Panel
        - Min TL: 7
        - Cost: Cr200 or free if Default Suite
    Improved Panel
        - Min TL: 8
        - Cost: Cr500
    Advanced Panel
        - Min TL: 10
        - Cost: Cr2000
    Basic Full Surface
        - Min TL: 7
        - Cost: Cr200 * Base Slots
    Improved Full Surface
        - Min TL: 8
        - Cost: Cr500 * Base Slots
    Advanced Full Surface
        - Min TL: 10
        - Cost: Cr2000 * Base Slots
    """
    # TODO: It would make sense for panels to be a component that can have
    # multiple instances installed but it doesn't make sense for full surface
    # screens. The easiest thing to do would be to split it into 2 components

    class _ScreenType(enum.Enum):
        BasicPanel = 'Basic Panel'
        ImprovedPanel = 'Improved Panel'
        AdvancedPanel = 'Advanced Panel'
        BasicFullSurface = 'Basic Full Surface'
        ImprovedFullSurface = 'Improved Full Surface'
        AdvancedFullSurface = 'Advanced Full Surface'

    _MinTLMap = {
        _ScreenType.BasicPanel: 7,
        _ScreenType.ImprovedPanel: 8,
        _ScreenType.AdvancedPanel: 10,
        _ScreenType.BasicFullSurface: 7,
        _ScreenType.ImprovedFullSurface: 8,
        _ScreenType.AdvancedFullSurface: 10
    }

    _CostMap = {
        # Constant costs
        _ScreenType.BasicPanel: (200, True),
        _ScreenType.ImprovedPanel: (500, True),
        _ScreenType.AdvancedPanel: (2000, True),
        # Per slot costs
        _ScreenType.BasicFullSurface: (200, False),
        _ScreenType.ImprovedFullSurface: (500, False),
        _ScreenType.AdvancedFullSurface: (2000, False)
    }

    _FreeDefaultSuiteTypes = [_ScreenType.BasicPanel]

    def __init__(
            self,
            isDefaultSuite: bool,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Video Screen',
            enumType=_VideoScreenSlotOptionImpl._ScreenType,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the screen type.',
            optionDefault=_VideoScreenSlotOptionImpl._ScreenType.BasicPanel,                      
            minTLMap=_VideoScreenSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
        self._isDefaultSuite = isDefaultSuite  

    def isZeroSlot(self) -> bool:
        return True         

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        screenType = self._enumOption.value()
        assert(isinstance(screenType, _VideoScreenSlotOptionImpl._ScreenType))

        if not self._isDefaultSuite or \
            screenType not in _VideoScreenSlotOptionImpl._FreeDefaultSuiteTypes:

            cost, isConstantCost = _VideoScreenSlotOptionImpl._CostMap[screenType]
            cost = common.ScalarCalculation(
                value=cost,
                name='{type} {component} {wording}'.format(
                    type=screenType.value,
                    component=self.componentString(),
                    wording='Cost' if isConstantCost else 'Cost Per Slot'))

            if not isConstantCost:
                cost = common.Calculator.multiply(
                    lhs=cost,
                    rhs=context.baseSlots(sequence=sequence),
                    name='{type} {component} Cost'.format(
                        type=screenType.value,
                        component=self.componentString()))

            step.setCredits(
                credits=construction.ConstantModifier(value=cost))
        
class _VoderSpeakerSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    Standard
    - Min TL: 8
    - Cost: Cr100 or free if Default Suite
    Broad Spectrum
    - Min TL: 10
    - Cost: Cr500
    """
    # TODO: Handle only compatible with biological robots after I
    # add support for biological

    class _SpeakerType(enum.Enum):
        Standard = 'Standard'
        BroadSpectrum = 'Broad Spectrum'

    _MinTLMap = {
        _SpeakerType.Standard: 8,
        _SpeakerType.BroadSpectrum: 10
    }

    _CostMap = {
        _SpeakerType.Standard: 100,
        _SpeakerType.BroadSpectrum: 500
    }

    _FreeDefaultSuiteTypes = [_SpeakerType.Standard]

    def __init__(
            self,
            isDefaultSuite: bool,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Voder Speaker',
            enumType=_VoderSpeakerSlotOptionImpl._SpeakerType,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the speaker type.',            
            optionDefault=_VoderSpeakerSlotOptionImpl._SpeakerType.Standard,                      
            minTLMap=_VoderSpeakerSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)

        self._isDefaultSuite = isDefaultSuite

    def isZeroSlot(self) -> bool:
        return True        

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        speakerType = self._enumOption.value()
        assert(isinstance(speakerType, _VoderSpeakerSlotOptionImpl._SpeakerType))

        if not self._isDefaultSuite or \
            (speakerType not in _VoderSpeakerSlotOptionImpl._FreeDefaultSuiteTypes):
            cost = common.ScalarCalculation(
                value=_VoderSpeakerSlotOptionImpl._CostMap[speakerType],
                name=f'{speakerType.value} {self.componentString()} Cost')

            step.setCredits(
                credits=construction.ConstantModifier(value=cost))

class _WirelessDataLinkSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 8
    Cost: Cr10 or free if Default Suite
    """
    def __init__(
            self,
            isDefaultSuite: bool,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Wireless Data Link',
            minTL=8,
            constantCost=None if isDefaultSuite else 10,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        
        
class _GeckoGrippersSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 9
    Cost: Cr500 * Base Slots
    """
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Gecko Grippers',
            minTL=9,
            perBaseSlotCost=500,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        
        
class _InjectorNeedleSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 7
    - Cost: Cr20
    - Requirement: Multiple Injector Needle can be installed, each taking up a
    zero-slot option
    """
    # NOTE: Support for multiple injectors is achieved in the component rather
    # than the impl

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Injector Needle',
            minTL=7,
            constantCost=20,
            incompatibleTypes=incompatibleTypes) 
        
    def isZeroSlot(self) -> bool:
        return True        

class _LaserDesignatorSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 7
    - Cost: Cr500
    """
    # TODO: Fire Control System needs to add a note that it receives a DM+2 to
    # attack designated targets

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Laser Designator',
            minTL=7,
            constantCost=500,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        
        
class _MagneticGrippersSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 8
    Cost: Cr10 * Base Slots
    Note: Robot can grip to metallic surfaces in gravity of 0-1.5G
    """
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Magnetic Grippers',
            minTL=8,
            perBaseSlotCost=10,
            notes=['Robot can grip to metallic surfaces in gravity of 0-1.5G'],
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True         
        
class _ParasiticLinkSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 10
    Cost: Cr10000
    """
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Parasitic Link',
            minTL=10,
            constantCost=10000,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        
        
class _SelfMaintenanceEnhancementSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    Basic (p37)
    - Min TL: 7
    - Cost: Cr20000 * Base Slots
    - Note: The robot requires maintenance every 12 years.
    - Note: If the maintenance schedule is not followed, a Malfunction Check (108) must be made every year
    Improved (p37)
    - Min TL: 8
    - Cost: Cr50000 * Base Slots
    - Note: The robot requires maintenance every 24 years.
    - Note: If the maintenance schedule is not followed, a Malfunction Check (108) must be made every 2 years
    Enhanced (p54)
    - Min TL: 13
    - Cost: Cr200000 * Base Slots
    - Slots: 10% of Base Slots
    - Trait: Maintenance Period = 60 years
    - Trait: Malfunction Check = 5 year
    Advanced (p54)
    - Min TL: 15
    - Cost: Cr500000 * Base Slots
    - Slots: 10% of Base Slots
    - Trait: Maintenance Period = Indefinite
    - Trait: Malfunction Check = Indefinite
    """
    # NOTE: Some maintenance types are zero slot options and some are slot
    # cost options

    _MinTLMap = {
        _OptionLevel.Basic: 7,
        _OptionLevel.Improved: 8,
        _OptionLevel.Enhanced: 13,
        _OptionLevel.Advanced: 15,
    }

    # Data Structure: Cost Per Base Slot, Base Slot Percentage, Maintenance Period, Malfunction Check
    _DataMap = {
        _OptionLevel.Basic: (20000, None, 12, 1),
        _OptionLevel.Improved: (50000, None, 24, 2),
        _OptionLevel.Improved: (200000, 10, 60, 5),
        _OptionLevel.Advanced: (500000, 10, None, None)
    }

    _ZeroSlotTypes = [
        _OptionLevel.Basic,
        _OptionLevel.Improved
    ]    

    def __init__(
            self,
            isDefaultSuite: bool,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Self-Maintenance Enhancement',
            enumType=_OptionLevel,
            optionId='Level',
            optionName='Level',
            optionDescription='Specify the maintenance level.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_SelfMaintenanceEnhancementSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
        self._isDefaultSuite = isDefaultSuite
        
    def isZeroSlot(self) -> bool:
        transceiverType = self._enumOption.value()
        return transceiverType in _SelfMaintenanceEnhancementSlotOptionImpl._ZeroSlotTypes
    
    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        super().updateOptions(sequence, context)

        if self._isDefaultSuite:
            # Only zero-slot options can be selected whe part of the default
            # suite
            self._enumOption.setOptions(
                _SelfMaintenanceEnhancementSlotOptionImpl._ZeroSlotTypes)    

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        level = self._enumOption.value()
        assert(isinstance(level, _OptionLevel))

        perSlotCost, percentageSlots, maintenancePeriod, malfunctionCheck = \
            _SelfMaintenanceEnhancementSlotOptionImpl._DataMap[level]
        
        baseString = f'{level.value} {self.componentString()}'
        
        if perSlotCost:
            perSlotCost = common.ScalarCalculation(
                value=perSlotCost,
                name=f'{baseString} Per Base Slot Cost')
            totalCost = common.Calculator.multiply(
                lhs=perSlotCost,
                rhs=context.baseSlots(sequence=sequence),
                name=f'{baseString} Total Cost')
            step.setCredits(
                credits=construction.ConstantModifier(value=totalCost))

        if percentageSlots:
            percentageSlots = common.ScalarCalculation(
                value=percentageSlots,
                name=f'{baseString} Base Slot Percentage')
            slots = common.Calculator.ceil(
                value=common.Calculator.takePercentage(
                    value=context.baseSlots(sequence=sequence),
                    percentage=percentageSlots),
                name=f'{baseString} Required Slots')
            step.setSlots(
                slots=construction.ConstantModifier(value=slots))            

        if maintenancePeriod:
            step.addNote(
                note='The robot requires maintenance every {period} years'.format(
                    period=maintenancePeriod))
            step.addNote(
                note='If the maintenance schedule is not followed, a Malfunction Check must be made every {wording} (p108) '.format(
                    wording='year' if malfunctionCheck == 1 else f'{malfunctionCheck} years'))
        else:
            step.addNote(note='The robot can operate indefinitely without maintenance')

class _StingerSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 7
    - Cost: Cr10
    - Requirement: Multiple Stingers can be installed each taking up a zero-slot
    option
    - Note: Does 1 point of damage and has AP equal to the base armour of a
    robot of it's TL (see table on p19)
    """
    # NOTE: Support for multiple stingers is achieved in the component rather
    # than the impl

    _TL6to8APTrait = common.ScalarCalculation(
        value=2,
        name='TL 6-8 Stinger AP Trait')
    _TL9to11APTrait = common.ScalarCalculation(
        value=3,
        name='TL 9-11 Stinger AP Trait')
    _TL12to17APTrait = common.ScalarCalculation(
        value=4,
        name='TL 12-17 Stinger AP Trait')
    _TL18PlusAPTrait = common.ScalarCalculation(
        value=6,
        name='TL 18+ Stinger AP Trait')

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Stinger',
            minTL=6,
            constantCost=10,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        
        
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        currentTL = context.techLevel()
        apTrait = None
        if currentTL >= 18:
            apTrait = _StingerSlotOptionImpl._TL18PlusAPTrait
        elif currentTL >= 12:
            apTrait = _StingerSlotOptionImpl._TL12to17APTrait
        elif currentTL >= 9:
            apTrait = _StingerSlotOptionImpl._TL9to11APTrait
        elif currentTL >= 6:
            apTrait = _StingerSlotOptionImpl._TL6to8APTrait

        if apTrait:        
            step.addNote(f'Does 1 point of damage and has AP {apTrait.value()}')

class _AtmosphericSensorSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 8
    Cost: Cr100
    """
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Atmospheric Sensor',
            minTL=8,
            constantCost=100,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        

class _AuditorySensorSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    Standard
    - Min TL: 5
    - Cost: Cr10 or free if Default Suite
    Broad Spectrum
    - Min TL: 8
    - Cost: Cr200
    - Trait: Heightened Senses
    """

    class _SensorType(enum.Enum):
        Standard = 'Standard'
        BroadSpectrum = 'Broad Spectrum'

    _MinTLMap = {
        _SensorType.Standard: 5,
        _SensorType.BroadSpectrum: 8
    }

    _CostMap = {
        _SensorType.Standard: 10,
        _SensorType.BroadSpectrum: 200
    }

    _FreeDefaultSuiteTypes = [_SensorType.Standard]

    def __init__(
            self,
            isDefaultSuite: bool,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Auditory Sensor',
            enumType=_AuditorySensorSlotOptionImpl._SensorType,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the sensor type.',            
            optionDefault=_AuditorySensorSlotOptionImpl._SensorType.Standard,                      
            minTLMap=_AuditorySensorSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)

        self._isDefaultSuite = isDefaultSuite

    def isZeroSlot(self) -> bool:
        return True        

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        speakerType = self._enumOption.value()
        assert(isinstance(speakerType, _AuditorySensorSlotOptionImpl._SensorType))

        if not self._isDefaultSuite or \
            (speakerType not in _AuditorySensorSlotOptionImpl._FreeDefaultSuiteTypes):
            cost = common.ScalarCalculation(
                value=_AuditorySensorSlotOptionImpl._CostMap[speakerType],
                name=f'{speakerType.value} {self.componentString()} Cost')

            step.setCredits(
                credits=construction.ConstantModifier(value=cost))
            
        if speakerType == _AuditorySensorSlotOptionImpl._SensorType.BroadSpectrum:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=robots.RobotAttributeId.HeightenedSenses))

class _EnvironmentalProcessorSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 10
    Cost: Cr10000
    Trait: Heightened Senses
    """
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Environmental Processor',
            minTL=10,
            constantCost=10000,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        
        
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.HeightenedSenses))

class _GeigerCounterSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 8
    Cost: Cr400
    """
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Geiger Counter',
            minTL=8,
            constantCost=400,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        
        
class _LightIntensifierSensorSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    Basic
    - Min TL: 7
    - Cost: Cr500
    Advanced
    - Min TL: 9
    - Cost: Cr1250
    - Trait: IR Vision
    """

    _MinTLMap = {
        _OptionLevel.Basic: 7,
        _OptionLevel.Advanced: 9
    }

    # Data Structure: Cost, Trait
    _DataMap = {
        _OptionLevel.Basic: (500, None),
        _OptionLevel.Advanced: (1250, robots.RobotAttributeId.IrVision)
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Light Intensifier Sensor',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the sensor type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_LightIntensifierSensorSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        
        
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        sensorType = self._enumOption.value()
        assert(isinstance(sensorType, _OptionLevel))

        cost, trait = _LightIntensifierSensorSlotOptionImpl._DataMap[sensorType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{sensorType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))        

        if trait:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=trait))
            
class _OlfactorySensorSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    Basic
    - Min TL: 8
    - Cost: Cr1000
    Improved
    - Min TL: 10
    - Cost: Cr3500
    - Trait: Heightened Senses
    Advanced
    - Min TL: 12
    - Cost: Cr10000
    - Trait: Heightened Senses
    """

    _MinTLMap = {
        _OptionLevel.Basic: 8,
        _OptionLevel.Improved: 10,
        _OptionLevel.Advanced: 12
    }

    # Data Structure: Cost, Trait
    _DataMap = {
        _OptionLevel.Basic: (1000, None),
        _OptionLevel.Improved: (3500, robots.RobotAttributeId.HeightenedSenses),
        _OptionLevel.Advanced: (10000, robots.RobotAttributeId.HeightenedSenses)
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Olfactory Sensor',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the sensor type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_OlfactorySensorSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        
        
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)

        sensorType = self._enumOption.value()
        assert(isinstance(sensorType, _OptionLevel))

        cost, trait = _OlfactorySensorSlotOptionImpl._DataMap[sensorType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{sensorType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))        

        if trait:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=trait))
            
class _PRISSensorSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 12
    Cost: Cr2000
    Trait: IR/UV Vision
    """

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='PRIS Sensor',
            minTL=12,
            constantCost=2000,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.IrUvVision))
        
class _ThermalSensorSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 6
    - Cost: Cr500
    - Trait: IR Vision
    """
    # TODO: According to p39 this is redundant if the robot has the TL 9 Light
    # Intensifier Sensor or PRIS Sensor. I'm not sure if it's worth the hassle
    # of adding that compatibility check

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Thermal Sensor',
            minTL=6,
            constantCost=500,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.IrVision))

class _VisualSpectrumSensorSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - 
    - Min TL: 7
    - Cost: Cr50 or free if Default Suite
    """
    def __init__(
            self,
            isDefaultSuite: bool,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Visual Spectrum Sensor',
            minTL=7,
            constantCost=None if isDefaultSuite else 50,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return True        

class _ActiveCamouflageSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 15
    Cost: Cr10000 * Base Slots
    Slots: 1
    Skill: Stealth 4
    Trait: Invisible
    Note: DM-4 to Recon and Electronics (sensors) checks to detect the robot
    """
    # TODO: Handle stealth skill
    # TODO: I think the DM-4 is the modifier for this component having the
    # Invisible trait. It means if I add a generic finalisation step to add
    # notes based on traits then this note will need removed as it will be a
    # duplicate rather than an additional -4

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Active Camouflage',
            minTL=15,
            perBaseSlotCost=10000,
            constantSlots=1,
            notes=['DM-4 to Recon and Electronics (sensors) checks to detect the robot'],
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False        
        
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(sequence, context, step)

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Invisible))
        
class _CorrosiveEnvironmentProtectionSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 9
    Cost: Cr600 * Base Slots
    Slots: 1
    """

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Corrosive Environment Protection',
            minTL=9,
            perBaseSlotCost=600,
            constantSlots=1,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False    
    
class _InsidiousEnvironmentProtectionSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 11
    Cost: Cr3000 * Base Slots
    Slots: 1
    """
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Insidious Environment Protection',
            minTL=11,
            perBaseSlotCost=3000,
            constantSlots=1,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False  
    
class _RadiationEnvironmentProtectionSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 7
    Cost: Cr600 * Base Slots * levels
    Slots: 1 per level 
    Trait: Rads +(TL * 50 * levels)
    Option: Number of levels (1 to infinity)
    """
    _PerBaseSlotCost = common.ScalarCalculation(
        value=600,
        name='Radiation Environment Protection Per Base Slot Cost')
    _RequiredSlots = common.ScalarCalculation(
        value=1,
        name='Radiation Environment Protection Required Slots')
    _BaseRadProtection = common.ScalarCalculation(
        value=+50,
        name='Radiation Environment Protection Base Rads Trait')

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Radiation Environment Protection',
            minTL=7,
            incompatibleTypes=incompatibleTypes)
        
        self._levelsOption = construction.IntegerOption(
            id='Levels',
            name='Levels',
            value=1,
            maxValue=100,
            minValue=1,
            description='Specify the number of levels of protection.')        
        
    def isZeroSlot(self) -> bool:
        return False
    
    def instanceString(self) -> str:
        levels: int = self._levelsOption.value()
        return f'{self.componentString()} x {levels}'

    def componentString(self) -> str:
        return self._componentString
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._levelsOption]

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        levels = common.ScalarCalculation(
            value=self._levelsOption.value(),
            name='Specified Levels')
        robotTL = common.ScalarCalculation(
            value=context.techLevel(),
            name='Robot TL')
        
        cost = common.Calculator.multiply(
            lhs=common.Calculator.multiply(
                lhs=_RadiationEnvironmentProtectionSlotOptionImpl._PerBaseSlotCost,
                rhs=context.baseSlots(sequence=sequence)),
            rhs=levels,
            name=f'{self.componentString()} Total Cost')
        step.setCredits(credits=construction.ConstantModifier(value=cost))

        slots = common.Calculator.multiply(
            lhs=_RadiationEnvironmentProtectionSlotOptionImpl._RequiredSlots,
            rhs=levels,
            name=f'{self.componentString()} Total Required Slots')
        step.setSlots(slots=construction.ConstantModifier(value=slots))

        rads = common.Calculator.multiply(
            lhs=common.Calculator.multiply(
                lhs=_RadiationEnvironmentProtectionSlotOptionImpl._BaseRadProtection,
                rhs=robotTL),
            rhs=levels,
            name=f'{self.componentString()} Total Rads Trait')
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Rads,
            modifier=construction.ConstantModifier(value=rads)))
        
class _SelfRepairingChassisSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    Min TL: 11
    Cost: Cr1000 * Base Slots
    Slots: 5% of Base Slots rounded up
    """
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Self-Repairing Chassis',
            minTL=11,
            perBaseSlotCost=1000,
            percentBaseSlots=5,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False 

class _SubmersibleEnvironmentProtectionSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    <ALL> (p42)
    - Option: Number of levels
    - Note: VTOL and aeroplane locomotion can't be used while submerged
    - Note: Locomotion other than aquatic suffers an Agility -2 modifier while submerged
    Basic
    - Min TL: 4
    - Cost: Cr200 * Base Slots * levels
    - Slots: (5% of Base Slots * levels) rounded up
    - Note: Safe Depth (50m * levels)
    Improved
    - Min TL: 6
    - Cost: Cr400 * Base Slots * levels
    - Slots: (2% of Base Slots * levels) rounded up
    - Note: Safe Depth (200m * levels)
    Enhanced
    - Min TL: 9
    - Cost: Cr800 * Base Slots * levels
    - Slots: (2% of Base Slots * levels) rounded up
    - Note: Safe Depth (600m * levels)
    Advanced
    - Min TL: 12
    - Cost: Cr1000 * Base Slots * levels
    - Slots: (2% of Base Slots * levels) rounded up
    - Note: Safe Depth (2000m * levels)
    Superior
    - Min TL: 15
    - Cost: Cr2000 * Base Slots * levels
    - Slots: (2% of Base Slots * levels) rounded up
    - Note: Safe Depth (4000m * levels)
    """

    _MinTLMap = {
        _OptionLevel.Basic: 4,
        _OptionLevel.Improved: 6,
        _OptionLevel.Enhanced: 9,
        _OptionLevel.Advanced: 12,
        _OptionLevel.Superior: 15,
    }

    # Data Structure: Cost Per Base Slot, Base Slot Percentage, Safe Depth
    _DataMap = {
        _OptionLevel.Basic: (200, 5, 50),
        _OptionLevel.Improved: (400, 2, 200),
        _OptionLevel.Improved: (800, 2, 600),
        _OptionLevel.Advanced: (1000, 2, 2000),
        _OptionLevel.Superior: (2000, 2, 4000)
    }

    _UnusableLocomotions = [
        robots.AeroplanePrimaryLocomotion,
        robots.VTOLPrimaryLocomotion,
        robots.VTOLSecondaryLocomotion
    ]

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Submersible Environment Protection',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the protection type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_SubmersibleEnvironmentProtectionSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
        self._levelsOption = construction.IntegerOption(
            id='Levels',
            name='Levels',
            value=1,
            maxValue=1, # Set in updateOptions
            minValue=1,
            description='Specify the number of levels of protection.')           
        
    def isZeroSlot(self) -> bool:
        return False
    
    def instanceString(self) -> str:
        levels: int = self._levelsOption.value()
        return f'{self.componentString()} x {levels}'    
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._levelsOption)
        return options
    
    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        super().updateOptions(sequence, context)

        protectionType = self._enumOption.value()
        assert(isinstance(protectionType, _OptionLevel))

        _, percentageSlots, _ = \
            _SubmersibleEnvironmentProtectionSlotOptionImpl._DataMap[protectionType]
        
        maxLevels = math.floor(100 / percentageSlots)
        self._levelsOption.setMax(maxLevels)

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        levels = common.ScalarCalculation(
            value=self._levelsOption.value(),
            name='Specified Levels')

        protectionType = self._enumOption.value()
        assert(isinstance(protectionType, _OptionLevel))

        perSlotCost, percentageSlots, maxDepth = \
            _SubmersibleEnvironmentProtectionSlotOptionImpl._DataMap[protectionType]
        
        baseString = f'{protectionType.value} {self.componentString()}'
        
        if perSlotCost:
            perSlotCost = common.ScalarCalculation(
                value=perSlotCost,
                name=f'{baseString} Per Base Slot Cost')
            totalCost = common.Calculator.multiply(
                lhs=common.Calculator.multiply(
                    lhs=perSlotCost,
                    rhs=context.baseSlots(sequence=sequence)),
                rhs=levels,
                name=f'{baseString} Total Cost')
            step.setCredits(
                credits=construction.ConstantModifier(value=totalCost))

        if percentageSlots:
            percentageSlots = common.ScalarCalculation(
                value=percentageSlots,
                name=f'{baseString} Base Slot Percentage')
            totalSlots = common.Calculator.ceil(
                value=common.Calculator.multiply(
                    lhs=common.Calculator.takePercentage(
                        value=context.baseSlots(sequence=sequence),
                        percentage=percentageSlots),
                    rhs=levels),
                name=f'{baseString} Total Required Slots')
            step.setSlots(
                slots=construction.ConstantModifier(value=totalSlots))            

        maxDepth *= levels.value()
        step.addNote(note=f'Safe depth for the robot is {maxDepth}m')

        locomotions = context.findComponents(
            componentType=robots.LocomotionInterface,
            sequence=sequence)
        unusableLocomotions = []
        modifiedLocomotions = []
        for locomotion in locomotions:
            locomotionType = type(locomotion)
            if locomotionType == robots.NoPrimaryLocomotion:
                continue # Ignore no motion
            if locomotionType in _SubmersibleEnvironmentProtectionSlotOptionImpl._UnusableLocomotions:
                locomotionName = locomotion.componentString()
                if locomotionName not in unusableLocomotions:
                    unusableLocomotions.append(locomotionName)
            elif locomotionType != robots.AquaticPrimaryLocomotion and \
                locomotionType != robots.AquaticSecondaryLocomotion:
                locomotionName = locomotion.componentString()
                if locomotionName not in modifiedLocomotions:
                    modifiedLocomotions.append(locomotionName)
        if unusableLocomotions:
            names = common.humanFriendlyListString(unusableLocomotions)
            step.addNote(note=f'{names} locomotion can\'t be used while submerged')
        if modifiedLocomotions:
            names = common.humanFriendlyListString(modifiedLocomotions)
            step.addNote(note=f'{names} locomotion suffer Agility -2 while submerged')

class _CleaningEquipmentSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    Min TL: 5
    """

    def __init__(
            self,
            componentString: str,
            # Data Structure: Cost, Slots, Square Meters per Hour
            dataMap: typing.Mapping[_OptionSize, typing.Tuple[int, int, int]],
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTL=5,
            enumType=_OptionSize,
            optionId='Size',
            optionName='Size',
            optionDescription='Specify the cleaning equipment size.',            
            optionDefault=_OptionSize.Small,                      
            incompatibleTypes=incompatibleTypes)
        
        self._dataMap = dataMap
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        size = self._enumOption.value()
        assert(isinstance(size, _OptionSize))

        cost, slots, speed = self._dataMap[size]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{size.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{size.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        step.addNote(f'Can clean {speed} square meters per hour')

class _DomesticCleaningEquipmentSlotOptionImpl(_CleaningEquipmentSlotOptionImpl):
    """
    Small
    - Min TL: 5
    - Cost: Cr100
    - Slots: 1
    - Note: Can clean 10 square meters per hour
    Medium
    - Min TL: 5
    - Cost: Cr1000
    - Slots: 4
    - Note: Can clean 50 square meters per hour
    Large
    - Min TL: 5
    - Cost: Cr5000
    - Slots: 8
    - Note: Can clean 120 square meters per hour
    """
    # Data Structure: Cost, Slots, Square Meters per Hour
    _DataMap = {
        _OptionSize.Small: (100, 1, 10),
        _OptionSize.Medium: (1000, 4, 50),
        _OptionSize.Large: (5000, 8, 120)
    }
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Domestic Cleaning Equipment',
            dataMap=_DomesticCleaningEquipmentSlotOptionImpl._DataMap,                  
            incompatibleTypes=incompatibleTypes)
        
class _IndustrialCleaningEquipmentSlotOptionImpl(_CleaningEquipmentSlotOptionImpl):
    """
    Small
    - Min TL: 5
    - Cost: Cr500
    - Slots: 2
    - Note: Can clean 10 square meters per hour
    Medium
    - Min TL: 5
    - Cost: Cr5000
    - Slots: 8
    - Note: Can clean 50 square meters per hour
    Large
    - Min TL: 5
    - Cost: Cr20000
    - Slots: 16
    - Note: Can clean 120 square meters per hour
    """
    # Data Structure: Cost, Slots, Square Meters per Hour
    _DataMap = {
        _OptionSize.Small: (500, 2, 10),
        _OptionSize.Medium: (5000, 8, 50),
        _OptionSize.Large: (20000, 16, 120)
    }
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Industrial Cleaning Equipment',
            dataMap=_IndustrialCleaningEquipmentSlotOptionImpl._DataMap,                  
            incompatibleTypes=incompatibleTypes)
        
class _HighFidelitySoundSystemSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    Basic
    - Min TL: 6
    - Cost: Cr1500
    - Slots: 4
    Improved
    - Min TL: 8
    - Cost: Cr2500
    - Slots: 3
    Enhanced
    - Min TL: 11
    - Cost: Cr4000
    - Slots: 3
    Advanced
    - Min TL: 12
    - Cost: Cr5000
    - Slots: 2
    """

    _MinTLMap = {
        _OptionLevel.Basic: 6,
        _OptionLevel.Improved: 8,
        _OptionLevel.Enhanced: 11,
        _OptionLevel.Advanced: 12
    }

    # Data Structure: Cost, Slots
    _DataMap = {
        _OptionLevel.Basic: (1500, 4),
        _OptionLevel.Improved: (2500, 3),
        _OptionLevel.Enhanced: (4000, 3),
        _OptionLevel.Advanced: (5000, 2)
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='High Fidelity Sound System',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_HighFidelitySoundSystemSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        systemType = self._enumOption.value()
        assert(isinstance(systemType, _OptionLevel))

        cost, slots = _HighFidelitySoundSystemSlotOptionImpl._DataMap[systemType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{systemType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{systemType.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))

class _RoboticDroneControllerSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Option: Biologically-Controlled check box
            - When checked the controller is limited to 1 drone but the Electronics (remote ops) level isn't limited
        - Requirement: The robot must have a transceiver
        - Requirement: The controlling robot must have a Electronics (remote ops) skill
    - Basic
        - Min TL: 7
        - Cost: Cr2000
        - Slots: 2
        - Note: Can control a max of 1 drone
        - Note: Electronics (remote ops) skill is limited to 0 when using Robotic Drone Controller
    - Improved
        - Min TL: 9
        - Cost: Cr10000
        - Slots: 1
        - Note: Can control a max of 2 drone
        - Note: Electronics (remote ops) skill is limited to 1 when using Robotic Drone Controller
    - Enhanced
        - Min TL: 10
        - Cost: Cr20000
        - Slots: 1
        - Note: Can control a max of 4 drone
        - Note: Electronics (remote ops) skill is limited to 2 when using Robotic Drone Controller
    - Advanced
        - Min TL: 11
        - Cost: Cr50000
        - Slots: 1
        - Note: Can control a max of 8 drone
        - Note: Electronics (remote ops) skill is limited to 3 when using Robotic Drone Controller
    """
    # TODO: Handle skill requirements
    # - Best way I can think to handle this is a finalisation step that adds a
    # warning if the robot doesn't have the skill

    _MinTLMap = {
        _OptionLevel.Basic: 7,
        _OptionLevel.Improved: 9,
        _OptionLevel.Enhanced: 10,
        _OptionLevel.Advanced: 11
    }

    # Data Structure: Cost, Slots, Max Drones, Max Skill
    _DataMap = {
        _OptionLevel.Basic: (2000, 2, 1, 0),
        _OptionLevel.Improved: (10000, 1, 2, 1),
        _OptionLevel.Enhanced: (20000, 1, 4, 2),
        _OptionLevel.Advanced: (50000, 1, 8, 3)
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Robotic Drone Controller',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_RoboticDroneControllerSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
        self._biologicalOption = construction.BooleanOption(
            id='BiologicallyControlled',
            name='Biologically-Controlled',
            value=False,
            description='Specify if the \'biologically-controlled\' variant')
        
    def isZeroSlot(self) -> bool:
        return False
    
    def instanceString(self) -> str:
        value: enum.Enum = self._enumOption.value()
        info = value.value

        if self._biologicalOption.value():
            info += ', Biologically-Controlled'

        return f'{self.componentString()} ({info})'
    
    def isCompatible(self, sequence: str, context: robots.RobotContext) -> bool:
        if not super().isCompatible(sequence, context):
            return False

        if context.findFirstComponent(
            componentType=TransceiverDefaultSuiteOption,
            sequence=sequence):
            return True
        
        if context.findFirstComponent(
            componentType=TransceiverSlotOption,
            sequence=sequence):
            return True        

        return False # No transceiver
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._biologicalOption)
        return options

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        controllerType = self._enumOption.value()
        assert(isinstance(controllerType, _OptionLevel))

        cost, slots, maxDrones, maxSkill = _RoboticDroneControllerSlotOptionImpl._DataMap[controllerType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{controllerType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{controllerType.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        if self._biologicalOption.value():
            maxDrones = 1
            maxSkill = None

        step.addNote(f'Interface can control at a maximum of {maxDrones} drones')
        if maxSkill != None:
            step.addNote(f'The robots Electronics (remote-ops) skill is limited to {maxSkill} when using the interface')

class _SatelliteUplinkSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 6
    - Cost: Cr1000
    - Slots: 2
    - Requirement: Requires a Transceiver with at least 500km range
    """
    # NOTE: The way this compatibility check works is worthy of note. It is
    # checking for the existence of default suite or slot option transmitter
    # with a range over a certain value. This only works because it's only
    # possible to get a Satellite Uplink as a slot cost option and not a
    # default slot option. The problem with doing it as a default slot option
    # would be that it would be possible for the transmitter to be a slot cost
    # option and, when compatibility of this component is checked when loading,
    # the transmitter component would exist but wouldn't have had it's range
    # option set yet so this component would be found to be incompatible.

    _MinTransceiverRange = 500

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Satellite Uplink',
            minTL=6,
            constantCost=1000,
            constantSlots=2,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False 

    def isCompatible(self, sequence: str, context: robots.RobotContext) -> bool:
        if not super().isCompatible(sequence, context):
            return False
    
        transceivers = []
        transceivers.extend(context.findComponents(
            componentType=TransceiverDefaultSuiteOption,
            sequence=sequence))
        transceivers.extend(context.findComponents(
            componentType=TransceiverSlotOption,
            sequence=sequence))
        hasRequiredRange = False
        for transceiver in transceivers:
            assert(isinstance(transceiver, TransceiverDefaultSuiteOption) or isinstance(transceiver, TransceiverSlotOption))
            if transceiver.range() >= _SatelliteUplinkSlotOptionImpl._MinTransceiverRange:
                hasRequiredRange = True
                break

        return hasRequiredRange

class _SwarmControllerSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Requirement: The robot must have a Wireless Data Link
        - Requirement: The controlling robot must have a Electronics
        (remote ops) skill
            - Best way I can think to handle this is a finalisation step that
            adds a warning if the robot doesn't have the skill
    - Basic
        - Min TL: 8
        - Cost: Cr10000
        - Slots: 3
        - Note: Swarms are limited to 1 task with a maximum complexity of Average (8+)
        - Note: Electronics (remote ops) skill is limited to 0 when using Swarm Controller
    - Improved
        - Min TL: 10
        - Cost: Cr20000
        - Slots: 2
        - Note: Swarms are limited to 2 tasks with a maximum complexity of Difficult (10+)
        - Note: Electronics (remote ops) skill is limited to 1 when using Swarm Controller  
    - Enhanced
        - Min TL: 12
        - Cost: Cr50000
        - Slots: 1
        - Note: Swarms are limited to 3 tasks with a maximum complexity of Very Difficult (12+)
        - Note: Electronics (remote ops) skill is limited to 2 when using Swarm Controller  
    - Advanced
        - Min TL: 14
        - Cost: Cr100000
        - Slots: 1
        - Note: Swarms are limited to 4 tasks with a maximum complexity of Formidable (14+)
        - Note: Electronics (remote ops) skill is limited to 3 when using Swarm Controller 
    """
    # TODO: Handle skill requirements
    # - Best way I can think to handle this is a finalisation step that adds a
    # warning if the robot doesn't have the skill

    _MinTLMap = {
        _OptionLevel.Basic: 8,
        _OptionLevel.Improved: 10,
        _OptionLevel.Enhanced: 12,
        _OptionLevel.Advanced: 14
    }

    # Data Structure: Cost, Slots, Max Tasks, Max Complexity, Max Skill
    _DataMap = {
        _OptionLevel.Basic: (10000, 3, 1, 'Average (8+)', 0),
        _OptionLevel.Improved: (20000, 2, 2, 'Difficult (10+)', 1),
        _OptionLevel.Enhanced: (50000, 1, 3, 'Difficult (12+)', 2),
        _OptionLevel.Advanced: (100000, 1, 4, 'Formidable (14+)', 3)
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Swarm Controller',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_SwarmControllerSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False
    
    def isCompatible(self, sequence: str, context: robots.RobotContext) -> bool:
        if not super().isCompatible(sequence, context):
            return False

        if context.findFirstComponent(
            componentType=WirelessDataLinkDefaultSuiteOption,
            sequence=sequence):
            return True
        
        if context.findFirstComponent(
            componentType=WirelessDataLinkSlotOption,
            sequence=sequence):
            return True        

        return False # No wireless data link

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        controllerType = self._enumOption.value()
        assert(isinstance(controllerType, _OptionLevel))

        cost, slots, maxTasks, maxComplexity, maxSkill = _SwarmControllerSlotOptionImpl._DataMap[controllerType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{controllerType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{controllerType.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        step.addNote(f'Swarms are limited to {maxTasks} tasks with a maximum complexity of {maxComplexity}')
        step.addNote(f'The robots Electronics (remote-ops) skill is limited to {maxSkill} when using the controller')


class _TightbeamCommunicatorSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 8
    - Cost: Cr2000
    - Slots: 1
    - Note: Range is 5,000km, when combined with a Satellite Uplink range is 500,000km
    """
    # NOTE: The way the note is handled is worth noting. It works by checking
    # for a component that is in the same stage as it is. This is generally a
    # bad idea as construction ordering could lead to non-deterministic
    # behaviour. The only reason it's ok in this situation is it's only
    # concerned with the existence of the component and that only affecting a
    # note (and notes have no affect on later construction). In this situation
    # it means the note may be inaccurate while the robot is being loaded but
    # will be correct at the point it's fully loaded.    

    _StandardRangeNote = 'Range is 5,000km'
    _SatelliteRangeNote = 'Range is 5,000km or 500,000km if using the Satellite Uplink'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Tightbeam Communicator',
            minTL=8,
            constantCost=2000,
            constantSlots=1,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False 
    
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        # NOTE: See note at top of class about why checking a component in the
        # same stage is safe in this instance but may not be in others. This
        # approach shouldn't be replicated without thought
        satelliteUplink = context.findFirstComponent(
            componentType=SatelliteUplinkSlotOption,
            sequence=sequence)
        if satelliteUplink:
            step.addNote(_TightbeamCommunicatorSlotOptionImpl._SatelliteRangeNote)
        else:
            step.addNote(_TightbeamCommunicatorSlotOptionImpl._StandardRangeNote)

# NOTE: The Medical Chamber component has multiple steps so it inherits directly
# from _SlotOptionImpl rather than  _SingleStepSlotOptionImpl
class _MedicalChamberSlotOptionImpl(_SlotOptionImpl):
    """
    - Min TL: 8
    - Cost: Cr200 per slot allocated to the chamber
    - Slots: The number of slots allocated to the chamber
    - Option: Spin box to select the number of slots to allocate to chamber
    (range: 1 to Base Slots)
    - Option: Combo box to _optionally_ select Berth option
        - Cryoberth (basic)
            - Min TL: 10
            - Cost: Cr20000
            - Slots: 8
        - Cryoberth (improved)
            - Min TL: 12
            - Cost: Cr20000
            - Slots 8
            - Note: DM+1 to freezing and revival checks
        - Low berth (basic)
            - Min TL: 10
            - Cost: Cr20000
            - Slots: 8
        - Low berth (improved)
            - Min TL: 12
            - Cost: Cr20000
            - Slots: 8
            - Note: DM+1 to freezing and revival checks
    - Option: Combo box to _optionally_ select Nanobot option
        - Applicator
            - Min TL: 13
            - Cost: Cr100000
            - Slots: 4
        - Applicator & Generator
            - Min TL: 13
            - Cost: Cr200000
            - Slots: 8
    - Option: Check box for Reanimation
        - Min TL: 14
        - Cost: Cr900000
        - Slots: 8
    - Option: Spin box to select number of species specific addons (min: 0)
        - Min TL: 10
        - Cost: Cr10000 per addon
        - Slots: 4 per addon
        - IMPORTANT: Whatever the count is set to that number of string options
        should be created so the user can enter the name of the species it's for
    - Requirement: A robot should have at least one manipulator of Size 3 or
    greater
    - Requirement: A Medical Chamber adds +1 to the Maximum Skill level supported
    by a Medkit option
    """
    # NOTE: The requirement regarding the Medikit Maximum Skill  is handled by
    # the Medikit implementation    
    # NOTE: Regarding a medical chamber the rules say "It can form the basis of
    # an ambulance robot or custom autodoc" (p46) and "Cryoberths, low berths
    # and autodocs are designed with the physiology of a specific species in
    # mind" (p47). This means when used an an ambulance robot the species
    # doesn't need to be specified. The most straight forward away I can see to
    # handle this is to always display the primary species option but have a
    # tooltip that explains in what cases it should be filled in.
    # TODO: Handle Requirement on manipulator size

    class _NanobotType(enum.Enum):
        Applicator = 'Applicator'
        ApplicatorGenerator = 'Applicator & Generator'

    _CostPerSlot = common.ScalarCalculation(
        value=200,
        name='Medical Chamber Cost Per Slot')

    _BerthMinTLMap = {
        _OptionLevel.Basic: 10,
        _OptionLevel.Improved: 12
    }

    _CryoberthCost = common.ScalarCalculation(
        value=20000,
        name='Medical Chamber Cryoberth Addon Cost')
    _CryoberthSlots = common.ScalarCalculation(
        value=8,
        name='Medical Chamber Cryoberth Addon Required Slots')
    _LowBerthCost = common.ScalarCalculation(
        value=20000,
        name='Medical Chamber Low-berth Addon Cost')
    _LowBerthSlots = common.ScalarCalculation(
        value=8,
        name='Medical Chamber Low-berth Addon Required Slots') 
    _ImprovedBerthNote = 'DM+1 to freezing and revival checks'   

    _NanobotMinTL = 13
    # Data Structure: Cost, Slots
    _NanobotDataMap = {
        _NanobotType.Applicator: (100000, 4),
        _NanobotType.ApplicatorGenerator: (200000, 8),
    }

    _ReanimationMinTL = 14
    _ReanimationCost = common.ScalarCalculation(
        value=900000,
        name='Medical Chamber Reanimation Addon Cost')
    _ReanimationSlots = common.ScalarCalculation(
        value=8,
        name='Medical Chamber Reanimation Addon Required Slots')    

    _SpeciesAddonMinTL = 10
    _SpeciesAddonCost = common.ScalarCalculation(
        value=10000,
        name='Medical Chamber Species Addon Cost')
    _SpeciesAddonSlots = common.ScalarCalculation(
        value=4,
        name='Medical Chamber Species Addon Required Slots')
    
    _PrimarySpeciesOptionDesc = \
    """
    <p>Specify the primary species the Medical Chamber is designed for</p>
    <p>The rules are aren't completely clear if a Medical Chamber needs the
    primary species it's designed for specified in all cases. They say<br>
    <br>
    "It can form the basis of an ambulance robot or custom autodoc" (p46)<br>
    and<br>
    "Cryoberths, low berths and autodocs are designed with the physiology of
    a specific species in mind" (p47)<br>
    <br>
    This would suggest that in some cases such as ambulance robot you don't
    need to specify the primary species the Medical Chamber is designed for.
    </p>
    """

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Medical Chamber',
            minTL=8,
            incompatibleTypes=incompatibleTypes)
        
        self._slotsOption = construction.IntegerOption(
            id='Slots',
            name='Slots',
            value=1,
            maxValue=1, # Set in updateOptions
            minValue=1,
            description='Specify the number of slots to allocate to the Medical Chamber.')
        
        self._primarySpeciesOption = construction.StringOption(
            id='PrimarySpecies',
            name='Species',
            value='',
            options=_PredefinedSpecies,
            description=_MedicalChamberSlotOptionImpl._PrimarySpeciesOptionDesc)
        
        self._cryoBerthOption = construction.EnumOption(
            id='CryoBerth',
            name='Cryo Berth',
            type=_OptionLevel,
            value=None,
            isOptional=True,
            description='Add a Cryo Berth to the Medical Chamber')
        
        self._lowBerthOption = construction.EnumOption(
            id='LowBerth',
            name='Low-berth',
            type=_OptionLevel,
            value=None,
            isOptional=True,
            description='Add a Low-berth to the Medical Chamber')
        
        self._nanobotsOption = construction.EnumOption(
            id='Nanobots',
            name='Nanobots',
            type=_MedicalChamberSlotOptionImpl._NanobotType,
            value=None,
            isOptional=True,
            description='Add a Nanobots to the Medical Chamber')        

        self._reanimationOption = construction.BooleanOption(
            id='Reanimation',
            name='Reanimation',
            value=False,
            description='Add a Reanimation to the Medical Chamber')
        
        self._speciesAddonCountOption = construction.IntegerOption(
            id='SpeciesAddons',
            name='Species-specific addons',
            value=0,
            maxValue=10,
            minValue=0,
            description='Specify the number of species-specific addons to add to the Medical Chamber.')
        self._speciesNameOptionList: typing.List[construction.StringOption] = []

    def instanceString(self) -> str:
        if self._primarySpeciesOption.isEnabled():
            primarySpecies = self._primarySpeciesOption.value()
            if primarySpecies:
                return f'{super().instanceString()} ({primarySpecies})'
        return super().instanceString()
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._slotsOption)
        options.append(self._primarySpeciesOption)

        if self._cryoBerthOption.isEnabled():
            options.append(self._cryoBerthOption)
        
        if self._lowBerthOption.isEnabled():
            options.append(self._lowBerthOption)

        if self._nanobotsOption.isEnabled():
            options.append(self._nanobotsOption)

        if self._reanimationOption.isEnabled():
            options.append(self._reanimationOption)

        if self._speciesAddonCountOption.isEnabled():
            options.append(self._speciesAddonCountOption)

        options.extend(self._speciesNameOptionList)

        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        super().updateOptions(sequence, context)

        robotTL = context.techLevel()

        baseSlots = context.baseSlots(sequence=sequence)
        self._slotsOption.setMax(value=baseSlots.value())
        
        berthOptions = []
        for berthType, minTL in _MedicalChamberSlotOptionImpl._BerthMinTLMap.items():
            if robotTL >= minTL:
                berthOptions.append(berthType)

        self._cryoBerthOption.setEnabled(not not berthOptions)
        self._cryoBerthOption.setOptions(options=berthOptions)

        self._lowBerthOption.setEnabled(not not berthOptions)
        self._lowBerthOption.setOptions(options=berthOptions)

        self._nanobotsOption.setEnabled(
            enabled=robotTL >= _MedicalChamberSlotOptionImpl._NanobotMinTL)        

        self._reanimationOption.setEnabled(
            enabled=robotTL >= _MedicalChamberSlotOptionImpl._ReanimationMinTL)
        
        if robotTL >= _MedicalChamberSlotOptionImpl._SpeciesAddonMinTL:
            self._speciesAddonCountOption.setEnabled(True)
            
            addonCount = self._speciesAddonCountOption.value()
            while len(self._speciesNameOptionList) > addonCount:
                self._speciesNameOptionList.pop()
            while len(self._speciesNameOptionList) < addonCount:
                addonIndex = len(self._speciesNameOptionList) + 1 # 1 based for user
                self._speciesNameOptionList.append(
                    construction.StringOption(
                        id=f'SpeciesAddon{addonIndex}',
                        name=f'Species {addonIndex}',
                        value='',
                        options=_PredefinedSpecies,
                        description='Specify the species that addon {addonIndex} gives support for.'))                    
        else:
            self._speciesAddonCountOption.setEnabled(False)
            self._speciesNameOptionList = []

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext,
            typeString: str
            ) -> None:
        self._createPrimaryStep(
            sequence=sequence,
            context=context,
            typeString=typeString)
        
        if self._cryoBerthOption.isEnabled() and \
                self._cryoBerthOption.value() != None:
            self._createCryoberthStep(
                sequence=sequence,
                context=context,
                typeString=typeString)
            
        if self._lowBerthOption.isEnabled() and \
                self._lowBerthOption.value() != None:
            self._createLowBerthStep(
                sequence=sequence,
                context=context,
                typeString=typeString)
            
        if self._nanobotsOption.isEnabled() and \
                self._nanobotsOption.value():
            self._createNanobotStep(
                sequence=sequence,
                context=context,
                typeString=typeString)
            
        if self._reanimationOption.isEnabled() and \
                self._reanimationOption.value():
            self._createReanimationStep(
                sequence=sequence,
                context=context,
                typeString=typeString)

        if self._speciesAddonCountOption.isEnabled() and \
                self._speciesAddonCountOption.value():
            self._createSpeciesSteps(
                sequence=sequence,
                context=context,
                typeString=typeString)

    def _createPrimaryStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            typeString: str
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=typeString)
        
        slots = common.ScalarCalculation(
            value=self._slotsOption.value(),
            name='Requested Chamber Slots')
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
       
        cost = common.Calculator.multiply(
            lhs=slots,
            rhs=_MedicalChamberSlotOptionImpl._CostPerSlot,
            name=f'{self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
                            
        context.applyStep(
            sequence=sequence,
            step=step)

    def _createCryoberthStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            typeString: str
            ) -> None:
        optionType = self._cryoBerthOption.value()
        assert(isinstance(optionType, _OptionLevel))

        step = robots.RobotStep(
            name=f'{self.componentString()} {optionType.value} Cryoberth',
            type=typeString)
        step.setCredits(credits=construction.ConstantModifier(
            value=_MedicalChamberSlotOptionImpl._CryoberthCost))        
        step.setSlots(slots=construction.ConstantModifier(
            value=_MedicalChamberSlotOptionImpl._CryoberthSlots))
        
        if optionType == _OptionLevel.Improved:
            step.addNote(_MedicalChamberSlotOptionImpl._ImprovedBerthNote)
                            
        context.applyStep(
            sequence=sequence,
            step=step)    

    def _createLowBerthStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            typeString: str
            ) -> None:
        optionType = self._lowBerthOption.value()
        assert(isinstance(optionType, _OptionLevel))

        step = robots.RobotStep(
            name=f'{self.componentString()} {optionType.value} Low-berth',
            type=typeString)
        step.setCredits(credits=construction.ConstantModifier(
            value=_MedicalChamberSlotOptionImpl._LowBerthCost))        
        step.setSlots(slots=construction.ConstantModifier(
            value=_MedicalChamberSlotOptionImpl._LowBerthSlots))
        
        if optionType == _OptionLevel.Improved:
            step.addNote(_MedicalChamberSlotOptionImpl._ImprovedBerthNote)
                            
        context.applyStep(
            sequence=sequence,
            step=step)
        
    def _createNanobotStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            typeString: str
            ) -> None:
        optionType = self._nanobotsOption.value()
        assert(isinstance(optionType, _MedicalChamberSlotOptionImpl._NanobotType))

        componentString = f'{self.componentString()} Nanobot {optionType.value}'

        step = robots.RobotStep(
            name=componentString,
            type=typeString)
        
        cost, slots = _MedicalChamberSlotOptionImpl._NanobotDataMap[optionType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{componentString} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{componentString} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
                            
        context.applyStep(
            sequence=sequence,
            step=step)
        
    def _createReanimationStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            typeString: str
            ) -> None:
        step = robots.RobotStep(
            name=f'{self.componentString()} Reanimation',
            type=typeString)
        step.setCredits(credits=construction.ConstantModifier(
            value=_MedicalChamberSlotOptionImpl._ReanimationCost))        
        step.setSlots(slots=construction.ConstantModifier(
            value=_MedicalChamberSlotOptionImpl._ReanimationSlots))
        
        context.applyStep(
            sequence=sequence,
            step=step)
        
    def _createSpeciesSteps(
            self,
            sequence: str,
            context: robots.RobotContext,
            typeString: str
            ) -> None:
        for index, speciesOption in enumerate(self._speciesNameOptionList):
            componentString = f'{self.componentString()} Species Addon {index + 1}'
            if speciesOption.value():
                componentString += f' ({speciesOption.value()})'
            step = robots.RobotStep(
                name=componentString,
                type=typeString)

            step.setCredits(credits=construction.ConstantModifier(
                value=_MedicalChamberSlotOptionImpl._SpeciesAddonCost))        
            step.setSlots(slots=construction.ConstantModifier(
                value=_MedicalChamberSlotOptionImpl._SpeciesAddonSlots))
            
            context.applyStep(
                sequence=sequence,
                step=step)

class _MedkitSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <All>
        - Requirement: The Max Skill level is increased by 1 if the robot has a
    - Medical Chamber slot cost option
        - Note: Replenishing Medikit costs Cr500
    - Medikit (basic)
        - Min TL: 8
        - Cost: Cr1000
        - Slots: 1
        - Note: Medic skill is limited to 0 when using Medikit
    - Medikit (improved)
        - Min TL: 10
        - Cost: Cr1500
        - Slots: 1
        - Note: Medic skill is limited to 1 when using Medikit            
    - Medikit (enhanced)
        - Min TL: 12
        - Cost: Cr5000
        - Slots: 1
        - Note: Medic skill is limited to 2 when using Medikit
    - Medikit (advanced)
        - Min TL: 14
        - Cost: Cr10000
        - Slots: 1
        - Note: Medic skill is limited to 3 when using Medikit
    """
    # NOTE: The way the Max Skill increase due to also having a Medical Changer
    # is handled is worth noting. It works by checking for a component that is
    # in the same stage as it is. This is generally a bad idea as construction
    # ordering could lead to non-deterministic behaviour. The only reason it's
    # ok in this situation is it's only concerned with the existence of the
    # component and that only affecting a note (and notes have no affect on
    # later construction). In this situation it means the note may be inaccurate
    # while the robot is being loaded but will be correct at the point it's
    # fully loaded.

    _MinTLMap = {
        _OptionLevel.Basic: 8,
        _OptionLevel.Improved: 10,
        _OptionLevel.Enhanced: 12,
        _OptionLevel.Advanced: 14
    }

    # Data Structure: Cost, Slots, Max Skill
    _DataMap = {
        _OptionLevel.Basic: (1000, 1, 0),
        _OptionLevel.Improved: (1500, 1, 1),
        _OptionLevel.Enhanced: (5000, 1, 2),
        _OptionLevel.Advanced: (10000, 1, 3)
    }

    _ReplenishmentNote = 'Replenishing the Medikit costs Cr500'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Medkit',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_MedkitSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        medkitType = self._enumOption.value()
        assert(isinstance(medkitType, _OptionLevel))

        cost, slots, maxSkill = _MedkitSlotOptionImpl._DataMap[medkitType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{medkitType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{medkitType.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        # NOTE: See note at top of class about why checking a component in the
        # same stage is safe in this instance but may not be in others. This
        # approach shouldn't be replicated without thought
        medicalChamber = context.findFirstComponent(
            componentType=MedicalChamberSlotOption,
            sequence=sequence)
        if medicalChamber:
            maxSkill += 1
        step.addNote(f'Medic skill is limited to {maxSkill} when using Medikit')
        
        step.addNote(_MedkitSlotOptionImpl._ReplenishmentNote)      

class _AgriculturalEquipmentSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Min TL: 5
    - Small
        - Cost: Cr100
        - Slots: 1
        - Note: Can process 20 square meters per hour
    - Medium
        - Cost: Cr1000 * levels
        - Slots: 4 * levels
        - Note: Can process 100 square meters per hour
    - Large
        - Cost: Cr10000 * levels
        - Slots: 16 * levels
        - Note: Can process 500 square meters per hour
    """
    # NOTE: The rules say multiple agricultural options can be added to cover a
    # greater area. This is handled by the component rather than the impl, it
    # does this by allowing multiple instances of this component type be added.
    # This has the added benefit that the player could add different sized
    # agricultural options.

    # Data Structure: Cost, Slots, Square Meters per Hour
    _DataMap = {
        _OptionSize.Small: (100, 1, 20),
        _OptionSize.Medium: (1000, 4, 100),
        _OptionSize.Large: (10000, 16, 500)
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Agricultural Equipment',
            minTL=5,
            enumType=_OptionSize,
            optionId='Size',
            optionName='Size',
            optionDescription='Specify the equipment size.',            
            optionDefault=_OptionSize.Small,                      
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        size = self._enumOption.value()
        assert(isinstance(size, _OptionSize))

        cost, slots, speed = _AgriculturalEquipmentSlotOptionImpl._DataMap[size]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{size.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{size.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        step.addNote(f'Can process {speed} square meters per hour')
        
class _AutobarSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - Basic
        - Min TL: 8
        - Cost: Cr500
        - Slots: 2
        - Note: Steward and Profession (bartender) skills is limited to 0 when using Autobar
        - Note: Replenishing the Autobar costs Cr250
    - Improved
        - Min TL: 9
        - Cost: Cr1000
        - Slots: 2
        - Note: Steward and Profession (bartender) skills are limited to 1 when using Autobar
        - Note: Replenishing the Autobar costs Cr500
    - Enhanced
        - Min TL: 10
        - Cost: Cr2000
        - Slots: 2
        - Note: Steward and Profession (bartender) skills are limited to 2 when using Autobar
        - Note: Replenishing the Autobar costs Cr1000
    - Advanced
        - Min TL: 11
        - Cost: Cr5000
        - Slots: 2
        - Note: Steward and Profession (bartender) skills are limited to 3 when using Autobar
        - Note: Replenishing the Autobar costs Cr2500
    """

    _MinTLMap = {
        _OptionLevel.Basic: 8,
        _OptionLevel.Improved: 9,
        _OptionLevel.Enhanced: 10,
        _OptionLevel.Advanced: 11
    }

    # Data Structure: Cost, Slots, Max Skill, Replenishment Cost
    _DataMap = {
        _OptionLevel.Basic: (500, 2, 0, 250),
        _OptionLevel.Improved: (1000, 2, 1, 500),
        _OptionLevel.Enhanced: (2000, 2, 2, 1000),
        _OptionLevel.Advanced: (5000, 2, 3, 2500)
    }
    
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Autobar',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_AutobarSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        autobarType = self._enumOption.value()
        assert(isinstance(autobarType, _OptionLevel))

        cost, slots, maxSkill, replenishmentCost = _AutobarSlotOptionImpl._DataMap[autobarType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{autobarType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{autobarType.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        step.addNote(f'Steward and Profession (bartender) skills are limited to {maxSkill} when using Autobar')      
        step.addNote(f'Replenishing the Autobar costs Cr{replenishmentCost}') 

class _AutochefSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - Basic
        - Min TL: 9
        - Cost: Cr500
        - Slots: 3
        - Note: Steward and Profession (chef) skills are limited to 0 when using Autochef
    - Improved
        - Min TL: 10
        - Cost: Cr2000
        - Slots: 3
        - Note: Steward and Profession (chef) skills are limited to 1 when using Autochef
    - Enhanced
        - Min TL: 11
        - Cost: Cr5000
        - Slots: 3
        - Note: Steward and Profession (chef) skills are limited to 2 when using Autochef
    - Advanced
        - Min TL: 12
        - Cost: Cr10000
        - Slots: 3
        - Note: Steward and Profession (chef) skills are limited to 3 when using Autochef 
    """

    _MinTLMap = {
        _OptionLevel.Basic: 9,
        _OptionLevel.Improved: 10,
        _OptionLevel.Enhanced: 11,
        _OptionLevel.Advanced: 12
    }

    # Data Structure: Cost, Slots, Max Skill
    _DataMap = {
        _OptionLevel.Basic: (500, 3, 0),
        _OptionLevel.Improved: (2000, 3, 1),
        _OptionLevel.Enhanced: (5000, 3, 2),
        _OptionLevel.Advanced: (10000, 3, 3)
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Autochef',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_AutochefSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        chefType = self._enumOption.value()
        assert(isinstance(chefType, _OptionLevel))

        cost, slots, maxSkill = _AutochefSlotOptionImpl._DataMap[chefType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{chefType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{chefType.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        step.addNote(f'Steward and Profession (chef) skills are limited to {maxSkill} when using Autochef')

class _AutopilotSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Requirement: Requires Speed Movement locomotion modification
        - Requirement: Autopilot and skill level packages do not stack; the
        higher of autopilot or vehicle operating skill applies.
    - Improved
        - Min TL: 7
        - Cost: Cr7500
        - Slots: 1
        - Trait: Autopilot = 1
    - Enhanced
        - Min TL: 9
        - Cost: Cr10000
        - Slots: 1
        - Trait: Autopilot = 2
    - Advanced
        - Min TL: 11
        - Cost: Cr15000
        - Slots: 1
        - Trait: Autopilot = 3
    """
    # TODO: Handle the requirement that Autopilot and skill level packages don't
    # stack. This could be a note that is added all the time by this component or
    # it could be added later by the skill or finalisation if it's applicable

    _MinTLMap = {
        _OptionLevel.Improved: 7,
        _OptionLevel.Enhanced: 9,
        _OptionLevel.Advanced: 11
    }

    # Data Structure: Cost, Slots, Autopilot Rating
    _DataMap = {
        _OptionLevel.Improved: (7500, 1, 1),
        _OptionLevel.Enhanced: (10000, 1, 2),
        _OptionLevel.Advanced: (15000, 1, 3)
    } 

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Autopilot',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Improved,                      
            minTLMap=_AutopilotSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence, context):
            return False
        
        return context.findFirstComponent(
            componentType=robots.VehicleSpeedMovement,
            sequence=sequence) != None

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        autopilotType = self._enumOption.value()
        assert(isinstance(autopilotType, _OptionLevel))

        cost, slots, autopilot = _AutopilotSlotOptionImpl._DataMap[autopilotType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{autopilotType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{autopilotType.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        autopilot = common.ScalarCalculation(
            value=autopilot,
            name=f'{autopilotType.value} {self.componentString()} Rating')
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Autopilot,
            value=autopilot))

class _BioreactionChamberSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Option: Spin box to choose number of slots to allocate (range: 1-Base Slots)
    - Basic
        - Min TL: 6
        - Cost: Cr1000 * slots allocated
        - Slots: Slots allocated
    - Improved
        - Min TL: 8
        - Cost: Cr2000 * slots allocated
        - Slots: Slots allocated
    - Enhanced
        - Min TL: 10
        - Cost: Cr5000 * slots allocated
        - Slots: Slots allocated
    - Advanced
        - Min TL: 13
        - Cost: Cr20000 * slots allocated
        - Slots: Slots allocated
    """

    _MinTLMap = {
        _OptionLevel.Basic: 6,
        _OptionLevel.Improved: 8,
        _OptionLevel.Enhanced: 10,
        _OptionLevel.Advanced: 13
    }

    _CostMap = {
        _OptionLevel.Basic: 1000,
        _OptionLevel.Improved: 2000,
        _OptionLevel.Enhanced: 5000,
        _OptionLevel.Advanced: 20000
    } 

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Bioreaction Chamber',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_BioreactionChamberSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
        self._slotsOption = construction.IntegerOption(
            id='Slots',
            name='Slots',
            value=1,
            maxValue=1, # Set in updateOptions
            minValue=1,
            description='Specify the number of slots to allocate to the Bioreaction Chamber.')        
        
    def isZeroSlot(self) -> bool:
        return False
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._slotsOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        super().updateOptions(sequence=sequence, context=context)

        baseSlots = context.baseSlots(sequence=sequence)
        self._slotsOption.setMax(value=baseSlots.value())

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        slots = common.ScalarCalculation(
            value=self._slotsOption.value(),
            name='Requested Chamber Slots')
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))        
        
        chamberType = self._enumOption.value()
        assert(isinstance(chamberType, _OptionLevel))

        costPerSlot = common.ScalarCalculation(
            value=_BioreactionChamberSlotOptionImpl._CostMap[chamberType],
            name=f'{chamberType.value} {self.componentString()} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=slots,
            rhs=costPerSlot,
            name=f'{chamberType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))

class _ConstructionEquipmentSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Min TL: 5
        - Options: Spin box to choose number of levels (min: 1)
    - Small
        - Cost: Cr500
        - Slots: 2
        - Note: Can construct 0.2 cubic meters per hour
    - Medium
        - Cost: Cr5000 
        - Slots: 8
        - Note: Can construct 1 cubic meters per hour
    - Large
        - Cost: Cr50000
        - Slots: 32
        - Note: Can construct 5 cubic meters per hour
    """
    # NOTE: The rules say multiple construction options can be added to cover a
    # greater area. This is handled by the component rather than the impl, it
    # does this by allowing multiple instances of this component type be added.
    # This has the added benefit that the player could add different sized
    # construction options.
    # TODO: The list of sizes that can be selected should probably be filtered
    # so sizes that are greater than the base size aren't included. I think this
    # is actually a more general issue. There will be other components where some
    # size/type options should be removed but in general anything that is over 1
    # slot should probably make the check as you can get some very small robots.

    # Data Structure: Cost, Slots, Cubic Meters per Hour
    _DataMap = {
        _OptionSize.Small: (500, 2, 0.2),
        _OptionSize.Medium: (5000, 8, 1),
        _OptionSize.Large: (50000, 32, 5)
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Construction Equipment',
            minTL=5,
            enumType=_OptionSize,
            optionId='Size',
            optionName='Size',
            optionDescription='Specify the equipment size.',            
            optionDefault=_OptionSize.Small,                      
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        size = self._enumOption.value()
        assert(isinstance(size, _OptionSize))

        cost, slots, speed = _ConstructionEquipmentSlotOptionImpl._DataMap[size]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{size.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{size.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        step.addNote(f'Can process {speed} cubic meters per hour')

class _FabricationChamberSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Option: Spin box to choose number of slots to allocate (range: 1-Base Slots)
    - Basic
        - Min TL: 8
        - Cost: Cr2000 * slots allocated
        - Slots: Slots allocated
    - Improved
        - Min TL: 10
        - Cost: Cr10000 * slots allocated
        - Slots: Slots allocated
    - Enhanced
        - Min TL: 13
        - Cost: Cr50000 * slots allocated
        - Slots: Slots allocated
    - Advanced
        - Min TL: 17
        - Cost: Cr200000 * slots allocated
        - Slots: Slots allocated
    """

    _MinTLMap = {
        _OptionLevel.Basic: 8,
        _OptionLevel.Improved: 10,
        _OptionLevel.Enhanced: 13,
        _OptionLevel.Advanced: 17
    }

    _CostMap = {
        _OptionLevel.Basic: 2000,
        _OptionLevel.Improved: 10000,
        _OptionLevel.Enhanced: 50000,
        _OptionLevel.Advanced: 200000
    } 

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Fabrication Chamber',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_FabricationChamberSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
        self._slotsOption = construction.IntegerOption(
            id='Slots',
            name='Slots',
            value=1,
            maxValue=1, # Set in updateOptions
            minValue=1,
            description='Specify the number of slots to allocate to the Fabrication Chamber.')        
        
    def isZeroSlot(self) -> bool:
        return False
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._slotsOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        super().updateOptions(sequence=sequence, context=context)

        baseSlots = context.baseSlots(sequence=sequence)
        self._slotsOption.setMax(value=baseSlots.value())

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        slots = common.ScalarCalculation(
            value=self._slotsOption.value(),
            name='Requested Chamber Slots')
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))        
        
        chamberType = self._enumOption.value()
        assert(isinstance(chamberType, _OptionLevel))

        costPerSlot = common.ScalarCalculation(
            value=_FabricationChamberSlotOptionImpl._CostMap[chamberType],
            name=f'{chamberType.value} {self.componentString()} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=slots,
            rhs=costPerSlot,
            name=f'{chamberType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))

class _ForkliftSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Min TL: 5
    - Small
        - Cost: Cr3000
        - Slots: 8
        - Note: Maximum load 0.5 tons
    - Medium
        - Cost: Cr5000
        - Slots: 12
        - Note: Maximum load 1 ton
    - Large
        - Cost: Cr20000
        - Slots: 60
        - Note: Maximum load 5 ton
    """

    # Data Structure: Cost, Slots, Max tonnage
    _DataMap = {
        _OptionSize.Small: (3000, 8, 0.5),
        _OptionSize.Medium: (5000, 12, 1),
        _OptionSize.Large: (20000, 60, 5)
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Forklift',
            minTL=5,
            enumType=_OptionSize,
            optionId='Size',
            optionName='Size',
            optionDescription='Specify the size.',            
            optionDefault=_OptionSize.Small,                      
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        size = self._enumOption.value()
        assert(isinstance(size, _OptionSize))

        cost, slots, maxLoad = _ForkliftSlotOptionImpl._DataMap[size]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{size.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{size.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        step.addNote(f'Maximum load is {maxLoad} ton')

class _HolographicProjectorSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 10
    - Cost: Cr1000
    - Slots: 1
    """
    # NOTE: I think it makes sense that more than one projector can be
    # installed. This is handled by the component

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Holographic Projector',
            minTL=10,
            constantCost=1000,
            constantSlots=1,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False 
    
class _MiningEquipmentSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Min TL: 5
    - Small
        - Cost: Cr2000
        - Slots: 5
        - Note: Can mine 0.5 cubic meters per hour
    - Medium
        - Cost: Cr5000
        - Slots: 15
        - Note: Can mine 2 cubic meters per hour
    - Large
        - Cost: Cr15000
        - Slots: 45
        - Note: Can mine 8 cubic meters per hour
    """
    # NOTE: The rules say multiple construction options can be added to cover a
    # greater area. This is handled by the component rather than the impl, it
    # does this by allowing multiple instances of this component type be added.
    # This has the added benefit that the player could add different sized
    # construction options.
    # TODO: The list of sizes that can be selected should probably be filtered
    # so sizes that are greater than the base size aren't included. I think this
    # is actually a more general issue. There will be other components where some
    # size/type options should be removed but in general anything that is over 1
    # slot should probably make the check as you can get some very small robots.

    # Data Structure: Cost, Slots, Cubic Meters per Hour
    _DataMap = {
        _OptionSize.Small: (2000, 5, 0.5),
        _OptionSize.Medium: (5000, 15, 2),
        _OptionSize.Large: (15000, 45, 8)
    }

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Mining Equipment',
            minTL=5,
            enumType=_OptionSize,
            optionId='Size',
            optionName='Size',
            optionDescription='Specify the equipment size.',            
            optionDefault=_OptionSize.Small,                      
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        size = self._enumOption.value()
        assert(isinstance(size, _OptionSize))

        cost, slots, speed = _MiningEquipmentSlotOptionImpl._DataMap[size]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{size.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{size.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        step.addNote(f'Can mine {speed} cubic meters per hour')

class _NavigationSystemSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL> 
        - Requirement: The skill level imparted by this option is based on the
        system’s information and not modified by a robot’s INT modifier
    - Basic
        - Min TL: 8
        - Cost: Cr2000
        - Slots: 2
        - Skill: Navigation 1
    - Improved
        - Min TL: 10
        - Cost: Cr10000
        - Slots: 2
        - Skill: Navigation 2
    - Enhanced
        - Min TL: 12
        - Cost: Cr25000
        - Slots: 1
        - Skill: Navigation 3
    - Advanced
        - Min TL: 14
        - Cost: Cr50000
        - Slots: 1
        - Skill: Navigation 4
    """
    # TODO: Handle Navigation skill
    # TODO: Handle requirement on not including robots INT. How I handle the
    # Navigation skill this component gives and if I include the robots INT
    # in the final skill value I calculate (I think the book does this)
    # - Rather than setting a Navigation skill I could add a note to this
    # component giving the skill when the Navigation System is in use. In this
    # case the requirement about not adding the INT is just a note as well
    # - If I set the robots Navigation skill to the value from this component
    # but don't include INT in the final value then the requirement about not
    # adding the INT is just a note for this component
    # - If I set the robots Navigation skill to the value from this component
    # and do include INT in the final value then this gets complex. It would
    # probably need some logic in the Navigation Skill component but that
    # could be made more complex if there are any other components that give
    # the Navigation skill.

    _MinTLMap = {
        _OptionLevel.Basic: 8,
        _OptionLevel.Improved: 10,
        _OptionLevel.Enhanced: 12,
        _OptionLevel.Advanced: 14
    }

    _DataMap = {
        _OptionLevel.Basic: (2000, 2, 1),
        _OptionLevel.Improved: (10000, 2, 2),
        _OptionLevel.Enhanced: (25000, 1, 3),
        _OptionLevel.Advanced: (50000, 1, 4)
    } 

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Navigation System',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_FabricationChamberSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        systemType = self._enumOption.value()
        assert(isinstance(systemType, _OptionLevel))        
        
        cost, slots, skill = _NavigationSystemSlotOptionImpl._DataMap[systemType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{systemType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{systemType.value} {self.componentString()} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))

class _SelfDestructSystemSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - Defensive
        - Min TL: 8
        - Cost: Cr500 * Base Slots
        - Slots: 5% of Base Slots
        - Note: The robot takes (Hits / 3) rounded up D damage plus 3 x 1D Severity Brain Critical Hits
        - Note: Anyone within 3 meters of the robot will take half the robots damage dice rounded down minis the robots armour
            - I think half the robots damage dice rounded down is (Hits / 6) rounded down
        - Note: The explosion has the Blast 3 trait
    - Offensive
        - Min TL: 6
        - Cost: Cr1000 * Base Slots
        - Slots: 10% of Base Slots
        - Note: The robot takes (Hits / 3) rounded up D damage plus 3 x 1D Severity Brain Critical Hits
        - Note: Anyone within the blast radius will take half the robots damage dice rounded down
            - NOTE: Unlike Defensive the robots armour doesn't reduce this
        - Note: The explosion has the Blast <Robot Size> trait
    - TDX
        - Min TL: 12
        - Cost: Cr1000 * Base Slots
        - Slots: 10% of Base Slots
        - Note: The robot takes (Hits / 3) rounded up D damage plus 3 x 1D Severity Brain Critical Hits
        - Note: Anyone within the blast radius will take (Hits)D damage
        - Note: The explosion has the Blast 15 trait
    - Nuclear
        - Min TL: 12
        - Cost: Cr500000
        - Slots: 4
        - Note: The robot is vaporised
        - Note: Anyone within the blast radius will take 10DD damage
        - Note: The explosion has the Blast 1000 and Radiation traits
    """
    # NOTE: The costs for the self-destruct system (other than nuclear) is per
    # base slot rather than per slot used by the component. This is different
    # from most components but it is what the table heading on p53 has.
    # TODO: Ideally the notes would calculate the value for things like Hits/3
    # and fill it in the string but doing that is only possible if there are no
    # other components that can increase the Hits value after this point
    # TODO: Some of the notes talk about the robots damage dice, I'm not sure
    # what that is referring to

    class _ExplosiveType(enum.Enum):
        Defensive = 'Defensive'
        Offensive = 'Offensive'
        TDX = 'TDX'
        Nuclear = 'Nuclear'

    _MinTLMap = {
        _ExplosiveType.Defensive: 8,
        _ExplosiveType.Offensive: 6,
        _ExplosiveType.TDX: 12,
        _ExplosiveType.Nuclear: 12
    }

    # Data Structure: Cost Per Base Slot, Constant Cost, Base Slot Percentage, Constant Slots, Blast Trait (or None for Robot Size), Damage Note
    _DataMap = {
        _ExplosiveType.Defensive: ( 500,   None,    5, None,    3, 'Anyone within 3 meters of the robot will take half the robots damage dice rounded down minus the robots armour'),
        _ExplosiveType.Offensive: (1000,   None,   10, None, None, 'Anyone within the blast radius will take half the robots damage dice rounded down'),
        _ExplosiveType.TDX:       (1000,   None,   10, None,   15, 'Anyone within the blast radius will take (Hits)D damage'),
        _ExplosiveType.Nuclear:   (None, 500000, None,    4, 1000, 'Anyone within the blast radius will take 10DD damage')
    }

    _StandardRobotDamageNote = 'The robot takes (Hits / 3) rounded up D damage plus 3 x 1D Severity Brain Critical Hits'
    _NuclearRobotDamageNote = 'The robot is vaporised'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Self-Destruct System',
            enumType=_SelfDestructSystemSlotOptionImpl._ExplosiveType,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_SelfDestructSystemSlotOptionImpl._ExplosiveType.Defensive,                      
            minTLMap=_SelfDestructSystemSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        explosiveType = self._enumOption.value()
        assert(isinstance(explosiveType, _SelfDestructSystemSlotOptionImpl._ExplosiveType))        
        
        costPerBaseSlot, constantCost, slotsPercentage, constantSlots, blastTrait, damageNote = \
            _SelfDestructSystemSlotOptionImpl._DataMap[explosiveType]
        
        componentName = f'{explosiveType.value} {self.componentString()}'
        baseSlots = context.baseSlots(sequence=sequence)

        if slotsPercentage != None:
            slotsPercentage = common.ScalarCalculation(
                value=slotsPercentage,
                name=f'{componentName} Percentage Base Slots Required Slots')        
            slots = common.Calculator.ceil(
                value=common.Calculator.takePercentage(
                    value=baseSlots,
                    percentage=slotsPercentage),
                name=f'{componentName} Required Slots')
        else:
            assert(constantSlots != None)
            slots = common.ScalarCalculation(
                value=constantSlots,
                name=f'{componentName} Required Slots')            
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))

        if costPerBaseSlot != None:
            costPerBaseSlot = common.ScalarCalculation(
                value=costPerBaseSlot,
                name=f'{componentName} Cost Per Base Slot')
            cost = common.Calculator.multiply(
                lhs=baseSlots,
                rhs=costPerBaseSlot,
                name=f'{componentName} Cost')
        else:
            assert(constantCost != None)
            cost = common.ScalarCalculation(
                value=constantCost,
                name=f'{componentName} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        if blastTrait == None:
            chassis = context.findFirstComponent(
                componentType=robots.Chassis,
                sequence=sequence)
            assert(isinstance(chassis, robots.Chassis))
            blastTrait = chassis.size()

        if explosiveType == _SelfDestructSystemSlotOptionImpl._ExplosiveType.Nuclear:
            step.addNote(_SelfDestructSystemSlotOptionImpl._NuclearRobotDamageNote)
            step.addNote(f'The blast has the Blast {blastTrait} and Radiation traits')
        else:
            step.addNote(_SelfDestructSystemSlotOptionImpl._StandardRobotDamageNote)
            step.addNote(f'The blast has the Blast {blastTrait} trait')
        step.addNote(damageNote)

class _StealthSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - Basic
        - Min TL: 7
        - Cost: Cr300 * Base Slots
        - Slots: 1
        - Trait: Stealth +1
    - Improved
        - Min TL: 9
        - Cost: Cr600 * Base Slots
        - Slots: 2
        - Trait: Stealth +2
    - Enhanced
        - Min TL: 11
        - Cost: Cr900 * Base Slots
        - Slots: 3
        - Trait: Stealth +3     
    - Advanced
        - Min TL: 13
        - Cost: Cr1200 * Base Slots
        - Slots: 4
        - Trait: Stealth +4  
    """
    # NOTE: The costs for the stealth is per base slot rather than per slot used
    # by the component.
    # NOTE: This is dealing with the Stealth Trait not the Stealth Skill

    _MinTLMap = {
        _OptionLevel.Basic: 7,
        _OptionLevel.Improved: 9,
        _OptionLevel.Enhanced: 11,
        _OptionLevel.Advanced: 13
    }

    # Data Structure: Cost Per Base Slot, Slots, Stealth Trait
    _DataMap = {
        _OptionLevel.Basic: (300, 1, 1),
        _OptionLevel.Improved: (600, 2, 2),
        _OptionLevel.Enhanced: (900, 3, 3),
        _OptionLevel.Advanced: (1200, 4, 4)
    } 

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Stealth',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_StealthSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        stealthType = self._enumOption.value()
        assert(isinstance(stealthType, _OptionLevel))        
        
        perBaseSlotCost, slots, stealthTrait = \
            _StealthSlotOptionImpl._DataMap[stealthType]
        componentString = f'{stealthType.value} {self.componentString()}'

        perBaseSlotCost = common.ScalarCalculation(
            value=perBaseSlotCost,
            name=f'{componentString} Cost Per Base Slot')
        cost = common.Calculator.multiply(
            lhs=context.baseSlots(sequence=sequence),
            rhs=perBaseSlotCost,
            name=f'{componentString} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{componentString} Required Slots')        
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        stealthTrait = common.ScalarCalculation(
            value=stealthTrait,
            name=f'{componentString} Trait')
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Stealth,
            value=stealthTrait))

class _StorageCompartmentSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Min TL: 6
        - Slots: Slots allocated
        - Option: Spin box to choose the number of slots to allocate
    - Standard
        - Cost: Cr50 * slots allocated
    - Refrigerated
        - Cost: Cr100 * slots allocated
    - Hazardous Materials
        - Cost: Cr500 * slots allocated
    """
    # NOTE: I think it makes sense to make sense to allow more than one storage
    # compartment to be added, for example separate ones for hazardous and
    # non-hazardous materials. This will be handled by the component rather than
    # the impl

    class _CompartmentType(enum.Enum):
        Standard = 'Standard'
        Refrigerated = 'Refrigerated'
        HazardousMaterials = 'Hazardous Materials'

    _CostMap = {
        _CompartmentType.Standard: 50,
        _CompartmentType.Refrigerated: 100,
        _CompartmentType.HazardousMaterials: 500
    } 

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Storage Compartment',
            minTL=6,
            enumType=_StorageCompartmentSlotOptionImpl._CompartmentType,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_StorageCompartmentSlotOptionImpl._CompartmentType.Standard,                      
            incompatibleTypes=incompatibleTypes)
        
        self._slotsOption = construction.IntegerOption(
            id='Slots',
            name='Slots',
            value=1,
            maxValue=1, # Set in updateOptions
            minValue=1,
            description='Specify the number of slots to allocate to the Storage Compartment.')        
        
    def isZeroSlot(self) -> bool:
        return False
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._slotsOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        super().updateOptions(sequence=sequence, context=context)

        baseSlots = context.baseSlots(sequence=sequence)
        self._slotsOption.setMax(value=baseSlots.value())

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        slots = common.ScalarCalculation(
            value=self._slotsOption.value(),
            name='Requested Chamber Slots')
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))        
        
        compartmentType = self._enumOption.value()
        assert(isinstance(compartmentType, _StorageCompartmentSlotOptionImpl._CompartmentType))

        costPerSlot = common.ScalarCalculation(
            value=_StorageCompartmentSlotOptionImpl._CostMap[compartmentType],
            name=f'{compartmentType.value} {self.componentString()} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=slots,
            rhs=costPerSlot,
            name=f'{compartmentType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))

class _VideoProjectorSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 7
    - Cost: Cr500
    - Slots: 1
    """
    # NOTE: I think it makes sense that more than one projector can be
    # installed. This is handled by the component

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Video Projector',
            minTL=7,
            constantCost=500,
            constantSlots=1,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False 

class _ExternalPowerSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 9
    - Cost: Cr100 * Base Slots
    - Slots: 5% of Base Slots
    """

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='External Power',
            minTL=9,
            perBaseSlotCost=100,
            percentBaseSlots=5,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False 

class _NoInternalPowerSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 6
    - Slot Gain: +10% Base Slots gained rounded up
    - Trait: I assume this should set the robots Endurance to 0
    """
    # TODO: I'm not sure about setting the robots endurance
    # TODO: This component feels like it's more of an endurance
    # modification (i.e. chassis option) rather than a slot
    # option

    _Endurance = common.ScalarCalculation(
        value=0,
        name='No Internal Power Endurance')

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='No Internal Power',
            minTL=9,
            perBaseSlotCost=100,
            percentBaseSlots=-10, # Negative as it's a slot gain
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False 
    
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Endurance,
            value=_NoInternalPowerSlotOptionImpl._Endurance))
        
class _RTGSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Note: When using the RTG as the only power source the robots movement
        rate and STR are halved (rounded down), it suffers an Agility -2 modifier
        and it cannot use the Vehicle Speed Movement modification or Athletics
        (endurance) skill.
        - Note: The RTG can recharge the robots power pack in 3 * <Robot
        Endurance> hours if the robot remains stationary or performs minimal
        activity
        - Note: After the <Half Life> years the RTG continues to provide
        power but it takes twice as long to recharge power packs and, when 
        using the RTG as the only power source, the robots movement rate and STR
        are halved (rounded down) again.
        - Note: The RTG stops providing power after <Half Life> * 2 years
        - Requirement: If a robot installs two RTG or solar power sources, in
        any combination, it is not subject to these performance degradations,
        provided both power sources are operating at full capability; in such
        cases the robot could support vehicle speed movement modifications
    - Long Duration
        - Basic
            - Min TL: 7
            - Cost: Cr20000 * Slots
            - Slots: 20% of Base Slots
            - Trait: Half Life = 25 years
        - Improved
            - Min TL: 9
            - Cost: Cr50000 * Slots
            - Slots: 15% of Base Slots
            - Trait: Half Life = 50 years
        - Advanced
            - Min TL: 11
            - Cost: Cr100000 * Slots
            - Slots: 10% of Base Slots
            - Trait: Half Life = 100 years
    - Short Duration
        - Basic
            - Min TL: 8
            - Cost: Cr50000 * Slots
            - Slots: 15% of Base Slots
            - Trait: Half Life = 3 years
        - Improved
            - Min TL: 10
            - Cost: Cr100000 * Slots
            - Slots: 10% of Base Slots
            - Trait: Half Life = 4 years
        - Advanced
            - Min TL: 12
            - Cost: Cr200000 * Slots
            - Slots: 5% of Base Slots
            - Trait: Half Life = 5 years
    """
    # TODO: Something seems off with the logic of how power packs are recharged.
    # The rules have it as 'three times a power pack’s endurance to fully
    # recharge it'. As a lot of robots have an Endurance the 100s of hours, this
    # can mean fully recharging their power packs can take a crazy length of time
    # (1000s of hours). It's these values I'm currently displaying to the user
    # but I they're so big it's pretty meaningless.
    # I suspect it's not really intended for how long it will take to charge the
    # robots battery from flat but how long to top it back up to full after doing
    # X hours of work. This is probably a much more meaningful piece of info for
    # the player. It would also mean there wouldn't be any values to calculate.    
    # TODO: Handle requirement regarding multiple RTGs or RTG/Solar combination.
    # I suspect this will need to be handled in finalisation, if that's the case
    # then a few of the notes for this component will need handled there

    class _Duration(enum.Enum):
        LongBasic = 'Basic Long Duration'
        LongImproved = 'Improved Long Duration'
        LongAdvanced = 'Advanced)Long Duration'
        ShortBasic = 'Basic Short Duration'
        ShortImproved = 'Improved Short Duration'
        ShortAdvanced = 'Advanced Short Duration'           

    _MinTLMap = {
        _Duration.LongBasic: 7,
        _Duration.LongImproved: 9,
        _Duration.LongAdvanced: 11,
        _Duration.ShortBasic: 8,
        _Duration.ShortImproved: 10,
        _Duration.ShortAdvanced: 12
    }

    # Data Structure: Cost Per Slot, Base Slot Percentage, Half Life (years)
    _DataMap = {
        _Duration.LongBasic: (20000, 20, 25),
        _Duration.LongImproved: (50000, 15, 50),
        _Duration.LongAdvanced: (100000, 10, 100),
        _Duration.ShortBasic: (50000, 15, 3),
        _Duration.ShortImproved: (100000, 10, 4),
        _Duration.ShortAdvanced: (200000, 5, 5)
    }

    _PowerPackRechargeEnduranceMultiplier = common.ScalarCalculation(
        value=3,
        name='RTG Power Pack Recharge Endurance Multiplier')
    _FailureEnduranceMultiplier = common.ScalarCalculation(
        value=2,
        name='RTG Failure Multiplier')

    _OnlyPowerSourceNote = 'When relying on the RTG as the only power source, the robots movement rate and STR are halved (rounded down), it suffers an Agility -2 modifier and it cannot use the Vehicle Speed Movement modification or the Athletics (endurance) skill.'
    _PowerPackRechargeNote = 'The robots power packs can be recharged in {recharge} hours if the robot remains stationary or performs minimal activity'
    _HalfLifeNote = 'After {endurance} years the RTG continues to power the robot but it takes twice as long to recharge power packs and, when using the RTG as the only power source, the robots movement rate and STR are halved again (rounded down).'
    _FailureNote = 'After {failure} years the RTG is no longer able to provide power to the robot'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='RTG',
            enumType=_RTGSlotOptionImpl._Duration,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_RTGSlotOptionImpl._Duration.LongBasic,                      
            minTLMap=_RTGSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        duration = self._enumOption.value()
        assert(isinstance(duration, _RTGSlotOptionImpl._Duration))

        costPerSlot, slotsPercentage, halfLife = \
            _RTGSlotOptionImpl._DataMap[duration]
        componentString = f'{duration.value} {self.componentString()}'        

        slotsPercentage = common.ScalarCalculation(
            value=slotsPercentage,
            name=f'{componentString} Base Slot Percentage Required')
        slots = common.Calculator.takePercentage(
            value=context.baseSlots(sequence=sequence),
            percentage=slotsPercentage,
            name=f'{componentString} Slots Required')
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))        
        
        costPerSlot = common.ScalarCalculation(
            value=costPerSlot,
            name=f'{componentString} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=slots,
            rhs=costPerSlot,
            name=f'{componentString} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        step.addNote(_RTGSlotOptionImpl._OnlyPowerSourceNote)        
        
        hasInternalPower = not context.hasComponent(
            componentType=NoInternalPowerSlotOption,
            sequence=sequence)
        if hasInternalPower:
            robotEndurance = context.attributeValue(
                attributeId=robots.RobotAttributeId.Endurance,
                sequence=sequence)
            assert(isinstance(robotEndurance, common.ScalarCalculation))

            rechargeHours = common.Calculator.multiply(
                lhs=robotEndurance,
                rhs=_RTGSlotOptionImpl._PowerPackRechargeEnduranceMultiplier,
                name=f'Power Pack Recharge Time')

            step.addNote(_RTGSlotOptionImpl._PowerPackRechargeNote.format(
                recharge=rechargeHours.value()))
            
        halfLife = common.ScalarCalculation(
            value=halfLife,
            name=f'{componentString} Half Life')
        usableLife = common.Calculator.multiply(
            lhs=halfLife,
            rhs=_RTGSlotOptionImpl._FailureEnduranceMultiplier,
            name=f'{componentString} Usable Lifetime')
        step.addNote(_RTGSlotOptionImpl._HalfLifeNote.format(endurance=halfLife.value()))
        step.addNote(_RTGSlotOptionImpl._FailureNote.format(failure=usableLife.value()))

class _SolarPowerUnitSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Note: When using the Solar Power as the only power source the robots
        movement rate and STR are halved (rounded down), it suffers an Agility -2
        modifier and it cannot use the Vehicle Speed Movement modification or the
        Athletics (endurance) skill.
        - Note: The robot can maintain a normal activity level for half the
        length of time it spends in sunlight. If the robot halves its movement
        rate and STR again and applies a further Agility -2 modifier, it can
        operation for the length of time it spent in sunlight. If the robot is
        stationary or performs minimal activity it can operate for twice as long
        as it spends in sunlight.
        - Note: If maintaining a normal activity level, the robot can recharge
        its power packs in <Robot Endurance> * 8 hours. If the robot applies the
        further reductions to movement rate and STR and Agility modifier, it can
        recharge its power packs in <Robot Endurance> * 4 hours. If the robot is
        stationary or performing minimal activity, it can recharge its power
        pack in <Robot Endurance> * 2 hours
        - Note: The solar panels stops providing power after <Lifespan> years        
        - Note: When solar panels are deployed the robots size is +1, it suffers
        a DM-2 to Stealth checks or provides a DM+2 to the oppositions
        Electronics (sensors) or Recon checks.
        - Note: Solar panels have an armour rating of the base armour rating for
        the robot and 10% the Hits of the robot.
        - Note: When attacks are made against a robot with deployed solar panels,
        half the successful attacks hit the panels unless they were specifically
        targetted at other components.
        - Requirement: If a robot installs two RTG or solar power sources, in
        any combination, it is not subject to these performance degradations,
        provided both power sources are operating at full capability; in such
        cases the robot could support vehicle speed movement modifications        
    - Basic
        - Min TL: 6
        - Cost: Cr2000 * Base Slots
        - Slots: 20% of Base Slots
        - Trait: Lifespan = 10 years
    - Improved
        - Min TL: 8
        - Cost: Cr5000 * Base Slots
        - Slots: 15% of Base Slots
        - Trait: Lifespan = 25 years
    - Enhanced
        - Min TL: 10
        - Cost: Cr10000 * Base Slots
        - Slots: 10% of Base Slots
        - Trait: Lifespan = 50 years 
    - Advanced
        - Min TL: 12
        - Cost: Cr20000 * Base Slots
        - Slots: 5% of Base Slots
        - Trait: Lifespan = 100 years
    """
    # TODO: Something seems off with the logic of how power packs are recharged.
    # The rules have it as a multiple of 'the hours as the power pack supplies',
    # with the lost multiple being 2 for minimal activity. The max number of
    # hours a robots power pack(s) can supply is its Endurance (i.e. how long
    # it can operate for continuously). As a lot of robots have an Endurance the
    # 100s of hours, this can mean fully recharging their power packs can take a
    # crazy length of time (1000s of hours). It's these values I'm currently
    # displaying to the user but I they're so big it's pretty meaningless.
    # I suspect it's not really intended for how long it will take to charge the
    # robots battery from flat but how long to top it back up to full after doing
    # X hours of work. This is probably a much more meaningful piece of info for
    # the player. It would also mean there wouldn't be any values to calculate.
    # TODO: Handle requirement regarding multiple RTGs or RTG/Solar combination.
    # I suspect this will need to be handled in finalisation, if that's the case
    # then a few of the notes for this component will need handled there 

    _MinTLMap = {
        _OptionLevel.Basic: 6,
        _OptionLevel.Improved: 8,
        _OptionLevel.Enhanced: 10,
        _OptionLevel.Advanced: 12
    }

    # Data Structure: Cost Per Slot, Base Slot Percentage, Lifespan (years)
    _DataMap = {
        _OptionLevel.Basic: (2000, 20, 10),
        _OptionLevel.Improved: (5000, 15, 25),
        _OptionLevel.Enhanced: (10000, 10, 50),
        _OptionLevel.Advanced: (20000, 5, 100)
    }

    _NormalPowerPackRechargeEnduranceMultiplier = common.ScalarCalculation(
        value=8,
        name='Solar Power Normal Activity Power Pack Recharge Endurance Multiplier')
    _QuarterPowerPackRechargeEnduranceMultiplier = common.ScalarCalculation(
        value=4,
        name='Solar Power Quarter Activity Power Pack Recharge Endurance Multiplier')
    _MinimalPowerPackRechargeEnduranceMultiplier = common.ScalarCalculation(
        value=2,
        name='Solar Power Minimal Activity Power Pack Recharge Endurance Multiplier')
    
    _DeployedSizeModifier = common.ScalarCalculation(
        value=1,
        name='Solar Power Deployed Size Modifier')
    
    _PanelsHitPercentage = common.ScalarCalculation(
        value=10,
        name='Solar Power Panel Hit Percentage')

    _OnlyPowerSourceNote = 'When relying on the solar panels as the only power source, the robots movement rate and STR are halved (rounded down), it suffers an Agility -2 modifier and it cannot use the Vehicle Speed Movement modification or the Athletics (endurance) skill.'
    _SunlightNote = 'The robot can maintain a normal activity level for half the length of time it spends in sunlight. If the robot halves its movement rate and STR again and applies a further Agility -2 modifier, it can operation for the length of time it spent in sunlight. If the robot is stationary or performs minimal activity it can operate for twice as long as it spends in sunlight.'
    _RechargeNote = 'If maintaining a normal activity level, the robot can recharge its power packs in {normal} hours. If the robot applies the further reductions to movement rate and STR and Agility modifier, it can recharge its power packs in {quarter} hours. If the robot is stationary or performing minimal activity, it can recharge its power pack in {minimal} hours'
    _LifespanNote = 'The solar panels stops providing power after {lifespan} years'
    _DeployedNote = 'When the solar panels are deployed the robots Size is {size}, it suffers a DM-2 to Stealth checks or provides a DM+2 to the oppositions Electronics (sensors) or Recon checks.'
    _DurabilityNote = 'The solar panels have an Armour of {armour} and Hits of {hits}.'
    _AttacksNote = 'When attacks are made against a robot with deployed solar panels, half the successful attacks hit the panels unless they were specifically targetted at other components.'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Solar Power Unit',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_SolarPowerUnitSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        panelType = self._enumOption.value()
        assert(isinstance(panelType, _OptionLevel))

        costPerSlot, slotsPercentage, lifespan = \
            _SolarPowerUnitSlotOptionImpl._DataMap[panelType]
        componentString = f'{panelType.value} {self.componentString()}'        

        slotsPercentage = common.ScalarCalculation(
            value=slotsPercentage,
            name=f'{componentString} Base Slot Percentage Required')
        slots = common.Calculator.takePercentage(
            value=context.baseSlots(sequence=sequence),
            percentage=slotsPercentage,
            name=f'{componentString} Slots Required')
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))        
        
        costPerSlot = common.ScalarCalculation(
            value=costPerSlot,
            name=f'{componentString} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=slots,
            rhs=costPerSlot,
            name=f'{componentString} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        step.addNote(_SolarPowerUnitSlotOptionImpl._OnlyPowerSourceNote)
        step.addNote(_SolarPowerUnitSlotOptionImpl._SunlightNote)
        
        hasInternalPower = not context.hasComponent(
            componentType=NoInternalPowerSlotOption,
            sequence=sequence)
        if hasInternalPower:
            robotEndurance = context.attributeValue(
                attributeId=robots.RobotAttributeId.Endurance,
                sequence=sequence)
            assert(isinstance(robotEndurance, common.ScalarCalculation))

            normalRechargeHours = common.Calculator.multiply(
                lhs=robotEndurance,
                rhs=_SolarPowerUnitSlotOptionImpl._NormalPowerPackRechargeEnduranceMultiplier,
                name='Normal Activity Power Pack Recharge Time')
            
            quarterRechargeHours = common.Calculator.multiply(
                lhs=robotEndurance,
                rhs=_SolarPowerUnitSlotOptionImpl._QuarterPowerPackRechargeEnduranceMultiplier,
                name='Quarter Activity Power Pack Recharge Time')
            
            minimalRechargeHours = common.Calculator.multiply(
                lhs=robotEndurance,
                rhs=_SolarPowerUnitSlotOptionImpl._MinimalPowerPackRechargeEnduranceMultiplier,
                name='Quarter Minimal Power Pack Recharge Time')

            step.addNote(_SolarPowerUnitSlotOptionImpl._RechargeNote.format(
                normal=normalRechargeHours.value(),
                quarter=quarterRechargeHours.value(),
                minimal=minimalRechargeHours.value()))
            
            step.addNote(_SolarPowerUnitSlotOptionImpl._LifespanNote.format(
                lifespan=lifespan))
            
        robotSize = context.attributeValue(
            attributeId=robots.RobotAttributeId.Size,
            sequence=sequence)
        assert(isinstance(robotSize, common.ScalarCalculation))
        deployedSize = common.Calculator.add(
            lhs=robotSize,
            rhs=_SolarPowerUnitSlotOptionImpl._DeployedSizeModifier,
            name='Deployed Size')
        step.addNote(_SolarPowerUnitSlotOptionImpl._DeployedNote.format(
            size=deployedSize.value()))  

        panelArmour = context.attributeValue(
            attributeId=robots.RobotAttributeId.BaseProtection,
            sequence=sequence)
        robotHits = context.attributeValue(
            attributeId=robots.RobotAttributeId.Hits,
            sequence=sequence)
        assert(isinstance(robotHits, common.ScalarCalculation))
        panelHits = common.Calculator.takePercentage(
            value=robotHits,
            percentage=_SolarPowerUnitSlotOptionImpl._PanelsHitPercentage,
            name='Solar Panel Hits')
        
        step.addNote(_SolarPowerUnitSlotOptionImpl._DurabilityNote.format(
            armour=panelArmour.value(),
            hits=panelHits.value()))
        
        step.addNote(_SolarPowerUnitSlotOptionImpl._AttacksNote)

class _QuickChargerSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 8
    - Cost: Cr200
    - Slots: 1
    - Note: Can fully recharge a robot not running on external power in 1 hour
    """
    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Quick Charger',
            minTL=8,
            constantCost=200,
            constantSlots=1,
            notes=['Can fully recharge a robot not running on external power in 1 hour'],
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

class _BioscannerSensorSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 15
    - Cost: Cr350000
    - Slots: 2
    - Requirement: Requires at least Electronics (sensors) level 0 to operator
    """
    # TODO: Not sure how to handle requirement. Could just be a note

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Bioscanner Sensor',
            minTL=15,
            constantCost=350000,
            constantSlots=2,
            notes=['Requires at least Electronics (sensors) level 0 to operator'],
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

class _DensitometerSensorSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 14
    - Cost: Cr20000
    - Slots: 3
    - Note: Target must be within 100m to be scanned
    - Requirement: Requires at least Electronics (sensors) level 0 to operator
    """
    # TODO: Not sure how to handle requirement. Could just be a note

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Densitometer Sensor',
            minTL=14,
            constantCost=20000,
            constantSlots=3,
            notes=[
                'Target must be within 100m to be scanned',
                'Requires at least Electronics (sensors) level 0 to operator'],
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

class _NeuralActivitySensorSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 15
    - Cost: Cr35000
    - Slots: 5
    - Note: Detects Neural Activity within 500m
    - Requirement: Requires at least Electronics (sensors) level 0 to operator
    """
    # TODO: Not sure how to handle requirement. Could just be a note

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Neural Activity Sensor',
            minTL=15,
            constantCost=35000,
            constantSlots=5,
            notes=[
                'Detects Neural Activity within 500m',
                'Requires at least Electronics (sensors) level 0 to operator'],
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

class _PlanetologySensorSuiteSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 12
    - Cost: Cr25000
    - Slots: 5
    - Note: Adds DM+1 to any checks conducted in conjunction with data provided by the suite
    - Requirement: Requires at least Electronics (sensors) level 0 to operator
    - Requirement: Added +1 to the Maximum Skill level allowed by the Science (planetology) Toolkit
    """
    # TODO: Not sure how to handle requirement. Could just be a note
    # TODO: Handle +1 to Science (planetology) Toolkit

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Planetology Sensor Suite',
            minTL=12,
            constantCost=25000,
            constantSlots=5,
            notes=['Adds DM+1 to any checks conducted in conjunction with data provided by the suite'],
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

class _ReconSensorSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Note: Recon skill levels provided by this sensor are not modified by a robot’s INT.
    - Basic
        - Min TL: 7
        - Cost: Cr1000
        - Slots: 2
        - Skill: Recon 1
    - Improved
        - Min TL: 8
        - Cost: Cr100
        - Slots: 1
        - Skill: Recon 1  
    - Enhanced
        - Min TL: 10
        - Cost: Cr10000
        - Slots: 1
        - Skill: Recon 2 
    - Advanced
        - Min TL: 12
        - Cost: Cr20000
        - Slots: 1
        - Skill: Recon 3
    """
    # TODO: Handle Recon skill. This is complicated by the fact it's not
    # modified by the robots INT (see note) where as the normal Recon skill
    # would be

    _MinTLMap = {
        _OptionLevel.Basic: 7,
        _OptionLevel.Improved: 8,
        _OptionLevel.Enhanced: 10,
        _OptionLevel.Advanced: 12
    }

    # Data Structure: Cost, Slots, Recon Skill
    _DataMap = {
        _OptionLevel.Basic: (1000, 2, 1),
        _OptionLevel.Improved: (100, 1, 1),
        _OptionLevel.Enhanced: (10000, 1, 2),
        _OptionLevel.Advanced: (20000, 1, 3)
    } 

    _ReconNote = 'Recon skill levels provided by this sensor are not modified by a robot’s INT.'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Recon Sensor',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_ReconSensorSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)   
        
    def isZeroSlot(self) -> bool:
        return False
    
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)     
        
        sensorType = self._enumOption.value()
        assert(isinstance(sensorType, _OptionLevel))

        cost, slots, recon = _ReconSensorSlotOptionImpl._DataMap[sensorType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{sensorType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{sensorType.value} {self.componentString()} Required Slots')
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        step.addNote(_ReconSensorSlotOptionImpl._ReconNote)

class _CuttingTorchSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Note: Can be used as an improvised weapon doing 3D damage with AP 4
    - Basic    
        - Min TL: 5
        - Cost: Cr500
        - Slots: 2
        - Note: Can cut through metal but not crystaliron or superdense alloys.
    - Improved
        - Min TL: 9
        - Cost: Cr5000
        - Slots: 2
        - Note: Can cut through nearly all materials, but can take a long time to breach hull armour.
    - Advanced
        - Min TL: 13
        - Cost: Cr5000
        - Slots: 1
        - Note: Can cut through nearly all materials, but can take a long time to breach hull armour.
    """

    _MinTLMap = {
        _OptionLevel.Basic: 5,
        _OptionLevel.Improved: 9,
        _OptionLevel.Enhanced: 13
    }

    # Data Structure: Cost, Slots
    _DataMap = {
        _OptionLevel.Basic: (500, 2),
        _OptionLevel.Improved: (5000, 2),
        _OptionLevel.Enhanced: (5000, 1)
    } 

    _BasicNote = 'Can cut through metal but not crystaliron or superdense alloys.'
    _BetterNote = 'Can cut through nearly all materials, but can take a long time to breach hull armour.'
    _WeaponNote = 'Can be used as a weapon doing 3D damage with AP 4.'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Cutting Torch',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_CuttingTorchSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)   
        
    def isZeroSlot(self) -> bool:
        return False
    
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)     
        
        sensorType = self._enumOption.value()
        assert(isinstance(sensorType, _OptionLevel))

        cost, slots = _CuttingTorchSlotOptionImpl._DataMap[sensorType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{sensorType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{sensorType.value} {self.componentString()} Required Slots')
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        if sensorType == _OptionLevel.Basic:
            step.addNote(_CuttingTorchSlotOptionImpl._BasicNote)
        else:
            step.addNote(_CuttingTorchSlotOptionImpl._BetterNote)

        step.addNote(_CuttingTorchSlotOptionImpl._WeaponNote)

class _ElectronicsToolkitSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Note: In general the toolkit only allows a positive DM to repair
        attempts on equipment with a TL less than or equal to it
    - Basic
        - Min TL: 6
        - Cost: Cr2000            
        - Slots: 1
        - Note: Electronics skills are limited to 0 when using the toolkit
    - Improved
        - Min TL: 8
        - Cost: Cr4000            
        - Slots: 1
        - Note: Electronics skills are limited to 1 when using the toolkit
    - Enhanced
        - Min TL: 10
        - Cost: Cr6000            
        - Slots: 1
        - Note: Electronics skills are limited to 2 when using the toolkit
    - Advanced
        - Min TL: 12
        - Cost: Cr8000            
        - Slots: 1
        - Note: Electronics skills are limited to 3 when using the toolkit
    """
    # NOTE: The rules say the toolkit only allows a positive DM when working on
    # equipment less than or equal to its TL. However, I'm not sure what
    # positive DM it's talking about. It could be the word 'allows' is important
    # and it means the robots Electronics skill is limited to 0  if the
    # equipments TL is higher than the toolkits

    _MinTLMap = {
        _OptionLevel.Basic: 6,
        _OptionLevel.Improved: 8,
        _OptionLevel.Enhanced: 10,
        _OptionLevel.Advanced: 12
    }

    # Data Structure: Cost, Max Electronics Skill
    _DataMap = {
        _OptionLevel.Basic: (2000, 0),
        _OptionLevel.Improved: (4000, 1),
        _OptionLevel.Enhanced: (6000, 2),
        _OptionLevel.Advanced: (8000, 3)
    } 

    _RequiredSlots = common.ScalarCalculation(
        value=1,
        name='Electronics Toolkit Required Slots')

    _MaxSkillNote = 'Electronics skills are limited to {max} when using the toolkit'
    _MaxTLNote = 'In general the toolkit only allows a positive DM to repair attempts on equipment with a TL less than or equal to {techlevel}.'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Electronics Toolkit',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_ElectronicsToolkitSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)   
        
    def isZeroSlot(self) -> bool:
        return False
    
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)     
        
        toolkitType = self._enumOption.value()
        assert(isinstance(toolkitType, _OptionLevel))

        minTL = _ElectronicsToolkitSlotOptionImpl._MinTLMap[toolkitType]
        cost, maxSkill = _ElectronicsToolkitSlotOptionImpl._DataMap[toolkitType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{toolkitType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        step.setSlots(slots=construction.ConstantModifier(
            value=_ElectronicsToolkitSlotOptionImpl._RequiredSlots))

        step.addNote(_ElectronicsToolkitSlotOptionImpl._MaxSkillNote.format(
            max=maxSkill))
        step.addNote(_ElectronicsToolkitSlotOptionImpl._MaxTLNote.format(
            techlevel=minTL))

class _FireExtinguisherSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 6
    - Cost: Cr100
    - Slots: 1
    - Note: Can extinguish most chemical and electrical fires.
    - Note: If used to assist a Traveller or NPC who has been set on fire,
    damage is reduced by half in the first round and all damage in subsequent
    rounds
    """

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Fire Extinguisher',
            minTL=6,
            constantCost=100,
            constantSlots=1,
            notes=[
                'Can extinguish most chemical and electrical fires.',
                'If used to assist a Traveller or NPC who has been set on fire, damage is reduced by half in the first round and all damage in subsequent rounds'],
            incompatibleTypes=incompatibleTypes)
        
    def isZeroSlot(self) -> bool:
        return False

class _ForensicToolkitSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - Basic
        - Min TL: 8
        - Cost: Cr2000
        - Slots: 5
        - Note: Science skills are limited to 0 when using the toolkit
    - Improved
        - Min TL: 10
        - Cost: Cr4000
        - Slots: 4
        - Note: Science skills are limited to 1 when using the toolkit
    - Enhanced
        - Min TL: 12
        - Cost: Cr8000
        - Slots: 4
        - Note: Science skills are limited to 2 when using the toolkit
    - Advanced
        - Min TL: 14
        - Cost: Cr10000
        - Slots: 3
        - Note: Science skills are limited to 3 when using the toolkit
    """

    _MinTLMap = {
        _OptionLevel.Basic: 9,
        _OptionLevel.Improved: 10,
        _OptionLevel.Enhanced: 12,
        _OptionLevel.Advanced: 14
    }

    # Data Structure: Cost, Slots, Max Science Skill
    _DataMap = {
        _OptionLevel.Basic: (2000, 5, 0),
        _OptionLevel.Improved: (4000, 4, 1),
        _OptionLevel.Enhanced: (8000, 4, 2),
        _OptionLevel.Advanced: (10000, 3, 3)
    }

    _MaxSkillNote = 'Science skills are limited to {max} when using the toolkit'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Forensic Toolkit',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_ForensicToolkitSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)   
        
    def isZeroSlot(self) -> bool:
        return False
    
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)     
        
        toolkitType = self._enumOption.value()
        assert(isinstance(toolkitType, _OptionLevel))

        cost, slots, maxSkill = _ForensicToolkitSlotOptionImpl._DataMap[toolkitType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{toolkitType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{toolkitType.value} {self.componentString()} Required Slots')
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))

        step.addNote(_ForensicToolkitSlotOptionImpl._MaxSkillNote.format(
            max=maxSkill))

class _MechanicalToolkitSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Note: Repair attempts suffer a DM-2 if the equipment being repaired is
        more than 2 TLs higher than the toolkit and robot
    - Basic
        - Min TL: 4
        - Cost: Cr1000
        - Slots: 6
    - Improved
        - Min TL: 8
        - Cost: Cr2000
        - Slots: 4
    - Advanced
        - Min TL: 12
        - Cost: Cr4000
        - Slots: 2
    """

    _MinTLMap = {
        _OptionLevel.Basic: 4,
        _OptionLevel.Improved: 8,
        _OptionLevel.Enhanced: 12
    }

    # Data Structure: Cost, Slots
    _DataMap = {
        _OptionLevel.Basic: (1000, 6),
        _OptionLevel.Improved: (2000, 4),
        _OptionLevel.Enhanced: (4000, 2)
    }

    _AdditionalTL = 2

    _MaxTLNote = 'Repair attempts suffer a DM-2 if the equipment being repaired is TL {techlevel} or higher.'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Mechanical Toolkit',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_MechanicalToolkitSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)   
        
    def isZeroSlot(self) -> bool:
        return False
    
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)     
        
        toolkitType = self._enumOption.value()
        assert(isinstance(toolkitType, _OptionLevel))

        robotTL = context.techLevel()
        minTL = _MechanicalToolkitSlotOptionImpl._MinTLMap[toolkitType]
        cost, slots = _MechanicalToolkitSlotOptionImpl._DataMap[toolkitType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{toolkitType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{toolkitType.value} {self.componentString()} Required Slots')
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))

        maxTL = min(robotTL, minTL) + 2
        step.addNote(_MechanicalToolkitSlotOptionImpl._MaxTLNote.format(
            techlevel=maxTL))
        
class _ScientificToolkitSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - <ALL>
        - Option: String specifying science the toolkit is for
    - Basic
        - Min TL: 5
        - Cost: Cr2000
        - Slots: 4
        - Note: Whatever Science skill the toolkit is for is limited to 0 when using it
    - Improved
        - Min TL: 8
        - Cost: Cr4000
        - Slots: 3
        - Note: Whatever Science skill the toolkit is for is limited to 1 when using it
    - Enhanced
        - Min TL: 11
        - Cost: Cr6000
        - Slots: 3
        - Note: Whatever Science skill the toolkit is for is limited to 2 when using it
    - Advanced
        - Min TL: 14
        - Cost: Cr8000
        - Slots: 3
        - Note: Whatever Science skill the toolkit is for is limited to 3 when using it
    """
    # TODO: Need to be able to select from a list of predefined sciences or specify a
    # custom string

    _MinTLMap = {
        _OptionLevel.Basic: 5,
        _OptionLevel.Improved: 8,
        _OptionLevel.Enhanced: 11,
        _OptionLevel.Advanced: 14
    }

    # Data Structure: Cost, Slots, Max Science Skill
    _DataMap = {
        _OptionLevel.Basic: (2000, 4, 0),
        _OptionLevel.Improved: (4000, 3, 1),
        _OptionLevel.Enhanced: (6000, 3, 2),
        _OptionLevel.Advanced: (8000, 3, 3)
    }

    _MaxSkillNote = 'Science ({science}) skill is limited to {max} when using the toolkit'
    _NoScienceSpecifiedNote = 'WARNING: The science the toolkit is designed for has not been specified'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Scientific Toolkit',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_ScientificToolkitSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes) 

        self._scienceOption = construction.StringOption(
            id='Science',
            name='Science',
            value='',
            options=_PredefinedSciences,
            description='Specify the science the toolkit is for.')          
        
    def isZeroSlot(self) -> bool:
        return False
    
    def instanceString(self) -> str:
        science: str = self._scienceOption.value()
        if not science:
            return super().instanceString()

        toolkitType: enum.Enum = self._enumOption.value()
        return f'{self.componentString()} ({toolkitType.value} {science})'
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._scienceOption)
        return options 
    
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)     
        
        toolkitType = self._enumOption.value()
        assert(isinstance(toolkitType, _OptionLevel))

        science = self._scienceOption.value()
        assert(isinstance(science, str))
        if not science:
            step.addNote(_ScientificToolkitSlotOptionImpl._NoScienceSpecifiedNote)
            science = 'unspecified'

        cost, slots, maxSkill = _ScientificToolkitSlotOptionImpl._DataMap[toolkitType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{toolkitType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{toolkitType.value} {self.componentString()} Required Slots')
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))
        
        step.addNote(_ScientificToolkitSlotOptionImpl._MaxSkillNote.format(
            science=science,
            max=maxSkill))

class _StarshipEngineeringToolkitSlotOptionImpl(_EnumSelectSlotOptionImpl):
    """
    - Basic
        - Min TL: 8
        - Cost: Cr1000
        - Slots: 6
        - Note: Electronics, Engineering and Mechanic skills are limited to 0 when using the toolkit
    - Improved
        - Min TL: 10
        - Cost: Cr2000
        - Slots: 5
        - Note: Electronics, Engineering and Mechanic skills are limited to 1 when using the toolkit
    - Enhanced
        - Min TL: 12
        - Cost: Cr4000
        - Slots: 5
        - Note: Electronics, Engineering and Mechanic skills are limited to 2 when using the toolkit
    - Advanced
        - Min TL: 14
        - Cost: Cr10000
        - Slots: 4
        - Note: Electronics, Engineering and Mechanic skills are limited to 3 when using the toolkit
    """
    # TODO: Need to be able to select from a list of predefined sciences or specify a
    # custom string

    _MinTLMap = {
        _OptionLevel.Basic: 8,
        _OptionLevel.Improved: 10,
        _OptionLevel.Enhanced: 12,
        _OptionLevel.Advanced: 14
    }

    # Data Structure: Cost, Slots, Max Science Skill
    _DataMap = {
        _OptionLevel.Basic: (1000, 6, 0),
        _OptionLevel.Improved: (2000, 5, 1),
        _OptionLevel.Enhanced: (4000, 5, 2),
        _OptionLevel.Advanced: (10000, 4, 3)
    }

    _MaxSkillNote = 'Electronics, Engineering and Mechanic skills are limited to {max} when using the toolkit'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Starship Engineering',
            enumType=_OptionLevel,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the type.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_StarshipEngineeringToolkitSlotOptionImpl._MinTLMap,
            incompatibleTypes=incompatibleTypes)     
        
    def isZeroSlot(self) -> bool:
        return False
    
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)     
        
        toolkitType = self._enumOption.value()
        assert(isinstance(toolkitType, _OptionLevel))

        cost, slots, maxSkill = _StarshipEngineeringToolkitSlotOptionImpl._DataMap[toolkitType]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{toolkitType.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
        slots = common.ScalarCalculation(
            value=slots,
            name=f'{toolkitType.value} {self.componentString()} Required Slots')
        step.setSlots(
            slots=construction.ConstantModifier(value=slots))

        step.addNote(_StarshipEngineeringToolkitSlotOptionImpl._MaxSkillNote.format(
            max=maxSkill))

class _StylistToolkitSlotOptionImpl(_SingleStepSlotOptionImpl):
    """
    - Min TL: 6
    - Cost: 2000
    - Slots: 3
    - Option: String to option to specified species the toolkit is designed for
    - Note: Replenishing the toolkit with product has a base cost of Cr500 but
    this doubles for every point past SOC 8 the product is intended for.
    - Note: A positive Effect of a Profession (stylist) check can increase the
    effective SOC of the product by the Effect.
    - Note: Using the toolkit on a species other than the one it was designed
    for gives a DM-3 or more modifier.
    - Requirement: Need to be able to add multiple instances to allow for
    multiple species
    """

    _ReplenishingNote = 'Replenishing the toolkit with product has a base cost of Cr500 but this doubles for every point past SOC 8 the product is intended for.'
    _ProfessionNote = 'A positive Effect of a Profession (stylist) check can increase the effective SOC of the product by the Effect.'
    _SpeciesNote = 'Using the toolkit on a species other than {species} gives a DM-3 or more modifier.'
    _NoSpeciesSpecifiedNote = 'WARNING: The species the toolkit is designed for has not been specified'

    def __init__(
            self,
            incompatibleTypes: typing.Optional[typing.Iterable[robots.RobotComponentInterface]] = None
            ) -> None:
        super().__init__(
            componentString='Stylist Toolkit',
            minTL=6,
            constantCost=2000,
            constantSlots=3,
            incompatibleTypes=incompatibleTypes)
        
        self._speciesOption = construction.StringOption(
            id='Species',
            name='Species',
            value='',
            options=_PredefinedSpecies,
            description='Specify the species the Styling Toolkit is designed for.')    
        
    def isZeroSlot(self) -> bool:
        return False
    
    def instanceString(self) -> str:
        species: str = self._speciesOption.value()
        if not species:
            return super().instanceString()
        return f'{self.componentString()} ({species})'    
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._speciesOption)
        return options 
    
    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            step=step)
        
        species = self._speciesOption.value()
        assert(isinstance(species, str))
        if not species:
            step.addNote(_StylistToolkitSlotOptionImpl._NoSpeciesSpecifiedNote)
            species = 'the one it was designed for'

        step.addNote(_StylistToolkitSlotOptionImpl._ReplenishingNote)
        step.addNote(_StylistToolkitSlotOptionImpl._ProfessionNote)
        step.addNote(_StylistToolkitSlotOptionImpl._SpeciesNote.format(
            species=species))


#  ██████████               ██████                       ████   █████        █████████              ███   █████            
# ░░███░░░░███             ███░░███                     ░░███  ░░███        ███░░░░░███            ░░░   ░░███             
#  ░███   ░░███  ██████   ░███ ░░░   ██████   █████ ████ ░███  ███████     ░███    ░░░  █████ ████ ████  ███████    ██████ 
#  ░███    ░███ ███░░███ ███████    ░░░░░███ ░░███ ░███  ░███ ░░░███░      ░░█████████ ░░███ ░███ ░░███ ░░░███░    ███░░███
#  ░███    ░███░███████ ░░░███░      ███████  ░███ ░███  ░███   ░███        ░░░░░░░░███ ░███ ░███  ░███   ░███    ░███████ 
#  ░███    ███ ░███░░░    ░███      ███░░███  ░███ ░███  ░███   ░███ ███    ███    ░███ ░███ ░███  ░███   ░███ ███░███░░░  
#  ██████████  ░░██████   █████    ░░████████ ░░████████ █████  ░░█████    ░░█████████  ░░████████ █████  ░░█████ ░░██████ 
# ░░░░░░░░░░    ░░░░░░   ░░░░░      ░░░░░░░░   ░░░░░░░░ ░░░░░    ░░░░░      ░░░░░░░░░    ░░░░░░░░ ░░░░░    ░░░░░   ░░░░░░  

class DefaultSuiteOption(robots.DefaultSuiteOptionInterface):
    def __init__(
            self,
            impl: _SlotOptionImpl,
            singular: bool = True
            ) -> None:
        super().__init__()
        self._impl = impl
        self._singular = singular

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def componentString(self) -> str:
        return self._impl.componentString()
    
    def typeString(self) -> str:
        return 'Default Suite'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not self._impl.isCompatible(
            sequence=sequence,
            context=context):
            return False
        
        # If the component is singular make it incompatible with it's self
        if self._singular and context.hasComponent(
            componentType=type(self),
            sequence=sequence):
            return False

        return True
    
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
        self._impl.createSteps(
            sequence=sequence,
            context=context,
            typeString=self.typeString())
        
# NOTE: The order of these components (at least the first 5) is important as
# they are the canonical default suite options (p29). They need to be defined
# first so contraction logic will select them as the defaults for the stage
class VisualSpectrumSensorDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_VisualSpectrumSensorSlotOptionImpl(isDefaultSuite=True))         

class VoderSpeakerDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_VoderSpeakerSlotOptionImpl(isDefaultSuite=True))

class AuditorySensorDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_AuditorySensorSlotOptionImpl(isDefaultSuite=True))  

class WirelessDataLinkDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_WirelessDataLinkSlotOptionImpl(isDefaultSuite=True))

class TransceiverDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_TransceiverSlotOptionImpl(isDefaultSuite=True))

    def range(self) -> int:
        assert(isinstance(self._impl, _TransceiverSlotOptionImpl))
        return self._impl.range()

class VisualConcealmentDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_VisualConcealmentSlotOptionImpl())

class AudibleConcealmentDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_AudibleConcealmentSlotOptionImpl())

class OlfactoryConcealmentDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_OlfactoryConcealmentSlotOptionImpl())

class HostileEnvironmentProtectionDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_HostileEnvironmentProtectionSlotOptionImpl())  

class ReflectArmourDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_ReflectArmourSlotOptionImpl())

class SolarCoatingDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_SolarCoatingSlotOptionImpl()) 

class VacuumEnvironmentProtectionDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_VacuumEnvironmentProtectionSlotOptionImpl()) 

class DroneInterfaceDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_DroneInterfaceSlotOptionImpl(isDefaultSuite=True))

    # List component _from this stage_ that should be processed before this
    # component
    def orderAfter(self) -> typing.List[typing.Type[construction.ComponentInterface]]:
        dependencies = super().orderAfter()
        dependencies.append(TransceiverDefaultSuiteOption)
        return dependencies        

class EncryptionModuleDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_EncryptionModuleSlotOptionImpl())

class VideoScreenDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_VideoScreenSlotOptionImpl(isDefaultSuite=True))

class GeckoGrippersDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_GeckoGrippersSlotOptionImpl())

# NOTE This component is different from most other slot options as multiple
# instances can be added
class InjectorNeedleDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_InjectorNeedleSlotOptionImpl(),
            singular=False)

class LaserDesignatorDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_LaserDesignatorSlotOptionImpl())

class MagneticGrippersDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_MagneticGrippersSlotOptionImpl())

class ParasiticLinkDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_ParasiticLinkSlotOptionImpl())

class SelfMaintenanceEnhancementDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_SelfMaintenanceEnhancementSlotOptionImpl(isDefaultSuite=True))

# NOTE This component is different from most other slot options as multiple
# instances can be added
class StingerDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_StingerSlotOptionImpl(),
            singular=False)

class AtmosphericSensorDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_AtmosphericSensorSlotOptionImpl())

class EnvironmentalProcessorDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_EnvironmentalProcessorSlotOptionImpl())
        
class GeigerCounterDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_GeigerCounterSlotOptionImpl())

class LightIntensifierSensorDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_LightIntensifierSensorSlotOptionImpl())     

class OlfactorySensorDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_OlfactorySensorSlotOptionImpl())

class PRISSensorDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_PRISSensorSlotOptionImpl())       

class ThermalSensorDefaultSuiteOption(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_ThermalSensorSlotOptionImpl())  




#   █████████  ████            █████          ███████               █████     ███                             
#  ███░░░░░███░░███           ░░███         ███░░░░░███            ░░███     ░░░                              
# ░███    ░░░  ░███   ██████  ███████      ███     ░░███ ████████  ███████   ████   ██████  ████████    █████ 
# ░░█████████  ░███  ███░░███░░░███░      ░███      ░███░░███░░███░░░███░   ░░███  ███░░███░░███░░███  ███░░  
#  ░░░░░░░░███ ░███ ░███ ░███  ░███       ░███      ░███ ░███ ░███  ░███     ░███ ░███ ░███ ░███ ░███ ░░█████ 
#  ███    ░███ ░███ ░███ ░███  ░███ ███   ░░███     ███  ░███ ░███  ░███ ███ ░███ ░███ ░███ ░███ ░███  ░░░░███
# ░░█████████  █████░░██████   ░░█████     ░░░███████░   ░███████   ░░█████  █████░░██████  ████ █████ ██████ 
#  ░░░░░░░░░  ░░░░░  ░░░░░░     ░░░░░        ░░░░░░░     ░███░░░     ░░░░░  ░░░░░  ░░░░░░  ░░░░ ░░░░░ ░░░░░░  
#                                                        ░███                                                 
#                                                        █████                                                
#                                                       ░░░░░    
        
class SlotOption(robots.SlotOptionInterface):
    """
    Zero-Slot
    - Requirement: Up to Size + TL Zero-Slot options can be added at no slot cost,
    additional zero-slot options cost 1 slot    
    - Requirement: Zero slot options should be incompatible with their default
    suite counterpart
    """
    # TODO: Handle component being incompatible with default suite counterpart
    # - IMPORTANT: If I end up adding slot cost variants of zero slot options to
    #   handle the 1 slot cost for options over the 'free' limit, then those
    #   components will need to be incompatible with the default suite _and_
    #   zero slot equivalents 

    _ZeroSlotCountIncrement = common.ScalarCalculation(
        value=1,
        name='Zero-Slot Count Increment')

    def __init__(
            self,
            impl: _SlotOptionImpl,
            singular: bool = True
            ) -> None:
        super().__init__()
        self._impl = impl
        self._singular = singular

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def componentString(self) -> str:
        return self._impl.componentString()
    
    def typeString(self) -> str:
        return 'Slot Option'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not self._impl.isCompatible(
            sequence=sequence,
            context=context):
            return False
        
        # If the component is singular make it incompatible with it's self
        if self._singular and context.hasComponent(
            componentType=type(self),
            sequence=sequence):
            return False

        return True
    
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
        self._impl.createSteps(
            sequence=sequence,
            context=context,
            typeString=self.typeString())

# TODO: This list needs split into groups like the spreadsheet (chassis,
# medical etc). Each one should be it's own own stage. The individual
# groups should be ordered alphabetically
   
class ActiveCamouflageSlotSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_ActiveCamouflageSlotOptionImpl())

class VisualConcealmentSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_VisualConcealmentSlotOptionImpl(
                incompatibleTypes=[VisualConcealmentDefaultSuiteOption]))

class AudibleConcealmentSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_AudibleConcealmentSlotOptionImpl(
                incompatibleTypes=[AudibleConcealmentDefaultSuiteOption]))

class OlfactoryConcealmentSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_OlfactoryConcealmentSlotOptionImpl(
                incompatibleTypes=[OlfactoryConcealmentDefaultSuiteOption]))

class CorrosiveEnvironmentProtectionSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_CorrosiveEnvironmentProtectionSlotOptionImpl())

class HostileEnvironmentProtectionSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_HostileEnvironmentProtectionSlotOptionImpl(
                incompatibleTypes=[HostileEnvironmentProtectionDefaultSuiteOption]))

class InsidiousEnvironmentProtectionSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_InsidiousEnvironmentProtectionSlotOptionImpl())
        
class RadiationEnvironmentProtectionSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_RadiationEnvironmentProtectionSlotOptionImpl())

class ReflectArmourSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_ReflectArmourSlotOptionImpl(
                incompatibleTypes=[ReflectArmourDefaultSuiteOption]))
        
class SelfRepairingChassisSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_SelfRepairingChassisSlotOptionImpl())        

class SolarCoatingSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_SolarCoatingSlotOptionImpl(
                incompatibleTypes=[SolarCoatingDefaultSuiteOption]))
        
class SubmersibleEnvironmentProtectionSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_SubmersibleEnvironmentProtectionSlotOptionImpl())      

class VacuumEnvironmentProtectionSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_VacuumEnvironmentProtectionSlotOptionImpl(
                incompatibleTypes=[VacuumEnvironmentProtectionDefaultSuiteOption]))
        
class DomesticCleaningEquipmentSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_DomesticCleaningEquipmentSlotOptionImpl())
        
class IndustrialCleaningEquipmentSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_IndustrialCleaningEquipmentSlotOptionImpl())        

class DroneInterfaceSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_DroneInterfaceSlotOptionImpl(
                isDefaultSuite=False,
                incompatibleTypes=[DroneInterfaceDefaultSuiteOption]))
        
    # List component _from this stage_ that should be processed before this
    # component
    def orderAfter(self) -> typing.List[typing.Type[construction.ComponentInterface]]:
        dependencies = super().orderAfter()
        dependencies.append(TransceiverSlotOption)
        return dependencies

class EncryptionModuleSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_EncryptionModuleSlotOptionImpl(
                incompatibleTypes=[EncryptionModuleDefaultSuiteOption]))
        
class HighFidelitySoundSystemSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_HighFidelitySoundSystemSlotOptionImpl())
        
class RoboticDroneControllerSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_RoboticDroneControllerSlotOptionImpl())
        
    # List component _from this stage_ that should be processed before this
    # component
    def orderAfter(self) -> typing.List[typing.Type[construction.ComponentInterface]]:
        dependencies = super().orderAfter()
        dependencies.append(TransceiverSlotOption)
        return dependencies        
        
class SatelliteUplinkSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_SatelliteUplinkSlotOptionImpl())
        
    # List component _from this stage_ that should be processed before this
    # component
    def orderAfter(self) -> typing.List[typing.Type[construction.ComponentInterface]]:
        dependencies = super().orderAfter()
        dependencies.append(TransceiverSlotOption)
        return dependencies
        
class SwarmControllerSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_SwarmControllerSlotOptionImpl())
        
    # List component _from this stage_ that should be processed before this
    # component
    def orderAfter(self) -> typing.List[typing.Type[construction.ComponentInterface]]:
        dependencies = super().orderAfter()
        dependencies.append(TransceiverSlotOption)
        return dependencies        
        
class TightbeamCommunicatorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_TightbeamCommunicatorSlotOptionImpl())        

class TransceiverSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_TransceiverSlotOptionImpl(
                isDefaultSuite=False,
                incompatibleTypes=[TransceiverDefaultSuiteOption]))
        
    def range(self) -> int:
        assert(isinstance(self._impl, _TransceiverSlotOptionImpl))
        return self._impl.range()        

class VideoScreenSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_VideoScreenSlotOptionImpl(
                isDefaultSuite=False,
                incompatibleTypes=[VideoScreenDefaultSuiteOption]))

class VoderSpeakerSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_VoderSpeakerSlotOptionImpl(
                isDefaultSuite=False,
                incompatibleTypes=[VoderSpeakerDefaultSuiteOption]))

class WirelessDataLinkSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_WirelessDataLinkSlotOptionImpl(
                isDefaultSuite=False,
                incompatibleTypes=[WirelessDataLinkDefaultSuiteOption]))

class GeckoGrippersSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_GeckoGrippersSlotOptionImpl(
                incompatibleTypes=[GeckoGrippersDefaultSuiteOption]))

# NOTE: As this is not a singular component it's NOT incompatible with its
# default suite counterpart
class InjectorNeedleSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_InjectorNeedleSlotOptionImpl(),
            singular=False)

class LaserDesignatorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_LaserDesignatorSlotOptionImpl(
                incompatibleTypes=[LaserDesignatorDefaultSuiteOption]))

class MagneticGrippersSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_MagneticGrippersSlotOptionImpl(
                incompatibleTypes=[MagneticGrippersDefaultSuiteOption]))

class ParasiticLinkSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_ParasiticLinkSlotOptionImpl(
                incompatibleTypes=[ParasiticLinkDefaultSuiteOption]))

class SelfMaintenanceEnhancementSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_SelfMaintenanceEnhancementSlotOptionImpl(
                isDefaultSuite=False,
                incompatibleTypes=[SelfMaintenanceEnhancementDefaultSuiteOption]))

# NOTE: As this is not a singular component it's NOT incompatible with its
# default suite counterpart
class StingerSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_StingerSlotOptionImpl(),
            singular=False)

class AtmosphericSensorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_AtmosphericSensorSlotOptionImpl(
                incompatibleTypes=[AtmosphericSensorDefaultSuiteOption]))

class AuditorySensorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_AuditorySensorSlotOptionImpl(
                isDefaultSuite=False,
                incompatibleTypes=[AuditorySensorDefaultSuiteOption]))

class EnvironmentalProcessorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_EnvironmentalProcessorSlotOptionImpl(
                incompatibleTypes=[EnvironmentalProcessorDefaultSuiteOption]))
        
class GeigerCounterSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_GeigerCounterSlotOptionImpl(
                incompatibleTypes=[GeigerCounterDefaultSuiteOption]))

class LightIntensifierSensorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_LightIntensifierSensorSlotOptionImpl(
                incompatibleTypes=[LightIntensifierSensorDefaultSuiteOption]))

class OlfactorySensorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_OlfactorySensorSlotOptionImpl(
                incompatibleTypes=[OlfactorySensorDefaultSuiteOption]))

class PRISSensorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_PRISSensorSlotOptionImpl(
                incompatibleTypes=[PRISSensorDefaultSuiteOption]))

class ThermalSensorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_ThermalSensorSlotOptionImpl(
                incompatibleTypes=[ThermalSensorDefaultSuiteOption]))

class VisualSpectrumSensorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_VisualSpectrumSensorSlotOptionImpl(
                isDefaultSuite=False,
                incompatibleTypes=[VisualSpectrumSensorDefaultSuiteOption]))

class MedicalChamberSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_MedicalChamberSlotOptionImpl())
        
class MedkitSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_MedkitSlotOptionImpl())
        
    # List component _from this stage_ that should be processed before this
    # component
    def orderAfter(self) -> typing.List[typing.Type[construction.ComponentInterface]]:
        dependencies = super().orderAfter()
        dependencies.append(MedicalChamberSlotOption)
        return dependencies        

class AgriculturalEquipmentSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_AgriculturalEquipmentSlotOptionImpl(),
            singular=False)
        
class AutobarSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_AutobarSlotOptionImpl())
        
class AutochefSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_AutochefSlotOptionImpl())
        
class AutopilotSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_AutopilotSlotOptionImpl())
        
class BioreactionChamberSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_BioreactionChamberSlotOptionImpl())
        
class ConstructionEquipmentSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_ConstructionEquipmentSlotOptionImpl(),
            singular=False)
        
class FabricationChamberSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_FabricationChamberSlotOptionImpl())
        
class ForkliftChamberSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_ForkliftSlotOptionImpl())
        
class HolographicProjectorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_HolographicProjectorSlotOptionImpl())
        
class MiningEquipmentSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_MiningEquipmentSlotOptionImpl(),
            singular=False)        

class NavigationSystemSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_NavigationSystemSlotOptionImpl())
        
class SelfDestructSystemSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_SelfDestructSystemSlotOptionImpl())
        
class StealthSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_StealthSlotOptionImpl())        
        
class StorageCompartmentSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_StorageCompartmentSlotOptionImpl(),
            singular=False)                
        
class VideoProjectorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_VideoProjectorSlotOptionImpl(),
            singular=False)   
        
class ExternalPowerSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_ExternalPowerSlotOptionImpl())      
        
class NoInternalPowerSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_NoInternalPowerSlotOptionImpl())     
        
class RTGSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_RTGSlotOptionImpl(),
            singular=False)
        
class SolarPowerUnitSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_SolarPowerUnitSlotOptionImpl(),
            singular=False)
        
class QuickChargerSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_QuickChargerSlotOptionImpl())            
        
class BioscannerSensorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_BioscannerSensorSlotOptionImpl())

class DensitometerSensorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_DensitometerSensorSlotOptionImpl())   

class NeuralActivitySensorSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_NeuralActivitySensorSlotOptionImpl())           

class PlanetologySensorSuiteSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_PlanetologySensorSuiteSlotOptionImpl())     

class CuttingTorchSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_CuttingTorchSlotOptionImpl(),
            singular=False)        

class ElectronicsToolkitSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_ElectronicsToolkitSlotOptionImpl())
        
class FireExtinguisherSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_FireExtinguisherSlotOptionImpl())  

class ForensicToolkitSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_ForensicToolkitSlotOptionImpl())  

class MechanicalToolkitSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_MechanicalToolkitSlotOptionImpl())

# NOTE: The Scientific Toolkit is not singular as a robot could have multiple
# for different sciences
class ScientificToolkitSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_ScientificToolkitSlotOptionImpl(),
            singular=False)  
        
class StarshipEngineeringToolkitSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_StarshipEngineeringToolkitSlotOptionImpl())

# NOTE: The Stylist Toolkit is not singular as a robot could have multiple
# for different species
class StylistToolkitSlotOption(SlotOption):
    def __init__(self) -> None:
        super().__init__(
            impl=_StylistToolkitSlotOptionImpl(),
            singular=False)          