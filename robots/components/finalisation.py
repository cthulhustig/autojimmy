import common
import construction
import enum
import math
import robots
import traveller
import typing



#   █████████  ████            █████       ███████████                                                           ████ 
#  ███░░░░░███░░███           ░░███       ░░███░░░░░███                                                         ░░███ 
# ░███    ░░░  ░███   ██████  ███████      ░███    ░███   ██████  █████████████    ██████  █████ █████  ██████   ░███ 
# ░░█████████  ░███  ███░░███░░░███░       ░██████████   ███░░███░░███░░███░░███  ███░░███░░███ ░░███  ░░░░░███  ░███ 
#  ░░░░░░░░███ ░███ ░███ ░███  ░███        ░███░░░░░███ ░███████  ░███ ░███ ░███ ░███ ░███ ░███  ░███   ███████  ░███ 
#  ███    ░███ ░███ ░███ ░███  ░███ ███    ░███    ░███ ░███░░░   ░███ ░███ ░███ ░███ ░███ ░░███ ███   ███░░███  ░███ 
# ░░█████████  █████░░██████   ░░█████     █████   █████░░██████  █████░███ █████░░██████   ░░█████   ░░████████ █████
#  ░░░░░░░░░  ░░░░░  ░░░░░░     ░░░░░     ░░░░░   ░░░░░  ░░░░░░  ░░░░░ ░░░ ░░░░░  ░░░░░░     ░░░░░     ░░░░░░░░ ░░░░░ 

# This is based on the min manipulator size for different mounts (p61)
def _manipulatorSizeToWeaponSize(manipulatorSize: int) -> typing.Optional[traveller.WeaponSize]:
    if manipulatorSize >= 7:
        return traveller.WeaponSize.Heavy
    if manipulatorSize >= 5:
        return traveller.WeaponSize.Medium
    if manipulatorSize >= 3:
        return traveller.WeaponSize.Small
    return None

class UnusedSlotRemoval(robots.RobotComponentInterface):
    """
    - Cost Saving: Cr100 per slot removed
    """    
    # NOTE: The fact this component doesn't check if there are any slots to
    # remove is important as we don't want the component to be removed if
    # the user temporarily adds a new component that takes the robot over
    # the slot limit. The problem with having it removed is the None option
    # will be selected (as it would be compatible) and then when the
    # temporary component is removed it it will remain as None as the
    # default component logic won't get applied (as there is a component)
    
    _PerSlotCostSaving = common.ScalarCalculation(
        value=-100,
        name='Unused Slot Removal Per Slot Cost Saving')
    
    def typeString(self) -> str:
        return 'Unused Slot Removal'
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:   
        slots = self._slotCount()
        if not slots: # None indicates remove all slots
            slots = self._calculateUnusedSlots(
                sequence=sequence,
                context=context)
        if slots.value() <= 0:
            return # No slots to remove so no step to create
            
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())               

        # NOTE: This assumes that the saving is a negative value
        cost = common.Calculator.multiply(
            lhs=CustomSlotRemoval._PerSlotCostSaving,
            rhs=slots,
            name=f'{self.componentString()} Total Cost Saving')
        step.setCredits(credits=construction.ConstantModifier(value=cost))

        step.setSlots(slots=construction.ConstantModifier(value=slots))

        context.applyStep(
            sequence=sequence,
            step=step)    
    
    def _calculateUnusedSlots(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> common.ScalarCalculation:
        maxSlots = context.attributeValue(
            attributeId=robots.RobotAttributeId.MaxSlots,
            sequence=sequence)
        if not maxSlots:
            return common.ScalarCalculation(
                value=0,
                name='Unused Slots When No Max Slots')
        assert(isinstance(maxSlots, common.ScalarCalculation))
        usedSlots = context.usedSlots(sequence=sequence)

        # NOTE: Construction intentionally allows more than the max slots to be
        # allocated so the unused slots needs to be clamped to a min of 0
        return common.Calculator.max(
            lhs=common.Calculator.subtract(
                lhs=maxSlots,
                rhs=usedSlots),
            rhs=common.ScalarCalculation(value=0),
            name='Unused Slots')
    
    def _slotCount(self) -> typing.Optional[common.ScalarCalculation]:
        raise RuntimeError(f'{type(self)} is derived from UnusedSlotRemoval so must implement _slotCount')    

class AllSlotRemoval(UnusedSlotRemoval):
    def __init__(self) -> None:
        super().__init__()
        
    def componentString(self) -> str:
        return 'Remove All'
        
    def _slotCount(self) -> typing.Optional[common.ScalarCalculation]:
        return None # Remove all

class CustomSlotRemoval(UnusedSlotRemoval):
    def __init__(self) -> None:
        super().__init__()

        self._slotCountOption = construction.IntegerOption(
            id='SlotCount',
            name='Slot Count',
            value=1,
            minValue=1,
            description='Specify the number of slots to remove')
        
    def instanceString(self) -> str:
        slots = self._slotCount()
        if slots:      
            return f'{self.componentString()} (x{slots.value()})'      
        return super().instanceString()
        
    def componentString(self) -> str:
        return 'Remove Custom'

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._slotCountOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        removableSlots = self._calculateUnusedSlots(
            sequence=sequence,
            context=context)
        hasSlotsToRemove = removableSlots.value() > 0
        if hasSlotsToRemove:
            self._slotCountOption.setMax(value=removableSlots.value())
        self._slotCountOption.setEnabled(hasSlotsToRemove)

    def _slotCount(self) -> typing.Optional[common.ScalarCalculation]:
        return common.ScalarCalculation(
            value=self._slotCountOption.value() if self._slotCountOption.isEnabled() else 0,
            name='Specified Custom Slot Count')
    


#   █████████                         █████    █████           █████████                    █████           
#  ███░░░░░███                       ░░███    ░░███           ███░░░░░███                  ░░███            
# ░███    ░░░  █████ ████ ████████   ███████   ░███████      ███     ░░░   ██████   █████  ███████    █████ 
# ░░█████████ ░░███ ░███ ░░███░░███ ░░░███░    ░███░░███    ░███          ███░░███ ███░░  ░░░███░    ███░░  
#  ░░░░░░░░███ ░███ ░███  ░███ ░███   ░███     ░███ ░███    ░███         ░███ ░███░░█████   ░███    ░░█████ 
#  ███    ░███ ░███ ░███  ░███ ░███   ░███ ███ ░███ ░███    ░░███     ███░███ ░███ ░░░░███  ░███ ███ ░░░░███
# ░░█████████  ░░███████  ████ █████  ░░█████  ████ █████    ░░█████████ ░░██████  ██████   ░░█████  ██████ 
#  ░░░░░░░░░    ░░░░░███ ░░░░ ░░░░░    ░░░░░  ░░░░ ░░░░░      ░░░░░░░░░   ░░░░░░  ░░░░░░     ░░░░░  ░░░░░░  
#               ███ ░███                                                                                    
#              ░░██████                                                                                     
#               ░░░░░░  

class SynthAdditionalCosts(robots.RobotComponentInterface):
    # NOTE: This multiplier is applied to all costs except the cost for skills.
    # This includes the cost of the Synthetic component. (p86 & p88)
    _SyntheticsAdditionalCostMultiplier = common.ScalarCalculation(
        value=3,
        name='Synthetic Robot Additional Cost Multiplier')
    _SyntheticsAdditionalCostPhases = [phase for phase in robots.RobotPhase if phase != robots.RobotPhase.Skills]

    def componentString(self) -> str:
        return 'Synth Additional Costs'

    def typeString(self) -> str:
        return 'Synth Additional Costs'
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return context.hasComponent(
            componentType=robots.Synthetic,
            sequence=sequence)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:   
        synthetic = context.findFirstComponent(
            componentType=robots.Synthetic,
            sequence=sequence)
        if not synthetic:
            return
        assert(isinstance(synthetic, robots.Synthetic))
            
        standardCost = context.multiPhaseCost(
            sequence=sequence,
            costId=robots.RobotCost.Credits,
            phases=SynthAdditionalCosts._SyntheticsAdditionalCostPhases)
        standardCost = common.Calculator.rename(
            value=standardCost,
            name='Robot Cost Without Skill Costs')

        # NOTE: This subtracts 1 from the multiplier as we're calculating
        # the additional cost not the total cost
        additionalCost = common.Calculator.multiply(
            lhs=standardCost,
            rhs=common.Calculator.subtract(
                lhs=SynthAdditionalCosts._SyntheticsAdditionalCostMultiplier,
                rhs=common.ScalarCalculation(value=1)),
            name='Synthetic Robot Additional Cost')
        
        step = robots.RobotStep(
            name=f'Additional Cost',
            type=synthetic.componentString())
        step.setCredits(
            credits=construction.ConstantModifier(value=additionalCost))
        context.applyStep(
            sequence=sequence,
            step=step)
        



#    █████████                    █████       ██████   ██████              █████  ███     ██████   ███                      █████     ███                     
#   ███░░░░░███                  ░░███       ░░██████ ██████              ░░███  ░░░     ███░░███ ░░░                      ░░███     ░░░                      
#  ███     ░░░   ██████   █████  ███████      ░███░█████░███   ██████   ███████  ████   ░███ ░░░  ████   ██████   ██████   ███████   ████   ██████  ████████  
# ░███          ███░░███ ███░░  ░░░███░       ░███░░███ ░███  ███░░███ ███░░███ ░░███  ███████   ░░███  ███░░███ ░░░░░███ ░░░███░   ░░███  ███░░███░░███░░███ 
# ░███         ░███ ░███░░█████   ░███        ░███ ░░░  ░███ ░███ ░███░███ ░███  ░███ ░░░███░     ░███ ░███ ░░░   ███████   ░███     ░███ ░███ ░███ ░███ ░███ 
# ░░███     ███░███ ░███ ░░░░███  ░███ ███    ░███      ░███ ░███ ░███░███ ░███  ░███   ░███      ░███ ░███  ███ ███░░███   ░███ ███ ░███ ░███ ░███ ░███ ░███ 
#  ░░█████████ ░░██████  ██████   ░░█████     █████     █████░░██████ ░░████████ █████  █████     █████░░██████ ░░████████  ░░█████  █████░░██████  ████ █████
#   ░░░░░░░░░   ░░░░░░  ░░░░░░     ░░░░░     ░░░░░     ░░░░░  ░░░░░░   ░░░░░░░░ ░░░░░  ░░░░░     ░░░░░  ░░░░░░   ░░░░░░░░    ░░░░░  ░░░░░  ░░░░░░  ░░░░ ░░░░░ 

class CostModification(robots.RobotComponentInterface):
    def typeString(self) -> str:
        return 'Cost Modification'
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence):
            return False
        
        totalCost = context.totalCredits(sequence=sequence)
        return totalCost.value() > 0
    
class FixedCostModifier(CostModification):
    def __init__(self):
        super().__init__()

        self._creditsOption = construction.FloatOption(
            id='CostModifier',
            name='Cost Modifier',
            value=0,
            description='The number of credits to add to or remove from the final cost of the robot')
        
    def fixedModifier(self) -> common.ScalarCalculation:
        return common.ScalarCalculation(
            value=self._creditsOption.value(),
            name='Specified Fixed Cost Modifier')
    
    def componentString(self) -> str:
        return 'Fixed Cost Modifier'
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._creditsOption]

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        totalCost = context.totalCredits(sequence=sequence)
        self._creditsOption.setMin(-totalCost.value())

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        costModifier = self.fixedModifier()
        if costModifier.value() == 0:
            return
        stepName = 'Cost {type} ({amount})'.format(
            type='Reduction' if costModifier.value() < 0 else 'Increase',
            amount=common.formatNumber(
                number=costModifier.value(),
                alwaysIncludeSign=True,
                prefix='Cr'))
        step = robots.RobotStep(
            name=stepName,
            type=self.typeString())
        step.setCredits(
            credits=construction.ConstantModifier(value=costModifier))
        context.applyStep(
            sequence=sequence,
            step=step)
        
class PercentageCostModifier(CostModification):
    def __init__(self):
        super().__init__()

        self._creditsOption = construction.IntegerOption(
            id='CostModifier',
            name='Cost Modifier',
            value=0,
            minValue=-100,
            description='The percentage to add to or remove from the final cost of the robot')
        
    def percentModifier(self) -> common.ScalarCalculation:
        return common.ScalarCalculation(
            value=self._creditsOption.value(),
            name='Specified Percentage Cost Modifier')
    
    def componentString(self) -> str:
        return 'Percentage Cost Modifier'
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._creditsOption]

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        percentageModifier = self.percentModifier()
        if percentageModifier.value() == 0:
            return
        costModifier = common.Calculator.takePercentage(
            value=context.totalCredits(sequence=sequence),
            percentage=percentageModifier,
            name='Fixed Cost Modifier')

        stepName = 'Cost {type} ({amount})'.format(
            type='Reduction' if percentageModifier.value() < 0 else 'Increase',
            amount=common.formatNumber(
                number=percentageModifier.value(),
                alwaysIncludeSign=True,
                suffix='%'))
        step = robots.RobotStep(
            name=stepName,
            type=self.typeString())
        step.setCredits(
            credits=construction.ConstantModifier(value=costModifier))
        context.applyStep(
            sequence=sequence,
            step=step)



#    █████████                    █████       ███████████                                      █████  ███                     
#   ███░░░░░███                  ░░███       ░░███░░░░░███                                    ░░███  ░░░                      
#  ███     ░░░   ██████   █████  ███████      ░███    ░███   ██████  █████ ████ ████████    ███████  ████  ████████    ███████
# ░███          ███░░███ ███░░  ░░░███░       ░██████████   ███░░███░░███ ░███ ░░███░░███  ███░░███ ░░███ ░░███░░███  ███░░███
# ░███         ░███ ░███░░█████   ░███        ░███░░░░░███ ░███ ░███ ░███ ░███  ░███ ░███ ░███ ░███  ░███  ░███ ░███ ░███ ░███
# ░░███     ███░███ ░███ ░░░░███  ░███ ███    ░███    ░███ ░███ ░███ ░███ ░███  ░███ ░███ ░███ ░███  ░███  ░███ ░███ ░███ ░███
#  ░░█████████ ░░██████  ██████   ░░█████     █████   █████░░██████  ░░████████ ████ █████░░████████ █████ ████ █████░░███████
#   ░░░░░░░░░   ░░░░░░  ░░░░░░     ░░░░░     ░░░░░   ░░░░░  ░░░░░░    ░░░░░░░░ ░░░░ ░░░░░  ░░░░░░░░ ░░░░░ ░░░░ ░░░░░  ░░░░░███
#                                                                                                                     ███ ░███
#                                                                                                                    ░░██████ 
#                                                                                                                     ░░░░░░  

class CostRounding(robots.RobotComponentInterface):
    def typeString(self) -> str:
        return 'Cost Rounding'
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence):
            return False
        
        totalCost = context.totalCredits(sequence=sequence)
        return totalCost.value() > 0        
        
class SignificantFigureCostRounding(CostRounding):
    def __init__(self):
        super().__init__()

        self._creditsOption = construction.IntegerOption(
            id='SignificantFigures',
            name='Significant Figures',
            value=1,
            minValue=1,
            description='The number of significant figures to round the final robot cost to.')
        
    def significantFigures(self) -> common.ScalarCalculation:
        return common.ScalarCalculation(
            value=self._creditsOption.value(),
            name='Specified Significant Figures')
    
    def componentString(self) -> str:
        return 'Significant Figures'
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._creditsOption]

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        totalCost = context.totalCredits(sequence=sequence)
        roundedCost = common.Calculator.significantDigits(
            value=totalCost,
            digits=self.significantFigures(),
            name='Rounded Total Cost')
        costModifier = common.Calculator.subtract(
            lhs=roundedCost,
            rhs=totalCost,
            name='Rounding Cost Modifier')

        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        step.setCredits(
            credits=construction.ConstantModifier(value=costModifier))
        context.applyStep(
            sequence=sequence,
            step=step)




#  ███████████  ███                       ████   ███                     █████     ███                     
# ░░███░░░░░░█ ░░░                       ░░███  ░░░                     ░░███     ░░░                      
#  ░███   █ ░  ████  ████████    ██████   ░███  ████   █████   ██████   ███████   ████   ██████  ████████  
#  ░███████   ░░███ ░░███░░███  ░░░░░███  ░███ ░░███  ███░░   ░░░░░███ ░░░███░   ░░███  ███░░███░░███░░███ 
#  ░███░░░█    ░███  ░███ ░███   ███████  ░███  ░███ ░░█████   ███████   ░███     ░███ ░███ ░███ ░███ ░███ 
#  ░███  ░     ░███  ░███ ░███  ███░░███  ░███  ░███  ░░░░███ ███░░███   ░███ ███ ░███ ░███ ░███ ░███ ░███ 
#  █████       █████ ████ █████░░████████ █████ █████ ██████ ░░████████  ░░█████  █████░░██████  ████ █████
# ░░░░░       ░░░░░ ░░░░ ░░░░░  ░░░░░░░░ ░░░░░ ░░░░░ ░░░░░░   ░░░░░░░░    ░░░░░  ░░░░░  ░░░░░░  ░░░░ ░░░░░ 

class Finalisation(robots.RobotComponentInterface):
    _AtmosphereFlyerLocomotions = [
        robots.AeroplanePrimaryLocomotion,
        robots.VTOLPrimaryLocomotion,
        robots.VTOLSecondaryLocomotion
    ]
    _GraveFlyerLocomotions = [
        robots.GravPrimaryLocomotion,
        robots.GravSecondaryLocomotion
    ]
    _ImprovedMaintenanceOptions = [
        robots.SelfMaintenanceDefaultSuiteOption,
        robots.SelfMaintenanceSlotOption
    ]
    _AutopilotVehicleSkills = [
        traveller.DriveSkillDefinition,
        traveller.FlyerSkillDefinition,
        robots.RobotVehicleSkillDefinition
    ]

    # These are the sensor components that require an Electronics skill
    _SkilledSensorSlotOptions = [
        robots.BioscannerSensorSlotOption,
        robots.DensitometerSensorSlotOption,
        robots.NeuralActivitySensorSlotOption,
        robots.PlanetologySensorSuiteSlotOption
    ]

    # Mapping of Android and BioRobot components to lists of the brain types
    # that allows the robot to be suitably life like that they don't fall into
    # the uncanny valley. Lower tier brains can be used however robots suffer
    # a DM-2 to social interactions (p86 & p88).
    # This is done here so it can be added as a warning like some of the other
    # construction level notes added during finalisation
    _SyntheticMinBrainMap = {
        robots.BasicAndroidSynthetic: (
            "Basic (x) or Hunter/Killer",
            [robots.BasicBrain, robots.HunterKillerBrain, robots.SkilledRobotBrain, robots.BrainInAJarBrain]),
        robots.ImprovedAndroidSynthetic: (
            "Advanced",
            [robots.AdvancedBrain, robots.VeryAdvancedBrain, robots.SelfAwareBrain, robots.ConsciousBrain, robots.BrainInAJarBrain]),
        robots.EnhancedAndroidSynthetic: (
            "Very Advanced",
            [robots.VeryAdvancedBrain, robots.SelfAwareBrain, robots.ConsciousBrain, robots.BrainInAJarBrain]),
        robots.AdvancedAndroidSynthetic: (
            "Very Advanced",
            [robots.VeryAdvancedBrain, robots.SelfAwareBrain, robots.ConsciousBrain, robots.BrainInAJarBrain]),
        robots.SuperiorAndroidSynthetic: (
            "Self-Aware",
            [robots.SelfAwareBrain, robots.ConsciousBrain, robots.BrainInAJarBrain]),
        robots.BasicBioRobotSynthetic: (
            "Basic (x) or Hunter/Killer",
            [robots.BasicBrain, robots.HunterKillerBrain, robots.SkilledRobotBrain, robots.BrainInAJarBrain]), 
        robots.ImprovedBioRobotSynthetic: (
            "Advanced",
            [robots.AdvancedBrain,  robots.VeryAdvancedBrain, robots.SelfAwareBrain, robots.ConsciousBrain, robots.BrainInAJarBrain]),
        robots.EnhancedBioRobotSynthetic: (
            "Very Advanced",
            [robots.VeryAdvancedBrain, robots.SelfAwareBrain, robots.ConsciousBrain, robots.BrainInAJarBrain]),
        robots.AdvancedBioRobotSynthetic: (
            "Self-Aware",
            [robots.SelfAwareBrain, robots.ConsciousBrain, robots.BrainInAJarBrain]),
    }
    _SyntheticMinBrainNote = 'WARNING: The robot requires a {brain} brain or better to be lifelike enough that it doesn\'t trigger the uncanny valley effect during social interactions. Without it, the robot suffers DM-2 in all such interactions. (p86/88)'

    _InoperableNote = 'When a robot\'s Hits reach 0, it\'s inoperable and cannot be easily repaired. If the robot sustains {doubleHits} cumulative damage, the robot is destroyed and can\'t be repaired. (p13)'
    _DefaultMaintenanceNote = 'The robot requires maintenance once a year and malfunction checks must be made every month if it\'s not followed. (p108)'
    
    _AutopilotNote = 'The DM for the robot\'s Autopilot rating and its vehicle skills don\'t stack, the higher of the two values should be used. (p49)'

    _CombatManipulatorCharacteristicsNote = 'Attacks rolls for weapons mounted to or held by a manipulator receive the STR/DEX characteristic DM for the manipulator in the same way as players receive a STR/DEX characteristic DM. (clarified by Geir Lanesskog, Robot Handbook author)'
    _CombatNonManipulatorCharacteristicsNote = 'Attack rolls for weapons not mounted to or held by a manipulator do not receive a STR/DEX characteristic DM. (clarified by Geir Lanesskog, Robot Handbook author)'
    _CombatManipulatorUndersizedNote = 'Manipulators of Size {sizes} are too small to hold weapons and use them effectively. Attacks rolls do not get the manipulators DEX or STR bonus. (p61)'
    _CombatManipulatorWeaponSizeNote = 'Manipulators of Size {sizes} can hold and effectively use {examples}. If weapons larger than this are being held, attack rolls do not get the manipulators STR or DEX bonus. (p61)'
    _CombatWeaponSizeExamples = {
        traveller.WeaponSize.Small: 'melee weapon useable with one hand, any pistol or equivalent single-handed ranged weapon, or an explosive charge or grenade of less than three kilograms',
        traveller.WeaponSize.Medium: 'any larger weapon usable by Melee or Gun Combat skills or an explosive of up to six kilograms',
        traveller.WeaponSize.Heavy: 'any weapon usable with Heavy Weapons (portable)'
    }

    _ManipulatorAthleticsNote = 'When using manipulators with {characteristic} {characteristicLevel}, they give the robot {skill} {skillLevel}, but it doesn\'t get a DM+{skillLevel} for the {characteristic} characteristic when making {skill} checks (p26). This {skill} {skillLevel} stacks with any additional levels from software skill packages and other hardware. (clarified by Geir Lanesskog, Robot Handbook author)'

    _VacuumOperationWithEnduranceNote = 'When operating in a vacuum, the robot\'s Endurance is halved to {halfEndurance} hour(s) and it must make a Malfunction check every {interval} hour(s). Malfunction checks are made at DM-2 if operating in temperatures below -100°C or over 100°C. (p34 & p108)'
    _VacuumOperationNoEnduranceNote = 'When operating in a vacuum, the robot must make a Malfunction check every {interval} hour(s). Malfunction checks are made at DM-2 if operating in temperatures below -100°C or over 100°C. (p34 & p108)'
    _VacuumOperationBiologicalNote = 'When operating in a vacuum, the robot suffers all the same effects as the species it\'s designed to imitate. (p34)'
    _VacuumProtectionComponents = [
        robots.VacuumEnvironmentProtectionDefaultSuiteOption,
        robots.VacuumEnvironmentProtectionSlotOption
    ]
    _VacuumIncreaseComponents = [
        robots.HostileEnvironmentProtectionDefaultSuiteOption,
        robots.HostileEnvironmentProtectionSlotOption
    ]
 
    _SkilledSensorNote = 'WARNING: The robot doesn\'t have the Electronics (Sensors) 0 skill required to operate its {component}'

    def componentString(self) -> str:
        return 'Finalisation'

    def typeString(self) -> str:
        return 'Finalisation'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return True

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        self._createProtectionStep(sequence=sequence, context=context)
        self._createTraitNoteSteps(sequence=sequence, context=context)
        self._createCombatStep(sequence=sequence, context=context)
        self._vacuumOperationStep(sequence=sequence, context=context)
        self._createInoperableStep(sequence=sequence, context=context)
        self._createMaintenanceStep(sequence=sequence, context=context)
        self._createAutopilotStep(sequence=sequence, context=context)
        self._createManipulatorAthleticsStep(sequence=sequence, context=context)

        # These are intentionally left to last to hopefully make them more
        # obvious.
        self._createSlotUsageStep(sequence=sequence, context=context)
        self._createBandwidthUsageStep(sequence=sequence, context=context)
        self._createSynthBrainStep(sequence=sequence, context=context)
        self._createSkilledSensorsSteps(sequence=sequence, context=context)

    def _createProtectionStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        protection = context.attributeValue(
            attributeId=robots.RobotAttributeId.Protection,
            sequence=sequence)
        if not protection:
            return # Nothing to do
        
        armour = common.Calculator.equals(
            value=protection,
            name='Armour Trait Value')
        
        step = robots.RobotStep(
            name=f'Protection ({protection.value()})',
            type='Trait')
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Armour,
            value=armour))
        context.applyStep(
            sequence=sequence,
            step=step)

    def _createTraitNoteSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        for trait in robots.TraitAttributeIds:
            if trait in robots.InternalAttributeIds:
                continue
            if not context.hasAttribute(sequence=sequence, attributeId=trait):
                continue

            name = trait.value
            notes = []
            if trait == robots.RobotAttributeId.ACV:
                notes.append('The robot can travel over solid and liquid surfaces. (p17)')
                notes.append('The robot can only hover up to a few meters above the surface. (p17)')
                notes.append('The robot need a minimum of a thin atmosphere to hover. (p17)')
            elif trait == robots.RobotAttributeId.Alarm:
                pass
            elif trait == robots.RobotAttributeId.Amphibious:
                # NOTE: I've not added anything for this as can't find anything
                # that adds it. If I do add something it's not straight forward
                # as the exact wording of the note should probably vary depending
                # on if the robot can operate while submerged or if it's just
                # on land and on top of water. I'm also not sure if it's just
                # water or liquid. The Submersible Environment Protection
                # description (p42) says Hostile Environment Protection can also
                # allow the robot to operate while submerged.
                pass
            elif trait == robots.RobotAttributeId.ATV:
                notes.append('DM+2 to checks made to negotiate rough terrain. (p17)')
            elif trait == robots.RobotAttributeId.Hardened:
                notes.append('The robot\'s brain is immune to ion weapons. (p8)')
                notes.append('Radiation damage inflicted on the robot is halved. (p8 & p106)')
                notes.append('The effects of critical hits against the robot\'s brain are negated. (p106)')
            elif trait == robots.RobotAttributeId.HeightenedSenses:
                notes.append('DM+1 to Recon and Survival Checks. (p8)')
            elif trait == robots.RobotAttributeId.Invisible:
                notes.append('DM-4 to checks to see the robot. This applies across the electromagnetic spectrum. (p8)')
            elif trait == robots.RobotAttributeId.IrVision:
                notes.append('The robot can see heat sources without the need for visible light. (p8)')
            elif trait == robots.RobotAttributeId.IrUvVision:
                notes.append('The robot can see clearly without the need for visible light. At the Referee\'s discretion, it may also be able see electromagnetic emissions from equipment. (p8)')
            elif trait == robots.RobotAttributeId.Seafarer:
                pass
            elif trait == robots.RobotAttributeId.Large:
                value = context.attributeValue(
                    attributeId=trait,
                    sequence=sequence)
                assert(isinstance(value, common.ScalarCalculation))
                name = f'{trait.value} ({common.formatNumber(value.value(), alwaysIncludeSign=True)})'
                notes.append(f'Attackers receive DM+{value.value()} when making ranged attacks against the robot. (p8)')
            elif trait == robots.RobotAttributeId.Small:
                value = context.attributeValue(
                    attributeId=trait,
                    sequence=sequence)
                assert(isinstance(value, common.ScalarCalculation))
                name = f'{trait.value} ({common.formatNumber(value.value(), alwaysIncludeSign=True)})'
                notes.append(f'Attackers receive DM{value.value()} when making ranged attacks against the robot. (p8)')
            elif trait == robots.RobotAttributeId.Stealth:
                value = context.attributeValue(
                    attributeId=trait,
                    sequence=sequence)
                assert(isinstance(value, common.ScalarCalculation))
                name = f'{trait.value} ({common.formatNumber(value.value(), alwaysIncludeSign=True)})'
                notes.append(f'DM+{value.value()} to checks made to evade electronic sensors such as radar or lidar. (p8)')
                notes.append(f'Electronic (Sensors) checks to detect the robot suffer a negative DM equal to the difference between the robot\'s TL of ({context.techLevel()} and the TL of the equipment. (p8)')
            elif trait == robots.RobotAttributeId.Thruster:
                value = context.attributeValue(
                    attributeId=trait,
                    sequence=sequence)
                assert(isinstance(value, common.ScalarCalculation))
                name = f'{trait.value} ({common.formatNumber(value.value(), alwaysIncludeSign=True)})'
                notes.append(f'The robot\'s thrusters can provide {value.value()}G of thrust. (p17)')
            elif trait == robots.RobotAttributeId.Flyer:
                value = context.attributeValue(
                    attributeId=trait,
                    sequence=sequence)
                assert(isinstance(value, enum.Enum))
                name = f'{trait.value} ({value.value})'

                needsAtmosphere = False
                for locomotion in Finalisation._AtmosphereFlyerLocomotions:
                    if context.hasComponent(
                        componentType=locomotion,
                        sequence=sequence):
                        needsAtmosphere = True
                        break
                if needsAtmosphere:
                    notes.append(f'Aeroplane or VTOL Flyer robots need a minimum of a thin atmosphere to fly. (p17)')    
            
                needsGrav = False
                for locomotion in Finalisation._GraveFlyerLocomotions:
                    if context.hasComponent(
                        componentType=locomotion,
                        sequence=sequence):
                        needsGrav = True
                        break
                if needsGrav:
                    notes.append(f'Grav Flyer robots require at a gravitational field to operate. (p17)')    

            if notes:
                step = robots.RobotStep(
                    name=name,
                    type='Trait',
                    notes=notes)
                context.applyStep(
                    sequence=sequence,
                    step=step)

    def _createInoperableStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        hits = context.attributeValue(
            attributeId=robots.RobotAttributeId.Hits,
            sequence=sequence)
        if not hits:
            return # Nothing to do
        assert(isinstance(hits, common.ScalarCalculation))

        step = robots.RobotStep(
            name='Damage',
            type='Resilience')
        step.addNote(note=Finalisation._InoperableNote.format(
            doubleHits=hits.value() * 2))
        context.applyStep(
            sequence=sequence,
            step=step)                      

    def _createMaintenanceStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        for component in Finalisation._ImprovedMaintenanceOptions:
            if context.hasComponent(
                componentType=component,
                sequence=sequence):
                # Nothing to do, the note only applies if the robot doesn't have
                # improved maintenance
                return

        step = robots.RobotStep(
            name='Maintenance',
            type='Resilience',
            notes=[Finalisation._DefaultMaintenanceNote])
        context.applyStep(
            sequence=sequence,
            step=step)
        
    def _createAutopilotStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        autopilot = context.hasAttribute(
            attributeId=robots.RobotAttributeId.Autopilot,
            sequence=sequence)
        if not autopilot:
            return
        
        hasVehicleSkill = False
        for skill in Finalisation._AutopilotVehicleSkills:
            if context.hasSkill(skillDef=skill, sequence=sequence):
                hasVehicleSkill = True
                break

        if not hasVehicleSkill:
            return
            
        step = robots.RobotStep(
            name='Autopilot',
            type='Skills',
            notes=[Finalisation._AutopilotNote])
        context.applyStep(
            sequence=sequence,
            step=step)
        
    # NOTE: This covers the Manipulator Athletics Skill Requirements (p26)
    # NOTE: The Athletics levels given by the manipulators stacks with software
    # Athletics skills. This was clarified by Geir.
    # https://forum.mongoosepublishing.com/threads/robot-handbook-rule-clarifications.124669/
    def _createManipulatorAthleticsStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        athletics = context.skill(
            skillDef=traveller.AthleticsSkillDefinition,
            sequence=sequence)
        if not athletics:
            # These rules only apply if the robot has the Athletics skill (the
            # level doesn't mater)
            return

        manipulators = context.findComponents(
            componentType=robots.Manipulator,
            sequence=sequence)
        dexterityModifierMap = {}
        strengthModifierMap = {}
        for manipulator in manipulators:
            assert(isinstance(manipulator, robots.Manipulator))
            if isinstance(manipulator, robots.RemoveBaseManipulator):
                continue
            
            dexterity = manipulator.dexterity()
            dexterityModifier = traveller.characteristicDM(level=dexterity)
            if dexterityModifier > 0:
                dexterityModifierMap[dexterity] = dexterityModifier

            strength = manipulator.strength()
            strengthModifier = traveller.characteristicDM(level=strength)
            if strengthModifier > 0:
                strengthModifierMap[strength] = strengthModifier

        for dexterity, modifier in dexterityModifierMap.items():
            skill = f'{traveller.AthleticsSkillDefinition.name()} ({traveller.AthleticsSkillSpecialities.Dexterity.value})'
            step = robots.RobotStep(
                name=skill,
                type='Skills')            
            step.addNote(Finalisation._ManipulatorAthleticsNote.format(
                characteristic='DEX',
                characteristicLevel=dexterity,
                skill=skill,
                skillLevel=modifier))
            context.applyStep(
                sequence=sequence,
                step=step)
            
        for strength, modifier in strengthModifierMap.items():
            skill = f'{traveller.AthleticsSkillDefinition.name()} ({traveller.AthleticsSkillSpecialities.Strength.value})'
            step = robots.RobotStep(
                name=skill,
                type='Skills')
            step.addNote(Finalisation._ManipulatorAthleticsNote.format(
                characteristic='STR',
                characteristicLevel=strength,
                skill=skill,
                skillLevel=modifier))
            context.applyStep(
                sequence=sequence,
                step=step)

    def _createCombatStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        manipulators = context.findComponents(
            componentType=robots.Manipulator,
            sequence=sequence)
        allManipulatorSizes: typing.List[int] = []
        for manipulator in manipulators:
            assert(isinstance(manipulator, robots.Manipulator))
            if isinstance(manipulator, robots.RemoveBaseManipulator):
                continue
            manipulatorSize = manipulator.size()
            if manipulatorSize not in allManipulatorSizes:
                allManipulatorSizes.append(manipulatorSize)
        allManipulatorSizes.sort()

        # Cover how DEX is used in attack rolls
        hasManipulator = len(allManipulatorSizes) > 0
        hasNonManipulatorWeapon = context.hasComponent(
            componentType=robots.ServoMountedWeapon,
            sequence=sequence)
        if hasManipulator or hasNonManipulatorWeapon:
            step = robots.RobotStep(
                name='Characteristics',
                type='Combat')
            if hasManipulator:
                step.addNote(note=Finalisation._CombatManipulatorCharacteristicsNote)
            if hasNonManipulatorWeapon:
                step.addNote(note=Finalisation._CombatNonManipulatorCharacteristicsNote)
            context.applyStep(
                sequence=sequence,
                step=step)
            
        # Cover what happens if a manipulator holds a weapon that would require
        # a larger mount that the manipulator can handle
        if hasManipulator:
            step = robots.RobotStep(
                name='Weapon Size',
                type='Combat')            
            sizingMap: typing.Dict[traveller.WeaponSize, typing.Iterable[str]] = {}
            for manipulatorSize in allManipulatorSizes:
                weaponSize = _manipulatorSizeToWeaponSize(
                    manipulatorSize=manipulatorSize)
                manipulatorSizes = sizingMap.get(weaponSize)
                if not manipulatorSizes:
                    manipulatorSizes = []
                    sizingMap[weaponSize] = manipulatorSizes
                manipulatorSizes.append(str(manipulatorSize))
            for weaponSize, manipulatorSizes in sizingMap.items():
                if weaponSize:
                    step.addNote(note=Finalisation._CombatManipulatorWeaponSizeNote.format(
                        sizes=common.humanFriendlyListString(manipulatorSizes),
                        examples=Finalisation._CombatWeaponSizeExamples[weaponSize]))
                else:
                    step.addNote(note=Finalisation._CombatManipulatorUndersizedNote.format(
                        sizes=common.humanFriendlyListString(manipulatorSizes)))
            context.applyStep(
                sequence=sequence,
                step=step)

    def _vacuumOperationStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        for componentType in Finalisation._VacuumProtectionComponents:
            if context.hasComponent(
                componentType=componentType,
                sequence=sequence):
                return
            
        if context.hasComponent(componentType=robots.BioRobotSynthetic):
            note = Finalisation._VacuumOperationBiologicalNote
        else:
            malfunctionInterval = 1
            for componentType in Finalisation._VacuumIncreaseComponents:
                if context.hasComponent(
                    componentType=componentType,
                    sequence=sequence):
                    malfunctionInterval = 2
                    break

            endurance = context.attributeValue(
                attributeId=robots.RobotAttributeId.Endurance,
                sequence=sequence)
            if isinstance(endurance, common.ScalarCalculation) and endurance.value() > 0:
                note = Finalisation._VacuumOperationWithEnduranceNote.format(
                    halfEndurance=common.formatNumber(endurance.value() / 2),
                    interval=common.formatNumber(malfunctionInterval))
            else:
                note = Finalisation._VacuumOperationNoEnduranceNote.format(
                    interval=common.formatNumber(malfunctionInterval))

        step = robots.RobotStep(
            name='Vacuum',
            type='Environment')
        step.addNote(note=note)
        context.applyStep(
            sequence=sequence,
            step=step)  

    def _createSynthBrainStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        synthetic = context.findFirstComponent(
            componentType=robots.Synthetic,
            sequence=sequence)
        if not synthetic:
            return
        brain = context.findFirstComponent(
            componentType=robots.Brain,
            sequence=sequence)
        if not brain:
            return
        
        minBrain, supportedBrains = self._SyntheticMinBrainMap.get(
            type(synthetic),
            (None, None))
        isBrainSupported = False
        if supportedBrains:
            for brainType in supportedBrains:
                if isinstance(brain, brainType):
                    isBrainSupported = True
                    break
        if isBrainSupported:
            return
        
        step = robots.RobotStep(
            name='Minimum Brain',
            type=synthetic.componentString())
        step.addNote(note=Finalisation._SyntheticMinBrainNote.format(
            brain=minBrain))
        context.applyStep(
            sequence=sequence,
            step=step)         

    def _createSkilledSensorsSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        # NOTE: The rules say that Electronics (sensors) 0 is required to use these
        # sensors. This is just base Electronics so no need to check speciality
        if context.hasSkill(
            skillDef=traveller.ElectronicsSkillDefinition,
            sequence=sequence):
            return

        for componentType in Finalisation._SkilledSensorSlotOptions:
            component = context.findFirstComponent(
                componentType=componentType,
                sequence=sequence)
            if not component:
                continue

            note = Finalisation._SkilledSensorNote.format(
                component=component.componentString())
            step = robots.RobotStep(
                name=f'{component.componentString()}',
                type='Skills',
                notes=[note])
            context.applyStep(
                sequence=sequence,
                step=step)
        
    def _createSlotUsageStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        maxSlots = context.attributeValue(
            attributeId=robots.RobotAttributeId.MaxSlots,
            sequence=sequence)
        if not maxSlots:
            return # No max so nothing to do
        assert(isinstance(maxSlots, common.ScalarCalculation))
        usedSlots = context.usedSlots(sequence=sequence)
        if usedSlots.value() == maxSlots.value():
            # Nothing to do, all available slots used
            return
        
        step = robots.RobotStep(
            name='Slots',
            type='Usage')
        
        if usedSlots.value() < maxSlots.value():
            step.addFactor(factor=construction.StringFactor(
                string=f'Unused Slots = {maxSlots.value() - usedSlots.value()}'))
        else:
            step.addNote(
                note='WARNING: {used} slots have been used but the robot has a max of {max}'.format(
                    used=usedSlots.value(),
                    max=maxSlots.value()))

        context.applyStep(
            sequence=sequence,
            step=step)
        
    def _createBandwidthUsageStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        if context.hasComponent(
            componentType=robots.BrainInAJarBrain,
            sequence=sequence):
            # There is no bandwidth limitation when using a brain in a jar
            return

        maxBandwidth = context.attributeValue(
            attributeId=robots.RobotAttributeId.MaxBandwidth,
            sequence=sequence)
        if not maxBandwidth:
            return # No max so nothing to do
        assert(isinstance(maxBandwidth, common.ScalarCalculation))
        usedBandwidth = context.usedBandwidth(sequence=sequence)
        if usedBandwidth.value() == maxBandwidth.value():
            # Nothing to do, all available bandwidth used
            return
        
        step = robots.RobotStep(
            name='Bandwidth',
            type='Usage')

        if usedBandwidth.value() < maxBandwidth.value():
            step.addFactor(factor=construction.StringFactor(
                string=f'Unused Bandwidth = {maxBandwidth.value() - usedBandwidth.value()}'))
        else:
            # NOTE: The max slots can be a float as some components add/remove a
            # percentage of the slots (e.g. None locomotion adds 25%)        
            step.addNote('WARNING: {used} bandwidth has been used but the robot has a max of {max}'.format(
                used=usedBandwidth.value(),
                max=math.floor(maxBandwidth.value())))

        context.applyStep(
            sequence=sequence,
            step=step)
