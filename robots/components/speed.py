import common
import construction
import robots
import typing

class SpeedModification(robots.SpeedModificationInterface):
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
        
    def typeString(self) -> str:
        return 'Speed Modification'
    
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

    # NOTE: The reason this is '<None>' rather than just 'None' is so it looks
    # like the entry added to selectors for optional selection stages
    def componentString(self) -> str:
        return '<None>'

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
    reduce the robots endurance by 100%
    """
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
    - Compatibility: Not compatible with Agile locomotion modification
    - Compatibility: Not compatible with Tactical Speed Enhancement    
    - Compatibility: Not compatible with Vehicle Speed Movement locomotion modification
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
        - Aeroplane: Medium
        - Aquatic: Very Slow
        - VTOL: Medium
        - Walker: Very Slow
        - Hovercraft: Medium
        - Thrusters: ??????
    - Skill: Autopilot 0
    - Option: Additional Speed Increase
        - Range: 0-3
        - Trait: Speed Band +1 per level taken
        - Slots: 10% of Base Slots per level taken
        - Cost: Each increase doubles the cost of the modification
    - Requirement: Robots with Aeroplane locomotion must have Vehicle Speed
    Movement
    - Note: Grav locomotion systems equipped with vehicle speed movement are
    capable of propelling a robot to orbit 
    """
    # NOTE: The requirement that robots with Aeroplane locomotion must have this
    # component is handled by the fact this component being used in a mandatory
    # single select stage and all other component derived from SpeedEnhancement
    # are incompatible with Aeroplane locomotion
    # NOTE: The table on p23 doesn't have a Speed Band entry for Aeroplane. The
    # rules are really unclear, p17 says aeroplane locomotion can't go slower
    # than Slow (otherwise it stalls) and that any aeroplane locomotion robot
    # can be launched from a vehicle moving at Medium speed. That would suggest
    # the a default of either Slow or Medium, it depends on if it makes sense to
    # have an aeroplane robot that can't take off without the use of a secondary
    # or external form of locomotion.
    # I've gone with Medium as it's the same as the Mongoose and fan created
    # spreadsheets. However it seems odd to me that this means it's not possible
    # to create an aeroplane robot that is capable of supersonic speeds without
    # the use of a secondary form of locomotion. With the speed band increase
    # being limited to 3 levels it means the base speed band would need to be
    # VeryFast to allow it to be increased to Supersonic
    # NOTE: The table on p23 doesn't have an entry for Thrusters. I've no idea
    # what that is. It could be because Thruster locomotion gives the Thruster
    # trait, but that doesn't really make sense as the Thruster trait is in G
    # which is acceleration not speed. The spreadsheet doesn't allow you to
    # select a Speed Band for Thruster equipped robots. Until I find a better
    # option I'll do the same.
    # TODO It component sounds like this is something that can be turned on or
    # of. On p23 it says "Vehicle speed movement reduces a robot’s endurance by
    # a factor of four when in use. Each further movement enhancement halves the
    # robot remaining endurance". Note the "when in use" bit
    # TODO: Need to decide if Medium is the correct Speed Band for Aeroplane
    # (see note above)
    # TODO: Need to figure out if there is a Speed Band for thrusters
    # TODO: Handle Autopilot. I'm not sure if Autopilot in this context will be
    # a skill or a trait
    # TODO: I think, if a robot has the Flyer Trait, it should be updated with
    # the new Speed Band. I assume that's how some of the example robots have
    # a Flyer trait other than Idle (e.g. p216, p258). I'm not sure if that that
    # should be instead of as well as whatever trait I'm using to store the
    # SpeedBand for non-Flyer robots.

    _BaseSlotPercent = common.ScalarCalculation(
        value=25,
        name='Vehicle Speed Movement Base Slot Requirement Percentage')
    _AdditionalSlotPercent = common.ScalarCalculation(
        value=10,
        name='Vehicle Speed Movement Additional Increase Slot Requirement Percentage')

    _WheelsBaseSpeedBand = robots.SpeedBand.Slow
    _TracksBaseSpeedBand = robots.SpeedBand.VerySlow
    _GravBaseSpeedBand = robots.SpeedBand.High
    _AeroplaneBaseSpeedBand = robots.SpeedBand.Medium
    _AquaticBaseSpeedBand = robots.SpeedBand.VerySlow
    _VTOLBaseSpeedBand = robots.SpeedBand.Medium
    _WalkerBaseSpeedBand = robots.SpeedBand.VerySlow
    _HovercraftBaseSpeedBand = robots.SpeedBand.Medium

    _GravLocomotionNote = 'Grav locomotion systems equipped with vehicle speed movement are capable of propelling a robot to orbit (p23)'

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

        # TODO: This is temp behaviour until I figure out what the base
        # speed band for Thrusters is
        locomotion = context.findFirstComponent(
            componentType=robots.ThrusterPrimaryLocomotion,
            sequence=sequence)
        return locomotion == None

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
        if not speedBand:
            # TODO: Handle error
            return
        if additionalIncrease.value() > 0:
            speedBand = common.incrementEnum(
                value=speedBand,
                count=additionalIncrease.value())
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.VehicleSpeed,
            value=speedBand))
        
        isGrav = context.findFirstComponent(
            componentType=robots.GravPrimaryLocomotion,
            sequence=sequence) != None
        if isGrav:
            step.addNote(VehicleSpeedMovement._GravLocomotionNote)        

        context.applyStep(
            sequence=sequence,
            step=step)
        
    def _calcBaseSpeedBand(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.SpeedBand]:
        locomotion = context.findFirstComponent(
            componentType=robots.PrimaryLocomotionInterface,
            sequence=sequence)
        if not locomotion:
            return None

        if isinstance(locomotion, robots.WheelsPrimaryLocomotion) or \
            isinstance(locomotion, robots.WheelsATVPrimaryLocomotion):
            return VehicleSpeedMovement._WheelsBaseSpeedBand
        elif isinstance(locomotion, robots.TracksPrimaryLocomotion):
            return  VehicleSpeedMovement._TracksBaseSpeedBand
        elif isinstance(locomotion, robots.GravPrimaryLocomotion):
            return  VehicleSpeedMovement._GravBaseSpeedBand
        elif isinstance(locomotion, robots.AeroplanePrimaryLocomotion):
            return  VehicleSpeedMovement._AeroplaneBaseSpeedBand
        elif isinstance(locomotion, robots.AquaticPrimaryLocomotion):
            return  VehicleSpeedMovement._AquaticBaseSpeedBand
        elif isinstance(locomotion, robots.VTOLPrimaryLocomotion):
            return  VehicleSpeedMovement._VTOLBaseSpeedBand
        elif isinstance(locomotion, robots.WalkerPrimaryLocomotion):
            return  VehicleSpeedMovement._WalkerBaseSpeedBand  
        elif isinstance(locomotion, robots.HovercraftPrimaryLocomotion):
            return  VehicleSpeedMovement._HovercraftBaseSpeedBand

        return None   

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