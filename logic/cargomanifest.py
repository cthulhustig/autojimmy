import common
import logic
import multiverse
import typing

class CargoManifest(object):
    def __init__(
            self,
            purchaseWorld: multiverse.World,
            saleWorld: multiverse.World,
            routeLogistics: logic.RouteLogistics,
            tradeOptions: typing.Iterable[logic.TradeOption]
            ) -> None:
        self._purchaseWorld = purchaseWorld
        self._saleWorld = saleWorld
        self._routeLogistics = routeLogistics
        self._tradeOptions = tradeOptions

        cargoQuantities = []
        cargoPrices = []
        cargoProfits = []
        for tradeOption in tradeOptions:
            cargoQuantity = tradeOption.cargoQuantity()
            assert(isinstance(cargoQuantity, common.ScalarCalculation))
            cargoQuantities.append(cargoQuantity)

            cargoPrice = common.Calculator.multiply(
                lhs=tradeOption.purchasePricePerTon(),
                rhs=cargoQuantity,
                name=f'Purchase Price for {cargoQuantity.value()} tons of {tradeOption.tradeGood().name()}')
            cargoPrices.append(cargoPrice)

            cargoProfit = common.Calculator.rename(
                value=tradeOption.grossProfit(),
                name=f'Profit for {cargoQuantity.value()} tons of {tradeOption.tradeGood().name()}')
            cargoProfits.append(cargoProfit)

        self._cargoQuantity = common.Calculator.sum(
            values=cargoQuantities,
            name='Cargo Quantity')
        assert(isinstance(self._cargoQuantity, common.ScalarCalculation))

        self._totalCargoCost = common.Calculator.sum(
            values=cargoPrices,
            name='Cargo Cost')

        self._grossProfit = common.Calculator.sum(
            values=cargoProfits,
            name='Gross Profit')

        self._netProfit = common.Calculator.subtract(
            lhs=self._grossProfit,
            rhs=self._routeLogistics.totalCosts(),
            name='Net Profit')

    def purchaseWorld(self) -> multiverse.World:
        return self._purchaseWorld

    def saleWorld(self) -> multiverse.World:
        return self._saleWorld

    def routeLogistics(self) -> logic.RouteLogistics:
        return self._routeLogistics

    def jumpCount(self) -> int:
        return self._routeLogistics.jumpCount()

    def jumpRoute(self) -> logic.JumpRoute:
        return self._routeLogistics.jumpRoute()

    def tradeOptions(self) -> typing.Iterable[logic.TradeOption]:
        return self._tradeOptions

    def cargoQuantity(self) -> common.ScalarCalculation:
        return self._cargoQuantity

    def cargoCost(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._totalCargoCost

    def cargoRecords(self) -> typing.Iterable[logic.CargoRecord]:
        cargoRecords = []
        for tradeOption in self._tradeOptions:
            cargoRecords.append(logic.CargoRecord(
                tradeGood=tradeOption.tradeGood(),
                pricePerTon=tradeOption.purchasePricePerTon(),
                quantity=tradeOption.cargoQuantity()))
        return cargoRecords

    def logisticsCosts(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._routeLogistics.totalCosts()

    def grossProfit(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._grossProfit

    def netProfit(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._netProfit

def generateCargoManifests(
        availableFunds: typing.Union[int, float, common.ScalarCalculation],
        shipCargoCapacity: typing.Union[int, common.ScalarCalculation],
        tradeOptions: typing.Iterable[logic.TradeOption],
        # Default to average case purchase logic. Generally this won't matter as planning a cargo
        # manifest only really makes sense when purchase prices are known and avg, worst and best
        # case values are the same
        purchaseLogic: logic.RollOutcome = logic.RollOutcome.AverageCase,
        # Default to worst case logistics logic. This is the safe option as it means we don't risk
        # spending so much we could run out of money on route due to bad dice rolls
        logisticsLogic: logic.RollOutcome = logic.RollOutcome.WorstCase,
        ) -> typing.List[CargoManifest]:
    if not isinstance(availableFunds, common.ScalarCalculation):
        assert(isinstance(availableFunds, int) or isinstance(availableFunds, float))
        availableFunds = common.ScalarCalculation(
            value=availableFunds,
            name='Available Funds')

    if not isinstance(shipCargoCapacity, common.ScalarCalculation):
        assert(isinstance(shipCargoCapacity, int))
        shipCargoCapacity = common.ScalarCalculation(
            value=shipCargoCapacity,
            name='Ship Cargo Capacity')

    # Split trade options into individual lists per sale world
    worldTradeOptions = {}
    worldLogistics = {}
    for tradeOption in tradeOptions:
        worldPair = (tradeOption.purchaseWorld(), tradeOption.saleWorld())
        if worldPair not in worldTradeOptions:
            worldTradeOptions[worldPair] = [tradeOption]
        else:
            worldTradeOptions[worldPair].append(tradeOption)

        if worldPair not in worldLogistics:
            worldLogistics[worldPair] = tradeOption.routeLogistics()

    cargoManifests = []
    for worldPair, tradeOptions in worldTradeOptions.items():
        purchaseWorld = worldPair[0]
        saleWorld = worldPair[1]

        remainingFunds: common.ScalarCalculation = common.Calculator.equals(
            value=availableFunds,
            name='Remaining Funds')
        remainingCargoCapacity: common.ScalarCalculation = common.Calculator.equals(
            value=shipCargoCapacity,
            name='Remaining Cargo Capacity')

        routeLogistics: logic.RouteLogistics = worldLogistics[worldPair]

        remainingFunds = common.Calculator.subtract(
            lhs=remainingFunds,
            rhs=routeLogistics.totalCosts())

        if logisticsLogic == logic.RollOutcome.AverageCase:
            remainingFunds = remainingFunds.averageCaseCalculation()
        elif logisticsLogic == logic.RollOutcome.WorstCase:
            remainingFunds = remainingFunds.worstCaseCalculation()
        else:
            assert(logisticsLogic == logic.RollOutcome.BestCase)
            remainingFunds = remainingFunds.bestCaseCalculation()

        cargoTradeOptions = []
        while tradeOptions and \
            (remainingFunds.value() > 0) and \
                (remainingCargoCapacity.value() > 0):
            # Find the next best trade option
            bestTradeOption = _findBestTradeOption(
                availableFunds=remainingFunds,
                shipCargoCapacity=remainingCargoCapacity,
                tradeOptions=tradeOptions,
                purchaseLogic=purchaseLogic)
            if not bestTradeOption:
                # No more affordable trade options
                break

            cargoTradeOptions.append(bestTradeOption)

            # Remove the trade option from the list that matches the trade good of the
            # best trade option in order to prevent the same trade good being selected
            # again. Note that _findBestTradeOption returns a new trade option so it's
            # not as simple as searching the list for a reference to bestTradeOption
            tradeOptions = [tradeOption for tradeOption in tradeOptions if tradeOption.tradeGood() != bestTradeOption.tradeGood()]

            # Subtract the cargo costs from the remaining funds
            purchaseQuantity = bestTradeOption.cargoQuantity()
            assert(isinstance(purchaseQuantity, common.ScalarCalculation))

            purchasePrice = common.Calculator.multiply(
                lhs=purchaseQuantity,
                rhs=bestTradeOption.purchasePricePerTon(),
                name=f'Purchase Price')

            if purchaseLogic == logic.RollOutcome.AverageCase:
                purchasePrice = purchasePrice.averageCaseCalculation()
            elif purchaseLogic == logic.RollOutcome.WorstCase:
                purchasePrice = purchasePrice.worstCaseCalculation()
            else:
                assert(purchaseLogic == logic.RollOutcome.BestCase)
                purchasePrice = purchasePrice.bestCaseCalculation()

            remainingFunds = common.Calculator.subtract(
                lhs=remainingFunds,
                rhs=purchasePrice,
                name='Remaining Funds')
            assert(remainingFunds.value() >= 0)

            # Subtract the cargo quantity from the remaining capacity
            remainingCargoCapacity = common.Calculator.subtract(
                lhs=remainingCargoCapacity,
                rhs=purchaseQuantity,
                name='Remaining Cargo Capacity')
            assert(remainingCargoCapacity.value() >= 0)

        if not cargoTradeOptions:
            # No safe cargo manifests for this world pair. This can happen due to the fact the
            # trader only filters out trade options based on average logistics costs but the cargo
            # manifest generator can assume worst case logistics costs when deciding how much cargo to
            # buy (to avoid running out of cash before you reach the sale world)
            continue

        cargoManifests.append(CargoManifest(
            purchaseWorld=purchaseWorld,
            saleWorld=saleWorld,
            routeLogistics=routeLogistics,
            tradeOptions=cargoTradeOptions))

    return cargoManifests

def _findBestTradeOption(
        availableFunds: common.ScalarCalculation,
        shipCargoCapacity: common.ScalarCalculation,
        tradeOptions: typing.Iterable[logic.TradeOption],
        purchaseLogic: logic.RollOutcome
        ) -> typing.Optional[logic.TradeOption]:
    bestTradeOption = None
    for tradeOption in tradeOptions:
        purchasePricePerTon = tradeOption.purchasePricePerTon()
        availableQuantity = tradeOption.cargoQuantity()
        grossProfit = tradeOption.grossProfit()

        if purchaseLogic == logic.RollOutcome.AverageCase:
            if grossProfit.averageCaseValue() <= 0:
                continue # Skip unprofitable trades

            purchasePricePerTon = purchasePricePerTon.averageCaseCalculation()
            availableQuantity = availableQuantity.averageCaseCalculation()
        elif purchaseLogic == logic.RollOutcome.WorstCase:
            if grossProfit.worstCaseValue() <= 0:
                continue # Skip unprofitable trades

            purchasePricePerTon = purchasePricePerTon.worstCaseCalculation()
            availableQuantity = availableQuantity.worstCaseCalculation()
        else:
            assert(purchaseLogic == logic.RollOutcome.BestCase)
            if grossProfit.bestCaseValue() <= 0:
                continue # Skip unprofitable trades

            purchasePricePerTon = purchasePricePerTon.bestCaseCalculation()
            availableQuantity = availableQuantity.bestCaseCalculation()

        if purchasePricePerTon.value() > 0:
            # Calculate the number of tons we can afford based on the average value
            # limited by the average number of tons available
            purchaseQuantity = common.Calculator.divideFloor(
                lhs=availableFunds,
                rhs=purchasePricePerTon,
                name=f'Affordable Quantity')
            purchaseQuantity = common.Calculator.min(
                lhs=purchaseQuantity,
                rhs=availableQuantity)
        else:
            # No purchase cost so the only limiting factor is availability
            purchaseQuantity = availableQuantity

        if purchaseQuantity.value() <= 0:
            # We can't afford this trade good so move onto the next one
            continue

        purchaseQuantity = common.Calculator.min(
            lhs=purchaseQuantity,
            rhs=shipCargoCapacity,
            name=f'Purchase Quantity')
        assert(isinstance(purchaseQuantity, common.ScalarCalculation))

        # Create a new trade option with the cargo quantity set to the number of tons to be
        # purchased. Any notes attached to the source trade option aren't copied as it's
        # not obvious they still apply.
        newTradeOption = logic.TradeOption(
            cargoRecord=tradeOption.originalCargoRecord(),
            purchaseWorld=tradeOption.purchaseWorld(),
            purchasePricePerTon=tradeOption.purchasePricePerTon(),
            saleWorld=tradeOption.saleWorld(),
            salePricePerTon=tradeOption.salePricePerTon(),
            cargoQuantity=purchaseQuantity,
            alreadyOwned=tradeOption.isAlreadyOwned(),
            routeLogistics=tradeOption.routeLogistics())

        # Check if this new trade option is the best trade option. The total gross profits are
        # compared rather than net profits as logistics have already been accounted for
        if not bestTradeOption:
            bestTradeOption = newTradeOption
        else:
            newProfit = newTradeOption.grossProfit()
            bestProfit = bestTradeOption.grossProfit()
            if purchaseLogic == logic.RollOutcome.AverageCase:
                newProfit = newProfit.averageCaseValue()
                bestProfit = bestProfit.averageCaseValue()
            elif purchaseLogic == logic.RollOutcome.WorstCase:
                newProfit = newProfit.worstCaseValue()
                bestProfit = bestProfit.worstCaseValue()
            else:
                assert(purchaseLogic == logic.RollOutcome.BestCase)
                newProfit = newProfit.bestCaseValue()
                bestProfit = bestProfit.bestCaseValue()

            if newProfit > bestProfit:
                bestTradeOption = newTradeOption

    return bestTradeOption
