import astronomer
import common
import typing

class ChangeEvent(object):
    def __init__(
            self,
            added: typing.Optional[typing.Collection[astronomer.Entity]] = None,
            modified: typing.Optional[typing.Collection[astronomer.Entity]] = None,
            deleted: typing.Optional[typing.Collection[astronomer.Entity]] = None
            ) -> None:
        self._added = set(added) if added else set()
        self._modified = set(modified) if modified else set()
        self._deleted = set(deleted) if deleted else set()

    def isAdded(self, entity: astronomer.Entity) -> bool:
        return entity in self._added

    def added(self) -> typing.Collection[astronomer.Entity]:
        return common.ConstSequenceRef(self._added)

    def isModified(self, entity: astronomer.Entity) -> bool:
        return entity in self._modified

    def modified(self) -> typing.Collection[astronomer.Entity]:
        return common.ConstSequenceRef(self._modified)

    def isDeleted(self, entity: astronomer.Entity) -> bool:
        return entity in self._deleted

    def deleted(self) -> typing.Collection[astronomer.Entity]:
        return common.ConstSequenceRef(self._deleted)