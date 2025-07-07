import gui
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

# https://stackoverflow.com/questions/14780517/toggle-switch-in-qt
# I've made the following changes
# - Updated to use full namespaces for classes and enums
# - Updated to use typing
# - Fixed exception in paintEvent where a float was being passed to setPixelSize
# - Added support for interface scaling
class ToggleButton(QtWidgets.QAbstractButton):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            track_radius: int = 10,
            thumb_radius: int = 8
            ) -> None:
        super().__init__(parent=parent)
        self.setCheckable(True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)

        # Scale control by interface scale
        interface_scale = gui.interfaceScale()
        self._track_radius = int(track_radius * interface_scale)
        self._thumb_radius = int(thumb_radius * interface_scale)

        self._margin = max(0, self._thumb_radius - self._track_radius)
        self._base_offset = max(self._thumb_radius, self._track_radius)
        self._end_offset = {
            True: lambda: self.width() - self._base_offset,
            False: lambda: self._base_offset,
        }
        self._offset = self._base_offset

        palette = self.palette()
        if self._thumb_radius > self._track_radius:
            self._track_color = {
                True: palette.highlight(),
                False: palette.dark(),
            }
            self._thumb_color = {
                True: palette.highlight(),
                False: palette.light(),
            }
            self._text_color = {
                True: palette.highlightedText().color(),
                False: palette.dark().color(),
            }
            self._thumb_text = {
                True: '',
                False: '',
            }
            self._track_opacity = 0.5
        else:
            self._thumb_color = {
                True: palette.highlightedText(),
                False: palette.light(),
            }
            self._track_color = {
                True: palette.highlight(),
                False: palette.dark(),
            }
            self._text_color = {
                True: palette.highlight().color(),
                False: palette.dark().color(),
            }
            self._thumb_text = {
                True: '✔',
                False: '✕',
            }
            self._track_opacity = 1

    @QtCore.pyqtProperty(int)
    def offset(self) -> int:
        return self._offset

    @offset.setter
    def offset(self, value: int) -> None:
        self._offset = value
        self.update()

    def sizeHint(self) -> QtCore.QSize:  # pylint: disable=invalid-name
        return QtCore.QSize(
            4 * self._track_radius + 2 * self._margin,
            2 * self._track_radius + 2 * self._margin,
        )

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self.offset = self._end_offset[checked]()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.offset = self._end_offset[self.isChecked()]()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # pylint: disable=invalid-name, unused-argument
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        track_opacity = self._track_opacity
        thumb_opacity = 1.0
        text_opacity = 1.0
        if self.isEnabled():
            track_brush = self._track_color[self.isChecked()]
            thumb_brush = self._thumb_color[self.isChecked()]
            text_color = self._text_color[self.isChecked()]
        else:
            track_opacity *= 0.8
            track_brush = self.palette().shadow()
            thumb_brush = self.palette().mid()
            text_color = self.palette().shadow().color()

        p.setBrush(track_brush)
        p.setOpacity(track_opacity)
        p.drawRoundedRect(
            self._margin,
            self._margin,
            self.width() - 2 * self._margin,
            self.height() - 2 * self._margin,
            self._track_radius,
            self._track_radius,
        )
        p.setBrush(thumb_brush)
        p.setOpacity(thumb_opacity)
        p.drawEllipse(
            self.offset - self._thumb_radius,
            self._base_offset - self._thumb_radius,
            2 * self._thumb_radius,
            2 * self._thumb_radius,
        )
        p.setPen(text_color)
        p.setOpacity(text_opacity)
        font = p.font()
        font.setPixelSize(int(1.5 * self._thumb_radius))
        p.setFont(font)
        p.drawText(
            QtCore.QRectF(
                self.offset - self._thumb_radius,
                self._base_offset - self._thumb_radius,
                2 * self._thumb_radius,
                2 * self._thumb_radius,
            ),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            self._thumb_text[self.isChecked()],
        )

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # pylint: disable=invalid-name
        super().mouseReleaseEvent(event)
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            anim = QtCore.QPropertyAnimation(self, b'offset', self)
            anim.setDuration(120)
            anim.setStartValue(self.offset)
            anim.setEndValue(self._end_offset[self.isChecked()]())
            anim.start()

    def enterEvent(self, event: QtCore.QEvent) -> None:  # pylint: disable=invalid-name
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        super().enterEvent(event)
