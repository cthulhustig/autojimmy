class Entity(object):
    def __init__(self, id: str) -> None:
        self._id = id

    def id(self) -> str:
        return self._id