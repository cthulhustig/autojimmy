import common
import construction
import enum
import robots
import typing

class _OptionLevel(enum.Enum):
    Primitive = 'Primitive'
    Basic = 'Basic'
    Improved = 'Improved'
    Enhanced = 'Enhanced'
    Advanced = 'Advanced'
    Superior = 'Superior'

#  ███████████                                 █████████  ████            █████       █████                           ████ 
# ░█░░░░░░███                                 ███░░░░░███░░███           ░░███       ░░███                           ░░███ 
# ░     ███░    ██████  ████████   ██████    ░███    ░░░  ░███   ██████  ███████      ░███  █████████████   ████████  ░███ 
#      ███     ███░░███░░███░░███ ███░░███   ░░█████████  ░███  ███░░███░░░███░       ░███ ░░███░░███░░███ ░░███░░███ ░███ 
#     ███     ░███████  ░███ ░░░ ░███ ░███    ░░░░░░░░███ ░███ ░███ ░███  ░███        ░███  ░███ ░███ ░███  ░███ ░███ ░███ 
#   ████     █░███░░░   ░███     ░███ ░███    ███    ░███ ░███ ░███ ░███  ░███ ███    ░███  ░███ ░███ ░███  ░███ ░███ ░███ 
#  ███████████░░██████  █████    ░░██████    ░░█████████  █████░░██████   ░░█████     █████ █████░███ █████ ░███████  █████
# ░░░░░░░░░░░  ░░░░░░  ░░░░░      ░░░░░░      ░░░░░░░░░  ░░░░░  ░░░░░░     ░░░░░     ░░░░░ ░░░░░ ░░░ ░░░░░  ░███░░░  ░░░░░ 
#                                                                                                           ░███           
#                                                                                                           █████          
#                                                                                                          ░░░░░           

class _ZeroSlotImpl(object):
    def __init__(
            self,
            componentString: str,
            minTL: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            perBaseSlotCost: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            constantCost: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            notes: typing.Iterable[str] = None,
            ) -> None:
        super().__init__()

        if minTL != None and not isinstance(minTL, common.ScalarCalculation):
            minTL = common.ScalarCalculation(
                value=minTL,
                name=f'{componentString} Minimum TL') 

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

        self._componentString = componentString
        self._minTL = minTL
        self._perBaseSlotCost = perBaseSlotCost
        self._constantCost = constantCost
        self._notes = notes

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

        return True
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        pass

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:
        cost = None
        if self._perBaseSlotCost != None: 
            cost = common.Calculator.multiply(
                lhs=self._perBaseSlotCost,
                rhs=context.baseSlots(sequence=sequence),
                name=f'{self.componentString()} Cost')
        elif self._constantCost != None:
            cost = self._constantCost
            
        if cost:
            step.setCredits(
                credits=construction.ConstantModifier(value=cost))

        if self._notes:
            for note in self._notes:
                step.addNote(note)

class _EnumSelectZeroSlotImpl(_ZeroSlotImpl):
    def __init__(
            self,
            componentString: str,
            enumType: typing.Type[enum.Enum],
            optionId: str,
            optionName: str,
            optionDescription: str,
            optionDefault: enum.Enum,
            minTLMap: typing.Mapping[_OptionLevel, int]
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTL=min(minTLMap.values())) # Absolute min
        
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

        currentTL = context.techLevel()
        options = []
        for level, levelTL in self._minTLMap.items():
            if currentTL >= levelTL:
                options.append(level)
        self._enumOption.setOptions(options=options)

class _VisualConcealmentZeroSlotImpl(_EnumSelectZeroSlotImpl):
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
            ) -> None:
        super().__init__(
            componentString='Visual Concealment',
            enumType=_OptionLevel,
            optionId='Level',
            optionName='Level',
            optionDescription='Specify the concealment level.',
            optionDefault=_OptionLevel.Basic,
            minTLMap=_VisualConcealmentZeroSlotImpl._MinTLMap)

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
            value=_VisualConcealmentZeroSlotImpl._CostPerSlotMap[level],
            name=f'{level.value} Visual Concealment Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=costPerSlot,
            rhs=context.baseSlots(sequence=sequence),
            name=f'{self.componentString()} Cost')

        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
class _AudibleConcealmentZeroSlotImpl(_EnumSelectZeroSlotImpl):
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
            ) -> None:
        super().__init__(
            componentString='Audible Concealment',
            enumType=_OptionLevel,
            optionId='Level',
            optionName='Level',
            optionDescription='Specify the concealment level.',            
            optionDefault=_OptionLevel.Basic,
            minTLMap=_AudibleConcealmentZeroSlotImpl._MinTLMap)

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
            value=_AudibleConcealmentZeroSlotImpl._CostPerSlotMap[level],
            name=f'{level.value} {self.componentString()} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=costPerSlot,
            rhs=context.baseSlots(sequence=sequence),
            name=f'{self.componentString()} Cost')

        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
class _OlfactoryConcealmentZeroSlotImpl(_EnumSelectZeroSlotImpl):
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
            ) -> None:
        super().__init__(
            componentString='Olfactory Concealment',
            enumType=_OptionLevel,
            optionId='Level',
            optionName='Level',
            optionDescription='Specify the concealment level.', 
            optionDefault=_OptionLevel.Basic,           
            minTLMap=_OlfactoryConcealmentZeroSlotImpl._MinTLMap)  

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
            value=_OlfactoryConcealmentZeroSlotImpl._CostPerSlotMap[level],
            name=f'{level.value} {self.componentString()} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=costPerSlot,
            rhs=context.baseSlots(sequence=sequence),
            name=f'{self.componentString()} Cost')

        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
class _HostileEnvironmentProtectionZeroSlotImpl(_ZeroSlotImpl):
    """
    - Min TL: 6
    - Cost: Cr300 * Base Slots
    - Trait: Rads +500
    """
    _RadsTrait = common.ScalarCalculation(
        value=+500,
        name='Hostile Environment Protection Rads Modifier')

    def __init__(
            self,
            ) -> None:
        super().__init__(
            componentString='Hostile Environment Protection',
            minTL=6,
            perBaseSlotCost=300)
        
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
                value=_HostileEnvironmentProtectionZeroSlotImpl._RadsTrait)))
        
class _ReflectArmourZeroSlotImpl(_ZeroSlotImpl):
    """
    - Min TL: 10
    - Cost: Cr100 * Base Slots
    - Requirement: Not compatible with Camouflage: Visual Concealment
    - Requirement: Not compatible with Solar Coating
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
            ) -> None:
        super().__init__(
            componentString='Reflect Armour',
            minTL=10,
            perBaseSlotCost=100)
        
class _SolarCoatingZeroSlotImpl(_EnumSelectZeroSlotImpl):
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
            ) -> None:
        super().__init__(
            componentString='Solar Coating',
            enumType=_OptionLevel,
            optionId='Level',
            optionName='Level',
            optionDescription='Specify the solar coating level.',
            optionDefault=_OptionLevel.Basic,            
            minTLMap=_SolarCoatingZeroSlotImpl._MinTLMap)

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
            value=_SolarCoatingZeroSlotImpl._CostPerSlotMap[level],
            name=f'{level.value} {self.componentString()} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=costPerSlot,
            rhs=context.baseSlots(sequence=sequence),
            name=f'{self.componentString()} Cost')

        step.setCredits(
            credits=construction.ConstantModifier(value=cost))

class _VacuumEnvironmentProtectionZeroSlotImpl(_EnumSelectZeroSlotImpl):
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
            ) -> None:
        super().__init__(
            componentString='Vacuum Environment Protection',
            enumType=_VacuumEnvironmentProtectionZeroSlotImpl._ProtectionType,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the protection type.',
            optionDefault=_VacuumEnvironmentProtectionZeroSlotImpl._ProtectionType.Standard,      
            minTLMap=_VacuumEnvironmentProtectionZeroSlotImpl._MinTLMap)   

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
        assert(isinstance(protection, _VacuumEnvironmentProtectionZeroSlotImpl._ProtectionType))

        costPerSlot = common.ScalarCalculation(
            value=_VacuumEnvironmentProtectionZeroSlotImpl._CostPerSlotMap[protection],
            name=f'{protection.value} {self.componentString()} Cost Per Slot')
        cost = common.Calculator.multiply(
            lhs=costPerSlot,
            rhs=context.baseSlots(sequence=sequence),
            name=f'{self.componentString()} Cost')

        step.setCredits(
            credits=construction.ConstantModifier(value=cost))
        
class _DroneInterfaceZeroSlotImpl(_ZeroSlotImpl):
    """
    Min TL: 6
    Cost: Cr100 or free if Default Suite
    Requirement: A drone interface requires a separate transceiver to be installed (p34)
    """
    # TODO: Handle the fact it requires a receiver
    # - I think this means it you also have to take a zero-slot or slot cost
    #   transceiver (there are transceivers of both types)
    # - Could handle it with a note in finalisation.
    #   - I think I do something similar in the gunsmith where Warning notes are
    #     added
    # - Could add a separate step in this component for a transceiver
    #   - Might actually need to be the component code that does this as it
    #     creates the step not the impl
    #   - Would need to make the transceiver zero-slot _and_ slot cost options
    #     incompatible with the drone interface so the user doesn't add it twice
    #   - Ideally it would have a check box that controls if it's added
    #     (defaulted to true). This would allow for things like external
    #     transceivers

    def __init__(
            self,
            isDefaultSuite: bool
            ) -> None:
        super().__init__(
            componentString='Drone Interface',
            minTL=6,
            constantCost=None if isDefaultSuite else 100)
        
class _EncryptionModuleZeroSlotImpl(_ZeroSlotImpl):
    """
    - Min TL: 6
    - Cost: Cr4000
    """
    def __init__(self) -> None:
        super().__init__(
            componentString='Encryption Module',
            minTL=6,
            constantCost=4000)
        
class _TransceiverZeroSlotImpl(_EnumSelectZeroSlotImpl):
    """
    Basic 5km
        - Min TL: 7
        - Cost: Cr250 or free if Default Suite
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
    Enhanced 50km
        - Min TL: 10
        - Cost: Cr250
    Enhanced 500km
        - Min TL: 11
        - Cost: Cr500
    Enhanced 5,000km
        - Min TL: 12
        - Cost: Cr1000
    Advanced 50km
        - Min TL: 13
        - Cost: Cr100
    Advanced 500km
        - Min TL: 14
        - Cost: Cr250
    Advanced 5,000km
        - Min TL: 15
        - Cost: Cr500
    """
    # NOTE: There are also larger transceivers available as slot cost options
    # TODO: Figure out how I'm going to handle the fact there are zero slot
    # and slot cost transceivers
    # TODO: I think there is scope for improving usability by reducing the
    # options that are shown to the user as some options wouldn't make logical
    # sense. For example, if your at designing a TL 14 robot there seems little
    # point giving the user the option to select Enhanced 500km as Advanced
    # 500km is half the price so they would only ever select that. I think it
    # should be possible to just get it down to a drop down where the user
    # selects the range they desired from a list of ranges available at that TL.
    # IMPORTANT: There may be some complexity around the 2 types that are free
    # for default suite

    class _TransceiverType(enum.Enum):
        Basic5km = 'Basic 5km'
        Improved5km = 'Improved 5km'
        Improved50km = 'Improved 50km'
        Improved500km = 'Improved 500km'
        Improved5000km = 'Improved 5,000km'
        Enhanced50km = 'Enhanced 50km'
        Enhanced500km = 'Enhanced 500km'
        Enhanced5000km = 'Enhanced 5,000km'
        Advanced50km = 'Advanced 50km'
        Advanced500km = 'Advanced 500km'
        Advanced5000km = 'Advanced 5,000km'

    _MinTLMap = {
        _TransceiverType.Basic5km: 7,
        _TransceiverType.Improved5km: 8,
        _TransceiverType.Improved50km: 8,
        _TransceiverType.Improved500km: 9,
        _TransceiverType.Improved5000km: 9,
        _TransceiverType.Enhanced50km: 10,
        _TransceiverType.Enhanced500km: 11,
        _TransceiverType.Enhanced5000km: 12,
        _TransceiverType.Advanced50km: 13,
        _TransceiverType.Advanced500km: 14,
        _TransceiverType.Advanced5000km: 15
    }

    _CostMap = {
        _TransceiverType.Basic5km: 250,
        _TransceiverType.Improved5km: 100,
        _TransceiverType.Improved50km: 500,
        _TransceiverType.Improved500km: 1000,
        _TransceiverType.Improved5000km: 5000,
        _TransceiverType.Enhanced50km: 250,
        _TransceiverType.Enhanced500km: 500,
        _TransceiverType.Enhanced5000km: 1000,
        _TransceiverType.Advanced50km: 100,
        _TransceiverType.Advanced500km: 250,
        _TransceiverType.Advanced5000km: 500
    }

    _FreeDefaultSuiteTypes = [
        _TransceiverType.Basic5km,
        _TransceiverType.Improved5km
    ]

    def __init__(
            self,
            isDefaultSuite: bool
            ) -> None:
        super().__init__(
            componentString='Transceiver',
            enumType=_TransceiverZeroSlotImpl._TransceiverType,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the transceiver type.',
            optionDefault=_TransceiverZeroSlotImpl._TransceiverType.Basic5km,                  
            minTLMap=_TransceiverZeroSlotImpl._MinTLMap)
        
        self._isDefaultSuite = isDefaultSuite

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
        assert(isinstance(transceiverType, _TransceiverZeroSlotImpl._TransceiverType))

        if not self._isDefaultSuite or \
                (transceiverType not in _TransceiverZeroSlotImpl._FreeDefaultSuiteTypes):
            cost = common.ScalarCalculation(
                value=_TransceiverZeroSlotImpl._CostMap[transceiverType],
                name=f'{transceiverType.value} {self.componentString()} Cost')

            step.setCredits(
                credits=construction.ConstantModifier(value=cost))
            
class _VideoScreenZeroSlotImpl(_EnumSelectZeroSlotImpl):
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
        _ScreenType.BasicPanel: (200, True), # TODO: Or free for default suite
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
            isDefaultSuite: bool
            ) -> None:
        super().__init__(
            componentString='Video Screen',
            enumType=_VideoScreenZeroSlotImpl._ScreenType,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the screen type.',
            optionDefault=_VideoScreenZeroSlotImpl._ScreenType.BasicPanel,                      
            minTLMap=_VideoScreenZeroSlotImpl._MinTLMap)
        
        self._isDefaultSuite = isDefaultSuite   

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
        assert(isinstance(screenType, _VideoScreenZeroSlotImpl._ScreenType))

        if not self._isDefaultSuite or \
            screenType not in _VideoScreenZeroSlotImpl._FreeDefaultSuiteTypes:

            cost, isConstantCost = _VideoScreenZeroSlotImpl._CostMap[screenType]
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
        
class _VoderSpeakerZeroSlotImpl(_EnumSelectZeroSlotImpl):
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
            isDefaultSuite: bool
            ) -> None:
        super().__init__(
            componentString='Voder Speaker',
            enumType=_VoderSpeakerZeroSlotImpl._SpeakerType,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the speaker type.',            
            optionDefault=_VoderSpeakerZeroSlotImpl._SpeakerType.Standard,                      
            minTLMap=_VoderSpeakerZeroSlotImpl._MinTLMap)

        self._isDefaultSuite = isDefaultSuite

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
        assert(isinstance(speakerType, _VoderSpeakerZeroSlotImpl._SpeakerType))

        if not self._isDefaultSuite or \
            (speakerType not in _VoderSpeakerZeroSlotImpl._FreeDefaultSuiteTypes):
            cost = common.ScalarCalculation(
                value=_VoderSpeakerZeroSlotImpl._CostMap[speakerType],
                name=f'{speakerType.value} {self.componentString()} Cost')

            step.setCredits(
                credits=construction.ConstantModifier(value=cost))

class _WirelessDataLinkZeroSlotImpl(_ZeroSlotImpl):
    """
    Min TL: 8
    Cost: Cr10 or free if Default Suite
    """
    def __init__(
            self,
            isDefaultSuite: bool
            ) -> None:
        super().__init__(
            componentString='Wireless Data Link',
            minTL=8,
            constantCost=None if isDefaultSuite else 10)
        
class _GeckoGrippersZeroSlotImpl(_ZeroSlotImpl):
    """
    Min TL: 9
    Cost: Cr500 * Base Slots
    """
    def __init__(self) -> None:
        super().__init__(
            componentString='Gecko Grippers',
            minTL=9,
            perBaseSlotCost=500)
        
class _InjectorNeedleZeroSlotImpl(_ZeroSlotImpl):
    """
    Min TL: 7
    Cost: Cr20
    Requirement: Multiple Injector Needle can be installed, each taking up a zero-slot option
    """
    # TODO: Handle multiple needles
    # - Could make this an integer option
    #   - This would need to handle the case where some of the needles take up
    #     a slot due to the zero slot limit being reached
    # - Could make it so it's not incompatible with its self
    #   - This would need to be done in the component by overriding the base
    #     comparability check
    def __init__(self) -> None:
        super().__init__(
            componentString='Injector Needle',
            minTL=7,
            constantCost=20) 

class _LaserDesignatorZeroSlotImpl(_ZeroSlotImpl):
    """
    Min TL: 7
    Cost: Cr500
    """
    # TODO: Fire Control System needs to add a note that it receives a DM+2 to
    # attack designated targets
    def __init__(self) -> None:
        super().__init__(
            componentString='Laser Designator',
            minTL=7,
            constantCost=500)
        
class _MagneticGrippersZeroSlotImpl(_ZeroSlotImpl):
    """
    Min TL: 8
    Cost: Cr10 * Base Slots
    Note: Robot can grip to metallic surfaces in gravity of 0-1.5G
    """
    def __init__(self) -> None:
        super().__init__(
            componentString='Magnetic Grippers',
            minTL=8,
            perBaseSlotCost=10,
            notes=['Robot can grip to metallic surfaces in gravity of 0-1.5G'])
        
class _ParasiticLinkZeroSlotImpl(_ZeroSlotImpl):
    """
    Min TL: 10
    Cost: Cr10000
    """
    def __init__(self) -> None:
        super().__init__(
            componentString='Parasitic Link',
            minTL=10,
            constantCost=10000)
        
class _SelfMaintenanceEnhancementZeroSlotImpl(_EnumSelectZeroSlotImpl):
    """
    Basic
    - Min TL: 7
    - Cost: Cr20000 * Base Slots
    - Note: The robot requires maintenance every 12 years.
    - Note: If the maintenance schedule is not followed, a Malfunction Check (108) must be made every year
    Improved
    - Min TL: 8
    - Cost: Cr50000 * Base Slots
    - Note: The robot requires maintenance every 24 years.
    - Note: If the maintenance schedule is not followed, a Malfunction Check (108) must be made every 2 years
    """
    # TODO: This is another component where there are zero-slot and slot cost
    # versions

    _MinTLMap = {
        _OptionLevel.Basic: 7,
        _OptionLevel.Improved: 8
    }

    # Data Structure: Cost Per Base Slot, Maintenance Period, Malfunction Check
    _DataMap = {
        _OptionLevel.Basic: (20000, 12, 1),
        _OptionLevel.Improved: (50000, 24, 2)
    }

    def __init__(self) -> None:
        super().__init__(
            componentString='Self-Maintenance Enhancement',
            enumType=_OptionLevel,
            optionId='Level',
            optionName='Level',
            optionDescription='Specify the maintenance level.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_SelfMaintenanceEnhancementZeroSlotImpl._MinTLMap)
        
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

        perSlotCost, maintenancePeriod, malfunctionCheck = \
            _SelfMaintenanceEnhancementZeroSlotImpl._DataMap[level]
        
        baseString = f'{level.value} {self.componentString()}'
        perSlotCost = common.ScalarCalculation(
            value=perSlotCost,
            name=f'{baseString} Per Base Slot Cost')
        totalCost = common.Calculator.multiply(
            lhs=perSlotCost,
            rhs=context.baseSlots(sequence=sequence),
            name=f'{baseString} Total Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=totalCost))        

        step.addNote(
            note='The robot requires maintenance every {period} years'.format(
                period=maintenancePeriod))
        step.addNote(
            note='If the maintenance schedule is not followed, a Malfunction Check must be made every {wording} (p108) '.format(
                wording='year' if malfunctionCheck == 1 else f'{malfunctionCheck} years'))

class _StingerZeroSlotImpl(_ZeroSlotImpl):
    """
    Min TL: 7
    Cost: Cr10
    Requirement: Multiple Stingers can be installed each taking up a zero-slot option
    Note: Does 1 point of damage and has AP equal to the base armour of a robot of it's TL (see table on p19)
    """
    # TODO: Handle multiple stingers
    # - Could make this an integer option
    #   - This would need to handle the case where some of the stingers take up
    #     a slot due to the zero slot limit being reached
    # - Could make it so it's not incompatible with its self
    #   - This would need to be done in the component by overriding the base
    #     comparability check

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

    def __init__(self) -> None:
        super().__init__(
            componentString='Stinger',
            minTL=6,
            constantCost=10)
        
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
            apTrait = _StingerZeroSlotImpl._TL18PlusAPTrait
        elif currentTL >= 12:
            apTrait = _StingerZeroSlotImpl._TL12to17APTrait
        elif currentTL >= 9:
            apTrait = _StingerZeroSlotImpl._TL9to11APTrait
        elif currentTL >= 6:
            apTrait = _StingerZeroSlotImpl._TL6to8APTrait

        if apTrait:        
            step.addNote(f'Does 1 point of damage and has AP {apTrait.value()}')

class _AtmosphericSensorZeroSlotImpl(_ZeroSlotImpl):
    """
    Min TL: 8
    Cost: Cr100
    """
    def __init__(self) -> None:
        super().__init__(
            componentString='Atmospheric Sensor',
            minTL=8,
            constantCost=100)

class _AuditorySensorZeroSlotImpl(_EnumSelectZeroSlotImpl):
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
            isDefaultSuite: bool
            ) -> None:
        super().__init__(
            componentString='Auditory Sensor',
            enumType=_VoderSpeakerZeroSlotImpl._SpeakerType,
            optionId='Type',
            optionName='Type',
            optionDescription='Specify the sensor type.',            
            optionDefault=_VoderSpeakerZeroSlotImpl._SpeakerType.Standard,                      
            minTLMap=_VoderSpeakerZeroSlotImpl._MinTLMap)

        self._isDefaultSuite = isDefaultSuite

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
        assert(isinstance(speakerType, _VoderSpeakerZeroSlotImpl._SpeakerType))

        if not self._isDefaultSuite or \
            (speakerType not in _AuditorySensorZeroSlotImpl._FreeDefaultSuiteTypes):
            cost = common.ScalarCalculation(
                value=_VoderSpeakerZeroSlotImpl._CostMap[speakerType],
                name=f'{speakerType.value} {self.componentString()} Cost')

            step.setCredits(
                credits=construction.ConstantModifier(value=cost))
            
        if speakerType == _AuditorySensorZeroSlotImpl._SensorType.BroadSpectrum:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=robots.RobotAttributeId.HeightenedSenses))

class _EnvironmentalProcessorZeroSlotImpl(_ZeroSlotImpl):
    """
    Min TL: 10
    Cost: Cr10000
    Trait: Heightened Senses
    """
    def __init__(self) -> None:
        super().__init__(
            componentString='Environmental Processor',
            minTL=10,
            constantCost=10000)
        
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

class _GeigerCounterZeroSlotImpl(_ZeroSlotImpl):
    """
    Min TL: 8
    Cost: Cr400
    """
    def __init__(self) -> None:
        super().__init__(
            componentString='Geiger Counter',
            minTL=8,
            constantCost=400)
        
class _LightIntensifierSensorZeroSlotImpl(_EnumSelectZeroSlotImpl):
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

    def __init__(self) -> None:
        super().__init__(
            componentString='Light Intensifier Sensor',
            enumType=_OptionLevel,
            optionId='Level',
            optionName='Level',
            optionDescription='Specify the sensor level.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_LightIntensifierSensorZeroSlotImpl._MinTLMap)
        
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

        cost, trait = _LightIntensifierSensorZeroSlotImpl._DataMap[level]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{level.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))        

        if trait:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=trait))
            
class _OlfactorySensorZeroSlotImpl(_EnumSelectZeroSlotImpl):
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

    def __init__(self) -> None:
        super().__init__(
            componentString='Olfactory Sensor',
            enumType=_OptionLevel,
            optionId='Level',
            optionName='Level',
            optionDescription='Specify the sensor level.',            
            optionDefault=_OptionLevel.Basic,                      
            minTLMap=_OlfactorySensorZeroSlotImpl._MinTLMap)
        
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

        cost, trait = _OlfactorySensorZeroSlotImpl._DataMap[level]

        cost = common.ScalarCalculation(
            value=cost,
            name=f'{level.value} {self.componentString()} Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))        

        if trait:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=trait))
            
class _PRISSensorZeroSlotImpl(_ZeroSlotImpl):
    """
    Min TL: 12
    Cost: Cr2000
    Trait: IR/UV Vision
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='PRIS Sensor',
            minTL=12,
            constantCost=2000)

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
        
class _ThermalSensorZeroSlotImpl(_ZeroSlotImpl):
    """
    - Min TL: 6
    - Cost: Cr500
    - Trait: IR Vision
    """
    # TODO: According to p39 this is redundant if the robot has the TL 9 Light
    # Intensifier Sensor or PRIS Sensor. I'm not sure if it's worth the hassle
    # of adding that compatibility check

    def __init__(self) -> None:
        super().__init__(
            componentString='Thermal Sensor',
            minTL=6,
            constantCost=500)

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

class _VisualSpectrumSensorZeroSlotImpl(_ZeroSlotImpl):
    """
    - 
    - Min TL: 7
    - Cost: Cr50 or free if Default Suite
    """
    def __init__(
            self,
            isDefaultSuite: bool
            ) -> None:
        super().__init__(
            componentString='Visual Spectrum Sensor',
            minTL=7,
            constantCost=None if isDefaultSuite else 50)



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
            impl: _ZeroSlotImpl
            ) -> None:
        super().__init__()
        self._impl = impl

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
        
        # Don't allow multiple options of the same type
        return not context.hasComponent(
            componentType=type(self),
            sequence=sequence)        
    
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

class VisualConcealmentDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_VisualConcealmentZeroSlotImpl())

class AudibleConcealmentDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_AudibleConcealmentZeroSlotImpl())

class OlfactoryConcealmentDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_OlfactoryConcealmentZeroSlotImpl())

class HostileEnvironmentProtectionDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_HostileEnvironmentProtectionZeroSlotImpl())  

class ReflectArmourDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_ReflectArmourZeroSlotImpl())

class SolarCoatingDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_SolarCoatingZeroSlotImpl()) 

class VacuumEnvironmentProtectionDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_VacuumEnvironmentProtectionZeroSlotImpl()) 

class DroneInterfaceDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_DroneInterfaceZeroSlotImpl(isDefaultSuite=True)) 

class EncryptionModuleDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_EncryptionModuleZeroSlotImpl())

class TransceiverDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_TransceiverZeroSlotImpl(isDefaultSuite=True))

class VideoScreenDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_VideoScreenZeroSlotImpl(isDefaultSuite=True))

class VoderSpeakerDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_VoderSpeakerZeroSlotImpl(isDefaultSuite=True))

class WirelessDataLinkDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_WirelessDataLinkZeroSlotImpl(isDefaultSuite=True))

class GeckoGrippersDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_GeckoGrippersZeroSlotImpl())

class InjectorNeedleDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_InjectorNeedleZeroSlotImpl())

class LaserDesignatorDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_LaserDesignatorZeroSlotImpl())

class MagneticGrippersDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_MagneticGrippersZeroSlotImpl())

class ParasiticLinkDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_ParasiticLinkZeroSlotImpl())

class SelfMaintenanceEnhancementDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_SelfMaintenanceEnhancementZeroSlotImpl())

class StingerDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_StingerZeroSlotImpl())

class AtmosphericSensorDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_AtmosphericSensorZeroSlotImpl())

class AuditorySensorDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_AuditorySensorZeroSlotImpl(isDefaultSuite=True))

class EnvironmentalProcessorDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_EnvironmentalProcessorZeroSlotImpl())
        
class GeigerCounterDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_GeigerCounterZeroSlotImpl())

class LightIntensifierSensorDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_LightIntensifierSensorZeroSlotImpl())     

class OlfactorySensorDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_OlfactorySensorZeroSlotImpl())

class PRISSensorDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_PRISSensorZeroSlotImpl())       

class ThermalSensorDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_ThermalSensorZeroSlotImpl())  

class VisualSpectrumSensorDefaultSuite(DefaultSuiteOption):
    def __init__(self) -> None:
        super().__init__(impl=_VisualSpectrumSensorZeroSlotImpl(isDefaultSuite=True))         



#  ███████████                                         █████████  ████            █████   
# ░█░░░░░░███                                         ███░░░░░███░░███           ░░███    
# ░     ███░    ██████  ████████   ██████            ░███    ░░░  ░███   ██████  ███████  
#      ███     ███░░███░░███░░███ ███░░███ ██████████░░█████████  ░███  ███░░███░░░███░   
#     ███     ░███████  ░███ ░░░ ░███ ░███░░░░░░░░░░  ░░░░░░░░███ ░███ ░███ ░███  ░███    
#   ████     █░███░░░   ░███     ░███ ░███            ███    ░███ ░███ ░███ ░███  ░███ ███
#  ███████████░░██████  █████    ░░██████            ░░█████████  █████░░██████   ░░█████ 
# ░░░░░░░░░░░  ░░░░░░  ░░░░░      ░░░░░░              ░░░░░░░░░  ░░░░░  ░░░░░░     ░░░░░  
        
class ZeroSlotOption(robots.ZeroSlotOptionInterface):
    """
    Requirement: Up to Size + TL Zero-Slot options can be added at no slot cost,
    additional zero-slot options cost 1 slot    
    Requirement: Zero slot options should be incompatible with their default
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
            impl: _ZeroSlotImpl
            ) -> None:
        super().__init__()
        self._impl = impl

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def componentString(self) -> str:
        return self._impl.componentString()
    
    def typeString(self) -> str:
        return 'Zero-Slot'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not self._impl.isCompatible(
            sequence=sequence,
            context=context):
            return False
        
        # Don't allow multiple options of the same type
        return not context.hasComponent(
            componentType=type(self),
            sequence=sequence)        
    
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
        
        slots = self._calcSlotRequirement(
            sequence=sequence,
            context=context)
        if slots:
            step.setSlots(slots=construction.ConstantModifier(value=slots))

        # Increment the zero-slot count, if this is the first zero-slot option
        # it will be set to 1
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.ZeroSlotCount,
            modifier=construction.ConstantModifier(
                value=ZeroSlotOption._ZeroSlotCountIncrement)))
                        
        context.applyStep(
            sequence=sequence,
            step=step)
        
    def _calcSlotRequirement(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[common.ScalarCalculation]:
        robotSize = context.attributeValue(
            attributeId=robots.RobotAttributeId.Size,
            sequence=sequence)
        assert(isinstance(robotSize, common.ScalarCalculation))
       
        limit = robotSize.value() + context.techLevel()
                
        currentCount = context.attributeValue(
            attributeId=robots.RobotAttributeId.ZeroSlotCount,
            sequence=sequence)
        if not currentCount:
            return None
        elif isinstance(currentCount, common.ScalarCalculation):
            if currentCount.value() < limit:
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

class VisualConcealmentZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_VisualConcealmentZeroSlotImpl())

class AudibleConcealmentZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_AudibleConcealmentZeroSlotImpl())

class OlfactoryConcealmentZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_OlfactoryConcealmentZeroSlotImpl())

class HostileEnvironmentProtectionZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_HostileEnvironmentProtectionZeroSlotImpl())  

class ReflectArmourZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_ReflectArmourZeroSlotImpl())

class SolarCoatingZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_SolarCoatingZeroSlotImpl()) 

class VacuumEnvironmentProtectionZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_VacuumEnvironmentProtectionZeroSlotImpl()) 

class DroneInterfaceZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_DroneInterfaceZeroSlotImpl(isDefaultSuite=False)) 

class EncryptionModuleZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_EncryptionModuleZeroSlotImpl())

class TransceiverZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_TransceiverZeroSlotImpl(isDefaultSuite=False))

class VideoScreenZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_VideoScreenZeroSlotImpl(isDefaultSuite=False))

class VoderSpeakerZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_VoderSpeakerZeroSlotImpl(isDefaultSuite=False))

class WirelessDataLinkZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_WirelessDataLinkZeroSlotImpl(isDefaultSuite=False))

class GeckoGrippersZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_GeckoGrippersZeroSlotImpl())

class InjectorNeedleZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_InjectorNeedleZeroSlotImpl())

class LaserDesignatorZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_LaserDesignatorZeroSlotImpl())

class MagneticGrippersZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_MagneticGrippersZeroSlotImpl())

class ParasiticLinkZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_ParasiticLinkZeroSlotImpl())

class SelfMaintenanceEnhancementZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_SelfMaintenanceEnhancementZeroSlotImpl())

class StingerZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_StingerZeroSlotImpl())

class AtmosphericSensorZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_AtmosphericSensorZeroSlotImpl())

class AuditorySensorZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_AuditorySensorZeroSlotImpl(isDefaultSuite=False))

class EnvironmentalProcessorZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_EnvironmentalProcessorZeroSlotImpl())
        
class GeigerCounterZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_GeigerCounterZeroSlotImpl())

class LightIntensifierSensorZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_LightIntensifierSensorZeroSlotImpl())     

class OlfactorySensorZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_OlfactorySensorZeroSlotImpl())

class PRISSensorZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_PRISSensorZeroSlotImpl())       

class ThermalSensorZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_ThermalSensorZeroSlotImpl())  

class VisualSpectrumSensorZeroSlot(ZeroSlotOption):
    def __init__(self) -> None:
        super().__init__(impl=_VisualSpectrumSensorZeroSlotImpl(isDefaultSuite=False))    


#   █████████  ████            █████         █████████                    █████   
#  ███░░░░░███░░███           ░░███         ███░░░░░███                  ░░███    
# ░███    ░░░  ░███   ██████  ███████      ███     ░░░   ██████   █████  ███████  
# ░░█████████  ░███  ███░░███░░░███░      ░███          ███░░███ ███░░  ░░░███░   
#  ░░░░░░░░███ ░███ ░███ ░███  ░███       ░███         ░███ ░███░░█████   ░███    
#  ███    ░███ ░███ ░███ ░███  ░███ ███   ░░███     ███░███ ░███ ░░░░███  ░███ ███
# ░░█████████  █████░░██████   ░░█████     ░░█████████ ░░██████  ██████   ░░█████ 
#  ░░░░░░░░░  ░░░░░  ░░░░░░     ░░░░░       ░░░░░░░░░   ░░░░░░  ░░░░░░     ░░░░░          
"""
Slot Cost Options
- Chassis Options
    - Active Camouflage
        - Min TL: 15
        - Cost: Cr10000 * Base Slots
        - Slots: 1
        - Skill: Stealth 4
        - Trait: Invisible
        - Note: DM-4 to Recon and Electronics  (sensors) checks to detect the robot
    - Corrosive Environment Protection
        - Min TL: 9
        - Cost: Cr600 * Base Slots
        - Slots: 1
    - Insidious Environment Protection
        - Min TL: 11
        - Cost: Cr3000 * Base Slots
        - Slots: 1
    - Radiation Environment Protection
        - Min TL: 7
        - Cost: Cr600 * Base Slots * levels
        - Slots: 1 per level 
        - Trait: Rads +(TL * 50 * levels)
        - Option: Number of levels (1 to infinity)
    - Self-Repairing Chassis
        - Min TL: 11
        - Cost: Cr1000 * Base Slots
        - Slots: 5% of Base Slots rounded up
    - Submersible Environment Protection
        - <ALL>
            - Option: Number of levels
                - The min is 1 but the max is dependant on the % of base slots each level takes
            - Note: VTOL and aeroplane locomotion can't be used while submerged
            - Note: Locomotion other than aquatic suffers an Agility -2 modifier while submerged
        - Basic
            - Min TL: 4
            - Cost: Cr200 * Base Slots * levels
            - Slots: (5% of Base Slots * levels) rounded up
                - NOTE: Rules explicitly say that rounding is done after multiplying by levels
            - Note: Safe Depth (50m * levels)
        - Improved
            - Min TL: 6
            - Cost: Cr400 * Base Slots * levels
            - Slots: (2% of Base Slots * levels) rounded up
                - NOTE: Rules explicitly say that rounding is done after multiplying by levels            
            - Note: Safe Depth (200m * levels)
        - Enhanced
            - Min TL: 9
            - Cost: Cr800 * Base Slots * levels
            - Slots: (2% of Base Slots * levels) rounded up
                - NOTE: Rules explicitly say that rounding is done after multiplying by levels 
            - Note: Safe Depth (600m * levels)
        - Advanced
            - Min TL: 12
            - Cost: Cr1000 * Base Slots * levels
            - Slots: (2% of Base Slots * levels) rounded up
                - NOTE: Rules explicitly say that rounding is done after multiplying by levels 
            - Note: Safe Depth (2000m * levels)
        - Superior
            - Min TL: 15
            - Cost: Cr2000 * Base Slots * levels
            - Slots: (2% of Base Slots * levels) rounded up
                - NOTE: Rules explicitly say that rounding is done after multiplying by levels 
            - Note: Safe Depth (4000m * levels)
- Cleaning Options
    - <ALL>
        - Option: Number of levels
    - Domestic Cleaning Equipment
        - Small
            - Min TL: 5
            - Cost: Cr100 * levels
            - Slots: 1 * levels
        - Medium
            - Min TL: 5
            - Cost: Cr1000 * levels
            - Slots: 4 * levels
        - Large
            - Min TL: 5
            - Cost: Cr5000 * levels
            - Slots: 8 * levels
    - Industrial Cleaning Equipment
        - Small
            - Min TL: 5
            - Cost: Cr500 * levels
            - Slots: 2 * levels
        - Medium
            - Min TL: 5
            - Cost: Cr5000 * levels
            - Slots: 8 * levels
        - Large
            - Min TL: 5
            - Cost: Cr20000 * levels
            - Slots: 16 * levels
- Communication Options
    - High Fidelity Sound System
        - Basic
            - Min TL: 6
            - Cost: Cr1500
            - Slots: 4
        - Improved
            - Min TL: 8
            - Cost: Cr2500
            - Slots: 3
        - Enhanced
            - Min TL: 11
            - Cost: Cr4000
            - Slots: 3
        - Advanced
            - Min TL: 12
            - Cost: Cr5000
            - Slots: 2
    - Robotic Drone Controller
        - <ALL>
            - Option: Biologically-Controlled check box
                - When checked the controller is limited to 1 drone but the Electronics (remote ops) level isn't limited
                - This affects which comments will be added
            - Complex: The controlling robot must have a Electronics (remote ops) skill
                - Best way I can think to handle this is a finalisation step that adds a warning if the robot doesn't have the skill
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
    - Satellite Uplink
        - Min TL: 6
        - Cost: Cr1000
        - Slots: 2
        - Complex Requirement: Requires a Transceiver with at least 500km range
            - If I'm having zero-slot options in the same stage as slot cost options then this will need a dependsOn relationship to force Satellite Uplink to be added/processed after Transceivers
            - This will have to cope with the fact Transceiver can also be in the Default Suite which will probably be different components
    - Swarm Controller
        - <ALL>
            - Complex: The controlling robot must have a Electronics (remote ops) skill
                - Best way I can think to handle this is a finalisation step that adds a warning if the robot doesn't have the skill
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
    - Tightbeam Communicator
        - Min TL: 8
        - Cost: Cr2000
        - Slots: 1
        - Note: Range is 5000km
    - Transceivers
        - Basic 50km
            - Min TL: 7
            - Cost: Cr1000
            - Slots: 1
        - Basic 500km
            - Min TL: 7
            - Cost: Cr2000
            - Slots: 1
        - Basic 5,000km
            - Min TL: 7
            - Cost: Cr10000
            - Slots: 2
        - Basic 50,000km
            - Min TL: 8
            - Cost: Cr20000
            - Slots: 4
        - Basic 500,000km
            - Min TL: 9
            - Cost: Cr50000
            - Slots: 8
        - Improved 50,000km
            - Min TL: 10
            - Cost: Cr10000
            - Slots: 2
        - Improved 500,000km
            - Min TL: 11
            - Cost: Cr25000
            - Slots: 4
        - Enhanced 50,000km
            - Min TL: 12
            - Cost: Cr5000
            - Slots: 1
        - Enhanced 500,000km
            - Min TL: 13
            - Cost: Cr10000
            - Slots: 2
        - Advanced 50,000km
            - Min TL: 15
            - Cost: Cr2500
            - Slots: 1
        - Advanced 500,000km
            - Min TL: 16
            - Cost: Cr5000
            - Slots: 1
        - IMPORTANT: These need to be merged into the zero-slot Transceivers but it looks like it should be straight forward to do
            - Just need to make sure these ones don't show up in the Default Suite options
- Medical Options
    - Medical Chamber
        - Min TL: 8
        - Cost: Cr200 per slot allocated to the chamber
        - Slots: The number of slots allocated to the chamber
        - Option: Spin box to select the number of slots to allocate to chamber (range: 1 to Base Slots)
        - Option: Combo box to _optionally_ select Berth option
            - Cryoberth (basic)
                - Min TL: 10
                - Cost: Cr20000
                - Slots: 8
            - Cryoberth (improved)
                - Min TL: 12
                - Cost: Cr20000
                - Slots 8
            - Low berth (basic)
                - Min TL: 10
                - Cost: Cr20000
                - Slots: 8
            - Low berth (improved)
                - Min TL: 12
                - Cost: Cr20000
                - Slots: 8
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
            - IMPORTANT: Whatever the count is set to that number of string options should be created so the user can enter the name of the species it's for
        - Requirement: A robot should have at least one manipulator of Size 3 or greater
        - Complex: A Medical Chamber adds +1 to the Maximum Skill level supported by a Medkit option
            - I think this is going to require a dependsOn relation ship but it will be defined by the Medikit as it will need to be processed after the Medical Chamber
        - IMPORTANT: This component is going to have a lot of options, it should split them all into separate steps so they all get their own line item on the manifest
    - Medkit
        - <All>
            - Complex: The Max Skill level can be increased by 1 if the robot has a Medical Chamber slot cost option
                - This will require a dependsOn relationship so Medikit is processed after Medical Chamber
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
- Miscellaneous Options
    - Agricultural Equipment
        - <ALL>
            - Option: Levels
        - Small
            - Min TL: 5
            - Cost: Cr100 * levels
            - Slots: 1 * levels
        - Medium
            - Min TL: 5
            - Cost: Cr1000 * levels
            - Slots: 4 * levels
        - Large
            - Min TL: 5
            - Cost: Cr10000 * levels
            - Slots: 16 * levels
    - Autobar
        - Basic
            - Min TL: 8
            - Cost: Cr500
            - Slots: 2
            - Note: Steward and Profession (bartender) skills is limited to 0 when using Autobar
            - Note: Replenishing the autobar costs Cr250
        - Improved
            - Min TL: 9
            - Cost: Cr1000
            - Slots: 2
            - Note: Steward and Profession (bartender) skills are limited to 1 when using Autobar
            - Note: Replenishing the autobar costs Cr500
        - Enhanced
            - Min TL: 10
            - Cost: Cr2000
            - Slots: 2
            - Note: Steward and Profession (bartender) skills are limited to 2 when using Autobar
            - Note: Replenishing the autobar costs Cr1000
        - Advanced
            - Min TL: 11
            - Cost: Cr5000
            - Slots: 2
            - Note: Steward and Profession (bartender) skills are limited to 3 when using Autobar
            - Note: Replenishing the autobar costs Cr2500
    - Autochef
        - Basic
            - Min TL: 9
            - Cost: Cr500
            - Slots: 3
            - Note: Steward and Profession (chef) skills are limited to 0 when using Autobar
        - Improved
            - Min TL: 10
            - Cost: Cr2000
            - Slots: 3
            - Note: Steward and Profession (chef) skills are limited to 1 when using Autobar
        - Enhanced
            - Min TL: 11
            - Cost: Cr5000
            - Slots: 3
            - Note: Steward and Profession (chef) skills are limited to 2 when using Autobar
        - Advanced
            - Min TL: 12
            - Cost: Cr10000
            - Slots: 3
            - Note: Steward and Profession (chef) skills are limited to 3 when using Autobar 
    - Autopilot
        - <ALL>
            - Requirement: I get the feeling this should require the Vehicle Speed Movement locomotion modification (or at least it's pointless without it) 
            - Complex: Autopilot and skill level packages do not stack; the higher of autopilot or vehicle operating skill applies.
                - This feels like a comment but not sure where to add it. Might need to be in the skill so it can check if there is an autopilot component or Vehicle Speed Movement locomotion modification (as it gives autopilot 0)
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
    - Bioreaction Chamber
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
    - Construction Equipment
        - <ALL>
            - Options: Spin box to choose number of levels (min: 1)
        - Small
            - Min TL: 5
            - Cost: Cr500 * levels
            - Slots: 2 * levels
        - Medium
            - Min TL: 5
            - Cost: Cr5000 * levels
            - Slots: 8 * levels
        - Large
            - Min TL: 5
            - Cost: Cr50000 * levels
            - Slots: 32 * levels
    - Fabrication Chamber
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
    - Forklift
        - Small
            - Min TL: 5
            - Cost: Cr3000
            - Slots: 8
            - Note: Maximum load 0.5 tons
        - Medium
            - Min TL: 5
            - Cost: Cr5000
            - Slots: 12
            - Note: Maximum load 1 ton
        - Large
            - Min TL: 5
            - Cost: Cr20000
            - Slots: 60
            - Note: Maximum load 5 ton
    - Holographic Projector
        - Min TL: 10
        - Cost: Cr1000
        - Slots: 1
    - Mining Equipment
        - <ALL>
            - Options: Spin box to choose number of levels (min: 1)
        - Small
            - Min TL: 5
            - Cost: Cr2000
            - Slots: 5
            - Note: Can mine 0.5 cubic meters per hour
        - Medium
            - Min TL: 5
            - Cost: Cr5000
            - Slots: 15
            - Note: Can mine 2 cubic meters per hour
        - Large
            - Min TL: 5
            - Cost: Cr15000
            - Slots: 45
            - Note: Can mine 8 cubic meters per hour
    - Navigation System
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
        - IMPORTANT: The skill level imparted by this option is based on the system’s information and not modified by a robot’s INT modifier
    - Self-Destruct System
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
    - Self-Maintenance Enhancement
        - Enhanced
            - Min TL: 13
            - Cost: Cr200000 * Base Slots
            - Trait: Maintenance Period = 60 years
            - Trait: Malfunction Check = 5 year
        - Advanced
            - Min TL: 15
            - Cost: Cr500000 * Base Slots
            - Trait: Maintenance Period = Indefinite
            - Trait: Malfunction Check = Indefinite
        - IMPORTANT: This should be merged in with the equivalent zero-slot options
    - Stealth
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
    - Storage Compartment
        - <ALL>
            - Option: Spin box to choose the number of slots to allocate
        - Standard
            - Min TL: 6
            - Cost: Cr50 * slots allocated
            - Slots: Slots allocated
        - Refrigerated
            - Min TL: 6
            - Cost: Cr100 * slots allocated
            - Slots: Slots allocated
        - Hazardous Materials
            - Min TL: 6
            - Cost: Cr500 * slots allocated
            - Slots: Slots allocated
    - Video Projector
        - Min TL: 7
        - Cost: Cr500
        - Slots: 1
- Power Options
    - External Power
        - Min TL: 9
        - Cost: Cr100 * Base Slots
        - Slots: 5% of Base Slots
    - No Internal Power
        - Min TL: 6
        - Slot Gain: +10% Base Slots gained rounded up
            - IMPORTANT: This shouldn't change the Base Slots value, but it does need to change the Available Slots
        - Trait: I assume this should set the robots Endurance to 0
    - RTG Long Duration
        - <ALL>
            - Complex: There is wording around modifiers for robots that rely on RTG on p55. I __think__  they're talking about robots that only have RTG
        - Basic
            - Min TL: 7
            - Cost: Cr20000 * Base Slots
            - Slots: 20% of Base Slots
            - Trait: Endurance = 25 years
                - NOTE: This might need to be a comment as it's more the lifetime of the power source
        - Improved
            - Min TL: 9
            - Cost: Cr50000 * Base Slots
            - Slots: 15% of Base Slots
            - Trait: Endurance = 50 years
                - NOTE: This might need to be a comment as it's more the lifetime of the power source
        - Advanced
            - Min TL: 11
            - Cost: Cr100000 * Base Slots
            - Slots: 10% of Base Slots
            - Trait: Endurance = 100 years
                - NOTE: This might need to be a comment as it's more the lifetime of the power source
    - RTG Short Duration
        - <ALL>
            - Complex: There is wording around modifiers for robots that rely on RTG on p55. I __think__  they're talking about robots that only have RTG
        - Basic
            - Min TL: 8
            - Cost: Cr50000 * Base Slots
            - Slots: 15% of Base Slots
            - Trait: Endurance = 3 years
                - NOTE: This might need to be a comment as it's more the lifetime of the power source
        - Improved
            - Min TL: 10
            - Cost: Cr100000 * Base Slots
            - Slots: 10% of Base Slots
            - Trait: Endurance = 4 years
                - NOTE: This might need to be a comment as it's more the lifetime of the power source
        - Advanced
            - Min TL: 12
            - Cost: Cr200000 * Base Slots
            - Slots: 5% of Base Slots
            - Trait: Endurance = 5 years
                - NOTE: This might need to be a comment as it's more the lifetime of the power source
    - Solar Power Unit
        - <ALL>
            - Complex: There is wording around modifiers for robots that rely on solar on p55. I __think__  they're talking about robots that only have solar
            - Note: There is a load of complex stuff on p56
        - Basic
            - Min TL: 6
            - Cost: Cr2000 * Base Slots
            - Slots: 20% of Base Slots
            - Endurance: 10 years
                - NOTE: This might need to be a comment as it's more the lifetime of the power source
        - Improved
            - Min TL: 8
            - Cost: Cr5000 * Base Slots
            - Slots: 15% of Base Slots
            - Endurance: 25 years
                - NOTE: This might need to be a comment as it's more the lifetime of the power source 
        - Enhanced
            - Min TL: 10
            - Cost: Cr10000 * Base Slots
            - Slots: 10% of Base Slots
            - Endurance: 50 years
                - NOTE: This might need to be a comment as it's more the lifetime of the power source      
        - Advanced
            - Min TL: 12
            - Cost: Cr20000 * Base Slots
            - Slots: 5% of Base Slots
            - Endurance: 100 years
                - NOTE: This might need to be a comment as it's more the lifetime of the power source
    - Quick Charger
        - Min TL: 8
        - Cost: Cr200
        - Slots: 1
        - Comments: Can fully recharge a robot not running on external power in 1 hour
            - NOTE: I could vary this comment depending on if the robot has External Power but it would require a dependsOn relationship
- Sensor Options
    - Bioscanner Sensor
        - Min TL: 15
        - Cost: Cr350000
        - Slots: 2
        - Complex: Requires at least Electronics (sensors) to operator
    - Bioscanner Sensor
        - Min TL: 14
        - Cost: Cr20000
        - Slots: 3
        - Note: Target must be within 100m to be scanned
        - Complex: Requires at least Electronics (sensors) to operator   
    - Neural Activity Sensor
        - Min TL: 15
        - Cost: Cr35000
        - Slots: 5
        - Note: Detects Neural Activity within 500m
        - Complex: Requires at least Electronics (sensors) to operator   
    - Planetology Sensor Suite
        - Min TL: 12
        - Cost: Cr25000
        - Slots: 5
        - Note: Detects Neural Activity within 500m
        - Note: Adds DM+1 to any checks conducted in conjunction with data provided by the suite
        - Complex: Requires at least Electronics (sensors) to operator
        - Complex: Added +1 to the Maximum Skill level allowed by the Science (planetology) Toolkit
            - NOTE: This will need to be handled like the Medical Chamber/Medikit dependency
    - Recon Sensor
        - <ALL>
            - Complex: Recon skill levels provided by this sensor are not modified by a robot’s INT.
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
- Toolkit Options
    - Cutting Torch
        - <ALL>
            - Note: Can be used as an improvised weapon doing 3D damage with AP 4
        - Basic    
            - Min TL: 5
            - Cost: Cr500
            - Slots: 2
        - Improved
            - Min TL: 9
            - Cost: Cr5000
            - Slots: 2
        - Advanced
            - Min TL: 13
            - Cost: Cr5000
            - Slots: 1
    - Electronics Toolkit
        - <ALL>
            - Note: In general a the toolkit only allows a positive DM to repair attempts on equipment with a TL less than or to it
                - IMPORTANT: For this to make sense the manifest will need to show the TL of the toolkit somehow
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
    - Fire Extinguisher
        - Min TL: 6
        - Cost: Cr100
        - Slots: 1
    - Forensic Toolkit
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
    - Mechanical Toolkit
        - <ALL>
            - Note: Repair attempts suffer a DM-2 if the equipment being repaired is more than 2 TLs higher than the toolkit and robot
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
    - Scientific Toolkit
        - <ALL>
            - Complex: You need to specify which science the toolkit is for when constructed
                - This means I need to support adding multiple toolkits for different sciences
                - The problem is there is no definitive list of all sciences so it kind of needs to allow the user to enter a string
                - Really it needs to allow for toolkits fo different TLs for different sciences (i.e. a basic chemistry toolkit and improved physics toolkit)
                - I think I'm going to need to have a single component that lets you select the number of toolkits then select the TL and enter the science
                - This might benefit from a new type of string construction option where you can specify some predefined strings fro the user to select from or allow them to type (basically an editable combo box). This would mean I could pre-populate a list with "popular" sciences
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
    - Starship Engineering Toolkit
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
    - Stylist Toolkit
        - Note: Replenishing the toolkit costs Cr500
        - Complex: Stylist Toolkits are species specific so I need to support more than 1
            - This could probably just be a spin box to select the number and dynamically created text entries
            - Each one needs to be added as it's own row to the manifest
- Weapons
    - Weapons are COMPLEX and will probably need to be handled separately from the other slot options
    - I think a lot of how they work will be determined by how manipulators are implemented
        - It might be easier if each manipulator is an instance of a component
    - I think basically what I need to do is to let the user create however many mounts they require
        - These can be slot mounted in the torso where they take slots or on manipulators where they don't take slots
        - When attaching to manipulators there are minimum manipulator sizes for the different levels of weapon mount
        - I assume leg manipulators can also have weapon mounts
        - It looks like weapon mount autoloader is just an option on a weapon mount
    - Fire Control then needs to be a separate stage after the weapon mounts as we need a way to link instances of fire control to multiple mounts (up to 4)
    - I'm not sure if I need a way to select the actual weapon as well
        - Could have a hard coded list of weapons from the field catalogue like the spreadsheet does 
        - Ideally it would let you select weapons created in the gunsmith but that isn't trivial
"""