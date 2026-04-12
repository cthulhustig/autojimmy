import app
import gc
import io
import logging
import typing

def _writeMessage(
        message: str,
        writeToTerminal: bool = False,
        writeToLogLevel: typing.Optional[int] = None,
        writeToFile: typing.Optional[io.TextIOWrapper] = None
        ) -> None:
    if writeToTerminal:
        print(message)
    if writeToLogLevel is not None:
        logging.log(writeToLogLevel, message)
    if writeToFile is not None:
        writeToFile.write(message)

def debugWriteGarbageCollectorStats(
        writeToTerminal: bool = False,
        writeToLogLevel: typing.Optional[int] = None,
        writeToFilePath: typing.Optional[str] = None
        ) -> None:
    file = open(writeToFilePath, 'w', encoding='UTF8') if writeToFilePath else None
    try:
        _writeMessage(
            message='Garbage Collector Stats',
            writeToTerminal=writeToTerminal,
            writeToLogLevel=writeToLogLevel,
            writeToFile=file)

        stats = gc.get_stats()

        for index, generation in enumerate(stats):
            _writeMessage(
                message=f'Generation {index}:',
                writeToTerminal=writeToTerminal,
                writeToLogLevel=writeToLogLevel,
                writeToFile=file)
            for key, value in generation.items():
                _writeMessage(
                    message=f'  {key}: {value}',
                    writeToTerminal=writeToTerminal,
                    writeToLogLevel=writeToLogLevel,
                    writeToFile=file)
    finally:
        if file:
            file.close()

def debugForceGarbageCollection(
        writeToTerminal: bool = False,
        writeToLogLevel: typing.Optional[int] = None,
        writeToFilePath: typing.Optional[str] = None
        ) -> None:
    file = open(writeToFilePath, 'w', encoding='UTF8') if writeToFilePath else None
    try:
        _writeMessage(
            message='Forcing Garbage Collection',
            writeToTerminal=writeToTerminal,
            writeToLogLevel=writeToLogLevel,
            writeToFile=file)

        gc.collect()
    finally:
        if file:
            file.close()

def debugCheckForTypeCycles(
        writeToTerminal: bool = False,
        writeToLogLevel: typing.Optional[int] = None,
        writeToFilePath: typing.Optional[str] = None
        ) -> None:
    file = open(writeToFilePath, 'w', encoding='UTF8') if writeToFilePath else None
    try:
        _writeMessage(
            message='Checking for type cycles',
            writeToTerminal=writeToTerminal,
            writeToLogLevel=writeToLogLevel,
            writeToFile=file)

        results = app.findTypeCycles()
        if not results:
            _writeMessage(
                message='No type cycles found',
                writeToTerminal=writeToTerminal,
                writeToLogLevel=writeToLogLevel,
                writeToFile=file)
            return

        count = len(results)
        _writeMessage(
            message=f'Found {count} type cycles',
            writeToTerminal=writeToTerminal,
            writeToLogLevel=writeToLogLevel,
            writeToFile=file)

        for cycle in results:
            _writeMessage(
                message='Cycle:',
                writeToTerminal=writeToTerminal,
                writeToLogLevel=writeToLogLevel,
                writeToFile=file)
            for objType in cycle:
                _writeMessage(
                    message=f'  {objType}',
                    writeToTerminal=writeToTerminal,
                    writeToLogLevel=writeToLogLevel,
                    writeToFile=file)
    finally:
        if file:
            file.close()
