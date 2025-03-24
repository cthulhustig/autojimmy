import logging
import maprenderer
import traveller
import travellermap
import typing

class AllegianceCache(object):
    _DefaultAllegiances = set([
        'Im', # Classic Imperium
        'ImAp', # Third Imperium, Amec Protectorate (Dagu)
        'ImDa', # Third Imperium, Domain of Antares (Anta/Empt/Lish)
        'ImDc', # Third Imperium, Domain of Sylea (Core/Delp/Forn/Mass)
        'ImDd', # Third Imperium, Domain of Deneb (Dene/Reft/Spin/Troj)
        'ImDg', # Third Imperium, Domain of Gateway (Glim/Hint/Ley)
        'ImDi', # Third Imperium, Domain of Ilelish (Daib/Ilel/Reav/Verg/Zaru)
        'ImDs', # Third Imperium, Domain of Sol (Alph/Dias/Magy/Olde/Solo)
        'ImDv', # Third Imperium, Domain of Vland (Corr/Dagu/Gush/Reft/Vlan)
        'ImLa', # Third Imperium, League of Antares (Anta)
        'ImLc', # Third Imperium, Lancian Cultural Region (Corr/Dagu/Gush)
        'ImLu', # Third Imperium, Luriani Cultural Association (Ley/Forn)
        'ImSy', # Third Imperium, Sylean Worlds (Core)
        'ImVd', # Third Imperium, Vegan Autonomous District (Solo)
        'XXXX', # Unknown
        '??', # Placeholder - show as blank
        '--', # Placeholder - show as blank
    ])

    # TODO: I think this is actually the same data that AllegianceManager loads
    # from allegiance.json. This file was taken directly from the Traveller Map
    # source code where as I __think__ the other one was exported using the API.
    # I should update AllegianceManager to use this copy as it will be easier
    # to maintain as I'm already going to have to pull snapshots of other files
    # from the traveller map source code periodically
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

    def __init__(self):
        self._allegiancesMap: typing.Optional[typing.Dict[
            str, # T5 Code
            str # Legacy Code
            ]] = {}
        self._loadData()

    def allegianceCode(self, world: traveller.World, useLegacy: bool, ignoreDefault: bool = False) -> str:
        allegiance = world.allegiance()
        if ignoreDefault and (allegiance in AllegianceCache._DefaultAllegiances):
            return None
        if useLegacy and self._allegiancesMap:
            allegiance = self._allegiancesMap.get(allegiance, allegiance)
        return allegiance

    def _loadData(self) -> None:
        self._allegiancesMap.clear()

        _, rows = maprenderer.parseTabContent(
            content=travellermap.DataStore.instance().loadTextResource(
                filePath=AllegianceCache._T5OfficialAllegiancesPath))
        for data in rows:
            code = data.get('Code')
            legacy = data.get('Legacy')
            self._allegiancesMap[code] = legacy
        for code, legacy in AllegianceCache._T5UnofficialAllegiances.items():
            if code in self._allegiancesMap:
                # Official takes presence in case of conflict
                if legacy != self._allegiancesMap[code]:
                    logging.warning(
                        'AllegianceCache ignoring unofficial "{code}={unofficial}" mapping due to conflict with official mapping "{code}={official}"'.format(
                            code=code,
                            unofficial=legacy,
                            official=self._allegiancesMap[code]))
                continue
            self._allegiancesMap[code] = legacy