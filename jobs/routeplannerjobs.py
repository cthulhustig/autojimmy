import logic
import time
import traveller
import travellermap
import typing
from PyQt5 import QtCore

class RoutePlannerJob(QtCore.QThread):
    # Signals MUST be defined at the class level (i.e. static). Qt does magic
    # when the super() is called to create per-instance interfaces to the
    # signals
    _progressSignal = QtCore.pyqtSignal([int])
    # See comment below as to why this uses a list rather than a JumpRoute
    _finishedSignal = QtCore.pyqtSignal([list], [Exception])

    _MinProgressInterval = 0.5

    def __init__(
            self,
            parent: QtCore.QObject,
            routingType: logic.RoutingType,
            milieu: travellermap.Milieu,
            hexSequence: typing.Sequence[traveller.World],
            shipTonnage: int,
            shipJumpRating: int,
            shipFuelCapacity: int,
            shipCurrentFuel: float,
            shipFuelPerParsec: typing.Optional[float],
            jumpCostCalculator: logic.JumpCostCalculatorInterface, # This will be called from the worker thread
            pitCostCalculator: typing.Optional[logic.PitStopCostCalculator], # This will be called from the worker thread
            hexFilter: typing.Optional[logic.HexFilterInterface] = None, # This will be called from the worker thread
            progressCallback: typing.Callable[[int, bool], typing.Any] = None,
            finishedCallback: typing.Callable[[typing.Union[logic.JumpRoute, Exception]], typing.Any] = None
            ) -> None:
        super().__init__(parent=parent)

        # When setting class variables copies should be made of all complex objects
        # to prevent issues if they are modified while the thread is running. The
        # exception to this is world objects as they are thread safe (although lists
        # holding them do need to be copied)
        self._routingType = routingType
        self._milieu = milieu
        self._hexSequence = list(hexSequence)
        self._shipTonnage = shipTonnage
        self._shipJumpRating = shipJumpRating
        self._shipFuelCapacity = shipFuelCapacity
        self._shipCurrentFuel = shipCurrentFuel
        self._shipFuelPerParsec = shipFuelPerParsec
        self._jumpCostCalculator = jumpCostCalculator
        self._pitCostCalculator = pitCostCalculator
        self._hexFilter = hexFilter

        self._planner = logic.RoutePlanner()
        self._lastProgressTimestamp = None

        if progressCallback:
            self._progressSignal[int].connect(progressCallback)
        if finishedCallback:
            # This is a MASSIVE bodge. When I switched to having jump routes as a class rather than
            # just a list of worlds I found the onFinishedCallback was being called twice. It seems
            # to be related to the fact there are two variants of the signal handler, somewhat
            # verified by the fact I stopped getting the second notification when I commented out the
            # line to connect the exception variant. I don't know if this is a bug in pyqtSignal or
            # (more likely) something I'm not understanding about it or Python typing in general. The
            # fix I've put in place is to pass the jump route to the signal as a single element list
            # then have a lambda that passes the first element to the real onFinishedCallback.
            finishedWrapper = lambda jumpRouteList: finishedCallback(jumpRouteList[0])
            self._finishedSignal[list].connect(finishedWrapper)
            self._finishedSignal[Exception].connect(finishedCallback)
        self._cancelled = False

    def cancel(self, block=False) -> None:
        self._cancelled = True
        if block:
            self.quit()
            self.wait()

    def isCancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        try:
            jumpRoute = self._planner.calculateSequenceRoute(
                routingType=self._routingType,
                milieu=self._milieu,
                hexSequence=self._hexSequence,
                shipTonnage=self._shipTonnage,
                shipJumpRating=self._shipJumpRating,
                shipFuelCapacity=self._shipFuelCapacity,
                shipCurrentFuel=self._shipCurrentFuel,
                shipFuelPerParsec=self._shipFuelPerParsec,
                jumpCostCalculator=self._jumpCostCalculator,
                pitCostCalculator=self._pitCostCalculator,
                hexFilter=self._hexFilter,
                progressCallback=self._handleProgress,
                isCancelledCallback=self.isCancelled)

            # See comment above as to why this uses a list rather than a JumpRoute
            self._finishedSignal[list].emit([jumpRoute])
        except Exception as ex:
            self._finishedSignal[Exception].emit(ex)

    def _handleProgress(
            self,
            routeCount: int,
            isFinished: bool
            ) -> None:
        currentTimestamp = time.time()
        shouldEmit = isFinished or \
            (not self._lastProgressTimestamp) or \
            ((currentTimestamp - self._lastProgressTimestamp) >= RoutePlannerJob._MinProgressInterval)
        if shouldEmit:
            self._progressSignal.emit(routeCount)
            self._lastProgressTimestamp = currentTimestamp

            # Yield this thread to stop the gui from locking up
            # due to having to process to many events
            time.sleep(0.0001)
