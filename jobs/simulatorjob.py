import logic
import time
import traveller
import travellermap
import typing
from PyQt5 import QtCore

class SimulatorJob(QtCore.QThread):
    # Signals MUST be defined at the class level (i.e. static). Qt does magic
    # when the super() is called to create per-instance interfaces to the
    # signals
    _eventSignal = QtCore.pyqtSignal([logic.Simulator.Event])
    _finishedSignal = QtCore.pyqtSignal([str], [Exception])

    def __init__(
            self,
            parent: QtCore.QObject,
            rules: traveller.Rules,
            startHex: travellermap.HexPosition,
            startingFunds: int,
            shipTonnage: int,
            shipJumpRating: int,
            shipCargoCapacity: int,
            shipFuelCapacity: int,
            shipFuelPerParsec: typing.Optional[float],
            jumpCostCalculator: logic.JumpCostCalculatorInterface,
            pitCostCalculator: logic.PitStopCostCalculator,
            perJumpOverheads: int,
            deadSpaceRouting: bool,
            searchRadius: int,
            playerBrokerDm: int,
            playerStreetwiseDm: typing.Optional[int],
            playerAdminDm: typing.Optional[int],
            minSellerDm: int,
            maxSellerDm: int,
            minBuyerDm: int,
            maxBuyerDm: int,
            randomSeed: typing.Optional[int] = None,
            simulationLength: typing.Optional[int] = None, # Length in simulated hours
            stepInterval: float = 2.0, # In seconds
            eventCallback: typing.Optional[typing.Callable[[logic.Simulator.Event], typing.Any]] = None,
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any] = None
            ) -> None:
        super().__init__(parent=parent)

        # When setting class variables copies should be made of all complex objects
        # to prevent issues if they are modified while the thread is running. The
        # exception to this is world objects as they are thread safe (although lists
        # holding them do need to be copied)
        self._startHex = startHex
        self._startingFunds = startingFunds
        self._shipTonnage = shipTonnage
        self._shipJumpRating = shipJumpRating
        self._shipCargoCapacity = shipCargoCapacity
        self._shipFuelCapacity = shipFuelCapacity
        self._shipFuelPerParsec = shipFuelPerParsec
        self._jumpCostCalculator = jumpCostCalculator
        self._pitCostCalculator = pitCostCalculator
        self._perJumpOverheads = perJumpOverheads
        self._deadSpaceRouting = deadSpaceRouting
        self._searchRadius = searchRadius
        self._playerBrokerDm = playerBrokerDm
        self._playerStreetwiseDm = playerStreetwiseDm
        self._playerAdminDm = playerAdminDm
        self._minSellerDm = minSellerDm
        self._maxSellerDm = maxSellerDm
        self._minBuyerDm = minBuyerDm
        self._maxBuyerDm = maxBuyerDm
        self._randomSeed = randomSeed
        self._simulationLength = simulationLength
        self._stepInterval = stepInterval

        self._simulator = logic.Simulator(
            rules=rules,
            eventCallback=self._handleEvent if eventCallback else None,
            nextStepDelayCallback=self._nextStepDelay,
            isCancelledCallback=self.isCancelled)

        if eventCallback:
            self._eventSignal[logic.Simulator.Event].connect(eventCallback)
        if finishedCallback:
            self._finishedSignal[str].connect(finishedCallback)
            self._finishedSignal[Exception].connect(finishedCallback)

        self._cancelled = False

    def setStepInterval(self, seconds: float) -> None:
        self._stepInterval = seconds

    def cancel(self, block=False) -> None:
        self._cancelled = True
        if block:
            self.quit()
            self.wait()

    def isCancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        try:
            self._simulator.run(
                startHex=self._startHex,
                startingFunds=self._startingFunds,
                shipTonnage=self._shipTonnage,
                shipJumpRating=self._shipJumpRating,
                shipCargoCapacity=self._shipCargoCapacity,
                shipFuelCapacity=self._shipFuelCapacity,
                shipFuelPerParsec=self._shipFuelPerParsec,
                jumpCostCalculator=self._jumpCostCalculator,
                pitCostCalculator=self._pitCostCalculator,
                perJumpOverheads=self._perJumpOverheads,
                deadSpaceRouting=self._deadSpaceRouting,
                searchRadius=self._searchRadius,
                playerBrokerDm=self._playerBrokerDm,
                playerStreetwiseDm=self._playerStreetwiseDm,
                playerAdminDm=self._playerAdminDm,
                minSellerDm=self._minSellerDm,
                maxSellerDm=self._maxSellerDm,
                minBuyerDm=self._minBuyerDm,
                maxBuyerDm=self._maxBuyerDm,
                randomSeed=self._randomSeed,
                simulationLength=self._simulationLength)

            self._finishedSignal[str].emit('Finished')
        except Exception as ex:
            self._finishedSignal[Exception].emit(ex)

    def _handleEvent(self, event: logic.Simulator.Event) -> None:
        self._eventSignal.emit(event)

        # Yield this thread to stop the gui from locking up
        # due to having to process to many events
        time.sleep(0.0001)

    def _nextStepDelay(self) -> float:
        return self._stepInterval
