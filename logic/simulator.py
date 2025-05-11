import common
import enum
import logic
import functools
import random
import time
import traveller
import travellermap
import typing

# Rules for finding a supplier (seller or buyer)
# - Finding a Supplier: Average (8+) Broker check (1D days, EDU or SOC).
# - Finding a Black Market Supplier of Illegal Goods: Average (8+) Streetwise check (1D days, EDU or SOC).
# - Finding an Online Supplier (TL8+ worlds only): Average (8+) Admin check (1D hours, EDU).
# - The size of the star port provides a bonus to finding a supplier.
#   - Class A: DM+6
#   - Class B: DM+4
#   - Class C: DM+2
# - Travellers can search for multiple suppliers, but there is DM-1 per previous attempt on a planet in the same month.
# - When selling, if a Traveller does not accept the price offered for his goods, they must find another buyer or wait a month

class Simulator(object):
    class Event(object):
        class Type(enum.Enum):
            FundsUpdate = 0
            HexUpdate = 1
            InfoMessage = 2

        def __init__(
                self,
                type: Type,
                data: typing.Any,
                timestamp: int
                ) -> None:
            self._type = type
            self._data = data
            self._timestamp = timestamp

        def type(self) -> Type:
            return self._type

        def data(self) -> typing.Any:
            return self._data

        def timestamp(self) -> int:
            return self._timestamp

    StarPortModifiers = {
        'A': 6,
        'B': 4,
        'C': 2
    }

    def __init__(
            self,
            rules: traveller.Rules,
            eventCallback: typing.Optional[typing.Callable[[Event], typing.Any]] = None,
            nextStepDelayCallback: typing.Optional[typing.Callable[[], float]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> None:
        self._rules = rules
        self._eventCallback = eventCallback
        self._nextStepDelayCallback = nextStepDelayCallback
        self._isCancelledCallback = isCancelledCallback
        self._cargoManifest = None
        self._jumpRouteIndex = None
        self._actualLogisticsCost = None

    def run(
            self,
            milieu: travellermap.Milieu,
            startHex: travellermap.HexPosition,
            startingFunds: int,
            shipTonnage: int,
            shipJumpRating: int,
            shipCargoCapacity: int,
            shipFuelCapacity: int,
            jumpCostCalculator: logic.JumpCostCalculatorInterface,
            pitCostCalculator: logic.PitStopCostCalculator,
            perJumpOverheads: int,
            deadSpaceRouting: bool,
            searchRadius: int,
            minSellerDm: int,
            maxSellerDm: int,
            minBuyerDm: int,
            maxBuyerDm: int,
            playerBrokerDm: typing.Optional[int],
            playerStreetwiseDm: typing.Optional[int] = None,
            playerAdminDm: typing.Optional[int] = None,
            shipFuelPerParsec: typing.Optional[float] = None,
            randomSeed: typing.Optional[int] = None,
            simulationLength: typing.Optional[int] = None # Length in simulated hours
            ) -> None:
        self._milieu = milieu
        self._shipTonnage = shipTonnage
        self._shipJumpRating = shipJumpRating
        self._shipCargoCapacity = shipCargoCapacity
        self._shipFuelCapacity = shipFuelCapacity
        self._shipFuelPerParsec = shipFuelPerParsec
        self._perJumpOverheads = perJumpOverheads
        self._jumpCostCalculator = jumpCostCalculator
        self._pitCostCalculator = pitCostCalculator
        self._deadSpaceRouting = deadSpaceRouting
        self._searchRadius = searchRadius
        self._playerBrokerDm = playerBrokerDm
        self._playerStreetwiseDm = playerStreetwiseDm
        self._playerAdminDm = playerAdminDm
        self._minSellerDm = minSellerDm
        self._maxSellerDm = maxSellerDm
        self._minBuyerDm = minBuyerDm
        self._maxBuyerDm = maxBuyerDm
        self._randomGenerator = common.RandomGenerator(
            seed=randomSeed,
            # Use legacy mode so seeds result in the same random
            # sequence as previous versions
            legacy=True)

        self._simulationTime = 0

        if randomSeed != None:
            self._logMessage(f'Random Seed: {randomSeed}')

        # Set the funds and world like this to trigger callbacks. Note
        # that this MUST be done AFTER the simulation time is reset
        self._setCurrentHex(hex=startHex)
        self._setAvailableFunds(startingFunds)

        while self._availableFunds > 0:
            if self._isCancelledCallback and self._isCancelledCallback():
                return # Don't do bankrupt check if cancelled
            if simulationLength and (self._simulationTime > simulationLength):
                return
            self._stepSimulation()

            if self._nextStepDelayCallback:
                time.sleep(self._nextStepDelayCallback())

        self._logMessage(f'You went bankrupt!')

    def _stepSimulation(self) -> None:
        currentWorld = traveller.WorldManager.instance().worldByPosition(
            hex=self._currentHex,
            milieu=self._milieu)

        if not self._cargoManifest:
            # No current cargo manifest so buy something on the current world
            assert(currentWorld) # Should always be on a world at this point

            # Filter out worlds that don't have refuelling options that match the refuelling strategy
            worldFilterCallback = lambda world: self._pitCostCalculator.refuellingType(world=world) is not None
            self._nearbyWorlds = traveller.WorldManager.instance().worldsInRadius(
                center=self._currentHex,
                searchRadius=self._searchRadius,
                filterCallback=worldFilterCallback,
                milieu=self._milieu)

            # Buy something
            self._logMessage(f'Buying goods on {currentWorld.name(includeSubsector=True)}')
            self._runTradeLoop(
                world=currentWorld,
                onTraderCallback=self._sellerFound,
                lookingForSeller=True)
            return

        jumpRoute = self._cargoManifest.jumpRoute()
        jumpCount = jumpRoute.jumpCount()
        if jumpCount > 0:
            routeLogistics = self._cargoManifest.routeLogistics()
            refuellingPlan = routeLogistics.refuellingPlan()
            assert(refuellingPlan != None)
            pitStop = refuellingPlan.pitStop(self._jumpRouteIndex)

            if pitStop:
                assert(currentWorld)
                assert(currentWorld == pitStop.world())

                if pitStop.hasBerthing():
                    # Roll dice to calculate actual berthing cost on this world
                    # NOTE: If we've got to this point then we know berthing is
                    # taking place, it may be to pick up fuel it may be because
                    # we've reached the finish world (or some other mandatory
                    # berthing situation). It doesn't mater which it is for now,
                    # all we care is that we get the berthing cost no mater what
                    # refuelling type is being used
                    diceRoller = common.DiceRoller(
                        randomGenerator=self._randomGenerator)
                    berthingCost = self._pitCostCalculator.berthingCost(
                        world=currentWorld,
                        mandatory=True,
                        diceRoller=diceRoller)
                    assert(isinstance(berthingCost, common.ScalarCalculation))
                    berthingCost = berthingCost.value()
                    self._logMessage(
                        'Berthing at {world} for a cost of Cr{cost}'.format(
                            world=currentWorld.name(includeSubsector=True),
                            cost=berthingCost))
                    self._setAvailableFunds(self._availableFunds - berthingCost)
                    self._actualLogisticsCost += berthingCost

                refuellingType = pitStop.refuellingType()
                if refuellingType != None:
                    fuelTons = pitStop.tonsOfFuel()
                    assert(isinstance(fuelTons, common.ScalarCalculation))
                    fuelTons = fuelTons.value()

                    fuelCost = pitStop.fuelCost()
                    fuelCost = fuelCost.value() if fuelCost else 0

                    infoString = 'Refuelling at {world}, taking on {tons} tons of {type} fuel'.format(
                        world=currentWorld.name(includeSubsector=True),
                        tons=fuelTons,
                        type=refuellingType.value.lower())
                    if fuelCost > 0:
                        infoString += f' for a cost of Cr{fuelCost}'

                    self._logMessage(infoString)
                    self._setAvailableFunds(self._availableFunds - fuelCost)
                    self._actualLogisticsCost += fuelCost

            self._jumpRouteIndex += 1
            if self._jumpRouteIndex < jumpRoute.nodeCount():
                # Not reached the end of the jump route yet so move on to the next world
                nextHex, nextWorld = jumpRoute[self._jumpRouteIndex]
                currentString = traveller.WorldManager.instance().canonicalHexName(
                    hex=self._currentHex,
                    milieu=self._milieu)
                nextString = traveller.WorldManager.instance().canonicalHexName(
                    hex=nextHex,
                    milieu=self._milieu)
                self._logMessage(
                    f'Travelling from {currentString} to {nextString}')

                self._simulationTime += self._calculateTravelHours(1)

                self._setCurrentHex(hex=nextHex)
                self._logMessage(f'Arrived on {nextWorld.name(includeSubsector=True)}')
                return

            if self._perJumpOverheads:
                # Only calculate jump overheads when we reach the sale world to save spamming messages
                jumpOverheads = self._perJumpOverheads * jumpCount
                self._logMessage(f'Jump overheads of Cr{jumpOverheads} for {jumpCount} jump(s)')
                self._setAvailableFunds(self._availableFunds - jumpOverheads)
                self._actualLogisticsCost += jumpOverheads

            # We've reached the sale world
            assert(self._currentHex == jumpRoute.finishHex())
            assert(self._actualLogisticsCost <= routeLogistics.totalCosts().worstCaseValue())
            assert(self._actualLogisticsCost >= routeLogistics.totalCosts().bestCaseValue())
        else:
            assert(currentWorld) # Should always be on a world if we get here
            self._logMessage(
                f'Staying on {currentWorld.name(includeSubsector=True)} to sell goods')

        assert(currentWorld) # Should always be on a world if we get here

        # Sell what was bought
        self._logMessage(f'Selling goods on {currentWorld.name(includeSubsector=True)}')
        self._runTradeLoop(
            world=currentWorld,
            onTraderCallback=self._buyerFound,
            lookingForSeller=False)

    def _setAvailableFunds(self, amount: int):
        self._availableFunds = amount
        if self._eventCallback:
            self._eventCallback(Simulator.Event(
                Simulator.Event.Type.FundsUpdate,
                self._availableFunds,
                self._simulationTime))

    def _setCurrentHex(self, hex: travellermap.HexPosition) -> None:
        self._currentHex = hex
        if self._eventCallback:
            self._eventCallback(Simulator.Event(
                Simulator.Event.Type.HexUpdate,
                self._currentHex,
                self._simulationTime))

    def _logMessage(self, message: str):
        if self._eventCallback:
            self._eventCallback(Simulator.Event(
                Simulator.Event.Type.InfoMessage,
                message,
                self._simulationTime))

    # Note that this function doesn't take into account
    # - Travel time from between world and jump point
    # - Time spent refuelling between jumps (wilderness or star port)
    def _calculateTravelHours(
            self,
            jumps: int
            ) -> int:
        totalHours = 0
        for _ in range(jumps):
            # Jump time taken from from P148 of the MGT2 rules
            diceRoll = common.randomRollDice(
                dieCount=1,
                randomGenerator=self._randomGenerator)
            totalHours += 148 + diceRoll.value()
        return totalHours

    def _sellerFound(
            self,
            world: traveller.World,
            elapsedHours: int,
            blackMarket: bool,
            ) -> bool:
        self._simulationTime += elapsedHours

        # Calculate the goods available on the current world.

        # A random seller DM (within the specified range) is used to simulate a "real" seller
        sellerDm = self._randomGenerator.randint(self._minSellerDm, self._maxSellerDm)
        self._logMessage(f'Found {"black market " if blackMarket else ""}seller with DM{sellerDm:+} after {elapsedHours} hours')

        diceRoller = common.DiceRoller(randomGenerator=self._randomGenerator)
        cargoRecords, _ = logic.generateRandomPurchaseCargo(
            rules=self._rules,
            world=world,
            playerBrokerDm=self._playerBrokerDm,
            sellerDm=sellerDm,
            blackMarket=blackMarket,
            diceRoller=diceRoller)

        purchaseGoodsMap = {}
        for cargoRecord in cargoRecords:
            purchaseGoodsMap[cargoRecord.tradeGood()] = cargoRecord

        tradeOptions = []
        infoMessages = []

        trader = logic.Trader(
            rules=self._rules,
            milieu=self._milieu,
            tradeOptionCallback=lambda tradeOption: tradeOptions.append(tradeOption),
            traderInfoCallback=lambda infoMessage: infoMessages.append(infoMessage),
            isCancelledCallback=self._isCancelledCallback)

        trader.calculateTradeOptionsForSingleWorld(
            purchaseWorld=world,
            possibleCargo=cargoRecords,
            currentCargo=None,
            saleWorlds=self._nearbyWorlds,
            playerBrokerDm=self._playerBrokerDm,
            minBuyerDm=self._minBuyerDm,
            maxBuyerDm=self._maxBuyerDm,
            availableFunds=self._availableFunds,
            shipTonnage=self._shipTonnage,
            shipJumpRating=self._shipJumpRating,
            shipCargoCapacity=self._shipCargoCapacity,
            shipFuelCapacity=self._shipFuelCapacity,
            shipStartingFuel=0, # Simulator always starts trading on a world with no fuel
            shipFuelPerParsec=self._shipFuelPerParsec,
            routingType=logic.RoutingType.DeadSpace if self._deadSpaceRouting else logic.RoutingType.FuelBased,
            jumpCostCalculator=self._jumpCostCalculator,
            pitCostCalculator=self._pitCostCalculator,
            perJumpOverheads=self._perJumpOverheads,
            includePurchaseWorldBerthing=False, # We're already berthed for the previous sale
            includeSaleWorldBerthing=True)

        if not tradeOptions:
            self._logMessage(f'No profitable sale options, looking for another seller')
            return False # Keep looking for another trader

        cargoManifests = logic.generateCargoManifests(
            availableFunds=self._availableFunds,
            shipCargoCapacity=self._shipCargoCapacity,
            tradeOptions=tradeOptions)
        if not cargoManifests:
            # No profitable cargo manifests found
            return False # Keep looking for another trader

        self._sortCargoManifestsInPlace(cargoManifests=cargoManifests)
        self._cargoManifest = cargoManifests[0]
        self._jumpRouteIndex = 0
        self._actualLogisticsCost = 0

        # The cargo costs should be a known value as they should have been taken from the known value
        # cargo records
        cargoCosts = self._cargoManifest.cargoCost()
        assert(isinstance(cargoCosts, common.ScalarCalculation))
        cargoCosts = cargoCosts.value()

        # Buy the most profitable goods
        totalPurchaseCosts = 0
        for tradeOption in self._cargoManifest.tradeOptions():
            purchasePricePerTon = tradeOption.purchasePricePerTon()
            assert(isinstance(purchasePricePerTon, common.ScalarCalculation))
            purchasePricePerTon = purchasePricePerTon.value()

            purchaseQuantity = tradeOption.cargoQuantity()
            assert(isinstance(purchaseQuantity, common.ScalarCalculation))
            purchaseQuantity = purchaseQuantity.value()

            purchaseCost = purchasePricePerTon * purchaseQuantity

            self._logMessage(
                f'Purchased {common.formatNumber(purchaseQuantity)} tons of {tradeOption.tradeGood().name()} for Cr{common.formatNumber(purchaseCost)}')
            totalPurchaseCosts += purchaseCost
        assert(totalPurchaseCosts == cargoCosts)

        self._setAvailableFunds(self._availableFunds - cargoCosts)

        return True # Return True to stop searching for another trader

    def _buyerFound(
            self,
            world: traveller.World,
            elapsedHours: int,
            blackMarket: bool,
            ) -> bool:
        self._simulationTime += elapsedHours

        # Generate a random DM for the buyer
        buyerDm = self._randomGenerator.randint(self._minBuyerDm, self._maxBuyerDm)
        self._logMessage(f'Found {"black market " if blackMarket else ""}seller with DM{buyerDm:+} after {elapsedHours} hours')

        purchaseCargoRecords = self._cargoManifest.cargoRecords()
        saleCargoRecords, _ = logic.generateRandomSaleCargo(
            rules=self._rules,
            world=world,
            currentCargo=purchaseCargoRecords,
            playerBrokerDm=self._playerBrokerDm,
            buyerDm=buyerDm,
            blackMarket=blackMarket,
            diceRoller=common.DiceRoller(randomGenerator=self._randomGenerator))

        purchasePricePerTonMap = {}
        for purchaseOption in purchaseCargoRecords:
            pricePerTon = purchaseOption.pricePerTon()
            assert(isinstance(pricePerTon, common.ScalarCalculation))
            purchasePricePerTonMap[purchaseOption.tradeGood()] = pricePerTon.value()

        salePriceMap = {}
        totalSalePrice = 0
        totalPurchasePrice = 0
        for saleOption in saleCargoRecords:
            tradeGood = saleOption.tradeGood()

            quantity = saleOption.quantity()
            assert(isinstance(quantity, common.ScalarCalculation))
            quantity = quantity.value()

            salePricePerTon = saleOption.pricePerTon()
            assert(isinstance(salePricePerTon, common.ScalarCalculation))
            salePricePerTon = salePricePerTon.value()

            salePrice = salePricePerTon * quantity
            salePriceMap[tradeGood] = salePrice
            totalSalePrice += salePrice

            assert(tradeGood in purchasePricePerTonMap)
            purchasePricePerTon = purchasePricePerTonMap[tradeGood]
            totalPurchasePrice += purchasePricePerTon * quantity

        if not salePriceMap:
            self._logMessage(f'Buyer doesn\'t trade in the goods you have, looking for a new buyer')
            return False

        # Make the trade as long as we make a profit
        profit = totalSalePrice - (totalPurchasePrice + self._actualLogisticsCost)
        if profit <= 0:
            self._logMessage(f'Sale wouldn\'t be profitable, looking for another buyer')
            return False # Keep looking for another trader

        # It's a profitable trade so sell the goods
        unsoldCargo = []
        for tradeOption in self._cargoManifest.tradeOptions():
            tradeGood = tradeOption.tradeGood()
            if tradeGood not in salePriceMap:
                unsoldCargo.append(tradeOption)
                continue

            quantity = tradeOption.cargoQuantity()
            assert(isinstance(quantity, common.ScalarCalculation))
            quantity = quantity.value()

            salePrice = salePriceMap[tradeGood]
            self._logMessage(
                f'Sold {common.formatNumber(quantity)} tons of {tradeGood.name()} for Cr{common.formatNumber(salePrice)}')
        self._logMessage(f'Total net profit = Cr{common.formatNumber(profit)}')
        self._setAvailableFunds(self._availableFunds + totalSalePrice)

        if unsoldCargo:
            # Create a new CargoManifest for the unsold cargo
            self._cargoManifest = logic.CargoManifest(
                purchaseWorld=self._cargoManifest.purchaseWorld(),
                saleWorld=self._cargoManifest.saleWorld(),
                routeLogistics=self._cargoManifest.routeLogistics(),
                tradeOptions=unsoldCargo)

            # We've recouped the logistics cost with this sale so it doesn't apply for further sales
            self._actualLogisticsCost = 0
            return False # Keep looking for a buyer to sell remaining cargo

        self._cargoManifest = None
        self._jumpRouteIndex = None
        self._actualLogisticsCost = None
        return True # Stop looking for more traders

    def _runTradeLoop(
            self,
            world: traveller.World,
            onTraderCallback: typing.Callable[[traveller.World, int, bool], bool],
            lookingForSeller: bool
            ) -> None:
        class MethodState(object):
            def __init__(
                self, skillRating: int,
                isOnline: bool,
                blackMarket: bool,
                retryModifier: int
            ):
                self.skillRating = skillRating
                self.isOnline = isOnline
                self.blackMarket = blackMarket
                self.retryModifier = retryModifier
                self.foundTrader = False
                self.stepTime = 0.0

        lookForLegalTrader = False
        lookForBlackMarketTrader = False
        if lookingForSeller:
            # When buying always initially start looking for legal and illegal traders.
            # Which we end up looking for is determined later based on the players skills
            lookForLegalTrader = True
            lookForBlackMarketTrader = True
        else:
            # When selling only look for a trader that deals in the cargo you have
            for tradeOption in self._cargoManifest.tradeOptions():
                tradeGood = tradeOption.tradeGood()

                if tradeGood.id() != traveller.TradeGoodIds.Exotics:
                    # Look for a buyer that matches the legality of the trade good
                    if tradeGood.isIllegal(world=world):
                        lookForBlackMarketTrader = True
                    else:
                        lookForLegalTrader = True
                else:
                    # I can't see an obvious correct way to handle selling exotics as really
                    # it would depend what the exotics were. Just assume that any buyer would
                    # be interested so look for both
                    lookForLegalTrader = True
                    lookForBlackMarketTrader = True

        methods: typing.List[MethodState] = []
        if lookForLegalTrader and self._playerBrokerDm != None:
            methods.append(MethodState(
                self._playerBrokerDm,
                False, # Not online
                False, # Legal buyer/seller
                0))
        if lookForBlackMarketTrader and self._playerStreetwiseDm != None:
            methods.append(MethodState(
                self._playerStreetwiseDm,
                False, # Not online
                True, # Black market buyer/seller
                0))
        if self._playerAdminDm != None and traveller.ehexToInteger(value=world.uwp().code(traveller.UWP.Element.TechLevel), default=-1) >= 8:
            if lookForLegalTrader:
                methods.append(MethodState(
                    self._playerAdminDm,
                    True, # Is online
                    False, # Legal online buyer/seller
                    0))
            if lookForBlackMarketTrader:
                methods.append(MethodState(
                    self._playerAdminDm,
                    True, # Is online
                    True, # Black market online buyer/seller
                    0))
        if not methods:
            raise RuntimeError('No trader to look for')

        # Tracking of time is done using an integer number of hours
        MonthLength = 30 * 24

        tradeTime = 0
        lastTraderFoundTime = 0
        lastMonth = 0
        worldModifier = Simulator._starPortModifier(world=world)

        while True:
            if self._isCancelledCallback and self._isCancelledCallback():
                return

            # If it's a new month reset the retry modifiers for the different methods
            currentMonth = tradeTime // MonthLength
            if currentMonth > lastMonth:
                for method in methods:
                    method.retryModifier = 0
                lastMonth = currentMonth

            # Step the methods
            lowestMethod = None
            lowestStepTime = None
            for method in methods:
                method.foundTrader, method.stepTime = self._traderSearchStep(
                    skillRating=method.skillRating,
                    worldModifier=worldModifier,
                    retryModifier=method.retryModifier,
                    isOnline=method.isOnline)

                if method.foundTrader:
                    # A trader has been found so this becomes the current method we're going
                    # to use if it has a lower step time than the current lowest
                    if (lowestMethod == None) or (method.stepTime < lowestMethod.stepTime):
                        lowestMethod = method
                        lowestStepTime = method.stepTime
                elif lowestMethod == None:
                    # No trade was found for this method and we don't currently have a lowest
                    # method. If this method has a lower step time than previous methods use
                    # this step time as new new low
                    if (lowestStepTime == None) or (method.stepTime < lowestStepTime):
                        lowestStepTime = method.stepTime

            # Update the elapsed time by the lowest step time
            tradeTime += lowestStepTime

            # Increment the retry modifier for the method(s) that completed a step. Note that
            # there could be more than one that completed a step with the same time.
            for method in methods:
                if method.stepTime <= lowestStepTime:
                    method.retryModifier += 1

            if lowestMethod:
                stopLooking = onTraderCallback(
                    world,
                    tradeTime - lastTraderFoundTime,
                    lowestMethod.blackMarket)
                if stopLooking:
                    return
                lastTraderFoundTime = tradeTime

    @staticmethod
    def _starPortModifier(world: traveller.World) -> int:
        starPortCode = world.uwp().code(traveller.UWP.Element.StarPort)
        return 0 if starPortCode not in Simulator.StarPortModifiers else Simulator.StarPortModifiers[starPortCode]

    def _traderSearchStep(
            self,
            skillRating: int,
            worldModifier: int,
            retryModifier: int,
            isOnline: bool,
            ) -> typing.Tuple[bool, int]:
        timeRoll = common.randomRollDice(
            dieCount=1,
            randomGenerator=self._randomGenerator)
        elapsedHours = timeRoll.value() if isOnline else timeRoll.value() * 24

        skillRoll = common.randomRollDice(
            dieCount=2,
            randomGenerator=self._randomGenerator)
        foundTrader = (skillRoll.value() + skillRating + worldModifier - retryModifier) >= 8

        return (foundTrader, elapsedHours)

    @staticmethod
    def _sortCargoManifestsInPlace(cargoManifests: typing.List[logic.CargoManifest]) -> None:
        cargoManifests.sort(key=functools.cmp_to_key(Simulator._compareCargoManifests))

    @staticmethod
    def _compareCargoManifests(
            cargoManifest1: logic.CargoManifest,
            cargoManifest2: logic.CargoManifest) -> int:

        # Cargo manifests with a larger avg profit are seen as preferable
        profit1 = cargoManifest1.netProfit()
        assert(isinstance(profit1, common.RangeCalculation))
        profit2 = cargoManifest2.netProfit()
        assert(isinstance(profit1, common.RangeCalculation))
        if profit1.averageCaseValue() > profit2.averageCaseValue():
            return -1
        if profit1.averageCaseValue() < profit2.averageCaseValue():
            return 1

        # If profit is the same then closer sale world is seen as
        # preferable.
        jumpRouteLength1 = cargoManifest1.jumpCount()
        jumpRouteLength2 = cargoManifest2.jumpCount()
        if jumpRouteLength1 < jumpRouteLength2:
            return -1
        if jumpRouteLength1 > jumpRouteLength2:
            return 1

        # If jump routes are the same length order by star port modifier.
        # The higher the modifier the easier it will be to sell the
        # goods (but it doesn't affect the price)
        starPortModifier1 = Simulator._starPortModifier(cargoManifest1.saleWorld())
        starPortModifier2 = Simulator._starPortModifier(cargoManifest2.saleWorld())
        if starPortModifier1 > starPortModifier2:
            return -1
        if starPortModifier1 < starPortModifier2:
            return 1

        return 0
