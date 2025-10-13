# Known Issues

## Windows: Microsoft Defender SmartScreen prevents the installer from running
This happens because the installer executable isn't digitally signed so Windows doesn't
know who created it and therefore doesn't automatically trust it. Auto-Jimmy is just a
passion project, so it doesn't really make sense for me to purchase the digital
certificate that would allow me to sign it.
If you want to make Windows run the installer, you can do the following:
1. Click the "More info" link directly under the warning text
2. Click "Run anyway"

## Windows: Running Auto-Jimmy from the command line opens the Windows app store
By default, Microsoft have made Windows use a fake Python executable that redirects to the app
store in an effort to get you to use it to install Python. If you install Python 3 manually
you may need to disable this "feature".
1. Use Windows search to open "Manage app execution aliases"
2. Disable the entries for python.exe and python3.exe

## Windows: Double clicking on autojimmy.py or autojimmy.pyw doesn't run the application
See the fix for [Running Auto-Jimmy from the command line opens the Windows app store](#windows-running-auto-jimmy-from-the-command-line-opens-the-windows-app-store)

## Debian/Ubuntu: qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found
This issue can be resolved by executing the following command
([source](https://forum.qt.io/topic/127696/qt-qpa-plugin-could-not-load-the-qt-platform-plugin-xcb-in-even-though-it-was-found/27))
```
sudo apt-get install '^libxcb.*-dev' libx11-xcb-dev libglu1-mesa-dev libxrender-dev libxi-dev libxkbcommon-dev libxkbcommon-x11-dev
```

## Debian/Ubuntu: The Traveller Map window is blank
> [!IMPORTANT]
> If using venv to run Python, it's recommended to create a new virtual environment
> specifically for running Auto-Jimmy, then repeat [Install Python Dependencies](../README.md#step-2-install-python-dependencies)
> for that environment before continuing with this fix.

> [!NOTE]
> There may be a better way to resolve this. If you know of one, please raise an
> [Issue](https://github.com/cthulhustig/autojimmy/issues) with details of how so I
> can update this help.

The issue can be resolved by executing the following commands
([source](https://stackoverflow.com/questions/73868174/pyqtwebengine-dontt-show-nothing)).
```
pip3 uninstall PyQt5 PyQt5-Qt5 PyQt5-sip PyQtWebEngine PyQtWebEngine-Qt5
sudo apt install python3-pyqt5.qtwebengine python3-pyqt5.qtsvg
```

If you're using venv, you will also need to run the following commands to symlink the
system PyQt5 install into your venv site-packages, replacing `<VENV_PATH>` with the path
to the venv being used and `<PYTHON_VERSION>` with the version of python being used (e.g.
python3.11).
```
rm -rf <VENV_PATH>/lib/<PYTHON_VERSION>/site-packages/PyQt5
ln -s /usr/lib/python3/dist-packages/PyQt5 <VENV_PATH>/lib/<PYTHON_VERSION>/site-packages/PyQt5
```

## Debian/Ubuntu: Installing requirements.txt fails when upgrading Auto-Jimmy
If your running Python in a venv and have previously used the workaround for
[The Traveller Map window is blank](#debianubuntu-the-traveller-map-window-is-blank),
you may get a error similar to the following after downloading a new version
of the Auto-Jimmy source and using pip to install requirements for the new
version.

> ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied: '<VENV_PATH>/lib/<PYTHON_VERSION>/site-packages/PyQt5/Qt5'<br>
> Check the permissions.

The issue can be resolved by deleting the symlink you created when applying the
previous fix, installing the requirements then re-applying the original fix. To
do this run the following commands, replacing `<VENV_PATH>` with the path to the
venv being used and `<PYTHON_VERSION>` with the version of python being used
(e.g. python3.11).
1. rm <VENV_PATH>/lib/<PYTHON_VERSION>/site-packages/PyQt5
2. pip3 install -r requirements.txt
3. rm -rf <VENV_PATH>/lib/<PYTHON_VERSION>/site-packages/PyQt5
4. ln -s /usr/lib/python3/dist-packages/PyQt5 <VENV_PATH>/lib/<PYTHON_VERSION>/site-packages/PyQt5

> [!NOTE]
> There may be a better way to resolve [The Traveller Map window is blank](#debianubuntu-the-traveller-map-window-is-blank).
> If you know of one, please raise an [Issue](https://github.com/cthulhustig/autojimmy/issues)
> with details of how so I can update this help.

## Debian/Ubuntu: The world search edit box on Traveller Map windows keeps resetting as I type
This seems to be an issue with Wayland on Ubuntu 23.04. It can be fixed by running the
following command before running Auto-Jimmy ([source](https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System/issues/288))
```
XDG_SESSION_TYPE=x11
```

## macOS: Segmentation fault: 11 when starting
This can happen when using Python 3.12. Using Python 3.11 resolves the issue.
