import maprenderer
import os
import typing

# TODO: This should probably live elsewhere
class MapLabel(object):
    def __init__(
            self,
            text: str,
            position: maprenderer.PointF,
            minor: bool = False
            ) -> None:
        self.text = text
        self.position = maprenderer.PointF(position)
        self.minor = minor

class MapLabelCache(object):
    _MinorLabelsPath = 'res/labels/minor_labels.tab'
    _MajorLabelsPath = 'res/labels/mega_labels.tab'

    def __init__(self, basePath: str):
        self.minorLabels = self._loadFile(
            os.path.join(basePath, MapLabelCache._MinorLabelsPath))
        self.megaLabels = self._loadFile(
            os.path.join(basePath, MapLabelCache._MajorLabelsPath))

    def _loadFile(self, path: str) -> typing.List[MapLabel]:
        _, rows = maprenderer.loadTabFile(path=path)
        labels = []
        for data in rows:
            labels.append(MapLabel(
                text=data['Text'].replace('\\n', '\n'),
                position=maprenderer.PointF(x=float(data['X']), y=float(data['Y'])),
                minor=bool(data['Minor'].lower() == 'true')))
        return labels