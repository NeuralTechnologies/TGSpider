import logging
import requests
import yaml
import os
_log_format = f"%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"

with open(os.getenv('CONFIG_DIRECTORY')+'/'+'config.yaml', 'r') as file:
    config = yaml.safe_load(file)


class TelegramHandler(logging.Handler):
    def __init__(self, level=logging.INFO, bot_token=config['LOGGING']['logs_bot_token'],
                 receiver=config['LOGGING']['logs_group_id'], **kwargs):
        self._bot_token = bot_token
        self._receiver = receiver
        super().__init__(level)

    def emit(self, record):
        url = f'https://api.telegram.org/bot{config['LOGGING']['logs_bot_token']}/sendMessage'
        data = {
            "chat_id": config['LOGGING']['logs_group_id'],
            "text": str(record.message)
        }
        requests.post(url, data=data)


def get_file_handler():
    file_handler = logging.FileHandler(config['LOGGING']['log_file'])
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(_log_format))
    return file_handler


def get_stream_handler():
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(_log_format))
    return stream_handler


def get_telegram_handler():
    telegram_handler = TelegramHandler()
    telegram_handler.setLevel(logging.INFO)
    telegram_handler.setFormatter(logging.Formatter(_log_format))
    return telegram_handler


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(get_file_handler())
    logger.addHandler(get_stream_handler())
    logger.addHandler(get_telegram_handler())
    return logger
