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

        survey.validateOptionalStarport(name='starport', value=starport)
        survey.validateOptionalWorldSize(name='worldSize', value=worldSize)
        survey.validateOptionalAtmosphere(name='atmosphere', value=atmosphere)
        survey.validateOptionalHydrographics(name='hydrographics', value=hydrographics)
        survey.validateOptionalPopulation(name='population', value=population)
        survey.validateOptionalGovernment(name='government', value=government)
        survey.validateOptionalLawLevel(name='lawLevel', value=lawLevel)
        survey.validateOptionalTechLevel(name='techLevel', value=techLevel)

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

        survey.validateOptionalResources(name='resources', value=resources)
        survey.validateOptionalLabour(name='labour', value=labour)
        survey.validateOptionalInfrastructure(name='infrastructure', value=infrastructure)
        survey.validateOptionalEfficiency(name='efficiency', value=efficiency)

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

        survey.validateOptionalHeterogeneity(name='heterogeneity', value=heterogeneity)
        survey.validateOptionalAcceptance(name='acceptance', value=acceptance)
        survey.validateOptionalStrangeness(name='strangeness', value=strangeness)
        survey.validateOptionalSymbols(name='symbols', value=symbols)

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

        common.validateMandatoryStr(name='sophont', value=sophont, allowEmpty=False)
        common.validateOptionalInt(name='percentage', value=percentage, min=0, max=100)

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

        survey.validateMandatoryHexX(name='x', value=x)
        survey.validateMandatoryHexY(name='y', value=y)
        common.validateOptionalStr(name='sector', value=sector, allowEmpty=False)

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

        # TODO: The way this is validating elements is hacky
        common.validateOptionalCollection(name='tradeCodes', value=tradeCodes, type=str, validationFn=lambda n, v: survey.validateMandatoryTradeCode(name=n, value=v))
        common.validateOptionalCollection(name='majorRaceHomeWorlds', value=majorRaceHomeWorlds, type=RawSophontPopulation)
        common.validateOptionalCollection(name='minorRaceHomeWorlds', value=minorRaceHomeWorlds, type=RawSophontPopulation)
        common.validateOptionalCollection(name='sophontPopulations', value=sophontPopulations, type=RawSophontPopulation)
        common.validateOptionalCollection(name='dieBackSophonts', value=dieBackSophonts, type=str)
        common.validateOptionalCollection(name='owningSystems', value=owningSystems, type=RawHexRef)
        common.validateOptionalCollection(name='colonySystems', value=colonySystems, type=RawHexRef)
        common.validateOptionalCollection(name='rulingAllegiances', value=rulingAllegiances, type=str)
        # TODO: The way this is validating elements is hacky
        common.validateOptionalCollection(name='researchStations', value=researchStations, type=str, validationFn=lambda n, v: survey.validateMandatoryResearchStation(name=n, value=v))
        common.validateOptionalCollection(name='customRemarks', value=customRemarks, type=str)

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

        survey.validateOptionalPopulationMultiplier(name='populationMultiplier', value=populationMultiplier)
        survey.validateOptionalPlanetoidBelts(name='planetoidBeltCount', value=planetoidBeltCount)
        survey.validateOptionalGasGiants(name='gasGiantCount', value=gasGiantCount)

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

        survey.validateMandatoryLuminosityClass(name='luminosityClass', value=luminosityClass)
        survey.validateOptionalSpectralClass(name='spectralClass', value=spectralClass)
        survey.validateOptionalSpectralScale(name='spectralScale', value=spectralScale)

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
            allegiance: typing.Optional[str] = None,
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

        survey.validateMandatoryHexX(name='x', value=x)
        survey.validateMandatoryHexY(name='y', value=y)
        common.validateOptionalStr(name='name', value=name, allowEmpty=False)
        common.validateOptionalStr(name='allegiance', value=allegiance, allowEmpty=False)
        survey.validateOptionalZone(name='zone', value=zone)
        common.validateOptionalObject(name='uwp', value=uwp, type=RawUWP)
        common.validateOptionalObject(name='economics', value=economics, type=RawEconomics)
        common.validateOptionalObject(name='culture', value=culture, type=RawCulture)
        # TODO: The way these are validating elements is hacky
        common.validateOptionalCollection(name='nobilities', value=nobilities, type=str, validationFn=lambda n, v: survey.validateMandatoryNobility(name=n, value=v))
        common.validateOptionalCollection(name='bases', value=bases, type=str, validationFn=lambda n, v: survey.validateMandatoryBase(name=n, value=v))
        common.validateOptionalObject(name='remarks', value=remarks, type=RawRemarks)
        common.validateOptionalInt(name='importance', value=importance)
        common.validateOptionalObject(name='pbg', value=pbg, type=RawPBG)
        common.validateOptionalInt(name='systemWorlds', value=systemWorlds, min=0)
        common.validateOptionalCollection(name=stars, value=stars, type=RawStar)

        self._x = x
        self._y = y
        self._name = name
        self._allegiance = allegiance
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

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

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

        common.validateMandatoryStr(name='code', value=code, allowEmpty=False)
        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)
        common.validateOptionalStr(name='base', value=base, allowEmpty=False)

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
            allegiance: typing.Optional[str],
            type: typing.Optional[str],
            style: typing.Optional[str],
            colour: typing.Optional[str],
            width: typing.Optional[float]
            ) -> None:
        super().__init__()

        survey.validateMandatoryHexX(name='startHexX', value=startHexX)
        survey.validateMandatoryHexY(name='startHexY', value=startHexY)
        survey.validateMandatoryHexX(name='endHexX', value=endHexX)
        survey.validateMandatoryHexY(name='endHexY', value=endHexY)
        common.validateOptionalInt(name='startOffsetX', value=startOffsetX)
        common.validateOptionalInt(name='startOffsetY', value=startOffsetY)
        common.validateOptionalInt(name='endOffsetX', value=endOffsetX)
        common.validateOptionalInt(name='endOffsetY', value=endOffsetY)
        common.validateOptionalStr(name='allegiance', value=allegiance, allowEmpty=False)
        common.validateOptionalStr(name='type', value=type, allowEmpty=False)
        survey.validateOptionalLineStyle(name='style', value=style)
        common.validateOptionalHtmlColour(name='colour', value=colour)
        common.validateOptionalFloat(name='width', value=width, min=0)

        self._startHexX = startHexX
        self._startHexY = startHexY
        self._endHexX = endHexX
        self._endHexY = endHexY
        self._startOffsetX = startOffsetX
        self._startOffsetY = startOffsetY
        self._endOffsetX = endOffsetX
        self._endOffsetY = endOffsetY
        self._allegiance = allegiance
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

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

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
            allegiance: typing.Optional[str],
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

        survey.validateMandatoryHexCollection(name='hexes', value=hexes, allowInvalid=True, allowEmpty=False)
        common.validateOptionalStr(name='allegiance', value=allegiance, allowEmpty=False)
        common.validateOptionalBool(name='showLabel', value=showLabel)
        common.validateOptionalBool(name='wrapLabel', value=wrapLabel)
        survey.validateOptionalHexX(name='labelHexX', value=labelHexX, allowInvalid=True)
        survey.validateOptionalHexY(name='labelHexY', value=labelHexY, allowInvalid=True)
        common.validateOptionalFloat(name='labelOffsetX', value=labelOffsetX)
        common.validateOptionalFloat(name='labelOffsetY', value=labelOffsetY)
        common.validateOptionalStr(name='label', value=label, allowEmpty=False)
        survey.validateOptionalLineStyle(name='style', value=style)
        common.validateOptionalHtmlColour(name='colour', value=colour)

        self._hexes = list(hexes)
        self._allegiance = allegiance
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

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

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

        survey.validateMandatoryHexCollection(name='hexes', value=hexes, allowInvalid=True, allowEmpty=False)
        common.validateOptionalBool(name='showLabel', value=showLabel)
        common.validateOptionalBool(name='wrapLabel', value=wrapLabel)
        survey.validateOptionalHexX(name='labelHexX', value=labelHexX, allowInvalid=True)
        survey.validateOptionalHexY(name='labelHexY', value=labelHexY, allowInvalid=True)
        common.validateOptionalFloat(name='labelOffsetX', value=labelOffsetX)
        common.validateOptionalFloat(name='labelOffsetY', value=labelOffsetY)
        common.validateOptionalStr(name='label', value=label, allowEmpty=False)
        common.validateOptionalHtmlColour(name='colour', value=colour)

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

class RawLabel(object):
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

        common.validateMandatoryStr(name='text', value=text, allowEmpty=False)
        survey.validateMandatoryHexX(name='hexX', value=hexX, allowInvalid=True)
        survey.validateMandatoryHexY(name='hexY', value=hexY, allowInvalid=True)
        common.validateOptionalHtmlColour(name='colour', value=colour)
        survey.validateOptionalLabelSize(name='size', value=size)
        common.validateOptionalBool(name='wrap', value=wrap)
        common.validateOptionalFloat(name='offsetX', value=offsetX)
        common.validateOptionalFloat(name='offsetY', value=offsetY)

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

        common.validateOptionalStr(name='publication', value=publication, allowEmpty=False)
        common.validateOptionalStr(name='author', value=author, allowEmpty=False)
        common.validateOptionalStr(name='publisher', value=publisher, allowEmpty=False)
        common.validateOptionalStr(name='reference', value=reference, allowEmpty=False)

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

# TODO: This is ugly and I can probably get rid of it by spitting out
# the individual components
class RawSources(object):
    def __init__(
            self,
            credits: typing.Optional[str],
            primary: typing.Optional[RawSource],
            products: typing.Optional[typing.Sequence[RawSource]]
            ) -> None:
        super().__init__()

        common.validateOptionalStr(name='credits', value=credits, allowEmpty=False)
        common.validateOptionalObject(name='primary', value=primary, type=RawSource)
        common.validateOptionalCollection(name='products', value=products, type=RawSource)

        self._credits = credits
        self._primary = primary
        self._products = list(products) if products is not None else None

    def credits(self) -> typing.Optional[str]:
        return self._credits

    def primary(self) -> typing.Optional[RawSource]:
        return self._primary

    def products(self) -> typing.Optional[typing.Sequence[RawSource]]:
        return common.ConstSequenceRef(self._products) if self._products is not None else None

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
            tags: typing.Optional[str],
            allegiances: typing.Optional[typing.Sequence[RawAllegiance]],
            routes: typing.Optional[typing.Sequence[RawRoute]],
            borders: typing.Optional[typing.Sequence[RawBorder]],
            labels: typing.Optional[typing.Sequence[RawLabel]],
            regions: typing.Optional[typing.Sequence[RawRegion]],
            sources: typing.Optional[RawSources],
            styleSheet: typing.Optional[str]
            ) -> None:
        super().__init__()

        common.validateMandatoryInt(name='x', value=x)
        common.validateMandatoryInt(name='y', value=y)
        common.validateMandatoryStr(name='canonicalName', value=canonicalName, allowEmpty=False)
        common.validateOptionalCollection(name='alternateNames', value=alternateNames)
        # TODO: Need a way to validate the nameLanguages map
        common.validateOptionalStr(name='abbreviation', value=abbreviation, allowEmpty=False)
        common.validateOptionalStr(name='sectorLabel', value=sectorLabel, allowEmpty=False)
        # TODO: Need a way to validate the subsectorNames map
        common.validateOptionalBool(name='selected', value=selected)
        common.validateOptionalStr(name='tags', value=tags, allowEmpty=False)
        common.validateOptionalCollection(name='allegiances', value=allegiances, type=RawAllegiance)
        common.validateOptionalCollection(name='routes', value=routes, type=RawRoute)
        common.validateOptionalCollection(name='borders', value=borders, type=RawBorder)
        common.validateOptionalCollection(name='labels', value=labels, type=RawLabel)
        common.validateOptionalCollection(name='regions', value=regions, type=RawRegion)
        common.validateOptionalObject(name='sources', value=sources, type=RawSources)
        common.validateOptionalStr(name='styleSheet', value=styleSheet, allowEmpty=False)

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

    # TODO: I need a an equivalent of ConstSequenceRef for mappings
    # _or_ I need to change how this works (I'm not a massive fan of
    # it, maybe switch to a RawSectorName object)
    def nameLanguages(self) -> typing.Mapping[str, str]:
        return self._nameLanguages

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def sectorLabel(self) -> typing.Optional[str]:
        return self._sectorLabel

    # TODO: I'm not a massive fan of using a mapping. Would probably
    # be better to create a RawSubsectorName object and just have
    # a list of them
    def subsectorNames(self) -> typing.Optional[typing.Mapping[str, str]]:
        return self._subsectorNames

    def selected(self) -> typing.Optional[bool]:
        return self._selected

    # TODO: This should probably be split to be held as a list of strings
    def tags(self) -> typing.Optional[str]:
        return self._tags

    def allegiances(self) -> typing.Optional[typing.Sequence[RawAllegiance]]:
        return common.ConstSequenceRef(self._allegiances) if self._allegiances is not None else None

    def routes(self) -> typing.Optional[typing.Sequence[RawRoute]]:
        return common.ConstSequenceRef(self._routes) if self._routes is not None else None

    def borders(self) -> typing.Optional[typing.Sequence[RawBorder]]:
        return common.ConstSequenceRef(self._borders) if self._borders is not None else None

    def labels(self) -> typing.Optional[typing.Sequence[RawLabel]]:
        return common.ConstSequenceRef(self._labels) if self._labels is not None else None

    def regions(self) -> typing.Optional[typing.Sequence[RawRegion]]:
        return common.ConstSequenceRef(self._regions) if self._regions is not None else None

    def sources(self) -> typing.Optional[RawSources]:
        return self._sources

    def styleSheet(self) -> typing.Optional[str]:
        return self._styleSheet

class RawNameInfo(object):
    def __init__(
            self,
            name: str,
            language: typing.Optional[str],
            source: typing.Optional[str]
            ):
        super().__init__()

        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)
        common.validateOptionalStr(name='language', value=language, allowEmpty=False)
        common.validateOptionalStr(name='source', value=source, allowEmpty=False)

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

        common.validateMandatoryInt(name='x', value=x)
        common.validateMandatoryInt(name='y', value=y)
        common.validateMandatoryStr(name='milieu', value=milieu, allowEmpty=False)
        common.validateOptionalStr(name='abbreviation', value=abbreviation, allowEmpty=False)
        common.validateOptionalStr(name='tags', value=tags, allowEmpty=False)
        common.validateOptionalCollection(name='nameInfos', value=nameInfos, type=RawNameInfo)

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

class RawUniverseInfo(object):
    def __init__(
            self,
            sectorInfos: typing.Sequence[RawSectorInfo]
            ) -> None:
        super().__init__()

        common.validateMandatoryCollection(name='sectorInfos', value=sectorInfos, type=RawSectorInfo)

        self._sectorInfos = list(sectorInfos)

    def sectorInfos(self) -> typing.Sequence[RawSectorInfo]:
        return common.ConstSequenceRef(self._sectorInfos)

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

        common.validateMandatoryStr(name='code', value=code, allowEmpty=False)
        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)
        common.validateMandatoryStr(name='legacy', value=legacy, allowEmpty=False)
        common.validateOptionalStr(name='base', value=base, allowEmpty=False)
        common.validateOptionalStr(name='location', value=location, allowEmpty=False)

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

        common.validateMandatoryStr(name='code', value=code, allowEmpty=False)
        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)
        common.validateOptionalStr(name='location', value=location, allowEmpty=False)

        self._code = code
        self._name = name
        self._location = location

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def location(self) -> str:
        return self._location

class RawRouteStyle(object):
    def __init__(
            self,
            tag: typing.Optional[str], # None means this is a default style
            colour: typing.Optional[str],
            style: typing.Optional[str],
            width: typing.Optional[float],
            ) -> None:
        super().__init__()

        common.validateOptionalStr(name='tag', value=tag, allowEmpty=False)
        common.validateOptionalHtmlColour(name='colour', value=colour)
        survey.validateOptionalLineStyle(name='style', value=style)
        common.validateOptionalFloat(name='width', value=width, min=0)

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

        common.validateOptionalStr(name='tag', value=tag, allowEmpty=False)
        common.validateOptionalHtmlColour(name='colour', value=colour)
        survey.validateOptionalLineStyle(name='style', value=style)

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

        common.validateMandatoryCollection(name='routeStyles', value=routeStyles, type=RawRouteStyle)
        common.validateMandatoryCollection(name='borderStyles', value=borderStyles, type=RawBorderStyle)

        self._routeStyles = list(routeStyles)
        self._borderStyles = list(borderStyles)

    def routeStyles(self) -> typing.Sequence[RawRouteStyle]:
        return common.ConstSequenceRef(self._routeStyles)

    def borderStyles(self) -> typing.Sequence[RawBorderStyle]:
        return common.ConstSequenceRef(self._borderStyles)