class Entity(object):
    def __init__(self, entityId: str) -> None:
        self._entityId = entityId

    def entityId(self) -> str:
        return self._entityId