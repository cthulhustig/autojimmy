import app
import os
from PyQt5 import QtCore

_CachedWindowSettings = None
def globalWindowSettings():
    global _CachedWindowSettings
    if not _CachedWindowSettings:
        filePath = os.path.join(app.ConfigEx.instance().appDir(), 'windows.ini')
        _CachedWindowSettings = QtCore.QSettings(filePath, QtCore.QSettings.Format.IniFormat)
    return _CachedWindowSettings
