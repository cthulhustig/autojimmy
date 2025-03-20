import common
import maprenderer
import os
import travellermap
import typing

# TODO: This should probably live elsewhere
class MapLabel(object):
    def __init__(
            self,
            text: str,
            position: maprenderer.AbstractPointF,
            minor: bool = False
            ) -> None:
        self.text = text
        self.position = maprenderer.AbstractPointF(position)
        self.minor = minor

class MapLabelCache(object):
    _MinorLabelsPath = 'res/labels/minor_labels.tab'
    _MajorLabelsPath = 'res/labels/mega_labels.tab'

    def __init__(self):
        self.minorLabels = self._parseContent(
            travellermap.DataStore.instance().loadTextResource(
                filePath=MapLabelCache._MinorLabelsPath))
        self.megaLabels = self._parseContent(
            travellermap.DataStore.instance().loadTextResource(
                filePath=MapLabelCache._MajorLabelsPath))

    def _parseContent(self, content: str) -> typing.List[MapLabel]:
        _, rows = maprenderer.parseTabContent(content=content)
        labels = []
        for data in rows:
            labels.append(MapLabel(
                text=data['Text'].replace('\\n', '\n'),
                position=maprenderer.AbstractPointF(x=float(data['X']), y=float(data['Y'])),
                minor=common.stringToBool(data['Minor'], strict=False)))
        return labels