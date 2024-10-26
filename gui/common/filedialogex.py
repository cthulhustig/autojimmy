import gui
import os
import typing
from PyQt5 import QtWidgets, QtCore

class FileDialogEx(QtWidgets.QFileDialog):
    _SettingSection = 'FileDialogEx'

    @staticmethod
    def getSaveFileName(
            parent: typing.Optional[QtWidgets.QWidget] = None,
            caption: typing.Optional[str] = None,
            directory: typing.Optional[str] = None,
            filter: typing.Optional[str] = None,
            initialFilter: typing.Optional[str] = None,
            options: typing.Union[QtWidgets.QFileDialog.Options, QtWidgets.QFileDialog.Option] = None,
            lastDirKey: typing.Optional[str] = None,
            defaultFileName: typing.Optional[str] = None
            ) -> typing.Tuple[str, str]:
        directory = FileDialogEx._initialPath(
            directory=directory,
            lastDirKey=lastDirKey,
            defaultFileName=defaultFileName)

        path, filter = QtWidgets.QFileDialog.getSaveFileName(
            parent=parent,
            caption=caption,
            directory=directory,
            filter=filter,
            initialFilter=initialFilter,
            options=options if options != None else QtWidgets.QFileDialog.Options())
        if path and lastDirKey:
            FileDialogEx._setLastDir(key=lastDirKey, dir=os.path.dirname(path))
        return (path, filter)

    @staticmethod
    def getOpenFileNames(
            parent: typing.Optional[QtWidgets.QWidget] = None,
            caption: typing.Optional[str] = None,
            directory: typing.Optional[str] = None,
            filter: typing.Optional[str] = None,
            initialFilter: typing.Optional[str] = None,
            options: typing.Union[QtWidgets.QFileDialog.Options, QtWidgets.QFileDialog.Option] = None,
            lastDirKey: typing.Optional[str] = None
            ) -> typing.Tuple[typing.List[str], str]:
        directory = FileDialogEx._initialPath(
            directory=directory,
            lastDirKey=lastDirKey)

        paths, filter = QtWidgets.QFileDialog.getOpenFileNames(
            parent=parent,
            caption=caption,
            directory=directory,
            filter=filter,
            initialFilter=initialFilter,
            options=options if options != None else QtWidgets.QFileDialog.Options())
        if paths and lastDirKey:
            FileDialogEx._setLastDir(key=lastDirKey, dir=os.path.dirname(paths[0]))
        return (paths, filter)

    @staticmethod
    def getOpenFileName(
            parent: typing.Optional[QtWidgets.QWidget] = None,
            caption: typing.Optional[str] = None,
            directory: typing.Optional[str] = None,
            filter: typing.Optional[str] = None,
            initialFilter: typing.Optional[str] = None,
            options: typing.Union[QtWidgets.QFileDialog.Options, QtWidgets.QFileDialog.Option] = None,
            lastDirKey: typing.Optional[str] = None
            ) -> typing.Tuple[str, str]:
        directory = FileDialogEx._initialPath(
            directory=directory,
            lastDirKey=lastDirKey)

        path, filter = QtWidgets.QFileDialog.getOpenFileName(
            parent=parent,
            caption=caption,
            directory=directory,
            filter=filter,
            initialFilter=initialFilter,
            options=options if options != None else QtWidgets.QFileDialog.Options())
        if path and lastDirKey:
            FileDialogEx._setLastDir(key=lastDirKey, dir=os.path.dirname(path))
        return (path, filter)

    @staticmethod
    def _initialPath(
            directory: typing.Optional[str] = None,
            lastDirKey: typing.Optional[str] = None,
            defaultFileName: typing.Optional[str] = None,
            ) -> typing.Optional[str]:
        path = directory
        if not path and lastDirKey:
            path = FileDialogEx._lastDir(key=lastDirKey)
            if not path:
                path = QtCore.QDir.homePath()
        if defaultFileName:
            path = os.path.join(path, defaultFileName)
        return path

    @staticmethod
    def _lastDir(key: str) -> typing.Optional[str]:
        settings = gui.globalWindowSettings()
        settings.beginGroup(FileDialogEx._SettingSection)
        lastDir = gui.safeLoadSetting(
            settings=settings,
            key=key,
            type=str,
            default=None)
        settings.endGroup()
        return lastDir

    @staticmethod
    def _setLastDir(key: str, dir: str) -> None:
        settings = gui.globalWindowSettings()
        settings.beginGroup(FileDialogEx._SettingSection)
        settings.setValue(key, dir)
        settings.endGroup()

