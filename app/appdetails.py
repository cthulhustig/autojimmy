import argparse

AppName = 'Auto-Jimmy'
AppVersion = '0.9.2'
AppDescription = 'Referee and Player aid for the Traveller RPG'
AppURL = 'https://github.com/cthulhustig/autojimmy'
AppAuthor = 'CthulhuStig'

# This is a hack so that the script that builds the installer can call this to get the current
# application version number
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Optional app description')
    parser.add_argument('--name', action='store_true', help='Print application name')
    parser.add_argument('--version', action='store_true', help='Print application version')
    parser.add_argument('--description', action='store_true', help='Print application description')
    parser.add_argument('--url', action='store_true', help='Print application url')
    parser.add_argument('--author', action='store_true', help='Print application author')
    args = parser.parse_args()
    if args.name:
        print(AppName)
    if args.version:
        print(AppVersion)
    if args.description:
        print(AppDescription)
    if args.url:
        print(AppURL)
    if args.author:
        print(AppAuthor)
