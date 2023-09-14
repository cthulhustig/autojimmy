import common
import logic
import math
import traveller
import typing

class Trader(object):
    def __init__(
            self,
            rules: traveller.Rules,
            tradeOptionCallback: typing.Callable[[logic.TradeOption], typing.Any],
            traderInfoCallback: typing.Optional[typing.Callable[[str], typing.Any]] = None,
            progressCallback: typing.Optional[typing.Callable[[int, int], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> None:
        self._rules = rules
        self._tradeOptionCallback = tradeOptionCallback
        self._traderInfoCallback = traderInfoCallback
        self._progressCallback = progressCallback
        self._isCancelledCallback = isCancelledCallback
        self._currentProgress = None
        self._optionsToProcess = None

    def calculateTradeOptionsForSingleWorld(
            self,
            purchaseWorld: traveller.World,
            saleWorlds: typing.Iterable[traveller.World],
            currentCargo: typing.Iterable[logic.CargoRecord],
            possibleCargo: typing.Iterable[logic.CargoRecord],
            playerBrokerDm: typing.Union[int, common.ScalarCalculation],
            minBuyerDm: typing.Union[int, common.ScalarCalculation],
            maxBuyerDm: typing.Union[int, common.ScalarCalculation],
            availableFunds: typing.Union[int, float, common.ScalarCalculation],
            shipTonnage: typing.Union[int, common.ScalarCalculation],
            shipJumpRating: typing.Union[int, common.ScalarCalculation],
            shipCargoCapacity: typing.Union[int, common.ScalarCalculation],
            shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
            shipStartingFuel: typing.Union[int, common.ScalarCalculation],
            perJumpOverheads: typing.Union[int, common.ScalarCalculation],
            jumpCostCalculator: logic.JumpCostCalculatorInterface,
            refuellingStrategy: logic.RefuellingStrategy,
            shipFuelPerParsec: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            useLocalSaleBroker: bool = False,
            localSaleBrokerDm: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None, # Only used for 1e & 2e
            includePurchaseWorldBerthing: bool = False, # Assume we're already berthed on the purchase world
            includeSaleWorldBerthing: bool = True, # Assume we'll have to berth on the sale world to complete the trade
            includeLogisticsCosts: bool = True,
            includeUnprofitableTrades: bool = False
            ) -> None:
        # Convert arguments used directly but this class to calculations if needed. Arguments that
        # are just passed on will be converted by the function they are passed to if required.
        if not isinstance(availableFunds, common.ScalarCalculation):
            assert(isinstance(availableFunds, int) or isinstance(availableFunds, float))
            availableFunds = common.ScalarCalculation(
                value=availableFunds,
                name='Available Funds')

        if not isinstance(shipTonnage, common.ScalarCalculation):
            assert(isinstance(shipTonnage, int))
            shipTonnage = common.ScalarCalculation(
                value=shipTonnage,
                name='Ship Tonnage')

        if not isinstance(shipJumpRating, common.ScalarCalculation):
            assert(isinstance(shipJumpRating, int))
            shipJumpRating = common.ScalarCalculation(
                value=shipJumpRating,
                name='Ship Jump Rating')

        if not isinstance(shipCargoCapacity, common.ScalarCalculation):
            assert(isinstance(shipCargoCapacity, int))
            shipCargoCapacity = common.ScalarCalculation(
                value=shipCargoCapacity,
                name='Ship Cargo Capacity')

        if not isinstance(shipFuelCapacity, common.ScalarCalculation):
            assert(isinstance(shipFuelCapacity, int))
            shipFuelCapacity = common.ScalarCalculation(
                value=shipFuelCapacity,
                name='Ship Fuel Capacity')

        if not isinstance(shipStartingFuel, common.ScalarCalculation):
            assert(isinstance(shipStartingFuel, int))
            shipStartingFuel = common.ScalarCalculation(
                value=shipStartingFuel,
                name='Ship Starting Fuel')

        if not shipFuelPerParsec:
            shipFuelPerParsec = traveller.calculateFuelRequiredForJump(
                jumpDistance=1,
                shipTonnage=shipTonnage)
        elif not isinstance(shipFuelPerParsec, common.ScalarCalculation):
            assert(isinstance(shipFuelPerParsec, (int, float)))
            shipFuelPerParsec = common.ScalarCalculation(
                value=shipFuelPerParsec,
                name='Ship Fuel Per Parsec')

        if not isinstance(perJumpOverheads, common.ScalarCalculation):
            assert(isinstance(perJumpOverheads, int))
            perJumpOverheads = common.ScalarCalculation(
                value=perJumpOverheads,
                name='Per Jump Overheads')

        self._verifyShipSettings(
            shipTonnage=shipTonnage,
            shipCargoCapacity=shipCargoCapacity,
            shipFuelCapacity=shipFuelCapacity,
            shipStartingFuel=shipStartingFuel)

        if not isinstance(minBuyerDm, common.ScalarCalculation):
            assert(isinstance(minBuyerDm, int))
            minBuyerDm = common.ScalarCalculation(
                value=minBuyerDm,
                name='Min Buyer DM')
        if not isinstance(maxBuyerDm, common.ScalarCalculation):
            assert(isinstance(maxBuyerDm, int))
            maxBuyerDm = common.ScalarCalculation(
                value=maxBuyerDm,
                name='Max Buyer DM')

        # When calculating the average buyers DM we round up to be pessimistic
        buyerDm = common.RangeCalculation(
            worstCase=maxBuyerDm,
            bestCase=minBuyerDm,
            averageCase=common.Calculator.ceil(
                value=common.Calculator.average(
                    lhs=minBuyerDm,
                    rhs=maxBuyerDm)),
            name='Buyer DM')

        if useLocalSaleBroker and (localSaleBrokerDm != None) and \
                not isinstance(localSaleBrokerDm, common.ScalarCalculation):
            assert(isinstance(localSaleBrokerDm, int))
            localSaleBrokerDm = common.ScalarCalculation(
                value=localSaleBrokerDm,
                name='Local Sale Broker DM Increase')

        self._optionsToProcess = (len(currentCargo) if currentCargo else 0) + \
            (len(possibleCargo) if possibleCargo else 0)
        self._optionsToProcess *= len(saleWorlds)
        self._currentProgress = 0

        self._calculateTradeOptions(
            purchaseWorld=purchaseWorld,
            saleWorlds=saleWorlds,
            currentCargo=currentCargo,
            possibleCargo=possibleCargo,
            playerBrokerDm=playerBrokerDm,
            buyerDm=buyerDm,
            availableFunds=availableFunds,
            shipTonnage=shipTonnage,
            shipJumpRating=shipJumpRating,
            shipCargoCapacity=shipCargoCapacity,
            shipFuelCapacity=shipFuelCapacity,
            shipStartingFuel=shipStartingFuel,
            shipFuelPerParsec=shipFuelPerParsec,
            perJumpOverheads=perJumpOverheads,
            jumpCostCalculator=jumpCostCalculator,
            refuellingStrategy=refuellingStrategy,
            useLocalSaleBroker=useLocalSaleBroker,
            localSaleBrokerDm=localSaleBrokerDm,
            includePurchaseWorldBerthing=includePurchaseWorldBerthing,
            includeSaleWorldBerthing=includeSaleWorldBerthing,
            includeLogisticsCosts=includeLogisticsCosts,
            includeUnprofitableTrades=includeUnprofitableTrades)

    def calculateTradeOptionsForMultipleWorlds(
            self,
            purchaseWorlds: typing.Iterable[traveller.World],
            saleWorlds: typing.Iterable[traveller.World],
            playerBrokerDm: typing.Union[int, common.ScalarCalculation],
            minSellerDm: typing.Union[int, common.ScalarCalculation],
            maxSellerDm: typing.Union[int, common.ScalarCalculation],
            minBuyerDm: typing.Union[int, common.ScalarCalculation],
            maxBuyerDm: typing.Union[int, common.ScalarCalculation],
            includeIllegal: bool,
            availableFunds: typing.Union[int, float, common.ScalarCalculation],
            shipTonnage: typing.Union[int, common.ScalarCalculation],
            shipJumpRating: typing.Union[int, common.ScalarCalculation],
            shipCargoCapacity: typing.Union[int, common.ScalarCalculation],
            shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
            shipStartingFuel: typing.Union[int, common.ScalarCalculation],
            perJumpOverheads: typing.Union[int, common.ScalarCalculation],
            jumpCostCalculator: logic.JumpCostCalculatorInterface,
            refuellingStrategy: logic.RefuellingStrategy,
            shipFuelPerParsec: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            useLocalPurchaseBroker: bool = False,
            localPurchaseBrokerDm: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None, # Only used for 1e & 2e
            useLocalSaleBroker: bool = False,
            localSaleBrokerDm: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None, # Only used for 1e & 2e
            includePurchaseWorldBerthing: bool = False, # Assume we're already berthed on the purchase world
            includeSaleWorldBerthing: bool = True, # Assume we'll have to berth on the sale world to complete the trade
            includeLogisticsCosts: bool = True,
            includeUnprofitableTrades: bool = False
            ) -> None:
        # Convert arguments used directly but this class to calculations if needed. Arguments that
        # are just passed on will be converted by the function they are passed to if required.
        if not isinstance(availableFunds, common.ScalarCalculation):
            assert(isinstance(availableFunds, int) or isinstance(availableFunds, float))
            availableFunds = common.ScalarCalculation(
                value=availableFunds,
                name='Available Funds')

        if not isinstance(shipTonnage, common.ScalarCalculation):
            assert(isinstance(shipTonnage, int))
            shipTonnage = common.ScalarCalculation(
                value=shipTonnage,
                name='Ship Tonnage')

        if not isinstance(shipJumpRating, common.ScalarCalculation):
            assert(isinstance(shipJumpRating, int))
            shipJumpRating = common.ScalarCalculation(
                value=shipJumpRating,
                name='Ship Jump Rating')

        if not isinstance(shipCargoCapacity, common.ScalarCalculation):
            assert(isinstance(shipCargoCapacity, int))
            shipCargoCapacity = common.ScalarCalculation(
                value=shipCargoCapacity,
                name='Ship Cargo Capacity')

        if not isinstance(shipFuelCapacity, common.ScalarCalculation):
            assert(isinstance(shipFuelCapacity, int))
            shipFuelCapacity = common.ScalarCalculation(
                value=shipFuelCapacity,
                name='Ship Fuel Capacity')

        if not isinstance(shipStartingFuel, common.ScalarCalculation):
            assert(isinstance(shipStartingFuel, int))
            shipStartingFuel = common.ScalarCalculation(
                value=shipStartingFuel,
                name='Ship Starting Fuel')

        if not shipFuelPerParsec:
            shipFuelPerParsec = traveller.calculateFuelRequiredForJump(
                jumpDistance=1,
                shipTonnage=shipTonnage)
        elif not isinstance(shipFuelPerParsec, common.ScalarCalculation):
            assert(isinstance(shipFuelPerParsec, (int, float)))
            shipFuelPerParsec = common.ScalarCalculation(
                value=shipFuelPerParsec,
                name='Ship Fuel Per Parsec')

        if not isinstance(perJumpOverheads, common.ScalarCalculation):
            assert(isinstance(perJumpOverheads, int))
            perJumpOverheads = common.ScalarCalculation(
                value=perJumpOverheads,
                name='Per Jump Overheads')

        self._verifyShipSettings(
            shipTonnage=shipTonnage,
            shipCargoCapacity=shipCargoCapacity,
            shipFuelCapacity=shipFuelCapacity,
            shipStartingFuel=shipStartingFuel)

        if shipFuelCapacity.value() > shipTonnage.value():
            raise ValueError('Ship\'s fuel capacity can\'t be larger than its total tonnage')
        if shipStartingFuel.value() > shipFuelCapacity.value():
            raise ValueError('Ship\'s starting fuel can\'t be larger than its fuel capacity')
        if shipCargoCapacity.value() > shipTonnage.value():
            raise ValueError('Ship\'s cargo capacity can\'t be larger than its total tonnage')
        if (shipFuelCapacity.value() + shipCargoCapacity.value()) > shipTonnage.value():
            raise ValueError('Ship\'s combined fuel and cargo capacities can\'t be larger than its total tonnage')

        if not isinstance(minBuyerDm, common.ScalarCalculation):
            assert(isinstance(minBuyerDm, int))
            minBuyerDm = common.ScalarCalculation(
                value=minBuyerDm,
                name='Min Buyer DM')
        if not isinstance(maxBuyerDm, common.ScalarCalculation):
            assert(isinstance(maxBuyerDm, int))
            maxBuyerDm = common.ScalarCalculation(
                value=maxBuyerDm,
                name='Max Buyer DM')

        # When calculating the average buyers DM we round up to be pessimistic
        buyerDm = common.RangeCalculation(
            worstCase=maxBuyerDm,
            bestCase=minBuyerDm,
            averageCase=common.Calculator.ceil(
                value=common.Calculator.average(
                    lhs=minBuyerDm,
                    rhs=maxBuyerDm)),
            name='Buyer DM')

        if useLocalPurchaseBroker and (localPurchaseBrokerDm != None) and \
                not isinstance(localPurchaseBrokerDm, common.ScalarCalculation):
            assert(isinstance(localPurchaseBrokerDm, int))
            localPurchaseBrokerDm = common.ScalarCalculation(
                value=localPurchaseBrokerDm,
                name='Local Purchase Broker DM')

        if useLocalSaleBroker and (localSaleBrokerDm != None) and \
                not isinstance(localSaleBrokerDm, common.ScalarCalculation):
            assert(isinstance(localSaleBrokerDm, int))
            localSaleBrokerDm = common.ScalarCalculation(
                value=localSaleBrokerDm,
                name='Local Sale Broker DM')

        self._optionsToProcess = 0
        purchaseWorldPossibleCargo = []
        for purchaseWorld in purchaseWorlds:
            possibleCargo = logic.generateSpeculativePurchaseCargo(
                rules=self._rules,
                world=purchaseWorld,
                playerBrokerDm=playerBrokerDm,
                useLocalBroker=useLocalPurchaseBroker,
                localBrokerDm=localPurchaseBrokerDm,
                minSellerDm=minSellerDm,
                maxSellerDm=maxSellerDm,
                includeLegal=True,
                includeIllegal=includeIllegal)
            purchaseWorldPossibleCargo.append(possibleCargo)
            self._optionsToProcess += len(possibleCargo)

        self._optionsToProcess *= len(saleWorlds)
        self._currentProgress = 0

        # Note that it's intentional that there is no check that the purchase and sale worlds are
        # the same. Depending on trade codes there are worlds where it's possible to make a profit
        # with average dice rolls just by buying and selling on the same world
        for index, purchaseWorld in enumerate(purchaseWorlds):
            if self._isCancelledCallback and self._isCancelledCallback():
                return

            possibleCargo = purchaseWorldPossibleCargo[index]
            if not possibleCargo:
                continue

            self._calculateTradeOptions(
                purchaseWorld=purchaseWorld,
                saleWorlds=saleWorlds,
                possibleCargo=possibleCargo,
                currentCargo=None,
                playerBrokerDm=playerBrokerDm,
                buyerDm=buyerDm,
                availableFunds=availableFunds,
                shipTonnage=shipTonnage,
                shipJumpRating=shipJumpRating,
                shipCargoCapacity=shipCargoCapacity,
                shipFuelCapacity=shipFuelCapacity,
                shipStartingFuel=shipStartingFuel,
                shipFuelPerParsec=shipFuelPerParsec,
                perJumpOverheads=perJumpOverheads,
                jumpCostCalculator=jumpCostCalculator,
                refuellingStrategy=refuellingStrategy,
                useLocalSaleBroker=useLocalSaleBroker,
                localSaleBrokerDm=localSaleBrokerDm,
                includePurchaseWorldBerthing=includePurchaseWorldBerthing,
                includeSaleWorldBerthing=includeSaleWorldBerthing,
                includeLogisticsCosts=includeLogisticsCosts,
                includeUnprofitableTrades=includeUnprofitableTrades)

    def _calculateTradeOptions(
            self,
            purchaseWorld: traveller.World,
            saleWorlds: typing.Iterable[traveller.World],
            currentCargo: typing.Iterable[logic.CargoRecord],
            possibleCargo: typing.Iterable[logic.CargoRecord],
            playerBrokerDm: common.ScalarCalculation,
            buyerDm: typing.Union[common.ScalarCalculation, common.RangeCalculation],
            availableFunds: common.ScalarCalculation,
            shipTonnage: common.ScalarCalculation,
            shipJumpRating: common.ScalarCalculation,
            shipCargoCapacity: common.ScalarCalculation,
            shipFuelCapacity: common.ScalarCalculation,
            shipStartingFuel: common.ScalarCalculation,
            shipFuelPerParsec: common.ScalarCalculation,
            perJumpOverheads: common.ScalarCalculation,
            jumpCostCalculator: logic.JumpCostCalculatorInterface,
            refuellingStrategy: logic.RefuellingStrategy,
            useLocalSaleBroker: bool = False,
            localSaleBrokerDm: typing.Optional[common.ScalarCalculation] = None, # Only used for 1e & 2e
            includePurchaseWorldBerthing: bool = False, # Assume we're already berthed on the purchase world
            includeSaleWorldBerthing: bool = True, # Assume we'll have to berth on the sale world to complete the trade
            includeLogisticsCosts: bool = True,
            includeUnprofitableTrades: bool = False
            ) -> None:
        routePlanner = logic.RoutePlanner()

        for saleWorld in saleWorlds:
            jumpRoute = routePlanner.calculateDirectRoute(
                startWorld=purchaseWorld,
                finishWorld=saleWorld,
                shipTonnage=shipTonnage,
                shipJumpRating=shipJumpRating,
                shipFuelCapacity=shipFuelCapacity,
                shipFuelPerParsec=shipFuelPerParsec,
                shipCurrentFuel=shipStartingFuel,
                jumpCostCalculator=jumpCostCalculator,
                refuellingStrategy=refuellingStrategy,
                worldFilterCallback=None,
                isCancelledCallback=self._isCancelledCallback)
            if not jumpRoute:
                if self._isCancelledCallback and self._isCancelledCallback():
                    # Operation was cancelled while calculating the jump route
                    return

                self._updateProgress(
                    processedCount=(len(currentCargo) if currentCargo else 0) + \
                    (len(possibleCargo) if possibleCargo else 0))

                if self._traderInfoCallback:
                    self._traderInfoCallback(
                        f'Ignoring sale of all trade goods on {saleWorld.name(includeSubsector=True)}. ' +
                        f'There is no jump route to get there with jump-{shipJumpRating}')
                continue

            requiredBerthingIndices = None
            if includePurchaseWorldBerthing or includeSaleWorldBerthing:
                requiredBerthingIndices = set()
                if includePurchaseWorldBerthing:
                    requiredBerthingIndices.add(0)
                if includeSaleWorldBerthing:
                    requiredBerthingIndices.add(jumpRoute.worldCount() - 1)

            routeLogistics = logic.calculateRouteLogistics(
                jumpRoute=jumpRoute,
                shipTonnage=shipTonnage,
                shipFuelCapacity=shipFuelCapacity,
                shipStartingFuel=shipStartingFuel,
                shipFuelPerParsec=shipFuelPerParsec,
                perJumpOverheads=perJumpOverheads,
                refuellingStrategy=refuellingStrategy,
                requiredBerthingIndices=requiredBerthingIndices,
                includeLogisticsCosts=includeLogisticsCosts)
            if not routeLogistics:
                self._updateProgress(
                    processedCount=(len(currentCargo) if currentCargo else 0) + \
                    (len(possibleCargo) if possibleCargo else 0))

                if self._traderInfoCallback:
                    self._traderInfoCallback(
                        f'Ignoring sale of all goods on {saleWorld.name(includeSubsector=True)}. ' +
                        f'There is no way to reach it with the current fuel settings.')
                continue

            # Calculate the usable funds you have after taking potential costs into account.
            # This is done so we reject trades that would leave us with insufficient funds to
            # jump to the sale world
            logisticsCosts = routeLogistics.totalCosts()
            useableFunds = common.Calculator.subtract(
                lhs=availableFunds,
                rhs=logisticsCosts,
                name='Usable Funds')
            useableFunds = common.Calculator.max(
                lhs=useableFunds,
                rhs=common.ScalarCalculation(0))

            if not includeUnprofitableTrades and useableFunds.averageCaseValue() <= 0:
                self._updateProgress(
                    processedCount=(len(currentCargo) if currentCargo else 0) + \
                    (len(possibleCargo) if possibleCargo else 0))

                if self._traderInfoCallback:
                    self._traderInfoCallback(
                        f'Ignoring sale of all goods on {saleWorld.name(includeSubsector=True)}. ' +
                        f'The average logistics cost is Cr{common.formatNumber(logisticsCosts.averageCaseValue())} so ' +
                        f'it would require higher than average dice rolls to get there for a price you could afford.')
                continue

            if currentCargo:
                for cargoRecord in currentCargo:
                    if self._isCancelledCallback and self._isCancelledCallback():
                        return
                    self._calculateTradeOption(
                        cargoRecord=cargoRecord,
                        alreadyOwned=True,
                        purchaseWorld=purchaseWorld,
                        saleWorld=saleWorld,
                        routeLogistics=routeLogistics,
                        playerBrokerDm=playerBrokerDm,
                        buyerDm=buyerDm,
                        useableFunds=useableFunds,
                        refuellingStrategy=refuellingStrategy,
                        shipCargoCapacity=None, # Cargo capacity doesn't apply for current cargo
                        shipFuelPerParsec=shipFuelPerParsec,
                        useLocalSaleBroker=useLocalSaleBroker,
                        localSaleBrokerDm=localSaleBrokerDm,
                        includeUnprofitableTrades=includeUnprofitableTrades)
                self._updateProgress(processedCount=len(currentCargo))

            if possibleCargo:
                for cargoRecord in possibleCargo:
                    if self._isCancelledCallback and self._isCancelledCallback():
                        return
                    self._calculateTradeOption(
                        cargoRecord=cargoRecord,
                        alreadyOwned=False,
                        purchaseWorld=purchaseWorld,
                        saleWorld=saleWorld,
                        routeLogistics=routeLogistics,
                        playerBrokerDm=playerBrokerDm,
                        buyerDm=buyerDm,
                        useableFunds=useableFunds,
                        refuellingStrategy=refuellingStrategy,
                        shipCargoCapacity=shipCargoCapacity,
                        shipFuelPerParsec=shipFuelPerParsec,
                        useLocalSaleBroker=useLocalSaleBroker,
                        localSaleBrokerDm=localSaleBrokerDm,
                        includeUnprofitableTrades=includeUnprofitableTrades)
                self._updateProgress(processedCount=len(possibleCargo))

    def _verifyShipSettings(
            self,
            shipTonnage: common.ScalarCalculation,
            shipCargoCapacity: common.ScalarCalculation,
            shipFuelCapacity: common.ScalarCalculation,
            shipStartingFuel: common.ScalarCalculation,
            ) -> None:
        if shipFuelCapacity.value() > shipTonnage.value():
            raise ValueError('Ship\'s fuel capacity can\'t be larger than its total tonnage')
        if shipStartingFuel.value() > shipFuelCapacity.value():
            raise ValueError('Ship\'s starting fuel can\'t be larger than its fuel capacity')
        if shipCargoCapacity.value() > shipTonnage.value():
            raise ValueError('Ship\'s cargo capacity can\'t be larger than its total tonnage')
        if (shipFuelCapacity.value() + shipCargoCapacity.value()) > shipTonnage.value():
            raise ValueError('Ship\'s combined fuel and cargo capacities can\'t be larger than its total tonnage')

    def _calculateTradeOption(
            self,
            cargoRecord: logic.CargoRecord,
            alreadyOwned: bool,
            purchaseWorld: traveller.World,
            saleWorld: traveller.World,
            routeLogistics: logic.RouteLogistics,
            playerBrokerDm: common.ScalarCalculation,
            buyerDm: typing.Union[common.ScalarCalculation, common.RangeCalculation],
            useableFunds: common.ScalarCalculation,
            refuellingStrategy: logic.RefuellingStrategy,
            shipCargoCapacity: typing.Optional[common.ScalarCalculation], # Only applies if alreadyOwned is False
            shipFuelPerParsec: common.ScalarCalculation,
            useLocalSaleBroker: bool,
            localSaleBrokerDm: typing.Optional[common.ScalarCalculation], # Only used for 1e & 2e
            includeUnprofitableTrades: bool
            ) -> None:
        tradeGood = cargoRecord.tradeGood()
        purchasePricePerTon = cargoRecord.pricePerTon()
        cargoQuantity = cargoRecord.quantity()

        if not alreadyOwned:
            cargoQuantity = Trader._calculateCargoQuantity(
                shipCargoCapacity=shipCargoCapacity,
                useableFunds=useableFunds,
                pricePerTon=purchasePricePerTon,
                availableQuantity=cargoQuantity)

            if not includeUnprofitableTrades and cargoQuantity.averageCaseValue() <= 0:
                if self._traderInfoCallback:
                    self._traderInfoCallback(
                        f'Ignoring purchase of {tradeGood.name()} on {purchaseWorld.name(includeSubsector=True)}. ' +
                        f'The average purchase price is Cr{common.formatNumber(purchasePricePerTon.averageCaseValue())} ' +
                        f'per ton so it would require higher than average dice rolls to buy at a price you could afford.')
                return

        localBrokerDm = None
        localBrokerCutPercentage = None
        if useLocalSaleBroker:
            # TODO: There is a deficiency here that I can't see how to easily fix. Exotics can be
            # legal or illegal but I don't currently have a way to represent that. As such they're
            # not explicitly illegal so a legal broker will always be used for them. The simplest
            # thing to make the trader ignore exotics as speculating them doesn't really make sense
            # as they're sale will most likely be role playing based
            localBrokerDm, localBrokerCutPercentage, _ = traveller.calculateLocalBrokerDetails(
                rules=self._rules,
                brokerDm=localSaleBrokerDm,
                blackMarket=tradeGood.isIllegal(saleWorld))

        salePricePerTon = tradeGood.calculateSalePrice(
            world=saleWorld,
            brokerDm=localBrokerDm if localBrokerDm else playerBrokerDm,
            buyerDm=buyerDm)

        if localBrokerDm != None:
            # The local broker's cut effectively drops the per ton sale price of
            # goods as they take their cut before any other overheads. In order
            # for this to work out the same as taking the cut from the final trade
            # price, it's important that we don't round here. Rounding should only
            # be done when the final price is calculated by multiplying by a quantity
            brokerCutPerTon = common.Calculator.multiply(
                lhs=common.Calculator.divideFloat(
                    lhs=salePricePerTon,
                    rhs=common.ScalarCalculation(value=100)),
                rhs=localBrokerCutPercentage,
                name='Local Broker Cut Per Ton')
            salePricePerTon = common.Calculator.subtract(
                lhs=salePricePerTon,
                rhs=brokerCutPerTon,
                name='Brokered Sale Price Per Ton')

        tradeOption = logic.TradeOption(
            cargoRecord=cargoRecord,
            purchaseWorld=purchaseWorld,
            purchasePricePerTon=purchasePricePerTon,
            saleWorld=saleWorld,
            salePricePerTon=salePricePerTon,
            cargoQuantity=cargoQuantity,
            alreadyOwned=alreadyOwned,
            routeLogistics=routeLogistics,
            tradeNotes=None)

        netProfit = tradeOption.netProfit()
        if not includeUnprofitableTrades and netProfit.averageCaseValue() <= 0:
            if self._traderInfoCallback:
                self._traderInfoCallback(
                    f'Ignoring sale of {tradeGood.name()} on {saleWorld.name(includeSubsector=True)}. ' +
                    f'The average net profit is Cr{common.formatNumber(netProfit.averageCaseValue())} so ' +
                    f'it would require higher than average dice rolls to make a profit')
            return

        tradeOption = self._generateTradeOptionNotes(
            tradeOption=tradeOption,
            shipFuelPerParsec=shipFuelPerParsec,
            refuellingStrategy=refuellingStrategy)

        if self._tradeOptionCallback:
            self._tradeOptionCallback(tradeOption)

    def _updateProgress(
            self,
            processedCount: int
            ) -> None:
        self._currentProgress += processedCount
        assert(self._currentProgress <= self._optionsToProcess)
        if self._progressCallback:
            self._progressCallback(self._currentProgress, self._optionsToProcess)

    @staticmethod
    def _calculateCargoQuantity(
            shipCargoCapacity: common.ScalarCalculation,
            useableFunds: typing.Union[common.ScalarCalculation, common.RangeCalculation],
            pricePerTon: typing.Union[common.ScalarCalculation, common.RangeCalculation],
            availableQuantity: typing.Union[common.ScalarCalculation, common.RangeCalculation]
            ) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        # Limit each of the cases to the available funds
        if pricePerTon.worstCaseValue() > 0:
            worstCaseAffordableTons = common.Calculator.min(
                lhs=common.Calculator.divideFloor(
                    lhs=useableFunds.worstCaseCalculation(),
                    rhs=pricePerTon.worstCaseCalculation()),
                rhs=availableQuantity.worstCaseCalculation())
        else:
            worstCaseAffordableTons = availableQuantity.worstCaseCalculation()

        if pricePerTon.bestCaseValue() > 0:
            bestCaseAffordableTons = common.Calculator.min(
                lhs=common.Calculator.divideFloor(
                    lhs=useableFunds.bestCaseCalculation(),
                    rhs=pricePerTon.bestCaseCalculation()),
                rhs=availableQuantity.bestCaseCalculation())
        else:
            bestCaseAffordableTons = availableQuantity.bestCaseCalculation()

        if pricePerTon.averageCaseValue() > 0:
            averageCaseAffordableTons = common.Calculator.min(
                lhs=common.Calculator.divideFloor(
                    lhs=useableFunds.averageCaseCalculation(),
                    rhs=pricePerTon.averageCaseCalculation()),
                rhs=availableQuantity.averageCaseCalculation())
        else:
            averageCaseAffordableTons = availableQuantity.averageCaseCalculation()

        affordableQuantity = common.RangeCalculation(
            worstCase=worstCaseAffordableTons,
            bestCase=bestCaseAffordableTons,
            averageCase=averageCaseAffordableTons,
            name='Affordable Quantity')

        # Limit the affordable cargo to the cargo capacity
        return common.Calculator.min(
            lhs=affordableQuantity,
            rhs=shipCargoCapacity,
            name='Cargo Quantity')

    @staticmethod
    def _generateTradeOptionNotes(
            tradeOption: logic.TradeOption,
            shipFuelPerParsec: common.ScalarCalculation,
            refuellingStrategy: logic.RefuellingStrategy
            ) -> logic.TradeOption:
        purchaseWorld = tradeOption.purchaseWorld()
        saleWorld = tradeOption.saleWorld()
        notes = []

        netProfit = tradeOption.netProfit()
        if netProfit.averageCaseValue() == 0:
            # This should only happen if the trader was told to include unprofitable trades
            notes.append('With average dice rolls this trade will only break even')
        elif netProfit.averageCaseValue() < 0:
            # This should only happen if the trader was told to include unprofitable trades
            notes.append('With average dice rolls this trade will make a loss')

        purchaseWorldRefuellingType = logic.selectRefuellingType(
            world=purchaseWorld,
            refuellingStrategy=refuellingStrategy)
        if purchaseWorldRefuellingType == None:
            notes.append('The purchase world doesn\'t allow the selected refuelling strategy')

        saleWorldRefuellingType = logic.selectRefuellingType(
            world=saleWorld,
            refuellingStrategy=refuellingStrategy)
        if saleWorldRefuellingType == None:
            notes.append('The sale world doesn\'t allow the selected refuelling strategy')

        if saleWorldRefuellingType == logic.RefuellingType.Refined or \
                saleWorldRefuellingType == logic.RefuellingType.Unrefined:
            fuelCostPerTon = traveller.starPortFuelCostPerTon(
                world=saleWorld,
                refinedFuel=saleWorldRefuellingType == logic.RefuellingType.Refined)
            assert(fuelCostPerTon)
            fuelCostToGetOffWorld = shipFuelPerParsec.value() * fuelCostPerTon.averageCaseValue()
            if netProfit.averageCaseValue() > 0 and fuelCostToGetOffWorld > 0:
                percentageOfProfit = math.ceil((fuelCostToGetOffWorld / netProfit.averageCaseValue()) * 100)
                notes.append(f'On the sale world the cost of buying the fuel for jump-1 will be Cr{fuelCostToGetOffWorld}. With average dice rolls, this will be {percentageOfProfit}% of the profits from the trade.')

        if purchaseWorld.hasTradeCode(traveller.TradeCode.LowPopulationWorld):
            notes.append(f'The purchase world has the Low Population trade code, you may struggle to find a seller')

        if saleWorld.hasTradeCode(traveller.TradeCode.LowPopulationWorld):
            notes.append(f'The sale world has the Low Population trade code, you may struggle to find a buyer')

        if notes:
            # There are notes for this trade option so create a copy of it with the notes. This is
            # a bodge due to trade options being immutable after construction
            tradeOption = logic.TradeOption(
                cargoRecord=tradeOption.originalCargoRecord(),
                purchaseWorld=tradeOption.purchaseWorld(),
                purchasePricePerTon=tradeOption.purchasePricePerTon(),
                saleWorld=tradeOption.saleWorld(),
                salePricePerTon=tradeOption.salePricePerTon(),
                cargoQuantity=tradeOption.cargoQuantity(),
                alreadyOwned=tradeOption.isAlreadyOwned(),
                routeLogistics=tradeOption.routeLogistics(),
                tradeNotes=notes)

        return tradeOption
