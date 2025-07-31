import logging
import os

from dotenv import load_dotenv

from byr.bot import Bot
from byr.client.qbittorrent import QBittorrent
from byr.login import LoginTool


def configure_logging() -> None:
    """配置日志等级和格式"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

    if log_level not in valid_levels:
        log_level = 'INFO'

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

if __name__ == '__main__':
    load_dotenv()
    configure_logging()

    login = LoginTool()
    qbittorrent = QBittorrent()
    with Bot(login, qbittorrent) as bot:
        bot.start()