@echo off
rem  Building the installer requires the following to be installed and added to the path
rem  - PyInstaller - https://pyinstaller.org
rem  - Inno Setup - https://jrsoftware.org/isinfo.php

rem This runs appdetails.py and captures the output 
for /F "tokens=*" %%a in ('.\app\appdetails.py --name') do SET APPNAME=%%a
for /F "tokens=*" %%a in ('.\app\appdetails.py --version') do SET APPVERSION=%%a
for /F "tokens=*" %%a in ('python -c "import xmlschema; import os; print(os.path.dirname(xmlschema.__file__))"') do  SET XMLSCHEMAPATH=%%a

echo Building installer for %APPNAME% %APPVERSION%

rem Make a copy of xmlschema resourses so they can be included in installer
set XMLSCHEMACOPY=".\build\xmlschema"
rmdir ".\build\xmlschema" /s /q
robocopy "%XMLSCHEMAPATH%" "%XMLSCHEMACOPY%" *.xsd /s

pyinstaller -w autojimmy.py -n %APPNAME% --icon ".\icons\autojimmy.ico" --add-data "data;data" --add-data "icons;icons" --add-data "licenses;licenses" --add-data "%XMLSCHEMACOPY%;xmlschema" --clean --noconfirm
iscc installer.iss /DApplicationName=%APPNAME% /DApplicationVersion=%APPVERSION%