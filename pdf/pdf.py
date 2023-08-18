from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Flowable, KeepTogether
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

import typing

# Based on https://gist.github.com/waylan/36535feae946810bcdce5dfb8c6bdcf8
class TextFormField(Flowable):
    def __init__(
            self,
            name: str,
            value: str = '',
            multiline: bool = False,
            fixedWidth: typing.Optional[float] = None,
            fixedHeight: typing.Optional[float] = None,
            maxWidth: typing.Optional[float] = None,
            maxHeight: typing.Optional[float] = None,
            maxLength: int = 1000000, # This is the default the ReportLab code uses
            fontName: str = 'Helvetica',
            fontSize: float = 12,
            textColour: str = '#000000',
            tooltip: typing.Optional[str] = None
            ) -> None:
        super().__init__()

        self._name = name
        self._value = value
        self._multiline = multiline
        self._fixedWidth = fixedWidth
        self._fixedHeight = fixedHeight
        self._maxWidth = maxWidth
        self._maxHeight = maxHeight
        self._maxLength = maxLength
        self._fontName = fontName
        self._fontSize = fontSize
        self._textColour = textColour
        self._tooltip = tooltip

        # Set base class variables if fixed width/height are used
        if self._fixedWidth != None:
            self.width = self._fixedWidth
        if self._fixedHeight != None:
            self._height = self._fixedHeight

    def wrap(self, availWidth: float, availHeight: float) -> None:
        if self._fixedWidth == None:
            self.width = availWidth
            if (self._maxWidth != None) and (self.width > self._maxWidth):
                self.width = self._maxWidth
        else:
            self.width = min(self._fixedWidth, availWidth)

        if self._fixedHeight == None:
            self.height = availHeight
            if (self._maxHeight != None) and (self.height > self._maxHeight):
                self.height = self._maxHeight
        else:
            self.height = min(self._fixedHeight, availHeight)

        return (self.width, self.height)

    def draw(self):
        assert(isinstance(self.canv, canvas.Canvas))
        self.canv.saveState()

        form = self.canv.acroForm
        form.textfieldRelative(
            name=self._name,
            value=self._value,
            tooltip=self._tooltip,
            width=self.width,
            height=self.height,
            borderWidth=None,
            fontName=self._fontName,
            fontSize=self._fontSize,
            textColor=self._textColour,
            fieldFlags='multiline' if self._multiline else '',
            maxlen=self._maxLength)

        self.canv.restoreState()

# Try to keep flowables together but with the option of limiting the amount of space that is wasted.
class KeepTogetherEx(KeepTogether):
    def __init__(
            self,
            flowables,
            limitWaste: typing.Optional[float] = None,
            maxHeight: typing.Optional[float] = None):
        super().__init__(
            flowables,
            maxHeight)

        self._limitWaste = limitWaste

    def split(
            self,
            aW: float,
            aH: float
            ):
        if (self._limitWaste != None) and (aH > self._limitWaste):
            return self._content[:]
        return super().split(aW, aH)

class MultiPageDocTemplateEx(BaseDocTemplate):
    def __init__(
            self,
            filePath: str,
            pagesize: typing.Tuple[float, float],
            pageColour: typing.Optional[str] = None,
            footerText: typing.Optional[str] = None,
            footerFontName: str = 'Helvetica',
            footerFontSize: int = 10,
            footerTextColour: str = '#000000',
            footerVMargin: int = 10,
            enablePageNumbers: bool = True,
            pageNumberFontName: str = 'Helvetica',
            pageNumberFontSize: int = 10,
            pageNumberTextColour: str = '#000000',
            pageNumberHMargin: int = 10,
            pageNumberVMargin: int = 10,
            **kwargs):
        super().__init__(filePath, pagesize=pagesize, _pageBreakQuick=0, **kwargs)

        self._pageColour = pageColour
        self._footerText = footerText
        self._footerFontName = footerFontName
        self._footerFontSize = footerFontSize
        self._footerTextColour = footerTextColour
        self._footerVMargin = footerVMargin
        self._enablePageNumbers = enablePageNumbers
        self._pageNumberFontName = pageNumberFontName
        self._pageNumberFontSize = pageNumberFontSize
        self._pageNumberTextColour = pageNumberTextColour
        self._pageNumberHMargin = pageNumberHMargin
        self._pageNumberVMargin = pageNumberVMargin
        self._pageNumber = 0

        # Setting up the frames, frames are use for dynamic content not fixed page elements
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='main_frame')

        # Creating the page templates
        pageTemplate = PageTemplate(id='FirstPage', frames=[frame], onPage=self._onNewPage)
        self.addPageTemplates([pageTemplate])

    def _onNewPage(
            self,
            canvas: canvas.Canvas,
            doc: 'MultiPageDocTemplateEx'
            ) -> None:
        self._pageNumber += 1 # Always update, even if not drawing page numbers

        if self._pageColour != None:
            self._drawBackgroundColour(canvas=canvas)

        if self._footerText != None:
            self._drawFooter(canvas=canvas, doc=doc)

        if self._enablePageNumbers:
            self._drawPageNumber(canvas=canvas, doc=doc)

    def _drawBackgroundColour(
            self,
            canvas: canvas.Canvas
            ) -> None:
        canvas.saveState()

        # Draw polygon to set background colour
        canvas.setFillColor(self._pageColour)
        path = canvas.beginPath()
        path.moveTo(0 * cm, 0 * cm)
        path.lineTo(0 * cm, 30 * cm)
        path.lineTo(25 * cm, 30 * cm)
        path.lineTo(25 * cm, 0 * cm)
        canvas.drawPath(path, True, True)

        canvas.restoreState()

    def _drawFooter(
            self,
            canvas: canvas.Canvas,
            doc: 'MultiPageDocTemplateEx'
            ) -> None:
        canvas.saveState()

        canvas.setFont(
            psfontname=self._footerFontName,
            size=self._footerFontSize)
        canvas.setFillColor(self._footerTextColour)
        canvas.drawCentredString(
            text=self._footerText,
            x=doc.leftMargin + (doc.width / 2),
            y=self._footerVMargin + (self._footerFontSize / 2))

        canvas.restoreState()

    def _drawPageNumber(
            self,
            canvas: canvas.Canvas,
            doc: 'MultiPageDocTemplateEx'
            ) -> None:
        canvas.saveState()

        pageWidth = doc.width + (doc.leftMargin * 2)

        text = str(self._pageNumber)
        width = stringWidth(
            text=text,
            fontName=self._pageNumberFontName,
            fontSize=self._pageNumberFontSize)
        indent = self._pageNumberHMargin + (width / 2)
        canvas.setFont(
            psfontname=self._pageNumberFontName,
            size=self._pageNumberFontSize)
        canvas.setFillColor(self._pageNumberTextColour)
        canvas.drawCentredString(
            text=str(self._pageNumber),
            x=pageWidth - indent if self._pageNumber % 2 else indent,
            y=self._pageNumberVMargin + (self._pageNumberFontSize / 2))

        canvas.restoreState()
