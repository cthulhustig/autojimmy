import common
import construction
import robots
import typing

#  █████                           ████ 
# ░░███                           ░░███ 
#  ░███  █████████████   ████████  ░███ 
#  ░███ ░░███░░███░░███ ░░███░░███ ░███ 
#  ░███  ░███ ░███ ░███  ░███ ░███ ░███ 
#  ░███  ░███ ░███ ░███  ░███ ░███ ░███ 
#  █████ █████░███ █████ ░███████  █████
# ░░░░░ ░░░░░ ░░░ ░░░░░  ░███░░░  ░░░░░ 
#                        ░███           
#                        █████          
#                       ░░░░░          

class _LocomotionImpl(object):
    """
    All Locomotion Types:
    - At TL12 Base Endurance is increased by 50% (p19)
    - At TL15 Base Endurance is increased by 100% (p19)
    - Primary Locomotion
        - Base Chassis Cost: Basic Cost * Cost Multiplier
        - Base Speed: 5m
    - Secondary Locomotion
        - Slots: 25% of Base Slots rounded up (p23)
        - Cost: Each slot costs Cr500 * Secondary Locomotion Cost Multiplier
        - Base Speed: 5m
        - Requirement: Other than Thrusters, only compatible with a primary
        locomotion that has a greater or equal cost multiplier (p23). Thrusters
        are a special case and can be be used even if the primary has a lower
        multiplier.
    """
    # NOTE: The rules say "Agility is a factor in determining a robot’s movement
    # rate, modifying a robot’s base movement rate of five metres per Minor
    # Action" (p16) but I've not found anything that explicitly says _how_ it
    # modifies it. I expect it just means the Agility gets added to the base
    # Speed of 5m per minor action. This appears to be what the spreadsheet
    # does
    # NOTE: Endurance and Agility of secondary locomotions is handled with a
    # note. There are a couple of unpleasant things about the way this is done
    # but it should be "good enough"
    # 1. The way Endurance is calculated is a bit ugly due to the fact you need
    # to take the EnduranceIncrease component. Technically checking for this
    # component and querying its settings isn't an issue as Secondary Locomotion
    # is applied after it is in construction order. It's just a bit horrible.
    # 2. It doesn't take the NoInternalPower component into account. Technically
    # it could because, although NoInternalPower is applied later in construction,
    # we only need to check for its presence which is allowed. It's just a bit
    # more horrible than I was willing to do so it is what it is.
    # NOTE: The secondary locomotion rules (p23) say that if the a robot has VSM
    # and the primary and secondary locomotion are of the same type, the the
    # secondary locomotion is considered to also have VSM. However, it doesn't
    # say anything about the same logic applying to agility or tactical speed
    # mods. I've gone with the assumption it would as the rules also say robots
    # with more than 8 legs/axles/thrusters can be considered to have a
    # secondary locomotion of the same type as the primary. I can't see how this
    # could possibly work if legs/axles/thrusters after the 8th will be less
    # agile or moving at a different speed to the others.
    # Having the endurance, agility and speed the same for the secondary is
    # achieved by not setting the secondary version of those attributes. The
    # logic being there it's effectively a single locomotion.

    _TL12EnduranceIncreasePercent = common.ScalarCalculation(
        value=50,
        name='TL12 Locomotion Endurance Increase')
    _TL15EnduranceIncreasePercent = common.ScalarCalculation(
        value=100,
        name='TL15 Locomotion Endurance Increase')
    
    _BaseSpeed = common.ScalarCalculation(
        value=5,
        name='Base Meters Per Minor Action')
    
    _SecondaryLocomotionSlotPercent = common.ScalarCalculation(
        value=25,
        name='Secondary Locomotion Slot Usage')
    _SecondaryLocomotionBaseCost = common.ScalarCalculation(
        value=500,
        name='Secondary Locomotion Base Cost Per Slot')
    
    _ImprovedComponentsIncreasePercent = common.ScalarCalculation(
        value=100,
        name='Improved Components Endurance Increase Percentage')

    _PowerPackIncreasePercent = common.ScalarCalculation(
        value=100,
        name='Power Pack Endurance Increase Percentage')        

    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            baseEndurance: int,
            costMultiplier: int,
            isNatural: bool,
            baseAgility: typing.Optional[int] = None,
            flagTrait: typing.Optional[robots.RobotAttributeId] = None,
            notes: typing.Optional[typing.Iterable[str]] = None,
            primaryEquivType: typing.Optional[robots.RobotComponentInterface] = None # Only set for secondary locomotions
            ) -> None:
        super().__init__()

        self._componentString = componentString
        self._minTechLevel = common.ScalarCalculation(
            value=minTechLevel,
            name=f'{componentString} Locomotion Minimum Tech Level')        
        self._baseEndurance = common.ScalarCalculation(
            value=baseEndurance,
            name=f'{componentString} Locomotion Base Endurance')
        self._costMultiplier = common.ScalarCalculation(
            value=costMultiplier,
                name=f'{componentString} Locomotion Cost Multiplier')
        self._isNatural = isNatural
        self._baseAgility = None
        if baseAgility != None:
            self._baseAgility = common.ScalarCalculation(
                value=baseAgility,
                name=f'{componentString} Locomotion Agility')
        self._flagTrait = flagTrait
        self._notes = notes
        self._primaryEquivType = primaryEquivType

    def isNatural(self) -> bool:
        return self._isNatural
    
    def instanceString(self) -> str:
        return self._componentString

    def componentString(self) -> str:
        return self._componentString
    
    def costMultiplier(self) -> common.ScalarCalculation:
        return self._costMultiplier

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if context.techLevel() < self._minTechLevel.value():
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

    def updateStep(
            self,
            sequence: str,
            context: robots.RobotContext,
            step: robots.RobotStep
            ) -> None:   
        if not self._primaryEquivType:
            # Primary Locomotion
            step.setCredits(
                credits=construction.MultiplierModifier(
                    value=self._costMultiplier))

            endurance = self._calculatePrimaryEndurance(context=context)
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=robots.RobotAttributeId.Endurance,
                value=endurance))
            
            if self._baseAgility:
                step.addFactor(factor=construction.SetAttributeFactor(
                    attributeId=robots.RobotAttributeId.Agility,
                    value=self._baseAgility))
                
                speed = common.Calculator.add(
                    lhs=_LocomotionImpl._BaseSpeed,
                    rhs=self._baseAgility,
                    name=f'{self._componentString} Base Speed')
                step.addFactor(factor=construction.SetAttributeFactor(
                    attributeId=robots.RobotAttributeId.Speed,
                    value=speed))
        else:
            # Secondary Locomotion
            baseSlots = context.baseSlots(sequence=sequence)
            requiredSlots = common.Calculator.ceil(
                value=common.Calculator.takePercentage(
                    value=baseSlots,
                    percentage=_LocomotionImpl._SecondaryLocomotionSlotPercent),
                name=f'Secondary {self._componentString} Required Slots')
            
            slotCost = common.Calculator.multiply(
                lhs=_LocomotionImpl._SecondaryLocomotionBaseCost,
                rhs=self._costMultiplier,
                name=f'Secondary {self._componentString} Cost Per Slot')
            totalCost = common.Calculator.multiply(
                lhs=slotCost,
                rhs=requiredSlots,
                name=f'Secondary {self._componentString} Cost')

            step.setCredits(
                credits=construction.ConstantModifier(value=totalCost))
            step.setSlots(
                slots=construction.ConstantModifier(value=requiredSlots))
            
            sameAsPrimary = context.hasComponent(
                componentType=self._primaryEquivType,
                sequence=sequence)
            if not sameAsPrimary:
                isBioRobot = context.hasComponent(
                    componentType=robots.BioRobotSynthetic,
                    sequence=sequence)
                if not isBioRobot:
                    endurance = self._calculateSecondaryEndurance(
                        context=context,
                        sequence=sequence)
                    step.addFactor(factor=construction.SetAttributeFactor(
                        attributeId=robots.RobotAttributeId.SecondaryEndurance,
                        value=endurance))
                    
                # NOTE: The secondary agility doesn't have any Agility Increase
                # modifiers applied as it's a locomotion modification and the
                # book says locomotion modification only apply to primary
                # locomotion (p22)
                if self._baseAgility:
                    step.addFactor(factor=construction.SetAttributeFactor(
                        attributeId=robots.RobotAttributeId.SecondaryAgility,
                        value=self._baseAgility))                    
                   
                    speed = common.Calculator.add(
                        lhs=_LocomotionImpl._BaseSpeed,
                        rhs=self._baseAgility,
                        name=f'{self._componentString} Base Speed')
                    step.addFactor(factor=construction.SetAttributeFactor(
                        attributeId=robots.RobotAttributeId.SecondarySpeed,
                        value=speed))                        

        if self._flagTrait:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=self._flagTrait))

        if self._notes:
            for note in self._notes:
                step.addNote(note)

    def _isPrimary(self) -> bool:
        return self._primaryEquivType == None

    def _calculatePrimaryEndurance(
            self,
            context: robots.RobotContext
            ) -> common.ScalarCalculation:
        endurance = self._baseEndurance
        if context.techLevel() >= 15:
            endurance = common.Calculator.applyPercentage(
                value=endurance,
                percentage=_LocomotionImpl._TL15EnduranceIncreasePercent,
                name='TL15 ' + endurance.name())
        elif context.techLevel() >= 12:
            endurance = common.Calculator.applyPercentage(
                value=endurance,
                percentage=_LocomotionImpl._TL12EnduranceIncreasePercent,
                name='TL12 ' + endurance.name())
        return endurance

    def _calculateSecondaryEndurance(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> common.ScalarCalculation:
        endurance = self._calculatePrimaryEndurance(context=context)

        # NOTE: So I don't panic myself thinking there is a bug in the
        # future. This looks broken because IncreasedEndurance appears
        # in a stage after locomotion, but remember that this branch in
        # the code is used for secondary locomotion which is in a stage
        # after the one IncreaseEndurance appears in.        
        enduranceIncrease = context.findFirstComponent(
            componentType=robots.IncreaseEndurance,
            sequence=sequence)
        if enduranceIncrease:
            assert(isinstance(enduranceIncrease, robots.IncreaseEndurance))
            if enduranceIncrease.improvedComponents():
                endurance = common.Calculator.applyPercentage(
                    value=endurance,
                    percentage=_LocomotionImpl._ImprovedComponentsIncreasePercent)
            powerPackCount = enduranceIncrease.powerPackCount()
            endurance = common.Calculator.applyPercentage(
                value=endurance,
                percentage=common.Calculator.multiply(
                    lhs=_LocomotionImpl._PowerPackIncreasePercent,
                    rhs=powerPackCount))
            endurance = common.Calculator.rename(
                value=endurance,
                name='Improved Secondary Endurance')
        return endurance

class _NoLocomotionImpl(_LocomotionImpl):
    """
    - TL: 5
    - Agility: None
    - Traits: None
    - Base Endurance: 216 hours
    - Cost Multiplier: x1
    - Available Slot: +25% Base Slots rounded up (p16)
    - Requirement: Can't be a secondary locomotion
    """
    # NOTE: The percentage slot gain is to available slots not base slots

    _MaxSlotIncreasePercent = common.ScalarCalculation(
        value=+25,
        name='No Locomotion Max Slots Percentage Increase')

    def __init__(self) -> None:
        super().__init__(
            componentString='None',
            minTechLevel=5,
            baseEndurance=216,
            costMultiplier=1,
            isNatural=True)
        
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
       
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.MaxSlots,
            modifier=construction.PercentageModifier(
                value=_NoLocomotionImpl._MaxSlotIncreasePercent,
                roundDown=True)))
 
class _WheelsLocomotionImpl(_LocomotionImpl):
    """
    - TL: 5
    - Agility: +0
    - Traits: None
    - Base Endurance: 72 hours
    - Cost Multiplier: x2
    - Options: Number of axles
    """
    def __init__(
            self,
            primaryEquivType: typing.Optional[robots.RobotComponentInterface] = None # Only set for secondary locomotions
            ) -> None:
        super().__init__(
            componentString='Wheels',
            minTechLevel=5,
            baseAgility=+0,
            baseEndurance=72,
            costMultiplier=2,
            isNatural=False,
            primaryEquivType=primaryEquivType)  

class _WheelsATVLocomotionImpl(_LocomotionImpl):
    """
    - TL: 5
    - Agility: +0
    - Traits: ATV
    - Base Endurance: 72 hours
    - Cost Multiplier: x3
    - Options: Number of axles
    """
    def __init__(
            self,
            primaryEquivType: typing.Optional[robots.RobotComponentInterface] = None # Only set for secondary locomotions
            ) -> None:
        super().__init__(
            componentString='Wheels, ATV',
            minTechLevel=5,
            baseAgility=+0,
            flagTrait=robots.RobotAttributeId.ATV,
            baseEndurance=72,
            costMultiplier=3,
            isNatural=False,
            primaryEquivType=primaryEquivType)
        
class _TracksLocomotionImpl(_LocomotionImpl):
    """
    - TL: 5
    - Agility: -1
    - Traits: ATV
    - Base Endurance: 72 hours
    - Cost Multiplier: x2
    - Options: Number of tracks
    """
    def __init__(
            self,
            primaryEquivType: typing.Optional[robots.RobotComponentInterface] = None # Only set for secondary locomotions
            ) -> None:
        super().__init__(
            componentString='Tracks',
            minTechLevel=5,
            baseAgility=-1,
            flagTrait=robots.RobotAttributeId.ATV,
            baseEndurance=72,
            costMultiplier=2,
            isNatural=False,
            primaryEquivType=primaryEquivType)
        
class _FlyerLocomotionImpl(_LocomotionImpl):
    """
    - Trait: Flyer (Idle) (p17)
    """
    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            baseAgility: int,
            baseEndurance: int,
            costMultiplier: int,
            isNatural: bool,
            notes: typing.Optional[typing.Iterable[str]] = None,
            primaryEquivType: typing.Optional[robots.RobotComponentInterface] = None # Only set for secondary locomotions
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTechLevel=minTechLevel,
            baseAgility=baseAgility,
            baseEndurance=baseEndurance,
            costMultiplier=costMultiplier,
            notes=notes,
            isNatural=isNatural,
            primaryEquivType=primaryEquivType)
        
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
            attributeId=robots.RobotAttributeId.Flyer,
            value=robots.SpeedBand.Idle))
        
class _GravLocomotionImpl(_FlyerLocomotionImpl):
    """
    - TL: 9
    - Agility: +1
    - Traits: Flyer
    - Base Endurance: 24 hours
    - Cost Multiplier: x20
    """
    def __init__(
            self,
            primaryEquivType: typing.Optional[robots.RobotComponentInterface] = None # Only set for secondary locomotions
            ) -> None:
        super().__init__(
            componentString='Grav',
            minTechLevel=9,
            baseAgility=+1,
            baseEndurance=24,
            costMultiplier=20,
            isNatural=False,
            primaryEquivType=primaryEquivType)
        
class _AeroplaneLocomotionImpl(_FlyerLocomotionImpl):
    """
    - TL: 5
    - Agility: +1
    - Traits: Flyer
    - Base Endurance: 12 hours
    - Cost Multiplier: x12
    - Requirement: Must include the Vehicle Speed Movement modification (p17)
    - Requirement: Can only be primary locomotion type
    - Note: Requires a runway of at least 50m for landing (p17)
    - Note: Size 1-3 aeroplanes can be launched by hand, larger require a runway
      of at least 50m (p16)
    - Note: Cannot move slower than Slow
    - Note: Requires a secondary locomotion type to do more than taxi to the
      runway
    """
    # NOTE: The requirement that Aeroplane can only be a primary locomotion is
    # implied from the fact the p17 of the robot rules say the Aeroplane
    # locomotion requires the Vehicle Speed Movement Locomotion Modification and
    # p22 says Locomotion Modifications alter the performance characteristics of
    # a robot's primary form of locomotion
    # NOTE: The requirement that Aeroplane locomotion requires Vehicle Speed
    # Movement is handled by the way I've set up the Speed Modification stage.
    # The stage is mandatory and added a hacky None component. All components
    # other than Vehicle Speed Movement are incompatible with Aeroplane
    # locomotion so it forces it to be selected.

    _SmallAeroplaneNote = 'Can be launched by hand. (p17)'

    _CommonAeroplaneNotes = [
        'Landing requires a runway of at least 50m. (p17)',
        'Cannot move slower than Speed Band (Slow) without stalling. (p17)',
        'Requires a secondary locomotion type to do more than taxi to the runway. (p17)']

    def __init__(
            self,
            primaryEquivType: typing.Optional[robots.RobotComponentInterface] = None # Only set for secondary locomotions
            ) -> None:
        super().__init__(
            componentString='Aeroplane',
            minTechLevel=5,
            baseAgility=+1,
            baseEndurance=12,
            costMultiplier=12,
            notes=None, # Notes handled locally
            isNatural=True,
            primaryEquivType=primaryEquivType)
        
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
        
        if context.hasComponent(componentType=robots.Size1Chassis) or \
            context.hasComponent(componentType=robots.Size2Chassis) or \
            context.hasComponent(componentType=robots.Size3Chassis):
            step.addNote(note=_AeroplaneLocomotionImpl._SmallAeroplaneNote)

        for note in _AeroplaneLocomotionImpl._CommonAeroplaneNotes:
            step.addNote(note=note)
        
class _AquaticLocomotionImpl(_LocomotionImpl):
    """
    - TL: 6
    - Agility: -2
    - Traits: Seafarer
    - Base Endurance: 72 hours
    - Cost Multiplier: x4
    """
    def __init__(
            self,
            primaryEquivType: typing.Optional[robots.RobotComponentInterface] = None # Only set for secondary locomotions
            ) -> None:
        super().__init__(
            componentString='Aquatic',
            minTechLevel=6,
            baseAgility=-2,
            flagTrait=robots.RobotAttributeId.Seafarer,
            baseEndurance=72,
            costMultiplier=4,
            isNatural=True,
            primaryEquivType=primaryEquivType)
        
class _VTOLLocomotionImpl(_FlyerLocomotionImpl):
    """
    - TL: 7
    - Agility: +0
    - Traits: Flyer
    - Base Endurance: 24 hours
    - Cost Multiplier: x14
    - Note: Requires a secondary locomotion type to move across the ground (p17)
    - Note: Agility -1 in thin atmosphere (p17)
    """
    def __init__(
            self,
            primaryEquivType: typing.Optional[robots.RobotComponentInterface] = None # Only set for secondary locomotions
            ) -> None:
        super().__init__(
            componentString='VTOL',
            minTechLevel=7,
            baseAgility=+0,
            baseEndurance=24,
            costMultiplier=14,
            isNatural=True,
            notes=[
                'Agility -1 in thin atmosphere. Although it\'s not explicitly stated, the implication of this is that the robot also suffers Speed -1. (p16/17)',
                'Requires a secondary locomotion type to move across the ground. (p17)'],
            primaryEquivType=primaryEquivType)
        
class _WalkerLocomotionImpl(_LocomotionImpl):
    """
    - TL: 8
    - Agility: +0
    - Traits: ATV
    - Base Endurance: 72 hours
    - Cost Multiplier: x10
    - Option: User specified number of legs (min 2)
    """
    # NOTE: This needs to prompt the user for the number of legs to allow
    # handling of leg manipulators later in construction. It makes logical
    # sense for it to specified here and it also makes the later implementation
    # simpler as the number of legs is known up front.
    def __init__(
            self,
            primaryEquivType: typing.Optional[robots.RobotComponentInterface] = None # Only set for secondary locomotions
            ) -> None:
        super().__init__(
            componentString='Walker',
            minTechLevel=8,
            baseAgility=+0,
            flagTrait=robots.RobotAttributeId.ATV,
            baseEndurance=72,
            costMultiplier=10,
            isNatural=True,
            primaryEquivType=primaryEquivType)
        
        self._legCountOption = construction.IntegerOption(
            id='LegCount',
            name='Leg Count',
            value=2,
            minValue=2,
            description='Specify the number of legs the robot has.')        
        
    def legCount(self) -> int:
        return self._legCountOption.value()
    
    def instanceString(self) -> str:
        legCount = self.legCount()
        if legCount:
            return f'{self._componentString} (Legs: {legCount})'
        return super().instanceString()      
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._legCountOption]    
        
class _HovercraftLocomotionImpl(_LocomotionImpl):
    """
    - TL: 7
    - Agility: +1
    - Traits: ACV
    - Base Endurance: 24 hours
    - Cost Multiplier: x10
    - Note: Agility -1 in thin atmosphere (p17)       
    """
    def __init__(
            self,
            primaryEquivType: typing.Optional[robots.RobotComponentInterface] = None # Only set for secondary locomotions
            ) -> None:
        super().__init__(
            componentString='Hovercraft',
            minTechLevel=7,
            baseAgility=+1,
            flagTrait=robots.RobotAttributeId.ACV,
            baseEndurance=24,
            costMultiplier=10,
            isNatural=False,
            notes=['Agility -1 in thin atmosphere. Although it\'s not explicitly stated, the implication of this is that the robot also suffers Speed -1. (p16/17).'],
            primaryEquivType=primaryEquivType)
        
class _ThrusterLocomotionImpl(_LocomotionImpl):
    """
    - TL: 7
    - Agility: +1
    - Traits: Thruster
    - Base Endurance: 2 hours
    - Cost Multiplier: x20
    - Trait: Thrust 0.1G as standard (p17)
    = Trait: Thrust 10G (TL8-13) or 15G (TL14+) if primary and secondary
      thrusters and Vehicle speed movement (p17)
    """
    # NOTE: There are 2 types of thrusters, standard thrusters intended to as a
    # secondary form of locomotion so the robot can maneuver in low gravity
    # (<= 0.1G), and missile thrusters that require thrusters to be installed as
    # the primary and secondary locomotion along with vehicle speed movement
    # NOTE: The table on p16 of the robot rules doesn't say that the Thrust
    # locomotion type has the Thrust trait from p17. I'm working on the
    # assumption this is an oversight

    _LowMissileTL = 8
    _HighMissileTL = 14

    def __init__(
            self,
            primaryEquivType: typing.Optional[robots.RobotComponentInterface] = None # Only set for secondary locomotions
            ) -> None:
        super().__init__(
            componentString='Thruster',
            minTechLevel=7,
            baseAgility=+1,
            baseEndurance=2,
            costMultiplier=20,
            isNatural=False,
            primaryEquivType=primaryEquivType)
        
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
        
        thrust = robots.ThrustGForce.Thrust0p1G
        if not self._isPrimary():
            # Only check for missile thrusters on secondary locomotion. I think
            # it makes logical sense as, out of the components requirements for
            # missile thrusters, secondary locomotion is the last in construction
            # so its conceptually it the component that takes it from standard
            # to missile.
            hasPrimaryThrusters = context.hasComponent(
                componentType=self._primaryEquivType,
                sequence=sequence)
            hasVehicleSpeed = context.hasComponent(
                componentType=robots.VehicleSpeedMovement,
                sequence=sequence)
            if hasPrimaryThrusters and hasVehicleSpeed:
                if context.techLevel() >= _ThrusterLocomotionImpl._HighMissileTL:
                    thrust = robots.ThrustGForce.Thrust15G
                elif context.techLevel() >= _ThrusterLocomotionImpl._LowMissileTL:
                    thrust = robots.ThrustGForce.Thrust10G

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Thruster,
            value=thrust))
    
class Locomotion(robots.RobotComponentInterface):
    def __init__(
            self,
            impl: _LocomotionImpl
            ) -> None:
        super().__init__()
        self._impl = impl

    def isNatural(self) -> bool:
        return self._impl.isNatural()

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def componentString(self) -> str:
        return self._impl.componentString()
    
    def costMultiplier(self) -> common.ScalarCalculation:
        return self._impl.costMultiplier()

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return self._impl.isCompatible(sequence=sequence, context=context)

    def options(self) -> typing.List[construction.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        return self._impl.updateOptions(sequence=sequence, context=context)

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

        
#  ███████████             ███                                                
# ░░███░░░░░███           ░░░                                                 
#  ░███    ░███ ████████  ████  █████████████    ██████   ████████  █████ ████
#  ░██████████ ░░███░░███░░███ ░░███░░███░░███  ░░░░░███ ░░███░░███░░███ ░███ 
#  ░███░░░░░░   ░███ ░░░  ░███  ░███ ░███ ░███   ███████  ░███ ░░░  ░███ ░███ 
#  ░███         ░███      ░███  ░███ ░███ ░███  ███░░███  ░███      ░███ ░███ 
#  █████        █████     █████ █████░███ █████░░████████ █████     ░░███████ 
# ░░░░░        ░░░░░     ░░░░░ ░░░░░ ░░░ ░░░░░  ░░░░░░░░ ░░░░░       ░░░░░███ 
#                                                                    ███ ░███ 
#                                                                   ░░██████  
#                                                                    ░░░░░░  

class PrimaryLocomotion(Locomotion):
    def __init__(
            self,
            impl: _LocomotionImpl
            ) -> None:
        super().__init__(impl=impl)

    def typeString(self) -> str:
        return 'Locomotion'
                
class NoPrimaryLocomotion(PrimaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_NoLocomotionImpl())

class WheelsPrimaryLocomotion(PrimaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_WheelsLocomotionImpl())

class WheelsATVPrimaryLocomotion(PrimaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_WheelsATVLocomotionImpl())  

class TracksPrimaryLocomotion(PrimaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_TracksLocomotionImpl())     

class GravPrimaryLocomotion(PrimaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_GravLocomotionImpl())

class AeroplanePrimaryLocomotion(PrimaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_AeroplaneLocomotionImpl())

class AquaticPrimaryLocomotion(PrimaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_AquaticLocomotionImpl())

class VTOLPrimaryLocomotion(PrimaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_VTOLLocomotionImpl())

class WalkerPrimaryLocomotion(PrimaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_WalkerLocomotionImpl())

    def legCount(self) -> int:
        assert(isinstance(self._impl, _WalkerLocomotionImpl))
        return self._impl.legCount()

class HovercraftPrimaryLocomotion(PrimaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_HovercraftLocomotionImpl())

class ThrusterPrimaryLocomotion(PrimaryLocomotion):
    # NOTE: The rules say that Thrusters are generally only available as a
    # secondary locomotion but the word 'generally' would imply it is
    # possible for them to be a primary locomotion. There is actually an
    # example of it being a primary but it's for a missile robot (p101)
    # that has thrusters as primary and secondary locomotion. There is
    # also some example robots that only have thruster locomotion
    # (e.g. p183 and p209). Conceivably the could have no primary
    # locomotion and thrusters as a secondary but the fact it has a
    # second endurance value in brackets would suggest it has Vehicle
    # Speed Movement which is primary locomotion only.
    def __init__(self) -> None:
        super().__init__(impl=_ThrusterLocomotionImpl())



#   █████████                                            █████                               
#  ███░░░░░███                                          ░░███                                
# ░███    ░░░   ██████   ██████   ██████  ████████    ███████   ██████   ████████  █████ ████
# ░░█████████  ███░░███ ███░░███ ███░░███░░███░░███  ███░░███  ░░░░░███ ░░███░░███░░███ ░███ 
#  ░░░░░░░░███░███████ ░███ ░░░ ░███ ░███ ░███ ░███ ░███ ░███   ███████  ░███ ░░░  ░███ ░███ 
#  ███    ░███░███░░░  ░███  ███░███ ░███ ░███ ░███ ░███ ░███  ███░░███  ░███      ░███ ░███ 
# ░░█████████ ░░██████ ░░██████ ░░██████  ████ █████░░████████░░████████ █████     ░░███████ 
#  ░░░░░░░░░   ░░░░░░   ░░░░░░   ░░░░░░  ░░░░ ░░░░░  ░░░░░░░░  ░░░░░░░░ ░░░░░       ░░░░░███ 
#                                                                                   ███ ░███ 
#                                                                                  ░░██████  
#                                                                                   ░░░░░░  

class SecondaryLocomotion(Locomotion):
    """
    - Requirement: Secondary locomotion types must be compatible with the same
    primary locomotion type
    """
    # NOTE: The requirement to allow primary and secondary locomotion to be the
    # same type is to allow users to handle the rule on p23 where robots with
    # more than 8 legs/axles/etc may be considered to have a secondary
    # locomotion of the same type as the primary.

    def __init__(
            self,
            impl: _LocomotionImpl
            ) -> None:
        super().__init__(impl=impl)

    def typeString(self) -> str:
        return 'Secondary Locomotion'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(
            sequence=sequence,
            context=context):
            return False

        # NOTE: If I ever add anything here it won't be applied for
        # secondary thrusters as it skips the base class

        primaryLocomotion = context.findFirstComponent(
            componentType=PrimaryLocomotion)
        if not primaryLocomotion:
            return False
        assert(isinstance(primaryLocomotion, PrimaryLocomotion))
        
        # Cost multiplier of primary locomotion must be greater or equal to the
        # cost multiplier of the secondary locomotion
        primaryMultiplier = primaryLocomotion.costMultiplier()
        return self._impl.costMultiplier().value() <= primaryMultiplier.value()
        
class WheelsSecondaryLocomotion(SecondaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_WheelsLocomotionImpl(
            primaryEquivType=WheelsPrimaryLocomotion))

class WheelsATVSecondaryLocomotion(SecondaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_WheelsATVLocomotionImpl(
            primaryEquivType=WheelsATVPrimaryLocomotion))

class TracksSecondaryLocomotion(SecondaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_TracksLocomotionImpl(
            primaryEquivType=TracksPrimaryLocomotion))

class GravSecondaryLocomotion(SecondaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_GravLocomotionImpl(
            primaryEquivType=GravPrimaryLocomotion))

class AquaticSecondaryLocomotion(SecondaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_AquaticLocomotionImpl(
            primaryEquivType=AquaticPrimaryLocomotion))

class VTOLSecondaryLocomotion(SecondaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_VTOLLocomotionImpl(
            primaryEquivType=VTOLPrimaryLocomotion))

class WalkerSecondaryLocomotion(SecondaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_WalkerLocomotionImpl(
            primaryEquivType=WalkerPrimaryLocomotion))

    def legCount(self) -> int:
        assert(isinstance(self._impl, _WalkerLocomotionImpl))
        return self._impl.legCount()            

class HovercraftSecondaryLocomotion(SecondaryLocomotion):
    def __init__(self) -> None:
        super().__init__(impl=_HovercraftLocomotionImpl(
            primaryEquivType=HovercraftPrimaryLocomotion))

class ThrusterSecondaryLocomotion(SecondaryLocomotion):
    """
    - Requirement: Secondary Locomotion Thruster are a special case and can be
    used with a primary locomotion that has a lower cost multiplier
    """
    def __init__(self) -> None:
        super().__init__(impl=_ThrusterLocomotionImpl(
            primaryEquivType=ThrusterPrimaryLocomotion))

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        # Don't call base class to avoid check that primary locomotion cost
        # multiplier isn't lower. The implementation still needs to be
        # called to perform the min TL check
        return self._impl.isCompatible(
            sequence=sequence,
            context=context)