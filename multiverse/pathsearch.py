import heapq
import itertools
import multiverse
import typing

def pathSearch(
        start: typing.Tuple[int, int],
        target: typing.Tuple[int, int],
        neighboursFn: typing.Callable[[typing.Tuple[int, int]], typing.Iterable[typing.Tuple[int, int]]],
        heuristicFn: typing.Optional[typing.Callable[[typing.Tuple[int, int], typing.Tuple[int, int]], float]] = None
        ) -> typing.Optional[typing.List[typing.Tuple[int, int]]]:
    if start == target:
        return [start]

    if heuristicFn is None:
        heuristicFn = lambda src, dst: multiverse.parsecsBetweenAbsoluteSpace(src, dst)

    counter = itertools.count()

    openSet: list[typing.Tuple[float, int, typing.Tuple[int, int]]] = []
    heapq.heappush(openSet, (heuristicFn(start, target), next(counter), start))

    cameFrom: dict[typing.Tuple[int, int], typing.Tuple[int, int]] = {}

    gScore: dict[typing.Tuple[int, int], float] = {start: 0}

    while openSet:
        _, _, current = heapq.heappop(openSet)

        if current == target:
            path = [current]

            while current in cameFrom:
                current = cameFrom[current]
                path.append(current)

            path.reverse()
            return path

        currentCost = gScore[current]

        for neighbour in neighboursFn(current):
            tentativeGScore = currentCost + 1

            if tentativeGScore >= gScore.get(neighbour, float('inf')):
                continue

            cameFrom[neighbour] = current
            gScore[neighbour] = tentativeGScore

            fScore = tentativeGScore + heuristicFn(neighbour, target)

            heapq.heappush(
                openSet,
                (fScore, next(counter), neighbour))

    return None