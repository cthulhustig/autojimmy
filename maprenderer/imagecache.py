import maprenderer
import os
import typing

class ImageCache(object):
    def __init__(
            self,
            graphics: maprenderer.AbstractGraphics,
            basePath: str
            ) -> None:
        self._graphics = graphics
        # TODO: There is a readme in the /res/Candy/ that gives copyright info, I'll
        # need to include that as well
        # TODO: These files should be pulled from DataStore to get caching and
        # filesystem layering
        self.nebulaImage = self._graphics.createImage(
            path=os.path.join(basePath, 'res/Candy/Nebula.png'))
        self.riftImage = self._graphics.createImage(
            path=os.path.join(basePath, 'res/Candy/Rifts.png'))
        self.galaxyImage = self._graphics.createImage(
            path=os.path.join(basePath, 'res/Candy/Galaxy.png'))
        self.galaxyImageGray = self._graphics.createImage(
            path=os.path.join(basePath, 'res/Candy/Galaxy_Gray.png'))
        self.worldImages: typing.Dict[str, maprenderer.AbstractImage] = {
            'Hyd0': self._graphics.createImage(
                path=os.path.join(basePath, 'res/Candy/Hyd0.png')),
            'Hyd1': self._graphics.createImage(
                path=os.path.join(basePath, 'res/Candy/Hyd1.png')),
            'Hyd2': self._graphics.createImage(
                path=os.path.join(basePath, 'res/Candy/Hyd2.png')),
            'Hyd3': self._graphics.createImage(
                path=os.path.join(basePath, 'res/Candy/Hyd3.png')),
            'Hyd4': self._graphics.createImage(
                path=os.path.join(basePath, 'res/Candy/Hyd4.png')),
            'Hyd5': self._graphics.createImage(
                path=os.path.join(basePath, 'res/Candy/Hyd5.png')),
            'Hyd6': self._graphics.createImage(
                path=os.path.join(basePath, 'res/Candy/Hyd6.png')),
            'Hyd7': self._graphics.createImage(
                path=os.path.join(basePath, 'res/Candy/Hyd7.png')),
            'Hyd8': self._graphics.createImage(
                path=os.path.join(basePath, 'res/Candy/Hyd8.png')),
            'Hyd9': self._graphics.createImage(
                path=os.path.join(basePath, 'res/Candy/Hyd9.png')),
            'HydA': self._graphics.createImage(
                path=os.path.join(basePath, 'res/Candy/HydA.png')),
            'Belt': self._graphics.createImage(
                path=os.path.join(basePath, 'res/Candy/Belt.png'))}