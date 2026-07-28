import common

class Entity(object):
    def __init__(self, entityId: str) -> None:
        common.validateStr(name='entityId', value=entityId, allowEmpty=False)

        self._entityId = entityId

    def entityId(self) -> str:
        return self._entityId