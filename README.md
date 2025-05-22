# QQ 聊天机器人 (NcatBot & LLM-Powered)

一款基于大型语言模型 API 和 NcatBot 框架的聊天机器人，专为 QQ 平台设计，具有灵活的配置和可扩展性。

## 主要功能

* **QQ平台集成**：基于 NcatBot，支持 QQ 群聊和私聊互动。
* **多 LLM 支持**：通过可配置的 `LLMInterface` 支持多种大模型 API（如 智谱AI GLM, OpenAI, Anthropic Claude）。
* **上下文对话**：能够记忆用户的历史消息，实现连续对话。
* **插件化消息处理**：核心聊天逻辑（包括历史管理、特定指令处理）由 `plugins/qq_bot.py` 插件管理。
* **灵活配置**：大量参数通过 `.env` 文件进行配置，包括 API 密钥、模型选择、机器人行为等。
* **数据本地化**：聊天记录、日志等数据保存在项目根目录下的 `data` 文件夹内。

## 环境准备

* Python 3.8+
* 安装所需 Python 依赖：
    ```bash
    pip install -r requirements.txt
    ```
    (请确保 `requirements.txt` 文件包含 `ncatbot`, `loguru`, `python-dotenv`, `openai`, `anthropic`, `zhipuai` 等必要库)
* **NcatBot 环境**:
    1.  安装 NcatBot: `pip install ncatbot -U -i https://mirrors.aliyun.com/pypi/simple/`
    2.  确保系统安装了 QQ >= 9.9.16.18 (2024年8月之后安装的QQ都可以使用)。
    3.  确保网络环境放通本机 NcatBot 所需端口 (通常是 6099 和 3001)。

## 项目结构

````

.
├── bot.py                      \# 主启动脚本
├── plugins/                    \# 插件目录
│   ├── **init**.py             \# 包初始化文件
│   ├── llm\_api.py              \# LLM API 统一接口封装
│   └── qq\_bot.py               \# QQ 机器人核心消息处理与命令插件
├── data/                       \# 数据存储目录 (自动创建)
│   ├── chat\_history/           \# 聊天历史记录 (JSON格式)
│   └── logs/                   \# 运行日志文件
├── .env                        \# 环境变量配置文件 (需手动创建)
├── .env.example                \# 环境变量配置文件模板 (可选，建议提供)
├── README.md                   \# 本说明文件
└── requirements.txt            \# Python 依赖列表



## 配置步骤

1.  **创建 `.env` 配置文件**:
    复制项目中的 `.env.example` (如果提供) 或根据下面的模板手动创建名为 `.env` 的文件，并填写您的配置信息。

    ```ini
    # --- 机器人QQ平台设置 (NcatBot) ---
    # 机器人运行的QQ号
    BT_UIN=your_bot_qq_number_here
    # 机器人管理员QQ号
    ROOT=your_admin_qq_number_here

    # --- LLM 提供商选择 ---
    # 指定使用哪个大模型提供商: "zhipu", "openai", "claude"
    LLM_PROVIDER=zhipu

    # --- ZhipuAI (智谱GLM) API 配置 (如果 LLM_PROVIDER="zhipu") ---
    ZHIPUAI_API_KEY=your_zhipuai_api_key_here
    GLM_MODEL=glm-4-flash
    GLM_MAX_TOKENS=8192
    GLM_ENABLE_WEB_SEARCH=true # 对于智谱AI，此选项通常由代码强制或默认为true
    GLM_TEMPERATURE=0.7

    # --- OpenAI API 配置 (如果 LLM_PROVIDER="openai") ---
    OPENAI_API_KEY=your_openai_api_key_here
    OPENAI_MODEL=gpt-3.5-turbo
    OPENAI_MAX_TOKENS=4096
    # OPENAI_TEMPERATURE=0.7 # (可选) 如需控制，需修改代码以读取并使用

    # --- Anthropic (Claude) API 配置 (如果 LLM_PROVIDER="claude") ---
    ANTHROPIC_API_KEY=your_anthropic_api_key_here
    CLAUDE_MODEL=claude-3-sonnet-20240229
    CLAUDE_MAX_TOKENS=4096
    # CLAUDE_TEMPERATURE=0.7 # (可选) 如需控制，需修改代码以读取并使用

    # --- QQ Bot 插件 (plugins/qq_bot.py) 特定设置 ---
    # qq_bot.py 使用的系统提示词
    QQBOT_SYSTEM_PROMPT="你是一个名为ChatGLM-Flash的AI助手，具备联网搜索能力，可以用它来回答需要实时信息的问题。"
    # qq_bot.py 保留的用户与助手对话消息数量 (不包括系统提示词本身)
    # 设置为 40，则总消息数 (含系统提示) 为 41
    QQBOT_MAX_HISTORY_LENGTH="40"
    ```

2.  **确认插件路径**：
    确保 `llm_api.py` 和 `qq_bot.py` 文件位于项目根目录下的 `plugins` 文件夹内，并且 `plugins` 文件夹包含一个空的 `__init__.py` 文件。

## 运行机器人

直接运行主脚本 `bot.py`：

```bash
python bot.py
````

首次运行时，NcatBot 可能会需要通过扫描二维码登录机器人QQ账号。请留意控制台输出。

## 与机器人交互 (通过 `plugins/qq_bot.py` 实现)

  * **私聊**：直接向机器人发送消息即可开始对话。
  * **群聊**：在群聊中 `@机器人 + 问题` 来与机器人进行交互。
  * **清除会话**：发送 `清除会话` 给机器人（私聊或群聊@机器人后发送），可以清除当前对话（私聊或对应群聊）的上下文历史记录。
  * **帮助指令**：发送 `帮助` 或 `help` 给机器人，可以查看可用的指令和当前配置信息。

## 自定义与扩展

  * **LLM API 扩展**：修改 `plugins/llm_api.py` 文件可以集成或调整对不同大型语言模型的 API 调用逻辑。
  * **机器人核心功能扩展**：修改 `plugins/qq_bot.py` 文件可以扩展或更改机器人的命令处理、对话管理风格、系统提示词逻辑等。
  * **NcatBot 事件处理**：`bot.py` 文件负责 NcatBot 的事件注册和基础消息分发。如果需要更底层的事件处理或添加不通过LLM插件的特定回复，可以在此文件修改。

## 数据存储

所有动态生成的数据都存储在项目根目录下的 `data` 文件夹中：

  * `data/chat_history/`：存储每个会话（私聊或群聊）的聊天历史记录，以 `session_id.json` 的格式保存。`session_id` 通常是 `private_用户QQ` 或 `group_群号`。
  * `data/logs/`：存储机器人运行时的详细日志文件，便于排查问题。

这种设计确保了数据的集中管理，方便备份和迁移。

## 贡献指南

我们欢迎并鼓励开发者通过pull request来改进本项目！如果您有任何想法或功能建议，请随时提交pull request。让我们一起让这个QQ机器人变得更强大、更智能！

当前最需要改进的方面包括：
- 添加更多LLM提供商的支持
- 开发新的插件功能
- 优化现有代码结构
- 改进文档和示例

期待您的贡献！



-----

## 云服务器部署详细指南 (Linux + systemd) ☁️

本指南将详细介绍如何在云服务器（以使用 `systemd` 的现代 Linux 发行版如 Ubuntu, CentOS 为例）上部署和持久化运行您的 QQ 聊天机器人。

### 1\. 前提条件 ✅

  * **云服务器**: 您需要一台已购买并配置好基本网络和安全设置的云服务器。
  * **操作系统**: 推荐使用较新的 Linux 发行版，如 Ubuntu 20.04 LTS 或更高版本，CentOS 7 或更高版本（或其衍生版如 AlmaLinux, Rocky Linux）。
  * **SSH 访问**: 您需要能够通过 SSH 客户端（如 PuTTY, OpenSSH, Termius）以具有 `sudo` 权限的用户登录服务器。
  * **Python 环境**: 服务器上需要安装 Python 3.8 或更高版本。
      * 检查 Python 版本: `python3 --version`
      * 如果未安装或版本过低，请根据您的 Linux 发行版安装/升级 Python。例如，在 Ubuntu上：
        ```bash
        sudo apt update
        sudo apt install python3 python3-pip python3-venv -y
        ```
  * **Git**: 用于从代码仓库拉取项目（如果您的代码在 Git 仓库中）。
    ```bash
    sudo apt install git -y # Ubuntu
    # sudo yum install git -y # CentOS
    ```

### 2\. 项目部署 📂

1.  **登录服务器**: 通过 SSH 登录到您的云服务器。
2.  **选择项目目录**: 选择一个合适的目录来存放您的机器人项目。例如，用户的主目录下：
    ```bash
    cd ~ # 进入用户主目录
    mkdir my_qq_bot # 创建项目文件夹
    cd my_qq_bot
    ```
3.  **获取项目文件**:
      * **如果使用 Git**:
        ```bash
        git clone your_repository_url . # 将 your_repository_url 替换为您的仓库地址，"." 表示克隆到当前目录
        ```
      * **如果手动上传**: 使用 FTP/SFTP 工具 (如 FileZilla, WinSCP) 将您本地的项目文件夹（包含 `bot.py`, `plugins/`, `.env` 等）上传到服务器上您创建的 `my_qq_bot` 目录中。
4.  **创建并激活 Python 虚拟环境**: 强烈建议使用虚拟环境来隔离项目依赖。
    ```bash
    python3 -m venv venv # 创建名为 venv 的虚拟环境
    source venv/bin/activate # 激活虚拟环境，之后命令提示符前会出现 (venv)
    ```
      * *注意*: 之后所有 Python 和 pip 命令都将在此虚拟环境内执行。
5.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```
6.  **创建并配置 `.env` 文件**:
      * 在项目根目录下（例如 `~/my_qq_bot/`），根据我们之前讨论的模板创建 `.env` 文件。
      * 请务必填写正确的 API 密钥、机器人 QQ 号 (`BT_UIN`)、管理员 QQ 号 (`ROOT`) 以及其他相关配置。
      * **权限**: 确保 `.env` 文件有适当的读取权限，但不要过度开放。通常，所有者可读写即可。
        ```bash
        chmod 600 .env # 设置文件权限，仅所有者可读写
        ```
7.  **创建数据和日志目录**: 虽然代码会自动创建，但预先创建并检查权限有时能避免问题。
    ```bash
    mkdir -p data/chat_history
    mkdir -p data/logs
    ```
    确保运行服务的用户对 `data` 目录及其子目录有写入权限。

### 3\. 设置 NcatBot 环境和 QQ 依赖 🐧

1.  **NcatBot 安装**: 确保 `requirements.txt` 中的 `ncatbot` 已正确安装到虚拟环境中。
2.  **QQ 客户端依赖**: NcatBot 通常依赖于一个 QQ 客户端。
      * **Wine (如果需要运行 Windows QQ)**: 如果 NcatBot 的实现依赖于在 Linux 上运行 Windows版本的 QQ（某些旧的或特定的框架可能如此，但现代 NcatBot 可能有其他机制），您可能需要安装 Wine。但根据您提供的 `README.md` 信息 "确保系统安装了 QQ \>= 9.9.16.18"，这暗示可能直接与系统中的 QQ 或其特定版本交互，或者 NcatBot 本身已包含所需组件。**请务必查阅您所使用的 NcatBot 版本的具体文档，了解其在 Linux 服务器上的确切运行要求。**
      * **headless QQ / Linux QQ**: 如果 NcatBot 支持或需要原生的 Linux QQ 或 headless 模式的 QQ，请按其文档指引进行安装和配置。
      * **端口**: 确保服务器防火墙（如 `ufw`, `firewalld`）已放通 NcatBot 所需的端口（您提到的是 6099 和 3001）。
          * **UFW (Ubuntu)**:
            ```bash
            sudo ufw allow 6099/tcp
            sudo ufw allow 3001/tcp
            sudo ufw reload
            sudo ufw status
            ```
          * **Firewalld (CentOS/RHEL)**:
            ```bash
            sudo firewall-cmd --permanent --add-port=6099/tcp
            sudo firewall-cmd --permanent --add-port=3001/tcp
            sudo firewall-cmd --reload
            sudo firewall-cmd --list-ports
            ```

### 4\. 使用 `systemd` 设置后台持久运行 ⚙️

`systemd`是现代 Linux 系统中用于管理系统进程和服务的标准工具。使用它能确保您的机器人在服务器重启后自动运行，并在意外崩溃时自动重启。

1.  **创建 `systemd` 服务单元文件**:
    在 `/etc/systemd/system/` 目录下创建一个新的服务文件，例如 `qqbot.service`：

    ```bash
    sudo nano /etc/systemd/system/qqbot.service
    ```

    将以下内容粘贴到文件中，并**务必根据您的实际路径和用户名进行修改**：

    ```ini
    [Unit]
    Description=QQ LLM ChatBot Service for my_qq_bot
    After=network.target # 表示在网络连接可用后启动

    [Service]
    # --- 用户和工作目录 ---
    User=your_linux_username # 替换为实际运行此服务的Linux用户名 (非常重要!)
    Group=your_linux_group   # 替换为该用户的组名 (通常与用户名相同)
    WorkingDirectory=/home/your_linux_username/my_qq_bot # 替换为项目的绝对路径 (非常重要!)

    # --- 启动命令 ---
    # 确保使用虚拟环境中的python解释器
    ExecStart=/home/your_linux_username/my_qq_bot/venv/bin/python bot.py

    # --- 重启策略 ---
    Restart=always     # 总是在服务退出时重启 (除非是正常停止)
    RestartSec=10      # 重启前等待10秒

    # --- 日志记录 (可选，但推荐) ---
    # systemd 会通过 journald 记录标准输出和标准错误
    # 如果希望将日志输出到特定文件，可以取消注释并修改以下行：
    # StandardOutput=append:/home/your_linux_username/my_qq_bot/data/logs/qqbot_stdout.log
    # StandardError=append:/home/your_linux_username/my_qq_bot/data/logs/qqbot_stderr.log

    # --- 环境变量文件 (重要!) ---
    # 指定 .env 文件的位置，systemd 会加载它
    EnvironmentFile=/home/your_linux_username/my_qq_bot/.env

    [Install]
    WantedBy=multi-user.target # 表示在多用户模式下启用此服务
    ```

    **关键修改点**:

      * `User`: 运行服务的 Linux 用户。**不要使用 `root` 用户运行应用程序，除非绝对必要，这有安全风险。** 创建一个专用用户或使用您的普通用户。
      * `Group`: 通常与 `User` 相同。
      * `WorkingDirectory`: 项目的**绝对根目录**。
      * `ExecStart`: 启动 `bot.py` 的命令，确保它指向**虚拟环境中的 Python 解释器** (`venv/bin/python`)。
      * `EnvironmentFile`: 指向您的 `.env` 文件的**绝对路径**。这使得 `systemd` 服务能够访问您定义的环境变量。

2.  **重载 `systemd` 配置**: 告知 `systemd` 有了新的服务文件。

    ```bash
    sudo systemctl daemon-reload
    ```

3.  **启动服务**:

    ```bash
    sudo systemctl start qqbot
    ```

4.  **检查服务状态**:

    ```bash
    sudo systemctl status qqbot
    ```

    如果一切正常，您应该会看到 `active (running)` 的状态。如果服务启动失败，状态信息通常会给出一些线索。

5.  **查看日志**: `systemd` 通过 `journald` 管理日志。

      * 查看实时日志:
        ```bash
        sudo journalctl -u qqbot -f
        ```
      * 查看最近的日志:
        ```bash
        sudo journalctl -u qqbot -e --no-pager
        ```

    如果之前在服务文件中配置了 `StandardOutput` 和 `StandardError` 重定向到文件，也可以直接查看那些文件。

6.  **设置开机自启**:

    ```bash
    sudo systemctl enable qqbot
    ```

    这样，在服务器重启后，`qqbot` 服务会自动启动。

7.  **停止或重启服务**:

      * 停止服务: `sudo systemctl stop qqbot`
      * 重启服务: `sudo systemctl restart qqbot`

### 5\. 首次运行与登录 🚀

  * 当您通过 `systemd` **首次启动**服务时，NcatBot 可能需要在控制台进行扫码登录。
  * 因为 `systemd` 服务在后台运行，您可能无法直接看到二维码。
  * **解决方案**:
    1.  **临时前台运行**: 在配置好 `systemd` 服务文件但**未启动或已停止**服务的情况下，手动在前台运行一次机器人以完成扫码登录：
        ```bash
        cd ~/my_qq_bot # 进入项目目录
        source venv/bin/activate # 激活虚拟环境
        python bot.py # 在前台运行
        ```
        此时，如果需要扫码，二维码会显示在您的 SSH 终端中。完成扫码登录，并确认机器人能正常工作。之后按 `Ctrl+C` 停止它。
    2.  **NcatBot 持久化登录**: 许多 QQ 框架（包括 NcatBot 的某些实现或其依赖）在成功登录后会保存 session/token 信息（通常在 `data` 目录或特定配置文件中），使得后续启动不再需要扫码。确保这个机制正常工作。
    3.  **启动 `systemd` 服务**: 完成扫码后，再通过 `sudo systemctl start qqbot` 启动后台服务。

### 6\. 维护与更新 🛠️

  * **更新代码**:
    1.  `cd ~/my_qq_bot`
    2.  `git pull` (如果使用 Git) 或重新上传新文件。
    3.  `source venv/bin/activate`
    4.  `pip install -r requirements.txt` (如果依赖有更新)
    5.  `sudo systemctl restart qqbot` (重启服务以应用更改)
  * **查看日志**: 定期检查 `journalctl -u qqbot` 或您指定的日志文件，监控机器人运行状况。

通过以上步骤， QQ 聊天机器人应该可在云服务器上稳定、持久地运行。务必仔细替换所有路径和用户名占位符。