import common
import datetime
import logic
import time
import traveller
import typing
from PyQt5 import QtCore

class _TraderJobBase(QtCore.QThread):
    _tradeOptionsSignal = QtCore.pyqtSignal([list])
    _tradeInfoSignal = QtCore.pyqtSignal([list])
    _progressSignal = QtCore.pyqtSignal([int, int])
    _finishedSignal = QtCore.pyqtSignal([str], [Exception])

    def __init__(
            self,
            parent: QtCore.QObject,
            rules: traveller.Rules,
            tradeOptionCallback: typing.Callable[[typing.List[logic.TradeOption]], typing.Any],
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any],
            tradeInfoCallback: typing.Optional[typing.Callable[[str], typing.Any]] = None,
            progressCallback: typing.Optional[typing.Callable[[int, int], typing.Any]] = None,
            tradeOptionsPerUpdate=10,
            infoStringsPerUpdate=100,
            yieldIntervalMs=20
            ) -> None:
        super().__init__(parent=parent)

        self._trader = logic.Trader(
            rules=rules,
            tradeOptionCallback=self._handleTradeOption,
            traderInfoCallback=self._handleTradeInfo,
            progressCallback=self._handleProgress,
            isCancelledCallback=self.isCancelled)

        self._tradeOptionsSignal[list].connect(tradeOptionCallback)
        self._finishedSignal[str].connect(finishedCallback)
        self._finishedSignal[Exception].connect(finishedCallback)

        if tradeInfoCallback:
            self._tradeInfoSignal[list].connect(tradeInfoCallback)
        if progressCallback:
            self._progressSignal[int, int].connect(progressCallback)

        self._tradeOptionsPerUpdate = tradeOptionsPerUpdate
        self._infoStringsPerUpdate = infoStringsPerUpdate
        self._tradeOptions = []
        self._infoStrings = []
        self._yieldDelta = datetime.timedelta(milliseconds=yieldIntervalMs)
        self._lastYieldTime = None
        self._cancelled = False
        self.start()

    def cancel(self, block=False) -> None:
        self._cancelled = True
        if block:
            self.quit()
            self.wait()

    def isCancelled(self) -> bool:
        return self._cancelled

    def _handleTradeOption(self, tradeOption: logic.TradeOption) -> None:
        self._tradeOptions.append(tradeOption)
        if len(self._tradeOptions) >= self._tradeOptionsPerUpdate:
            self._emitTradeOptions()
        self._yieldIfNeeded()

    def _handleTradeInfo(self, tradeInfo: str) -> None:
        self._infoStrings.append(tradeInfo)
        if len(self._infoStrings) >= self._infoStringsPerUpdate:
            self._emitTradeInfo()
        self._yieldIfNeeded()

    def _handleProgress(
            self,
            currentProgress: int,
            optionsToProcess: int
            ) -> None:
        self._progressSignal.emit(currentProgress, optionsToProcess)
        self._yieldIfNeeded()

    def _emitTradeOptions(self) -> None:
        self._tradeOptionsSignal.emit(self._tradeOptions)
        self._tradeOptions = []

    def _emitTradeInfo(self) -> None:
        self._tradeInfoSignal.emit(self._infoStrings)
        self._infoStrings = []

    def _yieldIfNeeded(self) -> None:
        now = datetime.datetime.now()
        shouldYield = (self._lastYieldTime == None) or \
            ((now - self._lastYieldTime) >= self._yieldDelta)
        if shouldYield:
            time.sleep(0.01)
            self._lastYieldTime = now

class SingleWorldTraderJob(_TraderJobBase):
    def __init__(
            self,
            parent: QtCore.QObject,
            rules: traveller.Rules,
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
            shipFuelPerParsec: typing.Optional[typing.Union[float, common.ScalarCalculation]],
            perJumpOverheads: typing.Union[int, common.ScalarCalculation],
            jumpCostCalculator: logic.JumpCostCalculatorInterface,
            refuellingStrategy: logic.RefuellingStrategy,
            useLocalSaleBroker: bool,
            localSaleBrokerDm: typing.Optional[typing.Union[int, common.ScalarCalculation]],
            includePurchaseWorldBerthing: bool,
            includeSaleWorldBerthing: bool,
            includeLogisticsCosts: bool,
            includeUnprofitableTrades: bool,
            tradeOptionCallback: typing.Callable[[typing.List[logic.TradeOption]], typing.Any],
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any],
            tradeInfoCallback: typing.Optional[typing.Callable[[str], typing.Any]] = None,
            progressCallback: typing.Optional[typing.Callable[[int, int], typing.Any]] = None,
            ) -> None:
        # When setting class variables copies should be made of all complex objects
        # to prevent issues if they are modified while the thread is running. The
        # exception to this is world objects as they are thread safe (although lists
        # holding them do need to be copied)
        self._purchaseWorld = purchaseWorld
        self._saleWorlds = saleWorlds.copy()
        self._currentCargo = currentCargo.copy()
        self._possibleCargo = possibleCargo.copy()
        self._playerBrokerDm = playerBrokerDm
        self._minBuyerDm = minBuyerDm
        self._maxBuyerDm = maxBuyerDm
        self._availableFunds = availableFunds
        self._shipTonnage = shipTonnage
        self._shipJumpRating = shipJumpRating
        self._shipCargoCapacity = shipCargoCapacity
        self._shipFuelCapacity = shipFuelCapacity
        self._shipStartingFuel = shipStartingFuel
        self._shipFuelPerParsec = shipFuelPerParsec
        self._perJumpOverheads = perJumpOverheads
        self._jumpCostCalculator = jumpCostCalculator
        self._refuellingStrategy = refuellingStrategy
        self._useLocalSaleBroker = useLocalSaleBroker
        self._localSaleBrokerDm = localSaleBrokerDm
        self._includePurchaseWorldBerthing = includePurchaseWorldBerthing
        self._includeSaleWorldBerthing = includeSaleWorldBerthing
        self._includeLogisticsCosts = includeLogisticsCosts
        self._includeUnprofitableTrades = includeUnprofitableTrades

        super().__init__(
            parent=parent,
            rules=rules,
            tradeOptionCallback=tradeOptionCallback,
            finishedCallback=finishedCallback,
            tradeInfoCallback=tradeInfoCallback,
            progressCallback=progressCallback)

    def run(self) -> None:
        try:
            self._trader.calculateTradeOptionsForSingleWorld(
                purchaseWorld=self._purchaseWorld,
                saleWorlds=self._saleWorlds,
                currentCargo=self._currentCargo,
                possibleCargo=self._possibleCargo,
                playerBrokerDm=self._playerBrokerDm,
                minBuyerDm=self._minBuyerDm,
                maxBuyerDm=self._maxBuyerDm,
                availableFunds=self._availableFunds,
                shipTonnage=self._shipTonnage,
                shipJumpRating=self._shipJumpRating,
                shipCargoCapacity=self._shipCargoCapacity,
                shipFuelCapacity=self._shipFuelCapacity,
                shipStartingFuel=self._shipStartingFuel,
                shipFuelPerParsec=self._shipFuelPerParsec,
                perJumpOverheads=self._perJumpOverheads,
                jumpCostCalculator=self._jumpCostCalculator,
                refuellingStrategy=self._refuellingStrategy,
                useLocalSaleBroker=self._useLocalSaleBroker,
                localSaleBrokerDm=self._localSaleBrokerDm,
                includePurchaseWorldBerthing=self._includePurchaseWorldBerthing,
                includeSaleWorldBerthing=self._includeSaleWorldBerthing,
                includeLogisticsCosts=self._includeLogisticsCosts,
                includeUnprofitableTrades=self._includeUnprofitableTrades)

            self._emitTradeOptions()
            self._emitTradeInfo()
            self._finishedSignal[str].emit('Finished')
        except Exception as ex:
            self._emitTradeOptions()
            self._emitTradeInfo()
            self._finishedSignal[Exception].emit(ex)

class MultiWorldTraderJob(_TraderJobBase):
    def __init__(
            self,
            parent: QtCore.QObject,
            rules: traveller.Rules,
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
            shipFuelPerParsec: typing.Optional[typing.Union[float, common.ScalarCalculation]],
            perJumpOverheads: typing.Union[int, common.ScalarCalculation],
            jumpCostCalculator: logic.JumpCostCalculatorInterface,
            refuellingStrategy: logic.RefuellingStrategy,
            useLocalPurchaseBroker: bool,
            localPurchaseBrokerDm: typing.Optional[typing.Union[int, common.ScalarCalculation]],
            useLocalSaleBroker: bool,
            localSaleBrokerDm: typing.Optional[typing.Union[int, common.ScalarCalculation]],
            includePurchaseWorldBerthing: bool,
            includeSaleWorldBerthing: bool,
            includeLogisticsCosts: bool,
            includeUnprofitableTrades: bool,
            tradeOptionCallback: typing.Callable[[logic.TradeOption], typing.Any],
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any],
            tradeInfoCallback: typing.Optional[typing.Callable[[str], typing.Any]] = None,
            progressCallback: typing.Optional[typing.Callable[[int, int], typing.Any]] = None,
            ) -> None:
        # Make a copy of the worlds list so it can't be modified
        # while the thread is running.
        self._purchaseWorlds = purchaseWorlds.copy()
        self._saleWorlds = saleWorlds.copy()
        self._playerBrokerDm = playerBrokerDm
        self._minSellerDm = minSellerDm
        self._maxSellerDm = maxSellerDm
        self._minBuyerDm = minBuyerDm
        self._maxBuyerDm = maxBuyerDm
        self._includeIllegal = includeIllegal
        self._availableFunds = availableFunds
        self._shipTonnage = shipTonnage
        self._shipJumpRating = shipJumpRating
        self._shipCargoCapacity = shipCargoCapacity
        self._shipFuelCapacity = shipFuelCapacity
        self._shipStartingFuel = shipStartingFuel
        self._shipFuelPerParsec = shipFuelPerParsec
        self._perJumpOverheads = perJumpOverheads
        self._jumpCostCalculator = jumpCostCalculator
        self._refuellingStrategy = refuellingStrategy
        self._useLocalPurchaseBroker = useLocalPurchaseBroker
        self._localPurchaseBrokerDm = localPurchaseBrokerDm
        self._useLocalSaleBroker = useLocalSaleBroker
        self._localSaleBrokerDm = localSaleBrokerDm
        self._includePurchaseWorldBerthing = includePurchaseWorldBerthing
        self._includeSaleWorldBerthing = includeSaleWorldBerthing
        self._includeLogisticsCosts = includeLogisticsCosts
        self._includeUnprofitableTrades = includeUnprofitableTrades

        super().__init__(
            parent=parent,
            rules=rules,
            tradeOptionCallback=tradeOptionCallback,
            finishedCallback=finishedCallback,
            tradeInfoCallback=tradeInfoCallback,
            progressCallback=progressCallback)

    def run(self) -> None:
        try:
            self._trader.calculateTradeOptionsForMultipleWorlds(
                purchaseWorlds=self._purchaseWorlds,
                saleWorlds=self._saleWorlds,
                playerBrokerDm=self._playerBrokerDm,
                minSellerDm=self._minSellerDm,
                maxSellerDm=self._maxSellerDm,
                minBuyerDm=self._minBuyerDm,
                maxBuyerDm=self._maxBuyerDm,
                includeIllegal=self._includeIllegal,
                availableFunds=self._availableFunds,
                shipTonnage=self._shipTonnage,
                shipJumpRating=self._shipJumpRating,
                shipCargoCapacity=self._shipCargoCapacity,
                shipFuelCapacity=self._shipFuelCapacity,
                shipStartingFuel=self._shipStartingFuel,
                shipFuelPerParsec=self._shipFuelPerParsec,
                perJumpOverheads=self._perJumpOverheads,
                jumpCostCalculator=self._jumpCostCalculator,
                refuellingStrategy=self._refuellingStrategy,
                useLocalPurchaseBroker=self._useLocalPurchaseBroker,
                localPurchaseBrokerDm=self._localPurchaseBrokerDm,
                useLocalSaleBroker=self._useLocalSaleBroker,
                localSaleBrokerDm=self._localSaleBrokerDm,
                includePurchaseWorldBerthing=self._includePurchaseWorldBerthing,
                includeSaleWorldBerthing=self._includeSaleWorldBerthing,
                includeLogisticsCosts=self._includeLogisticsCosts,
                includeUnprofitableTrades=self._includeUnprofitableTrades)

            self._emitTradeOptions()
            self._emitTradeInfo()
            self._finishedSignal[str].emit('Finished')
        except Exception as ex:
            self._emitTradeOptions()
            self._emitTradeInfo()
            self._finishedSignal[Exception].emit(ex)
