import maprenderer

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

    widths = [graphics.measureString(line, font)[0] for line in lines]

    fontUnitsToWorldUnits = font.emSize() / font.pointSize()
    lineSpacing = font.lineSpacing() * fontUnitsToWorldUnits

    totalHeight = lineSpacing * len(widths)

    # Offset from baseline to top-left.
    y += lineSpacing / 2

    widthFactor = 0
    if format == maprenderer.TextAlignment.MiddleLeft or \
        format == maprenderer.TextAlignment.Centered or \
        format == maprenderer.TextAlignment.MiddleRight:
        y -= totalHeight / 2
    elif format == maprenderer.TextAlignment.BottomLeft or \
        format == maprenderer.TextAlignment.BottomCenter or \
        format == maprenderer.TextAlignment.BottomRight:
        y -= totalHeight

    if format == maprenderer.TextAlignment.TopCenter or \
        format == maprenderer.TextAlignment.Centered or \
        format == maprenderer.TextAlignment.BottomCenter:
            widthFactor = -0.5
    elif format == maprenderer.TextAlignment.TopRight or \
        format == maprenderer.TextAlignment.MiddleRight or \
        format == maprenderer.TextAlignment.BottomRight:
            widthFactor = -1

    for line, width in zip(lines, widths):
        graphics.drawString(
            text=line,
            font=font,
            brush=brush,
            x=x + widthFactor * width + width / 2,
            y=y,
            format=maprenderer.TextAlignment.Centered)
        y += lineSpacing