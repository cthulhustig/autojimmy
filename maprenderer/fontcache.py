import enum
import logging
import maprenderer
import math
import random
import re
import traveller
import travellermap
import typing

class FontCache(object):
    def __init__(self, sheet: maprenderer.StyleSheet):
        self.sheet = sheet
        self._wingdingsFont = None
        self._glyphFont = None

    @property
    def wingdingFont(self) -> maprenderer.AbstractFont:
        if self._wingdingsFont:
            return self._wingdingsFont
        self._wingdingsFont = self.sheet.wingdingFont.makeFont()
        return self._wingdingsFont

    @property
    def glyphFont(self) -> maprenderer.AbstractFont:
        if self._glyphFont:
            return self._glyphFont
        self._glyphFont = self.sheet.glyphFont.makeFont()
        return self._glyphFont