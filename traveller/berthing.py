import common
import traveller
import typing

# Berthing costs are the same for Mongoose 1e (p178), 2e (p225) & 2022 (p257)
# Note that E class star ports have an entry as, even though the cost is 0,
# there is still a star port to berth at. This is conceptually different to
# there is no star port where there is no berthing
_StarPortBerthingCostScale = {
    'A': common.ScalarCalculation(value=1000, name='A Class Star Port Berthing Scale'),
    'B': common.ScalarCalculation(value=500, name='B Class Star Port Berthing Scale'),
    'C': common.ScalarCalculation(value=100, name='C Class Star Port Berthing Scale'),
    'D': common.ScalarCalculation(value=10, name='D Class Star Port Berthing Scale'),
    'E': common.ScalarCalculation(value=0, name='E Class Star Port Berthing Scale'),
}

# Fuel Caches are worlds that have the {Fuel} remark. From looking at the map
# data, the only place the remark is used in VoidBridges and Pirian Domain Fuel
# Factories. I'm working on the assumption that you have to berth in order to
# refuel, however, berthing doesn't cost anything as that would be weird when
# the fuel is free.
# https://www.wiki.travellerrpg.com/VoidBridges
# https://www.wiki.travellerrpg.com/Pirian_Domain_Fuel_Factories
_FuelCacheBerthingCost = common.ScalarCalculation(
    value=0,
    name='Fuel Cache Berthing Cost')

# The MGT2 rules aren't clear on what time range the berthing costs on p225 of the rules are
# over. For now I'm leaving it up to the consuming code to decide what it does with the value.
def calculateBerthingCost(
        world: traveller.World,
        diceRoller: typing.Optional[common.DiceRoller] = None
        ) -> typing.Optional[typing.Union[
            common.ScalarCalculation,
            common.RangeCalculation]]:
    if world.isFuelCache():
        return _FuelCacheBerthingCost

    starPortCode = world.uwp().code(traveller.UWP.Element.StarPort)
    berthingScale = _StarPortBerthingCostScale.get(starPortCode)
    if not berthingScale:
        return None

    if diceRoller:
        diceRoll = diceRoller.makeRoll(
            dieCount=1,
            name=f'Start Port Berthing Cost Roll For {world.name(includeSubsector=True)}')
    else:
        # We're not rolling dice so use the probability range for the dice
        # roll. We round the value up to be pessimistic. Note that the worst
        # and best case dice rolls are swapped as in this situation it's
        # better to roll low
        diceRoll = common.Calculator.ceil(
            value=common.calculateValueRangeForDice(
                dieCount=1,
                higherIsBetter=False))

    return common.Calculator.multiply(
        lhs=diceRoll,
        rhs=berthingScale,
        name='Berthing Cost')
