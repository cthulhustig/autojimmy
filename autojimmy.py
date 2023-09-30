#!/usr/bin/env python3

import app
import common
import gui
import gunsmith
import locale
import logging
import multiprocessing
import os
import pathlib
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

        self._configurationButton = QtWidgets.QPushButton('Configuration...', self)
        self._configurationButton.clicked.connect(self._showConfiguration)

        self._downloadButton = QtWidgets.QPushButton('Download Universe Data...', self)
        self._downloadButton.clicked.connect(self._downloadUniverse)

        self._aboutButton = QtWidgets.QPushButton('About...', self)
        self._aboutButton.clicked.connect(self._showAbout)

        systemLayout = QtWidgets.QVBoxLayout()
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

    def _showConfiguration(self) -> None:
        configDialog = gui.ConfigDialog()
        configDialog.exec()

    def _downloadUniverse(self) -> None:
        downloadProgress = gui.DownloadProgressDialog()
        if downloadProgress.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        gui.MessageBoxEx.information(
            parent=self,
            text=f'Download complete.\n{app.AppName} will load the new data when next started.')

    def _showAbout(self) -> None:
        licenseDir = os.path.join(_installDirectory(), 'Licenses')
        aboutDialog = gui.AboutDialog(licenseDir=licenseDir)
        aboutDialog.exec()

def main() -> None:
    # This is required for multiprocessing to work with apps that have been frozen as Windows exes.
    # Currently disabled as multiprocessing isn't being used at the moment.
    multiprocessing.freeze_support()

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

    exitCode = None
    try:
        installDir = _installDirectory()
        application.setWindowIcon(QtGui.QIcon(os.path.join(installDir, 'icons', 'autojimmy.ico')))

        appDirectory = _applicationDirectory()
        os.makedirs(appDirectory, exist_ok=True)

        logDirectory = os.path.join(appDirectory, 'logs')
        cacheDirectory = os.path.join(appDirectory, 'cache')

        app.setupLogger(logDir=logDirectory, logFile='autojimmy.log')
        logging.info(f'{app.AppName} v{app.AppVersion}')

        try:
            locale.setlocale(locale.LC_ALL, '')
        except Exception as ex:
            logging.warning('Failed to set default locale', exc_info=ex)

        app.Config.setDirs(
            installDir=installDir,
            appDir=appDirectory)

        # Set configured log level immediately after configuration has been setup
        try:
            app.setLogLevel(app.Config.instance().logLevel())
        except Exception as ex:
            logging.warning('Failed to set log level', exc_info=ex)

        common.RequestCache.setCacheDir(cacheDirectory)

        installMapDir = os.path.join(installDir, 'data', 'map')
        overlayMapDir = os.path.join(appDirectory, 'map')
        customMapDir = os.path.join(appDirectory, 'my_map') # TODO: Change the directory to custom_maps or something
        travellermap.DataStore.setSectorDirs(
            installDir=installMapDir,
            overlayDir=overlayMapDir,
            customDir=customMapDir)

        # TODO: I think when this is done might be important as I think a copy is made of the current processes memory
        # TODO: Ephemeral (possibly random) port number?. Might be best to not use a random port as
        # it will bypass any persisted caching done by the web widget
        tileProxy = travellermap.TileProxy(
            port=8002,
            customMapDir=customMapDir)
        tileProxy.run()

        traveller.WorldManager.setMilieu(milieu=app.Config.instance().milieu())

        gunsmith.WeaponStore.setWeaponDirs(
            userWeaponDir=os.path.join(appDirectory, 'weapons'),
            exampleWeaponDir=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'weapons'))

        gui.configureAppStyle(application)

        # Check if there is new universe data available BEFORE the app loads the local snapshot so it
        # can be updated without restarting
        if travellermap.DataStore.instance().checkForNewSnapshot():
            # TODO: At some point in the future I can remove the note about it being faster
            answer = gui.AutoSelectMessageBox.question(
                text='New universe data is available. Do you want to update?\nDon\'t worry, updating is a LOT faster than it used to be.',
                stateKey='DownloadUniverseAtStartup')
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                updateProgress = gui.DownloadProgressDialog()
                updateProgress.exec()
                # Force delete of progress dialog to stop it hanging around. The docs say it will be deleted
                # when exec is called on the application
                # https://doc.qt.io/qt-6/qobject.html#deleteLater
                updateProgress.deleteLater()

        loadProgress = gui.LoadProgressDialog()
        if loadProgress.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            raise RuntimeError('Failed to load data')
        # Force delete of progress dialog to stop it hanging around. The docs say it will be deleted
        # when exec is called on the application
        # https://doc.qt.io/qt-6/qobject.html#deleteLater
        loadProgress.deleteLater()

        window = MainWindow()
        exitCode = application.exec()
    except Exception as ex:
        message = 'Failed to initialise application'
        logging.error(message, exc_info=ex)
        gui.MessageBoxEx.critical(
            parent=None,
            text=message,
            exception=ex)
        exitCode = 1

    sys.exit(exitCode)


if __name__ == "__main__":
    main()
