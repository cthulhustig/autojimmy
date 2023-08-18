# Installer Build
These instructions cover building Auto-Jimmy into a Windows installer that allows the application to
be installed and run on another system without the need to manually install Python or other
dependencies. This works by using PyInstaller to create a frozen snapshot of the application and all
dependencies (including the Python binary), this is then packages into an installer using Inno Setup.

## Prerequisites
Before you begin, you need to have completed the instructions to clone the Auto-Jimmy repo and install
its dependencies before performing these instructions. See [README.md](../README.md) for more details.

## Step 1: Install Inno Setup
1. Download the Inno Setup installer from [here](https://jrsoftware.org/isdl.php) and install it
2. Add the Inno Setup install directory to your path if the installer didn't do it

## Step 2: Install PyInstaller
1. Open a command prompt
2. Execute the following command to install PyInstaller:
   ```
   pip3 install pyinstaller
   ```

## Step 3: Build Installer
1. Open a command prompt
2. Navigate to the clone of the Auto-Jimmy repository
3. Execute the following command to build the installer:
   ```
   buildwin.bat
   ```