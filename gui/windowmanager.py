import gui
import threading

class WindowManager(object):
    _instance = None # Singleton instance
    _lock = threading.Lock()
    _worldComparisonWindow = None
    _worldSearchWindow = None
    _jumpRouteWindow = None
    _purchaseCalculatorWindow = None
    _saleCalculatorWindow = None
    _worldTradeOptionsWindow = None
    _multiWorldTradeOptionsWindow = None
    _simulatorWindow = None
    _worldDetailsWindow = None
    _calculationWindow = None
    _travellerMapWindow = None
    _gunsmithWindow = None
    _robotBuilderWindow = None

    def __init__(self) -> None:
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls) -> 'WindowManager':
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check adn the lock
                if not cls._instance:
                    cls._instance = cls.__new__(cls)
        return cls._instance

    def closeWindows(self) -> None:
        if self._worldComparisonWindow:
            self._worldComparisonWindow.close()
        if self._worldSearchWindow:
            self._worldSearchWindow.close()
        if self._jumpRouteWindow:
            self._jumpRouteWindow.close()
        if self._purchaseCalculatorWindow:
            self._purchaseCalculatorWindow.close()
        if self._saleCalculatorWindow:
            self._saleCalculatorWindow.close()
        if self._worldTradeOptionsWindow:
            self._worldTradeOptionsWindow.close()
        if self._multiWorldTradeOptionsWindow:
            self._multiWorldTradeOptionsWindow.close()
        if self._simulatorWindow:
            self._simulatorWindow.close()
        if self._worldDetailsWindow:
            self._worldDetailsWindow.close()
        if self._calculationWindow:
            self._calculationWindow.close()
        if self._travellerMapWindow:
            self._travellerMapWindow.close()
        if self._gunsmithWindow:
            self._gunsmithWindow.close()
        if self._robotBuilderWindow:
            self._robotBuilderWindow.close()

    def showWorldComparisonWindow(self) -> 'gui.WorldComparisonWindow':
        if not self._worldComparisonWindow:
            self._worldComparisonWindow = gui.WorldComparisonWindow()
        self._worldComparisonWindow.bringToFront()
        return self._worldComparisonWindow

    def showWorldSearchWindow(self) -> 'gui.WorldSearchWindow':
        if not self._worldSearchWindow:
            self._worldSearchWindow = gui.WorldSearchWindow()
        self._worldSearchWindow.bringToFront()
        return self._worldSearchWindow

    def showJumpRouteWindow(self) -> 'gui.JumpRouteWindow':
        if not self._jumpRouteWindow:
            self._jumpRouteWindow = gui.JumpRouteWindow()
        self._jumpRouteWindow.bringToFront()
        return self._jumpRouteWindow

    def showPurchaseCalculatorWindow(self) -> 'gui.PurchaseCalculatorWindow':
        if not self._purchaseCalculatorWindow:
            self._purchaseCalculatorWindow = gui.PurchaseCalculatorWindow()
        self._purchaseCalculatorWindow.bringToFront()
        return self._purchaseCalculatorWindow

    def showSaleCalculatorWindow(self) -> 'gui.SaleCalculatorWindow':
        if not self._saleCalculatorWindow:
            self._saleCalculatorWindow = gui.SaleCalculatorWindow()
        self._saleCalculatorWindow.bringToFront()
        return self._saleCalculatorWindow

    def showWorldTradeOptionsWindow(self) -> 'gui.WorldTraderWindow':
        if not self._worldTradeOptionsWindow:
            self._worldTradeOptionsWindow = gui.WorldTraderWindow()
        self._worldTradeOptionsWindow.bringToFront()
        return self._worldTradeOptionsWindow

    def showMultiWorldTradeOptionsWindow(self) -> 'gui.MultiWorldTraderWindow':
        if not self._multiWorldTradeOptionsWindow:
            self._multiWorldTradeOptionsWindow = gui.MultiWorldTraderWindow()
        self._multiWorldTradeOptionsWindow.bringToFront()
        return self._multiWorldTradeOptionsWindow

    def showSimulatorWindow(self) -> 'gui.SimulatorWindow':
        if not self._simulatorWindow:
            self._simulatorWindow = gui.SimulatorWindow()
        self._simulatorWindow.bringToFront()
        return self._simulatorWindow

    def showWorldDetailsWindow(self) -> 'gui.WorldDetailsWindow':
        if not self._worldDetailsWindow:
            self._worldDetailsWindow = gui.WorldDetailsWindow()
        self._worldDetailsWindow.bringToFront()
        return self._worldDetailsWindow

    def showCalculationWindow(self) -> 'gui.CalculationWindow':
        if not self._calculationWindow:
            self._calculationWindow = gui.CalculationWindow()
        self._calculationWindow.bringToFront()
        return self._calculationWindow

    def showTravellerMapWindow(self) -> 'gui.TravellerMapWindow':
        if not self._travellerMapWindow:
            self._travellerMapWindow = gui.TravellerMapWindow()
        self._travellerMapWindow.bringToFront()
        return self._travellerMapWindow

    def showGunsmithWindow(self) -> 'gui.GunsmithWindow':
        if not self._gunsmithWindow:
            self._gunsmithWindow = gui.GunsmithWindow()
        self._gunsmithWindow.bringToFront()
        return self._gunsmithWindow

    def showRobotBuilderWindow(self) -> 'gui.RobotBuilderWindow':
        if not self._robotBuilderWindow:
            self._robotBuilderWindow = gui.RobotBuilderWindow()
        self._robotBuilderWindow.bringToFront()
        return self._robotBuilderWindow