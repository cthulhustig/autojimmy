import common
import construction
import robots
import typing

class SpeedModification(robots.RobotComponentInterface):
    """
    - Requirement: Not compatible with no locomotion for primary locomotion
    type (p22)    
    """
    # NOTE: The rules say "Locomotion modifications alter the performance
    # characteristics of a robot’s primary form of locomotion". Based on this
    # I'm making this component only apply to the primary locomotion type.
    # The logical side effect of this is you won't be able to apply it if you
    # use the rule that Thruster locomotion can be applied as a secondary
    # locomotion with the primary locomotion set to None (p17)
    # NOTE: I've intentionally not made Speed modifications incompatible with
    # BioRobots as there isn't anything that makes them obviously incompatible.
    # Normally the modifications would have an effect on endurance and the rules
    # do say standard robot Endurance doesn't apply for BioRobots (p88).
    # However, I don't think this makes it incompatible, just that the normal
    # Endurance costs/gains don't apply as it more like the natural ability
    # of the species the BioRobot is mimicking. This would be similar to how
    # the rules say a BioBot can have coatings but only if they're part of the
    # robots genome.

        
    def typeString(self) -> str:
        return 'Speed Modification'
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence):
            return False
                
        # Not compatible with no primary locomotion
        locomotion = context.findFirstComponent(
            componentType=robots.NoPrimaryLocomotion,
            sequence=sequence)
        return locomotion == None 
    
class NoSpeedModification(SpeedModification):
    """
    - Requirement: Not compatible with Aeroplane primary locomotion
    """
    # NOTE: This class is a hack to allow us to force robots with the Aeroplane
    # locomotion type to take Vehicle Speed Movement. The construction stage
    # is made mandatory and all SpeedModification derived components other than
    # VehicleSpeedMovement are made incompatible with Aeroplane locomotion.
    def __init__(self) -> None:
        super().__init__()

    def componentString(self) -> str:
        return 'None'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        # NOTE: Don't call base class as this component should be compatible
        # with all robots apart from the noted exception

        # Not compatible with Aeroplane primary locomotion
        locomotion = context.findFirstComponent(
            componentType=robots.AeroplanePrimaryLocomotion,
            sequence=sequence)
        return locomotion == None 

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        # NOTE: Don't create a step as we don't want this hacky component to be
        # shown in manifests
        pass       

class TacticalSpeedEnhancement(SpeedModification):
    """
    - Cost: 10% of Base Chassis Cost per meter added
    - Endurance: -10% per meter added
    - Requirement: Not compatible with Tactical Speed Reduction
    - Requirement: Not compatible with Vehicle Speed Movement locomotion
    modification
    - Requirement: Not compatible with Aeroplane primary locomotion  
    - Requirement: Tactical speed enhancement cannot increase a robot’s
    tactical movement rate beyond 12 metres per Minor Action
    - Requirement: At most 9 levels can be taken as any more than that will
    reduce the robot's endurance by 100%
    """
    # NOTE: The way the rules are worded around the the incompatibility with
    # Vehicle Speed Movement is a little ambiguous. Rather than saying they are
    # incompatible it says they can't be used 'in conjunction' with each other.
    # This could be taken to mean they are compatible, they just can't be used
    # at the same time. It would be an odd thing to say as I don't think anyone
    # would logically think they are something that would stack as they don't
    # share any common units, but it could be taken to mean that. The reason I
    # think it actually means incompatible is the wording of the Tactical Speed
    # Reduction as it says it can't be used in conjunction with the Agility
    # Enhancement, I don't think the Agility Enhancement is something that you
    # would logically turn on/off as it says it replaces the robot's components.
    # This would mean taking 'in conjunction' to mean you can have both
    # installed but not use both at the same time doesn't make sense at all,
    # the implication being it must mean only one can be installed at a time.
    # NOTE: Not being compatible with Tactical Speed Reduction and Vehicle
    # Speed Movement will come for free as all SpeedModification are
    # incompatible with each other so they will be a single select stage
    # NOTE: Not compatible with Aeroplane primary locomotion as the must have
    # Vehicle Speed Movement which is incompatible with this component

    _PerMeterCostPercent = common.ScalarCalculation(
        value=10,
        name='Tactical Speed Enhancement Per Meter Cost Percentage')
    _PerMeterEndurancePercent = common.ScalarCalculation(
        value=-10,
        name='Tactical Speed Enhancement Per Meter Endurance Reduction Percentage')    

    _MaxAllowedSpeed = 12
    _MaxAllowedIncrease = 9

    def __init__(self) -> None:
        super().__init__()

        self._speedIncreaseOption = construction.IntegerOption(
            id='SpeedIncrease',
            name='Speed Increase',
            value=1,
            minValue=1,
            description='Specify the speed increase in meters.') 

    def componentString(self) -> str:
        return 'Tactical Speed Enhancement'         

    def instanceString(self) -> str:
        return '{component} +{increase}m'.format(
            component=self.componentString(),
            increase=self._speedIncreaseOption.value())      

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        
        # Not compatible if no increase is possible
        maxIncrease = self._calcMaxIncrease(
            sequence=sequence,
            context=context)
        if not maxIncrease:
            return False        
        
        # Not compatible with Aeroplane primary locomotion
        locomotion = context.findFirstComponent(
            componentType=robots.AeroplanePrimaryLocomotion,
            sequence=sequence)
        return locomotion == None     

    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._speedIncreaseOption]

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        maxIncrease = self._calcMaxIncrease(
            sequence=sequence,
            context=context)
        if maxIncrease:
            self._speedIncreaseOption.setMin(1)
            self._speedIncreaseOption.setMax(maxIncrease)
        else:
            self._speedIncreaseOption.setMin(0)
            self._speedIncreaseOption.setMax(0)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        levelsTaken = common.ScalarCalculation(
            value=self._speedIncreaseOption.value(),
            name='Requested Speed Increase')

        totalCostPercent = common.Calculator.multiply(
            lhs=TacticalSpeedEnhancement._PerMeterCostPercent,
            rhs=levelsTaken,
            name=f'Total Tactical Speed Enhancement Cost Percentage')
        totalCost = common.Calculator.takePercentage(
            value=context.baseChassisCredits(sequence=sequence),
            percentage=totalCostPercent,
            name=f'Total Tactical Speed Enhancement Cost')
        step.setCredits(
            credits=construction.ConstantModifier(value=totalCost))

        speedModifier = common.Calculator.equals(
            value=levelsTaken,
            name='Total Tactical Speed Enhancement Speed Modified')
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Speed,
            modifier=construction.ConstantModifier(speedModifier)))
        
        if context.hasAttribute(
            attributeId=robots.RobotAttributeId.Endurance,
            sequence=sequence):
            totalEndurancePercent = common.Calculator.multiply(
                lhs=TacticalSpeedEnhancement._PerMeterEndurancePercent,
                rhs=levelsTaken,
                name=f'Total Tactical Speed Enhancement Endurance Reduction Percentage')
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=robots.RobotAttributeId.Endurance,
                modifier=construction.PercentageModifier(
                    value=totalEndurancePercent)))

        context.applyStep(
            sequence=sequence,
            step=step)

    def _calcMaxIncrease(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> int:
        speed = context.attributeValue(
            attributeId=robots.RobotAttributeId.Speed,
            sequence=sequence)
        if not speed:
            return 0

        return common.clamp(
            value=TacticalSpeedEnhancement._MaxAllowedSpeed - speed.value(),
            minValue=0,
            maxValue=TacticalSpeedEnhancement._MaxAllowedIncrease)
        
class TacticalSpeedReduction(SpeedModification):
    """
    - Cost Saving: 10% of Base Chassis Cost per meter reduced
    - Endurance: +10% per meter reduced
    - Requirement: Not compatible with Agile locomotion modification
    - Requirement: Not compatible with Tactical Speed Enhancement    
    - Requirement: Not compatible with Vehicle Speed Movement locomotion modification
    - Requirement: Not compatible with Aeroplane primary locomotion  
    - Requirement: Can't reduce robot speed below 1
    """
    # NOTE: Not being compatible with Tactical Speed Reduction and Vehicle
    # Speed Movement will come for free as all SpeedEnhancement are incompatible
    # with each other so they will be a single select stage
    # NOTE: Not compatible with Aeroplane primary locomotion as the must have
    # Vehicle Speed Movement which is incompatible with this component

    _PerMeterCostPercent = common.ScalarCalculation(
        value=-10,
        name='Tactical Speed Reduction Per Meter Cost Saving Percentage')
    _PerMeterEndurancePercent = common.ScalarCalculation(
        value=10,
        name='Tactical Speed Reduction Per Meter Endurance Increase Percentage')   
        
    def __init__(self) -> None:
        super().__init__()

        self._speedReductionOption = construction.IntegerOption(
            id='SpeedDecrease',
            name='Speed Decrease',
            value=1,
            minValue=1,
            description='Specify the speed decrease in meters.')         

    def componentString(self) -> str:
        return 'Tactical Speed Reduction'        

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        
        # Not compatible with Agility Enhancement
        agility = context.findFirstComponent(
            componentType=robots.AgilityEnhancement,
            sequence=sequence)
        if agility != None:
            return False

        # Not compatible with Aeroplane primary locomotion
        locomotion = context.findFirstComponent(
            componentType=robots.AeroplanePrimaryLocomotion,
            sequence=sequence)
        return locomotion == None    

    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._speedReductionOption]

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        maxDecrease = self._calcMaxDecrease(
            sequence=sequence,
            context=context)
        if maxDecrease:
            self._speedReductionOption.setMin(1)
            self._speedReductionOption.setMax(maxDecrease)
        else:
            self._speedReductionOption.setMin(0)
            self._speedReductionOption.setMax(0)    

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        levelsTaken = common.ScalarCalculation(
            value=self._speedReductionOption.value(),
            name='Tactical Speed Reduction Levels Requested')

        totalCostPercent = common.Calculator.multiply(
            lhs=TacticalSpeedReduction._PerMeterCostPercent,
            rhs=levelsTaken,
            name=f'Total Tactical Speed Reduction Cost Saving Percentage')
        totalSaving = common.Calculator.takePercentage(
            value=context.baseChassisCredits(sequence=sequence),
            percentage=totalCostPercent,
            name=f'Total Tactical Speed Reduction Cost Saving')
        step.setCredits(
            credits=construction.ConstantModifier(value=totalSaving))

        speedModifier = common.Calculator.negate(
            value=levelsTaken,
            name='Total Tactical Speed Reduction Speed Modifier')
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Speed,
            modifier=construction.ConstantModifier(speedModifier)))
        
        if context.hasAttribute(
            attributeId=robots.RobotAttributeId.Endurance,
            sequence=sequence):        
            totalEndurancePercent = common.Calculator.multiply(
                lhs=TacticalSpeedReduction._PerMeterEndurancePercent,
                rhs=levelsTaken,
                name=f'Total Tactical Speed Reduction Endurance Reduction Percentage')
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=robots.RobotAttributeId.Endurance,
                modifier=construction.PercentageModifier(
                    value=totalEndurancePercent)))

        context.applyStep(
            sequence=sequence,
            step=step)    

    def _calcMaxDecrease(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> int:
        speed = context.attributeValue(
            attributeId=robots.RobotAttributeId.Speed,
            sequence=sequence)
        if not speed:
            return 0
        return max(speed.value() - 1, 0)

class VehicleSpeedMovement(SpeedModification):
    """
    - Slots: 25% of Base Slots rounded up
    - Cost: Base Chassis Cost
    - Trait: Speed Band
        - Wheels (including ATV): Slow
        - Tracks: Very Slow
        - Grav: High
        - Aeroplane: Medium (clarified by Geir)
        - Aquatic: Very Slow
        - VTOL: Medium
        - Walker: Very Slow
        - Hovercraft: Medium
        - Thrusters: Hypersonic (clarified by Geir)
    - Trait: Autopilot 0
    - Trait: Flyer <SpeedBand> (only if Flyer was granted by Primary locomotion)
    - Option: Additional Speed Increase
        - Range: 0-3
        - Trait: Speed Band +1 per level taken
        - Slots: 10% of Base Slots per level taken
        - Cost: Each increase doubles the cost of the modification
    - Requirement: Robots with Aeroplane locomotion must have Vehicle Speed
    Movement
    - Requirement: Vehicle speed movement reduces a robot's endurance by a
    factor of four when in use. Each further movement enhancement halves
    the robot remaining endurance.
    - Note: Grav locomotion systems equipped with vehicle speed movement are
    capable of propelling a robot to orbit. (p23)
    - Note: Thruster locomotion can only achieve Hypersonic speeds in a vacuum.
    (clarified by Geir Lanesskog, Robot Handbook author)
    """
    # NOTE: The requirement that robots with Aeroplane locomotion must have this
    # component is handled by the fact this component being used in a mandatory
    # single select stage and all other component derived from SpeedEnhancement
    # are incompatible with Aeroplane locomotion
    # NOTE: This component sounds like this is something that can be turned on
    # or off. On p23 it says "Vehicle speed movement reduces a robot’s endurance
    # by a factor of four when in use. Each further movement enhancement halves
    # the robot remaining endurance". Note the "when in use" bit.
    # I don't think this means anything from an implementation point of view
    # - This component sets the VehicleSpeed attribute but it's the only
    #   component that sets it so it can be taken to only apply when using
    #   Vehicle Speed Movement
    # - This component sets the AutoPilot trait but this isn't an issue as the
    #   only other place it's set is in the AutoPilot slot option and this
    #   requires Vehicle Speed Movement for compatibility so AutoPilot can be
    #   taken to only apply when using Vehicle Speed Movement
    # NOTE: Setting the VehicleEndurance attribute only works here as it's
    # after the last place the Endurance attribute is set. The Endurance
    # attribute is set in Locomotion and Endurance which occur before this
    # component in construction. It can also be set by the other Tactical
    # Speed Increase and Reduction components but they're incompatible with
    # Vehicle Speed Movement.
    # NOTE: I didn't see anything in the rules that explicitly say the Vehicle
    # Speed Movement sets the Flyer trait but it's implied by the fact there
    # are example robots (e.g. p133 & p134) that have a Flyer trait higher
    # than Idle but I can't find anything that explicitly says it gives that.
    # I think it comes from Vehicle Speed Moment as, although the robot's don't
    # state they have it, all the examples I can see have the extra Endurance
    # in brackets that the Final Endurance section suggests (p23)
    # NOTE: The fact Aeroplane have a base Speed Band of Medium and Thrusters
    # have a base Speed Band of Hypersonic was clarified by Geir in this thread.
    # He also 
    # https://forum.mongoosepublishing.com/threads/robot-handbook-rule-clarifications.124669/

    _BaseSlotPercent = common.ScalarCalculation(
        value=25,
        name='Vehicle Speed Movement Base Slot Requirement Percentage')
    _AdditionalSlotPercent = common.ScalarCalculation(
        value=10,
        name='Vehicle Speed Movement Additional Increase Slot Requirement Percentage')
    _AutopilotRating = common.ScalarCalculation(
        value=0,
        name='Vehicle Speed Movement Base Autopilot Rating')
    _InitialEnduranceScale = common.ScalarCalculation(
        value=0.25,
        name='Vehicle Speed Movement Initial Endurance Scale')
    _IncreaseLevelEnduranceScale = common.ScalarCalculation(
        value=0.5,
        name='Vehicle Speed Movement Additional Increase Endurance Scale')

    _SpeedBandTypeMap = {
        robots.WheelsPrimaryLocomotion: robots.SpeedBand.Slow,
        robots.WheelsATVPrimaryLocomotion: robots.SpeedBand.Slow,
        robots.TracksPrimaryLocomotion: robots.SpeedBand.VerySlow,
        robots.GravPrimaryLocomotion: robots.SpeedBand.High,
        robots.AeroplanePrimaryLocomotion: robots.SpeedBand.Medium,
        robots.AquaticPrimaryLocomotion: robots.SpeedBand.VerySlow,
        robots.VTOLPrimaryLocomotion: robots.SpeedBand.Medium,
        robots.WalkerPrimaryLocomotion: robots.SpeedBand.VerySlow,
        robots.HovercraftPrimaryLocomotion: robots.SpeedBand.Medium,
        robots.ThrusterPrimaryLocomotion: robots.SpeedBand.Hypersonic
    }

    # NOTE: ThrusterPrimaryLocomotion is intentionally not included on this list
    # as the rules don't give it the Flyer trait (p16).
    _FlyerPrimaryLocomotions = [
        robots.GravPrimaryLocomotion,
        robots.AeroplanePrimaryLocomotion,
        robots.VTOLPrimaryLocomotion
    ]

    _GravLocomotionNote = 'The robot can reach orbit using grav locomotion and vehicle speed movement. (p23)'
    _ThrusterLocomotionNote = 'Thruster locomotion can only achieve hypersonic speeds in a vacuum. (clarified by Geir Lanesskog, Robot Handbook author) '

    def __init__(self) -> None:
        super().__init__()

        self._additionalIncreaseOption = construction.IntegerOption(
            id='AdditionalIncrease',
            name='Additional Increase',
            value=0,
            minValue=0,
            maxValue=3,
            description='Specify additional speed and increases.')        

    def componentString(self) -> str:
        return 'Vehicle Speed Movement'
    
    def instanceString(self) -> str:
        increase = self._additionalIncreaseOption.value()
        if increase <= 0:
            return super().instanceString()
        return 'Improved {component} {increase}'.format(
            component=self.componentString(),
            increase=increase)

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        
        return self._calcBaseSpeedBand(
            sequence=sequence,
            context=context) != None

    def options(self) -> typing.List[construction.ComponentOption]:
        options = []
        if self._additionalIncreaseOption.isEnabled():
            options.append(self._additionalIncreaseOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        maxIncrease = self._calcMaxIncrease(
            sequence=sequence,
            context=context)
        self._additionalIncreaseOption.setMax(value=maxIncrease)
        self._additionalIncreaseOption.setEnabled(enabled=maxIncrease > 0)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        additionalIncrease = common.ScalarCalculation(
            value=self._additionalIncreaseOption.value(),
            name='Additional Speed Band Increase Requested')
        
        totalCost = common.Calculator.equals(
            value=context.baseChassisCredits(sequence=sequence),
            name='Vehicle Speed Movement Base Cost')
        for index in range(additionalIncrease.value()):
            totalCost = common.Calculator.multiply(
                lhs=totalCost,
                rhs=common.ScalarCalculation(value=2),
                name=f'Increase {index + 1} Vehicle Speed Movement Cost')
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))
        
        totalSlotsPercent = common.Calculator.add(
            lhs=VehicleSpeedMovement._BaseSlotPercent,
            rhs=common.Calculator.multiply(
                lhs=VehicleSpeedMovement._AdditionalSlotPercent,
                rhs=additionalIncrease),
            name='Total Vehicle Speed Movement Slot Requirement Percentage')
        totalSlots = common.Calculator.ceil(
            value=common.Calculator.takePercentage(
                value=context.baseSlots(sequence=sequence),
                percentage=totalSlotsPercent),
            name='Total Vehicle Speed Movement Cost')
        step.setSlots(slots=construction.ConstantModifier(value=totalSlots))
              
        speedBand = self._calcBaseSpeedBand(
            sequence=sequence,
            context=context)
        assert(speedBand != None) # Compatibility should enforce this
        if additionalIncrease.value() > 0:
            speedBand = common.incrementEnum(
                value=speedBand,
                count=additionalIncrease.value())
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.VehicleSpeed,
            value=speedBand))
        
        # If the primary locomotion gives the robot the Flyer trait then set it
        # to the speed band. This doesn't just check for the existence of the
        # Flyer trait as it should only apply if the primary locomotion gave the
        # trait as Vehicle Speed Motion only applies to the primary locomotion.
        hasFlyerPrimary = False
        for locomotionType in VehicleSpeedMovement._FlyerPrimaryLocomotions:
            if context.hasComponent(
                componentType=locomotionType,
                sequence=sequence):
                hasFlyerPrimary = True
                break
        if hasFlyerPrimary:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=robots.RobotAttributeId.Flyer,
                value=speedBand))
        
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Autopilot,
            value=VehicleSpeedMovement._AutopilotRating))

        endurance = context.attributeValue(
            attributeId=robots.RobotAttributeId.Endurance,
            sequence=sequence)
        if endurance:
            vehicleEndurance = common.Calculator.multiply(
                lhs=endurance,
                rhs=VehicleSpeedMovement._InitialEnduranceScale)
            for _ in range(additionalIncrease.value()):
                vehicleEndurance = common.Calculator.multiply(
                    lhs=vehicleEndurance,
                    rhs=VehicleSpeedMovement._IncreaseLevelEnduranceScale)
            vehicleEndurance = common.Calculator.rename(
                value=vehicleEndurance,
                name='Vehicle Speed Movement Endurance')
            step.addFactor(construction.SetAttributeFactor(
                attributeId=robots.RobotAttributeId.VehicleEndurance,
                value=vehicleEndurance))
        
        isGrav = context.findFirstComponent(
            componentType=robots.GravPrimaryLocomotion,
            sequence=sequence) != None
        if isGrav:
            step.addNote(VehicleSpeedMovement._GravLocomotionNote)

        isThruster = context.findFirstComponent(
            componentType=robots.ThrusterPrimaryLocomotion,
            sequence=sequence) != None
        if isThruster:
            step.addNote(VehicleSpeedMovement._ThrusterLocomotionNote)

        context.applyStep(
            sequence=sequence,
            step=step)
        
    def _calcBaseSpeedBand(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.SpeedBand]:
        locomotion = context.findFirstComponent(
            componentType=robots.PrimaryLocomotion,
            sequence=sequence)
        if not locomotion:
            return None
        return VehicleSpeedMovement._SpeedBandTypeMap.get(type(locomotion))

    def _calcMaxIncrease(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> int:
        baseSpeed = self._calcBaseSpeedBand(
            sequence=sequence,
            context=context)
        if not baseSpeed:
            return 0
        
        baseIndex = common.enumToIndex(value=baseSpeed)
        maxIndex = len(robots.SpeedBand) - 1
        return min(maxIndex - baseIndex, 3)