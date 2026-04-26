import gui
import threading
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class WindowManager(object):
    _instance = None # Singleton instance
    _lock = threading.Lock()
    _customUniverseWindow: typing.Optional[gui.CustomUniverseWindow] = None
    _worldComparisonWindow: typing.Optional[gui.WorldComparisonWindow] = None
    _worldSearchWindow: typing.Optional[gui.WorldSearchWindow] = None
    _jumpRouteWindow: typing.Optional[gui.JumpRouteWindow] = None
    _purchaseCalculatorWindow: typing.Optional[gui.PurchaseCalculatorWindow] = None
    _saleCalculatorWindow: typing.Optional[gui.SaleCalculatorWindow] = None
    _worldTradeOptionsWindow: typing.Optional[gui.WorldTraderWindow] = None
    _multiWorldTradeOptionsWindow: typing.Optional[gui.MultiWorldTraderWindow] = None
    _simulatorWindow: typing.Optional[gui.SimulatorWindow] = None
    _hexDetailsWindow: typing.Optional[gui.HexDetailsWindow] = None
    _calculationWindow: typing.Optional[gui.CalculationWindow] = None
    _gunsmithWindow: typing.Optional[gui.GunsmithWindow] = None
    _robotBuilderWindow: typing.Optional[gui.RobotBuilderWindow] = None
    _diceRollerWindow: typing.Optional[gui.DiceRollerWindow] = None
    _mapWindows: typing.Set[gui.MapWindow] = set()

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
        if self._customUniverseWindow:
            self._customUniverseWindow.close()
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
        if self._hexDetailsWindow:
            self._hexDetailsWindow.close()
        if self._calculationWindow:
            self._calculationWindow.close()
        if self._gunsmithWindow:
            self._gunsmithWindow.close()
        if self._robotBuilderWindow:
            self._robotBuilderWindow.close()
        if self._diceRollerWindow:
            self._diceRollerWindow.close()

        for window in self._mapWindows:
            window.close()
        self._mapWindows.clear()

    def showCustomUniverseWindow(self) -> 'gui.CustomUniverseWindow':
        if not self._customUniverseWindow:
            self._customUniverseWindow = gui.CustomUniverseWindow()
        self._customUniverseWindow.bringToFront()
        return self._customUniverseWindow

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

    def showHexDetailsWindow(self) -> 'gui.HexDetailsWindow':
        if not self._hexDetailsWindow:
            self._hexDetailsWindow = gui.HexDetailsWindow()
        self._hexDetailsWindow.bringToFront()
        return self._hexDetailsWindow

    def showCalculationWindow(self) -> 'gui.CalculationWindow':
        if not self._calculationWindow:
            self._calculationWindow = gui.CalculationWindow()
        self._calculationWindow.bringToFront()
        return self._calculationWindow

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

    def showDiceRollerWindow(self) -> 'gui.DiceRollerWindow':
        if not self._diceRollerWindow:
            self._diceRollerWindow = gui.DiceRollerWindow()
        self._diceRollerWindow.bringToFront()
        return self._diceRollerWindow

    # NOTE: Unlike most windows, a new map window is created each time this function is
    # called. This is primarily done because most uses of the map window add overlays to
    # the map and you don't want them to hang around if the window was to be reused. I can
    # also see advantages from a users point of view as it allows them to be looking at
    # two worlds at once (but closing multiple windows could be a pain).
    def createMapWindow(self) -> 'gui.MapWindow':
        mapWindow = gui.MapWindow()
        mapWindow.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        mapWindow.show()
        WindowManager._mapWindows.add(mapWindow)
        mapWindow.destroyed.connect(lambda: WindowManager._mapWindows.discard(mapWindow))
        return mapWindow