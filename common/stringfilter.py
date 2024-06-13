import enum
import fnmatch
import re
import typing

class StringFilterType(enum.Enum):
    NoFilter = 'No Filter'
    ContainsString = 'Contains String'
    ExactString = 'Exact String'
    Regex = 'Regex'
    Wildcard = 'Wildcard'

class StringFilter(object):
    def __init__(
            self,
            filterType: StringFilterType = StringFilterType.NoFilter,
            filterString: typing.Optional[str] = None,
            ignoreCase: bool = True
            ) -> None:
        self._filterRegex = None
        self.setFilter(
            filterType=filterType,
            filterString=filterString,
            ignoreCase=ignoreCase)
            
    def setFilter(
            self,
            filterType: StringFilterType,
            filterString: typing.Optional[str] = None,
            ignoreCase: bool = True
            ) -> None:
        pattern = None
        if filterType == StringFilterType.NoFilter:
            pass
        elif filterType == StringFilterType.ContainsString:
            if filterString:
                pattern = f'.*{re.escape(filterString)}.*'
        elif filterType == StringFilterType.ExactString:
            if filterString:
                pattern = f'^{re.escape(filterString)}$'
        elif filterType == StringFilterType.Regex:
            pattern = filterString
        elif filterType == StringFilterType.Wildcard:
            if filterString:
                pattern = fnmatch.translate(filterString)
        else:
            raise ValueError(f'Invalid filter type {filterType}')

        if pattern:
            self._filterRegex = re.compile(
                pattern,
                re.IGNORECASE if ignoreCase else 0)
        else:
            self._filterRegex = None

    def matches(self, string: str) -> bool:
        if not self._filterRegex:
            # Filtering is disabled so all strings match
            return True
        return self._filterRegex.match(string) != None

    

