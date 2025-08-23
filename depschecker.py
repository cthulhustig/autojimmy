import enum
import importlib
import os
import platform
import sys

# NOTE: This script works on the assumption it's in the root of the install directory
_InstallPath = os.path.dirname(os.path.realpath(__file__))

# Library names to import when testing for dependencies
_Requirements = [
    'PyQt5',
    'pyqtgraph',
    'darkdetect',
    'reportlab',
    'PIL',
    'aiofiles',
    'aiohttp',
    'aiosqlite',
    'qasync',
    'xmlschema',
    'numpy',
    'packaging',
    'requests']
_RequirementsFile = 'requirements.txt'

# This is just a noddy check to make sure I remember to update the list. If it
# actually triggers it's pretty ugly as it gets printed out by any sub
# processes that are spawned
try:
    with open(_RequirementsFile, 'r') as file:
        lineCount = len([line for line in file.readlines() if line.strip()[:1] not in ('', '#')])
        if lineCount != len(_Requirements):
            print(f'Dependency checker requirements list length doesn\'t match the number of lines in {_RequirementsFile}, results may be inaccurate!')
except Exception as ex:
    print(f'Failed to open {_RequirementsFile} for dependency checking')

# Try to import each of the required modules
_MissingRequirements = []
for lib in _Requirements:
    try:
        importlib.import_module(lib)
    except OSError as ex:
        raise # Rethrow other OSErrors
    except ModuleNotFoundError as ex:
        _MissingRequirements.append(lib)

if _MissingRequirements and not os.environ.get('AUTOJIMMY_NO_DEPENDENCIES_CHECK'):
    # NOTE: This assumes that this file is at the same level as the requirements file
    errorMessage = \
        'Unable to start Auto-Jimmy due to missing dependencies.\n'  \
        '\n' \
        'The following modules were not found: \n' + ', '.join(_MissingRequirements) + '\n' \
        '\n' \
        'To install all required dependencies, open a command prompt and run the following commands:\n' \
        '\n' \
        f'cd {_InstallPath}\n' \
        f'pip3 install -r {_RequirementsFile}\n' \
        '\n' \
        'Further documentation can be found at\nhttps://github.com/cthulhustig/autojimmy'

    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "Error", errorMessage, QMessageBox.Ok)
        sys.exit(1)
    except Exception:
        pass # Just fall through to print to the console

    print(errorMessage)
    sys.exit(1)
