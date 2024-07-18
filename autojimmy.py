#!/usr/bin/env python3

# This should always be imported first. It will exit the app with more helpful message if any
# external dependencies are missing (assuming I remember to keep the list up to date)
import depschecker

import app
import enum
import gui
import gunsmith
import locale
import logging
import multiprocessing
import os
import pathlib
import proxy
import qasync
import robots
import socket
import sys
import traveller
import travellermap
import uuid
import typing
from PyQt5 import QtWidgets, QtGui, QtCore

_SingletonAppId = 'd2b192d8-4007-4588-bb80-8bd9721e9bcc'

_WelcomeMessage = """
    <html>
    <h2><center>Welcome to {name} v{version}</center></h2>
    <p>{name} is a collection of tools for the Traveller RPG. It's primarily aimed at Mongoose
    Traveller, but much of the functionality can be used with other rule systems.</p>
    <p>An internet connection is recommended when using {name} but not required. {name} comes with a
    snapshot of the universe data from Traveller Map, this allows most functionality to work when
    offline. An internet connection allows {name} to integrate with Traveller Map in order to allow
    more advanced UI features.<br>
    If you don't have an internet connection, it's recommended to disable the showing of world
    images in tool tips (see Configuration dialog).<p>
    <p>{name} is not endorsed by the wonderful people at Traveller Map, Mongoose Publishing or Far
    Future Enterprises. However, a great deal of thanks goes to Joshua Bell from Traveller Map for
    his help with the integration and Geir Lanesskog for his clarification of rules from the
    Mongoose Robots Handbook.</p>
    <p>{name} is released under the GPLv3. Further information can be found in the About dialog.</p>
    </html>
""".format(name=app.AppName, version=app.AppVersion)

# Works on the assumption the main file is in the root of the code/data hierarchy
def _installDirectory() -> str:
    return os.path.dirname(os.path.realpath(__file__))

def _applicationDirectory() -> str:
    if os.name == 'nt':
        return os.path.join(os.getenv('APPDATA'), app.AppName)
    else:
        return os.path.join(pathlib.Path.home(), '.' + app.AppName.lower())

def _cairoSvgInstallCheck(
        parent: typing.Optional[QtWidgets.QWidget] = None
        ) -> bool: # True if the application should continue, or False if it should exit
    if depschecker.DetectedCairoSvgState == depschecker.CairoSvgState.Working:
        return True # CairoSVG is working so app should continue

    svgCustomSectors = []
    sectors = travellermap.DataStore.instance().sectors(app.Config.instance().milieu())
    for sector in sectors:
        mapLevels = sector.customMapLevels()
        if not mapLevels:
            continue
        for mapLevel in mapLevels.values():
            if mapLevel.format() == travellermap.MapFormat.SVG:
                svgCustomSectors.append(sector.canonicalName())
                break

    alwaysShowPrompt = False
    if depschecker.DetectedCairoSvgState == depschecker.CairoSvgState.NotInstalled:
        promptMessage = 'The CairoSVG Python package is not installed.'
        promptIcon = QtWidgets.QMessageBox.Icon.Information
        logging.info(promptMessage)
    elif depschecker.DetectedCairoSvgState == depschecker.CairoSvgState.NoLibraries:
        promptMessage = 'The CairoSVG Python package is installed but it failed to find the Cairo libraries that it requires.'
        promptIcon = QtWidgets.QMessageBox.Icon.Warning
        logging.warning(promptMessage)
    else:
        promptMessage = 'The CairoSVG Python package is in an unknown state.'
        promptIcon = QtWidgets.QMessageBox.Icon.Critical
        alwaysShowPrompt = True
        logging.error(promptMessage)

    promptMessage += \
        '<br><br>New custom sector posters will be created using PNG images. This can ' \
        'introduce more visual artifacts around the borders of custom sectors when ' \
        'compositing them onto tiles returned by Traveller Map.'

    if svgCustomSectors:
        # Always show the prompt if there are SVG sectors that won't be rendered
        alwaysShowPrompt = True

        promptMessage += '<br><br>Existing custom sectors that use SVG posters will be disabled.'

        if len(svgCustomSectors) <= 4:
            promptMessage += ' The following custom sectors are currently using SVG posters:'
            for sectorName in svgCustomSectors:
                promptMessage += '<br>' + sectorName
        else:
            promptMessage += f' There are currently {len(svgCustomSectors)} custom sectors using SVG posters.'

    promptMessage += '<br><br>Details on how to install the CairoSVG package and its required libraries can ' \
        f'be found at <a href=\'{app.AppURL}\'>{app.AppURL}</a>.'
    promptMessage += f'<br><br>Do you want to continue loading {app.AppName}?'

    promptMessage = f'<html>{promptMessage}</html>'

    promptTitle = 'Prompt'
    promptButtons = QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
    promptDefaultButton = QtWidgets.QMessageBox.StandardButton.Yes
    if alwaysShowPrompt:
        answer = gui.MessageBoxEx.showMessageBox(
            parent=parent,
            title=promptTitle,
            icon=promptIcon,
            text=promptMessage,
            buttons=promptButtons,
            defaultButton=promptDefaultButton)
    else:
        answer = gui.AutoSelectMessageBox.showMessageBox(
            parent=parent,
            title=promptTitle,
            icon=promptIcon,
            text=promptMessage,
            buttons=promptButtons,
            defaultButton=promptDefaultButton,
            stateKey='ContinueIfCairoSvgNotWorking',
            rememberState=QtWidgets.QMessageBox.StandardButton.Yes) # Only remember if the user clicked yes

    return answer == QtWidgets.QMessageBox.StandardButton.Yes

class _SnapshotCheckResult(enum.Enum):
    NoUpdate = 0
    UpdateInstalled = 1
    IncompatibleUpdate = 2
    ExitRequested = 3
    Cancelled = 4

def _snapshotUpdateCheck(
        isStartup: bool,
        parent: typing.Optional[QtWidgets.QWidget] = None
        ) -> _SnapshotCheckResult:
    snapshotAvailability = travellermap.DataStore.instance().checkForNewSnapshot()

    if snapshotAvailability == travellermap.DataStore.SnapshotAvailability.NoNewSnapshot:
        return _SnapshotCheckResult.NoUpdate

    if snapshotAvailability != travellermap.DataStore.SnapshotAvailability.NewSnapshotAvailable:
        promptMessage = 'New universe data is available, however it can\'t be installed as this version of {app} is to {age} to use it.'.format(
            app=app.AppName,
            age='old' if snapshotAvailability == travellermap.DataStore.SnapshotAvailability.AppToOld else 'new')
        if snapshotAvailability == travellermap.DataStore.SnapshotAvailability.AppToOld:
            promptMessage += ' New versions can be downloaded from: <br><br><a href=\'{url}\'>{url}</a>'.format(
                url=app.AppURL)
            stateKey = 'UniverseUpdateAppToOld'
        else:
            promptMessage += ' Either your a time traveller or your\'re running a dev branch, either way, I\'ll assume you know what your\'re doing.'
            stateKey = 'UniverseUpdateAppToNew'

        if isStartup:
            # When running the startup check allow the user to choose to
            # ignore this error and continue loading the app. Remembering
            # not to continue loading the app isn't allowed as it could
            # result in the app just existing with the it not being clear
            # the user why
            promptMessage += '<br><br>Do you want to continue loading {app}?<br>'.format(
                app=app.AppName)
            answer = gui.AutoSelectMessageBox.question(
                text='<html>' + promptMessage + '<html>',
                stateKey=stateKey,
                rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
            return _SnapshotCheckResult.IncompatibleUpdate \
                if answer == QtWidgets.QMessageBox.StandardButton.Yes else \
                _SnapshotCheckResult.ExitRequested
        else:
            # Always show the message when performing a user requested check.
            # However this is purely informational, there is not choice for
            # the user as to what to do
            gui.MessageBoxEx.information(
                text='<html>' + promptMessage + '<html>')
            return _SnapshotCheckResult.IncompatibleUpdate

    # Ask for confirmation to install the update if this is the automated check
    # run at startup. If the user requested the check then it implies they want
    # it installed
    if isStartup:
        answer = gui.AutoSelectMessageBox.question(
            text='<html>New universe data is available. Do you want to update?<br>' \
            'Custom sectors will not be affected<br></html>',
            stateKey='DownloadUniverseAtStartup')
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            # User chose not to install update so just continue loading the app with the
            # old data
            return _SnapshotCheckResult.NoUpdate

    # Update the snapshot
    updateProgress = gui.DownloadProgressDialog(parent=parent)
    result = updateProgress.exec()

    # Force delete of progress dialog to stop it hanging around. The docs say it will be deleted
    # when exec is called on the application
    # https://doc.qt.io/qt-6/qobject.html#deleteLater
    updateProgress.deleteLater()

    return _SnapshotCheckResult.UpdateInstalled \
        if result == QtWidgets.QDialog.DialogCode.Accepted else \
        _SnapshotCheckResult.Cancelled

# Check that the loopback addresses required for the proxy host pool
# are available. This is required as macOS (and possibly some Linux
# distros) only enables 127.0.0.1 by default.
def _hostPoolSizeCheck(
        parent: typing.Optional[QtWidgets.QWidget] = None
        ) -> int:
    requestedHostCount = app.Config.instance().proxyHostPoolSize()
    availableHostCount = 0
    for index in range(1, requestedHostCount + 1):
        testSocket = None
        try:
            address = f'127.0.0.{index}'
            testSocket = socket.socket()
            testSocket.bind((address, 0))
            availableHostCount = index
        except Exception as ex:
            logging.debug(
                'An exception occurred when binding to {address} to test proxy host pool size.',
                exc_info=ex)
            break
        finally:
            if testSocket:
                testSocket.close()

    if availableHostCount == 0:
        logging.error(
            'Proxy will be disabled as no IPv4 loopback addresses were found')

        message = """
            <p>The proxy will be disabled as no IPv4 loopback addresses were
            found. When the proxy is disabled, custom sectors will not be overlaid
            on Traveller Map.</p>
            """
        gui.AutoSelectMessageBox.critical(
            parent=parent,
            text=message,
            stateKey='NoHostPoolInterfaces')
    elif availableHostCount != requestedHostCount:
        logging.warning(
            'Proxy host pool size will be reduced from {requested} to '
            '{available} due to insufficient IPv4 loopback addresses.'.format(
                requested=requestedHostCount,
                available=availableHostCount))

        message = """
            <p>The proxy is configured to have a host pool size of {requested}
            but only {available} IPv4 loopback {wording} available. This may
            reduce performance when displaying Traveller Map.</p>
            <p>For a pool size of {requested}, the loopback addresses
            127.0.0.1 -> 127.0.0.{requested} must be enabled.</p>
            """.format(
            requested=requestedHostCount,
            available=availableHostCount,
            wording='address is' if availableHostCount == 1 else 'addresses are')
        gui.AutoSelectMessageBox.warning(
            parent=parent,
            text=message,
            stateKey='NoHostPoolInterfaces')

    return availableHostCount

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super(MainWindow, self).__init__()

        gui.configureWindowTitleBar(widget=self)

        self.setWindowFlag(QtCore.Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setWindowTitle(f'{app.AppName} v{app.AppVersion}')
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().showMessage('Status: Ready')

        self._compareWorldsButton = QtWidgets.QPushButton('Compare Worlds...', self)
        self._compareWorldsButton.clicked.connect(gui.WindowManager.instance().showWorldComparisonWindow)

        self._searchWorldsButton = QtWidgets.QPushButton('Search Worlds...', self)
        self._searchWorldsButton.clicked.connect(gui.WindowManager.instance().showWorldSearchWindow)

        self._jumpRouteButton = QtWidgets.QPushButton('Jump Route Planner...', self)
        self._jumpRouteButton.clicked.connect(gui.WindowManager.instance().showJumpRouteWindow)

        self._worldTradeOptionsButton = QtWidgets.QPushButton('World Trade Options...', self)
        self._worldTradeOptionsButton.clicked.connect(gui.WindowManager.instance().showWorldTradeOptionsWindow)

        self._multiWorldTradeOptionsButton = QtWidgets.QPushButton('Multi World Trade Options...', self)
        self._multiWorldTradeOptionsButton.clicked.connect(gui.WindowManager.instance().showMultiWorldTradeOptionsWindow)

        self._simulatorButton = QtWidgets.QPushButton('Trade Simulator...', self)
        self._simulatorButton.clicked.connect(gui.WindowManager.instance().showSimulatorWindow)

        self._gunsmithButton = QtWidgets.QPushButton('Gunsmith...', self)
        self._gunsmithButton.clicked.connect(gui.WindowManager.instance().showGunsmithWindow)

        self._robotBuilderButton = QtWidgets.QPushButton('Robot Builder...', self)
        self._robotBuilderButton.clicked.connect(gui.WindowManager.instance().showRobotBuilderWindow)

        generalLayout = QtWidgets.QVBoxLayout()
        generalLayout.addWidget(self._compareWorldsButton)
        generalLayout.addWidget(self._searchWorldsButton)
        generalLayout.addWidget(self._jumpRouteButton)
        generalLayout.addWidget(self._worldTradeOptionsButton)
        generalLayout.addWidget(self._multiWorldTradeOptionsButton)
        generalLayout.addWidget(self._simulatorButton)
        generalLayout.addWidget(self._gunsmithButton)
        generalLayout.addWidget(self._robotBuilderButton)
        generalGroupBox = QtWidgets.QGroupBox('General Tools')
        generalGroupBox.setLayout(generalLayout)

        self._purchaseCalculatorButton = QtWidgets.QPushButton('Purchase Calculator...', self)
        self._purchaseCalculatorButton.clicked.connect(gui.WindowManager.instance().showPurchaseCalculatorWindow)

        self._saleCalculatorButton = QtWidgets.QPushButton('Sale Calculator...', self)
        self._saleCalculatorButton.clicked.connect(gui.WindowManager.instance().showSaleCalculatorWindow)

        refereeLayout = QtWidgets.QVBoxLayout()
        refereeLayout.addWidget(self._purchaseCalculatorButton)
        refereeLayout.addWidget(self._saleCalculatorButton)
        refereeGroupBox = QtWidgets.QGroupBox('Referee Tools')
        refereeGroupBox.setLayout(refereeLayout)

        self._customSectorsButton = QtWidgets.QPushButton('Custom Sectors...', self)
        self._customSectorsButton.clicked.connect(self._showCustomSectorsWindow)

        self._downloadButton = QtWidgets.QPushButton('Download Universe Data...', self)
        self._downloadButton.clicked.connect(self._downloadUniverse)

        self._configurationButton = QtWidgets.QPushButton('Configuration...', self)
        self._configurationButton.clicked.connect(self._showConfiguration)

        self._aboutButton = QtWidgets.QPushButton('About...', self)
        self._aboutButton.clicked.connect(self._showAbout)

        systemLayout = QtWidgets.QVBoxLayout()
        systemLayout.addWidget(self._customSectorsButton)
        systemLayout.addWidget(self._downloadButton)
        systemLayout.addWidget(self._configurationButton)
        systemLayout.addWidget(self._aboutButton)
        systemGroupBox = QtWidgets.QGroupBox('System')
        systemGroupBox.setLayout(systemLayout)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(generalGroupBox)
        windowLayout.addWidget(refereeGroupBox)
        windowLayout.addWidget(systemGroupBox)

        widget = QtWidgets.QWidget()
        widget.setLayout(windowLayout)
        self.setFixedSize(
            max(windowLayout.sizeHint().width(), 300),
            windowLayout.sizeHint().height())
        self.setCentralWidget(widget)

        self._settings = gui.globalWindowSettings()
        self._configSection = 'MainWindow'
        self.loadSettings()

        self.show()

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        if not e.spontaneous():
            QtCore.QTimer.singleShot(0, self._showWelcomeMessage)

        super().showEvent(e)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.saveSettings()
        gui.WindowManager.instance().closeWindows()
        super().closeEvent(event)

    def loadSettings(self) -> None:
        self._settings.beginGroup(self._configSection)
        storedGeometry = gui.safeLoadSetting(
            settings=self._settings,
            key='WindowGeometry',
            type=QtCore.QByteArray)
        if storedGeometry:
            self.restoreGeometry(storedGeometry)
        self._settings.endGroup()

    def saveSettings(self) -> None:
        # Write window size and position to config file
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('WindowGeometry', self.saveGeometry())
        self._settings.endGroup()

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title='Welcome',
            html=_WelcomeMessage,
            noShowAgainId='AppWelcome')
        message.exec()

    def _showCustomSectorsWindow(self) -> None:
        sectorDialog = gui.CustomSectorDialog(parent=self)
        sectorDialog.exec()

        if sectorDialog.modified():
            self._showRestartRequiredStatus()
            gui.MessageBoxEx.information(
                parent=self,
                text=f'{app.AppName} will load changes to custom sectors when next started.')

    def _showConfiguration(self) -> None:
        configDialog = gui.ConfigDialog(parent=self)
        configDialog.exec()

        if configDialog.restartRequired():
            self._showRestartRequiredStatus()
            gui.MessageBoxEx.information(
                parent=self,
                text=f'Some changes will only be applied when {app.AppName} is restarted.')

    def _downloadUniverse(self) -> None:
        try:
            result = _snapshotUpdateCheck(isStartup=False, parent=self)
            if result == _SnapshotCheckResult.NoUpdate:
                gui.MessageBoxEx.information(
                    parent=self,
                    text='There is no new universe data to download.')
            elif result == _SnapshotCheckResult.UpdateInstalled:
                self._showRestartRequiredStatus()
                gui.MessageBoxEx.information(
                    parent=self,
                    text=f'Universe update complete.\n{app.AppName} will load the new data when next started.')
        except Exception as ex:
            gui.MessageBoxEx.critical(
                parent=self,
                text='Failed to update universe data', exception=ex)

    def _showAbout(self) -> None:
        licenseDir = os.path.join(_installDirectory(), 'Licenses')
        aboutDialog = gui.AboutDialog(
            parent=self,
            licenseDir=licenseDir)
        aboutDialog.exec()

    def _showRestartRequiredStatus(self) -> None:
        self.statusBar().showMessage('Status: Restart Required')

def main() -> None:
    QtWidgets.QApplication.setAttribute(
        QtCore.Qt.ApplicationAttribute.AA_EnableHighDpiScaling)

    appId = _SingletonAppId
    if '--no-singleton' in sys.argv:
        appId = str(uuid.uuid4())

    application = gui.SingletonApplication(
        appId=appId,
        argv=sys.argv)
    if application.isAlreadyRunning():
        print(f'{app.AppName} is already running.')
        return

    exitCode = 0
    try:
        installDir = _installDirectory()
        application.setWindowIcon(QtGui.QIcon(os.path.join(installDir, 'icons', 'autojimmy.ico')))

        appDir = _applicationDirectory()
        os.makedirs(appDir, exist_ok=True)

        logDirectory = os.path.join(appDir, 'logs')
        app.setupLogger(logDir=logDirectory, logFile='autojimmy.log')
        # Log version before setting log level as it should always be logged
        logging.info(f'{app.AppName} v{app.AppVersion}')

        try:
            locale.setlocale(locale.LC_ALL, '')
        except Exception as ex:
            logging.warning('Failed to set default locale', exc_info=ex)

        app.Config.setDirs(
            installDir=installDir,
            appDir=appDir)

        # Set configured log level immediately after configuration has been setup
        logLevel = app.Config.instance().logLevel()
        try:
            app.setLogLevel(logLevel)
        except Exception as ex:
            logging.warning('Failed to set log level', exc_info=ex)

        installMapsDir = os.path.join(installDir, 'data', 'map')
        overlayMapsDir = os.path.join(appDir, 'map')
        customMapsDir = os.path.join(appDir, 'custom_map')
        travellermap.DataStore.setSectorDirs(
            installDir=installMapsDir,
            overlayDir=overlayMapsDir,
            customDir=customMapsDir)

        traveller.WorldManager.setMilieu(milieu=app.Config.instance().milieu())

        gunsmith.WeaponStore.setWeaponDirs(
            userDir=os.path.join(appDir, 'weapons'),
            exampleDir=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'weapons'))

        robots.RobotStore.setRobotDirs(
            userDir=os.path.join(appDir, 'robots'),
            exampleDir=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'robots'))

        gui.configureAppStyle(application)

        # Check if CairoSVG is working, possibly prompting the user if it's not. This needs to be
        # done after the DataStore singleton has been set up so it can check if there are any
        # existing SVG custom sectors
        if not _cairoSvgInstallCheck():
            sys.exit(0)

        # Check if there is new universe data available BEFORE the app loads the
        # local snapshot so it can be updated without restarting
        try:
            result = _snapshotUpdateCheck(isStartup=True)
            if result == _SnapshotCheckResult.ExitRequested:
                sys.exit(0)
        except Exception as ex:
            message = 'An exception occurred when checking for new universe data.'
            logging.error(message, exc_info=ex)
            gui.AutoSelectMessageBox.critical(
                text=message,
                exception=ex,
                stateKey='UniverseUpdateErrorWhenChecking')
            # Continue loading the app with the existing data

        # Configure the map proxy if it's enabled. The proxy isn't started now, that will be done later
        # so progress can be displayed
        startProxy = False
        if app.Config.instance().proxyEnabled():
            hostPoolSize = _hostPoolSizeCheck()
            if hostPoolSize > 0:
                proxy.MapProxy.configure(
                    listenPort=app.Config.instance().proxyPort(),
                    hostPoolSize=hostPoolSize,
                    travellerMapUrl=app.Config.instance().proxyMapUrl(),
                    tileCacheSize=app.Config.instance().proxyTileCacheSize(),
                    tileCacheLifetime=app.Config.instance().proxyTileCacheLifetime(),
                    svgComposition=app.Config.instance().proxySvgCompositionEnabled(),
                    mainsMilieu=app.Config.instance().milieu(),
                    installDir=installDir,
                    appDir=appDir,
                    logDir=logDirectory,
                    logLevel=logLevel)
                startProxy = True

        startupProgress = gui.StartupProgressDialog(startProxy=startProxy)
        if startupProgress.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            exception = startupProgress.exception()
            if exception is not None:
                raise exception
            raise RuntimeError('Startup failed with an unknown error')

        # Force delete of progress dialog to stop it hanging around. The docs say it will be deleted
        # when exec is called on the application
        # https://doc.qt.io/qt-6/qobject.html#deleteLater
        startupProgress.deleteLater()

        # Configure the tile client to use the proxy if it's running
        if proxy.MapProxy.instance().isRunning():
            travellermap.TileClient.configure(
                baseMapUrl=proxy.MapProxy.instance().accessUrl())
        else:
            travellermap.TileClient.configure(
                baseMapUrl=travellermap.TravellerMapBaseUrl)

        with qasync.QEventLoop() as asyncEventLoop:
            window = MainWindow()
            window.show()
            asyncEventLoop.run_forever()
    except Exception as ex:
        message = 'Failed to initialise application'
        logging.error(message, exc_info=ex)
        gui.MessageBoxEx.critical(
            text=message,
            exception=ex)
        exitCode = 1
    finally:
        proxy.MapProxy.instance().shutdown()

    sys.exit(exitCode)


if __name__ == "__main__":
    # This is required for multiprocessing to work with apps that have been frozen as Windows exes.
    # According to the docs this should be called as the first line of the script. Technically I'm
    # not doing this as the dependency checking runs first but I've tested it and it doesn't seem
    # to matter.
    # https://docs.python.org/3/library/multiprocessing.html#windows
    multiprocessing.freeze_support()

    main()
