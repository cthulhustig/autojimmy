import cartographer
import travellermap
import typing

class ImageStore(object):
    def __init__(
            self,
            graphics: cartographer.AbstractGraphics
            ) -> None:
        self._graphics = graphics
        self.nebulaImage = self._graphics.createImage(
            data=travellermap.DataStore.instance().loadBinaryResource(
                filePath='candy/Nebula.png'))
        self.riftImage = self._graphics.createImage(
            data=travellermap.DataStore.instance().loadBinaryResource(
                filePath='candy/Rifts.png'))
        self.galaxyImage = self._graphics.createImage(
            data=travellermap.DataStore.instance().loadBinaryResource(
                filePath='candy/Galaxy.png'))
        self.galaxyImageGray = self._graphics.createImage(
            data=travellermap.DataStore.instance().loadBinaryResource(
                filePath='candy/Galaxy_Gray.png'))
        self.worldImages: typing.Dict[str, cartographer.AbstractImage] = {
            'Hyd0': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='candy/Hyd0.png')),
            'Hyd1': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='candy/Hyd1.png')),
            'Hyd2': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='candy/Hyd2.png')),
            'Hyd3': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='candy/Hyd3.png')),
            'Hyd4': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='candy/Hyd4.png')),
            'Hyd5': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='candy/Hyd5.png')),
            'Hyd6': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='candy/Hyd6.png')),
            'Hyd7': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='candy/Hyd7.png')),
            'Hyd8': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='candy/Hyd8.png')),
            'Hyd9': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='candy/Hyd9.png')),
            'HydA': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='candy/HydA.png')),
            'Belt': self._graphics.createImage(
                data=travellermap.DataStore.instance().loadBinaryResource(
                    filePath='candy/Belt.png'))}
