import logging
import multiverse
import survey
import typing

_StockMajorSophonts = set([
    'Human',
    'Aslan',
    'Droyne',
    'Hiver',
    'K\'kree',
    'Vargr',
])

# This maps legacy single letter sophont codes to T5 sophont codes. There is no
# mapping for 'F' as I've no idea what T5 sophont it maps to
_LegacySophontMap = {
    'A': 'Asla',
    'C': 'Chir',
    'D': 'Droy',
    #'F': 'Non-Hiver Federation Member',
    'H': 'Hive',
    'I': 'Ithk',
    'M': 'Huma',
    'V': 'Varg',
    'X': 'Adda',
    'Z': 'Zhod'
}

class SophontMapper(object):
    def __init__(
            self,
            rawSectors: typing.List[typing.Tuple[survey.RawMetadata, typing.List[survey.RawWorld]]],
            rawStockSophonts: typing.List[survey.RawStockSophont],
            ) -> None:
        self._nameToDbSophont: typing.Dict[
            str, # Sophont Name
            multiverse.DbSophont
            ] = {}
        self._metadataToCodeMap: typing.Dict[
            typing.Optional[survey.RawMetadata], # None = global
            typing.Dict[
                str, # Sophont Code
                multiverse.DbSophont
            ]] = {}

        self._populate(
            rawSectors=rawSectors,
            rawStockSophonts=rawStockSophonts)

    def lookupSophontByName(self, name: str) -> typing.Optional[multiverse.DbSophont]:
        return self._nameToDbSophont.get(name)

    def lookupSophontByCode(
            self,
            rawMetadata: survey.RawMetadata,
            code: str
            ) -> typing.Optional[multiverse.DbSophont]:
        codeMap = self._metadataToCodeMap.get(rawMetadata)
        if codeMap is not None:
            dbSophont = codeMap.get(code)
            if dbSophont is not None:
                return dbSophont

        codeMap = self._metadataToCodeMap.get(None)
        if codeMap is not None:
            dbSophont = codeMap.get(code)
            if dbSophont is not None:
                return dbSophont

        return None

    def listSophonts(self) -> typing.List[multiverse.DbSophont]:
        return list(self._nameToDbSophont.values())

    def _populate(
            self,
            rawSectors: typing.List[typing.Tuple[survey.RawMetadata, typing.List[survey.RawWorld]]],
            rawStockSophonts: typing.List[survey.RawStockSophont],
            ) -> None:
        majorSophontNames = set(_StockMajorSophonts)
        usedSophontNames = set()
        usedSophontCodes = set()
        for rawSophont in rawStockSophonts:
            name = rawSophont.name()
            usedSophontNames.add(name)

            code = rawSophont.code()
            usedSophontCodes.add(code)

            location = rawSophont.location()
            if location == 'major':
                majorSophontNames.add(name)

        for _, rawWorlds in rawSectors:
            for rawWorld in rawWorlds:
                rawRemarks = rawWorld.remarks()
                if not rawRemarks:
                    continue

                if rawRemarks.sophontPopulations():
                    for rawPopulation in rawRemarks.sophontPopulations():
                        originalCode = rawPopulation.sophont()
                        usedSophontCodes.add(originalCode)

                        mappedCode = _LegacySophontMap.get(originalCode)
                        if mappedCode is not None:
                            usedSophontCodes.add(mappedCode)

                if rawRemarks.majorRaceHomeWorlds():
                    for rawPopulation in rawRemarks.majorRaceHomeWorlds():
                        name = rawPopulation.sophont()
                        majorSophontNames.add(name)
                        usedSophontNames.add(name)

                if rawRemarks.minorRaceHomeWorlds():
                    for rawPopulation in rawRemarks.minorRaceHomeWorlds():
                        name = rawPopulation.sophont()
                        usedSophontNames.add(name)

                if rawRemarks.dieBackSophonts():
                    for name in rawRemarks.dieBackSophonts():
                        usedSophontNames.add(name)


        globalCodeMap = self._metadataToCodeMap.get(None)
        if globalCodeMap is None:
            globalCodeMap = {}
            self._metadataToCodeMap[None] = globalCodeMap

        # NOTE: Although sophonts support a location string (in the same way as
        # allegiances), I don't use it as its format is not as consistent as
        # it is for allegiances
        for rawSophont in rawStockSophonts:
            name = rawSophont.name()
            code = rawSophont.code()

            dbSophontForName = self._nameToDbSophont.get(name)
            if dbSophontForName is None:
                dbSophontForName = multiverse.DbSophont(
                    name=name,
                    code=code,
                    isMajor=name in majorSophontNames)
                self._nameToDbSophont[name] = dbSophontForName

            globalCodeMap[code] = dbSophontForName

        for rawMetadata, rawWorlds in rawSectors:
            sectorCodeMap = self._metadataToCodeMap.get(rawMetadata)
            if sectorCodeMap is None:
                sectorCodeMap = {}
                self._metadataToCodeMap[rawMetadata] = sectorCodeMap

            for rawWorld in rawWorlds:
                rawRemarks = rawWorld.remarks()
                if rawRemarks is None:
                    continue

                if rawRemarks.sophontPopulations():
                    for rawPopulation in rawRemarks.sophontPopulations():
                        originalCode = rawPopulation.sophont()
                        mappedCode = _LegacySophontMap.get(originalCode, originalCode)

                        # When looking up the sector for whatever name the sophont code is mapped
                        # to, use the original name when checking the sector map, as we want to use
                        # the sophont this sector is referring to when it used that code, but, use
                        # the mapped name when checking the global map as we want the sophont for
                        # the mapped (no-legacy) code
                        dbSophontForName = sectorCodeMap.get(originalCode)
                        if dbSophontForName is None:
                            dbSophontForName = globalCodeMap.get(mappedCode)

                        if dbSophontForName is None:
                            # There is no existing sophont for this code so create one. The mapped
                            # code is used when creating the sophont as that's what we want to be
                            # used post conversion. Really we should never hit the case where a code
                            # has been mapped but there is no sophont for it as all the codes the
                            # legacy codes can be mapped to should be defined in the stock sophonts
                            # so that sophont should be used.
                            name = self._generateSophontName(
                                code=mappedCode,
                                usedNames=usedSophontNames)
                            dbSophontForName = multiverse.DbSophont(
                                name=name,
                                code=mappedCode,
                                isMajor=False)
                            self._nameToDbSophont[name] = dbSophontForName
                            globalCodeMap[mappedCode] = dbSophontForName
                            usedSophontNames.add(name)

                        # When updating the sector code map, use the original code as that is the code
                        # that the sector refers to the sophont by.
                        sectorCodeMap[originalCode] = dbSophontForName

                if rawRemarks.majorRaceHomeWorlds():
                    for rawPopulation in rawRemarks.majorRaceHomeWorlds():
                        name = rawPopulation.sophont()
                        dbSophontForName = self._nameToDbSophont.get(name)
                        if dbSophontForName is None:
                            code = SophontMapper._generateSophontCode(
                                name=name,
                                usedCodes=usedSophontCodes)
                            dbSophontForName = multiverse.DbSophont(
                                name=name,
                                code=code,
                                isMajor=True)
                            self._nameToDbSophont[name] = dbSophontForName
                            usedSophontCodes.add(code)

                if rawRemarks.minorRaceHomeWorlds():
                    for rawPopulation in rawRemarks.minorRaceHomeWorlds():
                        name = rawPopulation.sophont()
                        dbSophontForName = self._nameToDbSophont.get(name)
                        if dbSophontForName is None:
                            code = SophontMapper._generateSophontCode(
                                name=name,
                                usedCodes=usedSophontCodes)
                            dbSophontForName = multiverse.DbSophont(
                                name=name,
                                code=code,
                                isMajor=name in majorSophontNames)
                            self._nameToDbSophont[name] = dbSophontForName
                            usedSophontCodes.add(code)

                if rawRemarks.dieBackSophonts():
                    for name in rawRemarks.dieBackSophonts():
                        dbSophontForName = self._nameToDbSophont.get(name)
                        if dbSophontForName is None:
                            code = SophontMapper._generateSophontCode(
                                name=name,
                                usedCodes=usedSophontCodes)
                            dbSophontForName = multiverse.DbSophont(
                                name=name,
                                code=code,
                                isMajor=name in majorSophontNames)
                            self._nameToDbSophont[name] = dbSophontForName
                            usedSophontCodes.add(code)

    # This code generates a code for a sophont name following the rules defined on
    # the Traveller Wiki (at least as best as I can understand them)
    # https://wiki.travellerrpg.com/Sophont_Code
    @staticmethod
    def _generateSophontCode(
            name: str,
            usedCodes: typing.Collection[str]
            ) -> str:
        length = len(name)
        code = ''
        for i in range(4):
            char = name[i] if i < length else 'X'
            code += char if char.isalpha() else 'X'

        if code not in usedCodes:
            return code

        original = code
        for i in range(len(code) - 1, -1, -1):
            code = original
            prefix = code[:i]
            suffix = code[i + 1:]
            for j in range(25):
                old = ord(code[i])
                new = old + j + 1
                if old <= 90 and new > 90:
                    new -= 26
                elif old <= 122 and new > 122:
                    new -= 26

                code = prefix + chr(new) + suffix
                if code not in usedCodes:
                    return code

        raise RuntimeError(f'Unable to generate unused code for sophont {name}')

    @staticmethod
    def _generateSophontName(
        code: str,
        usedNames: typing.Collection[str]
        ) -> str:
        name = code
        while name in usedNames:
            name += 'X'
        return name
