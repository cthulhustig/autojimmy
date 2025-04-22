import datetime
import packaging.version
import sys

_Template = \
"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {build}, 0),
    prodvers=({major}, {minor}, {build}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x4,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',  # Language + code page (en-US + Unicode)
        [
          StringStruct('CompanyName', '{author}'),
          StringStruct('FileDescription', '{description}'),
          StringStruct('FileVersion', '{major}.{minor}.{build}'),
          StringStruct('InternalName', '{app}'),
          StringStruct('LegalCopyright', '© {year} {author}'),
          StringStruct('OriginalFilename', '{app}.exe'),
          StringStruct('ProductName', '{app}'),
          StringStruct('ProductVersion', '{major}.{minor}.{build}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

if __name__ == "__main__":
    print('Creating version file')

    appName = sys.argv[1]
    appDescription = sys.argv[2]
    appVersion = sys.argv[3]
    appAuthor = sys.argv[4]
    outputFile = sys.argv[5]

    try:
        appVersion = packaging.version.Version(appVersion)
    except Exception as ex:
        print('Failed to parse version number')
        exit(1)

    try:
        with open(outputFile, 'w', encoding='UTF8') as file:
            file.write(_Template.format(
                app=appName,
                description=appDescription,
                major=appVersion.major,
                minor=appVersion.minor,
                build=appVersion.micro,
                author=appAuthor,
                year=datetime.datetime.now().year))
    except Exception as ex:
        print('Failed to write version file')
        exit(1)

    exit(0)