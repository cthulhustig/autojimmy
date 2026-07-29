import common
import survey
import typing

class RawUWP(object):
    def __init__(
            self,
            starport: typing.Optional[str] = None,
            worldSize: typing.Optional[str] = None,
            atmosphere: typing.Optional[str] = None,
            hydrographics: typing.Optional[str] = None,
            population: typing.Optional[str] = None,
            government: typing.Optional[str] = None,
            lawLevel: typing.Optional[str] = None,
            techLevel: typing.Optional[str] = None
            ) -> None:
        super().__init__()

        survey.validateStarport(name='starport', value=starport, allowNone=True)
        survey.validateWorldSize(name='worldSize', value=worldSize, allowNone=True)
        survey.validateAtmosphere(name='atmosphere', value=atmosphere, allowNone=True)
        survey.validateHydrographics(name='hydrographics', value=hydrographics, allowNone=True)
        survey.validatePopulation(name='population', value=population, allowNone=True)
        survey.validateGovernment(name='government', value=government, allowNone=True)
        survey.validateLawLevel(name='lawLevel', value=lawLevel, allowNone=True)
        survey.validateTechLevel(name='techLevel', value=techLevel, allowNone=True)

        self._starport = starport
        self._worldSize = worldSize
        self._atmosphere = atmosphere
        self._hydrographics = hydrographics
        self._population = population
        self._government = government
        self._lawLevel = lawLevel
        self._techLevel = techLevel

    def starport(self) -> typing.Optional[str]:
        return self._starport

    def worldSize(self) -> typing.Optional[str]:
        return self._worldSize

    def atmosphere(self) -> typing.Optional[str]:
        return self._atmosphere

    def hydrographics(self) -> typing.Optional[str]:
        return self._hydrographics

    def population(self) -> typing.Optional[str]:
        return self._population

    def government(self) -> typing.Optional[str]:
        return self._government

    def lawLevel(self) -> typing.Optional[str]:
        return self._lawLevel

    def techLevel(self) -> typing.Optional[str]:
        return self._techLevel

class RawEconomics(object):
    def __init__(
            self,
            resources: typing.Optional[str] = None,
            labour: typing.Optional[str] = None,
            infrastructure: typing.Optional[str] = None,
            efficiency: typing.Optional[str] = None,
            ) -> None:
        super().__init__()

        survey.validateResources(name='resources', value=resources, allowNone=True)
        survey.validateLabour(name='labour', value=labour, allowNone=True)
        survey.validateInfrastructure(name='infrastructure', value=infrastructure, allowNone=True)
        survey.validateEfficiency(name='efficiency', value=efficiency, allowNone=True)

        self._resources = resources
        self._labour = labour
        self._infrastructure = infrastructure
        self._efficiency = efficiency

    def resources(self) -> typing.Optional[str]:
        return self._resources

    def labour(self) -> typing.Optional[str]:
        return self._labour

    def infrastructure(self) -> typing.Optional[str]:
        return self._infrastructure

    def efficiency(self) -> typing.Optional[str]:
        return self._efficiency

class RawCulture(object):
    def __init__(
            self,
            heterogeneity: typing.Optional[str] = None,
            acceptance: typing.Optional[str] = None,
            strangeness: typing.Optional[str] = None,
            symbols: typing.Optional[str] = None,
            ) -> None:
        super().__init__()

        survey.validateHeterogeneity(name='heterogeneity', value=heterogeneity, allowNone=True)
        survey.validateAcceptance(name='acceptance', value=acceptance, allowNone=True)
        survey.validateStrangeness(name='strangeness', value=strangeness, allowNone=True)
        survey.validateSymbols(name='symbols', value=symbols, allowNone=True)

        self._heterogeneity = heterogeneity
        self._acceptance = acceptance
        self._strangeness = strangeness
        self._symbols = symbols

    def heterogeneity(self) -> typing.Optional[str]:
        return self._heterogeneity

    def acceptance(self) -> typing.Optional[str]:
        return self._acceptance

    def strangeness(self) -> typing.Optional[str]:
        return self._strangeness

    def symbols(self) -> typing.Optional[str]:
        return self._symbols

class RawSophontPopulation(object):
    def __init__(
            self,
            sophont: str,
            percentage: typing.Optional[int]
            ) -> None:
        super().__init__()

        survey.validateSophontName(name='sophont', value=sophont)
        survey.validateSophontPercentage(name='percentage', value=percentage, allowNone=True)

        self._sophont = sophont
        self._percentage = percentage

    def sophont(self) -> str:
        return self._sophont

    def percentage(self) -> typing.Optional[int]:
        return self._percentage

class RawHexRef(object):
    def __init__(
            self,
            x: int,
            y: int,
            sector: typing.Optional[str] = None
            ):
        super().__init__()

        survey.validateHexX(name='x', value=x)
        survey.validateHexY(name='y', value=y)
        common.validateStr(name='sector', value=sector, allowNone=True, allowEmpty=False)

        self._x = x
        self._y = y
        self._sector = sector

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def sector(self) -> typing.Optional[str]:
        return self._sector

class RawRemarks(object):
    def __init__(
            self,
            tradeCodes: typing.Optional[typing.Sequence[str]] = None,
            majorRaceHomeWorlds: typing.Optional[typing.Sequence[RawSophontPopulation]] = None,
            minorRaceHomeWorlds: typing.Optional[typing.Sequence[RawSophontPopulation]] = None,
            sophontPopulations: typing.Optional[typing.Sequence[RawSophontPopulation]] = None,
            dieBackSophonts: typing.Optional[typing.Sequence[str]] = None,
            owningSystems: typing.Optional[typing.Sequence[RawHexRef]] = None,
            colonySystems: typing.Optional[typing.Sequence[RawHexRef]] = None,
            rulingAllegiances: typing.Optional[typing.Sequence[str]] = None,
            researchStations: typing.Optional[typing.Sequence[str]] = None,
            customRemarks: typing.Optional[typing.Sequence[str]] = None
            ) -> None:
        super().__init__()

        common.validateCollection(name='tradeCodes', value=tradeCodes, elementType=str, allowNone=True, validationFn=lambda n, i, v: survey.validateTradeCode(name=f'{n}[{i}]', value=v))
        common.validateCollection(name='majorRaceHomeWorlds', value=majorRaceHomeWorlds, elementType=RawSophontPopulation, allowNone=True)
        common.validateCollection(name='minorRaceHomeWorlds', value=minorRaceHomeWorlds, elementType=RawSophontPopulation, allowNone=True)
        common.validateCollection(name='sophontPopulations', value=sophontPopulations, elementType=RawSophontPopulation, allowNone=True)
        common.validateCollection(name='dieBackSophonts', value=dieBackSophonts, elementType=str, allowNone=True, validationFn=lambda n, i, v: survey.validateSophontName(name=f'{n}[{i}]', value=v))
        common.validateCollection(name='owningSystems', value=owningSystems, elementType=RawHexRef, allowNone=True)
        common.validateCollection(name='colonySystems', value=colonySystems, elementType=RawHexRef, allowNone=True)
        common.validateCollection(name='rulingAllegiances', value=rulingAllegiances, elementType=str, allowNone=True, validationFn=lambda n, i, v: survey.validateAllegianceCode(name=f'{n}[{i}]', value=v))
        common.validateCollection(name='researchStations', value=researchStations, elementType=str, allowNone=True, validationFn=lambda n, i, v: survey.validateResearchStation(name=f'{n}[{i}]', value=v))
        common.validateCollection(name='customRemarks', value=customRemarks, elementType=str, allowNone=True)

        self._tradeCodes = list(tradeCodes) if tradeCodes is not None else None
        self._sophontPopulations = list(sophontPopulations) if sophontPopulations is not None else None
        self._majorRaceHomeWorlds = list(majorRaceHomeWorlds) if majorRaceHomeWorlds is not None else None
        self._minorRaceHomeWorlds = list(minorRaceHomeWorlds) if minorRaceHomeWorlds is not None else None
        self._dieBackSophonts = list(dieBackSophonts) if dieBackSophonts is not None else None
        self._owningSystems = list(owningSystems) if owningSystems is not None else None
        self._colonySystems = list(colonySystems) if colonySystems is not None else None
        self._rulingAllegiances = list(rulingAllegiances) if rulingAllegiances is not None else None
        self._researchStations = list(researchStations) if researchStations is not None else None
        self._customRemarks = list(customRemarks) if customRemarks is not None else None

    def tradeCodes(self) -> typing.Optional[typing.Sequence[str]]:
        return common.ConstSequenceRef(self._tradeCodes) if self._tradeCodes is not None else None

    def sophontPopulations(self) -> typing.Optional[typing.Sequence[RawSophontPopulation]]:
        return common.ConstSequenceRef(self._sophontPopulations) if self._sophontPopulations is not None else None

    def majorRaceHomeWorlds(self) -> typing.Optional[typing.Sequence[RawSophontPopulation]]:
        return common.ConstSequenceRef(self._majorRaceHomeWorlds) if self._majorRaceHomeWorlds is not None else None

    def minorRaceHomeWorlds(self) -> typing.Optional[typing.Sequence[RawSophontPopulation]]:
        return common.ConstSequenceRef(self._minorRaceHomeWorlds) if self._minorRaceHomeWorlds is not None else None

    def dieBackSophonts(self) -> typing.Optional[typing.Sequence[str]]:
        return common.ConstSequenceRef(self._dieBackSophonts) if self._dieBackSophonts is not None else None

    def owningSystems(self) -> typing.Optional[typing.Sequence[RawHexRef]]:
        return common.ConstSequenceRef(self._owningSystems) if self._owningSystems is not None else None

    def colonySystems(self) -> typing.Optional[typing.Sequence[RawHexRef]]:
        return common.ConstSequenceRef(self._colonySystems) if self._colonySystems is not None else None

    def rulingAllegiances(self) -> typing.Optional[typing.Sequence[str]]:
        return common.ConstSequenceRef(self._rulingAllegiances) if self._rulingAllegiances is not None else None

    def researchStations(self) -> typing.Optional[typing.Sequence[str]]:
        return common.ConstSequenceRef(self._researchStations) if self._researchStations is not None else None

    def customRemarks(self) -> typing.Optional[typing.Sequence[str]]:
        return common.ConstSequenceRef(self._customRemarks) if self._customRemarks is not None else None

class RawPBG(object):
    def __init__(
            self,
            populationMultiplier: typing.Optional[str] = None,
            planetoidBeltCount: typing.Optional[str] = None,
            gasGiantCount: typing.Optional[str] = None
            ) -> None:
        super().__init__()

        survey.validatePopulationMultiplier(name='populationMultiplier', value=populationMultiplier, allowNone=True)
        survey.validatePlanetoidBelts(name='planetoidBeltCount', value=planetoidBeltCount, allowNone=True)
        survey.validateGasGiants(name='gasGiantCount', value=gasGiantCount, allowNone=True)

        self._populationMultiplier = populationMultiplier
        self._planetoidBeltCount = planetoidBeltCount
        self._gasGiantCount = gasGiantCount

    def populationMultiplier(self) -> typing.Optional[str]:
        return self._populationMultiplier

    def planetoidBeltCount(self) -> typing.Optional[str]:
        return self._planetoidBeltCount

    def gasGiantCount(self) -> typing.Optional[str]:
        return self._gasGiantCount

class RawStar(object):
    def __init__(
            self,
            luminosityClass: str,
            spectralClass: typing.Optional[str] = None,
            spectralScale: typing.Optional[str] = None
            ) -> None:
        super().__init__()

        survey.validateLuminosityClass(name='luminosityClass', value=luminosityClass)
        survey.validateSpectralClass(name='spectralClass', value=spectralClass, allowNone=True)
        survey.validateSpectralScale(name='spectralScale', value=spectralScale, allowNone=True)

        self._luminosityClass = luminosityClass
        self._spectralClass = spectralClass
        self._spectralScale = spectralScale

    def luminosityClass(self) -> str:
        return self._luminosityClass

    def spectralClass(self) -> typing.Optional[str]:
        return self._spectralClass

    def spectralScale(self) -> typing.Optional[str]:
        return self._spectralScale

class RawWorld(object):
    def __init__(
            self,
            x: int,
            y: int,
            name: typing.Optional[str] = None,
            allegianceCode: typing.Optional[str] = None,
            zone: typing.Optional[str] = None,
            uwp: typing.Optional[RawUWP] = None,
            economics: typing.Optional[RawEconomics] = None,
            culture: typing.Optional[RawCulture] = None,
            nobilities: typing.Optional[typing.Sequence[str]] = None,
            bases: typing.Optional[typing.Sequence[str]] = None,
            remarks: typing.Optional[RawRemarks] = None,
            importance: typing.Optional[int] = None,
            pbg: typing.Optional[RawPBG] = None,
            systemWorlds: typing.Optional[int] = None,
            stars: typing.Optional[typing.Sequence[RawStar]] = None
            ) -> None:
        super().__init__()

        survey.validateHexX(name='x', value=x)
        survey.validateHexY(name='y', value=y)
        common.validateStr(name='name', value=name, allowNone=True, allowEmpty=False)
        survey.validateAllegianceCode(name='allegianceCode', value=allegianceCode, allowNone=True)
        survey.validateZone(name='zone', value=zone, allowNone=True)
        common.validateObject(name='uwp', value=uwp, objectType=RawUWP, allowNone=True)
        common.validateObject(name='economics', value=economics, objectType=RawEconomics, allowNone=True)
        common.validateObject(name='culture', value=culture, objectType=RawCulture, allowNone=True)
        common.validateCollection(name='nobilities', value=nobilities, elementType=str, allowNone=True, validationFn=lambda n, i, v: survey.validateNobility(name=f'{n}[{i}]', value=v))
        common.validateCollection(name='bases', value=bases, elementType=str, allowNone=True, validationFn=lambda n, i, v: survey.validateBase(name=f'{n}[{i}]', value=v))
        common.validateObject(name='remarks', value=remarks, objectType=RawRemarks, allowNone=True)
        common.validateInt(name='importance', value=importance, allowNone=True)
        common.validateObject(name='pbg', value=pbg, objectType=RawPBG, allowNone=True)
        common.validateInt(name='systemWorlds', value=systemWorlds, allowNone=True, min=0)
        common.validateCollection(name=stars, value=stars, elementType=RawStar, allowNone=True)

        self._x = x
        self._y = y
        self._name = name
        self._allegianceCode = allegianceCode
        self._zone = zone
        self._uwp = uwp
        self._economics = economics
        self._culture = culture
        self._nobilities = list(nobilities) if nobilities is not None else None
        self._bases = list(bases) if bases is not None else None
        self._remarks = remarks
        self._importance = importance
        self._pbg = pbg
        self._systemWorlds = systemWorlds
        self._stars = list(stars) if stars is not None else None

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def name(self) -> typing.Optional[str]:
        return self._name

    def allegianceCode(self) -> typing.Optional[str]:
        return self._allegianceCode

    def zone(self) -> typing.Optional[str]:
        return self._zone

    def uwp(self) -> typing.Optional[RawUWP]:
        return self._uwp

    def economics(self) -> typing.Optional[RawEconomics]:
        return self._economics

    def culture(self) -> typing.Optional[RawCulture]:
        return self._culture

    def nobilities(self) -> typing.Optional[typing.Sequence[str]]:
        return common.ConstSequenceRef(self._nobilities) if self._nobilities is not None else None

    def bases(self) -> typing.Optional[typing.Sequence[str]]:
        return common.ConstSequenceRef(self._bases) if self._bases is not None else None

    def remarks(self) -> typing.Optional[RawRemarks]:
        return self._remarks

    def importance(self) -> typing.Optional[int]:
        return self._importance

    def pbg(self) -> typing.Optional[RawPBG]:
        return self._pbg

    def systemWorlds(self) -> typing.Optional[int]:
        return self._systemWorlds

    def stars(self) -> typing.Optional[typing.Sequence[RawStar]]:
        return common.ConstSequenceRef(self._stars) if self._stars is not None else None

class RawAllegiance(object):
    def __init__(
            self,
            code: str,
            name: str,
            base: typing.Optional[str]
            ) -> None:
        super().__init__()

        survey.validateAllegianceCode(name='code', value=code)
        survey.validateAllegianceName(name='name', value=name)
        survey.validateAllegianceCode(name='base', value=base, allowNone=True)

        self._code = code
        self._name = name
        self._base = base

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def base(self) -> typing.Optional[str]:
        return self._base

class RawRoute(object):
    def __init__(
            self,
            startHexX: int,
            startHexY: int,
            endHexX: int,
            endHexY: int,
            startOffsetX: typing.Optional[int],
            startOffsetY: typing.Optional[int],
            endOffsetX: typing.Optional[int],
            endOffsetY: typing.Optional[int],
            allegianceCode: typing.Optional[str],
            type: typing.Optional[str],
            style: typing.Optional[str],
            colour: typing.Optional[str],
            width: typing.Optional[float]
            ) -> None:
        super().__init__()

        # NOTE: The metadata spec says routes can have start/end sectors in the range
        # 0-33 in X and 0-41 in Y rather than the normal 1-32 and 1-40
        survey.validateHexX(name='startHexX', value=startHexX, allowInvalid=True)
        survey.validateHexY(name='startHexY', value=startHexY, allowInvalid=True)
        survey.validateHexX(name='endHexX', value=endHexX, allowInvalid=True)
        survey.validateHexY(name='endHexY', value=endHexY, allowInvalid=True)
        common.validateInt(name='startOffsetX', value=startOffsetX, allowNone=True)
        common.validateInt(name='startOffsetY', value=startOffsetY, allowNone=True)
        common.validateInt(name='endOffsetX', value=endOffsetX, allowNone=True)
        common.validateInt(name='endOffsetY', value=endOffsetY, allowNone=True)
        survey.validateAllegianceCode(name='allegianceCode', value=allegianceCode, allowNone=True)
        common.validateStr(name='type', value=type, allowNone=True, allowEmpty=False)
        survey.validateLineStyle(name='style', value=style, allowNone=True)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        survey.validateLineWidth(name='width', value=width, allowNone=True)

        self._startHexX = startHexX
        self._startHexY = startHexY
        self._endHexX = endHexX
        self._endHexY = endHexY
        self._startOffsetX = startOffsetX
        self._startOffsetY = startOffsetY
        self._endOffsetX = endOffsetX
        self._endOffsetY = endOffsetY
        self._allegianceCode = allegianceCode
        self._type = type
        self._style = style
        self._colour = colour
        self._width = width

    def startHexX(self) -> int:
        return self._startHexX

    def startHexY(self) -> int:
        return self._startHexY

    def endHexX(self) -> int:
        return self._endHexX

    def endHexY(self) -> int:
        return self._endHexY

    def startOffsetX(self) -> typing.Optional[int]:
        return self._startOffsetX

    def startOffsetY(self) -> typing.Optional[int]:
        return self._startOffsetY

    def endOffsetX(self) -> typing.Optional[int]:
        return self._endOffsetX

    def endOffsetY(self) -> typing.Optional[int]:
        return self._endOffsetY

    def allegianceCode(self) -> typing.Optional[str]:
        return self._allegianceCode

    def type(self) -> typing.Optional[str]:
        return self._type

    def style(self) -> typing.Optional[str]:
        return self._style

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def width(self) -> typing.Optional[float]:
        return self._width

# NOTE: If I'm ever generating borders then there are rules about the "winding" of the hex list
# https://travellermap.com/doc/metadata#borders
class RawBorder(object):
    def __init__(
            self,
            hexes: typing.Sequence[typing.Tuple[int, int]],
            allegianceCode: typing.Optional[str],
            showLabel: typing.Optional[bool],
            wrapLabel: typing.Optional[bool],
            labelHexX: typing.Optional[int],
            labelHexY: typing.Optional[int],
            labelOffsetX: typing.Optional[float],
            labelOffsetY: typing.Optional[float],
            label: typing.Optional[str],
            style: typing.Optional[str],
            colour: typing.Optional[str]
            ) -> None:
        super().__init__()

        survey.validateHexCollection(name='hexes', value=hexes, allowInvalid=True, allowEmpty=False)
        survey.validateAllegianceCode(name='allegianceCode', value=allegianceCode, allowNone=True)
        common.validateBool(name='showLabel', value=showLabel, allowNone=True)
        common.validateBool(name='wrapLabel', value=wrapLabel, allowNone=True)
        survey.validateHexX(name='labelHexX', value=labelHexX, allowNone=True, allowInvalid=True)
        survey.validateHexY(name='labelHexY', value=labelHexY, allowNone=True, allowInvalid=True)
        common.validateFloat(name='labelOffsetX', value=labelOffsetX, allowNone=True)
        common.validateFloat(name='labelOffsetY', value=labelOffsetY, allowNone=True)
        common.validateStr(name='label', value=label, allowNone=True, allowEmpty=False)
        survey.validateLineStyle(name='style', value=style, allowNone=True)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)

        self._hexes = list(hexes)
        self._allegianceCode = allegianceCode
        self._showLabel = showLabel
        self._wrapLabel = wrapLabel
        self._labelHexX = labelHexX
        self._labelHexY = labelHexY
        self._labelOffsetX = labelOffsetX
        self._labelOffsetY = labelOffsetY
        self._label = label
        self._style = style
        self._colour = colour

    def hexes(self) -> typing.Sequence[typing.Tuple[int, int]]:
        return common.ConstSequenceRef(self._hexes)

    def allegianceCode(self) -> typing.Optional[str]:
        return self._allegianceCode

    def showLabel(self) -> typing.Optional[bool]:
        return self._showLabel

    def wrapLabel(self) -> typing.Optional[bool]:
        return self._wrapLabel

    def labelHexX(self) -> typing.Optional[int]:
        return self._labelHexX

    def labelHexY(self) -> typing.Optional[int]:
        return self._labelHexY

    def labelOffsetX(self) -> typing.Optional[float]:
        return self._labelOffsetX

    def labelOffsetY(self) -> typing.Optional[float]:
        return self._labelOffsetY

    def label(self) -> typing.Optional[str]:
        return self._label

    def style(self) -> typing.Optional[str]:
        return self._style

    def colour(self) -> typing.Optional[str]:
        return self._colour

# NOTE: If I'm ever generating routes then they follow the same "winding" rules for the hex list as borders
# https://travellermap.com/doc/metadata#borders
class RawRegion(object):
    def __init__(
            self,
            hexes: typing.Sequence[typing.Tuple[int, int]],
            showLabel: typing.Optional[bool],
            wrapLabel: typing.Optional[bool],
            labelHexX: typing.Optional[int],
            labelHexY: typing.Optional[int],
            labelOffsetX: typing.Optional[float],
            labelOffsetY: typing.Optional[float],
            label: typing.Optional[str],
            colour: typing.Optional[str]
            ) -> None:
        super().__init__()

        survey.validateHexCollection(name='hexes', value=hexes, allowInvalid=True, allowEmpty=False)
        common.validateBool(name='showLabel', value=showLabel, allowNone=True)
        common.validateBool(name='wrapLabel', value=wrapLabel, allowNone=True)
        survey.validateHexX(name='labelHexX', value=labelHexX, allowNone=True, allowInvalid=True)
        survey.validateHexY(name='labelHexY', value=labelHexY, allowNone=True, allowInvalid=True)
        common.validateFloat(name='labelOffsetX', value=labelOffsetX, allowNone=True)
        common.validateFloat(name='labelOffsetY', value=labelOffsetY, allowNone=True)
        common.validateStr(name='label', value=label, allowNone=True, allowEmpty=False)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)

        self._hexes = list(hexes)
        self._showLabel = showLabel
        self._wrapLabel = wrapLabel
        self._labelHexX = labelHexX
        self._labelHexY = labelHexY
        self._labelOffsetX = labelOffsetX
        self._labelOffsetY = labelOffsetY
        self._label = label
        self._colour = colour

    def hexes(self) -> typing.Sequence[typing.Tuple[int, int]]:
        return common.ConstSequenceRef(self._hexes)

    def showLabel(self) -> typing.Optional[bool]:
        return self._showLabel

    def wrapLabel(self) -> typing.Optional[bool]:
        return self._wrapLabel

    def labelHexX(self) -> typing.Optional[int]:
        return self._labelHexX

    def labelHexY(self) -> typing.Optional[int]:
        return self._labelHexY

    def labelOffsetX(self) -> typing.Optional[float]:
        return self._labelOffsetX

    def labelOffsetY(self) -> typing.Optional[float]:
        return self._labelOffsetY

    def label(self) -> typing.Optional[str]:
        return self._label

    def colour(self) -> typing.Optional[str]:
        return self._colour

class RawSectorLabel(object):
    def __init__(
            self,
            text: str,
            hexX: int,
            hexY: int,
            colour: str,
            size: typing.Optional[str],
            wrap: typing.Optional[bool],
            offsetX: typing.Optional[float],
            offsetY: typing.Optional[float]
            ) -> None:
        super().__init__()

        common.validateStr(name='text', value=text, allowEmpty=False)
        survey.validateHexX(name='hexX', value=hexX, allowInvalid=True)
        survey.validateHexY(name='hexY', value=hexY, allowInvalid=True)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        survey.validateLabelSize(name='size', value=size, allowNone=True)
        common.validateBool(name='wrap', value=wrap, allowNone=True)
        common.validateFloat(name='offsetX', value=offsetX, allowNone=True)
        common.validateFloat(name='offsetY', value=offsetY, allowNone=True)

        self._text = text
        self._hexX = hexX
        self._hexY = hexY
        self._colour = colour
        self._size = size
        self._wrap = wrap
        self._offsetX = offsetX
        self._offsetY = offsetY

    def text(self) -> str:
        return self._text

    def hexX(self) -> int:
        return self._hexX

    def hexY(self) -> int:
        return self._hexY

    def colour(self) -> str:
        return self._colour

    def size(self) -> typing.Optional[str]:
        return self._size

    def wrap(self) -> typing.Optional[bool]:
        return self._wrap

    def offsetX(self) -> typing.Optional[float]:
        return self._offsetX

    def offsetY(self) -> typing.Optional[float]:
        return self._offsetY

class RawSource(object):
    def __init__(
            self,
            publication: typing.Optional[str],
            author: typing.Optional[str],
            publisher: typing.Optional[str],
            reference: typing.Optional[str]
            ) -> None:
        super().__init__()

        common.validateStr(name='publication', value=publication, allowNone=True, allowEmpty=False)
        common.validateStr(name='author', value=author, allowNone=True, allowEmpty=False)
        common.validateStr(name='publisher', value=publisher, allowNone=True, allowEmpty=False)
        common.validateStr(name='reference', value=reference, allowNone=True, allowEmpty=False)

        self._publication = publication
        self._publisher = publisher
        self._author = author
        self._reference = reference

    def publication(self) -> typing.Optional[str]:
        return self._publication

    def author(self) -> typing.Optional[str]:
        return self._author

    def publisher(self) -> typing.Optional[str]:
        return self._publisher

    def reference(self) -> typing.Optional[str]:
        return self._reference

class RawSources(object):
    def __init__(
            self,
            credits: typing.Optional[str],
            primary: typing.Optional[RawSource],
            products: typing.Optional[typing.Sequence[RawSource]]
            ) -> None:
        super().__init__()

        common.validateStr(name='credits', value=credits, allowNone=True, allowEmpty=False)
        common.validateObject(name='primary', value=primary, objectType=RawSource, allowNone=True)
        common.validateCollection(name='products', value=products, elementType=RawSource, allowNone=True)

        self._credits = credits
        self._primary = primary
        self._products = list(products) if products is not None else None

    def credits(self) -> typing.Optional[str]:
        return self._credits

    def primary(self) -> typing.Optional[RawSource]:
        return self._primary

    def products(self) -> typing.Optional[typing.Sequence[RawSource]]:
        return common.ConstSequenceRef(self._products) if self._products is not None else None

class RawRouteStyle(object):
    def __init__(
            self,
            tag: typing.Optional[str], # None means this is a default style
            colour: typing.Optional[str],
            style: typing.Optional[str],
            width: typing.Optional[float],
            ) -> None:
        super().__init__()

        common.validateStr(name='tag', value=tag, allowNone=True, allowEmpty=False)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        survey.validateLineStyle(name='style', value=style, allowNone=True)
        survey.validateLineWidth(name='width', value=width, allowNone=True)

        self._tag = tag
        self._colour = colour
        self._style = style
        self._width = width

    def tag(self) -> typing.Optional[str]:
        return self._tag

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def style(self) -> typing.Optional[str]:
        return self._style

    def width(self) -> typing.Optional[float]:
        return self._width

class RawBorderStyle(object):
    def __init__(
            self,
            tag: typing.Optional[str], # None means this is a default style
            colour: typing.Optional[str],
            style: typing.Optional[str]
            ) -> None:
        super().__init__()

        common.validateStr(name='tag', value=tag, allowNone=True, allowEmpty=False)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        survey.validateLineStyle(name='style', value=style, allowNone=True)

        self._tag = tag
        self._colour = colour
        self._style = style

    def tag(self) -> typing.Optional[str]:
        return self._tag

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def style(self) -> typing.Optional[str]:
        return self._style

class RawStyleSheet(object):
    def __init__(
            self,
            routeStyles: typing.Sequence[RawRouteStyle],
            borderStyles: typing.Sequence[RawBorderStyle],
            ) -> None:
        super().__init__()

        common.validateCollection(name='routeStyles', value=routeStyles, elementType=RawRouteStyle)
        common.validateCollection(name='borderStyles', value=borderStyles, elementType=RawBorderStyle)

        self._routeStyles = list(routeStyles)
        self._borderStyles = list(borderStyles)

    def routeStyles(self) -> typing.Sequence[RawRouteStyle]:
        return common.ConstSequenceRef(self._routeStyles)

    def borderStyles(self) -> typing.Sequence[RawBorderStyle]:
        return common.ConstSequenceRef(self._borderStyles)

class RawMetadata(object):
    def __init__(
            self,
            x: int,
            y: int,
            canonicalName: str,
            alternateNames: typing.Optional[typing.Sequence[str]],
            nameLanguages: typing.Optional[typing.Mapping[str, str]], # Maps names to languages
            abbreviation: typing.Optional[str],
            sectorLabel: typing.Optional[str],
            subsectorNames: typing.Optional[typing.Mapping[str, str]], # Maps subsector code (A-P) to the name of that sector
            selected: typing.Optional[bool],
            tags: typing.Optional[typing.Sequence[str]],
            allegiances: typing.Optional[typing.Sequence[RawAllegiance]],
            routes: typing.Optional[typing.Sequence[RawRoute]],
            borders: typing.Optional[typing.Sequence[RawBorder]],
            labels: typing.Optional[typing.Sequence[RawSectorLabel]],
            regions: typing.Optional[typing.Sequence[RawRegion]],
            sources: typing.Optional[RawSources],
            styleSheet: typing.Optional[RawStyleSheet]
            ) -> None:
        super().__init__()

        common.validateInt(name='x', value=x)
        common.validateInt(name='y', value=y)
        common.validateStr(name='canonicalName', value=canonicalName, allowEmpty=False)
        common.validateCollection(name='alternateNames', value=alternateNames, elementType=str, allowNone=True)
        common.validateMapping(name='nameLanguages', value=nameLanguages, keyType=str, valueType=str, allowNone=True, validationFn=RawMetadata._validateSectorNameLanguage)
        common.validateStr(name='abbreviation', value=abbreviation, allowNone=True, allowEmpty=False)
        common.validateStr(name='sectorLabel', value=sectorLabel, allowNone=True, allowEmpty=False)
        common.validateMapping(name='subsectorNames', value=subsectorNames, keyType=str, valueType=str, allowNone=True, validationFn=RawMetadata._validateSubsectorName)
        common.validateBool(name='selected', value=selected, allowNone=True)
        common.validateCollection(name='tags', value=tags, elementType=str, allowNone=True)
        common.validateCollection(name='allegiances', value=allegiances, elementType=RawAllegiance, allowNone=True)
        common.validateCollection(name='routes', value=routes, elementType=RawRoute, allowNone=True)
        common.validateCollection(name='borders', value=borders, elementType=RawBorder, allowNone=True)
        common.validateCollection(name='labels', value=labels, elementType=RawSectorLabel, allowNone=True)
        common.validateCollection(name='regions', value=regions, elementType=RawRegion, allowNone=True)
        common.validateObject(name='sources', value=sources, objectType=RawSources, allowNone=True)
        common.validateObject(name='styleSheet', value=styleSheet, objectType=RawStyleSheet, allowNone=True)

        self._x = x
        self._y = y
        self._canonicalName = canonicalName
        self._alternateNames = list(alternateNames) if alternateNames is not None else None
        self._nameLanguages = dict(nameLanguages) if nameLanguages is not None else None
        self._abbreviation = abbreviation
        self._sectorLabel = sectorLabel
        self._subsectorNames = dict(subsectorNames) if subsectorNames is not None else None
        self._selected = selected
        self._tags = tags
        self._allegiances = list(allegiances) if allegiances is not None else None
        self._routes = list(routes) if routes is not None else None
        self._borders = list(borders) if borders is not None else None
        self._labels = list(labels) if labels is not None else None
        self._regions = list(regions) if regions is not None else None
        self._sources = sources
        self._styleSheet = styleSheet

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def canonicalName(self) -> str:
        return self._canonicalName

    def alternateNames(self) -> typing.Optional[typing.Sequence[str]]:
        return common.ConstSequenceRef(self._alternateNames) if self._alternateNames is not None else None

    def names(self) -> typing.Sequence[str]:
        names = [self._canonicalName]
        if self._alternateNames:
            names.extend(self._alternateNames)
        return names

    def nameLanguage(self, name: str) -> typing.Optional[str]:
        if not self._nameLanguages:
            return None
        return self._nameLanguages.get(name, None)

    def nameLanguages(self) -> typing.Mapping[str, str]:
        return common.ConstMappingRef(self._nameLanguages) if self._nameLanguages is not None else None

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def sectorLabel(self) -> typing.Optional[str]:
        return self._sectorLabel

    def subsectorNames(self) -> typing.Optional[typing.Mapping[str, str]]:
        return common.ConstMappingRef(self._subsectorNames) if self._subsectorNames is not None else None

    def selected(self) -> typing.Optional[bool]:
        return self._selected

    def tags(self) -> typing.Optional[typing.Sequence[str]]:
        return common.ConstSequenceRef(self._tags) if self._tags is not None else None

    def allegiances(self) -> typing.Optional[typing.Sequence[RawAllegiance]]:
        return common.ConstSequenceRef(self._allegiances) if self._allegiances is not None else None

    def routes(self) -> typing.Optional[typing.Sequence[RawRoute]]:
        return common.ConstSequenceRef(self._routes) if self._routes is not None else None

    def borders(self) -> typing.Optional[typing.Sequence[RawBorder]]:
        return common.ConstSequenceRef(self._borders) if self._borders is not None else None

    def labels(self) -> typing.Optional[typing.Sequence[RawSectorLabel]]:
        return common.ConstSequenceRef(self._labels) if self._labels is not None else None

    def regions(self) -> typing.Optional[typing.Sequence[RawRegion]]:
        return common.ConstSequenceRef(self._regions) if self._regions is not None else None

    def sources(self) -> typing.Optional[RawSources]:
        return self._sources

    def styleSheet(self) -> typing.Optional[RawStyleSheet]:
        return self._styleSheet

    @staticmethod
    def _validateSectorNameLanguage(
            attributeName: str,
            sectorName: str,
            nameLanguage: str
            ) -> None:
        if len(sectorName) == 0:
            raise ValueError(f'{attributeName} names can\'t be empty')
        if len(nameLanguage) == 0:
            raise ValueError(f'{attributeName} languages can\'t be empty')

    @staticmethod
    def _validateSubsectorName(
            attributeName: str,
            subsectorCode: str,
            subsectorName: str
            ) -> None:
            upperCode = subsectorCode.upper()
            if len(upperCode) != 1 or (ord(upperCode) < ord('A') or ord(upperCode) > ord('P')):
                raise ValueError(f'{attributeName} codes must be A-P')
            if len(subsectorName) == 0:
                raise ValueError(f'{attributeName} names can\'t be empty')

class RawNameInfo(object):
    def __init__(
            self,
            name: str,
            language: typing.Optional[str],
            source: typing.Optional[str]
            ):
        super().__init__()

        common.validateStr(name='name', value=name, allowEmpty=False)
        common.validateStr(name='language', value=language, allowNone=True, allowEmpty=False)
        common.validateStr(name='source', value=source, allowNone=True, allowEmpty=False)

        self._name = name
        self._language = language
        self._source = source

    def name(self) -> str:
        return self._name

    def language(self) -> typing.Optional[str]:
        return self._language

    def source(self) -> typing.Optional[str]:
        return self._source

class RawSectorInfo(object):
    def __init__(
            self,
            x: int,
            y: int,
            milieu: str,
            abbreviation: typing.Optional[str],
            tags: typing.Optional[str],
            nameInfos: typing.Optional[typing.Sequence[RawNameInfo]],
            ) -> None:
        super().__init__()

        common.validateInt(name='x', value=x)
        common.validateInt(name='y', value=y)
        common.validateStr(name='milieu', value=milieu, allowEmpty=False)
        common.validateStr(name='abbreviation', value=abbreviation, allowNone=True, allowEmpty=False)
        common.validateStr(name='tags', value=tags, allowNone=True, allowEmpty=False)
        common.validateCollection(name='nameInfos', value=nameInfos, elementType=RawNameInfo, allowNone=True)

        self._x = x
        self._y = y
        self._milieu = milieu
        self._abbreviation = abbreviation
        self._tags = tags
        self._nameInfos = list(nameInfos) if nameInfos is not None else None

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def milieu(self) -> str:
        return self._milieu

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def tags(self) -> typing.Optional[str]:
        return self._tags

    def nameInfos(self) -> typing.Optional[typing.Sequence[RawNameInfo]]:
        return common.ConstSequenceRef(self._nameInfos) if self._nameInfos is not None else None

class RawStockAllegiance(object):
    def __init__(
            self,
            code: str,
            name: str,
            legacy: str,
            base: typing.Optional[str] = None,
            location: typing.Optional[str] = None
            ) -> None:
        super().__init__()

        common.validateStr(name='code', value=code, allowEmpty=False)
        common.validateStr(name='name', value=name, allowEmpty=False)
        common.validateStr(name='legacy', value=legacy, allowEmpty=False)
        common.validateStr(name='base', value=base, allowNone=True, allowEmpty=False)
        common.validateStr(name='location', value=location, allowNone=True, allowEmpty=False)

        self._code = code
        self._name = name
        self._legacy = legacy
        self._base = base
        self._location = location

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def legacy(self) -> str:
        return self._legacy

    def base(self) -> typing.Optional[str]:
        return self._base

    def location(self) -> typing.Optional[str]:
        return self._location

class RawStockSophont(object):
    def __init__(
            self,
            code: str,
            name: str,
            location: typing.Optional[str] = None
            ) -> None:
        super().__init__()

        common.validateStr(name='code', value=code, allowEmpty=False)
        common.validateStr(name='name', value=name, allowEmpty=False)
        common.validateStr(name='location', value=location, allowNone=True, allowEmpty=False)

        self._code = code
        self._name = name
        self._location = location

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def location(self) -> str:
        return self._location

class RawUniverseLabel(object):
    def __init__(
            self,
            text: str,
            worldX: float,
            worldY: float,
            minor: bool
            ) -> None:
        super().__init__()

        common.validateStr(name='text', value=text)
        common.validateFloat(name='worldX', value=worldX)
        common.validateFloat(name='worldY', value=worldY)
        common.validateBool(name='minor', value=minor)

        self._text = text
        self._worldX = worldX
        self._worldY = worldY
        self._minor = minor

    def text(self) -> str:
        return self._text

    def worldX(self) -> float:
        return self._worldX

    def worldY(self) -> float:
        return self._worldY

    def minor(self) -> bool:
        return self._minor

class RawWorldLabel(object):
    def __init__(
            self,
            name: str,
            sector: str,
            hexX: int,
            hexY: int,
            options: typing.Sequence[str],
            biasX: typing.Optional[int] = None,
            biasY: typing.Optional[int] = None,
            ) -> None:
        super().__init__()

        common.validateStr(name='name', value=name)
        common.validateStr(name='sector', value=sector, allowEmpty=False)
        common.validateInt(name='hexX', value=hexX)
        common.validateInt(name='hexY', value=hexY)
        common.validateCollection(name='options', value=options, elementType=str, allowEmpty=False)
        common.validateInt(name='biasX', value=biasX, allowNone=True)
        common.validateInt(name='biasY', value=biasY, allowNone=True)

        self._name = name
        self._sector = sector
        self._hexX = hexX
        self._hexY = hexY
        self._options = list(options)
        self._biasX = biasX
        self._biasY = biasY

    def name(self) -> str:
        return self._name

    def sector(self) -> str:
        return self._sector

    def hexX(self) -> int:
        return self._hexX

    def hexY(self) -> int:
        return self._hexY

    def options(self) -> typing.Sequence[str]:
        return common.ConstCollectionRef(self._options)

    def biasX(self) -> typing.Optional[int]:
        return self._biasX

    def biasY(self) -> typing.Optional[int]:
        return self._biasY