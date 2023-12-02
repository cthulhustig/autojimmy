# Auto-Jimmy
Auto-Jimmy is a collection of tools for the Traveller RPG. It's primarily aimed at Mongoose 1e and
2e Traveller, but much of the functionality can be used with other rule systems. It can be used
offline, but can also integrate with Traveller Map (internet connection required). It's written in
Python and can be run on Windows, Linux and macOS.

## Feature Highlights
* Rule system agnostic jump route calculation
    * Waypoint worlds the route must pass through
    * Avoid selected worlds and/or worlds based on attributes
    * Optimise routes by number of jumps, parsecs travelled or estimated cost
    * Integration with Traveller Map to display routes
* Refuelling plan calculation using Mongoose rules
    * Calculation of where to refuel along a jump route and how much fuel to take on in order to
    minimise costs
    * Most useful for long routes and/or when reliant on star port refuelling
* Automation of weapon creation using the Mongoose 2e Field Catalogue rules
    * Calculation of weapon attributes based on configuration and loaded ammunition
    * Automatically generated notes listing the more complex rules that apply to a weapon, when
    they apply and what their effect are
    * Export of weapons to PDF
* Referee aids Mongoose Speculative Trading & Smuggling rules
    * Dice rollers for purchase and sale process
    * Support for local brokers
* Experimental player aids for Mongoose Speculative Trading & Smuggling rules
    * Options to see how each variable in the trading process would affect a trade
    * Estimation of profits for trading between worlds if the player was to make average, worst
    and best case dice roles at each point in the trading process
* Import of custom sectors
    * Custom sector data integrated into all tools
    * Posters of custom sectors automatically generated and merged into Traveller Map views
    * Support for T5 Column & Row sector files and XML & JSON metadata

## Installing
For Windows users, an installer is available [here](https://github.com/cthulhustig/autojimmy/releases).
The installer allows Auto-Jimmy to be run without requiring Python and dependencies to be
manually installed. Note that the installer isn't digitally signed, so Windows may warn you about
running it. If you have problems, check out the [Common Issues](#Common-Issues) section.

For Linux, macOS and more adventurous Windows users, the instructions below cover how to download
Auto-Jimmy, install dependencies and run the application.

### Prerequisites
Before you begin, ensure that you have the following prerequisites installed:
* Python 3.11+ (3.8+ _should_ be ok, ymmv)
* Pip (Python package installer)

### Step 1: Download the Auto-Jimmy Source Code
Downloading the source code can be done either by cloning the repo with git or downloading a zip archive.

#### Option 1: Clone the Auto-Jimmy Repository
1. Open a terminal or command prompt.
2. Execute the following command to clone the Auto-Jimmy repository:
   ```
   git clone https://github.com/cthulhustig/autojimmy.git
   ```
#### Option 2: Download Source Code Zip File
1. Download https://github.com/cthulhustig/autojimmy/archive/refs/heads/main.zip
2. Extract the downloaded zip file

### Step 2: Install Python Dependencies
1. Open a terminal or command prompt.
2. Navigate to the directory containing the Auto-Jimmy source code
3. Execute the following command to install the required Python dependencies:
   ```
   pip3 install -r requirements.txt
   ```
   If using macOS Sierra execute this instead:
   ```
   pip3 install -r requirements_sierra.txt
   ```

### Step 3: Install libcairo (Optional)
Installing [libcairo](https://www.cairographics.org/) is recommended if you're going to
create custom sectors. It allows Auto-Jimmy to use SVG posters of your custom sectors
rather than bitmap posters. Primarily this is done to reduce visual artifacts when
compositing the posters onto the map tiles Traveller Map uses to display the universe,
however, it also has the added advantage that SVG posters take less time to generate.

#### Windows
On Windows, libcairo can be installed using the package manager that comes with MSYS2.
1. Follow the instructions here to install MSYS2 https://www.msys2.org/
> [!NOTE]  
> It's recommended to install MSYS2 in the default location of `c:\msys64`
2. Once the installer has completed it should launch a MSYS2 command prompt. If it doesn't
   happen, or you already have MSYS2 installed, you can launch one from the Windows Start
   Menu.
> [!NOTE]  
> MSYS2 add multiple command prompt entries to the Start Menu, each for a different
compiler. It doesn't which you use to run the following command.
3. Run the following command from the MSYS2 command prompt to install libcairo:
   ```
   pacman -S mingw-w64-x86_64-cairo
   ```
4. If you choose to install MSYS2 in a location other that the default of `c:\msys64`, you
   will need to set the `MSYS2_PATH` environment variable to the location you installed
   it.

#### macOS
On macOS, libcairo can be installed using the brew package manager.
1. Follow the instructions here to install brew https://brew.sh/
2. Open a terminal or command prompt.
3. Run the following command to install libcairo:
   ```
   brew install cairo
   ```

#### Linux
How libcairo is installed on Linux will vary depending on which distro you are using.
Some distros, such as recent versions of Ubuntu, come with it already installed.

### Step 4: Running Auto-Jimmy
1. Open a terminal or command prompt.
2. Navigate to the directory containing the Auto-Jimmy source code
3. Execute the following command to run the application:
   ```
   python3 autojimmy.py
   ```

## Common Issues

### Windows: Microsoft Defender SmartScreen prevents the installer from running
This happens because the installer executable isn't digitally signed so Windows doesn't
know who created it and therefore doesn't automatically trust it. Auto-Jimmy is just a
passion project, so it doesn't really make sense for me to purchase the digital
certificate that would allow me to sign it.
If you want to make Windows run the installer, you can do the following:
1. Click the "More info" link directly under the warning text
2. Click "Run anyway"

### Windows: Running Auto-Jimmy from the command line opens the Windows app store
By default, Microsoft have made Windows use a fake Python executable that redirects to the app
store in an effort to get you to use it to install Python. If you install Python 3 manually
you may need to disable this "feature".
1. Use Windows search to open "Manage app execution aliases"
2. Disable the entries for python.exe and python3.exe

### Windows: Double clicking on autojimmy.py or autojimmy.pyw doesn't run the application
See the fix for [Running Auto-Jimmy from the command line opens the Windows app store](#windows-running-auto-jimmy-from-the-command-line-opens-the-windows-app-store)

### Debian/Ubuntu: qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found
This issue can be resolved by executing the following command ([source](https://forum.qt.io/topic/127696/qt-qpa-plugin-could-not-load-the-qt-platform-plugin-xcb-in-even-though-it-was-found/27))
```
sudo apt-get install '^libxcb.*-dev' libx11-xcb-dev libglu1-mesa-dev libxrender-dev libxi-dev libxkbcommon-dev libxkbcommon-x11-dev
```

### Debian/Ubuntu: Integrated Traveller Map view is blank
IMPORTANT: If using venv to run Python, it's recommended to create a new virtual
environment specifically for running Auto-Jimmy, then repeat [Install Python Dependencies]
for that environment before continuing with this fix.

The issue can be resolved by executing the following commands ([source](https://stackoverflow.com/questions/73868174/pyqtwebengine-dontt-show-nothing)).
```
pip3 uninstall PyQt5 PyQt5-Qt5 PyQt5-sip PyQtWebEngine PyQtWebEngine-Qt5
sudo apt install python3-pyqt5.qtwebengine python3-pyqt5.qtsvg
```
If you're using venv, you will also need to run the following commands to symlink the
system PyQt5 install into your venv site-packages, replacing <VENV_PATH> with the path
to the venv being used and <PYTHON_VERSION> with the version of python being used (e.g.
python3.11).
```
rm -rf <VENV_PATH>/lib/<PYTHON_VERSION>/site-packages/PyQt5
ln -s /usr/lib/python3/dist-packages/PyQt5 <VENV_PATH>/lib/<PYTHON_VERSION>/site-packages/PyQt5
```

### Debian/Ubuntu: The world search edit box on Traveller Map windows keeps resetting as I type
This seems to be an issue with Wayland on Ubuntu 23.04. It can be fixed by running the
following command before running Auto-Jimmy ([source](https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System/issues/288))
```
XDG_SESSION_TYPE=x11
```

### macOS: World information tool tips aren't showing tile images from Traveller Map
This issue can be caused by an HTTPS certificate failure. After installing a versions of
Python downloaded from www.python.org on macOS, you need to manually install the Python
certificates.
1. From the main toolbar select *Go > Applications*
2. Find the application directory for Python 3.x and open it
3. Click on "Install Certificates.command" and select *Open*

## Useful Links
* [FAQ](./docs/faq.md)
* [Screenshots](./docs/screenshots.md)
* [Installer Build](./docs/installer_build.md)
* [Source Code](https://github.com/cthulhustig/autojimmy)
* [Traveller Map](https://travellermap.com)
* [Traveller Map API](https://travellermap.com/doc/api)

## Legal
Auto-Jimmy is released under the GPLv3. Copies of that licence and licences for dependencies can
be found [here](https://github.com/cthulhustig/autojimmy).

This repo contains a snapshot of the Traveller Map web interface and universe data. The copy of
the web interface is used to prevent issues caused by the continued development of Traveller Map.
The universe data is used to increase performance and allow the application to work offline. These
files are the copyright of their creators.

Auto-Jimmy is not endorsed by the wonderful people at Traveller Map, Mongoose Publishing or Far
Future Enterprises. However, a great deal of thanks goes to Joshua Bell from Traveller Map for
his help with the integration.

