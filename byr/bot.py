import contextlib
import logging
import os
import re
import sys
import time
import signal
from contextlib import ContextDecorator
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from byr.login import LoginTool

logger = logging.getLogger(__name__)

def format_size(bytes_size):
    # 辅助函数：格式化空间大小
    gb = bytes_size / (1024 ** 3)
    if gb >= 1000:
        return f"{gb / 1000:.2f}TB"
    return f"{gb:.2f}GB"

# noinspection PyUnusedLocal
def _handle_interrupt(signum, frame):
    sys.exit(0)

class Bot(ContextDecorator):
    def __init__(self, login: LoginTool, torrent_client):
        super(Bot, self).__init__()
        self.login_tool = login
        self.torrent_client = torrent_client
        self.page = None
        self.base_url = 'https://byr.pt/'
        self.torrent_url = self._get_url('torrents.php')
        self.old_torrent = list()

        self.max_torrent_total_size = int(os.getenv("MAX_TORRENTS_SIZE", "1024"))
        if self.max_torrent_total_size is None or self.max_torrent_total_size < 0:
            self.max_torrent_total_size = 0
        self.max_torrent_total_size = self.max_torrent_total_size * 1024 * 1024 * 1024

        self._tag_map = {
            # highlight & tag
            'free': '免费',
            'twoup': '2x上传',
            'twoupfree': '免费&2x上传',
            'halfdown': '50%下载',
            'twouphalfdown': '50%下载&2x上传',
            'thirtypercentdown': '30%下载',
            # icon
            '2up': '2x上传',
            'free2up': '免费&2x上传',
            '50pctdown': '50%下载',
            '50pctdown2up': '50%下载&2x上传',
            '30pctdown': '30%下载',
        }
        self._cat_map = {
            '电影': 'movie',
            '剧集': 'episode',
            '动漫': 'anime',
            '音乐': 'music',
            '综艺': 'show',
            '游戏': 'game',
            '软件': 'software',
            '资料': 'material',
            '体育': 'sport',
            '记录': 'documentary',
        }

    def __enter__(self):
        logger.info("BYRBT bot started.")
        signal.signal(signal.SIGINT, _handle_interrupt)
        signal.signal(signal.SIGTERM, _handle_interrupt)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.login_tool.close()
        logger.info("BYRBT bot exited.")

    def _get_url(self, url_path):
        return urljoin(self.base_url, url_path)

    def _get_tag(self, tag):
        try:
            if tag == '':
                return ''
            else:
                tag = tag.split('_')[0]

            return self._tag_map[tag]
        except KeyError:
            return ''

    @staticmethod
    def get_user_info(user_info_block):
        try:
            user_name = user_info_block.select_one('.nowrap').text
            user_info_text = user_info_block.text
            index_s = user_info_text.find('等级')
            index_e = user_info_text.find('当前活动')
            if index_s == -1 or index_e == -1:
                logger.debug("User info: []")
                return
            user_info_text = user_info_text[index_s:index_e]
            user_info_text = re.sub(r"[\xa0\n]+", ' ', user_info_text)
            user_info_text = re.sub(r'\[[^]]*]', '', user_info_text)
            user_info_text = re.sub(r'\s*[:：]\s*', ':', user_info_text)
            user_info_text = re.sub(r'\s+', ' ', user_info_text).strip()
            user_info_text = f"用户名:{user_name} {user_info_text}"
            logger.debug(f"User info: {user_info_text}")

        except Exception as e:
            logger.error(f"Failed to retrieve user info: {e}")

    def get_torrent_info_filter_by_tag(self, table):
        assert isinstance(table, list)
        start_idx = 1  # static offset
        torrent_infos = list()
        for item in table:
            torrent_info = dict()
            tds = item.find_all('td', recursive=False)
            # tds[0] 是 引用

            # tds[1] 是分类
            cat = tds[start_idx].find('a').text.strip()

            # 主要信息的 td
            main_td = tds[start_idx + 1]

            # 链接
            href = main_td.find('a').attrs['href'].strip()

            # 种子 id
            seed_id = re.findall(r'id=(\d+)', href)[0].strip()

            # 标题
            title = main_td.find('a').attrs['title'].strip()

            tags = set(
                [font.attrs['class'][0] for font in main_td.select('span > span') if 'class' in font.attrs.keys()])
            if '' in tags:
                tags.remove('')

            is_seeding = len(main_td.select('img[src="/pic/seeding.png"]')) > 0
            is_finished = len(main_td.select('img[src="/pic/finished.png"]')) > 0

            is_hot = False
            if 'hot' in tags:
                is_hot = True
                tags.remove('hot')
            is_new = False
            if 'new' in tags:
                is_new = True
                tags.remove('new')
            is_recommended = False
            if 'recommended' in tags:
                is_recommended = True
                tags.remove('recommended')

            # 根据控制面板中促销种子的标记方式不同来匹配
            if 'class' in item.attrs:
                # 默认高亮方式
                tag = self._get_tag(item.attrs['class'][0])
            elif len(tags) == 1:
                # 文字标记方式
                # 不属于 hot、new、recommended 的标记即为促销标记
                tag = self._get_tag(list(tags)[0])
            elif len(main_td.select('img[src="/pic/trans.gif"][class^="pro_"]')) > 0:
                # 添加图标方式
                tag = self._get_tag(
                    main_td.select('img[src="/pic/trans.gif"][class^="pro_"]')[-1].attrs['class'][0].split('_')[-1])
            else:
                tag = ''

            file_size = tds[start_idx + 4].text.strip()

            seeding = int(tds[start_idx + 5].text) if tds[start_idx + 5].text.isdigit() else -1
            downloading = int(tds[start_idx + 6].text) if tds[start_idx + 6].text.isdigit() else -1
            finished = int(tds[start_idx + 7].text) if tds[start_idx + 7].text.isdigit() else -1

            torrent_info['cat'] = cat
            torrent_info['is_hot'] = is_hot
            torrent_info['tag'] = tag
            torrent_info['is_seeding'] = is_seeding
            torrent_info['is_finished'] = is_finished
            torrent_info['seed_id'] = seed_id
            torrent_info['title'] = title
            torrent_info['seeding'] = seeding
            torrent_info['downloading'] = downloading
            torrent_info['finished'] = finished
            torrent_info['file_size'] = file_size
            torrent_info['is_new'] = is_new
            torrent_info['is_recommended'] = is_recommended
            torrent_infos.append(torrent_info)

        return torrent_infos

    def find_appropriate_torrents(self, torrent_infos):
        # 获取可用的种子的策略
        ok_infos = list()
        if len(torrent_infos) >= 20:
            # 遇到 free 或者免费种子太过了，择优选取，标准是(下载数/上传数)>20，并且文件大小大于 20GB
            logger.info("Too many qualifying torrents found—possibly a Free event is active. Raising the criteria for eligible torrents.")
            for torrent_info in torrent_infos:
                if torrent_info['seed_id'] in self.old_torrent:
                    continue
                # 下载 1GB-1TB 之间的种子（下载以 GB 大小结尾的种子，脚本需要不可修改）
                if 'GiB' not in torrent_info['file_size']:
                    continue
                if torrent_info['seeding'] <= 0 or torrent_info['downloading'] < 0:
                    continue
                if torrent_info['seeding'] != 0 and float(torrent_info['downloading']) / float(
                        torrent_info['seeding']) < 20:
                    continue
                file_size = torrent_info['file_size']
                file_size = file_size.replace('GiB', '')
                file_size = float(file_size.strip())
                if file_size < 20.0:
                    continue
                ok_infos.append(torrent_info)
        else:
            # 正常种子选择标准是免费种子
            for torrent_info in torrent_infos:
                if torrent_info['seed_id'] in self.old_torrent:
                    continue
                if torrent_info['seeding'] <= 0 or torrent_info['downloading'] < 0:
                    continue
                ok_infos.append(torrent_info)
        return ok_infos

    def start(self):
        scan_interval_in_sec = 45
        check_disk_space_interval_in_sec = 3600
        last_check_disk_space_time = -1
        while True:
            now_time = int(time.time())
            if now_time - last_check_disk_space_time > check_disk_space_interval_in_sec:
                logger.info('Check disk space ...')
                if self.check_disk_space():
                    last_check_disk_space_time = now_time
                else:
                    logger.error('Check disk space failed!')
                    time.sleep(scan_interval_in_sec)
                    continue

            if self.page is None:
                self.page = self.login_tool.login()
                if self.page is None:
                    self.login_tool.clear_browser()
                    break

            logger.debug('Scan torrent list ...')
            flag = False
            torrents_soup = None
            try:
                if self.page.get(self.torrent_url, retry=5) is False:
                    logger.error('Failed to access the website! URL: %s', self.torrent_url)
                    self.login_tool.clear_browser()
                else:
                    self.page.scroll.to_bottom()
                    if self.page.wait.doc_loaded(timeout=10) is False:
                        logger.error('Get torrents timeout!')
                        self.login_tool.clear_browser()
                    else:
                        torrents_soup = BeautifulSoup(self.page.html, 'html.parser')
                        flag = True
            except Exception as e:
                logger.error('%s', repr(e))
                self.login_tool.clear_browser()

            if not flag:
                logger.error('Login failed!')
                break

            try:
                user_info_block = torrents_soup.select_one('#info_block').select_one('.navbar-user-data')
                self.get_user_info(user_info_block)
            except Exception as e:
                logger.error('%s', repr(e))

            torrent_infos = list()
            try:
                torrent_free_bg_table = torrents_soup.find_all('tr', class_='free_bg')
                torrent_infos_free_bg = self.get_torrent_info_filter_by_tag(torrent_free_bg_table)
                torrent_infos.extend(torrent_infos_free_bg)
                torrent_twoupfree_bg_table = torrents_soup.find_all('tr', class_='twoupfree_bg')
                torrent_infos_twoupfree_bg = self.get_torrent_info_filter_by_tag(torrent_twoupfree_bg_table)
                torrent_infos.extend(torrent_infos_twoupfree_bg)
                flag = True
            except Exception as e:
                logger.error('%s', repr(e))
                flag = False

            if not flag:
                logger.error('Failed to parse torrent table!')
                break

            logger.debug('Free torrent list:')
            for i, info in enumerate(torrent_infos):
                logger.debug('%d : %s %s %s', i+1, info['seed_id'], info['file_size'], info['title'])

            appropriate_torrents = self.find_appropriate_torrents(torrent_infos)
            logger.debug('Available torrent list:')
            for i, info in enumerate(appropriate_torrents):
                logger.debug('%d : %s %s %s', i+1, info['seed_id'], info['file_size'], info['title'])

            for torrent in appropriate_torrents:
                if not self.download(torrent['seed_id']):
                    logger.error('%s download failed', torrent['title'])
                    continue

            time.sleep(scan_interval_in_sec)

    def download(self, torrent_id):
        # 检查是否已处理过该种子
        if torrent_id in self.old_torrent:
            logger.info(f"Torrent {torrent_id} already processed, skipping download")
            return True

        download_url = f'download.php?id={torrent_id}'
        download_url = self._get_url(download_url)
        torrent_content = None

        for i in range(5):
            try:
                save_path = os.path.join(self.page.download_path, 'data', 'torrents')

                # 抑制输出
                with open(os.devnull, 'w') as file_null, \
                        contextlib.redirect_stdout(file_null), \
                        contextlib.redirect_stderr(file_null):

                    result = self.page.download.download(
                        file_url=download_url,
                        save_path=save_path,
                        file_exists='overwrite',
                        rename=torrent_id,
                        suffix='torrent'
                    )

                # 检查下载结果
                if isinstance(result, tuple) and result[0] == 'success':
                    torrent_path = result[1]
                    with open(torrent_path, 'rb') as f:
                        torrent_content = f.read()
                    os.unlink(torrent_path)
                    break  # 下载成功，跳出循环

                # 下载失败处理
                logger.warning(f"Download attempt {i + 1} failed, retrying ...")
                self.page = self.login_tool.retry_login()
                time.sleep(1)

            except Exception as e:
                logger.warning(f"Failed to download torrent: {e}")
                logger.info("Retrying login ...")
                self.page = self.login_tool.retry_login()
                time.sleep(1)

        # 检查下载是否成功
        if torrent_content is None:
            logger.error(f"Failed to download torrent after 5 attempts: {download_url}")
            return False

        # 添加种子到客户端
        new_torrent = self.torrent_client.download_from_content(torrent_id, torrent_content, paused=True)
        if new_torrent is None:
            logger.error(f'Failed to add new torrent. Download URL: {download_url}')
            return False

        # 检查磁盘空间
        new_torrent_size = new_torrent.total_size
        result = self.check_remove(new_torrent_size / (1024 ** 3))

        if result is None or not result:  # 空间检查失败
            self.torrent_client.remove(new_torrent.hash, delete_data=True)
            if result is None:
                logger.error('Space check failed unexpectedly')
            else:
                logger.error(f'Insufficient space: Name: {new_torrent.name}, Size: {new_torrent_size / 1_000_000_000:.2f} GB')
            return False

        # 启动种子
        if self.torrent_client.start_torrent(new_torrent.hash):
            logger.info(f'Added torrent: [{new_torrent.comment}][{new_torrent_size / 1_000_000_000:.3f} GB][{new_torrent.name}]')
            self.old_torrent.append(torrent_id)  # 记录已处理理种子
            return True
        else:
            logger.error(f'Failed to start torrent: {new_torrent.name}, Size: {new_torrent_size / 1_000_000_000:.2f} GB')
            self.torrent_client.remove(new_torrent.hash, delete_data=True)
            return False

    def check_disk_space(self):
        # 定义常量
        min_space_required = 5_000_000_000  # 5GB

        # 获取当前磁盘空间
        free_space = self.torrent_client.get_free_space()
        if free_space is None:
            logger.error('Failed to retrieve available disk space.')
            return False

        # 记录当前空间状态
        logger.info('Current free space: %s', format_size(free_space))

        # 空间充足直接返回
        if free_space > min_space_required:
            return True

        # 空间不足处理流程
        logger.warning('Low disk space (%s < 5GB), clearing torrents ...', format_size(free_space))

        # 删除早期添加的种子
        self.check_remove()

        # 最终空间验证
        final_space = self.torrent_client.get_free_space() or free_space
        logger.info('Final free space: %s', format_size(final_space))

        return final_space > min_space_required

    def check_remove(self, min_free_space_gb=5):
        # 定义常量
        min_space_required = min_free_space_gb * (1024 ** 3)  # 转换为字节
        upload_rate_threshold = 200_000  # 200KB/s

        # 获取当前磁盘空间
        free_space = self.torrent_client.get_free_space()
        if free_space is None:
            logger.error("Failed to retrieve available disk space")
            return False

        # 记录当前空间状态
        logger.debug('Current free space: %s', format_size(free_space))

        # 如果空间已足够，直接返回
        if free_space >= min_space_required:
            return True

        # 空间不足处理流程
        logger.warning('Low disk space (%s < %sGB), clearing torrents ...',
                       format_size(free_space), min_free_space_gb)

        # 获取种子列表
        torrent_list = self.torrent_client.get_list()
        if torrent_list is None:
            logger.error("Failed to retrieve torrent list")
            return False

        # 排序策略：优先删除最早添加且上传速率低的种子
        torrent_list.sort(key=lambda x: (x.added_on, x.upspeed))

        # 遍历删除符合条件的种子
        removed_count = 0
        for torrent in torrent_list[:]:  # 创建副本避免修改原始列表
            if free_space >= min_space_required:
                break

            # 跳过不可删除的种子
            if torrent.state in ['checking', 'downloading']:
                continue
            if torrent.state in ['uploading', 'stalledUP', 'stalledDL', 'seeding'] and \
                    torrent.upspeed > upload_rate_threshold:
                continue

            # 执行删除操作
            if not self.torrent_client.remove(torrent.hash, delete_data=True):
                logger.warning("Removal failed: %s (Hash: %s)", torrent.name, torrent.hash)
                continue

            # 更新空间状态
            free_space += torrent.total_size
            removed_count += 1
            logger.info('Removed: %s (Freed: %s, New free space: %s)',
                        torrent.name,
                        format_size(torrent.total_size),
                        format_size(free_space))

        # 最终空间验证
        final_space = self.torrent_client.get_free_space() or free_space
        success = final_space >= min_space_required

        if success:
            logger.info('Successfully freed space. Final free space: %s', format_size(final_space))
        else:
            logger.warning('Still insufficient space after removal. Final free space: %s',
                           format_size(final_space))

        logger.info('Removed %d torrents during cleanup.', removed_count)
        return success
