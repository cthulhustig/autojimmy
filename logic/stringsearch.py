import astronomer
import fnmatch
import re
import typing

# The world search pattern matches a search string with the format of
# a world name followed by its subsector in brackets. Both the world name
# and subsector name are extracted
_WorldSearchPattern = re.compile(r'^(.+)\s+\(\s*(.+)\s*\)$')

def _findSectorWorlds(
        universe: astronomer.Universe,
        milieu: astronomer.Milieu,
        searchString: str,
        matches: typing.Optional[typing.Set[astronomer.World]] = None,
        worldFilter: typing.Optional[typing.Callable[[astronomer.World], bool]] = None
        ) -> typing.Set[astronomer.World]:
    if matches is None:
        matches: typing.Set[astronomer.World] = set()

    searchString = searchString.strip()
    if not searchString:
        return matches

    if searchString[-1:] != '*':
        # Try to mimic the behaviour of Traveller Map where just typing the start of a name
        # will match the without needing to specify wild cards.
        searchString += '*'
    expression = re.compile(
        fnmatch.translate(searchString),
        re.IGNORECASE)

    for sector in universe.yieldSectors(milieu=milieu):
        isMatch = expression.match(sector.name())

        if not isMatch:
            alternateNames = sector.alternateNames()
            if alternateNames:
                for alternateName in alternateNames:
                    if expression.match(alternateName):
                        isMatch = True
                        break
        if isMatch:
            matches.update(sector.worlds(filterCallback=worldFilter))

    return matches

def _findSubsectorWorlds(
        universe: astronomer.Universe,
        milieu: astronomer.Milieu,
        searchString: str,
        matches: typing.Optional[typing.Set[astronomer.World]] = None,
        worldFilter: typing.Optional[typing.Callable[[astronomer.World], bool]] = None
        ) -> typing.Set[astronomer.World]:
    if matches is None:
        matches: typing.Set[astronomer.World] = set()

    searchString = searchString.strip()
    if not searchString:
        return

    if searchString[-1:] != '*':
        # Try to mimic the behaviour of Traveller Map where just typing the start of a name
        # will match the without needing to specify wild cards.
        searchString += '*'
    expression = re.compile(
        fnmatch.translate(searchString),
        re.IGNORECASE)

    for sector in universe.yieldSectors(milieu=milieu):
        for subsectorName in sector.yieldSubsectorNames():
            if expression.match(subsectorName):
                subsectorCode = sector.subsectorCodeByName(name=subsectorName)
                if subsectorCode:
                    matches.update(sector.worlds(subsectorCode=subsectorCode, filterCallback=worldFilter))

    return matches

def _findHintWorlds(
        universe: astronomer.Universe,
        milieu: astronomer.Milieu,
        hintString: str,
        matches: typing.Optional[typing.Set[astronomer.World]] = None,
        worldFilter: typing.Optional[typing.Callable[[astronomer.World], bool]] = None
        ) -> None:
    matches = _findSectorWorlds(
        universe=universe,
        milieu=milieu,
        searchString=hintString,
        matches=matches,
        worldFilter=worldFilter)
    matches = _findSubsectorWorlds(
        universe=universe,
        milieu=milieu,
        searchString=hintString,
        matches=matches,
        worldFilter=worldFilter)
    return matches

def _createWorldFilter(
        searchString: str,
        seenWorlds: typing.Set[astronomer.World]
        ) -> typing.Callable[[astronomer.World], bool]:
    if searchString[-1:] != '*':
        # Try to mimic the behaviour of Traveller Map where just typing the start of a name
        # will match the without needing to specify wild cards.
        searchString += '*'
    expression = re.compile(
        fnmatch.translate(searchString),
        re.IGNORECASE)
    worldFilter: typing.Callable[[astronomer.World], bool] = \
        lambda world: (world not in seenWorlds) and expression.match(world.name())
    return worldFilter

def _sortResults(
        universe: astronomer.Universe,
        milieu: astronomer.Milieu,
        worlds: typing.Iterable[astronomer.World]
        ) -> typing.List[astronomer.World]:
    worldKeyMap: typing.Dict[astronomer.World, str] = {}
    for world in worlds:
        hex = world.hex()
        sector = universe.sectorByPosition(milieu=milieu, position=hex)
        if not sector:
            continue

        subsectorName = sector.subsectorName(code=hex.subsectorCode())
        if not subsectorName:
            subsectorName = hex.subsectorCode()

        worldKeyMap[world] = f'{world.name()}/{subsectorName}/{sector.name()}'.casefold()

    return sorted(worldKeyMap.keys(), key=lambda world: worldKeyMap[world])

def searchForWorlds(
        universe: astronomer.Universe,
        milieu: astronomer.Milieu,
        searchString: str
        ) -> typing.List[astronomer.World]:
    searchString = searchString.strip()
    if not searchString:
        # No matches if search string is empty after white space stripped
        return []

    # Check if the world string specifies a hex, if it does and there is
    # a world at that location then that is our only result
    try:
        hex = universe.stringToPosition(milieu=milieu, string=searchString)
        foundWorld = universe.worldByPosition(milieu=milieu, hex=hex)
        if foundWorld:
            return [foundWorld]
    except:
        pass

    seenWorlds: typing.Set[astronomer.World] = set()

    searchWorlds: typing.Optional[typing.Iterable[astronomer.World]] = None
    result = _WorldSearchPattern.match(searchString)
    if result:
        # We've matched the sector search hint pattern so check to see if the hint is actually
        # a known sector. If it is then perform the search with just the world portion of the
        # search string and filter the results afterwards. If it's not a known sector then just
        # perform the search with the full search string as normal
        worldString = result.group(1)
        hintString = result.group(2)

        worldFilter = _createWorldFilter(
            searchString=worldString,
            seenWorlds=seenWorlds)
        searchWorlds = _findHintWorlds(
            universe=universe,
            milieu=milieu,
            hintString=hintString,
            worldFilter=worldFilter)

    if not searchWorlds:
        # Search the worlds in all sectors. This will happen if no sector/subsector is specified
        # _or_ if the specified sector/subsector is unknown
        worldFilter = _createWorldFilter(
            searchString=searchString,
            seenWorlds=seenWorlds)
        searchWorlds = universe.yieldWorlds(
            milieu=milieu,
            filterCallback=worldFilter)

    matches = _sortResults(universe=universe, milieu=milieu, worlds=searchWorlds)
    seenWorlds.update(searchWorlds)

    # From now on we're nto filtering worlds by name, just if they've been seen before
    worldFilter = lambda world: world not in seenWorlds

    # If the search string matches any sub sectors add any worlds that
    # we've not already seen. Ordering of this relative to sectors
    # matches is important as sub sectors are more specific so matches
    # should be listed first in results
    searchWorlds = _findSubsectorWorlds(
        universe=universe,
        milieu=milieu,
        searchString=searchString,
        worldFilter=worldFilter)
    matches.extend(_sortResults(universe=universe, milieu=milieu, worlds=searchWorlds))
    seenWorlds.update(searchWorlds)

    # If the search string matches any sectors add any worlds that
    # we've not already seen
    searchWorlds = _findSectorWorlds(
        universe=universe,
        milieu=milieu,
        searchString=searchString,
        worldFilter=worldFilter)
    matches.extend(_sortResults(universe=universe, milieu=milieu, worlds=searchWorlds))
    seenWorlds.update(searchWorlds)

    return matches
