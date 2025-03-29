import cartographer
import travellermap
import typing

class ImageCache(object):
    def __init__(
            self,
            graphics: cartographer.AbstractGraphics
            ) -> None:
        self._graphics = graphics
        self.nebulaImage = self._graphics.createImage(
            data=travellermap.DataStore.instance().loadBinaryResource(
                filePath='res/Candy/Nebula.png'))
        self.riftImage = self._graphics.createImage(
            data=travellermap.DataStore.instance().loadBinaryResource(
                filePath='res/Candy/Rifts.png'))
        self.galaxyImage = self._graphics.createImage(
            data=travellermap.DataStore.instance().loadBinaryResource(
                filePath='res/Candy/Galaxy.png'))
        self.galaxyImageGray = self._graphics.createImage(
            data=travellermap.DataStore.instance().loadBinaryResource(
                filePath='res/Candy/Galaxy_Gray.png'))
        self.worldImages: typing.Dict[str, cartographer.AbstractImage] = {
            'Hyd0': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='res/Candy/Hyd0.png')),
            'Hyd1': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='res/Candy/Hyd1.png')),
            'Hyd2': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='res/Candy/Hyd2.png')),
            'Hyd3': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='res/Candy/Hyd3.png')),
            'Hyd4': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='res/Candy/Hyd4.png')),
            'Hyd5': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='res/Candy/Hyd5.png')),
            'Hyd6': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='res/Candy/Hyd6.png')),
            'Hyd7': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='res/Candy/Hyd7.png')),
            'Hyd8': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='res/Candy/Hyd8.png')),
            'Hyd9': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='res/Candy/Hyd9.png')),
            'HydA': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='res/Candy/HydA.png')),
            'Belt': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='res/Candy/Belt.png'))}