import common
import logic
import traveller
import typing

class RouteLogistics(object):
    def __init__(
            self,
            jumpRoute: logic.JumpRoute,
            refuellingPlan: typing.Optional[logic.RefuellingPlan],
            perJumpOverheads: typing.Optional[typing.Union[int, common.ScalarCalculation]]
            ) -> None:
        if not jumpRoute:
            raise ValueError('Invalid jump route')

        if perJumpOverheads and not isinstance(perJumpOverheads, common.ScalarCalculation):
            assert(isinstance(perJumpOverheads, int))
            perJumpOverheads = common.ScalarCalculation(
                value=perJumpOverheads,
                name='Per Jump Overheads')

        self._jumpRoute = jumpRoute
        self._refuellingPlan = refuellingPlan

        self._totalOverheads = None
        if perJumpOverheads:
            jumpCount = common.ScalarCalculation(
                value=self._jumpRoute.jumpCount(),
                name='Jump Count')

            self._totalOverheads = common.Calculator.multiply(
                lhs=perJumpOverheads,
                rhs=jumpCount,
                name='Total Overheads')

    def startWorld(self) -> traveller.World:
        return self._jumpRoute.startWorld()

    def finishWorld(self) -> traveller.World:
        return self._jumpRoute.finishWorld()

    def jumpCount(self) -> int:
        return self._jumpRoute.jumpCount()

    def totalParsecs(self) -> int:
        return self._jumpRoute.totalParsecs()

    def jumpRoute(self) -> logic.JumpRoute:
        return self._jumpRoute

    def refuellingPlan(self) -> typing.Optional[logic.RefuellingPlan]:
        return self._refuellingPlan

    def totalOverheads(self) -> typing.Optional[typing.Union[common.ScalarCalculation, common.RangeCalculation]]:
        return self._totalOverheads

    def totalCosts(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        costs = []

        if self._refuellingPlan:
            costs.append(self._refuellingPlan.totalPitStopCosts())
        if self._totalOverheads:
            costs.append(self._totalOverheads)

        return common.Calculator.sum(
            values=costs,
            name='Total Logistics Cost')

def calculateRouteLogistics(
        jumpRoute: logic.JumpRoute,
        shipTonnage: typing.Union[int, common.ScalarCalculation],
        shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
        shipStartingFuel: typing.Union[int, common.ScalarCalculation],
        perJumpOverheads: typing.Union[int, common.ScalarCalculation],
        refuellingStrategy: typing.Union[int, common.ScalarCalculation],
        shipFuelPerParsec: typing.Union[float, common.ScalarCalculation] = None,
        # Optional set containing the integer indices of jump route worlds where berthing is required.
        requiredBerthingIndices: typing.Optional[typing.Set[int]] = None,
        # Specify if generated route logistics will include refuelling costs. If not included the
        # costs will still be taken into account when calculating the optimal pit stop worlds,
        # however the costs for fuel and berthing will be zero
        includeLogisticsCosts: bool = True,
        diceRoller: typing.Optional[common.DiceRoller] = None
        ) -> typing.Optional[RouteLogistics]:
    refuellingPlan = None
    if jumpRoute.worldCount() > 1:
        refuellingPlan = logic.calculateRefuellingPlan(
            jumpRoute=jumpRoute,
            shipTonnage=shipTonnage,
            shipFuelCapacity=shipFuelCapacity,
            shipStartingFuel=shipStartingFuel,
            shipFuelPerParsec=shipFuelPerParsec,
            refuellingStrategy=refuellingStrategy,
            requiredBerthingIndices=requiredBerthingIndices,
            includeRefuellingCosts=includeLogisticsCosts,
            diceRoller=diceRoller)
        if not refuellingPlan:
            return None
    else:
        # The start and end world are the same so there are no travel costs. There can still be
        # berthing costs on the start world, this covers the case where you've not arrived on
        # the world yet
        requireStartWorldBerthing = requiredBerthingIndices and 0 in requiredBerthingIndices
        requireFinishWorldBerthing = requiredBerthingIndices and (jumpRoute.worldCount() - 1) in requiredBerthingIndices

        if requireStartWorldBerthing or requireFinishWorldBerthing:
            startWorld = jumpRoute.startWorld()
            berthingCost = traveller.starPortBerthingCost(
                world=startWorld)
            berthingCost = common.Calculator.rename(
                value=berthingCost,
                name=f'Berthing Cost For {startWorld.name(includeSubsector=True)}')

            reportedBerthingCost = berthingCost
            if reportedBerthingCost and not includeLogisticsCosts:
                reportedBerthingCost = common.Calculator.override(
                    old=reportedBerthingCost,
                    new=common.ScalarCalculation(value=0, name='Overridden Berthing Cost'),
                    name='Ignored Berthing Cost')

            pitStop = logic.PitStop(
                jumpIndex=0,
                world=startWorld,
                refuellingType=None, # No refuelling
                tonsOfFuel=None,
                fuelCost=None,
                berthingCost=reportedBerthingCost)
            refuellingPlan = logic.RefuellingPlan([pitStop])

    reportedPerJumpOverheads = perJumpOverheads
    if reportedPerJumpOverheads and not includeLogisticsCosts:
        reportedPerJumpOverheads = common.Calculator.override(
            old=reportedPerJumpOverheads,
            new=common.ScalarCalculation(value=0, name='Overridden Per Jump Overheads'),
            name='Ignored Per Jump Overheads')

    return logic.RouteLogistics(
        jumpRoute=jumpRoute,
        refuellingPlan=refuellingPlan,
        perJumpOverheads=reportedPerJumpOverheads)
