from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import traceback
import sys
import os
import logging
import asyncio
from pygptlink.gpt_completion import GPTCompletion

from gptrp.character_sheet import CharacterSheet
from gptrp.game_master import GameMaster


API_KEY = open("api_key.txt", 'r').read().rstrip()

LOG_DIR = "logs"
LOG_FILE = f"{LOG_DIR}/gptrp-{datetime.now().strftime('%Y-%m-%d')}.log"


def setup_logger():
    logger = logging.getLogger("pygptlink")
    logger.setLevel(logging.DEBUG)

    # Check if the logger already has a file handler
    file_handler_exists = any(isinstance(
        handler, TimedRotatingFileHandler) for handler in logger.handlers)

    if not file_handler_exists:
        encoding = "utf-8"
        os.makedirs(LOG_DIR, exist_ok=True)

        iso8601fmt = "%Y-%m-%dT%H:%M:%S%z"

        file_handler = TimedRotatingFileHandler(
            LOG_FILE, when="midnight", backupCount=3, encoding=encoding)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s', datefmt=iso8601fmt))
        logger.addHandler(file_handler)

        # Create a stream handler (terminal output)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.ERROR)
        stream_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s', datefmt=iso8601fmt))
        logger.addHandler(stream_handler)

        # Define a custom exception handler
        def log_uncaught_exceptions(exctype, value, tb):
            formatted_exception = ''.join(
                traceback.format_exception(exctype, value, tb))
            logger.error(f"Uncaught exception:\n{formatted_exception}")

        # Install the exception handler
        sys.excepthook = log_uncaught_exceptions

    return logger


logger = setup_logger()


def callback(sentence: str, response_done: bool):
    if sentence:
        print(f"{sentence}")


async def main():
    pc = CharacterSheet("Emi", "At the main gate of the castle.",
                        "Young knight.")

    ravenheart_cs = CharacterSheet("Ravenheart", "In the castle's throne room",
                                   "description")
    completion = GPTCompletion(
        api_key=API_KEY)

    gm = GameMaster(completion=completion, pc_cs=pc, all_npc_cs=[
                    ravenheart_cs], setting="The story takes place in a medieval fantasy world where magic exists and only a few are able to use it.", start_hour=16)

    while True:
        await gm.do_round()


if __name__ == "__main__":
    asyncio.run(main())
