import base64
import survey
import xml.etree.ElementTree

def parseVector(content: str) -> survey.RawVector:
    rootElement = xml.etree.ElementTree.fromstring(content)

    pointElements = rootElement.findall('./PathDataPoints/PointF')
    if not pointElements:
        raise RuntimeError('Vector has no PathDataPoints/PointF elements')

    points = []
    for index, pointElement in enumerate(pointElements):
        element = pointElement.find('./X')
        if element is None:
            raise RuntimeError(f'Vector PathDataPoint {index + 1} has no X element')
        try:
            x = float(element.text)
        except Exception:
            raise RuntimeError(f'Vector PathDataPoint {index + 1} X element is not a valid number')

        element = pointElement.find('./Y')
        if element is None:
            raise RuntimeError(f'Vector PathDataPoint {index + 1} has no Y element')
        try:
            y = float(element.text)
        except Exception:
            raise RuntimeError(f'Vector PathDataPoint {index + 1} Y element is not a valid number')

        points.append((x, y))

    element = rootElement.find('./PathDataTypes')
    pointTypes = None
    if points and element is not None:
        try:
            pointTypes = base64.b64decode(element.text)
        except Exception:
            raise RuntimeError('Vector PathDataTypes is not a valid base64 string')

    element = rootElement.find('./OriginX')
    originX = None
    if element is not None:
        try:
            originX = float(element.text)
        except Exception:
            raise RuntimeError('Vector OriginX is not a valid number')

    element = rootElement.find('./OriginY')
    originY = None
    if element is not None:
        try:
            originY = float(element.text)
        except Exception:
            raise RuntimeError('Vector OriginY is not a valid number')

    element = rootElement.find('./ScaleX')
    scaleX = None
    if element is not None:
        try:
            scaleX = float(element.text)
        except Exception:
            raise RuntimeError('Vector ScaleX is not a valid number')

    element = rootElement.find('./ScaleY')
    scaleY = None
    if element is not None:
        try:
            scaleY = float(element.text)
        except Exception:
            raise RuntimeError('Vector ScaleY is not a valid number')

    element = rootElement.find('./Name')
    name = None
    if element is not None:
        name = element.text

    element = rootElement.find('./NameX')
    nameX = None
    if element is not None:
        try:
            nameX = float(element.text)
        except Exception:
            raise RuntimeError('Vector NameX is not a valid number')

    element = rootElement.find('./NameY')
    nameY = None
    if element is not None:
        try:
            nameY = float(element.text)
        except Exception:
            raise RuntimeError('Vector NameY is not a valid number')

    element = rootElement.find('./Type')
    vectorType = None
    if element is not None:
        vectorType = element.text

    boundsElement = rootElement.find('./Bounds')
    bounds = None
    if boundsElement is not None:
        element = boundsElement.find('./X')
        if element is None:
            raise RuntimeError('Vector Bounds has no X element')
        try:
            x = float(element.text)
        except Exception:
            raise RuntimeError('Vector Bounds X element is not a valid number')

        element = boundsElement.find('./Y')
        if element is None:
            raise RuntimeError('Vector Bounds has no Y element')
        try:
            y = float(element.text)
        except Exception:
            raise RuntimeError('Vector Bounds Y element is not a valid number')

        element = boundsElement.find('./Width')
        if element is None:
            raise RuntimeError('Vector Bounds has no Width element')
        try:
            width = float(element.text)
        except Exception:
            raise RuntimeError('Vector Bounds Width element is not a valid number')

        element = boundsElement.find('./Height')
        if element is None:
            raise RuntimeError('Vector Bounds has no Height element')
        try:
            height = float(element.text)
        except Exception:
            raise RuntimeError('Vector Bounds Height element is not a valid number')

        bounds = survey.RawBounds(x=x, y=y, width=width, height=height)

    element = rootElement.find('./MapOptions')
    mapOptions = None
    if element is not None and element.text is not None:
        mapOptions = element.text.split()

    return survey.RawVector(
        pathDataPoints=points,
        pathDataTypes=pointTypes,
        originX=originX,
        originY=originY,
        scaleX=scaleX,
        scaleY=scaleY,
        name=name,
        nameX=nameX,
        nameY=nameY,
        vectorType=vectorType,
        bounds=bounds,
        mapOptions=mapOptions)