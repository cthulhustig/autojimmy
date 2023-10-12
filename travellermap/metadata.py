import typing
import xml.etree.ElementTree as ET

# TODO: This probably needs a less generic name
class Metadata(object):
    def __init__(
            self,
            xml: str
            ) -> None:       
        root = ET.fromstring(xml)

        nameElements = root.findall('./Name')
        if not nameElements:
            raise RuntimeError('Failed to find Name element in sector metadata')
        self._names = []
        self._nameLanguages = {}
        for element in nameElements:
            name = element.text
            self._names.append(name)

            lang = element.attrib.get('Lang')
            if lang != None:
                self._nameLanguages[name] = lang

        xElement = root.find('./X')
        if xElement == None:
            raise RuntimeError('Failed to find X element in sector metadata')
        self._x = int(xElement.text)
        
        yElement = root.find('./Y')
        if yElement == None:
            raise RuntimeError('Failed to find Y element in sector metadata')
        self._y = int(yElement.text)

    def canonicalName(self) -> str:
        return self._names[0] if self._names else None
    
    def alternateNames(self) -> typing.Optional[typing.Iterable[str]]:
        if len(self._names) < 2:
            return None
        return self._names[1:]

    def names(self) -> typing.Iterable[str]:
        return self._names
    
    def nameLanguage(self, name: str) -> typing.Optional[str]:
        return self._nameLanguages.get(name)
    
    def nameLanguages(self) -> typing.Mapping[str, str]:
        return self._nameLanguages.copy()

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y
