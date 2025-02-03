import maprenderer
import os
import typing

class ImageCache(object):
    def __init__(self, basePath: str) -> None:
        # TODO: There is a readme in the /res/Candy/ that gives copyright info, I'll
        # need to include that as well
        self.nebulaImage = maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Nebula.png'))
        self.riftImage = maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Rifts.png'))
        self.galaxyImage = maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Galaxy.png'))
        self.galaxyImageGray = maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Galaxy_Gray.png'))
        self.worldImages: typing.Dict[str, maprenderer.AbstractImage] = {
            'Hyd0': maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Hyd0.png')),
            'Hyd1': maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Hyd1.png')),
            'Hyd2': maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Hyd2.png')),
            'Hyd3': maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Hyd3.png')),
            'Hyd4': maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Hyd4.png')),
            'Hyd5': maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Hyd5.png')),
            'Hyd6': maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Hyd6.png')),
            'Hyd7': maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Hyd7.png')),
            'Hyd8': maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Hyd8.png')),
            'Hyd9': maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Hyd9.png')),
            'HydA': maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/HydA.png')),
            'Belt': maprenderer.AbstractImage(os.path.join(basePath, 'res/Candy/Belt.png'))}