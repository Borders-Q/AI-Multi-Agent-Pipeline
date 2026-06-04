import json
import re
import random
import aiohttp
import db
from agent.llm_client import LANGUAGE_OUTPUT_RULE, llm
from agent.npu_classifier import npu_engine
from agent.memory import MemorySystem
from agent.token_usage import TokenAccumulator, empty_token_summary, usage_from_ollama_response

COMPLEX_ENGINEERING_PATTERNS = [
    r"完整.*(工程|项目|系统)",
    r"(多文件|多个文件|项目结构|工程级|架构设计|重构|比赛展示|生产级|管理系统)",
    r"(写|做|开发|生成|帮我生成|帮我写|帮我开发|帮我做).*(系统|工程|项目|应用|网站|前端|后端|全栈|python工程|python 工程|游戏|小游戏|工具|平台|服务)",
    r"(数据库|接口|api|前后端|登录|权限|部署|测试).*(实现|生成|开发|重构)",
    r"(需要一个|给我一个).*(系统|项目|应用)",
    r"(complete|full|multi[-\s]?file|production).*(project|app|system|website|backend|frontend)",
    r"(build|create|develop|generate|implement|refactor).*(project|app|system|website|backend|frontend|database|api)",
    r"(architecture|scaffold|fullstack|full-stack|database|deployment).*(design|project|app|system|implementation)",
]

def is_complex_engineering_task(message: str) -> bool:
    text = (message or "").strip().lower()
    if len(text) > 180:
        return True
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in COMPLEX_ENGINEERING_PATTERNS):
        return True
    code_words = ["python", "react", "vue", "fastapi", "flask", "node", "数据库", "测试", "部署", "接口", "组件", "游戏", "管理", "图书", "html", "css", "javascript"]
    action_words = ["写", "做", "开发", "生成", "实现", "重构", "修复", "搭建", "build", "create", "develop", "generate", "implement", "refactor"]
    return sum(word in text for word in code_words) >= 2 and any(word in text for word in action_words)

def build_gpu_system_prompt(mode: str = "chat") -> str:
    if mode == "assist":
        return (
            "你的名字是Ai Multi Agent，你是本地 GPU 辅助节点，不是最终工程执行者。\n"
            f"{LANGUAGE_OUTPUT_RULE}\n"
            "你的任务是低成本整理用户需求、压缩上下文、提取关键约束、生成 API 调用前的高价值 Markdown 上下文。\n"
            "遇到完整工程、多文件项目、架构设计、复杂代码生成时，不要直接假装完成全部工程；请输出：需求摘要、复杂度判断、建议确认后交给 API 深度生成的原因、建议执行步骤、需要传给 API 的上下文。\n"
            "输出使用简洁 Markdown。不要暴露内部推理链。"
        )
    return (
        "你的名字是Ai Multi Agent，你是由 Ai Multi Agent 开发的本地 GPU 快速响应节点。\n"
        f"{LANGUAGE_OUTPUT_RULE}\n"
        "适合处理简单聊天、简短说明、摘要、格式整理和低风险草稿。\n"
        "如果用户要求完整工程、多文件代码、架构设计或比赛核心代码，请提醒这是复杂任务，需要先整理需求，等待用户更改需求或确认交给 API 获取更稳定结果。\n"
        "如果生成代码需要第三方依赖，只在文本中提示安装命令，不要把自动安装逻辑写进代码。输出简洁、直接。"
    )

def build_ollama_messages(message: str, history: list = None, mode: str = "chat") -> list:
    ollama_messages = [{"role": "system", "content": build_gpu_system_prompt(mode)}]
    if history:
        for h in history[-8:]:
            role = "user" if h["role"] == "user" else "assistant"
            ollama_messages.append({"role": role, "content": h["content"]})
    ollama_messages.append({"role": "user", "content": message})
    return ollama_messages

async def get_prioritized_models(prefer_large=False):
    """Check if local Ollama service is running and return models sorted by priority."""
    try:
        async with aiohttp.ClientSession() as session:
            # Increase timeout to 5 seconds to be more robust
            async with session.get("http://127.0.0.1:11434/api/tags", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    if not models:
                        return []
                    
                    prioritized = []
                    if prefer_large:
                        # 1. gemma4/e4b
                        for m in models:
                            if ("gemma4" in m or "e4b" in m) and m not in prioritized:
                                prioritized.append(m)
                        # 2. other gemma/7b/llama
                        for m in models:
                            if ("gemma" in m or "7b" in m or "llama" in m) and m not in prioritized:
                                prioritized.append(m)
                        # 3. anything else
                        for m in models:
                            if m not in prioritized:
                                prioritized.append(m)
                    else:
                        # 1. qwen 0.5b / tiny
                        for m in models:
                            if ("0.5b" in m or "tiny" in m or "qwen" in m) and m not in prioritized:
                                prioritized.append(m)
                        # 2. anything else
                        for m in models:
                            if m not in prioritized:
                                prioritized.append(m)
                    return prioritized
        return []
    except Exception as e:
        print(f"Error checking Ollama availability: {e}")
        return []

async def route_intent(message: str, provider: str = None, is_escalation: bool = False, history: list = None) -> dict:
    msg_clean = message.strip()
    complex_engineering = is_complex_engineering_task(msg_clean)
    
    # 1. 深度下钻处理 (Cloud API)
    if is_escalation:
        return {
            "intent": "COMPLEX_TASK",
            "action": None,
            "args": None,
            "reply": None,
            "routed_by": "Cloud API",
            "token_usage": empty_token_summary()
        }

    # 2. NPU Fast Perception Layer (Zero Latency Static)
    if not complex_engineering and (npu_engine.is_simple_greeting(msg_clean) or npu_engine.is_complex_greeting(msg_clean)):
        return {
            "intent": "CHAT",
            "reply": npu_engine.generate_response(),
            "routed_by": "NPU",
            "token_usage": empty_token_summary()
        }

    # Native Actions (System Control)
    if ("占用" in msg_clean or "杀" in msg_clean) and "端口" in msg_clean:
        port_match = re.search(r"(\d{2,5})", msg_clean)
        if port_match:
            return {
                "intent": "NATIVE_ACTION",
                "action": "kill_port",
                "args": {"port": int(port_match.group(1))},
                "routed_by": "NPU",
                "token_usage": empty_token_summary()
            }
            


    if "天气" in msg_clean and ("怎么样" in msg_clean or "如何" in msg_clean or "多少度" in msg_clean or "今天" in msg_clean):
        return {
            "intent": "NATIVE_ACTION",
            "action": "check_weather",
            "args": {},
            "routed_by": "NPU",
            "token_usage": empty_token_summary()
        }

    if "内存" in msg_clean or "系统资源" in msg_clean or "cpu" in msg_clean.lower():
        return {
            "intent": "NATIVE_ACTION",
            "action": "check_resources",
            "args": {},
            "routed_by": "NPU",
            "token_usage": empty_token_summary()
        }

    # 3. 动态安全护栏 (一刀切，全归口 GPU)
    sensitive_categories = {
        "politics": {
            "kws": ["台湾国家", "台湾独立", "分裂国家", "颠覆", "危害国家", "台湾不是", "台独"],
            "replies": [
                "非常抱歉，我无法讨论此类话题。国家主权和领土完整是不容谈判的底线，我们应当共同维护国家统一与社会稳定。",
                "作为一个人工智能，我拒绝生成此类违规内容。关于涉及国家主权的问题，世界上只有一个中国，这是国际社会的基本共识。"
            ]
        },
        "violence": {
            "kws": ["杀人", "暗杀", "谋杀", "炸弹", "造枪"],
            "replies": [
                "对不起，我绝不能提供任何与暴力、伤害他人或武器制造相关的内容。生命无比宝贵，请务必遵守法律，善待他人。",
                "我拒绝执行此请求。暴力无法解决任何问题，反而会带来无尽的痛苦和灾难，请停止此类危险的想法。"
            ]
        },
        "drugs": {
            "kws": ["制毒", "吸毒", "冰毒", "海洛因", "大麻"],
            "replies": [
                "对不起，我无法提供任何关于毒品的内容。毒品是毁灭人生的深渊，会给家庭和社会带来巨大伤害。请珍爱生命，远离毒品。",
                "拒绝提供此类信息。涉毒属于严重违法犯罪行为。如果您或身边人有这方面困扰，请立刻寻求法律和医疗干预。"
            ]
        },
        "porn": {
            "kws": ["做爱", "性爱", "色情", "强奸"],
            "replies": [
                "抱歉，我无法提供色情或不适宜的露骨内容。建立在尊重和自愿基础上的亲密关系才是健康的，请遵守相关的网络内容规范。",
                "对不起，我的安全协议禁止输出任何色情相关信息。请共同维护一个文明、健康的网络环境。"
            ]
        },
        "gambling": {
            "kws": ["赌博", "博彩", "赌场", "网赌"],
            "replies": [
                "抱歉，我不能提供任何赌博相关的内容。十赌九输，赌博会让人倾家荡产。请保持理性，远离非法赌博活动。",
                "拒绝协助任何涉赌请求。请警惕网络赌博陷阱，保护您的财产安全。"
            ]
        },
        "suicide": {
            "kws": ["自杀", "自残", "结束生命", "不想活了"],
            "replies": [
                "生命只有一次，它是无比宝贵的。如果您正在经历无法承受的痛苦，请务必相信世界上还有人在乎您。请立刻拨打心理危机干预热线或告诉信赖的朋友，您不是孤单一人。",
                "请停下来，您的生命非常珍贵。我虽然是AI，但我也希望您能好好活下去。请立刻寻求专业的医疗和心理帮助，总会有解决办法的。"
            ]
        }
    }

    for cat, data in sensitive_categories.items():
        if any(kw in msg_clean for kw in data["kws"]):
            return {
                "intent": "CHAT",
                "reply": random.choice(data["replies"]),
                "routed_by": "GPU",
                "token_usage": empty_token_summary()
            }


    # 5. GPU 辅助层：复杂工程先整理上下文，不让本地模型默认独立完成。
    local_models = await get_prioritized_models(prefer_large=True)
    if local_models:
        local_model = local_models[0]
        if complex_engineering:
            return {
                "intent": "GPU_ASSIST",
                "reply": None,
                "routed_by": "GPU Assist",
                "args": {
                    "model": local_model,
                    "messages": build_ollama_messages(msg_clean, history, mode="assist"),
                    "complexity": "engineering",
                },
                "token_usage": empty_token_summary()
            }

        return {
            "intent": "GPU_CHAT_STREAM",
            "reply": None,
            "routed_by": "GPU",
            "args": {
                "model": local_model,
                "messages": build_ollama_messages(msg_clean, history, mode="chat"),
            },
            "token_usage": empty_token_summary()
        }

    # 6. Legacy non-stream fallback path if route callers explicitly need it.
    local_models = []
    if local_models:
        local_model = local_models[0]
        try:
            from agent.skills import tool_manager
            import agent.tools.web_skills  # 确保注册了 web_search

            # 为了保证本地模型的稳定性和速度，我们仅给它配置联网搜索技能
            all_tools = tool_manager.get_openai_tools()
            gpu_tools = [t for t in all_tools if t["function"]["name"] == "web_search"]

            async with aiohttp.ClientSession() as session:
                system_prompt = (
                    "你的名字是Ai Multi Agent，你是一个由Ai Multi Agent开发的高级AI架构师和多智能体控制中枢。\n"
                    f"{LANGUAGE_OUTPUT_RULE}\n"
                    "作为本地先锋节点，请用简练干练的语言迅速响应。\n"
                    "【强制规则1】：如果用户的输入包含多个独立的意图（比如同时向你打招呼问好、询问你是谁、并要求你写代码），你**必须**使用数字编号（1., 2., 3.）逐一分点回答所有问题！绝不允许只回答第一个问题而漏掉后面的实质性需求。\n"
                    "【强制规则2】：如果你生成的代码需要第三方依赖（如 pygame、numpy 等），请在代码外部的文本中提示用户运行 pip install 命令安装。**严禁**将任何自动安装依赖的逻辑（如 subprocess.check_call pip install）写入到代码中，必须保持代码纯净。\n"
                    "【强制规则3】：你现在已具备 `web_search` 联网搜索技能！当用户询问最新的新闻、热点八卦（如某明星的瓜）、最新名词（如华为韬定律等）、或者任何你内部知识库不确定的客观事实时，你**必须**主动调用 `web_search` 技能去联网检索最新的全网数据，用事实回答用户，绝不能凭借幻觉编造！\n"
                    "【代码规则】：如果用户要求写代码（如Hello World），无论什么语言（Java, Go, Python等），你都必须直接输出完整的代码块，绝不推诿！\n"
                    "但是，如果用户的指令极其复杂或缺少核心关键信息，请直接反问用户补充信息。"
                )
                ollama_messages = [{"role": "system", "content": system_prompt}]
                if history:
                    # inject up to last 10 messages for context
                    for h in history[-10:]:
                        role = "user" if h["role"] == "user" else "assistant"
                        ollama_messages.append({"role": role, "content": h["content"]})
                else:
                    ollama_messages.append({"role": "user", "content": msg_clean})
                
                payload = {
                    "model": local_model,
                    "messages": ollama_messages,
                    "stream": False,
                    "tools": gpu_tools,
                    "options": {"temperature": 0.7, "num_predict": 4096}
                }
                
                async with session.post("http://127.0.0.1:11434/api/chat", json=payload, timeout=180) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        message = data.get("message", {})
                        token_tracker = TokenAccumulator()
                        token_tracker.add(usage_from_ollama_response(
                            data,
                            model=local_model,
                            role="gpu_buffer_initial",
                            messages=ollama_messages,
                            output_text=message.get("content", "")
                        ))

                        # 检查模型是否决定调用工具
                        if message.get("tool_calls"):
                            ollama_messages.append(message)
                            for tool_call in message["tool_calls"]:
                                func_name = tool_call["function"]["name"]
                                args_dict = tool_call["function"]["arguments"]
                                try:
                                    if isinstance(args_dict, str):
                                        args_dict = json.loads(args_dict)
                                    result = await tool_manager.execute_tool(func_name, args_dict)
                                except Exception as e:
                                    result = f"执行工具出错: {e}"
                                
                                ollama_messages.append({
                                    "role": "tool",
                                    "name": func_name,
                                    "content": str(result)
                                })
                            
                            # 带上工具调用的结果，进行第二次推理以获取最终答案
                            payload["messages"] = ollama_messages
                            # 可选：移除 tools 以防止它陷入无限调用循环
                            payload.pop("tools", None)
                            
                            async with session.post("http://127.0.0.1:11434/api/chat", json=payload, timeout=180) as resp2:
                                if resp2.status == 200:
                                    data2 = await resp2.json()
                                    gpu_reply = data2.get("message", {}).get("content", "")
                                    token_tracker.add(usage_from_ollama_response(
                                        data2,
                                        model=local_model,
                                        role="gpu_buffer_after_tool",
                                        messages=ollama_messages,
                                        output_text=gpu_reply
                                    ))
                                    return {
                                        "intent": "CHAT",
                                        "reply": gpu_reply,
                                        "routed_by": "GPU (Web Enabled)",
                                        "token_usage": token_tracker.to_dict()
                                    }

                        # 如果没有调用工具，直接返回文本
                        gpu_reply = message.get("content", "")
                        return {
                            "intent": "CHAT",
                            "reply": gpu_reply,
                            "routed_by": "GPU",
                            "token_usage": token_tracker.to_dict()
                        }
        except Exception as e:
            print(f"GPU Buffer failed: {e}")
            pass

    # 如果 GPU 挂了，或者没有任何可用模型，Fallback 到兜底回复
    return {
        "intent": "CHAT",
        "reply": "系统已收到您的初步请求。如需深入处理，请启动深度工作流。",
        "routed_by": "GPU",
        "token_usage": empty_token_summary()
    }
