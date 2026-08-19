import os
import json
import httpx
from openai import AsyncOpenAI
from agent.token_usage import usage_from_openai_response, estimate_messages_tokens, estimate_text_tokens

LANGUAGE_OUTPUT_RULE = (
    "【强制语言规则】默认必须使用简体中文输出。"
    "只有当用户明确要求使用英文或其他语言时，才切换到用户指定语言。"
    "代码、命令、文件名、库名、API 名称和必要的英文标识符保持原样。"
)

def enforce_language_rule(messages):
    normalized = [dict(message) for message in (messages or [])]
    for message in normalized:
        if message.get("role") == "system":
            content = message.get("content") or ""
            if LANGUAGE_OUTPUT_RULE not in content:
                message["content"] = f"{content}\n{LANGUAGE_OUTPUT_RULE}".strip()
            return normalized
    return [{"role": "system", "content": LANGUAGE_OUTPUT_RULE}, *normalized]

def identify_api_key(api_key: str):
    """
    Auto-recognize the LLM provider based on API key format.
    Returns: (provider_name, base_url, default_model)
    """
    api_key = api_key.strip()
    
    if api_key.startswith("AIza"):
        return "gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.5-pro"
        
    elif "." in api_key and len(api_key.split(".")) == 2:
        return "zhipu", "https://open.bigmodel.cn/api/paas/v4/", "glm-4"
        
    elif api_key.startswith("sk-ant-"):
        return "anthropic", None, "claude-3-5-sonnet-20241022"
        
    elif api_key.startswith("sk-"):
        if "proj" not in api_key and len(api_key) < 50:
            return "deepseek", "https://api.deepseek.com", "deepseek-chat"
        else:
            return "openai", "https://api.openai.com/v1", "gpt-4o"
            
    return "unknown", "https://api.openai.com/v1", "gpt-3.5-turbo"

class LLMClientManager:
    def __init__(self):
        # Allow multiple clients
        self.clients = {}  # format: {"provider_name": {"client": AsyncOpenAI, "model": "default_model"}}
        
        # Auto-register local Ollama client
        try:
            self.clients["ollama"] = {
                # Ollama is local. Bypass Windows/system proxy discovery so requests
                # to 127.0.0.1 are not sent through a configured gateway.
                "client": AsyncOpenAI(
                    base_url="http://127.0.0.1:11434/v1",
                    api_key="ollama",
                    http_client=httpx.AsyncClient(
                        timeout=httpx.Timeout(600.0, connect=10.0),
                        trust_env=False,
                    ),
                ),
                "model": "gemma4:e4b",  # Will be overridden by actual model name if needed
                "api_key": "ollama"
            }
        except:
            pass
            
        self.active_provider = None
        self.active_tasks = 0
        
    def set_active_provider(self, provider: str):
        self.active_provider = provider

    def add_key(self, api_key: str):
        provider, base_url, default_model = identify_api_key(api_key)
        
        # Initialize client
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.clients[provider] = {
            "client": client,
            "model": default_model,
            "api_key": api_key
        }
        return provider, default_model

    async def chat_completion(self, messages, provider=None, tools=None, stream_callback=None, **kwargs):
        is_background = kwargs.pop("is_background", False)
        if not is_background:
            self.active_tasks += 1
            
        try:
            return await self._chat_completion_inner(messages, provider, tools, stream_callback, **kwargs)
        finally:
            if not is_background:
                self.active_tasks -= 1
                
    async def _chat_completion_inner(self, messages, provider=None, tools=None, stream_callback=None, **kwargs):
        if not self.clients:
            raise ValueError("未配置任何大模型 API Key。")
        messages = enforce_language_rule(messages)
            
        # Select client
        use_provider = provider or self.active_provider
        if use_provider and use_provider in self.clients:
            selected = self.clients[use_provider]
            use_model = selected["model"]
        elif "ollama" in self.clients and use_provider:
            # Treat the provider string as the Ollama model name (e.g. gemma:2b)
            selected = self.clients["ollama"]
            use_model = use_provider
        else:
            # Default to the first available if not specified or not found
            selected = list(self.clients.values())[0]
            use_model = selected["model"]
            
        client = selected["client"]
        selected_provider = None
        for name, data in self.clients.items():
            if data is selected:
                selected_provider = name
                break
        selected_provider = selected_provider or use_provider or "unknown"
        
        if tools is not None and len(tools) == 0:
            tools = None
            
        if not stream_callback:
            # Fallback to standard blocking execution
            response = await client.chat.completions.create(
                model=use_model,
                messages=messages,
                tools=tools,
                **kwargs
            )
            try:
                response.skyt_provider = selected_provider
                response.skyt_model = use_model
                response.skyt_token_usage = usage_from_openai_response(
                    response,
                    provider=selected_provider,
                    model=use_model,
                    messages=messages,
                    output_text=getattr(response.choices[0].message, "content", "") if getattr(response, "choices", None) else "",
                )
            except Exception:
                pass
            return response

        # Streaming mode
        stream_kwargs = dict(kwargs)
        added_stream_options = False
        if "stream_options" not in stream_kwargs:
            stream_kwargs["stream_options"] = {"include_usage": True}
            added_stream_options = True
        try:
            stream = await client.chat.completions.create(
                model=use_model,
                messages=messages,
                tools=tools,
                stream=True,
                **stream_kwargs
            )
        except Exception:
            if not added_stream_options:
                raise
            stream_kwargs.pop("stream_options", None)
            stream = await client.chat.completions.create(
                model=use_model,
                messages=messages,
                tools=tools,
                stream=True,
                **stream_kwargs
            )

        full_content = ""
        tool_calls_dict = {}
        in_reasoning = False
        in_tool_build = False
        stream_usage = None

        async for chunk in stream:
            if getattr(chunk, "usage", None):
                stream_usage = chunk.usage
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                # Do not expose raw hidden reasoning. The UI receives high-level
                # execution steps from server/workflow events instead.
                in_reasoning = True
                continue

            if delta.content is not None:
                if in_reasoning:
                    in_reasoning = False
                full_content += delta.content
                await stream_callback(full_content)
                
            if getattr(delta, "tool_calls", None):
                if not in_tool_build:
                    in_tool_build = True
                    if in_reasoning:
                        in_reasoning = False
                        full_content += "\n\n"
                    full_content += "\n> ⚡ 正在构建系统工具参数...\n\n"
                    await stream_callback(full_content)
                    
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_dict:
                        tool_calls_dict[idx] = {
                            "id": tc.id or "",
                            "type": "function",
                            "function": {
                                "name": getattr(tc.function, "name", "") or "",
                                "arguments": getattr(tc.function, "arguments", "") or ""
                            }
                        }
                    else:
                        if getattr(tc.function, "name", None):
                            tool_calls_dict[idx]["function"]["name"] += tc.function.name
                        if getattr(tc.function, "arguments", None):
                            tool_calls_dict[idx]["function"]["arguments"] += tc.function.arguments

        class DummyFunction:
            def __init__(self, name, arguments):
                self.name = name
                self.arguments = arguments
            def model_dump(self):
                return {"name": self.name, "arguments": self.arguments}

        class DummyToolCall:
            def __init__(self, id, type, function):
                self.id = id
                self.type = type
                self.function = function
            def model_dump(self):
                return {"id": self.id, "type": self.type, "function": self.function.model_dump()}

        class DummyMessage:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls
            def model_dump(self):
                res = {"role": "assistant", "content": self.content}
                if self.tool_calls:
                    res["tool_calls"] = [tc.model_dump() for tc in self.tool_calls]
                return res

        class DummyChoice:
            def __init__(self, message):
                self.message = message

        class DummyUsage:
            def __init__(self, prompt_tokens=0, completion_tokens=0, total_tokens=0, estimated=False):
                self.prompt_tokens = prompt_tokens
                self.completion_tokens = completion_tokens
                self.total_tokens = total_tokens
                self.estimated = estimated

        class DummyResponse:
            def __init__(self, choices, usage=None):
                self.choices = choices
                self.usage = usage
                self.model = use_model
                self.skyt_provider = selected_provider
                self.skyt_model = use_model

        final_tool_calls = None
        if tool_calls_dict:
            final_tool_calls = []
            for idx in sorted(tool_calls_dict.keys()):
                tc = tool_calls_dict[idx]
                final_tool_calls.append(
                    DummyToolCall(tc["id"], tc["type"], DummyFunction(tc["function"]["name"], tc["function"]["arguments"]))
                )

        msg = DummyMessage(full_content if full_content else None, final_tool_calls)
        if stream_usage:
            usage = stream_usage
        else:
            prompt_tokens = estimate_messages_tokens(messages)
            completion_tokens = estimate_text_tokens(full_content)
            usage = DummyUsage(prompt_tokens, completion_tokens, prompt_tokens + completion_tokens, estimated=True)
        resp = DummyResponse([DummyChoice(msg)], usage)
        try:
            resp.skyt_token_usage = usage_from_openai_response(
                resp,
                provider=selected_provider,
                model=use_model,
                messages=messages,
                output_text=full_content,
            )
        except Exception:
            resp.skyt_token_usage = None
        
        return resp

    def list_providers(self):
        return [{"provider": p, "model": data["model"]} for p, data in self.clients.items()]

# Global instance
llm = LLMClientManager()
