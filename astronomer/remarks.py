import astronomer
import logging
import re
import typing

class Remarks(object):
    # Most of these are based on the descriptions here https://travellermap.com/doc/secondsurvey
    # with the exception of Colony which I found here https://wiki.travellerrpg.com/Trade_classification
    _TradeCodePattern = re.compile(r'^([A-Za-z]{2})$') # Argument gives trade code
    _MilitaryRulePattern = re.compile(r'^Mr\((\S{4})\)$') # Argument gives the controlling allegiance short code
    _ResearchStationPattern = re.compile(r'^Rs([ABGDEZHIO]?)$') # Argument gives grade of research station
    _OwnershipPattern = re.compile(r'^O:(?:(\S{4})-)?(\d{4})$') # Argument gives the owning world
    _ColonyPattern = re.compile(r'^C:(?:(\S{4})-)?(\d{4})$') # Argument gives the colony world
    _SophontMajorRacePattern = re.compile(r'^\[(.*)\]$') # Argument gives major sophont
    _SophontMinorRacePattern = re.compile(r'^\((.*)\)([0-9W]?)$') # Argument gives minor sophont with optional percentage
    _SophontDiebackWorldPattern = re.compile(r'^Di\((.+)\)$') # Argument gives previously inhabiting sophont
    _SophontShortCodePattern = re.compile(r'^(\S{4})([0-9W])$') # Argument gives sophont short code with optional percentage

    # Default to Gamma as per Traveller Map FromResearchCode. This is
    # used when the world just has the trade code 'Rs' with no level
    # character
    _DefaultResearchStation = 'G'

    def __init__(
            self,
            string: str,
            sectorName: str,
            zone: astronomer.ZoneType,
            sophontNames: typing.Mapping[str, str] # Maps sophont code to sophont name
            ) -> None:
        self._string = string
        self._tokenSet: typing.Set[str] = set()
        self._sectorName = sectorName
        self._zone = zone
        self._sophontNames = dict(sophontNames)
        self._tradeCodes: typing.Set[astronomer.TradeCode] = set()
        self._isMajorHomeworld = False
        self._isMinorHomeworld = False
        self._sophontPercentages: typing.Dict[str, int] = dict()
        self._diebackSophonts: typing.List[str] = list()
        self._owningWorld = None
        self._colonyWorlds = []
        self._rulingAllegiance = None
        self._researchStation = None

        self._parseRemarks()

        # Add custom trade codes for red/amber zone as it simplifies the
        # trade calculation logic as it can just deal with trade codes and
        # doesn't need to understand zones
        # TODO: I probably want to undo this hack before interactive editing
        # is added. I don't want the zone to be written to the database in the
        # remarks as it'd duplication of information. I also don't want to
        # be presenting them to the user as trade codes as they aren't. It might
        # make sense to do it now so I don't forget
        if self._zone == astronomer.ZoneType.AmberZone:
            self._tradeCodes.add(astronomer.TradeCode.AmberZone)
        elif self._zone == astronomer.ZoneType.RedZone:
            self._tradeCodes.add(astronomer.TradeCode.RedZone)

    def string(self) -> str:
        return self._string

    def isEmpty(self) -> bool:
        return not self._string

    def hasRemark(self, remark: str) -> bool:
        return remark in self._tokenSet

    def tradeCodes(self) -> typing.Iterable[astronomer.TradeCode]:
        return self._tradeCodes

    def hasTradeCode(
            self,
            tradeCode: astronomer.TradeCode
            ) -> bool:
        return tradeCode in self._tradeCodes

    def sophonts(self) -> typing.Iterable[str]:
        return self._sophontPercentages.keys()

    def hasSophont(
            self,
            sophont: str
            ) -> bool:
        return sophont in self._sophontPercentages

    def isMajorHomeworld(self) -> bool:
        return self._isMajorHomeworld

    def isMinorHomeworld(self) -> bool:
        return self._isMinorHomeworld

    def sophontPercentage(
            self,
            sophont: str
            ) -> int:
        if sophont not in self._sophontPercentages:
            return 0
        return self._sophontPercentages[sophont]

    def hasDiebackSophonts(self) -> bool:
        return len(self._diebackSophonts) > 0

    def diebackSophonts(self) -> typing.Iterable[str]:
        return self._diebackSophonts

    def hasOwner(self) -> bool:
        return self._owningWorld != None

    def ownerSectorHex(self) -> typing.Optional[str]:
        return self._owningWorld

    def hasColony(self) -> bool:
        return len(self._colonyWorlds) > 0

    def colonyCount(self) -> int:
        return len(self._colonyWorlds)

    def colonySectorHexes(self) -> typing.Iterable[str]:
        return self._colonyWorlds

    def rulingAllegiance(self) -> typing.Optional[str]:
        return self._rulingAllegiance

    """
    Research Stations:
    'A' == Alpha
    'B' == Beta
    'G' == Gamma
    'D' == Delta
    'E' == Epsilon
    'Z' == Zeta
    'H' == Eta
    'T' == Theta
    'O' == Omicron
    """

    def researchStation(self) -> typing.Optional[str]:
        return self._researchStation

    def _parseRemarks(self) -> None:
        if not self._string:
            return

        tokens = self._tokeniseRemarks()
        for remark in tokens:
            self._tokenSet.add(remark)

            result = self._TradeCodePattern.match(remark)
            if result:
                tradeCodeGlyph = result.group(1)
                tradeCode = astronomer.tradeCode(tradeCodeGlyph)
                if not tradeCode:
                    # Only log this at debug as it can happen a lot in some sectors
                    logging.debug(f'Ignoring unknown Trade Code glyph "{tradeCodeGlyph}"')
                    continue
                self._tradeCodes.add(tradeCode)

                if tradeCode == astronomer.TradeCode.ResearchStation:
                    self._researchStation = Remarks._DefaultResearchStation
                continue

            result = self._MilitaryRulePattern.match(remark)
            if result:
                self._tradeCodes.add(astronomer.TradeCode.MilitaryRule)

                allegiance = result.group(1)
                if allegiance:
                    self._rulingAllegiance = allegiance
                continue

            result = self._ResearchStationPattern.match(remark)
            if result:
                self._researchStation = result.group(1)
                if not self._researchStation:
                    self._researchStation = Remarks._DefaultResearchStation

                self._tradeCodes.add(astronomer.TradeCode.ResearchStation)
                continue

            result = self._OwnershipPattern.match(remark)
            if result:
                # This indicates the world is owned by a world elsewhere
                sector = result.group(1)
                if not sector:
                    # Empty string means current sector
                    sector = self._sectorName

                hex = result.group(2) # Hex in sector coordinates

                assert(not self._owningWorld) # Should only have one owning world
                self._owningWorld = f'{sector} {hex}'
                continue

            result = self._ColonyPattern.match(remark)
            if result:
                # This indicates this world has a colony elsewhere
                sector = result.group(1)
                if not sector:
                    # Empty string means current sector
                    sector = self._sectorName

                hex = result.group(2) # Hex in sector coordinates

                self._colonyWorlds.append(f'{sector} {hex}')
                continue

            result = self._SophontMajorRacePattern.match(remark)
            if result:
                sophontName = result.group(1)
                self._sophontPercentages[sophontName] = 100
                self._isMajorHomeworld = True
                continue

            result = self._SophontMinorRacePattern.match(remark)
            if result:
                sophontName = result.group(1)
                sophontPercentageCode = result.group(2)
                sophontPercentage = 100 if sophontPercentageCode == '' or sophontPercentageCode == 'W' else (int(sophontPercentageCode) * 10)
                self._sophontPercentages[sophontName] = sophontPercentage
                self._isMinorHomeworld = True
                continue

            result = self._SophontDiebackWorldPattern.match(remark)
            if result:
                self._tradeCodes.add(astronomer.TradeCode.DieBackWorld)

                sophont = result.group(1)
                if sophont:
                    self._diebackSophonts.append(sophont)
                continue

            result = self._SophontShortCodePattern.match(remark)
            if result:
                sophontShortCode = result.group(1)
                sophontPercentageCode = result.group(2)
                sophontPercentage = 100 if sophontPercentageCode == '' or sophontPercentageCode == 'W' else (int(sophontPercentageCode) * 10)

                sophontName = self._sophontNames.get(sophontShortCode)
                if not sophontName:
                    # Just use the short code for the name. In theory this shouldn't happen
                    # as the sophont entries should have been created in the database for
                    # every sophont code used
                    sophontName = sophontShortCode

                self._sophontPercentages[sophontName] = sophontPercentage
                continue

            # This is logged at a low log level as only a subset of remarks are parsed
            logging.debug(f'Ignoring unknown remark "{remark}"')

    # This function returns a list rather than storing tokens in _tokenSet so that the tokens will
    # be processed in the order they're written
    def _tokeniseRemarks(self) -> typing.Iterable[str]:
        tokens = []
        remark = None
        bracketNesting = 0
        for char in self._string:
            if bracketNesting > 0:
                # We're processing bracketed data so just add the character to the current remark no
                # mater what it is
                assert(remark != None)
                remark += char
            elif char.isspace() or char == ',':
                # We've hit the end of the current remark if there is one in progress, most remark data
                # is white space separated but a small number of Traveller Map worlds have comma
                # separated trade codes
                if remark != None:
                    tokens.append(remark)
                    remark = None
            else:
                if remark != None:
                    # We're processing a remark so just add the current character to it
                    remark += char
                else:
                    # We're not processing a remark so start a new one
                    remark = char

            # Check for begin/end of bracketed data. Note this parsing is really noddy, no attempt
            # is made to validate closing bracket types match opening bracket types and there is no
            # support for nested brackets
            if char == '[' or char == '(' or char == '{':
                bracketNesting += 1
            elif char == ']' or char == ')' or char == '}':
                assert(bracketNesting)
                bracketNesting -= 1

        if remark != None:
            # Add the in progress remark to the array
            tokens.append(remark)

        return tokens
