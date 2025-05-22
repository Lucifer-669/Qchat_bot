import os
import asyncio
import sys
from typing import List, Dict, Any, Optional
import re

from loguru import logger

# --- 尽早尝试加载 .ENV ---
try:
    from dotenv import load_dotenv

    if load_dotenv():
        logger.info("在 bot.py 顶层成功加载 .env 文件。")
    else:
        logger.info("在 bot.py 顶层加载 .env：未找到 .env 文件或文件为空。")
except ImportError:
    logger.info("python-dotenv 未安装，跳过在 bot.py 顶层的 .env 加载。")
# --- .ENV 早加载结束 ---

# --- 从 llm_api.py 导入 LLMInterface ---
from plugins.llm_api import LLMInterface

# --- 从 qq_bot.py 导入消息处理函数 ---
try:
    from plugins.qq_bot import process_message_content

    QQ_BOT_PLUGIN_AVAILABLE = True
    logger.info("已成功从 plugins.qq_bot 导入 process_message_content。")
except ImportError as e:
    QQ_BOT_PLUGIN_AVAILABLE = False
    process_message_content = None  # type: ignore
    logger.error(f"无法从 plugins.qq_bot 导入 process_message_content: {e}")
    logger.error("请确保 qq_bot.py 文件位于 plugins 文件夹下，并且 plugins 文件夹包含 __init__.py 文件。")
    # 如果插件不可用，机器人可能无法正常处理消息，这里可以决定是否退出或以受限模式运行

# --- SDK 导入 (仅保留 NcatBot 相关) ---
try:
    from ncatbot.core import BotClient, GroupMessage, PrivateMessage, MessageChain, Text, At, Image, Face, Reply

    NCATBOT_AVAILABLE = True
except ImportError:
    NCATBOT_AVAILABLE = False
    BotClient, GroupMessage, PrivateMessage, MessageChain, Text, At, Image, Face, Reply = [None] * 9  # type: ignore

# --- 数据目录与全局变量 ---
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
modules_status: Dict[str, bool] = {}
if NCATBOT_AVAILABLE and BotClient:
    bot = BotClient()
else:
    bot = None  # type: ignore


# --- 原有的对话历史存储 (内存中) ---
# conversation_history: Dict[str, List[Dict[str, Any]]] = {} # 已被 qq_bot.py 中的逻辑取代
# MAX_HISTORY_MESSAGES = 41 # 已被 qq_bot.py 中的逻辑取代
# DEFAULT_SYSTEM_PROMPT = "你是一个名为ChatGLM-Flash的AI助手，具备联网搜索能力，可以用它来回答需要实时信息的问题。" # 已被 qq_bot.py 中的逻辑取代


def load_configurations() -> bool:
    # .env 文件已在模块顶部加载，这里主要处理 config.py 和其他逻辑
    config_loaded_env = True  # 假设顶层加载已处理，或在此处再次调用 load_dotenv() 也可
    config_loaded_py = False
    logger.info("开始加载自定义配置 (config.py 及后续处理)...")

    # 再次调用 load_dotenv() 是安全的，如果顶层已加载，它不会重复加载
    try:
        from dotenv import load_dotenv
        if load_dotenv():
            logger.info("在 load_configurations 中确认 .env 文件已加载。")
            config_loaded_env = True
        # else: # 不需要else，因为顶层已经记录过未找到的情况
    except ImportError:
        pass  # 顶层已经记录过未安装的情况

    try:
        import config
        logger.info("尝试从自定义 config.py 加载配置...")
        config_py_vars_map = {
            "LLM_PROVIDER": "LLM_PROVIDER",
            "GLM_MODEL": "GLM_MODEL",
            "GLM_MAX_TOKENS": "GLM_MAX_TOKENS",
            "GLM_ENABLE_WEB_SEARCH": "GLM_ENABLE_WEB_SEARCH",
            "GLM_TEMPERATURE": "GLM_TEMPERATURE",
            "OPENAI_MODEL": "OPENAI_MODEL",
            "OPENAI_MAX_TOKENS": "OPENAI_MAX_TOKENS",
            "CLAUDE_MODEL": "CLAUDE_MODEL",
            "CLAUDE_MAX_TOKENS": "CLAUDE_MAX_TOKENS",
            "BT_UIN": "BT_UIN",
            "ROOT": "ROOT",
        }
        something_loaded_from_config_py = False
        for attr_name, env_key in config_py_vars_map.items():
            if env_key not in os.environ:  # 仅当环境变量中不存在时，才从config.py加载
                if hasattr(config, attr_name):
                    value_from_config = getattr(config, attr_name)
                    if value_from_config is not None:
                        os.environ[env_key] = str(value_from_config)
                        logger.debug(
                            f"从 config.py 加载到环境变量: {env_key}='{value_from_config}' (因.env或系统未提供)")
                        something_loaded_from_config_py = True
        if something_loaded_from_config_py:
            config_loaded_py = True
            logger.info("部分配置从 config.py 加载（作为 .env 或系统变量的后备）。")
        else:
            logger.info("config.py 中未找到需要加载的新配置（可能所有配置已由 .env 或系统变量提供）。")
    except ImportError:
        logger.warning("未找到 config.py，跳过 config.py 加载。")
    except AttributeError as e:
        logger.error(f"访问 config.py 属性或 LLMInterface 属性时出错: {e}")
    except Exception as e:
        logger.error(f"加载 config.py 时发生未知错误: {e}")

    try:
        if "LLM_PROVIDER" in os.environ and os.environ["LLM_PROVIDER"]:
            os.environ["LLM_PROVIDER"] = os.environ["LLM_PROVIDER"].lower()
        if "GLM_ENABLE_WEB_SEARCH" in os.environ and os.environ["GLM_ENABLE_WEB_SEARCH"]:
            os.environ["GLM_ENABLE_WEB_SEARCH"] = os.environ["GLM_ENABLE_WEB_SEARCH"].lower()
    except Exception as e:
        logger.error(f"设置部分全局配置变量时出错: {e}")

    logger.info("自定义配置加载完成。")
    return config_loaded_env or config_loaded_py


# --- 模块初始化 ---
def initialize_modules_status() -> Dict[str, bool]:
    logger.info("开始初始化模块状态...")
    global modules_status
    modules_status = {
        "ncatbot": NCATBOT_AVAILABLE and (bot is not None),
        "qq_bot_plugin": QQ_BOT_PLUGIN_AVAILABLE and (process_message_content is not None)
    }
    for name, status in modules_status.items():
        logger.log("SUCCESS" if status else "WARNING", f"{name} {'检查通过' if status else '未加载/不可用'}。")
    if not modules_status["qq_bot_plugin"]:
        logger.critical("QQ Bot 核心插件 (qq_bot.py) 未能加载，机器人功能将受限或无法工作！")
    logger.info("模块状态初始化完成。")
    return modules_status


# --- NcatBot 事件回调 ---
if NCATBOT_AVAILABLE and BotClient and GroupMessage and PrivateMessage and bot:
    @bot.group_event()
    async def my_group_message_handler(msg: GroupMessage):
        logger.info(f"--- [NcatBot EVENT] Group message received ---")
        logger.debug(f"GroupID={msg.group_id}, UserID={msg.user_id}, RawMessage='{msg.raw_message[:200]}'")

        session_id = f"group_{msg.group_id}"
        effective_text = ""
        processed_prompt_for_llm = ""

        try:
            if msg.text: effective_text = msg.text.strip()
        except AttributeError:
            logger.warning("GroupMessage no 'text' attr, cleaning raw_message.")

        if not effective_text and msg.raw_message:
            cleaned_message = re.sub(r"\[CQ:[^\]]+\]", "", msg.raw_message).strip()
            effective_text = cleaned_message

        processed_prompt_for_llm = effective_text

        if effective_text == "测试":
            try:
                await msg.reply(text="NcatBot (群) 测试成功喵~ (来自bot.py)");
                logger.info(f"回复群 {msg.group_id} 测试。")
            except Exception as e:
                logger.exception(f"回复群测试失败: {e}")
            return

        if effective_text.startswith('/'): return

        bot_qq_str = os.getenv("BT_UIN")
        if not bot_qq_str:
            logger.warning("BT_UIN未配置。")
            return

        is_at_me = False
        try:
            is_at_me = msg.is_at_me()
            if is_at_me:
                logger.info(f"Bot被@ (is_at_me). effective_text: '{effective_text}'")
                if msg.text:
                    processed_prompt_for_llm = msg.text.strip()
                else:
                    processed_prompt_for_llm = re.sub(rf"\[CQ:at,qq={bot_qq_str}\]", "", msg.raw_message, 1).strip()
                    processed_prompt_for_llm = re.sub(r"\[CQ:[^\]]+\]", "", processed_prompt_for_llm).strip()
        except AttributeError:
            logger.warning(f"msg无is_at_me方法，回退CQ码检查@。")
            cq_at_bot_tag = f"[CQ:at,qq={bot_qq_str}]"
            if cq_at_bot_tag in msg.raw_message:
                is_at_me = True
                temp_cleaned = msg.raw_message.replace(cq_at_bot_tag, "", 1).strip()
                processed_prompt_for_llm = re.sub(r"\[CQ:[^\]]+\]", "", temp_cleaned).strip()
                logger.info(f"Bot被@ (CQ码检查). 清理后: '{processed_prompt_for_llm}'")

        if is_at_me:
            final_prompt = processed_prompt_for_llm
            logger.info(f"Bot被@, 最终Prompt for Plugin: '{final_prompt}' (session: {session_id})")

            if not QQ_BOT_PLUGIN_AVAILABLE or not process_message_content:
                logger.error(f"QQ Bot 核心插件未加载，无法处理群消息: {final_prompt}")
                try:
                    await msg.reply(text="抱歉，我的核心处理模块出了一点问题，暂时无法回复您。")
                except Exception as e_reply:
                    logger.exception(f"发送核心插件错误提示失败: {e_reply}")
                return

            if final_prompt:
                raw_reply_from_plugin = await process_message_content(session_id, final_prompt)

                response_to_send = ""
                log_message_detail = ""

                if raw_reply_from_plugin is None:
                    logger.info(f"插件 (qq_bot.py) 未对 '{final_prompt}' 返回任何内容 (session: {session_id})。")
                elif raw_reply_from_plugin == LLMInterface.SEARCH_NO_DATA_HINT:
                    response_to_send = "抱歉，我尝试联网搜索并综合我的知识，但还是未能找到相关信息。这可能是因为信息不公开，或者查询条件过于具体。请尝试换个更宽泛的词再问我吧！"
                    log_message_detail = "插件返回 SEARCH_NO_DATA_HINT"
                elif raw_reply_from_plugin == LLMInterface.SENSITIVE_CONTENT_HINT:
                    response_to_send = raw_reply_from_plugin
                    log_message_detail = "插件返回 SENSITIVE_CONTENT_HINT"
                elif raw_reply_from_plugin.startswith("AI服务") or \
                        raw_reply_from_plugin.startswith("不支持的") or \
                        raw_reply_from_plugin.startswith("抱歉，处理您的消息时出现了错误:") or \
                        raw_reply_from_plugin.startswith("抱歉，处理您的消息时内部出现了错误:"):  # 覆盖插件返回的两种错误前缀
                    response_to_send = raw_reply_from_plugin
                    log_message_detail = f"插件返回错误或API服务消息: '{raw_reply_from_plugin}'"
                else:
                    response_to_send = raw_reply_from_plugin
                    log_message_detail = f"插件返回内容: '{response_to_send[:50]}...'"

                if response_to_send:
                    try:
                        reply_elements = [At(msg.user_id), Text(" " + str(response_to_send))] if At and Text else []
                        if MessageChain and reply_elements:
                            await msg.reply(rtf=MessageChain(reply_elements))
                        else:
                            await msg.reply(text=f"@{msg.user_id} {str(response_to_send)}")
                        logger.info(f"{log_message_detail} (已回复群@, session {session_id})")
                    except Exception as e:
                        logger.exception(f"通过插件发送回复或提示失败: {e}")
            else:
                try:
                    await msg.reply(text="喵？艾特我有什么事吗？");
                    logger.info(f"回复群 {msg.group_id} 空@。")
                except Exception as e:
                    logger.exception(f"回复空@失败: {e}")


    @bot.private_event()
    async def my_private_message_handler(msg: PrivateMessage):
        logger.info(f"--- [NcatBot EVENT] Private message received ---")
        logger.debug(f"UserID={msg.user_id}, RawMessage='{msg.raw_message[:200]}'")

        session_id = f"private_{msg.user_id}"
        effective_text = msg.raw_message.strip() if msg.raw_message else ""

        if effective_text == "测试":
            try:
                await bot.api.post_private_msg(user_id=msg.user_id, text="NcatBot (私聊) 测试成功喵~ (来自bot.py)");
                logger.info(f"回复用户 {msg.user_id} 私聊测试。")
            except Exception as e:
                logger.exception(f"回复私聊测试失败: {e}")
            return

        if effective_text.startswith('/'): return

        if not QQ_BOT_PLUGIN_AVAILABLE or not process_message_content:
            logger.error(f"QQ Bot 核心插件未加载，无法处理私聊消息: {effective_text}")
            try:
                await bot.api.post_private_msg(user_id=msg.user_id,
                                               text="抱歉，我的核心处理模块出了一点问题，暂时无法回复您。")
            except Exception as e_reply:
                logger.exception(f"发送核心插件错误提示失败: {e_reply}")
            return

        if effective_text:
            raw_reply_from_plugin = await process_message_content(session_id, effective_text)

            response_to_send = ""
            log_message_detail = ""

            if raw_reply_from_plugin is None:
                logger.info(f"插件 (qq_bot.py) 未对 '{effective_text}' 返回任何内容 (session: {session_id})。")
            elif raw_reply_from_plugin == LLMInterface.SEARCH_NO_DATA_HINT:
                response_to_send = "抱歉，我尝试联网搜索并综合我的知识，但还是未能找到相关信息。这可能是因为信息不公开，或者查询条件过于具体。请尝试换个更宽泛的词再问我吧！"
                log_message_detail = "插件返回 SEARCH_NO_DATA_HINT"
            elif raw_reply_from_plugin == LLMInterface.SENSITIVE_CONTENT_HINT:
                response_to_send = raw_reply_from_plugin
                log_message_detail = "插件返回 SENSITIVE_CONTENT_HINT"
            elif raw_reply_from_plugin.startswith("AI服务") or \
                    raw_reply_from_plugin.startswith("不支持的") or \
                    raw_reply_from_plugin.startswith("抱歉，处理您的消息时出现了错误:") or \
                    raw_reply_from_plugin.startswith("抱歉，处理您的消息时内部出现了错误:"):
                response_to_send = raw_reply_from_plugin
                log_message_detail = f"插件返回错误或API服务消息: '{raw_reply_from_plugin}'"
            else:
                response_to_send = raw_reply_from_plugin
                log_message_detail = f"插件返回内容: '{response_to_send[:50]}...'"

            if response_to_send:
                try:
                    logger.debug(
                        f"准备发送私聊回复给 {msg.user_id} (session {session_id}). 内容: '{str(response_to_send)[:100]}...'")
                    await bot.api.post_private_msg(user_id=msg.user_id, text=str(response_to_send))
                    logger.info(f"{log_message_detail} (已回复私聊, session {session_id})")
                except Exception as e:
                    logger.exception(f"通过插件发送私聊回复或提示失败: {e}")
        elif msg.raw_message and not effective_text:
            logger.info(f"收到用户 {msg.user_id} 非文本私聊，未处理。")
else:
    logger.error("NcatBot 未加载或核心插件存在问题，无法注册事件处理。")

# --- 主程序入口 ---
if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    log_file_path = os.path.join(LOGS_DIR, "bot_{time}.log")
    try:
        logger.add(log_file_path, rotation="20 MB", level="DEBUG", compression="zip", encoding="utf-8", backtrace=True,
                   diagnose=True)
    except Exception as e:
        sys.stderr.write(f"CRITICAL: 添加文件日志失败: {e}\n")
    logger.info(f"--- 应用启动 ({os.path.basename(__file__)}) ---")

    if not load_configurations():  # .env 应该在顶层已加载，这里主要是config.py和后续处理
        logger.warning("自定义配置加载可能不完整或失败（主要指config.py部分）。")

    try:
        logger.info(
            f"最终生效LLM_PROVIDER (通过环境变量或config.py): '{os.getenv('LLM_PROVIDER', 'zhipu (代码后备)')}'")
        if os.getenv('LLM_PROVIDER', 'zhipu').lower() == 'zhipu':
            logger.info(f"最终生效GLM_MODEL: '{os.getenv('GLM_MODEL', LLMInterface.DEFAULT_ZHIPU_MODEL_FALLBACK)}'")
            logger.info(
                f"最终生效GLM_MAX_TOKENS: '{os.getenv('GLM_MAX_TOKENS', str(LLMInterface.DEFAULT_MAX_TOKENS_FALLBACK))}'")
            logger.info(
                f"GLM_ENABLE_WEB_SEARCH (来自环境/配置): '{os.getenv('GLM_ENABLE_WEB_SEARCH', '未设置，将由llm_api决定')}'")
        logger.info(f"会话历史长度和系统提示词现在由 plugins/qq_bot.py 内部定义和管理。")
    except AttributeError as e:
        logger.critical(
            f"启动时访问 LLMInterface 属性失败: {e}. 请确保 plugins/llm_api.py 已正确保存且定义了必要的类属性。程序退出。")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"启动时发生未知配置错误: {e}. 程序退出。")
        sys.exit(1)

    modules_status = initialize_modules_status()
    if not modules_status.get("ncatbot") or not bot:
        logger.critical("NcatBot 未初始化，程序退出。")
        sys.exit(1)
    if not modules_status.get("qq_bot_plugin"):
        logger.critical("核心 QQ Bot 插件 (qq_bot.py) 未能加载，程序退出。")
        sys.exit(1)

    bot_uin_to_run = os.getenv("BT_UIN")
    if not bot_uin_to_run:
        logger.critical("BT_UIN 未设置，程序退出。")
        sys.exit(1)

    try:
        logger.info(f"准备使用QQ号 {bot_uin_to_run} 启动 NcatBot...");
        bot.run(bt_uin=str(bot_uin_to_run));
        logger.info("NcatBot 已停止。")
    except KeyboardInterrupt:
        logger.info("机器人被用户手动中断。")
    except Exception as e:
        logger.exception("运行 NcatBot 时发生严重错误。")
    finally:
        logger.info(f"--- 应用结束 ---")