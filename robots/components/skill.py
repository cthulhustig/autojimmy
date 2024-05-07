import common
import construction
import enum
import robots
import traveller
import typing


#  ███████████                     █████                                         
# ░░███░░░░░███                   ░░███                                          
#  ░███    ░███  ██████    ██████  ░███ █████  ██████    ███████  ██████   █████ 
#  ░██████████  ░░░░░███  ███░░███ ░███░░███  ░░░░░███  ███░░███ ███░░███ ███░░  
#  ░███░░░░░░    ███████ ░███ ░░░  ░██████░    ███████ ░███ ░███░███████ ░░█████ 
#  ░███         ███░░███ ░███  ███ ░███░░███  ███░░███ ░███ ░███░███░░░   ░░░░███
#  █████       ░░████████░░██████  ████ █████░░████████░░███████░░██████  ██████ 
# ░░░░░         ░░░░░░░░  ░░░░░░  ░░░░ ░░░░░  ░░░░░░░░  ░░░░░███ ░░░░░░  ░░░░░░  
#                                                      ███ ░███                 
#                                                     ░░██████                  
#                                                      ░░░░░░    

# Define custom skills for the Vehicle and Weapon skills used by some packages
RobotVehicleSkillDefinition = traveller.SkillDefinition(
    skillName='Vehicle',
    skillType=traveller.SkillDefinition.SkillType.Simple)

RobotWeaponSkillDefinition = traveller.SkillDefinition(
    skillName='Weapon',
    skillType=traveller.SkillDefinition.SkillType.Simple) 

class SkillPackage(robots.SkillPackageInterface):
    def __init__(
            self,
            componentName: str,
            minTL: int,
            brainType: typing.Type[robots.Brain],
            bandwidth: int,
            skills: typing.Optional[typing.Iterable[typing.Tuple[
                traveller.SkillDefinition, # Skill
                typing.Optional[typing.Union[enum.Enum, str]], # Speciality
                int # Level
            ]]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__()

        self._componentName = componentName
        self._minTL = common.ScalarCalculation(
            value=minTL,
            name=f'{self._componentName} {self.typeString()} Minimum TL')
        self._brainType = brainType 
        self._bandwidth = common.ScalarCalculation(
            value=bandwidth,
            name=f'{self._componentName} {self.typeString()} Required Bandwidth')
        self._notes = notes        
        
        self._skills: typing.List[typing.Tuple[
            traveller.SkillDefinition,
            typing.Optional[typing.Union[enum.Enum, str]],
            common.ScalarCalculation]] = []
        if skills:
            for skillDef, speciality, level in skills:
                assert(isinstance(skillDef, traveller.SkillDefinition))
                skillName = skillDef.name()
                if isinstance(speciality, enum.Enum):
                    skillName += f' {speciality.value}'
                elif isinstance(speciality, str):
                    skillName += f' {speciality}'
                level = common.ScalarCalculation(
                    value=level,
                    name=f'{self._componentName} {self.typeString()} {skillName} Skill Level')
                self._skills.append((skillDef, speciality, level))

    def componentString(self) -> str:
        return self._componentName

    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        if context.techLevel() < self._minTL.value():
            return False
        
        return context.hasComponent(
            componentType=self._brainType,
            sequence=sequence)

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
        context.applyStep(
            sequence=sequence,
            step=self._createStep(sequence=sequence, context=context))

    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        if self._bandwidth.value() > 0:
            step.setBandwidth(
                bandwidth=construction.ConstantModifier(value=self._bandwidth))
            
        for skillDef, speciality, level in self._skills:
            step.addFactor(factor=construction.SetSkillFactor(
                skillDef=skillDef,
                speciality=speciality,
                level=level))
            
        if self._notes:
            for note in self._notes:
                step.addNote(note)
        
        return step
    
class PrimitiveSkillPackage(SkillPackage):
    """
    - Min TL: 7
    - Bandwidth: 0
    - Note: Primitive brain package counteracts any negative DMs associated with
      the computer's DEX or INT characteristics.
    - Requirement: Only compatible with primitive brain
    """

    _PrimitiveNote = 'The package counteracts any potential negative DMs associated with the computer\'s DEX or INT characteristics'

    def __init__(
            self,
            componentName: str,
            skills: typing.Optional[typing.Iterable[typing.Tuple[
                traveller.SkillDefinition, # Skill
                typing.Optional[typing.Union[enum.Enum, str]], # Speciality
                int # Level
            ]]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__(
            componentName=componentName,
            minTL=7,
            brainType=robots.PrimitiveBrain,
            bandwidth=0,
            skills=skills,
            notes=notes + [PrimitiveSkillPackage._PrimitiveNote] if notes else [PrimitiveSkillPackage._PrimitiveNote])
        
    def typeString(self) -> str:
        return 'Primitive Skill Package'

class AlertPrimitiveSkillPackage(PrimitiveSkillPackage):
    """
    - Trait: Alarm
    - Skill: Recon 0
    """    
    def __init__(self) -> None:
        super().__init__(
            componentName='Alert',
            skills=[(traveller.ReconSkillDefinition, None, 0)])

    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Alarm))
        
        return step

class CleanPrimitiveSkillPackage(PrimitiveSkillPackage):
    """
    - Skill: Profession (domestic cleaner) 2
    """
    def __init__(self) -> None:
        super().__init__(
            componentName='Clean',
            skills=[(traveller.ProfessionSkillDefinition, 'Domestic Cleaner', 2)])

class EvadePrimitiveSkillPackage(PrimitiveSkillPackage):
    """
    - Skill: Athletics (dexterity) 1
    - Skill: Stealth 2       
    """
    def __init__(self) -> None:
        super().__init__(
            componentName='Evade',
            skills=[(traveller.AthleticsSkillDefinition, traveller.AthleticsSkillSpecialities.Dexterity, 1),
                    (traveller.StealthSkillDefinition, None, 2)])

class HomingPrimitiveSkillPackage(PrimitiveSkillPackage):
    """
    - Skill: Weapon 1
    - Option: Need something to select which Weapon skill this gives
    """
    _WeaponSkillLevel = common.ScalarCalculation(
        value=1,
        name='Primitive Homing Package Weapon Skill Level')

    def __init__(self) -> None:
        super().__init__(
            componentName='Homing',
            skills=[(RobotWeaponSkillDefinition, None, 1)])

class BasicSkillPackage(SkillPackage):
    """
    - Min TL: 8
    - Bandwidth: 1
    - Requirement: Only compatible with basic brain   
    """

    def __init__(
            self,
            componentName: str,
            skills: typing.Optional[typing.Iterable[typing.Tuple[
                traveller.SkillDefinition, # Skill
                typing.Optional[typing.Union[enum.Enum, str]], # Speciality
                int # Level
            ]]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__(
            componentName=componentName,
            minTL=8,
            brainType=robots.BasicBrain,
            bandwidth=1,
            skills=skills,
            notes=notes)
        
    def typeString(self) -> str:
        return 'Basic Skill Package'
    
# NOTE: None is the first basic skill package listed as it should appear
# before other 'real' options when listed by enumeration
class NoneBasicSkillPackage(BasicSkillPackage):
    """
    - Note: Skill packages installed in the brain are subject to limitations and negative modifiers
    """

    def __init__(self) -> None:
        super().__init__(
            componentName='None',
            notes=['When skill packages are installed in the brain they are subject to the robot\'s INT modifier'])    
        
class PreInstalledBasicSkillPackage(BasicSkillPackage):
    """
    - Note: Negative modifiers due to the robot\'s INT characteristic do no
    apply when making checks using skills provided by the package. (p70)
    """

    _BasicNote = 'Negative modifiers due to the robot\'s INT characteristic do no apply when making checks using skills provided by the package. (p70)'    

    def __init__(
            self,
            componentName: str,
            skills: typing.Optional[typing.Iterable[typing.Tuple[
                traveller.SkillDefinition, # Skill
                typing.Optional[typing.Union[enum.Enum, str]], # Speciality
                int # Level
            ]]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__(
            componentName=componentName,
            skills=skills,
            notes=notes + [PreInstalledBasicSkillPackage._BasicNote] if notes else [PreInstalledBasicSkillPackage._BasicNote])  

class LaboureurBasicSkillPackage(PreInstalledBasicSkillPackage):
    """
    - Skill: Profession (laboureur) 2
    """
    def __init__(self) -> None:
        super().__init__(
            componentName='Laboureur',
            skills=[(traveller.ProfessionSkillDefinition, 'Laboureur', 2)])
        
class LocomotionBasicSkillPackage(PreInstalledBasicSkillPackage):
    """
    - Skill: Vehicle skill equal to the robots Agility Enhancement Level (or
      0 if no enhancement)
    - Note: Athletics (dexterity) equal to the robots Agility Enhancement Level
    for purposes of hazardous manoeuvring and reactions such as dodging
    - Note: If the robot also has an Autopilot score, the modifiers for the
    Autopilot and Vehicle Skill don't stack (p49)
    - Requirement: Requires some form of locomotion
    """
    # NOTE: The note about Autopilot and vehicle skills not stacking is handled
    # by a note added in finalisation

    _DefaultAgilityModifier = common.ScalarCalculation(
        value=0,
        name='Default Agility Enhancement')

    _AthleticsNote = 'The robot has Athletics (dexterity) {agility} for purposes of hazardous manoeuvring and reactions such as dodging.'

    def __init__(self) -> None:
        super().__init__(componentName='Locomotion')

    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        
        locomotions = context.findComponents(
            componentType=robots.LocomotionInterface,
            sequence=sequence)
        hasCompatibleLocomotion = False
        for locomotion in locomotions:
            if not isinstance(locomotion, robots.NoPrimaryLocomotion):
                hasCompatibleLocomotion = True
                break
        return hasCompatibleLocomotion

    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = super()._createStep(sequence=sequence, context=context)

        agilityEnhancement = context.findFirstComponent(
            componentType=robots.AgilityEnhancement,
            sequence=sequence)
        if agilityEnhancement:
            assert(isinstance(agilityEnhancement, robots.AgilityEnhancement))
            agilityModifier = common.ScalarCalculation(
                value=agilityEnhancement.agilityModifier(),
                name='Agility Enhancement Modifier')
        else:
            agilityModifier = LocomotionBasicSkillPackage._DefaultAgilityModifier

        step.addFactor(factor=construction.SetSkillFactor(
            skillDef=RobotVehicleSkillDefinition,
            level=agilityModifier))

        if agilityModifier.value() != 0:
            step.addNote(note=LocomotionBasicSkillPackage._AthleticsNote.format(
                agility=agilityModifier.value()))

        return step

class ReconBasicSkillPackage(PreInstalledBasicSkillPackage):
    """
    - Skill: Recon 2
    """
    def __init__(self) -> None:
        super().__init__(
            componentName='Recon',
            skills=[(traveller.ReconSkillDefinition, None, 2)])
        
class SecurityBasicSkillPackage(PreInstalledBasicSkillPackage):
    """
    - Skill: Weapon 1
    - Skill: Tactics (military) 1
    - Option: Need something to select which Weapon skill this gives
    """
    _WeaponSkillLevel = common.ScalarCalculation(
        value=1,
        name='Primitive Homing Package Weapon Skill Level')
    _TacticsSkillLevel = common.ScalarCalculation(
        value=1,
        name='Primitive Homing Package Tactics (Military) Skill Level')    

    def __init__(self) -> None:
        super().__init__(
            componentName='Security',
            skills=[(RobotWeaponSkillDefinition, None, 1),
                    (traveller.TacticsSkillDefinition, traveller.TacticsSkillSpecialities.Military, 1)])

class ServantBasicSkillPackage(PreInstalledBasicSkillPackage):
    """
    - Skill: Profession (domestic servant or domestic cleaner) 2
    - Option: Need an option to select which Profession speciality this gives
    """
    class _Professions(enum.Enum):
        DomesticServant = 'Domestic Servant'
        DomesticCleaner = 'Domestic Cleaner'

    _ProfessionSkillLevel = common.ScalarCalculation(
        value=2,
        name='Servant Profession Skill Level')        

    def __init__(self) -> None:
        super().__init__(componentName='Servant')

        self._professionSkillOption = construction.EnumOption(
            id='Profession',
            name='Profession',
            type=ServantBasicSkillPackage._Professions,
            description='Specify the Profession speciality given by the skill package')
        
    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._professionSkillOption)
        return options

    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = super()._createStep(sequence=sequence, context=context)

        profession = self._professionSkillOption.value()
        assert(isinstance(profession, ServantBasicSkillPackage._Professions))

        step.addFactor(factor=construction.SetSkillFactor(
            skillDef=traveller.ProfessionSkillDefinition,
            speciality=profession.value,
            level=ServantBasicSkillPackage._ProfessionSkillLevel))  

        return step

class ServiceBasicSkillPackage(PreInstalledBasicSkillPackage):
    """
    - Skill: Mechanic 0
    - Skill: Steward 0
    - Note: Can support up to 8 Middle or 100 Basic passengers
    """
    def __init__(self) -> None:
        super().__init__(
            componentName='Service',
            skills=[(traveller.MechanicSkillDefinition, None, 0),
                    (traveller.StewardSkillDefinition, None, 0)],
            notes=['Can support up to 8 Middle or 100 Basic passengers'])

class TargetBasicSkillPackage(PreInstalledBasicSkillPackage):
    """
    - Skill: Explosives 1 or Weapon 1
    - Skill: Explosives 0 if Weapon is taken as the primary skill and the robot
    has a Self Destruct System Slot Option
    """
    class _CombatSkills(enum.Enum):
        Explosives = 'Explosives',
        Weapon = 'Weapon'

    _CombatSkillLevel = common.ScalarCalculation(
        value=1,
        name='Target Basic Skill Package Combat Skill Level')
    
    _SelfDestructExplosivesSkillLevel = common.ScalarCalculation(
        value=0,
        name='Target Basic Skill Package Self Destruct Explosives Skill')

    def __init__(self) -> None:
        super().__init__(componentName='Target')

        self._combatSkillOption = construction.EnumOption(
            id='CombatSkill',
            name='Combat Skill',
            type=TargetBasicSkillPackage._CombatSkills,
            description='Specify the combat skill granted by the Target Basic Skill Package')
        
    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._combatSkillOption)
        return options
    
    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = super()._createStep(sequence=sequence, context=context)

        combatSkill = self._combatSkillOption.value()
        assert(isinstance(combatSkill, TargetBasicSkillPackage._CombatSkills))

        if combatSkill == TargetBasicSkillPackage._CombatSkills.Explosives:
            step.addFactor(factor=construction.SetSkillFactor(
                skillDef=traveller.ExplosivesSkillDefinition,
                level=TargetBasicSkillPackage._CombatSkillLevel))
        elif combatSkill == TargetBasicSkillPackage._CombatSkills.Weapon:
            step.addFactor(factor=construction.SetSkillFactor(
                skillDef=RobotWeaponSkillDefinition,
                level=TargetBasicSkillPackage._CombatSkillLevel))
            
            if context.hasComponent(
                componentType=robots.SelfDestructSystemSlotOption,
                sequence=sequence):
                step.addFactor(factor=construction.SetSkillFactor(
                    skillDef=traveller.ExplosivesSkillDefinition,
                    level=TargetBasicSkillPackage._SelfDestructExplosivesSkillLevel))

        return step

class HunterKillerSkillPackage(SkillPackage):
    """
    - Min TL: 8
    - Bandwidth: 1
    """
    # NOTE: The rules don't explicitly state the minimum TL for a hunter/killer
    # brain. I've gone with 8 as that is the min TL for the associated brain.
    # This seems logical as there is no point in having the brain without the
    # skill package and vice versa. It's also consistent with the other skill
    # packages where the stated min TL matches the min TL for the brain it goes
    # with
    # NOTE: The rules don't state the bandwidth used by a hunter/killer package.
    # I've gone with 1 as it's the same as the basic brain packages, the brain
    # only has 1 bandwidth so it can't be more than that without forcing a
    # bandwidth upgrade but that would be weird to be forced to upgrade the base
    # brain to use a skill package, it also doesn't really make sense that it
    # would be less than the bandwidth of the basic brain package

    def __init__(
            self,
            componentName: str,
            skills: typing.Optional[typing.Iterable[typing.Tuple[
                traveller.SkillDefinition, # Skill
                typing.Optional[typing.Union[enum.Enum, str]], # Speciality
                int # Level
            ]]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__(
            componentName=componentName,
            minTL=8,
            brainType=robots.HunterKillerBrain,
            bandwidth=1,
            skills=skills,
            notes=notes)
        
    def typeString(self) -> str:
        return 'Hunter/Killer Skill Package'
    
class StandardHunterKillerSkillPackage(HunterKillerSkillPackage):
    """
    - Skill: Gun Combat 0
    - Skill: Melee 0
    - Skill: Recon 0    
    """
    def __init__(self) -> None:
        super().__init__(
            componentName='Standard',
            skills=[(traveller.GunCombatSkillDefinition, None, 0),
                    (traveller.MeleeSkillDefinition, None, 0),
                    (traveller.ReconSkillDefinition, None, 0)])
        
class TacticalHunterKillerSkillPackage(HunterKillerSkillPackage):
    """
    - Cost: Cr10000
    - Skill: Gun Combat 0
    - Skill: Melee 0
    - Skill: Recon 0        
    - Skill: Tactics (military) 2
    - Note: The Tactics (military) skill is not subject to the INT limitations
    of the robot's brain (e.g. negative DMs)    
    """
    _TacticsCost = common.ScalarCalculation(
        value=10000,
        name='Tactics Hunter/Killer Skill Package Cost')
    _TacticsNote = 'The rules say "This tactical skill is not subject to the INT limitations of the robot’s brain" (p73), this most likely means it doesn\'t suffer the DM-1 it normally would when using the skill due to the Hunter/Killer Brain having an INT of 3/4'

    def __init__(self) -> None:
        super().__init__(
            componentName='Tactical',
            skills=[(traveller.GunCombatSkillDefinition, None, 0),
                    (traveller.MeleeSkillDefinition, None, 0),
                    (traveller.ReconSkillDefinition, None, 0),
                    (traveller.TacticsSkillDefinition, traveller.TacticsSkillSpecialities.Military, 2)],
            notes=[TacticalHunterKillerSkillPackage._TacticsNote])

    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.setCredits(credits=construction.ConstantModifier(
            value=TacticalHunterKillerSkillPackage._TacticsCost))

        return step



#   █████████  █████       ███  ████  ████         
#  ███░░░░░███░░███       ░░░  ░░███ ░░███         
# ░███    ░░░  ░███ █████ ████  ░███  ░███   █████ 
# ░░█████████  ░███░░███ ░░███  ░███  ░███  ███░░  
#  ░░░░░░░░███ ░██████░   ░███  ░███  ░███ ░░█████ 
#  ███    ░███ ░███░░███  ░███  ░███  ░███  ░░░░███
# ░░█████████  ████ █████ █████ █████ █████ ██████ 
#  ░░░░░░░░░  ░░░░ ░░░░░ ░░░░░ ░░░░░ ░░░░░ ░░░░░░  

_PerLevelCostMultiplier = common.ScalarCalculation(
    value=10,
    name='Per Additional Level Cost Multiplier')
_RobotBrainMaxPossibleLevel = common.ScalarCalculation(
    value=3,
    name='Robot Brain Max Possible Skill Level')

def _calculateSkillCost(
        levelZeroCost: common.ScalarCalculation,
        skillLevel: common.ScalarCalculation
        ) -> common.ScalarCalculation:
    cost = levelZeroCost
    if skillLevel.value():
        for index in range(skillLevel.value()):
            cost = common.Calculator.multiply(
                lhs=cost,
                rhs=_PerLevelCostMultiplier,
                name=f'Level {index + 1} Cost')
    return cost

"""
- Requirement: The absolute max skill level for a robot is 3 (p73)
- Requirement: Each increase in skill level after 0 requires an additional TL
before it becomes available (p73)
- Requirement: A robot can't have a skill that requires more bandwidth than its
Inherent Bandwidth (p67)
"""
# NOTE: This assumes that the robot at least meets the TL and bandwidth
# requirements for the skill at level 0. This should be enforced by the skill
# components
def _calculateMaxSkillLevel(
        introTL: common.ScalarCalculation,
        robotTL: common.ScalarCalculation,
        levelZeroBandwidth: common.ScalarCalculation,
        inherentBandwidth: common.ScalarCalculation
        ) -> common.ScalarCalculation:
    maxByTL = common.Calculator.subtract(
        lhs=robotTL,
        rhs=introTL,
        name='Max Skill Level Allowed By TL')
    maxByBandwidth = common.Calculator.subtract(
        lhs=inherentBandwidth,
        rhs=levelZeroBandwidth,
        name='Max Skill Level Allowed By Inherent Bandwidth')
    return common.Calculator.min(
        lhs=common.Calculator.min(
            lhs=maxByTL,
            rhs=maxByBandwidth),
        rhs=_RobotBrainMaxPossibleLevel,
        name='Max Skill Level')

class Skill(robots.SkillInterface):
    """
    - Cost: Level 0 cost is multiplied by 10 for each additional level after 0
    = Option: Level
        - Range: 0-3
        - Requirement: 
    - Requirement: A robot can have a number of bandwidth 0 skills equal to
    its Inherent Bandwidth, after that they require 1 bandwidth at level 0 (p73)
    """
    # NOTE: When it comes to the rules about robots only being able to have
    # a number of zero bandwidth skills equal to their Inerrant Bandwidth it's
    # not explicit about if zero bandwidth skills that have their level
    # increased count towards the count of zero bandwidth skills installed.
    # The only clue I've found so far are from the example StarTek robots
    # brain (p68) and skills (p75). The description for the brain says the robot
    # can have 5 zero bandwidth skills and its list of skills shows it has 4
    # skills with bandwidth 0 and it says there is 1 spare zero bandwidth skill.
    # This means the fact the robots Mechanic 1 skill has not been counted
    # towards the number of zero bandwidth skills the robot has.    

    # This max count needs to be large enough to cover any legitimate user
    # requirement but also prevent the user for causing problems by specifying
    # a silly number and causing a large number of UI widgets to be created
    _CustomSpecialityMaxCount = 20

    _SpecialitySkillMaxBaseLevel = common.ScalarCalculation(
        value=0,
        name='Speciality Skill Max Base Level')

    _ZeroBandwidthSkillOverride = common.ScalarCalculation(
        value=1,
        name='Zero Bandwidth Skill Inherent Bandwidth Requirement')
    
    _ZeroBandwidthSkillCountIncrement = common.ScalarCalculation(
        value=1,
        name='Zero BandwidthSkill Count Increment')

    def __init__(
            self,
            skillDef: traveller.SkillDefinition,
            minTL: int,
            levelZeroBandwidth: int,
            levelZeroCost: int
            ) -> None:
        super().__init__()
        
        self._skillDef = skillDef
        self._minTL = common.ScalarCalculation(
            value=minTL,
            name=f'{self._skillDef.name()} Skill Minimum TL')        
        self._levelZeroBandwidth = common.ScalarCalculation(
            value=levelZeroBandwidth,
            name=f'{self._skillDef.name()} Level 0 Required Bandwidth')           
        self._levelZeroCost = common.ScalarCalculation(
            value=levelZeroCost,
            name=f'{self._skillDef.name()} Level 0 Cost')           
        
        self._levelOption = construction.IntegerOption(
            id='Level',
            name='Level',
            value=0,
            minValue=0,
            maxValue=_RobotBrainMaxPossibleLevel.value(),
            description='Specify the level of the skill')
        
        self._fixedSpecialityOptions = None
        if self._skillDef.isFixedSpeciality():
            self._fixedSpecialityOptions: typing.List[typing.Tuple[
                enum.Enum,
                construction.IntegerOption]] = []
            for speciality in self._skillDef.fixedSpecialities():
                assert(isinstance(speciality, enum.Enum))
                levelOption = construction.IntegerOption(
                    id=f'{speciality.name}Level',
                    name=f'{speciality.value} Level',
                    value=None,
                    minValue=0,
                    maxValue=_RobotBrainMaxPossibleLevel.value(),
                    isOptional=True,
                    description=f'Specify the level of the {speciality.value} speciality')
                self._fixedSpecialityOptions.append((speciality, levelOption))

        self._customSpecialityCountOption = None
        self._customSpecialityOptions = None
        if self._skillDef.isCustomSpeciality():
            self._customSpecialityCountOption = construction.IntegerOption(
                id='SpecialityCount',
                name='Specialities',
                value=0,
                minValue=0,
                maxValue=Skill._CustomSpecialityMaxCount,
                description='Specify the number of skill specialities.')
                        
            self._customSpecialityOptions: typing.List[typing.Tuple[
                construction.IntegerOption,
                construction.IntegerOption]] = []

    def componentString(self) -> str:
        return self._skillDef.name()
    
    def typeString(self) -> str:
        return 'Skill'        

    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        # Can only have a single instance of each skill
        if context.hasComponent(
            componentType=type(self),
            sequence=sequence):
            return False
                
        hasBrainInAJar = context.hasComponent(
            componentType=robots.BrainInAJarBrain,
            sequence=sequence)
        if hasBrainInAJar:
            # There is no TL or bandwidth restriction for Brain in a Jar
            return True        

        if context.techLevel() < self._minTL.value():
            return False

        if not context.hasComponent(
            componentType=robots.SkilledRobotBrain,
            sequence=sequence):
            return False
        
        # The bandwidth required for the skill at level 0 must be less than or
        # equal to the robots Inherent Bandwidth
        inherentBandwidth = context.attributeValue(
            attributeId=robots.RobotAttributeId.InherentBandwidth,
            sequence=sequence)
        if not inherentBandwidth:
            # NOTE: This assumes that if there is no inherent bandwidth it must
            # be a brain in a jar so the skill is compatible
            return True
        assert(isinstance(inherentBandwidth, common.ScalarCalculation))
        return self._levelZeroBandwidth.value() <= inherentBandwidth.value()
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = []
        if self._levelOption.isEnabled():
            options.append(self._levelOption)
        if self._fixedSpecialityOptions:
            for _, levelOption in self._fixedSpecialityOptions:
                if levelOption.isEnabled():
                    options.append(levelOption)
        if self._customSpecialityCountOption and \
            self._customSpecialityCountOption.isEnabled():
            options.append(self._customSpecialityCountOption)
        if self._customSpecialityOptions:
            for nameOption, levelOption in self._customSpecialityOptions:
                if nameOption.isEnabled():
                    options.append(nameOption)                
                if levelOption.isEnabled():
                    options.append(levelOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:       
        robotTL = common.ScalarCalculation(
            value=context.techLevel(),
            name='Robot TL')
        
        hasBrainInAJar = context.hasComponent(
            componentType=robots.BrainInAJarBrain,
            sequence=sequence)
        
        if hasBrainInAJar:
            maxLevel = None
            self._levelOption.setMax(maxLevel)
            self._levelOption.setEnabled(self._skillDef.isSimple())            
        else:
            inherentBandwidth = context.attributeValue(
                attributeId=robots.RobotAttributeId.InherentBandwidth,
                sequence=sequence)
            assert(isinstance(inherentBandwidth, common.ScalarCalculation))

            maxLevel = _calculateMaxSkillLevel(
                introTL=self._minTL,
                robotTL=robotTL,
                levelZeroBandwidth=self._levelZeroBandwidth,
                inherentBandwidth=inherentBandwidth)
            self._levelOption.setMax(maxLevel.value() \
                                    if self._skillDef.isSimple() else \
                                    Skill._SpecialitySkillMaxBaseLevel.value())
            self._levelOption.setEnabled(self._levelOption.max() > 0)

        if self._skillDef.isFixedSpeciality():
            for _, levelOption in self._fixedSpecialityOptions:
                levelOption.setMin(1)
                levelOption.setMax(maxLevel.value() \
                                   if maxLevel != None else \
                                    _RobotBrainMaxPossibleLevel.value())
                levelOption.setEnabled(maxLevel == None or maxLevel.value() > 0)
        elif self._skillDef.isCustomSpeciality():
            specialityCount = self._customSpecialityCountOption.value()
            while len(self._customSpecialityOptions) > specialityCount:
                self._customSpecialityOptions.pop()
            while len(self._customSpecialityOptions) < specialityCount:
                specialityIndex = len(self._customSpecialityOptions) + 1 # 1 based for user
                nameOption = construction.StringOption(
                    id=f'Speciality{specialityIndex}Name',
                    name=f'Speciality {specialityIndex} Name',
                    options=self._skillDef.customSpecialities(),
                    description='Specify the name of the speciality')
                levelOption = construction.IntegerOption(
                    id=f'Speciality{specialityIndex}Level',
                    name=f'Speciality {specialityIndex} Level',
                    value=1,
                    description=f'Specify the level of the speciality')
                self._customSpecialityOptions.append((nameOption, levelOption))

            # Level options are only enabled if the name is enabled and not empty
            for nameOption, levelOption in self._customSpecialityOptions:
                levelOption.setMin(1)
                levelOption.setMax(maxLevel.value() \
                                   if maxLevel != None else \
                                   _RobotBrainMaxPossibleLevel.value())
                levelOption.setEnabled(
                    enabled=nameOption.isEnabled() and nameOption.value())
            
    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        hasSpeciality = False
        if self._fixedSpecialityOptions:
            for _, levelOption in self._fixedSpecialityOptions:
                if not levelOption.isEnabled():
                    continue
                value = levelOption.value()
                if value != None and value > 0:
                    hasSpeciality = True
                    break
        elif self._customSpecialityOptions:
            for _, levelOption in self._customSpecialityOptions:
                if not levelOption.isEnabled():
                    continue
                value = levelOption.value()
                if value != None and value > 0:
                    hasSpeciality = True
                    break

        if not hasSpeciality:
            self._createSkillSteps(
                level=self._levelOption.value() if self._levelOption.isEnabled() else 0,
                speciality=None,
                sequence=sequence,
                context=context)
        else:
            if self._fixedSpecialityOptions:
                for speciality, levelOption in self._fixedSpecialityOptions:                
                    if not levelOption.isEnabled():
                        continue
                    value = levelOption.value()
                    if value == None or value <= 0:
                        continue

                    self._createSkillSteps(
                        level=levelOption.value(),
                        speciality=speciality,
                        sequence=sequence,
                        context=context)
                    
            if self._customSpecialityOptions:
                for nameOption, levelOption in self._customSpecialityOptions:
                    if not nameOption.isEnabled() or not nameOption.value():
                        continue
                    if not levelOption.isEnabled():
                        continue
                    value = levelOption.value()
                    if value == None or value <= 0:
                        continue

                    self._createSkillSteps(
                        level=levelOption.value(),
                        speciality=nameOption.value(),
                        sequence=sequence,
                        context=context)
        
    def _createSkillSteps(
        self,
        level: int,
        speciality: typing.Optional[typing.Union[enum.Enum, str]],
        sequence: str,
        context: robots.RobotContext,
        ) -> None:
        skillName = self._skillDef.name()
        if isinstance(speciality, enum.Enum):
            skillName += f' ({speciality.value})'
        elif isinstance(speciality, str):
            skillName += f' ({speciality})'

        level = common.ScalarCalculation(
            value=level,
            name=f'Specified {skillName} Level')
        # This is a hack to fix syntax highlighting
        assert(isinstance(level, common.ScalarCalculation))

        hasBrainInAJar = context.hasComponent(
            componentType=robots.BrainInAJarBrain,
            sequence=sequence)        

        step = robots.RobotStep(
            name=f'{skillName} {level.value()}',
            type=self.typeString())
        
        step.addFactor(factor=construction.SetSkillFactor(
            skillDef=self._skillDef,
            speciality=speciality,
            level=level))        

        if not hasBrainInAJar:
            bandwidth = self._levelZeroBandwidth
                    
            if level.value() > 0:
                bandwidth = common.Calculator.add(
                    lhs=bandwidth,
                    rhs=level,
                    name=f'{skillName} Level {level.value()} Required Bandwidth') 

            # Robot can only have a number of level 0 bandwidth skills equal to
            # their Inerrant Bandwidth. After that they require 1 bandwidth for
            # level 0.
            # NOTE: It's important that this check occurs AFTER the bandwidth is
            # increased for additional levels as skills that have had their level
            # increased shouldn't count towards the number of zero bandwidth skills
            # (see comment in class header)
            if not speciality and bandwidth.value() == 0:
                inherentBandwidth = context.attributeValue(
                    attributeId=robots.RobotAttributeId.InherentBandwidth,
                    sequence=sequence)
                assert(isinstance(inherentBandwidth, common.ScalarCalculation))

                currentCount = context.attributeValue(
                    attributeId=robots.RobotAttributeId.ZeroBandwidthSkillCount,
                    sequence=sequence)
                assert(not currentCount or isinstance(currentCount, common.ScalarCalculation))
                
                if currentCount and currentCount.value() >= inherentBandwidth.value():
                    # The robot already has the max number of zero bandwidth skills
                    # so this one requires bandwidth
                    assert(currentCount.value() == inherentBandwidth.value())
                    bandwidth = Skill._ZeroBandwidthSkillOverride
                else:
                    # Increment the zero bandwidth skill count, if this is the first
                    # the option is being set it will be set to 1
                    step.addFactor(factor=construction.ModifyAttributeFactor(
                        attributeId=robots.RobotAttributeId.ZeroBandwidthSkillCount,
                        modifier=construction.ConstantModifier(
                            value=Skill._ZeroBandwidthSkillCountIncrement)))                           

            if bandwidth.value() > 0:
                step.setBandwidth(
                    bandwidth=construction.ConstantModifier(value=bandwidth))  
            
            cost = _calculateSkillCost(
                levelZeroCost=self._levelZeroCost,
                skillLevel=level)
            step.setCredits(
                credits=construction.ConstantModifier(value=cost))

        context.applyStep(
            sequence=sequence,
            step=step) 
    
class AdminSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.AdminSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class AdvocateSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr500   
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.AdvocateSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=500)    

class AnimalsSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr200
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.AnimalsSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=200)

class ArtSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr500
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.ArtSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=500)

class AstrogationSkill(Skill):
    """
    - Min TL: 12
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.AstrogationSkillDefinition,
            minTL=12,
            levelZeroBandwidth=1,
            levelZeroCost=500)
        
class AthleticsSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: variable
    - Cost Cr100
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.AthleticsSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)

class BrokerSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.BrokerSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=200)

class CarouseSkill(Skill):
    """
    - Min TL: 11
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500  
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.CarouseSkillDefinition,
            minTL=11,
            levelZeroBandwidth=1,
            levelZeroCost=500)

class DeceptionSkill(Skill):
    """
    - Min TL: 13
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr1000 
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.DeceptionSkillDefinition,
            minTL=13,
            levelZeroBandwidth=1,
            levelZeroCost=1000)

class DiplomatSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.DiplomatSkillDefinition,
            minTL=10,
            levelZeroBandwidth=1,
            levelZeroCost=500)
  
class DriveSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100  
    - Note: If the robot also has an Autopilot score, the modifiers for the
    Autopilot and Vehicle Skill don't stack (p49)
    """    
    # NOTE: The note about Autopilot and vehicle skills not stacking is handled
    # by a note added in finalisation

    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.DriveSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class ElectronicsSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.ElectronicsSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class EngineerSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200 
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.EngineerSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=200)

class ExplosivesSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100  
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.ExplosivesSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class FlyerSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100   
    - Note: If the robot also has an Autopilot score, the modifiers for the
    Autopilot and Vehicle Skill don't stack (p49)
    """    
    # NOTE: The note about Autopilot and vehicle skills not stacking is handled
    # by a note added in finalisation
    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.FlyerSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)

class GamblerSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr500
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.GamblerSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=500)
        
class GunCombatSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.GunCombatSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class GunnerSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100   
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.GunnerSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class HeavyWeaponsSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100   
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.HeavyWeaponsSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)

class InvestigateSkill(Skill):
    """
    - Min TL: 11
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.InvestigateSkillDefinition,
            minTL=11,
            levelZeroBandwidth=1,
            levelZeroCost=500)

class LanguageSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.LanguageSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=200)  
        
class LeadershipSkill(Skill):
    """
    - Min TL: 13
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr1000 
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.LeadershipSkillDefinition,
            minTL=13,
            levelZeroBandwidth=1,
            levelZeroCost=1000)
        
class MechanicSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.MechanicSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)

class MedicSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200  
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.MedicSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=200)
        
class MeleeSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.MeleeSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=100)        

class NavigationSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.NavigationSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class PersuadeSkill(Skill):
    """
    - Min TL: 11
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500 
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.PersuadeSkillDefinition,
            minTL=11,
            levelZeroBandwidth=1,
            levelZeroCost=500)
        
class PilotSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100 
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.PilotSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class ProfessionSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.ProfessionSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=200)

class ReconSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr500  
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.ReconSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=500)  
        
class ScienceSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.ScienceSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=200) 
        
class SeafarerSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.SeafarerSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)            
   
class StealthSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr500
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.StealthSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=500)  
        
class StewardSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.StewardSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100) 
        
class StreetwiseSkill(Skill):
    """
    - Min TL: 13
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr1000
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.StreetwiseSkillDefinition,
            minTL=13,
            levelZeroBandwidth=1,
            levelZeroCost=1000)       

class SurvivalSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.SurvivalSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=200)  
        
class TacticsSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.TacticsSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class VaccSuitSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """
    # NOTE: Vacc Suit is the only core rule skill that isn't given skill
    # requirement data (p74). This appears to have been an oversight given
    # Geir's post here
    # https://forum.mongoosepublishing.com/threads/google-sheets-robot-designer.123626/
    # I've given it the same stat block as other skills that I feel would
    # be most similar (Drive, Flyer, Pilot)
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.VaccSuitSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class JackOfAllTradesSkill(Skill):
    """
    - Requirement: Only compatible with Brain In A Jar
    - Requirement: Max level of 3
    """
    _MaxJackSkillLevel = 3

    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.JackOfAllTradesSkillDefinition,
            minTL=0,
            levelZeroBandwidth=0,
            levelZeroCost=0)
    
    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        
        return context.hasComponent(
            componentType=robots.BrainInAJarBrain,
            sequence=sequence)

    def updateOptions(self, sequence: str, context: robots.RobotContext) -> None:
        super().updateOptions(sequence=sequence, context=context)    
        if self._levelOption.isEnabled():
            self._levelOption.setMax(JackOfAllTradesSkill._MaxJackSkillLevel)
