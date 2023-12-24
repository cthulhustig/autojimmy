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
# Fuel Caches are worlds that have the {Fuel} remark. From looking at the map
# data, the only place the remark is used in VoidBridges and Pirian Domain Fuel
# Factories. From the description of both the fuel is provided free
# https://www.wiki.travellerrpg.com/VoidBridges
# https://www.wiki.travellerrpg.com/Pirian_Domain_Fuel_Factories
FuelCacheFuelCostPerTon = common.ScalarCalculation(
    value=0,
    name='Fuel Cache Fuel Cost Per Ton')

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
