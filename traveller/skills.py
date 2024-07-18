import enum
import typing

class SkillDefinition(object):
    class SkillType(enum.Enum):
        Simple = 'Simple'
        FixedSpeciality = 'Fixed Speciality'
        CustomSpeciality = 'Custom Speciality'

    def __init__(
            self,
            skillName: str,
            skillType: SkillType,
            fixedSpecialities: typing.Optional[typing.Type[enum.Enum]] = None,
            customSpecialities: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        self._skillName = skillName
        self._skillType = skillType
        self._fixedSpecialities = None
        self._customSpecialities = None
        if self._skillType == SkillDefinition.SkillType.FixedSpeciality:
            if fixedSpecialities == None:
                raise AttributeError('Fixed speciality skills must have a fixed specialities type specified')
            self._fixedSpecialities = fixedSpecialities
        elif self._skillType == SkillDefinition.SkillType.CustomSpeciality:
            if customSpecialities == None:
                raise AttributeError('Custom speciality skills must have a list of example specialities specified')
            self._customSpecialities = customSpecialities

    def name(
            self,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> str:
        if isinstance(speciality, enum.Enum):
            return f'{self._skillName} ({speciality.value})'
        if isinstance(speciality, str):
            return f'{self._skillName} ({speciality})'
        return self._skillName

    def type(self) -> SkillType:
        return self._skillType

    def isSimple(self) -> bool:
        return self._skillType == SkillDefinition.SkillType.Simple

    def isFixedSpeciality(self) -> bool:
        return self._skillType == SkillDefinition.SkillType.FixedSpeciality

    def isCustomSpeciality(self) -> bool:
        return self._skillType == SkillDefinition.SkillType.CustomSpeciality

    def fixedSpecialities(self) -> typing.Type[enum.Enum]:
        return self._fixedSpecialities

    def customSpecialities(self) -> typing.Iterable[str]:
        return self._customSpecialities

    # This class represents immutable data so there should be no need to deep
    # copy it and doing so could introduce bugs because code performs
    # comparisons with the static class instances below. I could add an
    # equality operator but, due to the fact the data its self is static, it
    # seems better to do this
    def __deepcopy__(self, memo: typing.Dict) -> 'SkillDefinition':
        return self


AdminSkillDefinition = SkillDefinition(
    skillName='Admin',
    skillType=SkillDefinition.SkillType.Simple)

AdvocateSkillDefinition = SkillDefinition(
    skillName='Advocate',
    skillType=SkillDefinition.SkillType.Simple)

class AnimalsSkillSpecialities(enum.Enum):
    Handling = 'Handling'
    Training = 'Training'
    Veterinary = 'Veterinary'


AnimalsSkillDefinition = SkillDefinition(
    skillName='Animals',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=AnimalsSkillSpecialities)

ArtSkillSpecialities = [
    'Performer',
    'Holography',
    'Instrument',
    'Visual Media',
    'Write',
]
ArtSkillDefinition = SkillDefinition(
    skillName='Art',
    skillType=SkillDefinition.SkillType.CustomSpeciality,
    customSpecialities=ArtSkillSpecialities)

AstrogationSkillDefinition = SkillDefinition(
    skillName='Astrogation',
    skillType=SkillDefinition.SkillType.Simple)

class AthleticsSkillSpecialities(enum.Enum):
    Dexterity = 'Dexterity'
    Endurance = 'Endurance'
    Strength = 'Strength'


AthleticsSkillDefinition = SkillDefinition(
    skillName='Athletics',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=AthleticsSkillSpecialities)

BrokerSkillDefinition = SkillDefinition(
    skillName='Broker',
    skillType=SkillDefinition.SkillType.Simple)

CarouseSkillDefinition = SkillDefinition(
    skillName='Carouse',
    skillType=SkillDefinition.SkillType.Simple)

DeceptionSkillDefinition = SkillDefinition(
    skillName='Deception',
    skillType=SkillDefinition.SkillType.Simple)

DiplomatSkillDefinition = SkillDefinition(
    skillName='Diplomat',
    skillType=SkillDefinition.SkillType.Simple)

class DriveSkillSpecialities(enum.Enum):
    Hovercraft = 'Hovercraft'
    Mole = 'Mole'
    Tracked = 'Tracked'
    Walker = 'Walker'
    Wheeled = 'Wheeled'


DriveSkillDefinition = SkillDefinition(
    skillName='Drive',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=DriveSkillSpecialities)

class ElectronicsSkillSpecialities(enum.Enum):
    Comms = 'Comms'
    Computers = 'Computers'
    RemoteOps = 'Remote Ops'
    Sensors = 'Sensors'


ElectronicsSkillDefinition = SkillDefinition(
    skillName='Electronics',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=ElectronicsSkillSpecialities)

class EngineerSkillSpecialities(enum.Enum):
    JDrive = 'J-Drive'
    LifeSupport = 'Life Support'
    MDrive = 'M-Drive'
    PowerPlant = 'Power Plant'


EngineerSkillDefinition = SkillDefinition(
    skillName='Engineer',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=EngineerSkillSpecialities)

ExplosivesSkillDefinition = SkillDefinition(
    skillName='Explosives',
    skillType=SkillDefinition.SkillType.Simple)

class FlyerSkillSpecialities(enum.Enum):
    Airship = 'Airship'
    Grav = 'Grav'
    Ornithopter = 'Ornithopter'
    Rotor = 'Rotor'
    Wing = 'Wing'


FlyerSkillDefinition = SkillDefinition(
    skillName='Flyer',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=FlyerSkillSpecialities)

GamblerSkillDefinition = SkillDefinition(
    skillName='Gambler',
    skillType=SkillDefinition.SkillType.Simple)

class GunCombatSkillSpecialities(enum.Enum):
    Archaic = 'Archaic'
    Energy = 'Energy'
    Slug = 'Slug'


GunCombatSkillDefinition = SkillDefinition(
    skillName='Gun Combat',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=GunCombatSkillSpecialities)

class GunnerSkillSpecialities(enum.Enum):
    Capitol = 'Capitol'
    Ortillery = 'Ortillery'
    Screen = 'Screen'
    Turret = 'Turret'


GunnerSkillDefinition = SkillDefinition(
    skillName='Gunner',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=GunnerSkillSpecialities)

class HeavyWeaponsSkillSpecialities(enum.Enum):
    Artillery = 'Artillery'
    Portable = 'Portable' # aka Man-Port
    Vehicle = 'Vehicle'


HeavyWeaponsSkillDefinition = SkillDefinition(
    skillName='Heavy Weapons',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=HeavyWeaponsSkillSpecialities)

InvestigateSkillDefinition = SkillDefinition(
    skillName='Investigate',
    skillType=SkillDefinition.SkillType.Simple)

JackOfAllTradesSkillDefinition = SkillDefinition(
    skillName='Jack of All Trades',
    skillType=SkillDefinition.SkillType.Simple)

# Taken from https://wiki.travellerrpg.com/Languages_of_Charted_Space
LanguageSkillSpecialities = [
    'Aaca',
    'Aekhu',
    'Anglic',
    'Arrghoun',
    'Bilanidin',
    'Genosha',
    'Gurviotic',
    'Gvegh',
    'Hiver Sign Language',
    'Irilitok',
    'Kadli',
    '!Kee',
    'Kehuu',
    'Klatha\'sh',
    'Logaksu',
    'Marine Battle Language',
    'Na\'ans',
    'Ovaghoun',
    'Oynprith',
    'Sagamaal',
    'Sfuizia',
    'Suedzuk',
    'Te-Zlodh',
    'Trokh',
    'Vuakedh',
    'Wawa-pakekeke-wawa'
    'Zdeti',
]
LanguageSkillDefinition = SkillDefinition(
    skillName='Language',
    skillType=SkillDefinition.SkillType.CustomSpeciality,
    customSpecialities=LanguageSkillSpecialities)

LeadershipSkillDefinition = SkillDefinition(
    skillName='Leadership',
    skillType=SkillDefinition.SkillType.Simple)

MechanicSkillDefinition = SkillDefinition(
    skillName='Mechanic',
    skillType=SkillDefinition.SkillType.Simple)

MedicSkillDefinition = SkillDefinition(
    skillName='Medic',
    skillType=SkillDefinition.SkillType.Simple)

class MeleeSkillSpecialities(enum.Enum):
    Blade = 'Blade'
    Bludgeon = 'Bludgeon'
    Natural = 'Natural'
    Unarmed = 'Unarmed'
    # Whip isn't on the character sheet (at least the one I have) but is used by
    # some of the weapons from the robot construction spreadsheet (which seem to
    # have come from the Central Supply Catalogue)
    Whip = 'Whip'


MeleeSkillDefinition = SkillDefinition(
    skillName='Melee',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=MeleeSkillSpecialities)

NavigationSkillDefinition = SkillDefinition(
    skillName='Navigation',
    skillType=SkillDefinition.SkillType.Simple)

PersuadeSkillDefinition = SkillDefinition(
    skillName='Persuade',
    skillType=SkillDefinition.SkillType.Simple)

class PilotSkillSpecialities(enum.Enum):
    CapitalShips = 'Capital Ships'
    SmallCraft = 'Small Craft'
    Spacecraft = 'Spacecraft'


PilotSkillDefinition = SkillDefinition(
    skillName='Pilot',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=PilotSkillSpecialities)

# This list is a combination of examples from p68 of the core rule book and the
# ones selectable in the robot's spreadsheet
ProfessionSkillSpecialities = [
    'Belter',
    'Biologicals',
    'Civil Engineering',
    'Construction',
    'Domestic Cleaner',
    'Domestic Servant',
    'Fabricator',
    'Hydroponics',
    'Labourer',
    'Mining',
    'Polymers',
    'Robotics'
]
ProfessionSkillDefinition = SkillDefinition(
    skillName='Profession',
    skillType=SkillDefinition.SkillType.CustomSpeciality,
    customSpecialities=ProfessionSkillSpecialities)

ReconSkillDefinition = SkillDefinition(
    skillName='Recon',
    skillType=SkillDefinition.SkillType.Simple)

# List of sciences taken from https://wiki.travellerrpg.com/Science with
# some extras added by me
ScienceSkillSpecialities = [
    'Archaeology',
    'Architecture',
    'Artificial Intelligence',
    'Astrography',
    'Astronomy',
    'Astrophysics',
    'Biochemistry', # Added by me
    'Biology',
    'Biophysics', # Added by me
    'Biotechnology',
    'Botany', # Added by me
    'Chemistry',
    'Cloning',
    'Cognitive Science',
    'Computer Technology',
    'Cosmology',
    'Cybertechnology',
    'Ecology',
    'Economics',
    'Engineering',
    'Epidemiology',
    'Ethology',
    'Ethnography',
    'Ethnology',
    'Exobiochemistry',
    'Genetic Engineering',
    'Geology', # Added by me
    'Gravitics',
    'History',
    'Information Technology',
    'Life Sciences',
    'Linguistics',
    'Materials Technology',
    'Mathematics',
    'Metempsychology',
    'Microbiology', # Added by me
    'Meteorology', # Added by me
    'Nano Science',
    'Nanotechnology',
    'Neurotechnology',
    'Oceanography', # Added by me
    'Physics',
    'Physiology',
    'Planetology', # Added by me (there is an example of this in the robot rules)
    'Pocket Universes',
    'Psionicology',
    'Psychohistory',
    'Psychology',
    'Robotics',
    'Sociology',
    'Sophontology',
    'Taxonomy',
    'Technology',
    'Taxonomy',
    'Trophics',
    'Uplift',
    'Vulcanology',
    'Xenoarchaeology',
    'Xenobiology',
    'Xenolinguistics',
    'Xenology',
    'Zoology', # Added by me
]
ScienceSkillDefinition = SkillDefinition(
    skillName='Science',
    skillType=SkillDefinition.SkillType.CustomSpeciality,
    customSpecialities=ScienceSkillSpecialities)

class SeafarerSkillSpecialities(enum.Enum):
    OceanShips = 'Ocean Ships'
    Personal = 'Personal'
    Sail = 'Sail'
    Submarine = 'Submarine'


SeafarerSkillDefinition = SkillDefinition(
    skillName='Seafarer',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=SeafarerSkillSpecialities)

StealthSkillDefinition = SkillDefinition(
    skillName='Stealth',
    skillType=SkillDefinition.SkillType.Simple)

StewardSkillDefinition = SkillDefinition(
    skillName='Steward',
    skillType=SkillDefinition.SkillType.Simple)

StreetwiseSkillDefinition = SkillDefinition(
    skillName='Streetwise',
    skillType=SkillDefinition.SkillType.Simple)

SurvivalSkillDefinition = SkillDefinition(
    skillName='Survival',
    skillType=SkillDefinition.SkillType.Simple)

class TacticsSkillSpecialities(enum.Enum):
    Military = 'Military'
    Naval = 'Naval'


TacticsSkillDefinition = SkillDefinition(
    skillName='Tactics',
    skillType=SkillDefinition.SkillType.FixedSpeciality,
    fixedSpecialities=TacticsSkillSpecialities)

VaccSuitSkillDefinition = SkillDefinition(
    skillName='Vacc Suit',
    skillType=SkillDefinition.SkillType.Simple)

# NOTE: This list shouldn't be used as custom construction type specific skills
# can be defined. I've commented it out rather than delete it as it's the best
# way I can see to prevent myself thinking it's a good idea in the future
"""
AllStandardSkills = [
    AdminSkillDefinition,
    AdvocateSkillDefinition,
    AnimalsSkillDefinition,
    ArtSkillDefinition,
    AstrogationSkillDefinition,
    AthleticsSkillDefinition,
    BrokerSkillDefinition,
    CarouseSkillDefinition,
    DeceptionSkillDefinition,
    DiplomatSkillDefinition,
    DriveSkillDefinition,
    ElectronicsSkillDefinition,
    EngineerSkillDefinition,
    ExplosivesSkillDefinition,
    FlyerSkillDefinition,
    GamblerSkillDefinition,
    GunCombatSkillDefinition,
    GunnerSkillDefinition,
    HeavyWeaponsSkillDefinition,
    InvestigateSkillDefinition,
    JackOfAllTradesSkillDefinition,
    LanguageSkillDefinition,
    LeadershipSkillDefinition,
    MechanicSkillDefinition,
    MedicSkillDefinition,
    MeleeSkillDefinition,
    NavigationSkillDefinition,
    PersuadeSkillDefinition,
    PilotSkillDefinition,
    ProfessionSkillDefinition,
    ReconSkillDefinition,
    ScienceSkillDefinition,
    SeafarerSkillDefinition,
    StealthSkillDefinition,
    StewardSkillDefinition,
    StreetwiseSkillDefinition,
    SurvivalSkillDefinition,
    TacticsSkillDefinition
]
"""
