# Known Issues

## Windows: Installing requirements.txt fails for Python 3.12
At the time of writing, Python 3.12 is relatively new, and the precompiled wheels used by some
packages have not yet been rebuilt for it. The wheels will automatically be built as part of
the installation, however, this will fail with the error below if you don't have the Visual
Studio Build Tools installed on your system.

> ERROR: Could not build wheels for frozenlist, multidict, which is required to install pyproject.toml-based projects

One solution to this is to simply use Python 3.11 until package maintainers have had time to
update them for Python 3.12.

Alternatively, you can install the Visual Studio Build Tools by following these steps:
1. Download the Visual Studio Build Tools installer from https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Run the installer
3. When prompted to choose which Workloads to install, check "Desktop development with C++"
   then click the Install button in the lower right corner
4. Once the installer has completed, re-run the command to install requirements.txt

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

## Debian/Ubuntu: The integrated Traveller Map view is blank
> [!IMPORTANT]
> If using venv to run Python, it's recommended to create a new virtual environment
> specifically for running Auto-Jimmy, then repeat [Install Python Dependencies] for
> that environment before continuing with this fix.

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
[Integrated Traveller Map view is blank](https://github.com/cthulhustig/autojimmy#debianubuntu-the-integrated-traveller-map-view-is-blank),
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
1. rm -rf <VENV_PATH>/lib/<PYTHON_VERSION>/site-packages/PyQt5
2. pip3 install -r requirements.txt
3. rm -rf <VENV_PATH>/lib/<PYTHON_VERSION>/site-packages/PyQt5
4. ln -s /usr/lib/python3/dist-packages/PyQt5 <VENV_PATH>/lib/<PYTHON_VERSION>/site-packages/PyQt5

> [!NOTE]
> There may be a better way to resolve [Integrated Traveller Map view is blank](https://github.com/cthulhustig/autojimmy#debianubuntu-the-integrated-traveller-map-view-is-blank).
> If you know of one, please raise an [Issue](https://github.com/cthulhustig/autojimmy/issues)
> with details of how so I can update this help.

## Debian/Ubuntu: The world search edit box on Traveller Map windows keeps resetting as I type
This seems to be an issue with Wayland on Ubuntu 23.04. It can be fixed by running the
following command before running Auto-Jimmy ([source](https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System/issues/288))
```
XDG_SESSION_TYPE=x11
```

## macOS: World information tool tips aren't showing tile images from Traveller Map
This issue can be caused by an HTTPS certificate failure. After installing a versions of
Python downloaded from www.python.org on macOS, you need to manually install the Python
certificates.
1. From the main toolbar select *Go > Applications*
2. Find the application directory for Python 3.x and open it
3. Click on "Install Certificates.command" and select *Open*
