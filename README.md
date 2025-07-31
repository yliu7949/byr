<p style="text-align: center;">
  <img width="190" src="https://raw.githubusercontent.com/yliu7949/byr/master/assets/logo.svg" alt="Byrrot logo">
</p>


# Byrrot
[![byrbt](https://img.shields.io/static/v1?label=Byrrot&message=0.1.0&color=green)](https://github.com/yliu7949/byr)
[![GitHub License](https://img.shields.io/github/license/yliu7949/byr)](https://github.com/yliu7949/byr/blob/master/LICENSE)
![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fyliu7949%2Fbyr%2Frefs%2Fheads%2Fmaster%2Fpyproject.toml)
[![Docker Pulls](https://img.shields.io/docker/pulls/yliu7949/byr)](https://hub.docker.com/r/yliu7949/byr)
[![Docker Image Size (tag)](https://img.shields.io/docker/image-size/yliu7949/byr/latest)](https://hub.docker.com/r/yliu7949/byr)

Byrrot 是一款为[北邮人 BT 站 (BYRBT)](https://byr.pt/) 设计的自动化做种工具。它通过监控站点的最新置顶「免费」种子，结合 qBittorrent Web API 实现无人值守下载，帮助用户高效提升上传量，轻松达成"躺平刷上传"的目标。

该项目既可以在 Python 环境下直接运行，也支持 Docker 容器化部署。实际运行输出展示如下：

![demo](https://raw.githubusercontent.com/yliu7949/byr/master/assets/demo.png)

## 目录

- [特性](#特性)
- [快速开始](#快速开始)
  + [准备工作](#准备工作)
  + [使用方式一：在 Python 环境下直接运行](#使用方式一在-python-环境下直接运行)
  + [使用方式二：快速部署 Docker 容器](#使用方式二快速部署-docker-容器)
- [贡献指南](#贡献指南)
- [致谢](#致谢)
- [许可证](#许可证)

## 特性

|         核心功能          |                     说明                      |
|:---------------------:|:-------------------------------------------:|
|     **自动发现免费种子**      |  定时监控 byr.pt 的最新免费种子资源，自动下载 `.torrent` 文件   |
| **与 qBittorrent 交互**  | 通过 qBittorrent Web API 实现种子自动添加及存储空间智能清理功能  |
|      **灵活配置方式**       |       支持 `.env` 文件与环境变量双重配置机制，保护敏感信息        |
|       **容器化部署**       |       提供预构建的 Docker 镜像，支持快速部署和跨平台一致运行       |

## 快速开始

### 准备工作

1. 硬件设备：一台长期运行用于做种的设备（个人电脑、云服务器、NAS、树莓派皆可）。
2. 运行环境：Python 3.11+ 环境或 Docker 容器化环境。
3. 网络环境：支持 IPv6，能稳定访问 **[byr.pt](https://byr.pt/)**（北邮人 PT 站）。
4. qBittorrent 客户端：已在选项中**启用 Web 用户界面（远程控制）** 的 qBittorrent 客户端（当前推荐使用 v5.1.0 版本）。

### 使用方式一：在 Python 环境下直接运行

> 该方案更适合有本地调试或二次开发需求的用户，需要自行处理进程常驻和后台运行的问题。如无必要，推荐直接使用 Docker 方式运行。

首先将项目克隆到本地环境：

~~~bash
git clone https://github.com/yliu7949/byr.git
cd byr
~~~

复制项目提供的示例配置文件，使用你喜欢的文本编辑器编辑它：

~~~bash
cp .env.example .env
~~~

在 `.env` 文件中，请填写以下重要信息：

~~~dotenv
# BYRBT 账号信息
BYRBT_USERNAME="你的用户名"
BYRBT_PASSWORD="你的密码"

# qBittorrent Web 用户界面连接信息
QBITTORRENT_HOST="https://你的服务器地址:端口"
QBITTORRENT_USERNAME="qBittorrent 用户名"
QBITTORRENT_PASSWORD="qBittorrent 密码"
QBITTORRENT_DOWNLOAD_PATH="/downloads"

# 做种文件最大存储容量（单位：GB）
MAX_TORRENTS_SIZE=1024
~~~

安装 Python 依赖：

```bash
# 使用 pip 安装依赖
python -m pip install --upgrade pip
python -m pip install .

# 或者使用 uv 安装依赖
uv pip install .
```

完成上述步骤后，运行以下命令即可启动：

```bash
python main.py
```

### 使用方式二：快速部署 Docker 容器

> 想要更简单的运行方式？那就使用即开即用的 Docker 镜像！

在部署 Docker 容器前，需要按照前面所述的方式准备 `.env` 配置文件：

```bash
cp .env.example .env
```

填写完成 `.env` 文件中的配置后，可通过以下步骤启动 Docker 容器：

~~~bash
# 拉取最新容器镜像
docker pull yliu7949/byr:latest

# 启动容器
sudo docker run -d \
  --name byr \
  --user root \
  --network host \
  --restart unless-stopped \
  -e TZ=Asia/Shanghai \
  -v $(pwd)/.env:/app/.env \
  yliu7949/byr:latest
~~~

参数说明：

- `-v`：指定 `.env` 配置文件的完整路径

如果想要实时查看容器的运行日志，可以使用以下命令：

```bash
# 查看容器的实时输出
sudo docker logs -f byr
```

## 贡献指南

**🎯** 欢迎提交 **Issues** 和 **PR**！

- **新功能？** 请先在 Issue 中详细说明需求，讨论确认后再提交代码。
- **修复 Bug？** 可以直接提交 PR，请附上问题描述和修复方案。

本项目采用 **GPL‑3.0** 许可证，你的贡献将被视为接受该协议。感谢你的支持！🌟

## 致谢

本项目基于开源项目 [`byrbt_bot`](https://github.com/lipssmycode/byrbt_bot) 开发，保留了部分核心代码并进行了功能完善。特别感谢原作者的贡献！

## 许可证

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fyliu7949%2Fbyr.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fyliu7949%2Fbyr?ref=badge_large)
