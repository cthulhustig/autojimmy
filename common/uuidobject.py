import typing
import uuid

class UuidObject(object):
    def __init__(
            self,
            copyUuid: typing.Optional[str] = None
            ) -> None:
        self._uuid = copyUuid if copyUuid != None else str(uuid.uuid4())

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UuidObject):
            return self._uuid == other._uuid
        return False

    def __hash__(self) -> int:
        return hash(self._uuid)

    def uuid(self) -> str:
        return self._uuid