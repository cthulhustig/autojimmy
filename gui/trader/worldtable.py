import app
import enum
import gui
import json
import logging
import logic
import traveller
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class WorldTableTabBar(gui.TabBarEx):
    class DisplayMode(enum.Enum):
        AllColumns = 0
        SystemColumns = 1
        UWPColumns = 2
        EconomicsColumns = 3
        CultureColumns = 4
        RefuellingColumns = 5

    _StateVersion = 'WorldTableTabBar_v1'

    def __init__(self) -> None:
        tabs = [
            (WorldTableTabBar.DisplayMode.AllColumns, 'All'),
            (WorldTableTabBar.DisplayMode.SystemColumns, 'System'),
            (WorldTableTabBar.DisplayMode.UWPColumns, 'UWP'),
            (WorldTableTabBar.DisplayMode.EconomicsColumns, 'Economics'),
            (WorldTableTabBar.DisplayMode.CultureColumns, 'Culture'),
            (WorldTableTabBar.DisplayMode.RefuellingColumns, 'Refuelling'),
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
        stream.writeQString(WorldTableTabBar._StateVersion)
        stream.writeQString(displayMode.name)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> None:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != WorldTableTabBar._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore WorldTableTabBar state (Incorrect version)')
            return False

        name = stream.readQString()
        if name not in self.DisplayMode.__members__:
            logging.warning(f'Failed to restore WorldTableTabBar state (Unknown DisplayMode "{name}")')
            return False
        self.setCurrentDisplayMode(self.DisplayMode.__members__[name])
        return True

class WorldTable(gui.FrozenColumnListTable):
    class ColumnType(enum.Enum):
        World = 'World'
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
        ColumnType.World,
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
        ColumnType.World,
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
        ColumnType.World,
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
        ColumnType.World,
        ColumnType.Sector,
        ColumnType.Resources,
        ColumnType.Labour,
        ColumnType.Infrastructure,
        ColumnType.Efficiency
    ]

    CultureColumns = [
        ColumnType.World,
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
        ColumnType.World,
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

    _ContentVersion = 'v1'

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
            if column == self.ColumnType.World or column == self.ColumnType.Sector:
                self.setColumnWidth(index, 100)

    def world(self, row: int) -> typing.Optional[traveller.World]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)

    def worlds(self) -> typing.List[traveller.World]:
        worlds = []
        for row in range(self.rowCount()):
            world = self.world(row)
            if not world:
                continue
            worlds.append(world)
        return worlds

    def worldAt(self, position: QtCore.QPoint) -> typing.Optional[traveller.World]:
        item = self.itemAt(position)
        if not item:
            return None
        return self.world(item.row())

    def insertWorld(self, row: int, world: traveller.World) -> int:
        self.insertRow(row)
        return self._fillRow(row, world)

    def setWorld(self, row: int, world: traveller.World) -> int:
        return self._fillRow(row, world)

    def addWorld(self, world: traveller.World) -> int:
        return self.insertWorld(self.rowCount(), world)

    def addWorlds(self, worlds: typing.Iterable[traveller.World]) -> None:
        # Disable sorting while inserting multiple rows then sort once after they've
        # all been added
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for world in worlds:
                self.insertWorld(self.rowCount(), world)
        finally:
            self.setSortingEnabled(sortingEnabled)

    def removeWorld(self, world: traveller.World) -> bool:
        removed = False
        for row in range(self.rowCount() - 1, -1, -1):
            if world == self.world(row):
                self.removeRow(row)
                removed = True
        return removed

    def currentWorld(self) -> typing.Optional[traveller.World]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.world(row)

    def containsWorld(self, world: traveller.World) -> bool:
        for row in range(self.rowCount()):
            compareWorld = self.world(row)
            if compareWorld == world:
                return True
        return False

    def selectedRowCount(self) -> int:
        selection = self.selectedIndexes()
        if not selection:
            return 0
        count = 0
        for index in selection:
            if index.column() == 0:
                count += 1
        return count

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
        stream.writeQString(WorldTable._ContentVersion)

        data = logic.serialiseWorldList(worldList=self.worlds())
        stream.writeQString(json.dumps(data))

        return state

    def restoreContent(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != WorldTable._ContentVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore WorldTable content (Incorrect version)')
            return False

        try:
            data = json.loads(stream.readQString())
            worldList = logic.deserialiseWorldList(data=data)
            self.addWorlds(worlds=worldList)
        except Exception as ex:
            logging.warning(f'Failed to deserialise WorldTable content', exc_info=ex)
            return False

        return True

    def _fillRow(
            self,
            row: int,
            world: traveller.World
            ) -> int:
        # Workaround for the issue covered here, re-enabled after setting items
        # https://stackoverflow.com/questions/7960505/strange-qtablewidget-behavior-not-all-cells-populated-after-sorting-followed-b
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            uwp = world.uwp()
            economics = world.economics()
            culture = world.culture()
            pbg = world.pbg()
            worldTagColour = app.tagColour(app.calculateWorldTagLevel(world))
            rules = app.Config.instance().rules()

            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)
                tableItem = None
                tagColour = None
                if columnType == self.ColumnType.World:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, world.name())
                    tagColour = worldTagColour
                elif columnType == self.ColumnType.Sector:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, f'{world.subsectorName()} ({world.sectorName()})')
                    tagColour = worldTagColour
                elif columnType == self.ColumnType.Zone:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, traveller.zoneTypeCode(world.zone()))
                    tagColour = app.tagColour(app.calculateZoneTagLevel(world))
                elif columnType == self.ColumnType.StarPort:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.StarPort))
                    tagColour = app.tagColour(app.calculateStarPortTagLevel(world))
                elif columnType == self.ColumnType.TechLevel:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.TechLevel))
                    tagColour = app.tagColour(app.calculateTechLevelTagLevel(world))
                elif columnType == self.ColumnType.LawLevel:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.LawLevel))
                    tagColour = app.tagColour(app.calculateLawLevelTagLevel(world))
                elif columnType == self.ColumnType.Population:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.Population))
                    tagColour = app.tagColour(app.calculatePopulationTagLevel(world))
                elif columnType == self.ColumnType.Government:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.Government))
                    tagColour = app.tagColour(app.calculateGovernmentTagLevel(world))
                elif columnType == self.ColumnType.WorldSize:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.WorldSize))
                    tagColour = app.tagColour(app.calculateWorldSizeTagLevel(world))
                elif columnType == self.ColumnType.Atmosphere:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.Atmosphere))
                    tagColour = app.tagColour(app.calculateAtmosphereTagLevel(world))
                elif columnType == self.ColumnType.Hydrographics:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.Hydrographics))
                    tagColour = app.tagColour(app.calculateHydrographicsTagLevel(world))
                elif columnType == self.ColumnType.StarPortRefuelling:
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
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setText('yes' if world.hasGasGiantRefuelling() else 'no' )
                elif columnType == self.ColumnType.WaterRefuelling:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setText('yes' if world.hasWaterRefuelling() else 'no' )
                elif columnType == self.ColumnType.FuelCache:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setText('yes' if world.isFuelCache() else 'no' )
                elif columnType == self.ColumnType.Anomaly:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setText('yes' if world.isAnomaly() else 'no' )                    
                elif columnType == self.ColumnType.Resources:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(traveller.Economics.Element.Resources))
                    tagColour = app.tagColour(app.calculateResourcesTagLevel(world))
                elif columnType == self.ColumnType.Labour:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(traveller.Economics.Element.Labour))
                    tagColour = app.tagColour(app.calculateLabourTagLevel(world))
                elif columnType == self.ColumnType.Infrastructure:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(traveller.Economics.Element.Infrastructure))
                    tagColour = app.tagColour(app.calculateInfrastructureTagLevel(world))
                elif columnType == self.ColumnType.Efficiency:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(traveller.Economics.Element.Efficiency))
                    tagColour = app.tagColour(app.calculateEfficiencyTagLevel(world))
                elif columnType == self.ColumnType.Heterogeneity:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(traveller.Culture.Element.Heterogeneity))
                    tagColour = app.tagColour(app.calculateHeterogeneityTagLevel(world))
                elif columnType == self.ColumnType.Acceptance:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(traveller.Culture.Element.Acceptance))
                    tagColour = app.tagColour(app.calculateAcceptanceTagLevel(world))
                elif columnType == self.ColumnType.Strangeness:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(traveller.Culture.Element.Strangeness))
                    tagColour = app.tagColour(app.calculateStrangenessTagLevel(world))
                elif columnType == self.ColumnType.Symbols:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(traveller.Culture.Element.Symbols))
                    tagColour = app.tagColour(app.calculateSymbolsTagLevel(world))
                elif columnType == self.ColumnType.Nobilities:
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
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, world.allegiance())
                    tagColour = app.tagColour(app.calculateAllegianceTagLevel(world))
                elif columnType == self.ColumnType.Sophont:
                    tableItem = QtWidgets.QTableWidgetItem()
                    displayText = ''
                    remarks = world.remarks()
                    for sophont in remarks.sophonts():
                        percentage = remarks.sophontPercentage(sophont)
                        displayText += f', {sophont}' if displayText else sophont
                        displayText += f' ({percentage}%)'
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, displayText)
                elif columnType == self.ColumnType.TradeCodes:
                    tableItem = QtWidgets.QTableWidgetItem()
                    displayText = ''
                    for tradeCode in world.tradeCodes():
                        tradeCodeString = traveller.tradeCodeString(tradeCode)
                        displayText += f', {tradeCodeString}' if displayText else tradeCodeString
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, displayText)
                elif columnType == self.ColumnType.PopulationCount:
                    count = world.population()
                    if count >= 0:
                        tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                    else:
                        tableItem = QtWidgets.QTableWidgetItem('?')
                elif columnType == self.ColumnType.PopulationMultiplier:
                    count = traveller.ehexToInteger(
                        value=pbg.code(element=traveller.PBG.Element.PopulationMultiplier),
                        default=None)
                    if count != None:
                        tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                    else:
                        tableItem = QtWidgets.QTableWidgetItem('?')
                elif columnType == self.ColumnType.PlanetoidBeltCount:
                    count = traveller.ehexToInteger(
                        value=pbg.code(element=traveller.PBG.Element.PlanetoidBelts),
                        default=None)
                    if count != None:
                        tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                    else:
                        tableItem = QtWidgets.QTableWidgetItem('?')
                elif columnType == self.ColumnType.GasGiantCount:
                    count = traveller.ehexToInteger(
                        value=pbg.code(element=traveller.PBG.Element.GasGiants),
                        default=None)
                    if count != None:
                        tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                    else:
                        tableItem = QtWidgets.QTableWidgetItem('?')
                elif columnType == self.ColumnType.StarCount:
                    tableItem = gui.FormattedNumberTableWidgetItem(world.numberOfStars())
                elif columnType == self.ColumnType.SystemWorldCount:
                    tableItem = gui.FormattedNumberTableWidgetItem(world.numberOfSystemWorlds())
                elif columnType == self.ColumnType.Bases:
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
                    remarks = world.remarks()
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setText(remarks.string())

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, world)
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
        world = self.world(item.row())
        if not world:
            return None

        columnType = self.columnHeader(item.column())

        if columnType == self.ColumnType.World or columnType == self.ColumnType.Sector:
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
