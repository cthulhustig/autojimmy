import enum
import multiverse
import typing

# Descriptions in these mappings are taken from the 2e core rules, https://travellermap.com/doc/secondsurvey
# and https://travellertools.azurewebsites.net/.


#  █████████   █████                           ███████████                      █████
# ███░░░░░███ ░░███                           ░░███░░░░░███                    ░░███
#░███    ░░░  ███████    ██████   ████████     ░███    ░███  ██████  ████████  ███████
#░░█████████ ░░░███░    ░░░░░███ ░░███░░███    ░██████████  ███░░███░░███░░███░░░███░
# ░░░░░░░░███  ░███      ███████  ░███ ░░░     ░███░░░░░░  ░███ ░███ ░███ ░░░   ░███
# ███    ░███  ░███ ███ ███░░███  ░███         ░███        ░███ ░███ ░███       ░███ ███
#░░█████████   ░░█████ ░░████████ █████        █████       ░░██████  █████      ░░█████
# ░░░░░░░░░     ░░░░░   ░░░░░░░░ ░░░░░        ░░░░░         ░░░░░░  ░░░░░        ░░░░░

_StarPortStringMap = {
    'A': 'Excellent Star Port - Refined fuel, Shipyard (all), Repairs',
    'B': 'Good Star Port - Refined fuel, Shipyard (spacecraft), Repairs',
    'C': 'Routine Star Port- Unrefined fuel, Shipyard (small craft), Repairs',
    'D': 'Poor Star Port - Unrefined fuel, No Shipyard, Limited Repairs',
    'E': 'Frontier Star Port - No fuel, No Shipyard, No Repairs',
    'F': 'Good Space Port', # This was taken from the Traveller Map source code (world_utils.js)
    'G': 'Poor Space Port', # This was taken from the Traveller Map source code (world_utils.js)
    'H': 'Primitive Space Port', # This was taken from the Traveller Map source code (world_utils.js)
    'X': 'No Star Port',
    'Y': 'No Space Port', # This was taken from the Traveller Map source code (world_utils.js)
    '?': 'Unknown'
}

# █████   ███   █████                    ████      █████     █████████   ███
#░░███   ░███  ░░███                    ░░███     ░░███     ███░░░░░███ ░░░
# ░███   ░███   ░███   ██████  ████████  ░███   ███████    ░███    ░░░  ████   █████████  ██████
# ░███   ░███   ░███  ███░░███░░███░░███ ░███  ███░░███    ░░█████████ ░░███  ░█░░░░███  ███░░███
# ░░███  █████  ███  ░███ ░███ ░███ ░░░  ░███ ░███ ░███     ░░░░░░░░███ ░███  ░   ███░  ░███████
#  ░░░█████░█████░   ░███ ░███ ░███      ░███ ░███ ░███     ███    ░███ ░███    ███░   █░███░░░
#    ░░███ ░░███     ░░██████  █████     █████░░████████   ░░█████████  █████  █████████░░██████
#     ░░░   ░░░       ░░░░░░  ░░░░░     ░░░░░  ░░░░░░░░     ░░░░░░░░░  ░░░░░  ░░░░░░░░░  ░░░░░░

# The source of these values is a bit convoluted. The diameter and gravity
# values come from world_util.js in the Traveller Map repo. However I don't know
# what where the masses used to calculate the gravity values came from. The
# gravity values are also different to https://travellermap.com/doc/secondsurvey.
# As world_util.js doesn't have escape velocity values and the ones on
# https://travellermap.com/doc/secondsurvey appear to be innacurate. I used this
# link to calculate the mass from the gravity and diameter values, doing this
# also gives the escape velocity values.
# https://www.wolframalpha.com/input?i=surface+gravity+calculator
#
# I've not included the mass in the description as I don't think it's would
# really be of intereast to anyone. These were the masses calculated, I've
# converted them from kg to earths (i.e. multiples of 12800km)
# 1 = 0.0019, 2 = 0.0156, 3 = 0.0534, 4 = 0.1250,
# 5 = 0.2461, 6 = 0.4218, 7 = 0.6737, 8 = 1.0000,
# 9 = 1.4173, A = 1.9522, B = 2.6084, C = 3.3743
# D = 4.3047, E = 5.3597, F = 7.0311
_WorldSizeStringMap = {
    '0': 'Asteroid belt',
    '1': 'Diameter 1600km, Gravity 0.12g, Escape Velocity 1.37km/s',
    '2': 'Diameter 3200km, Gravity 0.25g, Escape Velocity 2.80km/s',
    '3': 'Diameter 4800km, Gravity 0.38g, Escape Velocity 4.23km/s',
    '4': 'Diameter 6400km, Gravity 0.50g, Escape Velocity 5.60km/s',
    '5': 'Diameter 8000km, Gravity 0.63g, Escape Velocity 7.03km/s',
    '6': 'Diameter 9600km, Gravity 0.75g, Escape Velocity 8.40km/s',
    '7': 'Diameter 11200km, Gravity 0.88g, Escape Velocity 9.83km/s',
    '8': 'Diameter 12800km, Gravity 1.00g, Escape Velocity 11.20km/s',
    '9': 'Diameter 14400km, Gravity 1.12g, Escape Velocity 12.58km/s',
    'A': 'Diameter 16000km, Gravity 1.25g, Escape Velocity 14.00km/s',
    'B': 'Diameter 17600km, Gravity 1.38g, Escape Velocity 15.43km/s',
    'C': 'Diameter 19200km, Gravity 1.50g, Escape Velocity 16.81km/s',
    'D': 'Diameter 20800km, Gravity 1.63g, Escape Velocity 18.23km/s',
    'E': 'Diameter 22400km, Gravity 1.75g, Escape Velocity 19.61km/s',
    'F': 'Diameter 24000km, Gravity 2.00g, Escape Velocity 21.70km/s',
    '?': 'Unknown'
}

#   █████████    █████                                               █████
#  ███░░░░░███  ░░███                                               ░░███
# ░███    ░███  ███████   █████████████    ██████   █████  ████████  ░███████    ██████  ████████   ██████
# ░███████████ ░░░███░   ░░███░░███░░███  ███░░███ ███░░  ░░███░░███ ░███░░███  ███░░███░░███░░███ ███░░███
# ░███░░░░░███   ░███     ░███ ░███ ░███ ░███ ░███░░█████  ░███ ░███ ░███ ░███ ░███████  ░███ ░░░ ░███████
# ░███    ░███   ░███ ███ ░███ ░███ ░███ ░███ ░███ ░░░░███ ░███ ░███ ░███ ░███ ░███░░░   ░███     ░███░░░
# █████   █████  ░░█████  █████░███ █████░░██████  ██████  ░███████  ████ █████░░██████  █████    ░░██████
#░░░░░   ░░░░░    ░░░░░  ░░░░░ ░░░ ░░░░░  ░░░░░░  ░░░░░░   ░███░░░  ░░░░ ░░░░░  ░░░░░░  ░░░░░      ░░░░░░
#                                                          ░███
#                                                          █████
#                                                         ░░░░░
_AtmosphereStringMap = {
    '0': 'Vacuum - Requires vacc suit',
    '1': 'Trace - Requires vacc suit',
    '2': 'Very Thin (Tainted) - Requires respirator & filter',
    '3': 'Very Thin - Requires respirator',
    '4': 'Thin (Tainted) - Requires filter',
    '5': 'Thin - Breathable',
    '6': 'Standard - Breathable',
    '7': 'Standard (Tainted) - Requires filter',
    '8': 'Dense - Breathable',
    '9': 'Dense (Tainted) - Requires filter',
    'A': 'Exotic - Requires air supply',
    'B': 'Corrosive - Requires vacc suit',
    'C': 'Insidious - Requires vacc suit',
    'D': 'Dense (High) - Breathable above a minimum altitude',
    'E': 'Thin (Low) - Breathable below certain altitudes',
    'F': 'Unusual - Breathability varies',
    '?': 'Unknown'
}

# █████   █████                █████                                                           █████       ███
#░░███   ░░███                ░░███                                                           ░░███       ░░░
# ░███    ░███  █████ ████  ███████  ████████   ██████   ███████ ████████   ██████   ████████  ░███████   ████   ██████   █████
# ░███████████ ░░███ ░███  ███░░███ ░░███░░███ ███░░███ ███░░███░░███░░███ ░░░░░███ ░░███░░███ ░███░░███ ░░███  ███░░███ ███░░
# ░███░░░░░███  ░███ ░███ ░███ ░███  ░███ ░░░ ░███ ░███░███ ░███ ░███ ░░░   ███████  ░███ ░███ ░███ ░███  ░███ ░███ ░░░ ░░█████
# ░███    ░███  ░███ ░███ ░███ ░███  ░███     ░███ ░███░███ ░███ ░███      ███░░███  ░███ ░███ ░███ ░███  ░███ ░███  ███ ░░░░███
# █████   █████ ░░███████ ░░████████ █████    ░░██████ ░░███████ █████    ░░████████ ░███████  ████ █████ █████░░██████  ██████
#░░░░░   ░░░░░   ░░░░░███  ░░░░░░░░ ░░░░░      ░░░░░░   ░░░░░███░░░░░      ░░░░░░░░  ░███░░░  ░░░░ ░░░░░ ░░░░░  ░░░░░░  ░░░░░░
#                ███ ░███                               ███ ░███                     ░███
#               ░░██████                               ░░██████                      █████
#                ░░░░░░                                 ░░░░░░                      ░░░░░
_HydrographicsStringMap = {
    '0': '0-5% Water',
    '1': '6-15% Water',
    '2': '16-25% Water',
    '3': '25-35% Water',
    '4': '36-45% Water',
    '5': '46-55% Water',
    '6': '56-65% Water',
    '7': '66-75% Water',
    '8': '76-85% Water',
    '9': '86-95% Water',
    'A': '96-100% Water',
    '?': 'Unknown'
}

# ███████████                                ████             █████     ███
#░░███░░░░░███                              ░░███            ░░███     ░░░
# ░███    ░███  ██████  ████████  █████ ████ ░███   ██████   ███████   ████   ██████  ████████
# ░██████████  ███░░███░░███░░███░░███ ░███  ░███  ░░░░░███ ░░░███░   ░░███  ███░░███░░███░░███
# ░███░░░░░░  ░███ ░███ ░███ ░███ ░███ ░███  ░███   ███████   ░███     ░███ ░███ ░███ ░███ ░███
# ░███        ░███ ░███ ░███ ░███ ░███ ░███  ░███  ███░░███   ░███ ███ ░███ ░███ ░███ ░███ ░███
# █████       ░░██████  ░███████  ░░████████ █████░░████████  ░░█████  █████░░██████  ████ █████
#░░░░░         ░░░░░░   ░███░░░    ░░░░░░░░ ░░░░░  ░░░░░░░░    ░░░░░  ░░░░░  ░░░░░░  ░░░░ ░░░░░
#                       ░███
#                       █████
#                      ░░░░░
_PopulationStringMap = {
    '0': 'Unpopulated',
    '1': 'Tens',
    '2': 'Hundreds',
    '3': 'Thousands',
    '4': 'Tens of thousands',
    '5': 'Hundreds of thousands',
    '6': 'Millions',
    '7': 'Tens of millions',
    '8': 'Hundreds of millions',
    '9': 'Billions',
    'A': 'Tens of billions',
    'B': 'Hundreds of billions',
    'C': 'Trillions',
    'D': 'Tens of trillions',
    'E': 'Hundreds of trillions',
    'F': 'Quadrillions',
    '?': 'Unknown'
}

#   █████████                                                                                          █████
#  ███░░░░░███                                                                                        ░░███
# ███     ░░░   ██████  █████ █████  ██████  ████████  ████████   █████████████    ██████  ████████   ███████
#░███          ███░░███░░███ ░░███  ███░░███░░███░░███░░███░░███ ░░███░░███░░███  ███░░███░░███░░███ ░░░███░
#░███    █████░███ ░███ ░███  ░███ ░███████  ░███ ░░░  ░███ ░███  ░███ ░███ ░███ ░███████  ░███ ░███   ░███
#░░███  ░░███ ░███ ░███ ░░███ ███  ░███░░░   ░███      ░███ ░███  ░███ ░███ ░███ ░███░░░   ░███ ░███   ░███ ███
# ░░█████████ ░░██████   ░░█████   ░░██████  █████     ████ █████ █████░███ █████░░██████  ████ █████  ░░█████
#  ░░░░░░░░░   ░░░░░░     ░░░░░     ░░░░░░  ░░░░░     ░░░░ ░░░░░ ░░░░░ ░░░ ░░░░░  ░░░░░░  ░░░░ ░░░░░    ░░░░░
# Note these strings aren't valid for Worlds in the Wilds
# see https://travellermap.com/doc/secondsurvey
_GovernmentStringMap = {
    '0': 'None',
    '1': 'Company/Corporation',
    '2': 'Participatory Democracy',
    '3': 'Self-Perpetuating Oligarchy',
    '4': 'Representative Democracy',
    '5': 'Feudal Technocracy',
    '6': 'Captive Government',
    '7': 'Balkanized',
    '8': 'Civil Service Bureaucracy',
    '9': 'Impersonal Bureaucracy',
    'A': 'Charismatic Dictator',
    'B': 'Non-Charismatic Dictator',
    'C': 'Charismatic Oligarchy',
    'D': 'Religious Dictatorship',
    'E': 'Religious Autocracy',
    'F': 'Totalitarian Oligarchy',
    'G': 'Small Station or Facility (Aslan)',
    'H': 'Split Clan Control (Aslan)',
    'J': 'Single On-world Clan Control (Aslan)',
    'K': 'Single Multi-world Clan Control (Aslan)',
    'L': 'Major Clan Control (Aslan)',
    'M': 'Vassal Clan Control (Aslan)',
    'N': 'Major Vassal Clan Control (Aslan)',
    'P': 'Small Station or Facility (K\'kree)',
    'Q': 'Krurruna or Krumanak Rule for Off-world Steppelord (K\'kree)',
    'R': 'Steppelord On-world Rule (K\'kree)',
    'S': 'Sept (Hiver)',
    'T': 'Unsupervised Anarchy (Hiver)',
    'U': 'Supervised Anarchy (Hiver)',
    'W': 'Committee (Hiver)',
    'X': 'Droyne Hierarchy (Droyne)', # This is different to Traveller Map which has Unknown (world_utils.js)
    '?': 'Unknown'
}

# █████                                    █████                                     ████
#░░███                                    ░░███                                     ░░███
# ░███         ██████   █████ ███ █████    ░███         ██████  █████ █████  ██████  ░███
# ░███        ░░░░░███ ░░███ ░███░░███     ░███        ███░░███░░███ ░░███  ███░░███ ░███
# ░███         ███████  ░███ ░███ ░███     ░███       ░███████  ░███  ░███ ░███████  ░███
# ░███      █ ███░░███  ░░███████████      ░███      █░███░░░   ░░███ ███  ░███░░░   ░███
# ███████████░░████████  ░░████░████       ███████████░░██████   ░░█████   ░░██████  █████
#░░░░░░░░░░░  ░░░░░░░░    ░░░░ ░░░░       ░░░░░░░░░░░  ░░░░░░     ░░░░░     ░░░░░░  ░░░░░
_LawLevelStringMap = {
    '0': 'Lawless. All weapons allowed (and probably recommended). Candidate for Amber Zone status.',
    '1': 'Poison gas, explosives, undetectable weapons, weapons of mass destruction and battle dress are prohibited.',
    '2': 'Portable energy and laser weapons and combat armour are prohibited.',
    '3': 'Military Weapons and flack armour are prohibited.',
    '4': 'Light assault weapons, submachine guns and cloth armour are prohibited.',
    '5': 'Personal concealed weapons and cloth armour are prohibited.',
    '6': 'All firearms except for shotguns and stunners and mesh armour are prohibited. Carrying weapons is discouraged.',
    '7': 'Shotguns are prohibited.',
    '8': 'Bladed weapons, stunners and all visible armour are prohibited.',
    '9': 'All weapons or armour are prohibited. Candidate for Amber Zone status.',
    'A': 'Highly restrictive government. All weapons forbidden. Candidate for Amber Zone status.',
    'B': 'Rigid control of civilian movement.',
    'C': 'Unrestricted invasion of privacy.',
    'D': 'Paramilitary law enforcement.',
    'E': 'Full-fledged police state.',
    'F': 'All facets of daily life rigidly controlled.',
    'G': 'Severe punishment for petty infractions.',
    'H': 'Legalized oppressive practices.',
    'J': 'Routinely oppressive and restrictive.',
    'K': 'Excessively oppressive and restrictive.',
    'L': 'Totally oppressive and restrictive.',
    'S': 'Special/Variable situation.',
    '?': 'Unknown'
}

# ███████████                   █████         █████                                     ████
#░█░░░███░░░█                  ░░███         ░░███                                     ░░███
#░   ░███  ░   ██████   ██████  ░███████      ░███         ██████  █████ █████  ██████  ░███
#    ░███     ███░░███ ███░░███ ░███░░███     ░███        ███░░███░░███ ░░███  ███░░███ ░███
#    ░███    ░███████ ░███ ░░░  ░███ ░███     ░███       ░███████  ░███  ░███ ░███████  ░███
#    ░███    ░███░░░  ░███  ███ ░███ ░███     ░███      █░███░░░   ░░███ ███  ░███░░░   ░███
#    █████   ░░██████ ░░██████  ████ █████    ███████████░░██████   ░░█████   ░░██████  █████
#   ░░░░░     ░░░░░░   ░░░░░░  ░░░░ ░░░░░    ░░░░░░░░░░░  ░░░░░░     ░░░░░     ░░░░░░  ░░░░░
_TechLevelStringMap = {
    '0': 'Stone Age. Primitive.',
    '1': 'Bronze, Iron. Bronze Age to Middle Ages',
    '2': 'Printing Press. circa 1400 to 1700.',
    '3': 'Basic Science. circa 1700 to 1860.',
    '4': 'External Combustion. circa 1860 to 1900.',
    '5': 'Mass Production. circa 1900 to 1939.',
    '6': 'Nuclear Power. circa 1940 to 1969.',
    '7': 'Miniaturized Electronics. circa 1970 to 1979.',
    '8': 'Quality Computers. circa 1980 to 1989.',
    '9': 'Anti-Gravity. circa 1990 to 2000.',
    'A': 'Interstellar community.',
    'B': 'Lower Average Imperial.',
    'C': 'Average Imperial.',
    'D': 'Above Average Imperial.',
    'E': 'Above Average Imperial.',
    'F': 'Technical Imperial Maximum.',
    'G': 'Robots.',
    'H': 'Artificial Intelligence.',
    'J': 'Personal Disintegrators.',
    'K': 'Plastic Metals.',
    'L': 'Comprehensible only as technological magic.',
    '?': 'Unknown'
}

class UWP(object):
    class Element(enum.Enum):
        # Enum values are the index into the UWP string
        StarPort = 0
        WorldSize = 1
        Atmosphere = 2
        Hydrographics = 3
        Population = 4
        Government = 5
        LawLevel = 6
        TechLevel = 8

    _elementDescriptionMaps: typing.List[typing.Mapping[str, str]] = [
        _StarPortStringMap,
        _WorldSizeStringMap,
        _AtmosphereStringMap,
        _HydrographicsStringMap,
        _PopulationStringMap,
        _GovernmentStringMap,
        _LawLevelStringMap,
        None, # This accounts for the '-' in the UWP string
        _TechLevelStringMap
    ]

    def __init__(
            self,
            string: str
            ) -> None:
        self._string = string
        self._sanitised = self._sanitise(self._string)

    def string(self) -> str:
        return self._string

    def sanitised(self) -> str:
        return self._sanitised

    def code(
            self,
            element: Element
            ) -> str:
        return self._sanitised[element.value]

    def numeric(
            self,
            element: Element,
            default: int = -1
            ) -> int:
        code = self.code(element=element)
        return multiverse.ehexToInteger(code, default)

    def description(
            self,
            element: Element
            ) -> str:
        return UWP._elementDescriptionMaps[element.value][self.code(element)]

    @staticmethod
    def codeList(element: Element) -> typing.Iterable[str]:
        return UWP._elementDescriptionMaps[element.value].keys()

    @staticmethod
    def descriptionMap(element: Element) -> typing.Mapping[str, str]:
        return UWP._elementDescriptionMaps[element.value]

    @staticmethod
    def _sanitise(uwp: str) -> str:
        sanitized = ''

        # Check for worlds where the UWP is all X and replace it with all ?. This is important to
        # stop the star port and government values (which have valid mappings for X) from being
        # miss-detected
        if uwp == 'XXXXXXX-X':
            return '???????-?'

        for index in range(9):
            if index != 7:
                sanitized += UWP._sanitiseElement(index, uwp)
            else:
                sanitized += '-'
        return sanitized

    @staticmethod
    def _sanitiseElement(index: int, uwp: str) -> str:
        if index >= len(uwp):
            return '?'
        code = uwp[index].upper()
        if code not in UWP._elementDescriptionMaps[index]:
            return '?'
        return code
