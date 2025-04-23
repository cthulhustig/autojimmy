@echo off
rem  Building the installer requires the following to be installed and added to the path
rem  - PyInstaller - https://pyinstaller.org
rem  - Inno Setup - https://jrsoftware.org/isinfo.php
rem  - MSYS2 - https://www.msys2.org/

rem This runs appdetails.py and captures the output
for /F "tokens=*" %%a in ('python .\app\appdetails.py --name') do SET APPNAME=%%a
for /F "tokens=*" %%a in ('python .\app\appdetails.py --version') do SET APPVERSION=%%a
for /F "tokens=*" %%a in ('python .\app\appdetails.py --description') do SET APPDESCRIPTION=%%a
for /F "tokens=*" %%a in ('python .\app\appdetails.py --author') do SET APPAUTHOR=%%a
for /F "tokens=*" %%a in ('python -c "import xmlschema; import os; print(os.path.dirname(xmlschema.__file__))"') do  SET XMLSCHEMAPATH=%%a

echo Building installer for %APPNAME% %APPVERSION%

rem Make a copy of xmlschema resourses so they can be included in installer
rem Note that robocopy uses an exit code of 1 to indicate that at least 1 file
rem was copied
set XMLSCHEMACOPY=.\build\xmlschema
if exist %XMLSCHEMACOPY%\ rmdir %XMLSCHEMACOPY% /s /q
robocopy "%XMLSCHEMAPATH%" %XMLSCHEMACOPY% *.xsd /s
if %ERRORLEVEL% NEQ 1 exit /b 1

rem Package up MSYS2 so libcairo can be included in the installer
set MSYS2COPY=.\build\msys64
if exist %MSYS2COPY%\ rmdir %MSYS2COPY% /s /q
python ./scripts/packagemsys2.py %MSYS2COPY%
if %ERRORLEVEL% NEQ 0 exit /b 1

set APPVERSIONFILE=.\build\app_version.txt
python ./scripts/createversionfile.py "%APPNAME%" "%APPVERSION%" "%APPDESCRIPTION%" "%APPAUTHOR%" "%APPVERSIONFILE%"
if %ERRORLEVEL% NEQ 0 exit /b 1

rem Disable the dependency check in depscheck.py while pyinstaller is running.
rem This is needed as it looks like it does some kind of import of the source
rem code to find dependencies. Due to the hacky way my dependency checking code
rem works it gets run during this import and fails because it looks like not all
rem libraries can be found at that point in time.
set AUTOJIMMY_NO_DEPENDENCIES_CHECK=1

pyinstaller -w autojimmy.py -n %APPNAME% --icon ".\icons\autojimmy.ico" --version-file %APPVERSIONFILE% --add-data "data;data" --add-data "icons;icons" --add-data "licenses;licenses" --add-data "%XMLSCHEMACOPY%;xmlschema" --add-data "%MSYS2COPY%;msys64" --clean --noconfirm
if %ERRORLEVEL% NEQ 0 exit /b 1

iscc installer.iss /DApplicationName=%APPNAME% /DApplicationVersion=%APPVERSION%
if %ERRORLEVEL% NEQ 0 exit /b 1