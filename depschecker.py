import enum
import importlib
import os

class CairoSvgState(enum.Enum):
    Working = 0
    NotInstalled = 1
    NoLibraries = 2

_Requirements = [
    'PyQt5',
    'PyQt5.QtWebEngineWidgets',
    'pyqtgraph',
    'darkdetect',
    'reportlab',
    'PIL',
    'aiohttp',
    'qasync',
    'xmlschema',
    'cairosvg',
    'numpy']
_RequirementsFile = 'requirements.txt'
_CairoModuleName = 'cairosvg'

DetectedCairoSvgState = CairoSvgState.Working

# This is just a noddy check to make sure I remember to update the list. If it actually triggers it's pretty
# ugly as it gets printed out by any sub processes that are spawned
try:
    with open(_RequirementsFile, 'r') as file:
        lineCount = len(file.readlines())
        if lineCount != len(_Requirements):
            print(f'Dependency checker requirements list length doesn\'t match the number of lines in {_RequirementsFile}, results may be inaccurate!')
except Exception as ex:
    print(f'Failed to open {_RequirementsFile} for dependency checking')

# Try to import each of the required modules to display
for lib in _Requirements:
    try:
        importlib.import_module(lib)
    except OSError as ex:
        if lib == _CairoModuleName:
            DetectedCairoSvgState = CairoSvgState.NoLibraries
            continue
        raise # Rethrow other OSErrors on
    except ModuleNotFoundError as ex:
        if lib == _CairoModuleName:
            DetectedCairoSvgState = CairoSvgState.NotInstalled
            continue

        print(ex)
        print()
        print('To install all dependencies required by Auto-Jimmy, run the following commands:')
        print()
        # NOTE: This assumes that this file is at the same level as the requirements file
        print(f'cd {os.path.dirname(os.path.realpath(__file__))}')
        print(f'pip3 install -r {_RequirementsFile}')
        exit(1)
