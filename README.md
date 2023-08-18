# Auto-Jimmy
Auto-Jimmy is a collection of tools for the Traveller RPG. It's primarily aimed at Mongoose 1e and
2e Traveller, but much of the functionality can be used with other rule systems. It can be used
offline, but can also integrate with Traveller Map (internet connection required).

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

## Installing
Windows users are recommended to use the installer available [here](https://github.com/cthulhustig/autojimmy/releases).
The installer allows Auto-Jimmy to be run without requiring Python and required libraries to be
manually installed.

For Linux, macOS and more adventurous Windows users, the instructions below cover how to clone the
Auto-Jimmy repository and run the application.

### Prerequisites
Before you begin, ensure that you have the following prerequisites installed:
* Python 3.11+ (3.8+ _should_ be ok, ymmv)
* Pip (Python package installer)

### Step 1: Clone the Auto-Jimmy Repository
1. Open a terminal or command prompt.
2. Execute the following command to clone the Auto-Jimmy repository:
   ```
   git clone https://github.com/cthulhustig/autojimmy.git
   ```

### Step 2: Install Python Dependencies
1. Open a terminal or command prompt.
2. Navigate to the clone of the Auto-Jimmy repository
3. Execute the following command to install the required Python dependencies:
   ```
   pip3 install -r requirements.txt
   ```
   If using macOS Sierra execute this instead:
   ```
   pip3 install -r requirements_sierra.txt
   ```

### Step 3: Running Auto-Jimmy
1. Open a terminal or command prompt.
2. Navigate to the clone of the Auto-Jimmy repository
3. Execute the following command to run the application:
   ```
   python3 autojimmy.py
   ```

## Common Issues

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
This issue can be resolved by executing the following commands ([source](https://stackoverflow.com/questions/73868174/pyqtwebengine-dontt-show-nothing))
```
pip3 uninstall PyQt5 PyQt5-Qt5 PyQt5-sip PyQtWebEngine PyQtWebEngine-Qt5
sudo apt install python3-pyqt5.qtwebengine
```

### macOS: World information tool tips aren't showing tile images from Traveller Map
This issue can be caused be caused by an HTTPS certificate failure. After installing a versions of
Python downloaded from www.python.org on macOS, you need to manually install the Python
certificates.
1. From the main toolbar select *Go > Applications*
2. Find the application directory for Python 3.x an open it
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

