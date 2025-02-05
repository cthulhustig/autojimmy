import maprenderer
from PyQt5 import QtGui # TODO: Get rid of the need for this include

# TODO: Ideally I want to refactor things so this file isn't needed. All rendering
# should live in the render context

def drawStringHelper(
        graphics: maprenderer.AbstractGraphics,
        text: str,
        font: maprenderer.AbstractFont,
        brush: maprenderer.AbstractBrush,
        x: float,
        y: float,
        format: maprenderer.TextAlignment = maprenderer.TextAlignment.Centered
        ) -> None:
    if not text:
        return

    lines = text.split('\n')
    if len(lines) <= 1:
        graphics.drawString(
            text=text,
            font=font,
            brush=brush,
            x=x, y=y,
            format=format)
        return

    sizes = [graphics.measureString(line, font) for line in lines]

    # TODO: This needs updated to not use QT
    qtFont = font.qtFont()
    qtFontMetrics = QtGui.QFontMetrics(qtFont)

    # TODO: Not sure how to calculate this
    #fontUnitsToWorldUnits = qtFont.pointSize() / font.FontFamily.GetEmHeight(font.Style)
    fontUnitsToWorldUnits = font.emSize() / qtFont.pointSize()
    lineSpacing = qtFontMetrics.lineSpacing() * fontUnitsToWorldUnits
    # TODO: I've commented this line out, it's uncommented in the traveller map code but
    # the value is never used
    #ascent = qtFontMetrics.ascent() * fontUnitsToWorldUnits
    # NOTE: This was commented out in the Traveller Map source code
    #float descent = font.FontFamily.GetCellDescent(font.Style) * fontUnitsToWorldUnits;

    maxWidthRect = max(sizes, key=lambda size: size.width())
    boundingSize = maprenderer.AbstractSizeF(width=maxWidthRect.width(), height=lineSpacing * len(sizes))

    # Offset from baseline to top-left.
    y += lineSpacing / 2

    widthFactor = 0
    if format == maprenderer.TextAlignment.MiddleLeft or \
        format == maprenderer.TextAlignment.Centered or \
        format == maprenderer.TextAlignment.MiddleRight:
        y -= boundingSize.height() / 2
    elif format == maprenderer.TextAlignment.BottomLeft or \
        format == maprenderer.TextAlignment.BottomCenter or \
        format == maprenderer.TextAlignment.BottomRight:
        y -= boundingSize.height()

    if format == maprenderer.TextAlignment.TopCenter or \
        format == maprenderer.TextAlignment.Centered or \
        format == maprenderer.TextAlignment.BottomCenter:
            widthFactor = -0.5
    elif format == maprenderer.TextAlignment.TopRight or \
        format == maprenderer.TextAlignment.MiddleRight or \
        format == maprenderer.TextAlignment.BottomRight:
            widthFactor = -1

    for line, size in zip(lines, sizes):
        graphics.drawString(
            text=line,
            font=font,
            brush=brush,
            x=x + widthFactor * size.width() + size.width() / 2,
            y=y,
            format=maprenderer.TextAlignment.Centered)
        y += lineSpacing