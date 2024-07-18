import common
import construction
import enum
import robots
import traveller
import typing

class _SkillData(object):
    _RobotBrainMaxPossibleLevel = common.ScalarCalculation(
        value=3,
        name='Robot Brain Max Possible Skill Level')

    def __init__(
            self,
            skillDef: traveller.SkillDefinition,
            minTL: int,
            levelZeroBandwidth: int,
            levelZeroCost: int
            ) -> None:
        self._skillDef = skillDef
        self._minTL = common.ScalarCalculation(
            value=minTL,
            name=f'{skillDef.name()} 0 Min TL')
        self._levelZeroBandwidth = common.ScalarCalculation(
            value=levelZeroBandwidth,
            name=f'{skillDef.name()} 0 Required Bandwidth')
        self._levelZeroCost = common.ScalarCalculation(
            value=levelZeroCost,
            name=f'{skillDef.name()} 0 Cost')

    def skillDef(self) -> traveller.SkillDefinition:
        return self._skillDef

    def name(self) -> str:
        return self._skillDef.name()

    def minTL(self) -> common.ScalarCalculation:
        return self._minTL

    def levelZeroBandwidth(self) -> common.ScalarCalculation:
        return self._levelZeroBandwidth

    def levelZeroCost(self) -> common.ScalarCalculation:
        return self._levelZeroCost

    """
    - Requirement: The absolute max skill level for a robot is 3 (p73)
    - Requirement: Each increase in skill level after 0 requires an additional
    TL before it becomes available (p73)
    - Requirement: A robot can't have a skill that requires more bandwidth than
    its Inherent Bandwidth (p67)
    """
    # NOTE: This shouldn't be used for Brain in a Jar as it has no max skill
    # level
    # NOTE: Inherent bandwidth is optional as it's not obvious that it applies
    # when a single skill is being added as part of a Basic (None) package. The
    # rules just say you can install a package up to level 1 (p71). It does
    # say the skill is subject to the limitations of the brain but that seems
    # to be talking about modifiers to skill checks not compatibility.

    def calculateMaxSkillLevel(
            self,
            robotTL: common.ScalarCalculation,
            inherentBandwidth: typing.Optional[common.ScalarCalculation] = None
            ) -> typing.Optional[common.ScalarCalculation]:
        if robotTL.value() < self._minTL.value():
            return None
        maxLevel = common.Calculator.subtract(
            lhs=robotTL,
            rhs=self._minTL,
            name=f'{self._skillDef.name()} Max Skill Level Allowed By TL')
        if inherentBandwidth:
            bandwidthLimit = common.Calculator.subtract(
                lhs=inherentBandwidth,
                rhs=self._levelZeroBandwidth,
                name=f'{self._skillDef.name()} Max Skill Level Allowed By Inherent Bandwidth')
            maxLevel = common.Calculator.min(
                lhs=maxLevel,
                rhs=bandwidthLimit)
        return common.Calculator.min(
            lhs=maxLevel,
            rhs=_SkillData._RobotBrainMaxPossibleLevel,
            name=f'{self._skillDef.name()} Max Skill Level')

    def calculateBandwidthForLevel(
            self,
            level: common.ScalarCalculation
            ) -> common.ScalarCalculation:
        bandwidth = self._levelZeroBandwidth
        if level.value() > 0:
            bandwidth = common.Calculator.add(
                lhs=bandwidth,
                rhs=level,
                name=f'{self._skillDef.name()} {level.value()} Required Bandwidth')
        return bandwidth


# NOTE: Vacc Suit is the only core rule skill that isn't given skill requirement
# data (p74). This appears to have been an oversight given Geir's post here
# https://forum.mongoosepublishing.com/threads/google-sheets-robot-designer.123626/
# I've given it the same stat block as other skills that I feel would be most
# similar (Drive, Flyer, Pilot)
# NOTE Jack of all trades is only applicable to Brain in a Jar where the skills
# come from the biological brain
_SkillDataList = [
    _SkillData(traveller.AdminSkillDefinition,           8, 0,  100),
    _SkillData(traveller.AdvocateSkillDefinition,       10, 0,  500),
    _SkillData(traveller.AnimalsSkillDefinition,         9, 0,  200),
    _SkillData(traveller.ArtSkillDefinition,            10, 0,  500),
    _SkillData(traveller.AstrogationSkillDefinition,    12, 1,  500),
    _SkillData(traveller.AthleticsSkillDefinition,       8, 0,  100),
    _SkillData(traveller.BrokerSkillDefinition,         10, 0,  200),
    _SkillData(traveller.CarouseSkillDefinition,        11, 1,  500),
    _SkillData(traveller.DeceptionSkillDefinition,      13, 1, 1000),
    _SkillData(traveller.DiplomatSkillDefinition,       10, 1,  500),
    _SkillData(traveller.DriveSkillDefinition,           8, 0,  100),
    _SkillData(traveller.ElectronicsSkillDefinition,     8, 0,  100),
    _SkillData(traveller.EngineerSkillDefinition,        9, 0,  200),
    _SkillData(traveller.ExplosivesSkillDefinition,      8, 0,  100),
    _SkillData(traveller.FlyerSkillDefinition,           8, 0,  100),
    _SkillData(traveller.GamblerSkillDefinition,        10, 0,  500),
    _SkillData(traveller.GunCombatSkillDefinition,       8, 0,  100),
    _SkillData(traveller.GunnerSkillDefinition,          8, 0,  100),
    _SkillData(traveller.HeavyWeaponsSkillDefinition,    8, 0,  100),
    _SkillData(traveller.InvestigateSkillDefinition,    11, 1,  500),
    _SkillData(traveller.LanguageSkillDefinition,        9, 0,  200),
    _SkillData(traveller.LeadershipSkillDefinition,     13, 1, 1000),
    _SkillData(traveller.MechanicSkillDefinition,        8, 0,  100),
    _SkillData(traveller.MedicSkillDefinition,           9, 0,  200),
    _SkillData(traveller.MeleeSkillDefinition,           8, 0,  100),
    _SkillData(traveller.NavigationSkillDefinition,      8, 0,  100),
    _SkillData(traveller.PersuadeSkillDefinition,       11, 1,  500),
    _SkillData(traveller.PilotSkillDefinition,           8, 0,  100),
    _SkillData(traveller.ProfessionSkillDefinition,      9, 0,  200),
    _SkillData(traveller.ReconSkillDefinition,          10, 0,  500),
    _SkillData(traveller.ScienceSkillDefinition,         9, 0,  200),
    _SkillData(traveller.SeafarerSkillDefinition,        8, 0,  100),
    _SkillData(traveller.StealthSkillDefinition,        10, 0,  500),
    _SkillData(traveller.StewardSkillDefinition,         8, 0,  100),
    _SkillData(traveller.StreetwiseSkillDefinition,     13, 1, 1000),
    _SkillData(traveller.SurvivalSkillDefinition,       10, 0,  200),
    _SkillData(traveller.TacticsSkillDefinition,         8, 0,  100),
    _SkillData(traveller.VaccSuitSkillDefinition,        8, 0,  100),
    _SkillData(traveller.JackOfAllTradesSkillDefinition, 0, 0,    0)
]

_SkillDefDataMap = {skill.skillDef(): skill for skill in _SkillDataList}
_SkillNameMap = {skill.name(): skill for skill in _SkillDataList}

# NOTE: This function determines if a software skill stacks with hardware. It's
# a bit of a hack to deal with the fact the Navigation skill given by the
# Navigation System slot option doesn't stack with software Navigation skill
# where as skills given by hardware do stack with their software equivalent.
# This was a clarification by Geir
# https://forum.mongoosepublishing.com/threads/robot-handbook-rule-clarifications.124669/
# NOTE: This works on the assumption that (apart from software packages) the
# only source of the Navigation skill is the Navigation System
def _stacksWithHardware(
        skillDef: traveller.SkillDefinition,
        speciality: typing.Optional[str] = None
        ) -> bool:
    return  skillDef != traveller.NavigationSkillDefinition

def _calculateMaxSkillLevels(
        context: robots.RobotContext,
        sequence: str,
        skills: typing.Optional[typing.Iterable[traveller.SkillDefinition]] = None
        ) -> typing.Mapping[traveller.SkillDefinition, common.ScalarCalculation]:
    robotTL = common.ScalarCalculation(
        value=context.techLevel(),
        name='Robot TL')
    inherentBandwidth = context.attributeValue(
        attributeId=robots.RobotAttributeId.InherentBandwidth,
        sequence=sequence)
    if isinstance(inherentBandwidth, common.ScalarCalculation):
        return {}

    if not skills:
        skills = _SkillDefDataMap.keys()
    skillMap = {}
    for skillDef in skills:
        assert(isinstance(skillDef, traveller.SkillDefinition))
        skillData = _SkillDefDataMap.get(skillDef)
        if not skillData:
            continue
        maxSkillLevel = skillData.calculateMaxSkillLevel(
            robotTL=robotTL,
            inherentBandwidth=inherentBandwidth)
        if maxSkillLevel:
            skillMap[skillDef] = maxSkillLevel

    return skillMap


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

class SkillPackage(robots.RobotComponentInterface):
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
                levels=level,
                # Set flags for no negative modifiers
                flags=construction.SkillFlags.ApplyPositiveCharacteristicModifier,
                stacks=_stacksWithHardware(
                    skillDef=skillDef,
                    speciality=speciality)))

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

    _PrimitiveNote = 'The skill package counteracts any negative DMs associated with the robot\'s DEX or INT characteristics. (p69)'

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
    # NOTE: The rules aren't clear what it means for a robot to have the Weapon
    # skill. I think the intention it's intended to have a single mounted
    # weapon, or at least mounted weapons all of the same basic class. With the
    # package giving the robot the skill needed to use that class of weapon.
    # This is a little ambiguous for robots with weapons of different types but
    # but I suspect in practice such a robot is unlikely to exist as there would
    # be no way of giving it the skills to use two classes of weapon. I've gone
    # with the approach that the user can select what weapon skill they want the
    # robot to have as it gives the most flexibility.

    _WeaponSkills = [
        traveller.GunCombatSkillDefinition,
        traveller.HeavyWeaponsSkillDefinition,
        traveller.MeleeSkillDefinition
        ]

    _WeaponSkillLevel = common.ScalarCalculation(
        value=1,
        name='Primitive (Homing) Skill Package Weapon Skill Level')

    def __init__(self) -> None:
        super().__init__(componentName='Homing')

        self._combatSkillOption = construction.StringOption(
            id='WeaponSkill',
            name='Weapon Skill',
            choices=['default'],
            isEditable=False,
            isOptional=False,
            description='Specify the weapon skill granted by the skill package')

        self._specialityOption = construction.StringOption(
            id='WeaponSpeciality',
            name='Speciality',
            choices=['default'],
            isEditable=False,
            isOptional=False,
            description='Specify the weapon skill speciality granted by the skill package')

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._combatSkillOption)
        options.append(self._specialityOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> None:
        super().updateOptions(sequence, context)

        self._combatSkillOption.setChoices(
            choices=[s.name() for s in HomingPrimitiveSkillPackage._WeaponSkills])

        skillData = self._selectedSkill()
        specialityChoices = []
        if skillData:
            skillDef = skillData.skillDef()
            if skillDef.isFixedSpeciality():
                specialityChoices = [s.value for s in skillDef.fixedSpecialities()]
            elif skillDef.isCustomSpeciality():
                specialityChoices = skillDef.customSpecialities()
        self._specialityOption.setChoices(choices=specialityChoices)
        self._specialityOption.setEnabled(len(specialityChoices) > 0)

    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = super()._createStep(sequence=sequence, context=context)

        skillData = self._selectedSkill()
        if skillData:
            skillDef = skillData.skillDef()
            speciality = self._selectedSpeciality()

            step.addFactor(factor=construction.SetSkillFactor(
                skillDef=skillDef,
                speciality=speciality,
                levels=HomingPrimitiveSkillPackage._WeaponSkillLevel,
                # Set flags for no negative modifiers
                flags=construction.SkillFlags.ApplyPositiveCharacteristicModifier,
                stacks=_stacksWithHardware(skillDef=skillDef, speciality=speciality)))

        return step

    def _selectedSkill(self) -> typing.Optional[_SkillData]:
        skillName = self._combatSkillOption.value() if self._combatSkillOption.isEnabled() else None
        if not skillName:
            return None
        return _SkillNameMap.get(skillName)

    def _selectedSpeciality(self) -> typing.Optional[typing.Union[enum.Enum, str]]:
        specialityName = self._specialityOption.value() if self._specialityOption.isEnabled() else None
        if not specialityName:
            return None
        assert(isinstance(specialityName, str))

        skillData = self._selectedSkill()
        if not skillData:
            return None
        skillDef = skillData.skillDef()
        if skillDef.isFixedSpeciality():
            for speciality in skillDef.fixedSpecialities():
                assert(isinstance(speciality, enum.Enum))
                if specialityName == speciality.value:
                    return speciality
        elif skillDef.isCustomSpeciality():
            return specialityName

        return None

class BasicSkillPackage(SkillPackage):
    """
    - Min TL: 8
    - Requirement: Only compatible with basic brain
    """

    def __init__(
            self,
            componentName: str,
            bandwidth: int,
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
            bandwidth=bandwidth,
            skills=skills,
            notes=notes)

    def typeString(self) -> str:
        return 'Basic Skill Package'

# NOTE: None is the first basic skill package listed as it should appear
# before other 'real' options when listed by enumeration
# NOTE: The rules also talk about being able to buy basic skill packages
# on a chip that you can install on a robot with a Basic (None) skill
# package. I've not done anything to implement this for now as I don't
# think it's worth the faff. If you want to know the robots stats with
# chip installed you can just switch it from None to whatever skill package
# you installed in the UI.
class NoneBasicSkillPackage(BasicSkillPackage):
    """
    - Requirement: A Basic (None) robot can have up to 2 standard skills
    installed and each skill can by up to level 1. Individual skills
    can't consume more than 1 bandwidth. Unlike other Basic skill packages,
    these skills are subject to negative INT characteristic DMs
    """

    _StandardSkillNote = 'Standard skills installed in a Basic (None) robot are subject to the brain\'s negative INT characteristic DMs. (p71)'

    def __init__(self) -> None:
        super().__init__(
            componentName='None',
            bandwidth=0)

        self._primarySkillOption = construction.StringOption(
            id='PrimarySkill',
            name='Primary Skill',
            value=None,
            choices=[],
            isOptional=True,
            isEditable=False,
            enabled=False,
            description='Optionally select a primary standard skill to be installed on the robot. (p71)')

        self._primarySpecialityOption = construction.StringOption(
            id='PrimarySpeciality',
            name='Primary Speciality',
            value=None,
            choices=[],
            isOptional=True,
            enabled=False,
            description='Optionally select a speciality for the primary skill.')

        self._primaryLevelOption = construction.IntegerOption(
            id='PrimaryLevel',
            name='Primary Level',
            value=1,
            minValue=0,
            maxValue=1,
            enabled=False,
            description='Select the level for the primary skill.')

        self._secondarySkillOption = construction.StringOption(
            id='SecondarySkill',
            name='Secondary Skill',
            value=None,
            choices=[],
            isOptional=True,
            isEditable=False,
            enabled=False,
            description='Optionally select a secondary standard skill to be installed on the robot. (p71)')

        self._secondarySpecialityOption = construction.StringOption(
            id='SecondarySpeciality',
            name='Secondary Speciality',
            value=None,
            choices=[],
            isOptional=True,
            enabled=False,
            description='Optionally select a speciality for the secondary skill.')

        self._secondaryLevelOption = construction.IntegerOption(
            id='SecondaryLevel',
            name='Secondary Level',
            value=1,
            minValue=0,
            maxValue=1,
            enabled=False,
            description='Select the primary level for the secondary skill.')

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()

        if self._primarySkillOption.isEnabled():
            options.append(self._primarySkillOption)
        if self._primarySpecialityOption.isEnabled():
            options.append(self._primarySpecialityOption)
        if self._primaryLevelOption.isEnabled():
            options.append(self._primaryLevelOption)

        if self._secondarySkillOption.isEnabled():
            options.append(self._secondarySkillOption)
        if self._secondarySpecialityOption.isEnabled():
            options.append(self._secondarySpecialityOption)
        if self._secondaryLevelOption.isEnabled():
            options.append(self._secondaryLevelOption)

        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        super().updateOptions(sequence, context)

        self._updateSkillOptions(context=context, isPrimary=True)
        self._updateSkillOptions(context=context, isPrimary=False)

    def _updateSkillOptions(
            self,
            context: robots.RobotContext,
            isPrimary: bool
            ) -> None:
        if isPrimary:
            skillOption = self._primarySkillOption
            specialityOption = self._primarySpecialityOption
            levelOption = self._primaryLevelOption
        else:
            skillOption = self._secondarySkillOption
            specialityOption = self._secondarySpecialityOption
            levelOption = self._secondaryLevelOption

        compatibleSkills = self._compatibleSkills(
            robotTL=context.techLevel(),
            isPrimary=isPrimary)
        skillOption.setChoices(choices=compatibleSkills.keys())
        skillOption.setEnabled(enabled=len(compatibleSkills) > 0)

        skillData = compatibleSkills.get(skillOption.value())
        skillDef = skillData.skillDef() if skillData else None

        if skillDef:
            robotTL = common.ScalarCalculation(
                value=context.techLevel(),
                name='Robot TL')
            maxSkillLevel = skillData.calculateMaxSkillLevel(robotTL=robotTL)
            levelOneBandwidth = skillData.calculateBandwidthForLevel(
                level=common.ScalarCalculation(value=1))
            canIncreaseSkill = maxSkillLevel.value() > 0 and levelOneBandwidth.value() < 2

            if canIncreaseSkill and not skillDef.isSimple():
                if skillDef.isFixedSpeciality():
                    specialityEnum = skillDef.fixedSpecialities()
                    specialityOption.setChoices(
                        choices=[speciality.value for speciality in specialityEnum])
                elif skillDef.isCustomSpeciality():
                    specialityOption.setChoices(
                        choices=skillDef.customSpecialities())

                specialityOption.setEditable(
                    editable=skillDef.isCustomSpeciality())
                specialityOption.setEnabled(enabled=True)
            else:
                specialityOption.setEnabled(enabled=False)

            levelOption.setEnabled(
                enabled=canIncreaseSkill and skillDef.isSimple())
        else:
            specialityOption.setEnabled(False)
            levelOption.setEnabled(False)

    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = super()._createStep(sequence=sequence, context=context)

        bandwidths = []
        hasSkill = False
        for isPrimary in [True, False]:
            skillData = self._selectedSkill(isPrimary=isPrimary)
            if skillData:
                skillDef = skillData.skillDef()
                speciality = self._selectedSpeciality(isPrimary=isPrimary)
                level = self._selectedLevel(isPrimary=isPrimary)
                hasSkill = True

                bandwidths.append(
                    skillData.calculateBandwidthForLevel(level=level))

                # The rules say that, for the skills installed on a basic none
                # brain, negative characteristic DMs should be applied for INT
                # based skills but not DEX (and I assume STR) based ones (p71).
                characteristic = robots.skillToCharacteristic(
                    skillDef=skillDef,
                    speciality=speciality)
                flags = construction.SkillFlags.ApplyPositiveCharacteristicModifier
                if characteristic == traveller.Characteristic.Intellect:
                    flags |= construction.SkillFlags.ApplyNegativeCharacteristicModifier

                stacks = _stacksWithHardware(
                    skillDef=skillDef,
                    speciality=speciality)
                step.addFactor(factor=construction.SetSkillFactor(
                    skillDef=skillDef,
                    speciality=speciality,
                    levels=level,
                    flags=flags,
                    stacks=stacks))

        totalBandwidth = common.Calculator.sum(
            values=bandwidths,
            name=f'{self.componentString()} Total Bandwidth Required')
        if totalBandwidth.value() > 0:
            step.setBandwidth(bandwidth=construction.ConstantModifier(
                value=totalBandwidth))

        if hasSkill:
            step.addNote(note=NoneBasicSkillPackage._StandardSkillNote)

        return step

    def _compatibleSkills(
            self,
            robotTL: int,
            isPrimary: bool
            ) -> typing.Mapping[str, _SkillData]:
        skills = {}

        otherSkillData = self._selectedSkill(isPrimary=not isPrimary)

        for skillData in _SkillDataList:
            if skillData.skillDef() == traveller.JackOfAllTradesSkillDefinition:
                continue
            if skillData == otherSkillData:
                continue

            if robotTL >= skillData.minTL().value():
                skills[skillData.name()] = skillData

        return skills

    def _selectedSkill(
            self,
            isPrimary: bool
            ) -> typing.Optional[_SkillData]:
        skillOption = self._primarySkillOption if isPrimary else self._secondarySkillOption
        skillName = skillOption.value() if skillOption.isEnabled() else None
        if not skillName:
            return None
        return _SkillNameMap.get(skillName)

    def _selectedSpeciality(
            self,
            isPrimary
            ) -> typing.Optional[typing.Union[enum.Enum, str]]:
        specialityOption = self._primarySpecialityOption if isPrimary else self._secondarySpecialityOption
        specialityName = specialityOption.value() if specialityOption.isEnabled() else None
        if not specialityName:
            return None
        assert(isinstance(specialityName, str))

        skillData = self._selectedSkill(isPrimary=isPrimary)
        if not skillData:
            return None
        skillDef = skillData.skillDef()
        if skillDef.isFixedSpeciality():
            for speciality in skillDef.fixedSpecialities():
                assert(isinstance(speciality, enum.Enum))
                if specialityName == speciality.value:
                    return speciality
        elif skillDef.isCustomSpeciality():
            return specialityName

        return None

    def _selectedLevel(
            self,
            isPrimary: bool
            ) -> typing.Optional[common.ScalarCalculation]:
        skillData = self._selectedSkill(isPrimary=isPrimary)
        if not skillData:
            return None

        speciality = self._selectedSpeciality(isPrimary=isPrimary)
        if speciality:
            skillLevel = 1
        else:
            levelOption = self._primaryLevelOption if isPrimary else self._secondaryLevelOption
            skillLevel = levelOption.value() if levelOption.isEnabled() else 0
        return common.ScalarCalculation(
            value=skillLevel,
            name='Selected {wording} Skill Level'.format(
                wording={"Primary" if isPrimary else "Secondary"}))

class PreInstalledBasicSkillPackage(BasicSkillPackage):
    """
    - Bandwidth: 1
    - Note: Negative modifiers due to the robot\'s INT characteristic do no
    apply when making checks using skills provided by the package. (p70)
    """

    _BasicNote = 'The skill package counteracts any negative DMs associated with the robot\'s INT characteristic. (p70)'

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
            bandwidth=1,
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
    - Skill: Vehicle skill equal to the robot's Agility Enhancement Level (or
      0 if no enhancement)
    - Note: Athletics (dexterity) equal to the robot's Agility Enhancement Level
    for purposes of hazardous manoeuvring and reactions such as dodging
    - Note: If the robot also has an Autopilot score, the modifiers for the
    Autopilot and Vehicle Skill don't stack (p49)
    - Requirement: Requires some form of locomotion
    """
    # NOTE: The rules are a bit confusing when a robot can take the locomotion
    # skill package and what skills they can get from it. They say the the
    # package is usually installed on robots with VSM, but they don't say that
    # has to be the case (p70). The also say it gives the robot a skill in it's
    # vehicle class (p71). For this later point I assume this is intended to be
    # based on its primary locomotion, however that seems ambiguous for some
    # forms of locomotion. It's pretty obvious for Wheels, Tracks, Grav, Walker,
    # Aeroplane & Hovercraft as they have either exact or very obvious mappings
    # to skill specialities. VTOL and Aquatic are ambiguous as pretty much any
    # of the Flyer/Seafarer specialities could be applicable. Thruster's is just
    # a complete odd ball as it's not obvious any of the standard skills would
    # be applicable, my best guess would be one of the Flyer or Pilot skills but
    # it would really depend on how the thrust was actually being used to propel
    # the robot. As it's so ambiguous I've chosen to just give the user free
    # choice from all the vehicle related skills for all locomotion types.
    # NOTE: The note about Autopilot and vehicle skills not stacking is handled
    # by a note added in finalisation

    _VehicleSkills = [
        traveller.DriveSkillDefinition,
        traveller.FlyerSkillDefinition,
        traveller.SeafarerSkillDefinition,
        traveller.PilotSkillDefinition
        ]

    _DefaultAgilityModifier = common.ScalarCalculation(
        value=0,
        name='Default Agility Enhancement')

    _AthleticsNote = 'The robot has Athletics (dexterity) {agility} for purposes of hazardous manoeuvring and reactions such as dodging. (p71)'

    def __init__(self) -> None:
        super().__init__(componentName='Locomotion')

        self._vehicleSkillOption = construction.StringOption(
            id='VehicleSkill',
            name='Vehicle Skill',
            choices=['default'],
            isEditable=False,
            isOptional=False,
            description='Specify the vehicle skill granted by the skill package')

        self._specialityOption = construction.StringOption(
            id='VehicleSpeciality',
            name='Speciality',
            choices=['default'],
            isEditable=False,
            isOptional=False,
            description='Specify the vehicle skill speciality granted by the skill package')

    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        locomotions = context.findComponents(
            componentType=robots.Locomotion,
            sequence=sequence)
        hasCompatibleLocomotion = False
        for locomotion in locomotions:
            if not isinstance(locomotion, robots.NoPrimaryLocomotion):
                hasCompatibleLocomotion = True
                break
        return hasCompatibleLocomotion

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._vehicleSkillOption)
        if self._specialityOption.isEnabled():
            options.append(self._specialityOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> None:
        super().updateOptions(sequence, context)

        self._vehicleSkillOption.setChoices(
            choices=[s.name() for s in LocomotionBasicSkillPackage._VehicleSkills])

        skillData = self._selectedSkill()
        specialityChoices = []
        if skillData:
            skillDef = skillData.skillDef()
            if skillDef.isFixedSpeciality():
                specialityChoices = [s.value for s in skillDef.fixedSpecialities()]
            elif skillDef.isCustomSpeciality():
                specialityChoices = skillDef.customSpecialities()
        self._specialityOption.setChoices(choices=specialityChoices)
        self._specialityOption.setEnabled(len(specialityChoices) > 0)

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
            agilityModifier = agilityEnhancement.agilityModifier()
        else:
            agilityModifier = LocomotionBasicSkillPackage._DefaultAgilityModifier

        skillData = self._selectedSkill()
        if skillData:
            skillDef = skillData.skillDef()
            speciality = self._selectedSpeciality()
            skillLevel = common.Calculator.equals(
                value=agilityModifier,
                name=f'{self.componentString()} Vehicle Skill Level')

            step.addFactor(factor=construction.SetSkillFactor(
                skillDef=skillDef,
                speciality=speciality,
                levels=skillLevel,
                # Set flags for no negative modifiers
                flags=construction.SkillFlags.ApplyPositiveCharacteristicModifier,
                stacks=_stacksWithHardware(skillDef=skillDef, speciality=speciality)))

        if agilityModifier.value() != 0:
            step.addNote(note=LocomotionBasicSkillPackage._AthleticsNote.format(
                agility=agilityModifier.value()))

        return step

    def _selectedSkill(self) -> typing.Optional[_SkillData]:
        skillName = self._vehicleSkillOption.value() if self._vehicleSkillOption.isEnabled() else None
        if not skillName:
            return None
        return _SkillNameMap.get(skillName)

    def _selectedSpeciality(self) -> typing.Optional[typing.Union[enum.Enum, str]]:
        specialityName = self._specialityOption.value() if self._specialityOption.isEnabled() else None
        if not specialityName:
            return None
        assert(isinstance(specialityName, str))

        skillData = self._selectedSkill()
        if not skillData:
            return None
        skillDef = skillData.skillDef()
        if skillDef.isFixedSpeciality():
            for speciality in skillDef.fixedSpecialities():
                assert(isinstance(speciality, enum.Enum))
                if specialityName == speciality.value:
                    return speciality
        elif skillDef.isCustomSpeciality():
            return specialityName

        return None

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
    - Trait: Alarm
    - Option: Need something to select which Weapon skill this gives
    """
    # NOTE: See note on HomingPrimitiveSkillPackage for details on now the
    # Weapon skill is handled

    _WeaponSkills = [
        traveller.GunCombatSkillDefinition,
        traveller.HeavyWeaponsSkillDefinition,
        traveller.MeleeSkillDefinition
        ]

    _WeaponSkillLevel = common.ScalarCalculation(
        value=1,
        name='Security (Basic) Skill Package Weapon Skill Level')

    def __init__(self) -> None:
        super().__init__(
            componentName='Security',
            skills=[(traveller.TacticsSkillDefinition, traveller.TacticsSkillSpecialities.Military, 1)])

        self._combatSkillOption = construction.StringOption(
            id='WeaponSkill',
            name='Weapon Skill',
            choices=['default'],
            isEditable=False,
            isOptional=False,
            description='Specify the weapon skill granted by the skill package')

        self._specialityOption = construction.StringOption(
            id='WeaponSpeciality',
            name='Speciality',
            choices=['default'],
            isEditable=False,
            isOptional=False,
            description='Specify the weapon skill speciality granted by the skill package')

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._combatSkillOption)
        options.append(self._specialityOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> None:
        super().updateOptions(sequence, context)

        self._combatSkillOption.setChoices(
            choices=[s.name() for s in SecurityBasicSkillPackage._WeaponSkills])

        skillData = self._selectedSkill()
        specialityChoices = []
        if skillData:
            skillDef = skillData.skillDef()
            if skillDef.isFixedSpeciality():
                specialityChoices = [s.value for s in skillDef.fixedSpecialities()]
            elif skillDef.isCustomSpeciality():
                specialityChoices = skillDef.customSpecialities()
        self._specialityOption.setChoices(choices=specialityChoices)
        self._specialityOption.setEnabled(len(specialityChoices) > 0)

    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = super()._createStep(sequence=sequence, context=context)

        skillData = self._selectedSkill()
        if skillData:
            skillDef = skillData.skillDef()
            speciality = self._selectedSpeciality()

            step.addFactor(factor=construction.SetSkillFactor(
                skillDef=skillDef,
                speciality=speciality,
                levels=SecurityBasicSkillPackage._WeaponSkillLevel,
                # Set flags for no negative modifiers
                flags=construction.SkillFlags.ApplyPositiveCharacteristicModifier,
                stacks=_stacksWithHardware(skillDef=skillDef, speciality=speciality)))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Alarm))

        return step

    def _selectedSkill(self) -> typing.Optional[_SkillData]:
        skillName = self._combatSkillOption.value() if self._combatSkillOption.isEnabled() else None
        if not skillName:
            return None
        return _SkillNameMap.get(skillName)

    def _selectedSpeciality(self) -> typing.Optional[typing.Union[enum.Enum, str]]:
        specialityName = self._specialityOption.value() if self._specialityOption.isEnabled() else None
        if not specialityName:
            return None
        assert(isinstance(specialityName, str))

        skillData = self._selectedSkill()
        if not skillData:
            return None
        skillDef = skillData.skillDef()
        if skillDef.isFixedSpeciality():
            for speciality in skillDef.fixedSpecialities():
                assert(isinstance(speciality, enum.Enum))
                if specialityName == speciality.value:
                    return speciality
        elif skillDef.isCustomSpeciality():
            return specialityName

        return None

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
            levels=ServantBasicSkillPackage._ProfessionSkillLevel,
            # Set flags for no negative modifiers
            flags=construction.SkillFlags.ApplyPositiveCharacteristicModifier,
            stacks=_stacksWithHardware(
                skillDef=traveller.ProfessionSkillDefinition,
                speciality=profession.value)))

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
            notes=['Can support up to 8 Middle or 100 Basic passengers. (p72)'])

class TargetBasicSkillPackage(PreInstalledBasicSkillPackage):
    """
    - Skill: Explosives 1 or Weapon 1
    - Skill: Explosives 0 if Weapon is taken as the primary skill and the robot
    has a Self Destruct System Slot Option
    - Skill: Recon 0 (p72)
    """
    # NOTE: The table on p70 doesn't have Recon 0 but the description on
    # p72 does
    # NOTE: See note on HomingPrimitiveSkillPackage for details on now the
    # Weapon skill is handled

    _CombatSkills = [
        traveller.ExplosivesSkillDefinition,
        traveller.GunCombatSkillDefinition,
        traveller.HeavyWeaponsSkillDefinition,
        traveller.MeleeSkillDefinition
        ]

    _CombatSkillLevel = common.ScalarCalculation(
        value=1,
        name='Basic (Target) Skill Package Combat Skill Level')

    _SelfDestructExplosivesSkillLevel = common.ScalarCalculation(
        value=0,
        name='Basic (Target) Skill Package Self Destruct Explosives Skill')

    def __init__(self) -> None:
        super().__init__(
            componentName='Target',
            skills=[(traveller.ReconSkillDefinition, None, 0)])

        self._combatSkillOption = construction.StringOption(
            id='CombatSkill',
            name='Combat Skill',
            choices=['default'],
            isEditable=False,
            isOptional=False,
            description='Specify the combat skill granted by the skill package')

        self._specialityOption = construction.StringOption(
            id='CombatSpeciality',
            name='Speciality',
            choices=['default'],
            isEditable=False,
            isOptional=False,
            description='Specify the combat skill speciality granted by the skill package')

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._combatSkillOption)
        if self._specialityOption.isEnabled():
            options.append(self._specialityOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> None:
        super().updateOptions(sequence, context)

        self._combatSkillOption.setChoices(
            choices=[s.name() for s in TargetBasicSkillPackage._CombatSkills])

        skillData = self._selectedSkill()
        specialityChoices = []
        if skillData:
            skillDef = skillData.skillDef()
            if skillDef.isFixedSpeciality():
                specialityChoices = [s.value for s in skillDef.fixedSpecialities()]
            elif skillDef.isCustomSpeciality():
                specialityChoices = skillDef.customSpecialities()
        self._specialityOption.setChoices(choices=specialityChoices)
        self._specialityOption.setEnabled(len(specialityChoices) > 0)

    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = super()._createStep(sequence=sequence, context=context)

        skillData = self._selectedSkill()
        if skillData:
            skillDef = skillData.skillDef()
            speciality = self._selectedSpeciality()

            step.addFactor(factor=construction.SetSkillFactor(
                skillDef=skillDef,
                speciality=speciality,
                levels=TargetBasicSkillPackage._CombatSkillLevel,
                # Set flags for no negative modifiers
                flags=construction.SkillFlags.ApplyPositiveCharacteristicModifier,
                stacks=_stacksWithHardware(skillDef=skillDef, speciality=speciality)))

            if skillDef != traveller.ExplosivesSkillDefinition:
                hasSelfDestruct = context.hasComponent(
                    componentType=robots.SelfDestructSystemSlotOption,
                    sequence=sequence)
                if hasSelfDestruct:
                    step.addFactor(factor=construction.SetSkillFactor(
                        skillDef=traveller.ExplosivesSkillDefinition,
                        levels=TargetBasicSkillPackage._SelfDestructExplosivesSkillLevel,
                        # Set flags for no negative modifiers
                        flags=construction.SkillFlags.ApplyPositiveCharacteristicModifier,
                        stacks=_stacksWithHardware(skillDef=traveller.ExplosivesSkillDefinition)))

        return step

    def _selectedSkill(self) -> typing.Optional[_SkillData]:
        skillName = self._combatSkillOption.value() if self._combatSkillOption.isEnabled() else None
        if not skillName:
            return None
        return _SkillNameMap.get(skillName)

    def _selectedSpeciality(self) -> typing.Optional[typing.Union[enum.Enum, str]]:
        specialityName = self._specialityOption.value() if self._specialityOption.isEnabled() else None
        if not specialityName:
            return None
        assert(isinstance(specialityName, str))

        skillData = self._selectedSkill()
        if not skillData:
            return None
        skillDef = skillData.skillDef()
        if skillDef.isFixedSpeciality():
            for speciality in skillDef.fixedSpecialities():
                assert(isinstance(speciality, enum.Enum))
                if specialityName == speciality.value:
                    return speciality
        elif skillDef.isCustomSpeciality():
            return specialityName

        return None

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
    # NOTE: The rules don't explicitly state that the package negates negative
    # characteristics DM. The tactical variant says "This tactical skill is not
    # subject to the INT limitations of the robot’s brain" but there is nothing
    # for the standard package. I suspect this is an oversight as it would be
    # odd for a hunter/killers Recon skill to be affected by INT when the basic
    # recon and target packages aren't.

    _BaseNote = 'The rules don\'t explicitly state it, but it seems logical that this skill package counteracts any negative DMs associated with the robot\'s INT characteristic in the same way as basic skill packages do. (p72)'

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
            notes=[HunterKillerSkillPackage._BaseNote])

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
    # NOTE: The note about the skill not being affected by INT is handled
    # in the base class

    _TacticsCost = common.ScalarCalculation(
        value=10000,
        name='Tactics Hunter/Killer Skill Package Cost')

    def __init__(self) -> None:
        super().__init__(
            componentName='Tactical',
            skills=[(traveller.GunCombatSkillDefinition, None, 0),
                    (traveller.MeleeSkillDefinition, None, 0),
                    (traveller.ReconSkillDefinition, None, 0),
                    (traveller.TacticsSkillDefinition, traveller.TacticsSkillSpecialities.Military, 2)])

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

class Skill(robots.RobotComponentInterface):
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
    # This means the fact the robot's Mechanic 1 skill has not been counted
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
            skillDef: traveller.SkillDefinition
            ) -> None:
        super().__init__()

        self._skillDef = skillDef

        self._levelOption = construction.IntegerOption(
            id='Level',
            name='Level',
            value=0,
            minValue=0,
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
                    value=0,
                    minValue=0,
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

        skillData = _SkillDefDataMap[self._skillDef]
        if context.techLevel() < skillData.minTL().value():
            return False

        if not context.hasComponent(
                componentType=robots.SkilledRobotBrain,
                sequence=sequence):
            return False

        # The bandwidth required for the skill at level 0 must be less than or
        # equal to the robot's Inherent Bandwidth
        inherentBandwidth = context.attributeValue(
            attributeId=robots.RobotAttributeId.InherentBandwidth,
            sequence=sequence)
        if not inherentBandwidth:
            # NOTE: This assumes that if there is no inherent bandwidth it must
            # be a brain in a jar so the skill is compatible
            return True
        assert(isinstance(inherentBandwidth, common.ScalarCalculation))
        return skillData.levelZeroBandwidth().value() <= inherentBandwidth.value()

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
            self._levelOption.setMax(None)
            self._levelOption.setEnabled(self._skillDef.isSimple())
        else:
            inherentBandwidth = context.attributeValue(
                attributeId=robots.RobotAttributeId.InherentBandwidth,
                sequence=sequence)
            assert(isinstance(inherentBandwidth, common.ScalarCalculation))

            skillData = _SkillDefDataMap[self._skillDef]
            maxLevel = skillData.calculateMaxSkillLevel(
                robotTL=robotTL,
                inherentBandwidth=inherentBandwidth)
            self._levelOption.setMax(maxLevel.value() \
                                     if self._skillDef.isSimple() else \
                                     Skill._SpecialitySkillMaxBaseLevel.value())
            self._levelOption.setEnabled(self._levelOption.max() > 0)

        if self._skillDef.isFixedSpeciality():
            for _, levelOption in self._fixedSpecialityOptions:
                levelOption.setMax(maxLevel.value() \
                                   if maxLevel != None else \
                                   None) # Robot brains have no max
                levelOption.setEnabled(maxLevel == None or maxLevel.value() > 0)
        elif self._skillDef.isCustomSpeciality():
            self._customSpecialityCountOption.setEnabled(
                enabled=(maxLevel == None) or (maxLevel.value() > 0))

            specialityCount = 0
            if self._customSpecialityCountOption.isEnabled():
                specialityCount = self._customSpecialityCountOption.value()

            while len(self._customSpecialityOptions) > specialityCount:
                self._customSpecialityOptions.pop()
            while len(self._customSpecialityOptions) < specialityCount:
                specialityIndex = len(self._customSpecialityOptions) + 1 # 1 based for user
                nameOption = construction.StringOption(
                    id=f'Speciality{specialityIndex}Name',
                    name=f'Speciality {specialityIndex} Name',
                    choices=self._skillDef.customSpecialities(),
                    value='',
                    description='Specify the name of the speciality')
                levelOption = construction.IntegerOption(
                    id=f'Speciality{specialityIndex}Level',
                    name=f'Speciality {specialityIndex} Level',
                    value=1,
                    minValue=1,
                    description=f'Specify the level of the speciality')
                self._customSpecialityOptions.append((nameOption, levelOption))

            # Level options are only enabled if the name is enabled and not empty
            for nameOption, levelOption in self._customSpecialityOptions:
                levelOption.setMax(maxLevel.value() \
                                   if maxLevel != None else \
                                   None) # Robot brains have no max
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
        skillName = self._skillDef.name(speciality=speciality)
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
            levels=level,
            # Set flags for positive and negative characteristics to be applied
            flags=construction.SkillFlags.ApplyPositiveCharacteristicModifier |
            construction.SkillFlags.ApplyNegativeCharacteristicModifier,
            stacks=_stacksWithHardware(
                skillDef=self._skillDef,
                speciality=speciality)))

        if not hasBrainInAJar:
            skillData = _SkillDefDataMap[self._skillDef]
            bandwidth = skillData.calculateBandwidthForLevel(level=level)

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
                levelZeroCost=skillData.levelZeroCost(),
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
        super().__init__(skillDef=traveller.AdminSkillDefinition)

class AdvocateSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr500
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.AdvocateSkillDefinition)

class AnimalsSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr200
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.AnimalsSkillDefinition)

class ArtSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr500
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.ArtSkillDefinition)

class AstrogationSkill(Skill):
    """
    - Min TL: 12
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.AstrogationSkillDefinition)

class AthleticsSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: variable
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.AthleticsSkillDefinition)

class BrokerSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.BrokerSkillDefinition)

class CarouseSkill(Skill):
    """
    - Min TL: 11
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.CarouseSkillDefinition)

class DeceptionSkill(Skill):
    """
    - Min TL: 13
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr1000
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.DeceptionSkillDefinition)

class DiplomatSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.DiplomatSkillDefinition)

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
        super().__init__(skillDef=traveller.DriveSkillDefinition)

class ElectronicsSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.ElectronicsSkillDefinition)

class EngineerSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.EngineerSkillDefinition)

class ExplosivesSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.ExplosivesSkillDefinition)

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
        super().__init__(skillDef=traveller.FlyerSkillDefinition)

class GamblerSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr500
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.GamblerSkillDefinition)

class GunCombatSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.GunCombatSkillDefinition)

class GunnerSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.GunnerSkillDefinition)

class HeavyWeaponsSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.HeavyWeaponsSkillDefinition)

class InvestigateSkill(Skill):
    """
    - Min TL: 11
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.InvestigateSkillDefinition)

class LanguageSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.LanguageSkillDefinition)

class LeadershipSkill(Skill):
    """
    - Min TL: 13
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr1000
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.LeadershipSkillDefinition)

class MechanicSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.MechanicSkillDefinition)

class MedicSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.MedicSkillDefinition)

class MeleeSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.MeleeSkillDefinition)

class NavigationSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.NavigationSkillDefinition)

class PersuadeSkill(Skill):
    """
    - Min TL: 11
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.PersuadeSkillDefinition)

class PilotSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.PilotSkillDefinition)

class ProfessionSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.ProfessionSkillDefinition)

class ReconSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr500
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.ReconSkillDefinition)

class ScienceSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.ScienceSkillDefinition)

class SeafarerSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.SeafarerSkillDefinition)

class StealthSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr500
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.StealthSkillDefinition)

class StewardSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.StewardSkillDefinition)

class StreetwiseSkill(Skill):
    """
    - Min TL: 13
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr1000
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.StreetwiseSkillDefinition)

class SurvivalSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.SurvivalSkillDefinition)

class TacticsSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.TacticsSkillDefinition)

class VaccSuitSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.VaccSuitSkillDefinition)

class JackOfAllTradesSkill(Skill):
    """
    - Requirement: Only compatible with Brain In A Jar
    - Requirement: Max level of 3
    """
    _MaxJackSkillLevel = 3

    def __init__(self) -> None:
        super().__init__(skillDef=traveller.JackOfAllTradesSkillDefinition)

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
