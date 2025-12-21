import re
import typing

# Most of these are based on the descriptions here https://travellermap.com/doc/secondsurvey
# with the exception of Colony which I found here https://wiki.travellerrpg.com/Trade_classification

# All Trade codes
_TradeCodePattern = re.compile(r'^(Ag|As|Ba|De|Fl|Ga|Hi|Ht|Ic|In|Lo|Lt|Na|Ni|Po|Ri|Va|Wa|Az|Rz|Co|Fr|Ho|Tr|Tu|Pa|Pi|Pr|He|Lk|Oc|Tz|Cp|Cs|Cx|Cy|Di|Ph|Fa|Mi|Mr|Pe|Px|Re|Ab|An|Ax|Da|Fo|Pz|Rs|Sa|Xb)$') # Argument gives trade code

# Military Rule - "Mr(XXXX)" where XXXX is controlling allegiance short code
_MilitaryRulePattern = re.compile(r'^Mr\(\s*(\S{4})\s*\)$')

# Research Station - "RsX" where X is optional grade of station
# I believe the optional character references the specific research stations described
# on this wiki page rather than being a more generic grade or something similar that
# could be applied to multiple research stations in different locations (i.e. there
# should only ever by one station with each letter in the entire universe).
# However, there is nothing to prevent a user entering multiple different RsX entries
# in a remark string (or even multiple of the same) so this code handles it and
# exposes all instances
# https://wiki.travellerrpg.com/Imperial_Research_Station
# 'A' == Alpha
# 'B' == Beta
# 'G' == Gamma
# 'D' == Delta
# 'E' == Epsilon
# 'Z' == Zeta
# 'H' == Eta
# 'T' == Theta
# 'O' == Omicron
_ResearchStationPattern = re.compile(r'^Rs([ABGDEZHTO]?)$')

# Owning System: "O:####" or "O:XXXX-####" where XXXX is the system abbreviation or current
# system if not specified and #### is the hex in sector coordinates. The range of hex values
# is restricted to 1-32 on the X axis and 1-40 on they Y axis.
# By the documentation, the '-' separator between the abbreviation and hex is mandatory but
# NOTE: I've made it optional as it's not really needed as a separator, as the things it's
# separating are a fixed length, and there is at least one place that uses it (Yaweakhea'e
# in M1105 Khaeaw).
# NOTE: I've used \S (any non space) for the abbreviation rather than \w (alphanumeric or
# underscore) as there are uses of non-alphanumeric characters in other codes (e.g. Sophont
# Populations) and I want to be consistent
_OwnershipPattern = re.compile(r'^O:(?:(\S{4})-?)?(0[1-9]|[12][0-9]|3[0-2])(0[1-9]|[1-3][0-9]|40)$')

# Colony System: "C:####" or "C:XXXX-####" where XXXX is the system abbreviation or current
# system if not specified and #### is the hex in sector coordinates. The range of hex values
# is restricted to 1-32 on the X axis and 1-40 on they Y axis.
# NOTE: As with the ownership pattern, I've made the '-' separator optional
# NOTE: I've used \S (any non space) for the abbreviation rather than \w (alphanumeric or
# underscore) as there are uses of non-alphanumeric characters in other codes (e.g. Sophont
# Populations) and I want to be consistent
_ColonyPattern = re.compile(r'^C:(?:(\S{4})-?)?(0[1-9]|[12][0-9]|3[0-2])(0[1-9]|[1-3][0-9]|40)$')

# TODO: In the Traveller Map data there are quite a few places that use ? as the population
# when specifying major/minor home worlds and T5/Legacy populations. I assume this is to
# indicate that the sophont is present but the population isn't known (which seems like a
# very valid state). Ideally I should probably support this but it would need to be the
# whole way through (database, astronomer etc). I'd also need a new way to represent die back
# sophonts in the database as currently they're a sophont population with a null value.

# Major Race Home World: "[NAME]" or "[NAME]#" where NAME is the sophont name and # is
# the optional population percentage in 10 percent intervals. If no population is
# specified it is taken to be 100%
# NOTE: The second survey spec only has the population percentage for minor home worlds
# but it seems odd to assume the home world is always 100%
_SophontMajorRacePattern = re.compile(r'^\[\s*(?=\S)(.+?)\s*\]([0-9W]?)$')

# Minor Race Home World: "(NAME)" or "(NAME)#" where NAME is the sophont name and # is
# the optional population percentage in 10 percent intervals. If no population is
# specified it is taken to be 100%
_SophontMinorRacePattern = re.compile(r'^\(\s*(?=\S)(.+?)\s*\)([0-9W]?)$')

# T5 Sophont Population: "CODE#" where CODE is the sophont code and # is the population
# percentage in 10 precent intervals or W if 100%
# NOTE: I support an optional : separator between the code and population. It's
# not part of the of the second survey spec but some sector files do use it.
# NOTE: I've used \S (anything that's not a space) for the code (rather than \w) as
# there are some uses of none alphabetic characters (notably Za'tW in M1105 Wrenton)
_T5SophontPopulationPattern = re.compile(r'^(\S{4}):?([0-9W])$')

# Legacy Sophont Populations: "X:#" where X is one of the legacy single letter sophont
# codes and # is the population percentage in 10 percent intervals or w if 100%
_LegacySophontPopulationPattern = re.compile(r'^([ACDFHIMVXZ]):?([0-9w])$')

# Die Back Sophont: "Di(NAME)" where NAME is the sophont name
_SophontDieBackWorldPattern = re.compile(r'^Di\(\s*(?=\S)(.+?)\s*\)$')

# This function returns a list rather than storing tokens in _tokenSet so that the tokens will
# be processed in the order they're written
def _tokeniseRemarks(string: str) -> typing.Generator[str, None, None]:
    remark = None
    bracketNesting = 0
    for char in string:
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
                yield remark
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
        yield remark

def parseSystemRemarksString(
        string: str
        ) -> typing.Tuple[
            typing.List[str], # Trade Codes
            typing.List[typing.Tuple[ # Major Race Home World
                str, # Sophont Name
                int # Population Percentage
                ]],
            typing.List[typing.Tuple[ # Minor Race Home World
                str, # Sophont Name
                int # Population Percentage
                ]],
            typing.List[typing.Tuple[ # Sophont Populations
                str, # Sophont Code
                int # Population Percentage
                ]],
            typing.List[str], # Die back Sophont Names
            typing.List[typing.Tuple[ # Owning Systems
                int, # Hex X in sector coordinates
                int, # Hex Y in sector coordinates
                typing.Optional[str] # Sector Abbreviation or None if Current Sector
            ]],
            typing.List[typing.Tuple[ # Colony Systems
                int, # Hex X in sector coordinates
                int, # Hex Y in sector coordinates
                typing.Optional[str] # Sector Abbreviation or None if Current Sector
            ]],
            typing.List[str], # Ruling Allegiance Codes
            typing.List[str], # Research Stations Codes
            typing.List[str] # Unrecognised Remarks
        ]:
    if not string:
        return

    tradeCodes: typing.List[str] = []
    majorHomeWorlds: typing.List[typing.Tuple[
        str,
        int # Population percentage
        ]] = []
    minorHomeWorlds: typing.List[typing.Tuple[
        str,
        int # Population percentage
        ]] = []
    sophontPopulations: typing.List[typing.Tuple[
        str, # Code
        int, # Population percentage
        ]] = []
    dieBackSophonts: typing.List[str] = []
    owningSystems: typing.List[typing.Tuple[
        int, # Hex X in sector coordinates
        int, # Hex Y in sector coordinates
        typing.Optional[str] # Sector Abbreviation or None if Current Sector
        ]] = []
    colonySystems: typing.List[typing.Tuple[
        int, # Hex X in sector coordinates
        int, # Hex Y in sector coordinates
        typing.Optional[str] # Sector Abbreviation or None if Current Sector
        ]] = []
    rulingAllegiances: typing.List[str] = []
    researchStations: typing.List[str] = []
    unrecognisedRemarks: typing.List[str] = []
    for remark in _tokeniseRemarks(string):
        result = _TradeCodePattern.match(remark)
        if result:
            tradeCodes.append(result.group(1))
            continue

        result = _SophontMajorRacePattern.match(remark)
        if result:
            name = result.group(1)
            population = result.group(2)
            population = 100 if not population or population == 'W' else (int(population) * 10)
            majorHomeWorlds.append((name, population))
            continue

        result = _SophontMinorRacePattern.match(remark)
        if result:
            name = result.group(1)
            population = result.group(2)
            population = 100 if not population or population == 'W' else (int(population) * 10)
            minorHomeWorlds.append((name, population))
            continue

        result = _T5SophontPopulationPattern.match(remark)
        if result:
            code = result.group(1)
            population = result.group(2)
            population = 100 if population == '' or population == 'W' else (int(population) * 10)
            sophontPopulations.append((code, population))
            continue

        result = _LegacySophontPopulationPattern.match(remark)
        if result:
            code = result.group(1)
            population = result.group(2)
            population = 100 if population == '' or population == 'w' else (int(population) * 10)
            sophontPopulations.append((code, population))
            continue

        result = _SophontDieBackWorldPattern.match(remark)
        if result:
            dieBackSophonts.append(result.group(1))

            if 'Di' not in tradeCodes:
                tradeCodes.append('Di')
            continue

        result = _OwnershipPattern.match(remark)
        if result:
            # This indicates the world is owned by a world elsewhere
            sector = result.group(1) # Null if current sector
            hexX = int(result.group(2)) # Hex X in sector coordinates
            hexY = int(result.group(3)) # Hex Y in sector coordinates
            owningSystems.append((hexX, hexY, sector))
            continue

        result = _ColonyPattern.match(remark)
        if result:
            # This indicates this world has a colony elsewhere
            sector = result.group(1) # Null if current sector
            hexX = int(result.group(2)) # Hex X in sector coordinates
            hexY = int(result.group(3)) # Hex Y in sector coordinates
            colonySystems.append((hexX, hexY, sector))
            continue

        result = _MilitaryRulePattern.match(remark)
        if result:
            rulingAllegiances.append(result.group(1))

            if 'Mr' not in tradeCodes:
                tradeCodes.append('Mr')
            continue

        result = _ResearchStationPattern.match(remark)
        if result:
            researchStation = result.group(1)
            if researchStation:
                researchStations.append(researchStation)

            if 'Rs' not in tradeCodes:
                tradeCodes.append('Rs')
            continue

        unrecognisedRemarks.append(remark)

    return (
        tradeCodes,
        majorHomeWorlds,
        minorHomeWorlds,
        sophontPopulations,
        dieBackSophonts,
        owningSystems,
        colonySystems,
        rulingAllegiances,
        researchStations,
        unrecognisedRemarks)

def formatSystemRemarksString(
        tradeCodes: typing.Optional[typing.Collection[str]],
        majorRaceHomeWorlds: typing.Optional[typing.Collection[typing.Tuple[
            str, # Sophont Name
            int # Population Percentage
            ]]] = None,
        minorRaceHomeWorlds: typing.Optional[typing.Collection[typing.Tuple[
            str, # Sophont Name
            int # Population Percentage
            ]]] = None,
        sophontPopulations: typing.Optional[typing.Collection[typing.Tuple[
            str, # Sophont Code
            int # Population Percentage
            ]]] = None,
        dieBackSophonts: typing.Optional[typing.Collection[str]] = None,
        owningSystems: typing.Optional[typing.Collection[typing.Tuple[
            int, # Hex X in sector coordinates
            int, # Hex Y in sector coordinates
            typing.Optional[str] # Sector Abbreviation or None if Current Sector
        ]]] = None,
        colonySystems: typing.Optional[typing.Collection[typing.Tuple[
            int, # Hex X in sector coordinates
            int, # Hex Y in sector coordinates
            typing.Optional[str] # Sector Abbreviation or None if Current Sector
        ]]] = None,
        rulingAllegiances: typing.Optional[typing.Collection[str]] = None,
        researchStations: typing.Optional[typing.Collection[str]] = None,
        customRemarks: typing.Optional[typing.Collection[str]] = None
        ) -> str:
    remarks = []

    if tradeCodes:
        for tradeCode in tradeCodes:
            # No need to put out military rule, research station or die back
            # trade codes if there are ruling allegiance codes, research
            # station codes or die back sophonts supplied as they imply the
            # trade code
            if tradeCode == 'Mr' and rulingAllegiances:
                continue
            if tradeCode == 'Rs' and researchStations:
                continue
            if tradeCode == 'Di' and dieBackSophonts:
                continue
            remarks.append(tradeCode)

    if majorRaceHomeWorlds:
        for sophont, percentage in majorRaceHomeWorlds:
            percentage //= 10
            remarks.append('[{sophont}]{percentage}'.format(
                sophont=sophont,
                percentage=percentage if percentage < 10 else ''))

    if minorRaceHomeWorlds:
        for sophont, percentage in minorRaceHomeWorlds:
            percentage //= 10
            remarks.append('({sophont}){percentage}'.format(
                sophont=sophont,
                percentage=percentage if percentage < 10 else ''))

    if sophontPopulations:
        for sophont, percentage in sophontPopulations:
            percentage //= 10
            remarks.append('{sophont}{percentage}'.format(
                sophont=sophont,
                percentage=percentage if percentage < 10 else 'W'))

    if dieBackSophonts:
        for sophont in dieBackSophonts:
            remarks.append('Di({sophont})'.format(sophont=sophont))

    if owningSystems:
        for hexX, hexY, sector in owningSystems:
            if sector:
                # TODO: Check this formatting is correct
                remarks.append('O:{x:02d}{y:02d}-{sector}'.format(
                    x=hexX,
                    y=hexY,
                    sector=sector))
            else:
                remarks.append('O:{x:02d}{y:02d}'.format(
                    x=hexX,
                    y=hexY))

    if colonySystems:
        for hexX, hexY, sector in colonySystems:
            if sector:
                # TODO: Check this formatting is correct
                remarks.append('C:{x:02d}{y:02d}-{sector}'.format(
                    x=hexX,
                    y=hexY,
                    sector=sector))
            else:
                remarks.append('C:{x:02d}{y:02d}'.format(
                    x=hexX,
                    y=hexY))

    if rulingAllegiances:
        for allegiance in rulingAllegiances:
            remarks.append('Mr({allegiance})'.format(
                allegiance=allegiance))

    if researchStations:
        for station in researchStations:
            remarks.append('Rs{station}'.format(
                station=station))

    if customRemarks:
        remarks.extend(customRemarks)

    return ' '.join(remarks)