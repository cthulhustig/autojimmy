import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

def setupLogger(
        logDir: str,
        logFile: str
        ) -> None:
    os.makedirs(logDir, exist_ok=True)
    logFile = os.path.join(logDir, logFile)
    fileHandler = RotatingFileHandler(
        logFile,
        maxBytes=1024 * 1024,
        backupCount=10)
    fileFormatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fileFormatter.converter = time.gmtime
    fileHandler.setFormatter(fileFormatter)
    consoleHandler = logging.StreamHandler(sys.stdout)
    logger = logging.getLogger()
    logger.addHandler(fileHandler)
    logger.addHandler(consoleHandler)
    logger.setLevel(logging.INFO)

def setLogLevel(logLevel: int) -> None:
    logger = logging.getLogger()
    logger.setLevel(logLevel)
