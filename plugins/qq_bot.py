import asyncio
import os
import json
import time
from loguru import logger
from typing import List, Dict, Any, Optional

from .llm_api import LLMInterface # 确保 llm_api.py 在同一目录下或正确配置的包路径下

# 获取数据目录路径
# __file__ 是当前脚本 (qq_bot.py) 的路径
# os.path.dirname(__file__) 是 qq_bot.py 所在的目录 (例如 plugins/)
# os.path.dirname(os.path.dirname(__file__)) 是 plugins/ 的上一级目录 (即项目根目录)
PROJECT_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT_DIR, "data")
CHAT_HISTORY_DIR = os.path.join(DATA_DIR, "chat_history")

# 存储对话历史的字典，键为用户ID，值为消息列表
user_sessions: Dict[str, List[Dict[str, str]]] = {}

# --- 从环境变量读取配置，并提供默认值 ---
# 系统提示词
SYSTEM_PROMPT = os.getenv("QQBOT_SYSTEM_PROMPT", """你是一个名为ChatGLM-Flash的AI助手，具备联网搜索能力，可以用它来回答需要实时信息的问题。""")
logger.info(f"QQBOT_SYSTEM_PROMPT 加载为: '{SYSTEM_PROMPT[:100]}...'")

# 会话历史长度上限
try:
    MAX_HISTORY_LENGTH = int(os.getenv("QQBOT_MAX_HISTORY_LENGTH", "10"))
    logger.info(f"QQBOT_MAX_HISTORY_LENGTH 加载为: {MAX_HISTORY_LENGTH}")
except ValueError:
    logger.warning(f"环境变量 QQBOT_MAX_HISTORY_LENGTH 的值 '{os.getenv('QQBOT_MAX_HISTORY_LENGTH')}' 不是有效的整数，将使用默认值 10。")
    MAX_HISTORY_LENGTH = 10
# --- 配置读取结束 ---

# 加载用户会话历史
def load_user_sessions():
    """从文件加载所有用户的会话历史"""
    global user_sessions

    if not os.path.exists(CHAT_HISTORY_DIR):
        os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)
        logger.info(f"聊天历史目录 {CHAT_HISTORY_DIR} 已创建。")
        return

    logger.info(f"开始从 {CHAT_HISTORY_DIR} 加载用户会话历史...")
    loaded_count = 0
    for filename in os.listdir(CHAT_HISTORY_DIR):
        if filename.endswith('.json'):
            user_id = filename[:-5] # 移除 '.json' 后缀
            file_path = os.path.join(CHAT_HISTORY_DIR, filename)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    # 校验并可能更新 system prompt
                    if not session_data or not isinstance(session_data, list) or not session_data[0].get("role") == "system":
                        logger.warning(f"用户 {user_id} 的历史记录格式不正确或缺少系统提示，将重新初始化。")
                        user_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
                    elif session_data[0].get("content") != SYSTEM_PROMPT:
                        logger.info(f"用户 {user_id} 的系统提示词与当前配置不同，将使用新的系统提示词更新会话。")
                        session_data[0]["content"] = SYSTEM_PROMPT
                        user_sessions[user_id] = session_data
                    else:
                        user_sessions[user_id] = session_data
                    loaded_count += 1
            except json.JSONDecodeError:
                logger.error(f"解析用户 {user_id} 的会话历史文件 {file_path} 失败 (JSON格式错误)，将为此用户创建新会话。")
                user_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
            except Exception as e:
                logger.error(f"加载用户 {user_id} 的会话历史时出错 ({file_path}): {e}，将为此用户创建新会话。")
                user_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if loaded_count > 0:
        logger.info(f"成功加载了 {loaded_count} 个用户的会话历史。")
    else:
        logger.info("未找到任何已保存的用户会话历史文件。")

# 保存用户会话历史到文件
def save_user_session(user_id: str):
    """将用户会话历史保存到文件"""
    if user_id not in user_sessions:
        logger.warning(f"尝试保存用户 {user_id} 的会话历史，但该用户不在内存中。")
        return

    if not os.path.exists(CHAT_HISTORY_DIR):
        try:
            os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)
            logger.info(f"聊天历史目录 {CHAT_HISTORY_DIR} 在保存时创建。")
        except Exception as e:
            logger.error(f"创建聊天历史目录 {CHAT_HISTORY_DIR} 失败: {e}，无法保存会话。")
            return

    file_path = os.path.join(CHAT_HISTORY_DIR, f"{user_id}.json")

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(user_sessions[user_id], f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存用户 {user_id} 的会话历史到 {file_path} 时出错: {e}")

# 初始化时加载会话历史
load_user_sessions()

async def process_message_content(user_id: str, message_text: str) -> Optional[str]:
    """
    处理用户消息内容，包括命令处理和与LLM交互。
    由 bot.py 中的 NcatBot 消息处理器调用。
    """
    logger.info(f"[process_message_content] 用户 {user_id} | 消息: '{message_text[:100]}...'")
    message_text = message_text.strip()

    if not message_text:
        logger.info(f"[process_message_content] 用户 {user_id} | 消息内容为空，忽略。")
        return None

    if message_text.lower() == "清除会话":
        logger.info(f"[process_message_content] 用户 {user_id} | 检测到清除会话命令。")
        return await handle_clear_session(user_id)
    elif message_text.lower() in ["帮助", "help"]:
        logger.info(f"[process_message_content] 用户 {user_id} | 检测到帮助命令。")
        return await handle_help()

    if user_id not in user_sessions:
        logger.info(f"[process_message_content] 用户 {user_id} | 初始化新会话。")
        user_sessions[user_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    elif user_sessions[user_id] and user_sessions[user_id][0].get("content") != SYSTEM_PROMPT:
        logger.info(f"[process_message_content] 用户 {user_id} | 系统提示词已更改，更新当前会话的系统提示。")
        user_sessions[user_id][0]["content"] = SYSTEM_PROMPT

    user_sessions[user_id].append({"role": "user", "content": message_text})

    if len(user_sessions[user_id]) > MAX_HISTORY_LENGTH + 1:
        logger.info(f"[process_message_content] 用户 {user_id} | 会话历史 ({len(user_sessions[user_id])}条) 超出限制 ({MAX_HISTORY_LENGTH + 1}条)，进行截断。")
        system_message = user_sessions[user_id][0]
        recent_messages = user_sessions[user_id][-(MAX_HISTORY_LENGTH):]
        user_sessions[user_id] = [system_message] + recent_messages
        logger.debug(f"[process_message_content] 用户 {user_id} | 截断后会话长度: {len(user_sessions[user_id])}")

    try:
        response = await LLMInterface.generate_response(
            messages=user_sessions[user_id]
        )

        if response:
            user_sessions[user_id].append({"role": "assistant", "content": response})
            if len(user_sessions[user_id]) > MAX_HISTORY_LENGTH + 1: # 再次检查
                system_message = user_sessions[user_id][0]
                recent_messages = user_sessions[user_id][-(MAX_HISTORY_LENGTH):]
                user_sessions[user_id] = [system_message] + recent_messages
            save_user_session(user_id)
        else:
            logger.warning(f"[process_message_content] 用户 {user_id} | LLM未返回有效内容。")
        return response
    except Exception as e:
        logger.exception(f"[process_message_content] 用户 {user_id} | 处理消息时调用LLM出错: {e}")
        return f"抱歉，处理您的消息时内部出现了错误: {str(e)}"

async def handle_clear_session(user_id: str) -> str:
    logger.info(f"[handle_clear_session] 用户 {user_id} | 处理清除会话命令。")
    if user_id in user_sessions:
        user_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        save_user_session(user_id)
        logger.info(f"[handle_clear_session] 用户 {user_id} | 会话历史已清除并保存。")
        return "您的会话历史已清除！"
    else:
        logger.warning(f"[handle_clear_session] 用户 {user_id} | 未找到会话历史，仍尝试初始化。")
        user_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        save_user_session(user_id)
        return "没有找到您的会话历史，已为您初始化新会话。"

async def handle_help() -> str:
    logger.info(f"[handle_help] 处理帮助命令。")
    help_text = f"""
QQ机器人指令帮助：
1. 私聊直接发送问题，我会尽力回答。
2. 群聊中@我并发送问题。
3. 发送 "清除会话" 可以清除当前对话的历史记录。
4. 发送 "帮助" 或 "help" 查看此帮助信息。

当前对话设置：
- 系统提示词: "{SYSTEM_PROMPT[:50]}..."
- 最大历史消息保留: {MAX_HISTORY_LENGTH} (指用户与助手的对话消息)

祝您使用愉快！
"""
    return help_text