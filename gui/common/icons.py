import app
import enum
import gui
import os
import typing
from PyQt5 import QtGui

class Icon(enum.Enum):
    FrozenColumn = 'frozen_column'
    UnfrozenColumn = 'unfrozen_column'
    CloseTab = 'close_tab'
    NewFile = 'new_file'
    SaveFile = 'save_file'
    DeleteFile = 'delete_file'
    CopyFile = 'copy_file'
    RenameFile = 'rename_file'
    RevertFile = 'revert_file'
    ImportFile = 'import_file'
    ExportFile = 'export_file'
    Search = 'search'
    Info = 'info'


_IconMap: typing.Dict[str, QtGui.QIcon] = {}

class IconTheme(enum.Enum):
    DarkMode = 0
    LightMode = 1

def loadIcon(
        icon: Icon,
        theme: typing.Optional[IconTheme] = None
        ) -> QtGui.QIcon:
    if not theme:
        theme = IconTheme.DarkMode if gui.isDarkModeEnabled() else IconTheme.LightMode

    baseFileName = f'{icon.value}_{"dark" if theme == IconTheme.DarkMode else "light"}'
    iconFileName = baseFileName + '.png'
    icon = _IconMap.get(iconFileName)
    if not icon:
        iconDir = os.path.join(app.Config.instance().installDir(), 'icons')
        normalIconPath = os.path.join(iconDir, iconFileName)
        icon = QtGui.QIcon(QtGui.QPixmap(normalIconPath))

        disabledIconPath = os.path.join(iconDir, baseFileName + '_disabled.png')
        if os.path.exists(disabledIconPath):
            icon.addPixmap(QtGui.QPixmap(disabledIconPath), QtGui.QIcon.Mode.Disabled)

        _IconMap[iconFileName] = icon
    return icon
