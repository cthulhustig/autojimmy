import app
import enum
import gui
import json
import logging
import logic
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class HexTableTabBar(gui.TabBarEx):
    class DisplayMode(enum.Enum):
        AllColumns = 0
        SystemColumns = 1
        UWPColumns = 2
        EconomicsColumns = 3
        CultureColumns = 4
        RefuellingColumns = 5

    # TODO: This might need to stay as WorldTableTabBar_v1 for backwards
    # compatibility
    _StateVersion = 'HexTableTabBar_v1'

    def __init__(self) -> None:
        tabs = [
            (HexTableTabBar.DisplayMode.AllColumns, 'All'),
            (HexTableTabBar.DisplayMode.SystemColumns, 'System'),
            (HexTableTabBar.DisplayMode.UWPColumns, 'UWP'),
            (HexTableTabBar.DisplayMode.EconomicsColumns, 'Economics'),
            (HexTableTabBar.DisplayMode.CultureColumns, 'Culture'),
            (HexTableTabBar.DisplayMode.RefuellingColumns, 'Refuelling'),
        ]
        super().__init__()
        for index, (mode, text) in enumerate(tabs):
            self.addTab(text)
            self.setTabData(index, mode)

    def currentDisplayMode(self) -> DisplayMode:
        return self.tabData(self.currentIndex())

    def setCurrentDisplayMode(
            self,
            displayMode: DisplayMode
            ) -> None:
        for index in range(self.count()):
            if displayMode == self.tabData(index):
                self.setCurrentIndex(index)
                return

    def saveState(self) -> QtCore.QByteArray:
        displayMode = self.currentDisplayMode()
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(HexTableTabBar._StateVersion)
        stream.writeQString(displayMode.name)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> None:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != HexTableTabBar._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore HexTableTabBar state (Incorrect version)')
            return False

        name = stream.readQString()
        if name not in self.DisplayMode.__members__:
            logging.warning(f'Failed to restore HexTableTabBar state (Unknown DisplayMode "{name}")')
            return False
        self.setCurrentDisplayMode(self.DisplayMode.__members__[name])
        return True

class HexTable(gui.FrozenColumnListTable):
    class ColumnType(enum.Enum):
        Name = 'Name'
        Sector = 'Sector'
        Zone = 'Zone'
        Allegiance = 'Allegiance'
        PopulationCount = 'Population\n(Count)'
        StarPort = 'Star Port\n(ehex)'
        TechLevel = 'Tech Level\n(ehex)'
        LawLevel = 'Law Level\n(ehex)'
        Population = 'Population\n(ehex)'
        Government = 'Government\n(ehex)'
        WorldSize = 'World Size\n(ehex)'
        Atmosphere = 'Atmosphere\n(ehex)'
        Hydrographics = 'Hydrographics\n(ehex)'
        Resources = 'Resources\n(ehex)'
        Labour = 'Labour\n(ehex)'
        Infrastructure = 'Infrastructure\n(ehex)'
        Efficiency = 'Efficiency\n(ehex)'
        Heterogeneity = 'Heterogeneity\n(ehex)'
        Acceptance = 'Acceptance\n(ehex)'
        Strangeness = 'Strangeness\n(ehex)'
        Symbols = 'Symbols\n(ehex)'
        Nobilities = 'Nobilities'
        Sophont = 'Sophont'
        TradeCodes = 'Trade Codes'
        PopulationMultiplier = 'Population\nMultiplier'
        PlanetoidBeltCount = 'Planetoid Belts\n(Count)'
        GasGiantCount = 'Gas Giants\n(Count)'
        StarCount = 'Stars\n(Count)'
        SystemWorldCount = 'System Worlds\n(Count)'
        StarPortRefuelling = 'Star Ports\nRefuelling'
        GasGiantRefuelling = 'Gas Giant\nRefuelling'
        WaterRefuelling = 'Water\nRefuelling'
        FuelCache = 'Fuel\nCache'
        Anomaly = 'Anomaly'
        Bases = 'Bases'
        ScoutBase = 'Scout Base'
        MilitaryBase = 'Military Base'
        OwnerWorld = 'Owner'
        ColonyWorlds = 'Colonies\n(Count)'
        Remarks = 'Remarks'

    AllColumns = [
        ColumnType.Name,
        ColumnType.Sector,
        ColumnType.Zone,
        ColumnType.Allegiance,
        ColumnType.PopulationCount,
        ColumnType.StarPort,
        ColumnType.TechLevel,
        ColumnType.LawLevel,
        ColumnType.Population,
        ColumnType.Government,
        ColumnType.WorldSize,
        ColumnType.Atmosphere,
        ColumnType.Hydrographics,
        ColumnType.Resources,
        ColumnType.Labour,
        ColumnType.Infrastructure,
        ColumnType.Efficiency,
        ColumnType.Heterogeneity,
        ColumnType.Acceptance,
        ColumnType.Strangeness,
        ColumnType.Symbols,
        ColumnType.Nobilities,
        ColumnType.Sophont,
        ColumnType.TradeCodes,
        ColumnType.PopulationMultiplier,
        ColumnType.PlanetoidBeltCount,
        ColumnType.GasGiantCount,
        ColumnType.StarCount,
        ColumnType.SystemWorldCount,
        ColumnType.StarPortRefuelling,
        ColumnType.GasGiantRefuelling,
        ColumnType.WaterRefuelling,
        ColumnType.FuelCache,
        ColumnType.Bases,
        ColumnType.ScoutBase,
        ColumnType.MilitaryBase,
        ColumnType.OwnerWorld,
        ColumnType.ColonyWorlds,
        ColumnType.Anomaly,
        ColumnType.Remarks
    ]

    SystemColumns = [
        ColumnType.Name,
        ColumnType.Sector,
        ColumnType.Zone,
        ColumnType.Allegiance,
        ColumnType.PopulationCount,
        ColumnType.Nobilities,
        ColumnType.Sophont,
        ColumnType.TradeCodes,
        ColumnType.StarCount,
        ColumnType.SystemWorldCount,
        ColumnType.PlanetoidBeltCount,
        ColumnType.GasGiantCount,
        ColumnType.Bases,
        ColumnType.ScoutBase,
        ColumnType.MilitaryBase,
        ColumnType.OwnerWorld,
        ColumnType.ColonyWorlds,
        ColumnType.Anomaly,
    ]

    UWPColumns = [
        ColumnType.Name,
        ColumnType.Sector,
        ColumnType.StarPort,
        ColumnType.WorldSize,
        ColumnType.Atmosphere,
        ColumnType.Hydrographics,
        ColumnType.Population,
        ColumnType.Government,
        ColumnType.LawLevel,
        ColumnType.TechLevel
    ]

    EconomicsColumns = [
        ColumnType.Name,
        ColumnType.Sector,
        ColumnType.Resources,
        ColumnType.Labour,
        ColumnType.Infrastructure,
        ColumnType.Efficiency
    ]

    CultureColumns = [
        ColumnType.Name,
        ColumnType.Sector,
        ColumnType.Heterogeneity,
        ColumnType.Acceptance,
        ColumnType.Strangeness,
        ColumnType.Symbols
    ]

    PBGColumns = [
        ColumnType.PopulationMultiplier,
        ColumnType.PlanetoidBeltCount,
        ColumnType.GasGiantCount
    ]

    RefuellingColumns = [
        ColumnType.Name,
        ColumnType.Sector,
        ColumnType.StarPortRefuelling,
        ColumnType.GasGiantRefuelling,
        ColumnType.WaterRefuelling,
        ColumnType.FuelCache,
        ColumnType.StarPort,
        ColumnType.GasGiantCount,
        ColumnType.Hydrographics,
        ColumnType.Atmosphere,
    ]

    # Version 1 format used a world list rather than a hex list. I can't
    # remember why this was just 'v1' rather than 'WorldTable_v1' as would
    # be consistent with other widgets, possibly just because this was pretty
    # much the first table I created way back when
    _LegacyContentV1 = 'v1'
    # Version 2 format was added when the table was switched from using worlds
    # to hexes as part of support for dead space routing
    _ContentVersion = 'HexTable_v2'

    def __init__(
            self,
            columns: typing.Iterable[ColumnType] = AllColumns
            ) -> None:
        super().__init__()

        self.setColumnHeaders(columns)
        self.resizeColumnsToContents() # Size columns to header text
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)

        for index, column in enumerate(columns):
            if column == self.ColumnType.Name or column == self.ColumnType.Sector:
                self.setColumnWidth(index, 100)

    # TODO: It would be nice to get rid of the world versions of all these
    # functions so the external interface only deals in hexes
    def hex(self, row: int) -> typing.Optional[travellermap.HexPosition]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)[0]

    def world(self, row: int) -> typing.Optional[traveller.World]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)[1]

    def hexes(self) -> typing.List[travellermap.HexPosition]:
        hexes = []
        for row in range(self.rowCount()):
            hexes.append(self.hex(row))
        return hexes

    def worlds(self) -> typing.List[traveller.World]:
        worlds = []
        for row in range(self.rowCount()):
            worlds.append(self.world(row))
        return worlds

    def hexAt(self, position: QtCore.QPoint) -> typing.Optional[traveller.World]:
        item = self.itemAt(position)
        if not item:
            return None
        return self.hex(item.row())

    def worldAt(self, position: QtCore.QPoint) -> typing.Optional[traveller.World]:
        item = self.itemAt(position)
        if not item:
            return None
        return self.world(item.row())

    def insertHex(
            self,
            row: int,
            pos: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> int:
        self.insertRow(row)
        if isinstance(pos, traveller.World):
            world = pos
            pos = world.hexPosition()
        else:
            world = traveller.WorldManager.instance().worldByPosition(pos=pos)
        return self._fillRow(row, pos, world)

    # TODO: This feels a little pointless. I could switch calls
    # to it for calls to insertHex.
    # - IMPORTANT: Remember to update the variable name used in calls
    #   from world to pos
    def insertWorld(self, row: int, world: traveller.World) -> int:
        return self.insertHex(row, world)

    def setHex(
            self,
            row: int,
            pos: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> int:
        if isinstance(pos, traveller.World):
            world = pos
            pos = world.hexPosition()
        else:
            world = traveller.WorldManager.instance().worldByPosition(pos=pos)
        return self._fillRow(row, pos, world)

    # TODO: This feels a little pointless. I could switch calls
    # to it for calls to setHex.
    # - IMPORTANT: Remember to update the variable name used in calls
    #   from world to pos
    def setWorld(self, row: int, world: traveller.World) -> int:
        return self.setHex(row, world)

    def setHexes(
            self,
            positions: typing.Iterator[
                typing.Union[travellermap.HexPosition, traveller.World]
            ]) -> None:
        self.removeAllRows()
        for pos in positions:
            self.addHex(pos)

    # TODO: This feels a little pointless. I could switch calls
    # to it for calls to setHexes.
    # - IMPORTANT: Remember to update the variable name used in calls
    #   from world to pos
    def setWorlds(
            self,
            positions: typing.Iterator[traveller.World]
            ) -> None:
        self.setHexes(positions)

    def addHex(
            self,
            pos: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> int:
        return self.insertHex(self.rowCount(), pos)

    # TODO: This feels a little pointless. I could switch calls
    # to it for calls to addHex.
    # - IMPORTANT: Remember to update the variable name used in calls
    #   from world to pos
    def addWorld(self, world: traveller.World) -> int:
        return self.addHex(world)

    def addHexes(
            self,
            positions: typing.Iterable[
                typing.Union[travellermap.HexPosition, traveller.World]
                ]) -> None:
        # Disable sorting while inserting multiple rows then sort once after they've
        # all been added
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for pos in positions:
                self.insertHex(self.rowCount(), pos)
        finally:
            self.setSortingEnabled(sortingEnabled)

    # TODO: This feels a little pointless. I could switch calls
    # to it for calls to addWorlds.
    # - IMPORTANT: Remember to update the variable name used in calls
    #   from worlds to positions
    def addWorlds(self, worlds: typing.Iterable[traveller.World]) -> None:
        self.addHexes([world.hexPosition() for world in worlds])

    def removeHex(
            self,
            pos: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> bool:
        if isinstance(pos, traveller.World):
            pos = pos.hexPosition()
        removed = False
        for row in range(self.rowCount() - 1, -1, -1):
            if pos == self.hex(row):
                self.removeRow(row)
                removed = True
        return removed

    # TODO: This feels a little pointless. I could switch calls
    # to it for calls to removeHex.
    # - IMPORTANT: Remember to update the variable name used in calls
    #   from worlds to positions
    def removeWorld(self, world: traveller.World) -> bool:
        return self.removeHex(world)

    def currentWorld(self) -> typing.Optional[traveller.World]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.world(row)

    def currentHex(self) -> typing.Optional[travellermap.HexPosition]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.hex(row)

    # TODO: Ideally this should be removed as a return value of
    # None is ambiguity as to if there is no current row or it's
    # dead space with no world
    def currentWorld(self) -> typing.Optional[traveller.World]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.world(row)

    def containsHex(
            self,
            pos: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> bool:
        if isinstance(pos, traveller.World):
            pos = pos.hexPosition()
        for row in range(self.rowCount()):
            if pos == self.hex(row):
                return True
        return False

    def containsWorld(self, world: traveller.World) -> bool:
        return self.containsHex(world)

    def selectedRowCount(self) -> int:
        selection = self.selectedIndexes()
        if not selection:
            return 0
        count = 0
        for index in selection:
            if index.column() == 0:
                count += 1
        return count

    def selectedHexes(self) -> typing.List[travellermap.HexPosition]:
        selection = self.selectedIndexes()
        if not selection:
            return None
        hexes = []
        for index in selection:
            if index.column() == 0:
                hexes.append(self.hex(index.row()))
        return hexes

    # TODO: Ideally this would be removed as it's ambiguous in
    # a similar way to currentWorld
    def selectedWorlds(self) -> typing.List[traveller.World]:
        selection = self.selectedIndexes()
        if not selection:
            return None
        worlds = []
        for index in selection:
            if index.column() == 0:
                world = self.world(index.row())
                worlds.append(world)
        return worlds

    def saveContent(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(HexTable._ContentVersion)

        count = self.rowCount()
        stream.writeUInt32(count)
        for row in range(self.rowCount()):
            pos = self.hex(row)
            stream.writeInt32(pos.absoluteX())
            stream.writeInt32(pos.absoluteY())

        return state

    def restoreContent(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version == HexTable._LegacyContentV1:
            # TODO: Need to test this works ok
            try:
                data = json.loads(stream.readQString())
                worlds = logic.deserialiseWorldList(data=data)
                self.setHexes(positions=[world.hexPosition() for world in worlds])
            except Exception as ex:
                logging.warning(f'Failed to deserialise v1 HexTable content', exc_info=ex)
        elif version == HexTable._ContentVersion:
            count = stream.readUInt32()
            positions = []
            for _ in range(count):
                positions.append(travellermap.HexPosition(
                    absoluteX=stream.readInt32(),
                    absoluteY=stream.readInt32()))
            self.setHexes(positions=positions)
        else:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore HexTable content (Unsupported version)')
            return False

        return True

    def _fillRow(
            self,
            row: int,
            pos: travellermap.HexPosition,
            world: typing.Optional[traveller.World]
            ) -> int:
        # Workaround for the issue covered here, re-enabled after setting items
        # https://stackoverflow.com/questions/7960505/strange-qtablewidget-behavior-not-all-cells-populated-after-sorting-followed-b
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            rules = app.Config.instance().rules()
            uwp = economics = culture = phg = worldTagColour = None
            if world:
                uwp = world.uwp()
                economics = world.economics()
                culture = world.culture()
                pbg = world.pbg()
                worldTagColour = app.tagColour(app.calculateWorldTagLevel(world))

            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)
                tableItem = None
                tagColour = None
                if columnType == self.ColumnType.Name:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, world.name())
                        tagColour = worldTagColour
                    else:
                        hexString = f'{pos.offsetX():02d}{pos.offsetY():02d}'
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, hexString)
                        tagColour = app.tagColour(app.TagLevel.Danger) # Tag dead space as danger level
                elif columnType == self.ColumnType.Sector:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, f'{world.subsectorName()} ({world.sectorName()})')
                        tagColour = worldTagColour
                    else:
                        # TODO: This should include the subsector name in the same way as when there
                        # is a world but I don't think I have code yet that can get a subsector from
                        # a position
                        sector = traveller.WorldManager.instance().sectorByPosition(pos=pos)
                        sectorString = sector.name() if sector else 'Unknown Sector'
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, sectorString)
                        tagColour = app.tagColour(app.TagLevel.Danger) # Tag dead space as danger level
                elif columnType == self.ColumnType.Zone:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, traveller.zoneTypeCode(world.zone()))
                        tagColour = app.tagColour(app.calculateZoneTagLevel(world))
                    else:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Dead Space')
                        tagColour = app.tagColour(app.TagLevel.Danger) # Tag dead space as danger level
                elif columnType == self.ColumnType.StarPort:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.StarPort))
                        tagColour = app.tagColour(app.calculateStarPortTagLevel(world))
                elif columnType == self.ColumnType.TechLevel:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.TechLevel))
                        tagColour = app.tagColour(app.calculateTechLevelTagLevel(world))
                elif columnType == self.ColumnType.LawLevel:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.LawLevel))
                        tagColour = app.tagColour(app.calculateLawLevelTagLevel(world))
                elif columnType == self.ColumnType.Population:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.Population))
                        tagColour = app.tagColour(app.calculatePopulationTagLevel(world))
                elif columnType == self.ColumnType.Government:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.Government))
                        tagColour = app.tagColour(app.calculateGovernmentTagLevel(world))
                elif columnType == self.ColumnType.WorldSize:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.WorldSize))
                        tagColour = app.tagColour(app.calculateWorldSizeTagLevel(world))
                elif columnType == self.ColumnType.Atmosphere:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.Atmosphere))
                        tagColour = app.tagColour(app.calculateAtmosphereTagLevel(world))
                elif columnType == self.ColumnType.Hydrographics:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.Hydrographics))
                        tagColour = app.tagColour(app.calculateHydrographicsTagLevel(world))
                elif columnType == self.ColumnType.StarPortRefuelling:
                    if world:
                        text = ''
                        if world.hasStarPortRefuelling(rules=rules, includeUnrefined=False):
                            text += 'refined'
                        if world.hasStarPortRefuelling(rules=rules, includeRefined=False):
                            if text:
                                text += ' & '
                            text += 'unrefined'
                        if not text:
                            text = 'none'
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setText(text)
                elif columnType == self.ColumnType.GasGiantRefuelling:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setText('yes' if world.hasGasGiantRefuelling() else 'no' )
                elif columnType == self.ColumnType.WaterRefuelling:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setText('yes' if world.hasWaterRefuelling() else 'no' )
                elif columnType == self.ColumnType.FuelCache:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setText('yes' if world.isFuelCache() else 'no' )
                elif columnType == self.ColumnType.Anomaly:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setText('yes' if world.isAnomaly() else 'no' )
                elif columnType == self.ColumnType.Resources:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(traveller.Economics.Element.Resources))
                        tagColour = app.tagColour(app.calculateResourcesTagLevel(world))
                elif columnType == self.ColumnType.Labour:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(traveller.Economics.Element.Labour))
                        tagColour = app.tagColour(app.calculateLabourTagLevel(world))
                elif columnType == self.ColumnType.Infrastructure:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(traveller.Economics.Element.Infrastructure))
                        tagColour = app.tagColour(app.calculateInfrastructureTagLevel(world))
                elif columnType == self.ColumnType.Efficiency:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(traveller.Economics.Element.Efficiency))
                        tagColour = app.tagColour(app.calculateEfficiencyTagLevel(world))
                elif columnType == self.ColumnType.Heterogeneity:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(traveller.Culture.Element.Heterogeneity))
                        tagColour = app.tagColour(app.calculateHeterogeneityTagLevel(world))
                elif columnType == self.ColumnType.Acceptance:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(traveller.Culture.Element.Acceptance))
                        tagColour = app.tagColour(app.calculateAcceptanceTagLevel(world))
                elif columnType == self.ColumnType.Strangeness:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(traveller.Culture.Element.Strangeness))
                        tagColour = app.tagColour(app.calculateStrangenessTagLevel(world))
                elif columnType == self.ColumnType.Symbols:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(traveller.Culture.Element.Symbols))
                        tagColour = app.tagColour(app.calculateSymbolsTagLevel(world))
                elif columnType == self.ColumnType.Nobilities:
                    if world:
                        nobilities = world.nobilities()
                        highestTagLevel = None
                        for nobility in nobilities:
                            tagLevel = app.calculateNobilityTagLevel(nobility)
                            if tagLevel and (not highestTagLevel or highestTagLevel < tagLevel):
                                highestTagLevel = tagLevel
                        tableItem = QtWidgets.QTableWidgetItem(nobilities.string())
                        if highestTagLevel:
                            tagColour = app.tagColour(highestTagLevel)
                elif columnType == self.ColumnType.Allegiance:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, world.allegiance())
                        tagColour = app.tagColour(app.calculateAllegianceTagLevel(world))
                elif columnType == self.ColumnType.Sophont:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        displayText = ''
                        remarks = world.remarks()
                        for sophont in remarks.sophonts():
                            percentage = remarks.sophontPercentage(sophont)
                            displayText += f', {sophont}' if displayText else sophont
                            displayText += f' ({percentage}%)'
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, displayText)
                elif columnType == self.ColumnType.TradeCodes:
                    if world:
                        tableItem = QtWidgets.QTableWidgetItem()
                        displayText = ''
                        for tradeCode in world.tradeCodes():
                            tradeCodeString = traveller.tradeCodeString(tradeCode)
                            displayText += f', {tradeCodeString}' if displayText else tradeCodeString
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, displayText)
                elif columnType == self.ColumnType.PopulationCount:
                    if world:
                        count = world.population()
                        if count >= 0:
                            tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                        else:
                            tableItem = QtWidgets.QTableWidgetItem('?')
                elif columnType == self.ColumnType.PopulationMultiplier:
                    if world:
                        count = traveller.ehexToInteger(
                            value=pbg.code(element=traveller.PBG.Element.PopulationMultiplier),
                            default=None)
                        if count != None:
                            tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                        else:
                            tableItem = QtWidgets.QTableWidgetItem('?')
                elif columnType == self.ColumnType.PlanetoidBeltCount:
                    if world:
                        count = traveller.ehexToInteger(
                            value=pbg.code(element=traveller.PBG.Element.PlanetoidBelts),
                            default=None)
                        if count != None:
                            tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                        else:
                            tableItem = QtWidgets.QTableWidgetItem('?')
                elif columnType == self.ColumnType.GasGiantCount:
                    if world:
                        count = traveller.ehexToInteger(
                            value=pbg.code(element=traveller.PBG.Element.GasGiants),
                            default=None)
                        if count != None:
                            tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                        else:
                            tableItem = QtWidgets.QTableWidgetItem('?')
                elif columnType == self.ColumnType.StarCount:
                    if world:
                        tableItem = gui.FormattedNumberTableWidgetItem(world.numberOfStars())
                elif columnType == self.ColumnType.SystemWorldCount:
                    if world:
                        tableItem = gui.FormattedNumberTableWidgetItem(world.numberOfSystemWorlds())
                elif columnType == self.ColumnType.Bases:
                    if world:
                        bases = world.bases()
                        highestTagLevel = None
                        for base in bases:
                            tagLevel = app.calculateBaseTypeTagLevel(base)
                            if tagLevel and (not highestTagLevel or highestTagLevel < tagLevel):
                                highestTagLevel = tagLevel
                        tableItem = QtWidgets.QTableWidgetItem(bases.string())
                        if highestTagLevel:
                            tagColour = app.tagColour(highestTagLevel)
                elif columnType == self.ColumnType.ScoutBase:
                    if world:
                        bases = world.bases()
                        scoutBases = bases.scoutBases()
                        highestTagLevel = None
                        if scoutBases:
                            for base in scoutBases:
                                tagLevel = app.calculateBaseTypeTagLevel(base)
                                if tagLevel and (not highestTagLevel or highestTagLevel < tagLevel):
                                    highestTagLevel = tagLevel
                        tableItem = QtWidgets.QTableWidgetItem('yes' if scoutBases else 'no')
                        if highestTagLevel:
                            tagColour = app.tagColour(highestTagLevel)
                elif columnType == self.ColumnType.MilitaryBase:
                    if world:
                        bases = world.bases()
                        militaryBases = bases.militaryBases()
                        highestTagLevel = None
                        if militaryBases:
                            for base in militaryBases:
                                tagLevel = app.calculateBaseTypeTagLevel(base)
                                if tagLevel and (not highestTagLevel or highestTagLevel < tagLevel):
                                    highestTagLevel = tagLevel
                        tableItem = QtWidgets.QTableWidgetItem('yes' if militaryBases else 'no')
                        if highestTagLevel:
                            tagColour = app.tagColour(highestTagLevel)
                elif columnType == self.ColumnType.OwnerWorld:
                    if world:
                        ownerString = None
                        tagLevel = None
                        if world.hasOwner():
                            try:
                                ownerWorld = traveller.WorldManager.instance().world(sectorHex=world.ownerSectorHex())
                            except Exception:
                                ownerWorld = None

                            if ownerWorld:
                                ownerString = ownerWorld.name(includeSubsector=True)
                                tagLevel = app.calculateWorldTagLevel(world=ownerWorld)
                            else:
                                # We don't know about this world so just display the sector hex and tag it as danger
                                ownerString = world.ownerSectorHex()
                                tagLevel = app.TagLevel.Danger
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, ownerString)
                        if tagLevel:
                            tagColour = app.tagColour(tagLevel)
                elif columnType == self.ColumnType.ColonyWorlds:
                    if world:
                        highestTagLevel = None
                        for colonySectorHex in world.colonySectorHexes():
                            try:
                                colonyWorld = traveller.WorldManager.instance().world(colonySectorHex)
                            except Exception:
                                colonyWorld = None

                            if colonyWorld:
                                tagLevel = app.calculateWorldTagLevel(world=colonyWorld)
                                if tagLevel and (not highestTagLevel or tagLevel > highestTagLevel):
                                    highestTagLevel = tagLevel
                            else:
                                # We don't know about this world so the tag level is error, no need to continue looking
                                highestTagLevel = app.TagLevel.Danger
                                break
                        tableItem = gui.FormattedNumberTableWidgetItem(world.colonyCount())
                        if highestTagLevel:
                            tagColour = app.tagColour(highestTagLevel)
                elif columnType == self.ColumnType.Remarks:
                    if world:
                        remarks = world.remarks()
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setText(remarks.string())

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, (pos, world))
                    if tagColour:
                        tableItem.setBackground(QtGui.QColor(tagColour))

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row

    def _createToolTip(self, item: QtWidgets.QTableWidgetItem) -> typing.Optional[str]:
        pos = self.hex(item.row())
        if not pos:
            return None
        world = self.world(item.row())
        if not world:
            # TODO: Better tool tip, should include sector hex
            return gui.createStringToolTip('Dead Space')

        columnType = self.columnHeader(item.column())

        if columnType == self.ColumnType.Name or columnType == self.ColumnType.Sector:
            return gui.createWorldToolTip(world)
        elif columnType == self.ColumnType.Zone:
            zone = world.zone()
            if not zone:
                return None
            return gui.createStringToolTip(traveller.zoneTypeName(zone))
        elif columnType == self.ColumnType.StarPort:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.StarPort))
        elif columnType == self.ColumnType.TechLevel:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.TechLevel))
        elif columnType == self.ColumnType.LawLevel:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.LawLevel))
        elif columnType == self.ColumnType.Population:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.Population))
        elif columnType == self.ColumnType.Government:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.Government))
        elif columnType == self.ColumnType.WorldSize:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.WorldSize))
        elif columnType == self.ColumnType.Atmosphere:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.Atmosphere))
        elif columnType == self.ColumnType.Hydrographics:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.Hydrographics))
        elif columnType == self.ColumnType.Resources:
            return gui.createStringToolTip(world.economics().description(traveller.Economics.Element.Resources))
        elif columnType == self.ColumnType.Labour:
            return gui.createStringToolTip(world.economics().description(traveller.Economics.Element.Labour))
        elif columnType == self.ColumnType.Infrastructure:
            return gui.createStringToolTip(world.economics().description(traveller.Economics.Element.Infrastructure))
        elif columnType == self.ColumnType.Efficiency:
            return gui.createStringToolTip(world.economics().description(traveller.Economics.Element.Efficiency))
        elif columnType == self.ColumnType.Heterogeneity:
            return gui.createStringToolTip(world.culture().description(traveller.Culture.Element.Heterogeneity))
        elif columnType == self.ColumnType.Acceptance:
            return gui.createStringToolTip(world.culture().description(traveller.Culture.Element.Acceptance))
        elif columnType == self.ColumnType.Strangeness:
            return gui.createStringToolTip(world.culture().description(traveller.Culture.Element.Strangeness))
        elif columnType == self.ColumnType.Symbols:
            return gui.createStringToolTip(world.culture().description(traveller.Culture.Element.Symbols))
        elif columnType == self.ColumnType.Nobilities:
            lines = []
            lineColours = {}
            nobilities = world.nobilities()
            for nobilityType in nobilities:
                nobilityDescription = traveller.Nobilities.description(nobilityType)
                lines.append(nobilityDescription)

                tagLevel = app.calculateNobilityTagLevel(nobilityType)
                if tagLevel:
                    lineColours[nobilityDescription] = app.tagColour(tagLevel)
            if lines:
                return gui.createListToolTip(
                    title=f'Nobilities: {nobilities.string()}',
                    strings=lines,
                    stringColours=lineColours)
        elif columnType == self.ColumnType.Allegiance:
            allegiance = traveller.AllegianceManager.instance().allegianceName(world)
            if allegiance:
                return gui.createStringToolTip(allegiance)
        elif columnType == self.ColumnType.Sophont:
            lines = []
            remarks = world.remarks()
            for sophont in remarks.sophonts():
                percentage = remarks.sophontPercentage(sophont)
                sophont += f' ({percentage}%)'
                lines.append(sophont)
            if lines:
                return gui.createListToolTip(
                    title='Sophonts:',
                    strings=lines)
        elif columnType == self.ColumnType.TradeCodes:
            lines = []
            for tradeCode in world.tradeCodes():
                lines.append(traveller.tradeCodeName(tradeCode=tradeCode))
            if lines:
                return gui.createListToolTip(
                    title='Trade Codes:',
                    strings=lines)
        elif columnType == self.ColumnType.StarCount:
            lines = []
            lineIndents = {}
            lineColours = {}
            stellar = world.stellar()
            for star in stellar:
                lines.append(f'Classification: {star.string()}')
                spectralClass = f'Spectral Class: {star.code(traveller.Star.Element.SpectralClass)} - {star.description(traveller.Star.Element.SpectralClass)}'
                spectralScale = f'Spectral Scale: {star.code(traveller.Star.Element.SpectralScale)} - {star.description(traveller.Star.Element.SpectralScale)}'
                luminosityClass = f'Luminosity Class: {star.code(traveller.Star.Element.LuminosityClass)} - {star.description(traveller.Star.Element.LuminosityClass)}'
                lines.append(spectralClass)
                lines.append(spectralScale)
                lines.append(luminosityClass)

                # There could be collisions when adding to dicts in the following code as multiple
                # stars can have the same spectral/luminosity text. This isn't an issue though as
                # the mapping value will always be the same for a given piece of text
                lineIndents[spectralClass] = 1
                lineIndents[spectralScale] = 1
                lineIndents[luminosityClass] = 1

                tagLevel = app.calculateSpectralTagLevel(star=star)
                if tagLevel:
                    lineColours[spectralClass] = app.tagColour(tagLevel=tagLevel)

                tagLevel = app.calculateLuminosityTagLevel(star=star)
                if tagLevel:
                    lineColours[luminosityClass] = app.tagColour(tagLevel=tagLevel)

            if lines:
                return gui.createListToolTip(
                    title=f'Stars: {stellar.string()}',
                    strings=lines,
                    stringColours=lineColours,
                    stringIndents=lineIndents)
        elif columnType == self.ColumnType.PopulationCount:
            if world.population() >= 0:
                return None
            return gui.createStringToolTip(string='Unknown')
        elif columnType == self.ColumnType.PopulationMultiplier:
            return gui.createStringToolTip(world.pbg().description(element=traveller.PBG.Element.PopulationMultiplier))
        elif columnType == self.ColumnType.PlanetoidBeltCount:
            return gui.createStringToolTip(world.pbg().description(element=traveller.PBG.Element.PlanetoidBelts))
        elif columnType == self.ColumnType.GasGiantCount:
            return gui.createStringToolTip(world.pbg().description(element=traveller.PBG.Element.GasGiants))
        elif columnType == self.ColumnType.Bases:
            return gui.createBasesToolTip(world=world)
        elif columnType == self.ColumnType.ScoutBase:
            bases = world.bases()
            scoutBases = bases.scoutBases()
            if scoutBases:
                return gui.createBasesToolTip(
                    world=world,
                    includeBaseTypes=scoutBases)
        elif columnType == self.ColumnType.MilitaryBase:
            bases = world.bases()
            militaryBases = bases.militaryBases()
            if militaryBases:
                return gui.createBasesToolTip(
                    world=world,
                    includeBaseTypes=militaryBases)
        elif columnType == self.ColumnType.OwnerWorld:
            if world.hasOwner():
                try:
                    ownerWorld = traveller.WorldManager.instance().world(sectorHex=world.ownerSectorHex())
                except Exception:
                    ownerWorld = None

                if ownerWorld:
                    return gui.createWorldToolTip(world=ownerWorld)
                else:
                    return gui.createStringToolTip(f'Unknown world at {world.ownerSectorHex()}')
        elif columnType == self.ColumnType.ColonyWorlds:
            if world.hasColony():
                listStrings = []
                listColours = {}
                for colonySectorHex in world.colonySectorHexes():
                    try:
                        colonyWorld = traveller.WorldManager.instance().world(sectorHex=colonySectorHex)
                    except Exception:
                        colonyWorld = None

                    if colonyWorld:
                        colonyString = colonyWorld.name(includeSubsector=True)
                        listStrings.append(colonyString)
                        listColours[colonyString] = app.tagColour(
                            tagLevel=app.calculateWorldTagLevel(world=colonyWorld))
                    else:
                        colonyString = f'Unknown world at {colonySectorHex}'
                        listStrings.append(colonyString)
                        listColours[colonyString] = app.tagColour(tagLevel=app.TagLevel.Danger)
                return gui.createListToolTip(
                    title='Colony Worlds',
                    strings=listStrings,
                    stringColours=listColours)
        elif columnType == self.ColumnType.Remarks:
            remarks = world.remarks()
            return gui.createStringToolTip(remarks.string())

        return None
