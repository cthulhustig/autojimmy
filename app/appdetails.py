import argparse

AppName = 'Auto-Jimmy'
AppVersion = '0.9.2'
AppURL = 'https://github.com/cthulhustig/autojimmy'

# This is a hack so that the script that builds the installer can call this to get the current
# application version number
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Optional app description')
    parser.add_argument('--name', action='store_true', help='Print application name')
    parser.add_argument('--version', action='store_true', help='Print application version')
    args = parser.parse_args()
    if args.name:
        print(AppName)
    if args.version:
        print(AppVersion)
