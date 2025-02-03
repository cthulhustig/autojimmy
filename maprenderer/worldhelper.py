import maprenderer
import os
import traveller
import typing

class WorldHelper(object):
    # Traveller Map doesn't use trade codes for things you might expect it
    # would. Instead it has it's own logic based on UWP. Best guess is this is
    # to support older sector data that might not have trade codes
    _HighPopulation = 9
    _AgriculturalAtmospheres = set([4, 5, 6, 7, 8, 9])
    _AgriculturalHydrographics = set([4, 5, 6, 7, 8])
    _AgriculturalPopulations = set([5, 6, 7])
    _IndustrialAtmospheres = set([0, 1, 2, 4, 7, 9, 10, 11, 12])
    _IndustrialMinPopulation = 9
    _RichAtmospheres = set([6, 8])
    _RichPopulations = set([6, 7, 8])

    _DefaultAllegiances = set([
        "Im", # Classic Imperium
        "ImAp", # Third Imperium, Amec Protectorate (Dagu)
        "ImDa", # Third Imperium, Domain of Antares (Anta/Empt/Lish)
        "ImDc", # Third Imperium, Domain of Sylea (Core/Delp/Forn/Mass)
        "ImDd", # Third Imperium, Domain of Deneb (Dene/Reft/Spin/Troj)
        "ImDg", # Third Imperium, Domain of Gateway (Glim/Hint/Ley)
        "ImDi", # Third Imperium, Domain of Ilelish (Daib/Ilel/Reav/Verg/Zaru)
        "ImDs", # Third Imperium, Domain of Sol (Alph/Dias/Magy/Olde/Solo)
        "ImDv", # Third Imperium, Domain of Vland (Corr/Dagu/Gush/Reft/Vlan)
        "ImLa", # Third Imperium, League of Antares (Anta)
        "ImLc", # Third Imperium, Lancian Cultural Region (Corr/Dagu/Gush)
        "ImLu", # Third Imperium, Luriani Cultural Association (Ley/Forn)
        "ImSy", # Third Imperium, Sylean Worlds (Core)
        "ImVd", # Third Imperium, Vegan Autonomous District (Solo)
        "XXXX", # Unknown
        "??", # Placeholder - show as blank
        "--", # Placeholder - show as blank
    ])

    _T5OfficialAllegiancesPath = 'res/t5ss/allegiance_codes.tab'
    _T5UnofficialAllegiances = {
            # -----------------------
            # Unofficial/Unreviewed
            # -----------------------

            # M1120
            'FdAr': 'Fa',
            'BoWo': 'Bw',
            'LuIm': 'Li',
            'MaSt': 'Ma',
            'BaCl': 'Bc',
            'FdDa': 'Fd',
            'FdIl': 'Fi',
            'AvCn': 'Ac',
            'CoAl': 'Ca',
            'StIm': 'St',
            'ZiSi': 'Rv', # Ziru Sirka
            'VA16': 'V6',
            'CRVi': 'CV',
            'CRGe': 'CG',
            'CRSu': 'CS',
            'CRAk': 'CA'
    }
    _T5AllegiancesMap: typing.Optional[typing.Dict[
        str, # Code
        str # Legacy Code
        ]] = None

    _HydrographicsImageMap = {
        0x1: 'Hyd1',
        0x2: 'Hyd2',
        0x3: 'Hyd3',
        0x4: 'Hyd4',
        0x5: 'Hyd5',
        0x6: 'Hyd6',
        0x7: 'Hyd7',
        0x8: 'Hyd8',
        0x9: 'Hyd9',
        0xA: 'HydA',
    }
    _HydrographicsDefaultImage = 'Hyd0'

    @staticmethod
    def loadData(basePath: str) -> None:
        if WorldHelper._T5AllegiancesMap is not None:
            return # Already loaded
        WorldHelper._T5AllegiancesMap = {}

        _, rows = maprenderer.loadTabFile(path=os.path.join(basePath, WorldHelper._T5OfficialAllegiancesPath))
        for data in rows:
            code = data.get('Code')
            legacy = data.get('Legacy')
            WorldHelper._T5AllegiancesMap[code] = legacy
        for code, legacy in WorldHelper._T5UnofficialAllegiances.items():
            WorldHelper._T5AllegiancesMap[code] = legacy

    @staticmethod
    def hasWater(world: traveller.World) -> bool:
        return world.hasWaterRefuelling()

    @staticmethod
    def hasGasGiants(world: traveller.World) -> bool:
        return world.hasGasGiantRefuelling()

    @staticmethod
    def isHighPopulation(world: traveller.World) -> bool:
        uwp = world.uwp()
        population = uwp.numeric(element=traveller.UWP.Element.Population, default=-1)
        return population >= WorldHelper._HighPopulation

    @staticmethod
    def isAgricultural(world: traveller.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1)
        hydrographics = uwp.numeric(element=traveller.UWP.Element.Hydrographics, default=-1)
        population = uwp.numeric(element=traveller.UWP.Element.Population, default=-1)
        return atmosphere in WorldHelper._AgriculturalAtmospheres and \
            hydrographics in WorldHelper._AgriculturalHydrographics and \
            population in WorldHelper._AgriculturalPopulations

    @staticmethod
    def isIndustrial(world: traveller.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1)
        population = uwp.numeric(element=traveller.UWP.Element.Population, default=-1)
        return atmosphere in WorldHelper._IndustrialAtmospheres and \
            population >= WorldHelper._IndustrialMinPopulation

    @staticmethod
    def isRich(world: traveller.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1)
        population = uwp.numeric(element=traveller.UWP.Element.Population, default=-1)
        return atmosphere in WorldHelper._RichAtmospheres and \
            population in WorldHelper._RichPopulations

    @staticmethod
    def isVacuum(world: traveller.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1)
        return atmosphere == 0

    @staticmethod
    def isCapital(world: traveller.World) -> bool:
        # TODO: Need to check "Capital" support is working
        return world.hasTradeCode(traveller.TradeCode.SectorCapital) or \
            world.hasTradeCode(traveller.TradeCode.SubsectorCapital) or \
            world.hasTradeCode(traveller.TradeCode.ImperialCapital) or \
            world.hasRemark('Capital')

    @staticmethod
    def allegianceCode(world: traveller.World, ignoreDefault: bool, useLegacy: bool) -> str:
        allegiance = world.allegiance()
        if ignoreDefault and (allegiance in WorldHelper._DefaultAllegiances):
            return None
        if useLegacy and WorldHelper._T5AllegiancesMap:
            allegiance = WorldHelper._T5AllegiancesMap.get(allegiance, allegiance)
        return allegiance

    @staticmethod
    def worldImage(
            world: traveller.World,
            images: maprenderer.ImageCache
            ) -> maprenderer.AbstractImage:
        uwp = world.uwp()
        size = uwp.numeric(element=traveller.UWP.Element.WorldSize, default=-1)
        if size <= 0:
            return images.worldImages['Belt']

        hydrographics = uwp.numeric(element=traveller.UWP.Element.Hydrographics, default=-1)
        return images.worldImages[
            WorldHelper._HydrographicsImageMap.get(hydrographics, WorldHelper._HydrographicsDefaultImage)]