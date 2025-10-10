import enum
import typing

# NOTE: If I ever change the names of these enums I'll need to add some kind of
# mapping to CargoRecord serialization/deserialization as the names are store
# in the file files
class RuleSystem(enum.Enum):
    MGT = 'Mongoose Traveller'
    MGT2 = 'Mongoose Traveller 2e'
    MGT2022 = 'Mongoose Traveller Update 2022'

class StarPortFuelType(enum.Enum):
    AllTypes = 'All Types'
    RefinedOnly = 'Refined Only'
    UnrefinedOnly = 'Unrefined Only'
    NoFuel = 'No Fuel'

class Rules(object):
    @typing.overload
    def __init__(
        self,
        system: RuleSystem,
        classAStarPortFuelType: StarPortFuelType = StarPortFuelType.AllTypes,
        classBStarPortFuelType: StarPortFuelType = StarPortFuelType.AllTypes,
        classCStarPortFuelType: StarPortFuelType = StarPortFuelType.UnrefinedOnly,
        classDStarPortFuelType: StarPortFuelType = StarPortFuelType.UnrefinedOnly,
        classEStarPortFuelType: StarPortFuelType = StarPortFuelType.NoFuel,
        ) -> None: ...

    @typing.overload
    def __init__(self, other: 'Rules' ) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, Rules):
                raise TypeError('The other parameter must be an Rules')
            self._system = other._system
            self._starPortFuelTypes = dict(other._starPortFuelTypes)
        else:
            self._system = args[0] if len(args) > 0 else kwargs['system']
            self._starPortFuelTypes = {
                'A': args[1] if len(args) > 1 else kwargs.get('classAStarPortFuelType', StarPortFuelType.AllTypes),
                'B': args[2] if len(args) > 2 else kwargs.get('classBStarPortFuelType', StarPortFuelType.AllTypes),
                'C': args[3] if len(args) > 3 else kwargs.get('classCStarPortFuelType', StarPortFuelType.UnrefinedOnly),
                'D': args[4] if len(args) > 4 else kwargs.get('classDStarPortFuelType', StarPortFuelType.UnrefinedOnly),
                'E': args[5] if len(args) > 5 else kwargs.get('classEStarPortFuelType', StarPortFuelType.NoFuel)}

    def system(self) -> RuleSystem:
        return self._system

    # The Mongoose rules as written seem a little strange as they say that class
    # A & B star ports have refined fuel but doesn't mention unrefined fuel,
    # this is the case for 1e, 2e & 2022. This seems odd as you would expect
    # there would be a market for ships that can't or don't want to take the time
    # for wilderness refuelling (e.g. systems with limited water and distant gas
    # giants).
    # The 2e Travellers Companion (p125) clarifies some things but makes other
    # less clear. In it's description of class A star ports it says they sell
    # refined and unrefined fuel. However, it makes no mention of fuel in the
    # description of class B star ports but does say class C star ports usually
    # sell refined and unrefined fuel.
    # The T5 Core rules (p267) explicitly say A & B starports have refined and
    # unrefined fuel available.
    # The Classic Traveller rules are interesting. In the description of A/B
    # star ports (p84) it says "refined fuel available", but if you take also
    # factor in the wording for C/D class star ports where it says "only unrefined
    # fuel available", that could be taken to imply that unrefined fuel is also
    # available at A/B star ports. This seems to be further backed up by the fact
    # the example adventure it contains it says Alell Down Starport is B class and
    # sells refined and unrefined fuel (p141).
    # Personally I think the Mongoose rules were meant to have A/B star ports sell
    # both types but the subtlety in the CT rules was lost when the moved the
    # information to a table. The Travellers Companion was meant to clarify this
    # but a mistake was made and the description for class C star ports was updated
    # rather than the description of class B.
    # https://forum.mongoosepublishing.com/threads/refined-fuel.123497/
    def starPortFuelType(
            self,
            code: str
            ) -> typing.Optional[StarPortFuelType]:
        return self._starPortFuelTypes.get(code)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rules):
            return False
        return self._system == other._system and \
            self._starPortFuelTypes == other._starPortFuelTypes
