import gc
import types
import typing

# This uses Tarjan's SCC algorithm to find loops in object
# references tracked by the garbage collector
# https://en.wikipedia.org/wiki/Tarjan%27s_strongly_connected_components_algorithm
def findObjectCycles(
        targetType: typing.Optional[typing.Type] = None
        ) -> typing.List[typing.List[typing.Any]]:
    graph: typing.Dict[int, typing.List[int]] = {}
    objects: typing.Dict[int, typing.Any] = {}
    indices: typing.Dict[int, int] = {}
    lowLink: typing.Dict[int, int] = {}
    stack: typing.List[int] = []
    onStack: typing.Set[int] = set()
    sccs: typing.List[typing.List[int]] = []
    index = 0

    def _filteredReferents(obj):
        # Bound method → only follow the instance
        if isinstance(obj, types.MethodType):
            return [obj.__self__]

        # Function → ignore completely (no useful ownership)
        if isinstance(obj, types.FunctionType):
            return []

        # Class → ignore (prevents function/class/global cycles)
        if isinstance(obj, type):
            return []

        # Default
        return gc.get_referents(obj)

    def _isInteresting(obj: typing.Any) -> bool:
        return not isinstance(obj, (type, types.ModuleType, types.FrameType, types.CodeType))

    def _strongConnect(objId: int) -> None:
        nonlocal index

        # Set the depth index for objId to the smallest unused index
        indices[objId] = index
        lowLink[objId] = index
        index += 1
        stack.append(objId)
        onStack.add(objId)

        refs = graph[objId]

        if refs:
            for refId in refs:
                if refId not in graph:
                    # Apparently get_referents can return objects that aren't included in
                    # get_objects. These objects are ignored
                    continue

                if refId not in indices:
                    # Successor neighbourId has not yet been visited; recurse on it
                    _strongConnect(refId)
                    lowLink[objId] = min(lowLink[objId], lowLink[refId])
                elif refId in onStack:
                    # Successor refId is in stack and hence in the current SCC
                    # If refId is not on stack, then objId to refId is an edge pointing to an SCC already found and must be ignored
                    # See below regarding the next line
                    lowLink[objId] = min(lowLink[objId], indices[refId])

        # If objId is a root node, pop the stack and generate an SCC
        if lowLink[objId] == indices[objId]:
            # start a new strongly connected component
            scc = []
            while True:
                refId = stack.pop()
                onStack.remove(refId)
                scc.append(refId)
                if refId == objId:
                    break

            if len(scc) > 1 or (len(scc) == 1 and objId in graph[objId]):
                sccs.append(scc)

    try:
        for obj in gc.get_objects():
            if _isInteresting(obj):
                objId = id(obj)
                refs = _filteredReferents(obj)
                graph[objId] = [id(r) for r in refs if _isInteresting(r)]
                objects[objId] = obj

        for objId in graph.keys():
            if objId not in indices:
                _strongConnect(objId)

        results = []
        for scc in sccs:
            objs = [objects[objId] for objId in scc if objId in objects]
            if targetType is not None:
                if not any(isinstance(o, targetType) for o in objs):
                    continue
            results.append(objs)

        return results
    finally:
        # Explicitly clear all containers as they can be massive and it looks
        # like they can result in lots of garbage which can then skew results
        # if the code gets run again
        graph.clear()
        objects.clear()
        indices.clear()
        lowLink.clear()
        stack.clear()
        onStack.clear()
        sccs.clear()

def findTypeCycles() -> typing.List[typing.Tuple[
            typing.List[typing.Type], # Cycle
            int]]: # Occurrence count
    def _canonicalize(types: typing.List[type]) -> typing.Tuple[int, ...]:
        ids = [id(t) for t in types]
        n = len(ids)

        # Generate list of all possible sequences of type ids
        fwdRotations = [tuple(ids[i:] + ids[:i]) for i in range(n)]

        # Generate a reverse list of all sequences of type ids
        rev = list(reversed(ids))
        revRotations = [tuple(rev[i:] + rev[:i]) for i in range(n)]

        # Find the sequence where the type ids are in the minimum order
        return min(fwdRotations + revRotations)

    typeCycles: typing.List[typing.List[typing.Type]] = []
    seen: typing.Dict[typing.Tuple[int, ...], int] = {}

    try:
        for objectCycle in findObjectCycles():
            typeCycle = [type(o) for o in objectCycle]
            key = _canonicalize(typeCycle)

            seenCount = seen.get(key)
            if seenCount is None:
                seen[key] = 1
                typeCycles.append(typeCycle)
            else:
                seen[key] = seenCount + 1

        return [(c, seen[_canonicalize(c)]) for c in typeCycles]
    finally:
        typeCycles.clear()
        seen.clear()