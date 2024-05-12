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
    and best case dice rolls at each point in the trading process
* Import of custom sectors
    * Custom sector data integrated into all tools
    * Posters of custom sectors automatically generated and overlaid onto Traveller Map views
    * Support for T5 Column & Tab sector files and XML & JSON metadata

## Installing
For Windows users, an installer is available [here](https://github.com/cthulhustig/autojimmy/releases).
The installer allows Auto-Jimmy to be run without requiring Python and other dependencies
to be manually installed. The downside of using the installer is I only create them
periodically so you may need to wait a bit longer for new features and bug fixes.

> [!NOTE] 
> The installer isn't digitally signed, so Windows may warn you about running it. If you
have problems, check out the [Known Issues](./docs/known_issues.md#windows-microsoft-defender-smartscreen-prevents-the-installer-from-running) section.

For Linux, macOS and more adventurous Windows users, the instructions below cover how to
download Auto-Jimmy, install dependencies and run the application.

> [!NOTE]  
> If you have any problems when installing, you can check the
> [Known Issues](./docs/known_issues.md) for a possible solution.

### Prerequisites
Before you begin, ensure that you have the following prerequisites installed:
* Python 3.11+ (3.8+ _should_ be ok, ymmv)
* Pip (Python package installer)

> [!IMPORTANT]  
> If you're using Python 3.12 on Windows, see
> [Installing requirements.txt fails for Python 3.12](./docs/known_issues.md#windows-installing-requirementstxt-fails-for-python-312)

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
create custom sectors as it allows the use of SVG sector posters rather than bitmap
posters. Primarily this is done to reduce visual artifacts when compositing the
posters onto the map tiles Traveller Map uses to display the universe, however, it also
has the added advantage that SVG posters take less time to generate.

#### Install libcairo on Windows
On Windows, libcairo can be installed using the package manager that comes with
[MSYS2](https://www.msys2.org/).
1. Follow the instructions from https://www.msys2.org/ to install MSYS2 . When prompted to
   choose an install location, it's recommended to use the default of `c:\msys64`
2. Once the installer has completed it should launch a MSYS2 command prompt. If it doesn't
   happen, or you already have MSYS2 installed, you can launch one from the Windows Start
   Menu.

   Note: MSYS2 adds multiple command prompt entries to the Start Menu, each for a different
   compiler. It doesn't matter which you use to run the following command.
3. Run the following command from the MSYS2 command prompt:
   ```
   pacman -S mingw-w64-x86_64-cairo
   ```
4. If you choose to install MSYS2 in a location other that the default of `c:\msys64`, you
   will need to set the `MSYS2_PATH` environment variable to the location you installed
   it.

#### Install libcairo on macOS
On macOS, libcairo can be installed using the [Homebrew](https://brew.sh/) package manager.
1. Follow the instructions at https://brew.sh/ to install Homebrew 
2. Open a terminal.
3. Run the following command:
   ```
   brew install cairo
   ```

#### Install libcairo on Linux
How libcairo is installed on Linux will vary depending on which distro you are using.
Some distros, such as recent versions of Ubuntu, come with it already installed.

### Step 4: Running Auto-Jimmy
1. Open a terminal or command prompt.
2. Navigate to the directory containing the Auto-Jimmy source code
3. Execute the following command to run the application:
   ```
   python3 autojimmy.py
   ```

## Useful Links
* [Known Issues](./docs/known_issues.md)
* [FAQ](./docs/faq.md)
* [Screenshots](./docs/screenshots.md)
* [Custom Sectors](./docs/custom_sectors.md)
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
his help with the integration and Geir Lanesskog for his clarification of rules from the
Mongoose Robots Handbook.

