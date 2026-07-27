import common
import multiverse
import survey
import typing

_T5OfficialAllegiancesPath = 't5ss/allegiance_codes.tab'
def loadSnapshotStockAllegiances(
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.List[survey.RawStockAllegiance]:
    # TODO: This should take the reporter
    return survey.parseTabStockAllegiances(
        content=multiverse.SnapshotManager.instance().readTextResource(
            filePath=_T5OfficialAllegiancesPath))

_T5OfficialSophontsPath = 't5ss/sophont_codes.tab'
def loadSnapshotStockSophonts(
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.List[survey.RawStockSophont]:
    # TODO: This should take the reporter
    return survey.parseTabStockSophonts(
        content=multiverse.SnapshotManager.instance().readTextResource(
            filePath=_T5OfficialSophontsPath))

_OTUStyleSheetPath = 'styles/otu.css'
def loadSnapshotStyleSheet(
        reporter: typing.Optional[common.Reporter] = None
        ) -> survey.RawStyleSheet:
    return survey.parseStyleSheet(
        content=multiverse.SnapshotManager.instance().readTextResource(
            filePath=_OTUStyleSheetPath),
        reporter=reporter)

_MegaLabelsPath = 'labels/mega_labels.tab'
def loadMegaLabels(
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.List[survey.RawUniverseLabel]:
    return survey.parseUniverseLabels(
        content=multiverse.SnapshotManager.instance().readTextResource(
            filePath=_MegaLabelsPath),
        reporter=reporter)

_MinorLabelsPath = 'labels/minor_labels.tab'
def loadMinorLabels(
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.List[survey.RawUniverseLabel]:
    return survey.parseUniverseLabels(
        content=multiverse.SnapshotManager.instance().readTextResource(
            filePath=_MinorLabelsPath),
        reporter=reporter)

_WorldLabelPath = 'labels/Worlds.xml'
def loadWorldLabels(
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.List[survey.RawUniverseLabel]:
    return survey.parseWorldLabels(
        content=multiverse.SnapshotManager.instance().readTextResource(
            filePath=_WorldLabelPath),
        reporter=reporter)