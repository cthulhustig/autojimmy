import common
import logic
import traveller
import travellermap
import typing

class RouteLogistics(object):
    def __init__(
            self,
            milieu: travellermap.Milieu,
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

        self._milieu = milieu
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

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

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
        milieu: travellermap.Milieu,
        jumpRoute: logic.JumpRoute,
        shipTonnage: typing.Union[int, common.ScalarCalculation],
        shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
        shipStartingFuel: typing.Union[float, common.ScalarCalculation],
        perJumpOverheads: typing.Union[int, common.ScalarCalculation],
        pitCostCalculator: typing.Optional[logic.PitStopCostCalculator] = None,
        shipFuelPerParsec: typing.Union[float, common.ScalarCalculation] = None,
        # Specify if generated route logistics will include refuelling costs. If not included the
        # costs will still be taken into account when calculating the optimal pit stop worlds,
        # however the costs for fuel and berthing will be zero
        includeLogisticsCosts: bool = True,
        diceRoller: typing.Optional[common.DiceRoller] = None
        ) -> typing.Optional[RouteLogistics]:
    refuellingPlan = None
    if pitCostCalculator:
        if jumpRoute.nodeCount() > 1:
            refuellingPlan = logic.calculateRefuellingPlan(
                milieu=milieu,
                jumpRoute=jumpRoute,
                shipTonnage=shipTonnage,
                shipFuelCapacity=shipFuelCapacity,
                shipStartingFuel=shipStartingFuel,
                shipFuelPerParsec=shipFuelPerParsec,
                pitCostCalculator=pitCostCalculator,
                includeRefuellingCosts=includeLogisticsCosts,
                diceRoller=diceRoller)
            if not refuellingPlan:
                return None
        else:
            # The start and end world are the same so there are no travel costs. There can still be
            # berthing costs on the start world, this covers the case where you've not arrived on
            # the world yet
            if jumpRoute.mandatoryBerthing(index=0) or jumpRoute.mandatoryBerthing(index=jumpRoute.nodeCount() - 1):
                startHex = jumpRoute.startNode()
                startWorld = traveller.WorldManager.instance().worldByPosition(milieu=milieu, hex=startHex)
                if startWorld:
                    berthingCost = pitCostCalculator.berthingCost(
                        world=startWorld,
                        mandatory=True)
                    if berthingCost:
                        berthingCost = common.Calculator.rename(
                            value=berthingCost,
                            name=f'Berthing Cost For {startWorld.name(includeSubsector=True)}')

                        if not includeLogisticsCosts:
                            berthingCost = common.Calculator.override(
                                old=berthingCost,
                                new=common.ScalarCalculation(value=0, name='Overridden Berthing Cost'),
                                name='Ignored Berthing Cost')

                    pitStop = logic.PitStop(
                        jumpIndex=0,
                        world=startWorld,
                        refuellingType=None, # No refuelling
                        tonsOfFuel=None,
                        fuelCost=None,
                        berthingCost=berthingCost)
                    refuellingPlan = logic.RefuellingPlan(
                        milieu=milieu,
                        pitStops=[pitStop])

    reportedPerJumpOverheads = perJumpOverheads
    if reportedPerJumpOverheads and not includeLogisticsCosts:
        reportedPerJumpOverheads = common.Calculator.override(
            old=reportedPerJumpOverheads,
            new=common.ScalarCalculation(value=0, name='Overridden Per Jump Overheads'),
            name='Ignored Per Jump Overheads')

    return logic.RouteLogistics(
        milieu=milieu,
        jumpRoute=jumpRoute,
        refuellingPlan=refuellingPlan,
        perJumpOverheads=reportedPerJumpOverheads)
