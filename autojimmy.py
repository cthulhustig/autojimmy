#!/usr/bin/env python3

# This should always be imported first. It will exit the app with more helpful message if any
# external dependencies are missing (assuming I remember to keep the list up to date)
import depschecker

import app
import common
import gui
import gunsmith
import locale
import logging
import multiprocessing
import os
import pathlib
import proxy
import qasync
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
    his help with the integration.</p>
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

def _cairoSvgInstallCheck() -> bool: # True if the application should continue, or False if it should exit
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
        promptMessage = 'The CairoSVG Python library is not installed.'
        promptIcon = QtWidgets.QMessageBox.Icon.Information
        logging.info(promptMessage)
    elif depschecker.DetectedCairoSvgState == depschecker.CairoSvgState.NoLibraries:
        promptMessage = 'The CairoSVG Python library is installed but it failed to find the Cairo system libraries that it requires.'
        promptIcon = QtWidgets.QMessageBox.Icon.Warning
        logging.warning(promptMessage)
    else:
        promptMessage = 'The CairoSVG Python library is in an unknown state.'
        promptIcon = QtWidgets.QMessageBox.Icon.Critical
        alwaysShowPrompt = True
        logging.error(promptMessage)

    promptMessage += \
        '<br><br>New custom sector posters will be created using PNG images, this can ' + \
        'introduce more render artifacts around their borders.'

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

    promptMessage += '<br><br>CairoSVG install info: <a href=\'https://cairosvg.org/documentation/\'>https://cairosvg.org/documentation/</a>'
    promptMessage += f'<br><br>Do you want to continue loading {app.AppName}?'

    promptMessage = f'<html>{promptMessage}</html>'

    promptTitle = 'Prompt'
    promptButtons = QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
    promptDefaultButton = QtWidgets.QMessageBox.StandardButton.Yes
    if alwaysShowPrompt:
        answer = gui.MessageBoxEx.showMessageBox(
            title=promptTitle,
            icon=promptIcon,
            text=promptMessage,
            buttons=promptButtons,
            defaultButton=promptDefaultButton)
    else:
        answer = gui.AutoSelectMessageBox.showMessageBox(
            title=promptTitle,
            icon=promptIcon,
            text=promptMessage,
            buttons=promptButtons,
            defaultButton=promptDefaultButton,
            stateKey='ContinueIfCairoSvgNotWorking',
            rememberState=QtWidgets.QMessageBox.StandardButton.Yes) # Only remember if the user clicked yes

    return answer == QtWidgets.QMessageBox.StandardButton.Yes

def _snapshotUpdateCheck(
        automaticUpdate: bool = False,
        noUpdateMessage: typing.Optional[str] = None,
        successMessage: typing.Optional[str] = None
        ) -> bool: # True if the application should continue, or False if it should exit
    try:
        snapshotAvailability = travellermap.DataStore.instance().checkForNewSnapshot()
    except Exception as ex:
        message = 'An error occurred when checking for new universe data.'
        logging.error(message, exc_info=ex)
        gui.AutoSelectMessageBox.critical(
            text=message,
            exception=ex,
            stateKey='UniverseUpdateErrorWhenChecking')
        return True # Continue loading the app

    if snapshotAvailability == travellermap.DataStore.SnapshotAvailability.NoNewSnapshot:
        if noUpdateMessage:
            gui.MessageBoxEx.information(text=noUpdateMessage)
        return True # No update available so just continue loading

    if snapshotAvailability != travellermap.DataStore.SnapshotAvailability.NewSnapshotAvailable:
        promptMessage = 'New universe data is available, however this version of {app} is to {age} to use it.'.format(
            app=app.AppName,
            age='old' if snapshotAvailability == travellermap.DataStore.SnapshotAvailability.AppToOld else 'new')
        if snapshotAvailability == travellermap.DataStore.SnapshotAvailability.AppToOld:
            promptMessage += ' New versions can be downloaded from: <br><br><a href=\'{url}\'>{url}</a>'.format(
                url=app.AppURL)
            stateKey = 'UniverseUpdateAppToOld'
        else:
            promptMessage += ' Either your a time traveller or your\'re running a dev branch, either way, I\'ll assume you know what your\'re doing.'
            stateKey = 'UniverseUpdateAppToNew'
        promptMessage += '<br><br>Do you want to continue loading {app}?<br>'.format(
            app=app.AppName)

        answer = gui.AutoSelectMessageBox.question(
            text='<html>' + promptMessage + '<html>',
            stateKey=stateKey,
            rememberState=QtWidgets.QMessageBox.StandardButton.Yes) # Only remember if the user clicked yes
        return answer == QtWidgets.QMessageBox.StandardButton.Yes

    if not automaticUpdate:
        # TODO: At some point in the future I can remove the note about it being faster
        answer = gui.AutoSelectMessageBox.question(
            text='<html>New universe data is available. Do you want to update?<br>' \
            'Custom sectors will not be affected<br><br>' \
            'Don\'t worry, updating is a LOT faster than it used to be.</html>',
            stateKey='DownloadUniverseAtStartup')
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return True # User chose not to install update so just continue loading the app with the old data

    # Update the snapshot
    updateProgress = gui.DownloadProgressDialog()
    result = updateProgress.exec()
    if (result == QtWidgets.QDialog.DialogCode.Accepted) and successMessage:
        gui.MessageBoxEx.information(text=successMessage)

    # Force delete of progress dialog to stop it hanging around. The docs say it will be deleted
    # when exec is called on the application
    # https://doc.qt.io/qt-6/qobject.html#deleteLater
    updateProgress.deleteLater()

    return True # Update is complete so continue loading


class _MapProxyMonitor(QtCore.QObject):
    error = QtCore.pyqtSignal()

    _PollIntervalMs = 5000

    def __init__(
            self,
            parent: typing.Optional[QtCore.QObject] = None
            ) -> None:
        super().__init__(parent)
        self._status = None
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._checkStatus)

    def start(self) -> None:
        self._timer.start(_MapProxyMonitor._PollIntervalMs)

    def stop(self) -> None:
        self._timer.stop()

    def _checkStatus(self) -> None:
        newStatus = proxy.MapProxy.instance().status()
        isError = newStatus == proxy.MapProxy.ServerStatus.Error
        wasError = self._status == proxy.MapProxy.ServerStatus.Error

        if isError and not wasError:
            self.error.emit()

        self._status = newStatus

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super(MainWindow, self).__init__()

        gui.configureWindowTitleBar(widget=self)

        self.setWindowFlag(QtCore.Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setWindowTitle(f'{app.AppName} v{app.AppVersion}')
        self.statusBar().setSizeGripEnabled(False)

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

        generalLayout = QtWidgets.QVBoxLayout()
        generalLayout.addWidget(self._compareWorldsButton)
        generalLayout.addWidget(self._searchWorldsButton)
        generalLayout.addWidget(self._jumpRouteButton)
        generalLayout.addWidget(self._worldTradeOptionsButton)
        generalLayout.addWidget(self._multiWorldTradeOptionsButton)
        generalLayout.addWidget(self._simulatorButton)
        generalLayout.addWidget(self._gunsmithButton)
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

        self._configurationButton = QtWidgets.QPushButton('Configuration...', self)
        self._configurationButton.clicked.connect(self._showConfiguration)

        self._downloadButton = QtWidgets.QPushButton('Download Universe Data...', self)
        self._downloadButton.clicked.connect(self._downloadUniverse)

        self._aboutButton = QtWidgets.QPushButton('About...', self)
        self._aboutButton.clicked.connect(self._showAbout)

        systemLayout = QtWidgets.QVBoxLayout()
        systemLayout.addWidget(self._customSectorsButton)
        systemLayout.addWidget(self._configurationButton)
        systemLayout.addWidget(self._downloadButton)
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
            title='Welcome',
            html=_WelcomeMessage,
            noShowAgainId='AppWelcome')
        message.exec()

    def _showCustomSectorsWindow(self) -> None:
        configDialog = gui.CustomSectorDialog()
        configDialog.exec()

        if configDialog.modified():
            gui.MessageBoxEx.information(
                parent=self,
                text=f'{app.AppName} will load changes to custom sectors when next started.')

    def _showConfiguration(self) -> None:
        configDialog = gui.ConfigDialog()
        configDialog.exec()

    def _downloadUniverse(self) -> None:
        try:
            _snapshotUpdateCheck(
                automaticUpdate=True, # Automatically install the update if one is available
                noUpdateMessage=f'There is no new universe data to download.',
                successMessage=f'Universe update complete.\n{app.AppName} will load the new data when next started.')
        except Exception as ex:
            gui.MessageBoxEx.critical(
                text='Failed to update universe data', exception=ex)

    def _showAbout(self) -> None:
        licenseDir = os.path.join(_installDirectory(), 'Licenses')
        aboutDialog = gui.AboutDialog(licenseDir=licenseDir)
        aboutDialog.exec()

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
    asyncEventLoop = qasync.QEventLoop()

    exitCode = 0
    mapProxyMonitor = None
    try:
        installDir = _installDirectory()
        application.setWindowIcon(QtGui.QIcon(os.path.join(installDir, 'icons', 'autojimmy.ico')))

        appDir = _applicationDirectory()
        os.makedirs(appDir, exist_ok=True)

        logDirectory = os.path.join(appDir, 'logs')
        cacheDirectory = os.path.join(appDir, 'cache')

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
            userWeaponDir=os.path.join(appDir, 'weapons'),
            exampleWeaponDir=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'weapons'))

        gui.configureAppStyle(application)

        # Check if CairoSVG is working, possibly prompting the user if it's not. This needs to be
        # done after the DataStore singleton has been set up so it can check if there are any
        # existing SVG custom sectors
        if not _cairoSvgInstallCheck():
            sys.exit(0)

        # Check if there is new universe data available BEFORE the app loads the local snapshot so it
        # can be updated without restarting
        if not _snapshotUpdateCheck():
            sys.exit(0)

        # Set up map proxy now to give it time to start its child process while data is being loaded.
        # It's important this is done after the check for new map data. If new data is downloaded it
        # should be done before the proxy is started so it and the main app don't end up with a different
        # view of the data.
        travellerMapUrl = app.Config.instance().travellerMapUrl()
        mapProxyPort = app.Config.instance().mapProxyPort()
        if mapProxyPort:
            proxy.MapProxy.configure(
                listenPort=mapProxyPort,
                hostPoolSize=app.Config.instance().mapProxyPoolSize(),
                travellerMapUrl=travellerMapUrl,
                installDir=installDir,
                appDir=appDir,
                mainsMilieu=app.Config.instance().milieu(),
                logDir=logDirectory,
                logLevel=logLevel)
            proxy.MapProxy.instance().run()

        travellermap.TileClient.configure(
            mapBaseUrl=travellerMapUrl,
            mapProxyPort=mapProxyPort)

        loadProgress = gui.LoadProgressDialog()
        if loadProgress.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            raise RuntimeError('Failed to load data')
        # Force delete of progress dialog to stop it hanging around. The docs say it will be deleted
        # when exec is called on the application
        # https://doc.qt.io/qt-6/qobject.html#deleteLater
        loadProgress.deleteLater()

        if mapProxyPort:
            # Start monitoring the map proxy after everything has loaded. If it does fail, this prevents
            # an error popup being displayed while loading (it will be displayed when the monitor first
            # polls the proxy)
            mapProxyMonitor = _MapProxyMonitor()
            mapProxyMonitor.error.connect(lambda: gui.MessageBoxEx.critical(
                'The map proxy has stopped running or failed to start. Check logs for further details.'))
            mapProxyMonitor.start()

        window = MainWindow()
        window.show()
        with asyncEventLoop:
            asyncEventLoop.run_forever()
    except Exception as ex:
        message = 'Failed to initialise application'
        logging.error(message, exc_info=ex)
        gui.MessageBoxEx.critical(
            parent=None,
            text=message,
            exception=ex)
        exitCode = 1
    finally:
        if mapProxyMonitor:
            mapProxyMonitor.stop()

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
