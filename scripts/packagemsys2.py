import os
import re
import shutil
import subprocess
import sys

_DumpBin = 'dumpbin.exe'

_Msys2InstallPath = 'c:\\msys64'
_PacmanPath = os.path.join(_Msys2InstallPath, 'usr', 'bin', 'pacman.exe')
_CairoPackageName = 'mingw-w64-x86_64-cairo'
_LibCairoFileName = 'libcairo-2.dll'
_DllRegex = re.compile(r'^\s+(.*\.dll)$')

_RelativeBinPath = os.path.join('mingw64', 'bin')
_SrcBinPath = os.path.join(_Msys2InstallPath, _RelativeBinPath)

_RelativeLicensePath = os.path.join('mingw64', 'share', 'licenses')
_SrcLicensePath = os.path.join(_Msys2InstallPath, _RelativeLicensePath)

if __name__ == "__main__":
    print('Packaging MSYS2')

    outputDir = sys.argv[1]
    if os.path.exists(outputDir):
        print('Output directory already exists')
        exit(1)

    try:
        subprocess.check_output([_DumpBin, '/NOLOGO'])
    except:
        print('Unable to run dumpbin')
        exit(1)

    try:
        subprocess.check_output([_PacmanPath, '--sync', '--noconfirm', '--refresh'])
        subprocess.check_output([_PacmanPath, '--sync', '--noconfirm', '--sysupgrade', _CairoPackageName])
    except:
        print('Failed to upgrade Cairo')
        exit(1)

    dstBinPath = os.path.join(outputDir, _RelativeBinPath)
    dstLicensePath = os.path.join(outputDir, _RelativeLicensePath)

    os.makedirs(dstBinPath, exist_ok=False)
    os.makedirs(dstLicensePath, exist_ok=False)

    _LibCairoFilePath = os.path.join(_SrcBinPath, _LibCairoFileName)
    if not os.path.exists(_LibCairoFilePath):
        print(f'{_LibCairoFilePath} not found')
        exit(1)

    todoList = [_LibCairoFilePath]
    copyList = [_LibCairoFilePath]
    seenSet = set()
    while todoList:
        filePath = todoList.pop(0)
        print(f'Checking {filePath} for dependencies')

        command = [_DumpBin, '/DEPENDENTS', filePath]
        result = subprocess.check_output(command)

        for line in result.decode().splitlines():
            matched = _DllRegex.match(line)
            if not matched:
                continue
            dependency = matched.group(1)
            if dependency in seenSet:
                continue

            seenSet.add(dependency)

            dependencyPath = os.path.join(_SrcBinPath, dependency)
            if os.path.exists(dependencyPath):
                copyList.append(dependencyPath)
                todoList.append(dependencyPath)

    # Copy dlls
    for filePath in copyList:
        print(f'Copying {filePath}')
        shutil.copy(filePath, dstBinPath)

    # Copy Licenses
    # NOTE: This copies the licenses for all packages currently installed for the
    # MSYS2 mingw64 compiler. This will include packages where we're not using any
    # of the dlls. I don't think there's a problem with doing this, as long as it
    # does include the licenses of the packages we are taking dlls from
    print(f'Copying Licenses')
    shutil.copytree(_SrcLicensePath, dstLicensePath, dirs_exist_ok=True)
