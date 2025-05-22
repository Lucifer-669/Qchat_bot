import os
import asyncio
import sys
from typing import List, Dict, Any, Optional
from loguru import logger

# --- LLM SDK 导入 ---
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    OPENAI_AVAILABLE = False
try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None
    ANTHROPIC_AVAILABLE = False
try:
    import zhipuai

    ZHIPUAI_AVAILABLE = True
except ImportError:
    zhipuai = None
    ZHIPUAI_AVAILABLE = False


class LLMInterface:
    """大模型API统一接口封装"""

    DEFAULT_MAX_TOKENS_FALLBACK = 8192
    DEFAULT_ZHIPU_MODEL_FALLBACK = "glm-4-flash"
    DEFAULT_OPENAI_MODEL_FALLBACK = "gpt-3.5-turbo"
    DEFAULT_CLAUDE_MODEL_FALLBACK = "claude-3-sonnet-20240229"

    SEARCH_NO_DATA_HINT = "[[SEARCH_NO_DATA_FOUND]]"
    SENSITIVE_CONTENT_HINT = "抱歉，我无法回答这类问题，这可能涉及到一些敏感内容。"

    @staticmethod
    async def generate_response(
            messages: List[Dict[str, str]],
            provider: Optional[str] = None,
            model: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: Optional[int] = None,
            enable_web_search: Optional[bool] = None,
            **kwargs
    ) -> str:
        effective_provider = (provider or os.getenv("LLM_PROVIDER", "zhipu")).lower()

        if model:
            effective_model = model
        else:
            if effective_provider == "zhipu":
                effective_model = os.getenv("GLM_MODEL", LLMInterface.DEFAULT_ZHIPU_MODEL_FALLBACK)
            elif effective_provider == "openai":
                effective_model = os.getenv("OPENAI_MODEL", LLMInterface.DEFAULT_OPENAI_MODEL_FALLBACK)
            elif effective_provider == "claude":
                effective_model = os.getenv("CLAUDE_MODEL", LLMInterface.DEFAULT_CLAUDE_MODEL_FALLBACK)
            else:
                effective_model = "unknown-model-fallback"  # Should not happen with default

        if max_tokens is not None:
            effective_max_tokens = max_tokens
        else:
            env_var_name = f"{effective_provider.upper()}_MAX_TOKENS"
            default_fallback_str = str(LLMInterface.DEFAULT_MAX_TOKENS_FALLBACK)
            effective_max_tokens_str = os.getenv(env_var_name, os.getenv("LLM_MAX_TOKENS", default_fallback_str))
            try:
                effective_max_tokens = int(effective_max_tokens_str)
            except ValueError:
                logger.warning(f"无效的 MAX_TOKENS 值 '{effective_max_tokens_str}', 回退到 {default_fallback_str}")
                effective_max_tokens = LLMInterface.DEFAULT_MAX_TOKENS_FALLBACK

        if enable_web_search is None:
            if effective_provider == "zhipu":
                logger.warning("enable_web_search 未由调用者明确提供给Zhipu，默认设为True以符合预期行为 (llm_api.py)")
                effective_enable_web_search = True
            else:
                effective_enable_web_search = False
        else:
            effective_enable_web_search = enable_web_search

        effective_temperature = temperature

        logger.debug(
            f"LLMInterface (llm_api.py): Effective - Provider='{effective_provider}', Model='{effective_model}', "
            f"MaxTokens='{effective_max_tokens}', WebSearch(param)='{enable_web_search}', EffectiveWebSearch='{effective_enable_web_search}', Temp='{effective_temperature}'"
        )

        try:
            if effective_provider == "openai":
                if not OPENAI_AVAILABLE: return "OpenAI SDK 未安装"
                return await LLMInterface._call_openai(messages, effective_model, effective_temperature,
                                                       effective_max_tokens)
            elif effective_provider == "claude":
                if not ANTHROPIC_AVAILABLE: return "Anthropic SDK 未安装"
                return await LLMInterface._call_claude(messages, effective_model, effective_temperature,
                                                       effective_max_tokens)
            elif effective_provider == "zhipu":
                if not ZHIPUAI_AVAILABLE: return "ZhipuAI SDK 未安装"
                return await LLMInterface._call_zhipu(messages, effective_model, effective_temperature,
                                                      effective_max_tokens,
                                                      effective_enable_web_search)
            else:
                return f"不支持的模型提供商: {effective_provider}"
        except Exception as e:
            logger.exception(f"生成回复时发生错误 ({effective_provider}, model: {effective_model}): {e}")
            return f"AI服务 ({effective_provider}) 暂时不可用: {str(e)}"

    @staticmethod
    async def _call_openai(messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: int) -> str:
        if not openai: return "OpenAI SDK not loaded (internal check)."
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key or openai_api_key == "your_openai_api_key_here": return "OpenAI API Key未配置"
        client = openai.AsyncOpenAI(api_key=openai_api_key)
        try:
            response = await client.chat.completions.create(model=model, messages=messages, temperature=temperature,
                                                            max_tokens=max_tokens)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.exception(f"OpenAI API 调用失败 (model: {model}): {e}")
            return f"OpenAI API 调用失败: {str(e)}"

    @staticmethod
    async def _call_claude(messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: int) -> str:
        if not anthropic: return "Anthropic SDK not loaded (internal check)."
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key == "your_anthropic_api_key_here": return "Anthropic API Key未配置"
        client = anthropic.AsyncAnthropic(api_key=api_key)
        system_messages = [m["content"] for m in messages if m["role"] == "system"]
        system_prompt = "\n".join(system_messages) if system_messages else None
        conversation = [m for m in messages if m["role"] != "system"]
        try:
            response = await client.messages.create(model=model, system=system_prompt, messages=conversation,
                                                    temperature=temperature, max_tokens=max_tokens)
            if response.content and isinstance(response.content, list) and len(response.content) > 0 and hasattr(
                    response.content[0], 'text'):
                return response.content[0].text or ""
            logger.warning(f"从Claude (model: {model}) 获取的响应内容格式不符合预期: {response}")
            return "从Claude获取的响应内容格式不符合预期"
        except Exception as e:
            logger.exception(f"Claude API 调用失败 (model: {model}): {e}")
            return f"Claude API 调用失败: {str(e)}"

    @staticmethod
    async def _call_zhipu(
            messages: List[Dict[str, str]], model_name: str, temperature: float,
            max_tokens: int, enable_web_search: bool
    ) -> str:
        if not zhipuai: return "ZhipuAI SDK not loaded (internal check)."
        api_key = os.getenv("ZHIPUAI_API_KEY")
        if not api_key or api_key == "your_zhipuai_api_key_here":  # 检查占位符
            return "ZhipuAI API Key未配置或仍为占位符"
        client = zhipuai.ZhipuAI(api_key=api_key)

        search_attempt_yielded_no_content = False
        response_content = ""

        # --- 第一次尝试 ---
        tools_config = []  # 修改变量名以更通用
        if enable_web_search:
            # 根据官方文档，为web_search添加search_engine参数
            web_search_tool = {
                "type": "web_search",
                "web_search": {
                    "enable": True,
                    "search_engine": "search_pro"  # 明确指定搜索引擎，即使是默认值
                }
            }
            # 可选：根据需要可以从环境变量读取并添加其他web_search参数
            # if os.getenv("ZHIPU_WEBSEARCH_REQUIRE_RESULT", "false").lower() == "true":
            #     web_search_tool["web_search"]["require_search"] = True
            # if os.getenv("ZHIPU_WEBSEARCH_RETURN_DETAILS", "false").lower() == "true":
            #     web_search_tool["web_search"]["search_result"] = True

            tools_config.append(web_search_tool)
            logger.info(f"智谱AI GLM ({model_name}, llm_api.py): 第一次尝试 - 联网搜索已启用 (引擎: search_std)。")
        else:
            logger.info(f"智谱AI GLM ({model_name}, llm_api.py): 第一次尝试 - 联网搜索未启用。")

        try:
            logger.debug(
                f"智谱AI GLM (llm_api.py, 第一次尝试) 参数: Model='{model_name}', Temp='{temperature}', "
                f"MaxTokens='{max_tokens}', Tools='{tools_config if tools_config else '无'}'"
            )
            response = client.chat.completions.create(
                model=model_name, messages=messages,
                temperature=max(0.01, min(temperature, 0.99)),
                max_tokens=max_tokens,
                tools=tools_config if tools_config else None,  # 传递构造好的tools
                stream=False
            )

            message = response.choices[0].message
            response_content = message.content or ""
            finish_reason = response.choices[0].finish_reason
            tool_calls = message.   tool_calls  # 检查模型是否要求工具调用

            logger.info(
                f"非流式 (第一次尝试) 完成 模型: {model_name}. "
                f"结束原因: '{finish_reason}', 是否有工具调用对象: {bool(tool_calls)}, "
                f"内容长度: {len(response_content)}"
            )

            if finish_reason == 'sensitive':
                logger.info(f"内容因敏感被模型 {model_name} 拦截 (第一次尝试)。")
                return LLMInterface.SENSITIVE_CONTENT_HINT

            if response_content:  # 如果API直接返回了内容（即使是搜索后的内容），则使用它
                return response_content

            # 如果没有直接内容，但模型要求工具调用（非web_search的预期行为，但作为一种情况处理）
            # 或者开启了web_search但模型返回空，且没有明确的工具调用，也视为搜索无内容
            if (tool_calls or finish_reason == 'tool_calls') and not response_content:
                logger.info(
                    f"模型 {model_name} (第一次尝试) 要求工具调用或因工具调用结束但未直接生成文本内容。"
                    f"准备进行第二次尝试（不使用联网搜索）。"
                )
                search_attempt_yielded_no_content = True
            elif enable_web_search and not response_content:  # 开启了搜索但结果为空
                logger.info(
                    f"模型 {model_name} (第一次尝试) 在启用联网搜索后未生成文本内容。"
                    f"准备进行第二次尝试（不使用联网搜索）。"
                )
                search_attempt_yielded_no_content = True
            elif not response_content:  # 没有内容，且不是因为工具调用或搜索问题
                logger.warning(
                    f"模型 {model_name} (第一次尝试) 未生成内容。"
                    f"结束原因: {finish_reason}. 返回空字符串。"
                )
                return ""

        except Exception as e:
            logger.exception(f"智谱AI GLM ({model_name}, llm_api.py) API调用失败 (第一次尝试): {e}")
            # 尝试解析Zhipu特定的API错误
            if hasattr(e, 'response') and hasattr(e.response, 'status_code') and hasattr(e.response, 'json'):
                try:
                    error_data = e.response.json()
                    if "error" in error_data:
                        error_code = error_data["error"].get("code")
                        error_message = error_data["error"].get("message")
                        if error_code == "1703":  # Zhipu API 明确表示搜索引擎无数据
                            logger.info(
                                f"智谱AI API 明确报告搜索引擎无数据 (错误码 1703) 模型 {model_name}。"
                                f"将进行第二次尝试（不使用联网搜索）。"
                            )
                            search_attempt_yielded_no_content = True
                        else:
                            return f"AI服务遇到API层面问题 (代码: {error_code}, 消息: {error_message})"
                except Exception as parse_e:
                    logger.error(f"解析智谱AI错误响应失败: {parse_e}")

            if not search_attempt_yielded_no_content:  # 如果不是因特定错误进入第二次尝试，则第一次尝试的失败是最终失败
                return f"AI服务暂时不可用 (调用出错): {str(e)}"

        # --- 第二次尝试: 不使用联网搜索 (仅当第一次搜索尝试未产生内容时执行) ---
        if search_attempt_yielded_no_content:
            logger.info(f"智谱AI GLM ({model_name}, llm_api.py): 第二次尝试 - 联网搜索已禁用。")
            try:
                response_no_search = client.chat.completions.create(
                    model=model_name, messages=messages,
                    temperature=max(0.01, min(temperature, 0.99)),
                    max_tokens=max_tokens,
                    tools=None,  # 明确不使用工具
                    stream=False
                )
                message_no_search = response_no_search.choices[0].message
                content_no_search = message_no_search.content or ""
                finish_reason_no_search = response_no_search.choices[0].finish_reason

                logger.info(
                    f"非流式 (第二次尝试 - 无搜索) 完成 模型: {model_name}. "
                    f"结束原因: '{finish_reason_no_search}', "
                    f"内容长度: {len(content_no_search)}"
                )

                if finish_reason_no_search == 'sensitive':
                    logger.info(f"内容因敏感被模型 {model_name} 拦截 (第二次尝试)。")
                    return LLMInterface.SENSITIVE_CONTENT_HINT

                if content_no_search:
                    return content_no_search
                else:  # 如果第二次尝试（无搜索）仍然没有内容
                    logger.warning(
                        f"模型 {model_name} 在第二次尝试（无搜索）后仍未生成内容。"
                        f"结束原因: {finish_reason_no_search}. 返回 SEARCH_NO_DATA_HINT。"
                    )
                    return LLMInterface.SEARCH_NO_DATA_HINT  # 最终后备提示
            except Exception as e2:
                logger.exception(f"智谱AI GLM ({model_name}, llm_api.py) API调用失败 (第二次尝试 - 无搜索): {e2}")
                return f"AI服务暂时不可用 (后备调用出错): {str(e2)}"

        logger.error(
            f"智谱AI GLM ({model_name}, llm_api.py): _call_zhipu 意外到达函数末尾。search_attempt_yielded_no_content={search_attempt_yielded_no_content}")
        return LLMInterface.SEARCH_NO_DATA_HINT


# --- llm_api.py 的独立测试部分 (可选) ---
async def main_test_llm_api():
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    try:
        from dotenv import load_dotenv
        if load_dotenv(): logger.info("llm_api.py standalone test: .env loaded.")
    except ImportError:
        pass

    if not os.getenv("ZHIPUAI_API_KEY") or "your_zhipuai_api_key_here" in os.getenv("ZHIPUAI_API_KEY", ""):
        print("警告: ZHIPUAI_API_KEY 未在环境变量中正确设置。测试可能无法正确执行。")
        return

    os.environ["LLM_PROVIDER"] = "zhipu"
    os.environ["GLM_MODEL"] = os.getenv("GLM_MODEL", LLMInterface.DEFAULT_ZHIPU_MODEL_FALLBACK)

    logger.info(f"\n--- LLM_API_TEST: 智谱模型 (联网查询天气) ---")
    messages_weather = [{"role": "system", "content": "你是一个AI助手，请使用联网搜索回答问题。"},
                        {"role": "user", "content": "北京今天天气怎么样？"}]
    response_weather = await LLMInterface.generate_response(messages_weather, enable_web_search=True)
    print(f"Zhipu 天气回复:\n{response_weather}\n")

    logger.info(f"\n--- LLM_API_TEST: 智谱模型 (普通对话) ---")
    messages_simple = [{"role": "user", "content": "你好，介绍一下你自己"}]
    response_simple = await LLMInterface.generate_response(messages_simple, enable_web_search=False)  # 测试关闭搜索
    print(f"Zhipu 普通回复:\n{response_simple}\n")


if __name__ == "__main__":
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main_test_llm_api())