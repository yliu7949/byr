import atexit
import logging
import platform
import shutil
from DrissionPage import WebPage, ChromiumOptions
import os
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class LoginTool:

    def __init__(self):
        self.try_count = 5
        self.base_url = 'https://byr.pt/'
        self.cookie_save_path = './data/ByrbtCookies.pickle'
        self.chromium_local_port = 23546
        self.chromium_user_data_path = r'./data/cache/drission_page'
        self.chromium_cache_path = r'./data/cache/drission_page_cache'
        self.chromium_proxy = ''
        self.chromium_options = self.init_chromium_options()
        self.page = None

    def init_chromium_options(self):
        chromium_options = ChromiumOptions().set_paths(
            local_port=self.chromium_local_port,
            user_data_path=self.chromium_user_data_path,
            cache_path=self.chromium_cache_path,
        )
        chromium_options.no_imgs(True).mute(True)
        chromium_options.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Heicore/138.0.0.0 Safari/537.36')

        system = platform.system()
        if system == 'Windows' or system == 'Darwin':
            pass
        elif system == 'Linux':
            chromium_options = chromium_options.headless()
            chromium_options = chromium_options.set_argument('--test-type')
            chromium_options = chromium_options.set_argument('--disable-gpu')
            chromium_options = chromium_options.set_argument('--no-sandbox')
            chromium_options = chromium_options.set_argument('--no-zygote')
            chromium_options = chromium_options.set_argument("--disable-dev-shm-usage")
            chromium_options = chromium_options.set_argument("--disable-infobars")
            chromium_options = chromium_options.set_argument("--disable-extensions")
            chromium_options = chromium_options.set_argument("--disable-browser-side-navigation")
            chromium_options = chromium_options.set_argument("--window-position=0,0")
            chromium_options = chromium_options.set_argument("--window-size=1920,1080")
        else:
            logger.error(f'Unsupported platform {system}')
            exit(1)
        if len(self.chromium_proxy) > 0:
            chromium_options = chromium_options.set_proxy(self.chromium_proxy)
        return chromium_options

    def get_url(self, url_path):
        return urljoin(self.base_url, url_path)

    def clear_browser(self):
        if self.page is not None:
            atexit.unregister(self.page.close())
            self.page.close()
        self.page = None
        if os.path.exists(self.chromium_user_data_path):
            shutil.rmtree(self.chromium_user_data_path)
        os.makedirs(self.chromium_user_data_path, exist_ok=True)
        if os.path.exists(self.chromium_cache_path):
            shutil.rmtree(self.chromium_cache_path)
        os.makedirs(self.chromium_cache_path, exist_ok=True)
        logger.info('Browser cleared successfully!')

    def login(self):
        self.page = WebPage(chromium_options=self.chromium_options)
        atexit.register(self.page.close)
        if self.page.get(self.base_url, retry=5) is False:
            logger.error('Failed to access the website: %s', self.base_url)
            return None
        if self.page.url.endswith('login'):
            self.page.ele('@autocomplete=username').input(os.getenv("BYRBT_USERNAME"), clear=True)
            self.page.ele('@autocomplete=current-password').input(os.getenv("BYRBT_PASSWORD"), clear=True)
            self.page.ele('@text()=保持登录').click()
            self.page.ele('@text()= 登录 ').click()
            if not self.page.wait.load_start(timeout=30):
                logger.error('Login timeout during load start')
                return None
            if not self.page.wait.doc_loaded(timeout=30):
                logger.error('Login timeout during document load')
                return None
        if self.page.url != self.base_url and '最近消息' not in self.page.html:
            logger.error('Login failed!')
            return None
        logger.info('Login success!')
        return self.page


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    loginTool = LoginTool()
    loginTool.login()
