import logging
import os
import platform
import shutil
import time
from urllib.parse import urljoin

from DrissionPage import Chromium, ChromiumOptions

logger = logging.getLogger(__name__)

class LoginTool:

    def __init__(self):
        self.try_count = 5
        self.base_url = 'https://byr.pt/'
        self.chromium_user_data_path = r'./data/cache/drission_page'
        self.chromium_cache_path = r'./data/cache/drission_page_cache'
        self.chromium_options = self.init_chromium_options()
        self.browser = Chromium(addr_or_opts=self.chromium_options)
        self.tab = self.browser.latest_tab

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self.browser is not None:
            self.browser.quit()
            self.browser = None
        self.tab = None

    def init_chromium_options(self):
        chromium_options = (ChromiumOptions().set_paths(
            user_data_path=self.chromium_user_data_path,
            cache_path=self.chromium_cache_path,
        ).no_imgs(True).mute(True).auto_port(True)
        .set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Heicore/138.0.0.0 Safari/537.36'))

        system = platform.system()
        if system == 'Windows' or system == 'Darwin':
            pass
        elif system == 'Linux':
            arguments = [
                '--test-type',
                '--disable-gpu',
                '--no-sandbox',
                '--no-zygote',
                '--disable-dev-shm-usage',
                '--disable-infobars',
                '--disable-extensions',
                '--disable-browser-side-navigation',
                '--window-position=0,0',
                '--window-size=1920,1080'
            ]
            chromium_options = chromium_options.headless()
            for argument in arguments:
                chromium_options = chromium_options.set_argument(argument)
        else:
            logger.error(f'Unsupported platform {system}')
            exit(1)
        return chromium_options

    def get_url(self, url_path):
        return urljoin(self.base_url, url_path)

    def clear_browser(self):
        self.tab.close()
        self.tab = self.browser.new_tab()

        if os.path.exists(self.chromium_user_data_path):
            shutil.rmtree(self.chromium_user_data_path)
        os.makedirs(self.chromium_user_data_path, exist_ok=True)
        if os.path.exists(self.chromium_cache_path):
            shutil.rmtree(self.chromium_cache_path)
        os.makedirs(self.chromium_cache_path, exist_ok=True)
        logger.info('Browser cleared successfully!')

    def login(self):
        if self.tab.get(self.base_url, retry=5) is False:
            logger.error('Failed to access the website: %s', self.base_url)
            return None
        if self.tab.url.endswith('login'):
            self.tab.ele('@autocomplete=username').input(os.getenv("BYRBT_USERNAME"))
            self.tab.ele('@autocomplete=current-password').input(os.getenv("BYRBT_PASSWORD"))
            self.tab.ele('@text()=保持登录').click()
            self.tab.ele('@text()= 登录 ').click()
            if not self.tab.wait.load_start(timeout=30):
                logger.error('Login timeout during load start')
                return None
            if not self.tab.wait.doc_loaded(timeout=30):
                logger.error('Login timeout during document load')
                return None
        if self.tab.url != self.base_url and '最近消息' not in self.tab.html:
            logger.error('Login failed!')
            return None
        logger.info('Login success!')
        return self.tab

    def retry_login(self):
        self.clear_browser()
        return self.login()

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    loginTool = LoginTool()
    loginTool.login()
    time.sleep(3)

    loginTool.retry_login()
    time.sleep(3)
    loginTool.close()
