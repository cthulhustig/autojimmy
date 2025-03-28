from PyQt5 import QtWidgets, QtCore, QtGui
import app
import gui
import locale
import logging
import os
import pathlib
import traveller
import travellermap

class MyWidget(gui.WindowWidget):
    def __init__(self):
        super().__init__(title='Map Hack', configSection='MapHack')
        self._widget = gui.LocalMapWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._widget)

        self.setLayout(layout)

def _installDirectory() -> str:
    return os.path.dirname(os.path.realpath(__file__))

def _applicationDirectory() -> str:
    if os.name == 'nt':
        return os.path.join(os.getenv('APPDATA'), app.AppName)
    else:
        return os.path.join(pathlib.Path.home(), '.' + app.AppName.lower())

if __name__ == "__main__":
    application = QtWidgets.QApplication([])

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

    traveller.WorldManager.setMilieu(milieu=travellermap.Milieu.M1105)
    traveller.WorldManager.instance().loadSectors()

    gui.configureAppStyle(application)

    window = MyWidget()
    window.resize(800, 600)
    #window.setFixedSize(256, 256)
    #window.setFixedSize(937, 723)
    window.show()
    application.exec_()
