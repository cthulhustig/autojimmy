import typing
import uuid

class UuidObject(object):
    def __init__(
            self,
            cloneUuid: typing.Optional[str] = None
            ) -> None:
        self._uuid = cloneUuid if cloneUuid != None else str(uuid.uuid4())

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UuidObject):
            return self._uuid == other._uuid
        return False

    def uuid(self) -> str:
        return self._uuid