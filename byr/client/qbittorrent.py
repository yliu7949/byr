import logging
import os
import time
import uuid

from qbittorrentapi import Client, LoginFailed

# 配置日志
logger = logging.getLogger(__name__)


class QBittorrent:
    def __init__(self):
        self.host = os.getenv('QBITTORRENT_HOST')
        self.username = os.getenv('QBITTORRENT_USERNAME')
        self.password = os.getenv('QBITTORRENT_PASSWORD')
        self.download_path = os.getenv('QBITTORRENT_DOWNLOAD_PATH')
        self.client = None
        self._connect()

    def _connect(self):
        """连接到 qBittorrent 客户端"""
        try:
            self.client = Client(
                host=f"{self.host}",
                username=self.username,
                password=self.password,
                VERIFY_WEBUI_CERTIFICATE=False  # 忽略证书验证
            )
            self.client.auth_log_in()  # 显式登录
            logger.info("Successfully connected to qBittorrent.")
        except LoginFailed as e:
            logger.error(f"Login failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise

    def get_list(self):
        """获取所有任务列表"""
        try:
            return self.client.torrents_info()
        except Exception as e:
            logger.error(f"Get torrent list failed: {e}")
            return None

    def get_free_space(self):
        """获取下载目录剩余空间"""
        try:
            return self.client.sync.maindata().server_state.free_space_on_disk
        except Exception as e:
            logger.error(f"Get free space failed: {e}")
            return None

    def remove(self, hashes, delete_data=False):
        """删除任务"""
        try:
            if isinstance(hashes, str):
                hashes = [hashes]
            self.client.torrents_delete(
                delete_files=delete_data,
                torrent_hashes=hashes
            )
            return True
        except Exception as e:
            logger.error(f"Remove torrent failed: {e}")
            return False

    def download_from_content(self, torrent_id, content, paused=False):
        """通过种子内容添加任务"""
        try:
            # 获取当前最新任务的时间戳作为基准点
            existing_torrents = self.client.torrents.info(sort='added_on', reverse=True)
            last_added_time = existing_torrents[0].added_on if existing_torrents else 0

            # 添加任务
            unique_tag = f"temp_{uuid.uuid4().hex}"
            self.client.torrents_add(
                torrent_files=content,
                save_path=self.download_path,
                is_paused=paused,
                tags=[unique_tag]  # 添加唯一标签
            )

            # 重试机制确保获取新任务
            new_torrent = None
            retries = 5  # 最多重试 5 次
            while retries > 0 and not new_torrent:
                time.sleep(0.5)  # 每次等待 0.5 秒
                retries -= 1

                # 方法 1：通过时间戳过滤
                latest_torrents = self.client.torrents.info(sort='added_on', reverse=True)
                for latest_torrent in latest_torrents:
                    if latest_torrent.added_on > last_added_time or latest_torrent.comment == torrent_id:
                        new_torrent = latest_torrent
                        break

                # 方法 2：通过唯一标签过滤
                if not new_torrent:
                    tagged = self.client.torrents_info(tag=unique_tag)
                    if tagged:
                        new_torrent = tagged[0]

            # 移除种子上的临时标签
            if new_torrent and unique_tag in new_torrent.tags:
                try:
                    self.client.torrents_remove_tags(
                        torrent_hashes=new_torrent.hash,
                        tags=[unique_tag]
                    )
                except Exception as e:
                    logger.warning(f"Failed to remove temp tag: {e}")

            # 删除创建的临时标签
            try:
                all_tags = self.client.torrents_tags()
                temp_tags = [tag for tag in all_tags if tag.startswith('temp_')]
                if temp_tags:
                    self.client.torrents_delete_tags(tags=temp_tags)
            except Exception as e:
                logger.warning(f"Failed to delete temp tags: {e}")

            return new_torrent

        except Exception as e:
            logger.error(f"Add torrent failed: {e}")
            return None

    def start_torrent(self, hashes):
        """开始任务"""
        try:
            self.client.torrents_resume(torrent_hashes=hashes)
            return True
        except Exception as e:
            logger.error(f"Start torrent failed: {e}")
            return False

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    qbittorrent = QBittorrent()

    # 测试获取任务列表
    torrents = qbittorrent.get_list()
    if torrents:
        print(f"Found {len(torrents)} torrents:")
        for torrent in torrents[:10]:
            print(f" - {torrent.name} (Status: {torrent.state})")

    # 测试获取剩余空间
    free_space = qbittorrent.get_free_space()
    if free_space is not None:
        print(f"Free space: {free_space / (1024 ** 4):.2f} TB.")