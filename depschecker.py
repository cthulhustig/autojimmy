import enum
import importlib
import os
import platform

class CairoSvgState(enum.Enum):
    Working = 0
    NotInstalled = 1
    NoLibraries = 2


# NOTE: This script works on the assumption it's in the root of the install directory
_InstallPath = os.path.dirname(os.path.realpath(__file__))

# Library names to import when testing for dependencies
_Requirements = [
    'PyQt5',
    'PyQt5.QtWebEngineWidgets',
    'pyqtgraph',
    'darkdetect',
    'reportlab',
    'PIL',
    'aiofiles',
    'aiohttp',
    'aiosqlite',
    'qasync',
    'xmlschema',
    'cairosvg',
    'numpy']
_RequirementsFile = 'requirements.txt'
_CairoModuleName = 'cairosvg'

# NOTE: This is public so other scripts can check the status of libcairo
DetectedCairoSvgState = CairoSvgState.Working


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

# On Windows the expectation is libcairo will come from MSYS2. This will either
# be manually installed following the instructions in the README.md if cloning
# the repo or be a local copy in the install directory if using the installer.
# Multiple paths will be added if they exist in a best effort attempt to get
# something working.
# NOTE: It's important these paths are added at the end of the existing path as
# the MSYS2 directory can contains a lot of other dlls and binaries so we don't
# want them taking precedence over part of the system install.
if platform.system() == 'Windows':
    paths = []

    # If the MSYS2_PATH environment variable is set it should be the first
    # entry added to the path
    envPath = os.environ.get('MSYS2_PATH')
    if envPath is not None:
        binPath = os.path.join(envPath, 'mingw64', 'bin')
        if os.path.exists(binPath):
            paths.append(binPath)

    # If there is a local copy of msys2 then it should be used next
    binPath = os.path.join(_InstallPath, 'msys64', 'mingw64', 'bin')
    if os.path.exists(binPath):
        paths.append(binPath)

    # Lastly the default msys2 path should be added to the path if it
    # exists
    binPath = os.path.join('c:\\', 'msys64', 'mingw64', 'bin')
    if os.path.exists(binPath):
        paths.append(binPath)

    if paths:
        os.environ["PATH"] += os.pathsep + os.pathsep.join(paths)

# Try to import each of the required modules
_MissingRequirements = []
for lib in _Requirements:
    try:
        importlib.import_module(lib)
    except OSError as ex:
        if lib == _CairoModuleName:
            # CairoSVG is optional
            DetectedCairoSvgState = CairoSvgState.NoLibraries
            continue
        raise # Rethrow other OSErrors
    except ModuleNotFoundError as ex:
        if lib == _CairoModuleName:
            # CairoSVG is optional
            DetectedCairoSvgState = CairoSvgState.NotInstalled
            continue
        _MissingRequirements.append(lib)

if _MissingRequirements:
    print(f'Unable to start Auto-Jimmy due to missing dependencies.')
    print('The following modules were not found: ' + ', '.join(_MissingRequirements))
    print()
    print('To install all required dependencies, run the following commands:')
    print()
    # NOTE: This assumes that this file is at the same level as the requirements file
    print(f'cd {_InstallPath}')
    print(f'pip3 install -r {_RequirementsFile}')
    print()
    print('Further documentation can be found at https://github.com/cthulhustig/autojimmy')
    exit(1)
