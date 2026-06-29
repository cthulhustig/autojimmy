#!/usr/bin/env python3

# This should always be imported first. It will exit the app with more helpful message if any
# external dependencies are missing (assuming I remember to keep the list up to date)
import depschecker

import app
import astronomer
import enum
import gui
import gunsmith
import locale
import logging
import multiprocessing
import multiverse
import objectdb
import os
import pathlib
import qasync
import robots
import startup
import sys
import uuid
import typing
from PyQt5 import QtWidgets, QtGui, QtCore

# TODO: Initial universe creation/management
# - All universes are custom universes that can be edited and they only contain data for a single Milieu
#       - Avoids confusion as to why you can't edit the "stock" universe
#       - When a new universe is created, if the user wants stock data, its imported from files at that point
#           - I don't think I want to give an option to let the user choose if FarAway sectors are imported as
#           there are so few of them it doesn't warrant it. I think I either want to always include them or always
#           exclude them.
#       - Rather than the current sector metadata, I think I want to have a sector_source table that tracks what the source was for sectors
#           - Rather than index by sector id, it will be indexed by sector position
#           - Should store the source data hash in the same way as the current sector metadata
#           - Will need to have wrapper objects so the data can be read and written from the application layer
#       - Rather than store timestamps per source sector, the timestamp of the map snapshot it was imported from should be stored
#           - IMPORTANT: This is currently stored in the registry database but should be stored in the universe
#       - The Milieu the source data was taken from will also need to be stored in the universe database
#           - This is needed so, if we pull in updates from map snapshot, we know which Milieu to pull them from
#       - Downside of this is doing auto updates when the stock traveller map changes so I'll need a method to import
#           - Need to display a list of any custom sectors that have updates and let the user choose what to do
#           - I'll probably also need to store if the user chose to not import far away as you wouldn't want to import them as part of the update
# - First Startup
#   1. Create a universe for each Milieu in the map snapshot
#   2. Load custom sectors for each Milieu into corresponding universe
#   3. Add flag indicating custom sectors have been imported
#   3. Prompt the user asking which universe to load
#   4. Set the selected universe as the active universe in the config file
# - Normal Startup
#   1. Load the active universe
#       - If it succeeds, nothing more to do
#   2. Display Universe Management dialog so user can create a universe
#       - Shouldn't let the user proceed until they create a universe (disable OK button)
#       - If they cancel the app should exit
# - Update Process
#   1. Read timestamp from universe DB and compare it with snapshot timestamp
#      - If the universe DB timestamp is greater or equal, nothing to do
#      - If there is no universe DB timestamp, nothing to do (the universe was created as an empty universe)
#   2. Read metadata and sector files from map snapshot using Milieu specified in universe DB
#      - If no Milieu is set, it means the universe was created as an empty universe, need to prompt for which Milieu to use
#   3. Read sector_source info from universe DB
#   4. Compare the map snapshot and sector_source info to see what has changed
#      - If a sector is in the map snapshot but not in the sector_source, add it to the added list
#      - If a sector is not in the map snapshot but is in the sector_source, add it to the deleted list
#      - If a sector is in both, the file hashes need to be compared, if they are different add it to the modified list
#   5. For each sector added/modified/deleted lists, check if there is a sector in the universe at that location and,
#      if there is check if it's marked as being custom (i.e. modified since the universe was created). If it is, the
#      user needs prompted if it should be updated.
#      - If the user chooses not to update one of the sectors, remove it from the corresponded added/modified/deleted lists
#   6. Delete any sectors on the deleted list
#   7. Add any sectors on the added list
#   8. Replace any sectors on the modified list
# - The fact Universes should be single milieu only means
#      - A load of code can be deleted, no need to have the config option, no need for windows to handle it changing
#      - If the user wants a different Milieu, they can create a new universe (and have it import the stock data for that Milieu)
# - IMPORTANT: Will need to handle the case where the user has created an empty Universe and then chooses to sync the map snapshot into it
#      - This should be possible but the user will need to specify which Milieu they want
#      - Once they specify which Millie, the one they chose needs to be written to the universe DB
# - If there is no universe when user starts app, they are shown the create universe dialog
#       - Lets them choose if they want to import stock data, including which Milieu to import from
#       - Will need an additional check that isn't usually part to the create universe dialog that asks if they want to import legacy custom sectors

_SingletonAppId = 'd2b192d8-4007-4588-bb80-8bd9721e9bcc'

_WelcomeMessage = """
    <html>
    <h2><center>Welcome to {name} v{version}</center></h2>
    <p>{name} is a collection of tools for the Traveller RPG. It's primarily aimed at Mongoose
    Traveller, but much of the functionality can be used with other rule systems.</p>
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
    snapshotAvailability = multiverse.SnapshotManager.instance().checkForNewSnapshot()

    if snapshotAvailability == multiverse.SnapshotManager.SnapshotAvailability.NoNewSnapshot:
        return _SnapshotCheckResult.NoUpdate

    if snapshotAvailability != multiverse.SnapshotManager.SnapshotAvailability.NewSnapshotAvailable:
        promptMessage = 'New universe data is available, however it can\'t be installed as this version of {app} is to {age} to use it.'.format(
            app=app.AppName,
            age='old' if snapshotAvailability == multiverse.SnapshotManager.SnapshotAvailability.AppToOld else 'new')
        if snapshotAvailability == multiverse.SnapshotManager.SnapshotAvailability.AppToOld:
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

def _pushConfigChangeToWorldManager(
        option: app.ConfigOption,
        oldValue: typing.Any,
        newValue: typing.Any
        ) -> None:
    if option is app.ConfigOption.Universe:
        startupProgressDlg = gui.StartupProgressDialog()

        # TODO: I don't like the fact this is reinitialising the whole
        # world manager. Should probably have it's own job rather than
        # reusing
        startupProgressDlg.addJob(job=startup.InitWorldManager())

        if startupProgressDlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            # TODO: Not sure how best to handle errors
            pass

        # Force delete of progress dialog to stop it hanging around. The docs say it will be deleted
        # when exec is called on the application
        # https://doc.qt.io/qt-6/qobject.html#deleteLater
        startupProgressDlg.deleteLater()

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

        self._diceRollerButton = QtWidgets.QPushButton('Dice Roller...', self)
        self._diceRollerButton.clicked.connect(gui.WindowManager.instance().showDiceRollerWindow)

        generalLayout = QtWidgets.QVBoxLayout()
        generalLayout.addWidget(self._compareWorldsButton)
        generalLayout.addWidget(self._searchWorldsButton)
        generalLayout.addWidget(self._jumpRouteButton)
        generalLayout.addWidget(self._worldTradeOptionsButton)
        generalLayout.addWidget(self._multiWorldTradeOptionsButton)
        generalLayout.addWidget(self._simulatorButton)
        generalLayout.addWidget(self._gunsmithButton)
        generalLayout.addWidget(self._robotBuilderButton)
        generalLayout.addWidget(self._diceRollerButton)
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

        self._customUniverseButton = QtWidgets.QPushButton('Custom Universe...', self)
        self._customUniverseButton.clicked.connect(self._showCustomUniverse)

        self._downloadButton = QtWidgets.QPushButton('Download Universe Data...', self)
        self._downloadButton.clicked.connect(self._downloadUniverse)

        self._configurationButton = QtWidgets.QPushButton('Configuration...', self)
        self._configurationButton.clicked.connect(self._showConfiguration)

        self._aboutButton = QtWidgets.QPushButton('About...', self)
        self._aboutButton.clicked.connect(self._showAbout)
        # Add debug context menu to about button
        self._aboutButton.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._aboutButton.customContextMenuRequested.connect(self._showDebugMenu)

        systemLayout = QtWidgets.QVBoxLayout()
        systemLayout.addWidget(self._customUniverseButton)
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

    def _showConfiguration(self) -> None:
        try:
            configDialog = gui.ConfigDialog(parent=self)
        except Exception as ex:
            message = 'Failed to open configuration dialog'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)
            return

        result = configDialog.exec()

        if result == QtWidgets.QDialog.DialogCode.Accepted and app.Config.instance().isRestartRequired():
            self._showRestartRequiredStatus()
            gui.MessageBoxEx.information(
                parent=self,
                text=f'Some changes will only be applied when {app.AppName} is restarted.')

    def _showCustomUniverse(self) -> None:
        universe = astronomer.WorldManager.instance().universe()
        if not universe.isCustom():
            # TODO: Display a message box explaining you need to create a custom universe
            # TODO: If there are no custom universes in the registry, just display a simple dialog to create a new universe
            # TODO: If there are existing custom universes (it's just they aren't selected), display a universe manager window
            # that lets the user create a new one _or_ switch to an existing one
            pass

        gui.WindowManager.instance().showCustomUniverseWindow()

    # TODO: If the the current universe is a custom universe this should probably give
    # a warning telling the user that their universe won't update.
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
        try:
            aboutDialog = gui.AboutDialog(
                parent=self,
                licenseDir=os.path.join(_installDirectory(), 'licenses'))
        except Exception as ex:
            message = 'Failed to open about dialog'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)
            return

        aboutDialog.exec()

    def _showRestartRequiredStatus(self) -> None:
        self.statusBar().showMessage('Status: Restart Required')

    def _showDebugMenu(
            self,
            point: QtCore.QPoint
            ) -> None:
        if not gui.isShiftKeyDown(exclusive=False) or not gui.isCtrlKeyDown(exclusive=False):
            # Only show menu if you hold down shift and ctrl
            return

        writeGarbageCollectorStatsAction = QtWidgets.QAction('Write Garbage Collector Stats', self)
        writeGarbageCollectorStatsAction.triggered.connect(self._debugWriteGarbageCollectorStats)

        forceGarbageCollectionAction = QtWidgets.QAction('Force Garbage Collector', self)
        forceGarbageCollectionAction.triggered.connect(self._debugForceGarbageCollector)

        checkForTypeCyclesAction = QtWidgets.QAction('Check For Type Cycles', self)
        checkForTypeCyclesAction.triggered.connect(self._debugCheckForTypeCycles)

        menu = QtWidgets.QMenu(self)
        menu.addAction(writeGarbageCollectorStatsAction)
        menu.addAction(forceGarbageCollectionAction)
        menu.addAction(checkForTypeCyclesAction)
        # NOTE: The passed in point isn't used to make showing the menu independent
        # of whatever control it's attached to
        menu.exec(QtGui.QCursor.pos())

    def _debugWriteGarbageCollectorStats(self) -> None:
        app.debugWriteGarbageCollectorStats(
            writeToLogLevel=app.currentLogLevel())

    def _debugForceGarbageCollector(self) -> None:
        try:
            logLevel = app.currentLogLevel()
            app.debugWriteGarbageCollectorStats(writeToLogLevel=logLevel)
            app.debugForceGarbageCollection(writeToLogLevel=logLevel)
            app.debugWriteGarbageCollectorStats(writeToLogLevel=logLevel)
        except Exception as ex:
            logging.error('Failed to force garbage collection', exc_info=ex)

    def _debugCheckForTypeCycles(self) -> None:
        try:
            logLevel = app.currentLogLevel()
            app.debugCheckForTypeCycles(writeToLogLevel=logLevel)
        except Exception as ex:
            logging.error('Failed to check for type cycles', exc_info=ex)

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

    try:
        installDir = _installDirectory()
        application.setWindowIcon(QtGui.QIcon(os.path.join(installDir, 'icons', 'autojimmy.ico')))

        appDir = _applicationDirectory()
        os.makedirs(appDir, exist_ok=True)

        logDirectory = os.path.join(appDir, 'logs')
        app.setupLogger(logDir=logDirectory, logFile='autojimmy.log')
        # Log version before setting log level as it should always be logged
        logging.info(f'{app.AppName} v{app.AppVersion}')
        logging.info(f'Python: {sys.version}')

        try:
            locale.setlocale(locale.LC_ALL, '')
        except Exception as ex:
            logging.warning('Failed to set default locale', exc_info=ex)

        app.Config.setDirs(
            installDir=installDir,
            appDir=appDir)

        # Set configured log level immediately after configuration has been setup
        logLevel = app.Config.instance().value(option=app.ConfigOption.LogLevel)
        try:
            app.setLogLevel(logLevel)
        except Exception as ex:
            logging.warning('Failed to set log level', exc_info=ex)

        multiverseDbPath = os.path.join(appDir, 'autojimmy.db')
        objectdb.ObjectDbManager.instance().initialise(databasePath=multiverseDbPath)

        installMapsDir = os.path.join(installDir, 'data', 'map')
        overlayMapsDir = os.path.join(appDir, 'map')
        multiverse.SnapshotManager.setSectorDirs(
            installDir=installMapsDir,
            overlayDir=overlayMapsDir)

        gunsmith.WeaponStore.setWeaponDirs(
            userDir=os.path.join(appDir, 'weapons'),
            exampleDir=os.path.join(installDir, 'data', 'weapons'))

        robots.RobotStore.setRobotDirs(
            userDir=os.path.join(appDir, 'robots'),
            exampleDir=os.path.join(installDir, 'data', 'robots'))

        gui.configureAppStyle(
            application=application,
            interfaceTheme=app.Config.instance().value(option=app.ConfigOption.ColourTheme),
            interfaceScale=app.Config.instance().value(option=app.ConfigOption.InterfaceScale))

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

        multiversePath = os.path.join(appDir, 'multiverse')
        multiverse.UniverseManager.initialise(multiversePath=multiversePath)

        shouldSyncStockUniverse = False
        try:
            shouldSyncStockUniverse = multiverse.isStockUniverseSnapshotNewer()
        except Exception as ex:
            logging.warning('Failed to compare stock universe snapshot age.', exc_info=ex)

        # Check if we need to import legacy custom sectors
        # TODO: At some point in the future I should be able to remove this
        legacyCustomSectorsDir = os.path.join(appDir, 'custom_map')
        shouldImportLegacyCustomSectors = False
        try:
            shouldImportLegacyCustomSectors = not multiverse.haveLegacyCustomSectorsBeenImported(
                directoryPath=legacyCustomSectorsDir)
        except Exception as ex:
            logging.warning('Failed to check for imported legacy custom sectors.', exc_info=ex)

        startupProgressDlg = gui.StartupProgressDialog()

        if shouldSyncStockUniverse:
            startupProgressDlg.addJob(job=startup.ImportStockUniverseJob())

        if shouldImportLegacyCustomSectors:
            startupProgressDlg.addJob(job=startup.ImportLegacyCustomSectorsJob(
                directoryPath=legacyCustomSectorsDir))

        startupProgressDlg.addJob(job=startup.InitWorldManager())
        startupProgressDlg.addJob(job=startup.LoadWeaponsJob())
        startupProgressDlg.addJob(job=startup.LoadRobotsJob())

        if startupProgressDlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            sys.exit(1)

        # Force delete of progress dialog to stop it hanging around. The docs say it will be deleted
        # when exec is called on the application
        # https://doc.qt.io/qt-6/qobject.html#deleteLater
        startupProgressDlg.deleteLater()

        # Register a callback that will push config changes (i.e. switching universe) to
        # the world manager
        # NOTE: It is VERY important that this is registered early as we need the world
        # manager to be the first thing that is notified of a change in universe as other
        # subscribers may assume it's been updated
        # TODO: Doing this here feels wrong
        app.Config.instance().configChanged.connect(
            _pushConfigChangeToWorldManager)

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
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    # This is required for multiprocessing to work with apps that have been frozen as Windows exes.
    # According to the docs this should be called as the first line of the script. Technically I'm
    # not doing this as the dependency checking runs first but I've tested it and it doesn't seem
    # to matter.
    # https://docs.python.org/3/library/multiprocessing.html#windows
    multiprocessing.freeze_support()

    main()
