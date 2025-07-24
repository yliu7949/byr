import logging

from dotenv import load_dotenv

from byr.client.qbittorrent import QBittorrent
from byr.login import LoginTool
from byr.bot import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

if __name__ == '__main__':
    load_dotenv()

    login = LoginTool()
    qbittorrent = QBittorrent()
    with Bot(login, qbittorrent) as bot:
        bot.start()