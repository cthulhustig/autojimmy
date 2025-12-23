import astronomer
import common
import traveller
import typing

# Fuel costs are the same for Mongoose 1e (p140), 2e (p226) & 2022 (p154)
RefinedFuelCostPerTon = common.ScalarCalculation(
    value=500,
    name='Refined Fuel Cost Per Ton')
UnrefinedFuelCostPerTon = common.ScalarCalculation(
    value=100,
    name='Unrefined Fuel Cost Per Ton')
WildernessFuelCostPerTon = common.ScalarCalculation(
    value=0,
    name='Wilderness Fuel Cost Per Ton')

# I can't find anything in the Mongoose 2e rules the explicitly states how you calculate how much
# fuel a ship requires to make a jump of a given distance (I suspect I'm not looking hard enough).
# Going by the example ships it's calculated as 10% of the ships tonnage multiplied by the jump
# distance (see Far Trader example on p166).
def calculateFuelRequiredForJump(
        jumpDistance: typing.Union[int, common.ScalarCalculation],
        shipTonnage: typing.Union[int, common.ScalarCalculation]
        ) -> common.ScalarCalculation:
    if not isinstance(jumpDistance, common.ScalarCalculation):
        assert(isinstance(jumpDistance, int))
        jumpDistance = common.ScalarCalculation(
            value=jumpDistance,
            name='Jump Parsecs')

    if not isinstance(shipTonnage, common.ScalarCalculation):
        assert(isinstance(shipTonnage, int))
        shipTonnage = common.ScalarCalculation(
            value=shipTonnage,
            name='Ship Tonnage')

    calculation = common.Calculator.multiply(
        lhs=shipTonnage,
        rhs=common.ScalarCalculation(value=0.1))
    calculation = common.Calculator.multiply(
        lhs=calculation,
        rhs=jumpDistance)
    calculation = common.Calculator.ceil(
        value=calculation,
        name='Jump Fuel')
    assert(isinstance(calculation, common.ScalarCalculation))
    return calculation

def worldHasStarPortRefuelling(
        world: astronomer.World,
        rules: traveller.Rules,
        includeRefined: bool = True,
        includeUnrefined: bool = True
        ) -> bool:
    uwp = world.uwp()
    starPortFuelType = rules.starPortFuelType(
        code=uwp.code(astronomer.UWP.Element.StarPort))

    if starPortFuelType is traveller.StarPortFuelType.AllTypes:
        return includeRefined or includeUnrefined
    elif starPortFuelType is traveller.StarPortFuelType.RefinedOnly:
        return includeRefined
    elif starPortFuelType is traveller.StarPortFuelType.UnrefinedOnly:
        return includeUnrefined

    return False

def worldHasGasGiantRefuelling(world: astronomer.World) -> bool:
    numberOfGasGiants = world.numberOfGasGiants()
    return numberOfGasGiants is not None and numberOfGasGiants > 0

# This method of detecting if the system has water is based on Traveller Maps (WaterPresent in
# World.cs). I've added the check for the water world trade code as it gives a quick out.
# There are a couple of things i'm not entirely convinced by about the Traveller Map algorithm
# but i've gone with them anyway for consistency
# - It counts anything with a hydrographics > 0 as having water. My concern is that this could be
# as low as 6% water, such a low parentage could cause issues if you're trying to do water refuelling
# - It includes worlds with atmosphere code 15. This is 'Unusual (Varies)' which doesn't sound like
# it would guarantee accessible water for refuelling
def worldHasWaterRefuelling(world: astronomer.World) -> bool:
    if world.hasTradeCode(astronomer.TradeCode.WaterWorld):
        return True

    uwp = world.uwp()
    try:
        hydrographics = astronomer.ehexToInteger(
            value=uwp.code(astronomer.UWP.Element.Hydrographics),
            default=-1)
        atmosphere = astronomer.ehexToInteger(
            value=uwp.code(astronomer.UWP.Element.Atmosphere),
            default=-1)
    except ValueError:
        return False

    return (hydrographics > 0) and ((2 <= atmosphere <= 9) or (13 <= atmosphere <= 15))

def worldHasWildernessRefuelling(world: astronomer.World) -> bool:
    return worldHasGasGiantRefuelling(world=world) or \
        worldHasWaterRefuelling(world=world)

def worldHasRefuelling(
        world: astronomer.World,
        rules: traveller.Rules
        ) -> bool:
    return worldHasWildernessRefuelling(world=world) or \
        worldHasStarPortRefuelling(world=world, rules=rules) or \
        world.isFuelCache()
