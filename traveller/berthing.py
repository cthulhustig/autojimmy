import common
import traveller
import typing

# Berthing costs are the same for Mongoose 1e (p178), 2e (p225) & 2022 (p257)
_StarPortBerthingCostScale = {
    'A': common.ScalarCalculation(value=1000, name='A Class Star Port Berthing Scale'),
    'B': common.ScalarCalculation(value=500, name='B Class Star Port Berthing Scale'),
    'C': common.ScalarCalculation(value=100, name='C Class Star Port Berthing Scale'),
    'D': common.ScalarCalculation(value=10, name='D Class Star Port Berthing Scale'),
}

# The MGT2 rules aren't clear on what time range the berthing costs on p225 of the rules are
# over. For now I'm leaving it up to the consuming code to decide what it does with the value.
def starPortBerthingCost(
        world: traveller.World,
        diceRoller: typing.Optional[common.DiceRoller] = None
        ) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
    starPortCode = world.uwp().code(traveller.UWP.Element.StarPort)
    if starPortCode in _StarPortBerthingCostScale:
        if diceRoller:
            diceRoll = diceRoller.makeRoll(
                dieCount=1,
                name=f'Start Port Berthing Cost Roll For {world.name(includeSubsector=True)}')
        else:
            # We're not rolling dice so use the probability range for the dice roll.
            # We round the value up to be pessimistic. Note that the worst and best
            # case dice rolls are swap as in this situation it's better to roll low
            diceRoll = common.Calculator.ceil(
                value=common.calculateValueRangeForDice(
                    dieCount=1,
                    higherIsBetter=False))
        berthingCost = common.Calculator.multiply(
            lhs=diceRoll,
            rhs=_StarPortBerthingCostScale[starPortCode],
            name='Berthing Cost')
    else:
        berthingCost = common.ScalarCalculation(
            value=0,
            name='Berthing Cost')
    return berthingCost
