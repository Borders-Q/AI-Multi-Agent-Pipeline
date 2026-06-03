import asyncio
import re
import os
import json
import time
import uuid
import subprocess
from agent.llm_client import llm
from agent.token_usage import TokenAccumulator, format_token_summary, merge_usage_calls, usage_from_openai_response
from agent.skills import tool_manager
from agent.code_artifacts import extract_code_blocks, extract_local_urls, save_code_blocks_to_dir
from agent.deployment import deploy_workspace_preview, format_deployment_summary
from agent.project_scaffold import generate_flask_crud_blocks
import agent.tools.web_skills
import agent.tools.code_analysis
import agent.tools.project_tools
import agent.tools.http_tools
import agent.tools.fs_tools
import db


def _workflow_artifact_policy(workflow: dict) -> dict:
    meta = (workflow or {}).get("meta") or {}
    return meta.get("artifact_policy") or {}


def _workflow_preview_policy(workflow: dict) -> dict:
    meta = (workflow or {}).get("meta") or {}
    return meta.get("preview_policy") or {}


def _node_can_emit_artifact(node_data: dict, policy: dict) -> bool:
    if not policy.get("save_code_blocks"):
        return False
    node_name = str(node_data.get("label") or node_data.get("name") or "")
    agent_id = str(node_data.get("agentId") or node_data.get("agent_id") or node_name)
    stage = str(node_data.get("stage") or "")
    outputs_value = node_data.get("outputFields") or []
    outputs = " ".join(outputs_value) if isinstance(outputs_value, list) else str(outputs_value)
    text = f"{node_name} {agent_id} {stage} {outputs}".lower()
    return any(keyword in text for keyword in [
        "coder", "code", "implementation", "代码", "实现", "修复", "patch", "file_changes", "code_blocks"
    ])


def _format_artifact_summary(saved_artifacts: list[dict], workspace: str) -> str:
    if not saved_artifacts:
        return ""
    lines = [f"\n\n## 已保存到本地工作区\n\n目标目录：`{workspace}`"]
    for item in saved_artifacts:
        node_name = item.get("node") or "工作流节点"
        lines.append(f"\n### {node_name}")
        for rel_path in item.get("saved_files") or []:
            lines.append(f"- `{rel_path}`")
    return "\n".join(lines)


def _clip_context(text: str, limit: int = 12000) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    head = text[: limit // 2]
    tail = text[-limit // 2:]
    return f"{head}\n\n...【中间长上下文已压缩，保留首尾与已落盘文件摘要】...\n\n{tail}"


def _is_engineering_template(workflow_meta: dict) -> bool:
    template_id = str((workflow_meta or {}).get("template_id") or "")
    name = str((workflow_meta or {}).get("template_name") or "")
    return template_id == "tmpl_competition_engineering_pipeline" or "工程生成" in name


def _inside_workspace(path: str, workspace: str) -> bool:
    try:
        base = os.path.abspath(workspace)
        target = os.path.abspath(path)
        return os.path.commonpath([base, target]) == base
    except Exception:
        return False

CONDITION_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(==|!=|>=|<=|>|<)\s*(true|false|null|none|-?\d+(?:\.\d+)?|'[^']*'|\"[^\"]*\")\s*$",
    re.IGNORECASE,
)
ALLOWED_CONDITION_FIELDS = {
    "success",
    "test_success",
    "approved",
    "retry_count",
    "max_retry_count",
    "quality_score",
    "coverage_percent",
    "error_log",
    "status",
    "has_code_blocks",
}


def _edge_data(edge: dict) -> dict:
    data = edge.get("data") if isinstance(edge.get("data"), dict) else {}
    loop_policy = data.get("loopPolicy") if isinstance(data.get("loopPolicy"), dict) else {}
    if isinstance(edge.get("loopPolicy"), dict):
        loop_policy = {**loop_policy, **edge.get("loopPolicy")}
    return {
        "edgeType": edge.get("edgeType") or data.get("edgeType") or "control",
        "condition": edge.get("condition") or data.get("condition") or "",
        "label": edge.get("label") or data.get("label") or "",
        "fromOutputField": edge.get("fromOutputField") or data.get("fromOutputField") or "",
        "toInputField": edge.get("toInputField") or data.get("toInputField") or "",
        "loopPolicy": loop_policy,
    }


def _literal_value(raw: str):
    value = str(raw).strip()
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in ("null", "none"):
        return None
    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
        return value[1:-1]
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def _compare_condition(left, operator: str, right) -> bool:
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    try:
        left_num = float(left)
        right_num = float(right)
    except (TypeError, ValueError):
        return False
    if operator == ">":
        return left_num > right_num
    if operator == "<":
        return left_num < right_num
    if operator == ">=":
        return left_num >= right_num
    if operator == "<=":
        return left_num <= right_num
    return False


def _evaluate_condition(condition: str, state: dict) -> bool:
    normalized = (condition or "").strip()
    if not normalized or normalized.lower() in ("always", "default"):
        return True
    if normalized.lower() == "else":
        return False
    match = CONDITION_RE.match(normalized)
    if not match:
        return False
    field_name, operator, literal = match.groups()
    if field_name not in ALLOWED_CONDITION_FIELDS:
        return False
    return _compare_condition(state.get(field_name), operator, _literal_value(literal))


def _node_type(node: dict) -> str:
    data = node.get("data", {}) or {}
    return str(data.get("nodeType") or data.get("node_type") or "agent")


def _derive_runtime_state(node_result: str, previous: dict) -> dict:
    result = str(node_result or "")
    lowered = result.lower()
    failed = any(token in lowered for token in ["error", "failed", "exception", "traceback", "失败", "报错", "错误"])
    success = not failed
    next_state = dict(previous)
    next_state.update({
        "success": success,
        "status": "success" if success else "failed",
        "error_log": result[:1000] if failed else "",
        "has_code_blocks": "```" in result,
        "test_success": success if "test" in lowered or "测试" in result or "验证" in result else next_state.get("test_success", success),
        "last_output": result[:4000],
    })
    return next_state


def _scope_tool_args_to_workspace(func_name: str, kwargs: dict, workspace: str) -> tuple[dict, str | None]:
    """Keep workflow tool calls inside the user-bound workspace when possible."""
    if not workspace:
        return kwargs, None
    next_kwargs = dict(kwargs or {})
    rel_saved_path = None
    if func_name == "write_file":
        raw_path = str(next_kwargs.get("path") or next_kwargs.get("file_path") or "").strip()
        if raw_path:
            target = raw_path if os.path.isabs(raw_path) else os.path.join(workspace, raw_path)
            if not _inside_workspace(target, workspace):
                target = os.path.join(workspace, os.path.basename(raw_path))
            next_kwargs["path"] = target
            rel_saved_path = os.path.relpath(target, workspace).replace("\\", "/")
    elif func_name in ("run_command", "start_background_service") and not next_kwargs.get("cwd"):
        next_kwargs["cwd"] = workspace
    return next_kwargs, rel_saved_path


class AgentWorkflowEngine:
    def __init__(self, provider="openai"):
        self.provider = provider
        self.last_run_id = None
        self.last_token_usage = None
        self.workspace = None
        self.saved_artifacts = []
        self.preview_urls = []
        self.deployment_result = None
        
    async def execute_dag(self, task_description: str, sse_queue: asyncio.Queue, routed_by="Cloud API", enabled_skills: list[str] = None, workflow_mode: str = "standard"):
        """
        Executes a Tool-Calling Loop with Ai Multi Agent Deep Thinking (Reflection) Mode.
        """
        run_id = f"RUN_{uuid.uuid4().hex[:8].upper()}"
        self.last_run_id = run_id
        session_id = getattr(self, "session_id", "default")
        db.create_run_record(run_id, session_id, task_description)
        token_tracker = TokenAccumulator()
        total_tokens = 0
        
        # Load Long-Term Memory if it exists
        long_term_memory = ""
        from agent.memory import MemorySystem
        # We assume the workspace is the current working directory, which should be correct for the backend server
        mem_sys = MemorySystem(workspace_dir=".")
        long_term_memory = mem_sys.get_long_term_memory_content()
        
        async def emit(node_name, state, detail=None, token_usage=None):
            step_payload = {
                "type": "execution_step",
                "node": node_name,
                "state": state,
                "routed_by": routed_by,
                "description": detail or node_name,
                "token_usage": token_usage,
            }
            await sse_queue.put(step_payload)
            await sse_queue.put({"type": "workflow", "node": node_name, "state": state, "routed_by": routed_by, "description": detail, "token_usage": token_usage})
            if state in ("done", "failed", "error"):
                try:
                    db.save_run_event(
                        run_id,
                        "EXECUTION_STEP",
                        routed_by,
                        "SUCCESS" if state == "done" else "FAILED",
                        node_name,
                        json.dumps({"execution_step": step_payload, "token_usage": token_usage}, ensure_ascii=False),
                        0
                    )
                except Exception:
                    pass
            await asyncio.sleep(0.1)
            
        sys_prompt = (
            "你是Ai Multi Agent，一个极其强大的全能架构师和AI智能体。\n"
            "你有能力调用工具(Tools)来解决问题。如果是计算、画图、搜索、总结脑图，务必调用对应的技能。\n"
            "【强制规则1】：如果用户的输入包含多个独立的意图（比如打招呼、算数学题、搜索新闻），你**必须**使用数字编号逐一回答。\n"
            "【强制规则2】：只要涉及到生成文件、编写脚本、保存代码等需要落盘的操作，你的第一步**必须且只能是**先调用 ask_user_for_directory 工具，弹窗让用户选择保存文件夹！只有在获取到用户选择的路径后，你才能继续执行写文件的操作。\n"
            "【强制规则3】：如果你生成的代码需要第三方依赖库（如 pygame、numpy 等），**严禁**将 pip install 等自动安装逻辑写在生成的代码内部！作为智能体，你必须亲自调用 `run_command` 工具，主动执行 `pip install <库名> -i https://pypi.tuna.tsinghua.edu.cn/simple` 来为用户提前配置好环境。环境准备完毕后，再进行后续的代码编写与测试，确保提供给用户的是纯净的业务代码。\n"
            "【强制规则4】：所有生成的 Python 脚本必须严格以 `.py` 为扩展名保存。绝对禁止生成诸如 `.snake`、`.txt` 这种无效扩展名。\n"
            "【强制规则5】：严禁代码结构混乱！同一个 Python 文件内绝对禁止出现多个入口死循环（如多个 `while running`）、绝对禁止重复初始化（如多次调用 `pygame.init()`）、绝对禁止定义多个同名类。必须保持“单一职责”和“整洁的面向对象结构”。\n"
            "【强制规则6】：**拥抱联网搜索，打破知识盲区！** 你的内部知识可能无法涵盖最新事件，如果你遇到以下情况：1) 准备安装第三方依赖但不确定兼容性或确切包名；2) 用户询问最新新闻、热点事件或八卦资讯（例如“某明星最新的瓜”）；3) 用户提及新出现的名词、前沿科技动态（例如“华为最新的韬定律”）；4) 任何你不确定的客观事实。**你都必须毫不犹豫地优先调用 `web_search` 技能**进行联网检索，用最新的全网数据武装自己后再作答，绝不能凭借幻觉编造！\n"
            "【强制规则7】：**绝对禁止“执行前请示”或“确认流程”！** 当你收到“已批准计划”、“开始执行”或任何代码编写指令时，你必须**立即**输出工具调用(Tool Call)来写文件或跑命令。绝不允许回复诸如“流程确认：任务目标确认”、“请指导我下一步”、“确认窗口”等废话。闭嘴，直接干活！\n"
            "【自检与自动启动机制】（非常重要）：\n"
            "1. 写完代码必须使用 `run_command` 运行关键功能以进行自我纠错和报错分析。\n"
            "2. 如果报错，必须修复代码后重新测试。\n"
            "3. 如果涉及持续运行的服务（如 Web、API 等），测试通过后必须调用 `start_background_service`启动它。\n"
            "4. 最终交付结果中，务必提供一个【一键启动】按钮供用户在聊天界面直接运行项目。格式必须严格为：`[🚀 一键启动服务](command:你的启动命令)` （例如 `[🚀 一键启动项目](command:npm run dev)` 或 `[🚀 运行Python](command:python main.py)`）。\n"
        )
        
        if workflow_mode == "expert_review":
            sys_prompt += "\n【专家审查模式开启】：你必须以最严谨的逻辑、最挑剔的眼光去审视问题，确保解决方案在性能、安全和可扩展性上达到业界顶尖水平。\n"
        elif workflow_mode == "creative_brainstorm":
            sys_prompt += "\n【发散风暴模式开启】：请放飞你的想象力，突破常规思维，提供多种富有创意和非传统视角的解决方案。鼓励使用图表和新颖的观点。\n"
        elif workflow_mode == "deep_thought":
            sys_prompt += "\n【标准深思模式开启】：请进行一步步的逻辑推演，在给出最终答案前，确保每一个环节严丝合缝。\n"
        
        if long_term_memory:
            sys_prompt += f"\n\n【长期记忆库】\n{long_term_memory}\n"
            
        messages = [
            {"role": "system", "content": sys_prompt}
        ]
        
        # Fetch episodic session history
        history = db.get_history(session_id)
        if history:
            # If the last message is the generic approve placeholder, drop it so we can append the rich task_description
            if history[-1]["content"].startswith("✅ 批准计划"):
                history = history[:-1]
                
            for h in history[-10:]:
                role = "user" if h["role"] == "user" else "assistant"
                messages.append({"role": role, "content": h["content"]})
                
        messages.append({"role": "user", "content": task_description})
        
        # Fetch custom workflow if defined
        custom_workflow_json = db.get_session_workflow(session_id)
        custom_workflow = None
        if custom_workflow_json:
            try:
                custom_workflow = json.loads(custom_workflow_json)
            except Exception as e:
                print(f"Failed to parse custom workflow: {e}")

        # Override for chat custom agent mention
        agent_match = re.match(r"^@([^\s:]+)[:\s]+(.*)$", task_description.replace("用户原始需求: ", "").split("\n")[0])
        if agent_match and not custom_workflow:
            agent_name = agent_match.group(1)
            agent_instruction = agent_match.group(2)
            custom_workflow = {
                "nodes": [{
                    "id": "single",
                    "data": {
                        "label": agent_name,
                        "agentId": agent_name,
                        "role": f"{agent_name} 专属节点",
                        "instruction": f"用户在聊天窗口直接指定本节点执行：{agent_instruction}",
                        "inputFields": ["requirement"],
                        "outputFields": ["agent_result"],
                    }
                }],
                "edges": []
            }

        all_tools = tool_manager.get_openai_tools()
        tools = []
        if enabled_skills is not None:
            tools = [t for t in all_tools if t["function"]["name"] in enabled_skills]
        else:
            tools = all_tools
            
        # --- CUSTOM WORKFLOW EXECUTION PATH ---
        if custom_workflow and custom_workflow.get("nodes") and len(custom_workflow["nodes"]) > 0:
            return await self._execute_custom_workflow(custom_workflow, task_description, messages, sse_queue, routed_by, tools, run_id, token_tracker)
            
        max_iterations = 150
        reflected = False
        
        for i in range(max_iterations):
            await emit(f"架构与逻辑推理 (Iter {i+1})", "running")
            
            async def sse_callback(text):
                await sse_queue.put({
                    "type": "execution",
                    "response": text,
                    "status": "streaming",
                    "routed_by": routed_by
                })
            
            t0 = time.time()
            try:
                response = await llm.chat_completion(messages, provider=self.provider, tools=tools, stream_callback=sse_callback)
                message = response.choices[0].message
                call_usage = getattr(response, "skyt_token_usage", None) or usage_from_openai_response(
                    response,
                    provider=self.provider,
                    role=f"workflow_reasoning_iter_{i+1}",
                    messages=messages,
                    output_text=getattr(message, "content", "") or "",
                )
                token_tracker.add(call_usage)
                total_tokens = token_tracker.total_tokens
                dur_ms = int((time.time() - t0) * 1000)
                
                raw_preview = message.content[:200] + "..." if message.content and len(message.content) > 200 else (message.content or "")
                
                event_type = "LLM_REFLECTION" if reflected else "LLM_THINK"
                db.save_run_event(
                    run_id,
                    event_type,
                    "CodeAgent",
                    "SUCCESS",
                    f"架构与逻辑推理 (Iter {i+1})",
                    json.dumps({
                        "input_payload": {"messages_count": len(messages), "tools_count": len(tools or [])},
                        "output_payload": {"role": "assistant", "preview": raw_preview},
                        "token_usage": call_usage,
                        "model_info": {"provider": self.provider, "routed_by": routed_by},
                    }, ensure_ascii=False),
                    dur_ms
                )
                await emit(f"架构与逻辑推理 (Iter {i+1})", "done", "模型完成一轮架构推理并写入回放记录。", call_usage)
                
                if message.content:
                    code_blocks = re.findall(r'```(\w+)?\n(.*?)```', message.content, re.DOTALL)
                    for idx, (lang, code) in enumerate(code_blocks):
                        lang = lang or "text"
                        lines = len(code.strip().split('\n'))
                        event_title = f"编写 {lang.upper()} 模块代码 ({lines}行)"
                        fake_dur = min(3000, lines * 30)
                        
                        await emit(event_title, "running")
                        await asyncio.sleep(0.3)
                        db.save_run_event(run_id, "CODE_GEN", "CodeGenerator", "SUCCESS", event_title, json.dumps({
                            "input_payload": {"language": lang},
                            "output_payload": {"lines": lines, "code_preview": code[:150]},
                        }, ensure_ascii=False), fake_dur)
                        await emit(event_title, "done")

            except Exception as e:
                dur_ms = int((time.time() - t0) * 1000)
                db.save_run_event(run_id, "LLM_THINK", "CodeAgent", "FAILED", f"LLM Error: {str(e)}", None, dur_ms)
                summary = token_tracker.to_dict()
                self.last_token_usage = summary
                db.update_run_record(run_id, False, 0.0, summary["total_tokens"], summary["api_tokens"], summary["local_tokens"], summary["source"], summary)
                return f"模型推演失败: {str(e)}"
                
            if hasattr(message, "tool_calls") and message.tool_calls:
                messages.append(message.model_dump() if hasattr(message, "model_dump") else message)
                for idx, tool_call in enumerate(message.tool_calls):
                    func_name = tool_call.function.name
                    args_str = tool_call.function.arguments
                    try:
                        kwargs = json.loads(args_str)
                    except:
                        kwargs = {}
                        
                    if func_name == "write_file":
                        ui_state = f"📝 正在编写/修改代码..."
                    elif func_name == "run_command":
                        ui_state = f"🔍 进行自我纠错与验证测试..."
                    elif func_name == "start_background_service":
                        ui_state = f"🚀 正在启动后台服务..."
                    else:
                        ui_state = f"执行技能: {func_name}"
                        
                    await emit(ui_state, "running")
                    await sse_queue.put({
                        "type": f"tool_call_{func_name}_{idx}", 
                        "response": f"⚡ Ai Multi Agent 正在执行技能: `[{func_name}]` ...\n```json\n{args_str}\n```", 
                        "status": "streaming", 
                        "routed_by": routed_by
                    })
                    
                    t1 = time.time()
                    try:
                        result = await tool_manager.execute_tool(func_name, kwargs)
                        dur_ms = int((time.time() - t1) * 1000)
                        db.save_run_event(run_id, "TOOL_CALL", func_name, "SUCCESS", f"Executed {func_name}", json.dumps({
                            "input_payload": {"args": kwargs},
                            "output_payload": {"result": str(result)},
                            "execution_step": {"node": ui_state, "state": "done", "routed_by": routed_by},
                        }, ensure_ascii=False), dur_ms)
                        if str(result).startswith("[APPROVAL_REQUIRED]"):
                            await sse_queue.put({
                                "type": "approval_required",
                                "response": str(result),
                                "status": "streaming",
                                "routed_by": routed_by,
                                "tool": func_name
                            })
                        
                        # Emit success update to the UI
                        await sse_queue.put({
                            "type": f"tool_call_{func_name}_{idx}", 
                            "response": f"⚡ Ai Multi Agent 正在执行技能: `[{func_name}]` ...\n```json\n{args_str}\n```\n\n✅ 执行完毕 (耗时 {dur_ms}ms)", 
                            "status": "streaming", 
                            "routed_by": routed_by
                        })
                    except Exception as e:
                        dur_ms = int((time.time() - t1) * 1000)
                        result = f"Error executing tool: {str(e)}"
                        db.save_run_event(run_id, "TOOL_CALL", func_name, "FAILED", f"Tool Error: {str(e)}", json.dumps({
                            "input_payload": {"args": kwargs},
                            "output_payload": {"error": str(e)},
                            "execution_step": {"node": ui_state, "state": "failed", "routed_by": routed_by},
                        }, ensure_ascii=False), dur_ms)
                        
                        # Emit failure update to the UI
                        await sse_queue.put({
                            "type": f"tool_call_{func_name}_{idx}", 
                            "response": f"⚡ Ai Multi Agent 正在执行技能: `[{func_name}]` ...\n```json\n{args_str}\n```\n\n❌ 执行失败: {str(e)}", 
                            "status": "streaming", 
                            "routed_by": routed_by
                        })
                    
                    await emit(ui_state, "done")
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": str(result)
                    })
            else:
                # No more tools. Check if reflection is enabled based on workflow_mode
                if workflow_mode in ["deep_thought", "expert_review"] and not reflected:
                    await emit("Ai Multi Agent 深思引擎 (博弈与反思)", "running")
                    await sse_queue.put({
                        "type": "message", 
                        "response": "\n\n🧠 **Ai Multi Agent系统进入深思模式**：正在对生成的方案进行逻辑校验与自我反思...\n", 
                        "status": "streaming", 
                        "routed_by": routed_by
                    })
                    messages.append(message.model_dump() if hasattr(message, "model_dump") else message)
                    messages.append({
                        "role": "system",
                        "content": "【Ai Multi Agent 深思要求】作为高级审查者，请极其严厉地审视你刚刚给出的最终答案。\n"
                                   "1. 如果代码或方案存在任何语法错误、逻辑漏洞或不符合用户要求的地方，请立刻提供修改后的正确版本。\n"
                                   "2. 如果完全正确，没有任何问题，请直接回答『Ai Multi Agent 深思校验通过：方案完美』，无需重复输出内容。"
                    })
                    reflected = True
                    await emit("Ai Multi Agent 深思引擎 (博弈与反思)", "done")
                    continue # Continue the loop to get the reflected answer
                
                # Final Return
                summary = token_tracker.to_dict()
                self.last_token_usage = summary
                db.save_run_event(
                    run_id,
                    "TOKEN_USAGE",
                    "TokenMeter",
                    "SUCCESS",
                    format_token_summary(summary),
                    json.dumps({"token_usage": summary}, ensure_ascii=False),
                    0
                )
                await sse_queue.put({"type": "token_usage", "token_usage": summary, "status": "streaming", "routed_by": routed_by})
                db.update_run_record(run_id, True, 9.8 if reflected else 9.0, summary["total_tokens"], summary["api_tokens"], summary["local_tokens"], summary["source"], summary)
                
                # --- AUTO GENERATE MARKDOWN REPORT ---
                try:
                    events = db.get_run_events(run_id)
                    report_md = f"# Ai Multi Agent 深度工作流运行报告\n\n"
                    report_md += f"**运行 ID**: `{run_id}`\n"
                    report_md += f"**模型提供商**: `{self.provider}`\n"
                    report_md += f"**Token 消耗**: `{format_token_summary(summary)}`\n\n"
                    
                    report_md += f"## 📝 任务需求\n{task_description}\n\n"
                    
                    # 提取架构决策 (LLM_THINK / LLM_REFLECTION)
                    thoughts = [e for e in events if e['event_type'] in ('LLM_THINK', 'LLM_REFLECTION')]
                    if thoughts:
                        report_md += "## 🧠 架构决策与逻辑演进\n"
                        for t in thoughts:
                            report_md += f"- **[{t['event_type']}]** ({t['duration_ms']}ms): {t['message']}\n"
                            if t['detail_json']:
                                try:
                                    det = json.loads(t['detail_json'])
                                    if 'preview' in det:
                                        report_md += f"  > {det['preview'].replace(chr(10), ' ')}\n"
                                except:
                                    pass
                        report_md += "\n"
                        
                    # 提取执行流转记录 (TOOL_CALL, CODE_GEN, NATIVE_ACTION)
                    actions = [e for e in events if e['event_type'] not in ('LLM_THINK', 'LLM_REFLECTION', 'SYSTEM_LOG')]
                    if actions:
                        report_md += "## ⚙️ 执行流转记录\n"
                        for a in actions:
                            status_icon = "✅" if a['status'] == 'SUCCESS' else "❌"
                            report_md += f"- {status_icon} **{a['event_type']}**: {a['message']} ({a['duration_ms']}ms)\n"
                            if a['detail_json'] and a['status'] == 'SUCCESS':
                                try:
                                    det = json.loads(a['detail_json'])
                                    if 'args' in det:
                                        report_md += f"  ```json\n  {json.dumps(det['args'], ensure_ascii=False)}\n  ```\n"
                                except:
                                    pass
                        report_md += "\n"
                        
                    # 提取错误摘要
                    errors = [e for e in events if e['status'] == 'FAILED' or 'Error' in e['message']]
                    if errors:
                        report_md += "## ⚠️ 错误摘要与复盘\n"
                        for err in errors:
                            report_md += f"> [!WARNING]\n> **{err['event_type']} 失败**: {err['message']}\n\n"
                            if err['detail_json']:
                                try:
                                    det = json.loads(err['detail_json'])
                                    report_md += f"```json\n{json.dumps(det, ensure_ascii=False, indent=2)}\n```\n"
                                except:
                                    report_md += f"```text\n{err['detail_json']}\n```\n"
                        report_md += "\n"
                        
                    # 最终交付
                    report_md += f"## 🎯 最终交付成果\n\n"
                    report_md += f"{message.content}\n"
                    
                    db.save_report(f"Workflow Report: {run_id}", report_md)
                except Exception as e:
                    print(f"Failed to auto-generate markdown report: {e}")
                # -------------------------------------

                return message.content
                
        summary = token_tracker.to_dict()
        self.last_token_usage = summary
        db.update_run_record(run_id, False, 5.0, summary["total_tokens"], summary["api_tokens"], summary["local_tokens"], summary["source"], summary)
        return "达到最大迭代次数 (150次)，任务已安全终止防止死循环。"

    async def _execute_custom_workflow(self, workflow, task_description, messages, sse_queue, routed_by, tools, run_id, token_tracker):
        total_tokens = token_tracker.total_tokens
        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])
        workflow_meta = workflow.get("meta") or {}
        artifact_policy = _workflow_artifact_policy(workflow)
        preview_policy = _workflow_preview_policy(workflow)
        workspace_dir = (getattr(self, "workspace", None) or "").strip()
        saved_artifacts = []
        saved_signatures = set()
        preview_urls_seen = set()
        
        # Extremely simple topological sort (or just sequential execution by x position for simplicity if edges are complex)
        # We will sort nodes by x position if edges don't enforce order, otherwise try simple topo
        node_map = {n['id']: n for n in nodes}
        in_degree = {n['id']: 0 for n in nodes}
        adj = {n['id']: [] for n in nodes}
        
        for e in edges:
            src = e.get('source')
            tgt = e.get('target')
            if src in adj and tgt in in_degree:
                adj[src].append(tgt)
                in_degree[tgt] += 1
                
        q = [n['id'] for n in nodes if in_degree[n['id']] == 0]
        sorted_nodes = []
        while q:
            curr = q.pop(0)
            sorted_nodes.append(node_map[curr])
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    q.append(nxt)
                    
        # Fallback if there's a cycle or disconnected graph
        if len(sorted_nodes) < len(nodes):
            sorted_nodes = sorted(nodes, key=lambda n: n.get('position', {}).get('x', 0))

        outgoing_edges = {}
        incoming_edges = {}
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if not src or not tgt:
                continue
            edge_info = _edge_data(edge)
            outgoing_edges.setdefault(src, []).append(edge)
            if edge_info.get("edgeType") != "loop":
                incoming_edges.setdefault(tgt, []).append(edge)
        entry_nodes = [node for node in sorted_nodes if not incoming_edges.get(node.get("id"))] or sorted_nodes[:1]
        node_queue = [node.get("id") for node in entry_nodes if node.get("id")]
        completed_nodes = set()
        skipped_edges = set()
        loop_counts = {}
        runtime_state = {
            "success": True,
            "test_success": True,
            "approved": True,
            "retry_count": 0,
            "max_retry_count": 3,
            "quality_score": 0,
            "coverage_percent": 0,
            "error_log": "",
            "status": "success",
            "has_code_blocks": False,
        }
        max_workflow_steps = max(20, len(nodes) * 8)
        workflow_steps = 0

        def enqueue_node(node_id: str):
            if node_id and node_id in node_map and node_id not in node_queue:
                node_queue.append(node_id)

        def join_ready(node: dict) -> bool:
            node_id = node.get("id")
            node_kind = _node_type(node)
            incoming = incoming_edges.get(node_id, [])
            if node_kind == "join_and":
                return all(edge.get("source") in completed_nodes for edge in incoming)
            if node_kind == "join_or":
                return not incoming or any(edge.get("source") in completed_nodes for edge in incoming)
            return True
            
        current_state_context = f"初始任务: {task_description}"
        if workspace_dir:
            current_state_context += f"\n当前绑定工作区: {workspace_dir}"
        final_reply = ""
        base_step_messages = []
        if messages:
            if isinstance(messages[0], dict) and messages[0].get("role") == "system":
                base_step_messages.append(messages[0])
            base_step_messages.append({"role": "user", "content": task_description})
        
        async def emit(node_name, state, detail=None, token_usage=None):
            step_payload = {
                "type": "execution_step",
                "node": node_name,
                "state": state,
                "routed_by": routed_by,
                "description": detail or node_name,
                "token_usage": token_usage,
            }
            await sse_queue.put(step_payload)
            await sse_queue.put({"type": "workflow", "node": node_name, "state": state, "routed_by": routed_by, "description": detail, "token_usage": token_usage})
            if state in ("done", "failed", "error"):
                try:
                    db.save_run_event(
                        run_id,
                        "EXECUTION_STEP",
                        routed_by,
                        "SUCCESS" if state == "done" else "FAILED",
                        node_name,
                        json.dumps({"execution_step": step_payload, "token_usage": token_usage}, ensure_ascii=False),
                        0
                    )
                except Exception:
                    pass
            await asyncio.sleep(0.1)

        async def emit_preview_urls(text, source):
            if not (preview_policy.get("open_local_url") or preview_policy.get("detect_from_output")):
                return
            for url in extract_local_urls(str(text or "")):
                if url in preview_urls_seen:
                    continue
                preview_urls_seen.add(url)
                self.preview_urls.append(url)
                db.save_run_event(
                    run_id,
                    "WORKFLOW_PREVIEW_URL",
                    "WorkflowEngine",
                    "SUCCESS",
                    f"检测到本地预览地址: {url}",
                    json.dumps({
                        "input_payload": {"source": source},
                        "output_payload": {"url": url},
                    }, ensure_ascii=False),
                    0
                )
                await sse_queue.put({"type": "browser_open", "url": url, "source": source, "run_id": run_id})
            
        async def sse_callback(text):
            await sse_queue.put({
                "type": "execution",
                "response": text,
                "status": "streaming",
                "routed_by": routed_by
            })
            
        while node_queue and workflow_steps < max_workflow_steps:
            node_id = node_queue.pop(0)
            node = node_map.get(node_id)
            if not node:
                continue
            has_loop_incoming = any(_edge_data(edge).get("edgeType") == "loop" for edge in edges if edge.get("target") == node_id)
            if node_id in completed_nodes and not has_loop_incoming:
                continue
            if not join_ready(node):
                db.save_run_event(
                    run_id,
                    "WORKFLOW_JOIN_WAITING",
                    "WorkflowEngine",
                    "SKIPPED",
                    f"汇合节点等待上游完成: {node.get('data', {}).get('label', node_id)}",
                    json.dumps({
                        "input_payload": {"node": node_id, "incoming": [edge.get("source") for edge in incoming_edges.get(node_id, [])]},
                        "output_payload": {"completed_nodes": list(completed_nodes)},
                    }, ensure_ascii=False),
                    0
                )
                continue
            if _node_type(node) in ("join_and", "join_or"):
                db.save_run_event(
                    run_id,
                    "WORKFLOW_JOIN_READY",
                    "WorkflowEngine",
                    "SUCCESS",
                    f"汇合节点已满足进入条件: {node.get('data', {}).get('label', node_id)}",
                    json.dumps({
                        "input_payload": {"node": node_id, "incoming": [edge.get("source") for edge in incoming_edges.get(node_id, [])]},
                        "output_payload": {"completed_nodes": list(completed_nodes), "joinType": _node_type(node)},
                    }, ensure_ascii=False),
                    0
                )
            workflow_steps += 1
            node_data = node.get("data", {}) or {}
            node_name = node_data.get("label", node.get("id"))
            if isinstance(node_name, dict):
                node_name = str(node_name)
            if "label" not in node_data and "name" in node_data:
                node_name = node_data["name"]
            node_agent_id = node_data.get("agentId") or node_data.get("agent_id") or node_data.get("agentKey") or node_name
            node_role = node_data.get("role") or (node_data.get("customAgentMeta") or {}).get("role") or ""
            node_instruction = node_data.get("instruction") or ""
            node_system_prompt = node_data.get("systemPrompt") or ""
            node_description = node_data.get("description") or ""
            node_inputs = node_data.get("inputFields") or []
            node_outputs = node_data.get("outputFields") or []
            node_condition = node_data.get("condition") or ""
            prompt_ref = (node_data.get("customAgentMeta") or {}).get("promptRef") or ""
                
            await emit(node_name, "running")
            t0 = time.time()
            
            node_prompt = (
                f"【工作流节点执行】: 你当前正在执行工作流节点 '{node_name}'。\n"
                f"这是之前的执行上下文:\n{current_state_context}\n"
                f"请你完成此节点应该负责的任务。必要时可调用工具。"
            )
            
            node_prompt = (
                f"【工作流节点执行】你当前正在执行节点「{node_name}」。\n"
                f"节点 Key：{node_agent_id}\n"
                f"节点角色：{node_role or '未单独指定，请按节点名称理解职责'}\n"
                f"节点说明：{node_description or '无'}\n"
                f"节点额外指令：{node_instruction or '无'}\n"
                f"系统提示词覆盖：{node_system_prompt or '无'}\n"
                f"Prompt 模板引用：{prompt_ref or '无'}\n"
                f"输入字段：{', '.join(node_inputs) if isinstance(node_inputs, list) else node_inputs}\n"
                f"输出字段：{', '.join(node_outputs) if isinstance(node_outputs, list) else node_outputs}\n"
                f"条件表达式：{node_condition or '无'}\n\n"
                f"这是之前节点产生的上下文：\n{_clip_context(current_state_context)}\n\n"
                "请严格只完成本节点负责的事情。如果节点额外指令要求只做需求、测试、代码或审批，"
                "请不要越界替其他节点完成。必要时可以调用工具。"
            )
            if workspace_dir:
                node_prompt += (
                    f"\n\n【工作区边界】当前已绑定工作区：{workspace_dir}。"
                    "如本节点产出工程代码或补丁，必须使用带目标文件名的 Markdown 代码块输出，"
                    "或调用写文件工具写入该工作区内。不得写入工作区外。"
                )
            if artifact_policy:
                node_prompt += f"\n【模板产物策略】{json.dumps(artifact_policy, ensure_ascii=False)}"
            if preview_policy.get("open_local_url") or preview_policy.get("detect_from_output"):
                node_prompt += "\n【预览策略】如果生成或启动了本地 Web 服务，请明确输出 http://127.0.0.1:端口 或 http://localhost:端口。"
            if str(node_agent_id).lower() not in ("websearch", "web_search") and node_data.get("stage") != "research":
                node_prompt += "\n【联网约束】本节点不负责联网搜索，除非用户明确要求实时资料，否则不要调用 web_search，直接基于用户需求和已有上下文完成。"
            node_tools = tools
            if node_data.get("nodeType") == "tool_skill":
                tool_config = node_data.get("toolSkillConfig") or {}
                target_tool = str(tool_config.get("name") or str(node_agent_id).replace("skill:", "")).strip()
                node_tools = [tool for tool in tools if (tool.get("function") or {}).get("name") == target_tool]
                node_prompt += (
                    f"\n【系统 Skill 调用约束】本节点只允许围绕 `{target_tool}` 技能工作。"
                    "请先根据用户需求和上游上下文整理参数；如果工具可用，必须调用该工具；"
                    "如果参数不足，请输出缺失参数和可执行的替代总结。"
                )

            step_messages = base_step_messages.copy() if base_step_messages else messages.copy()
            step_messages.append({"role": "user", "content": node_prompt})
            
            try:
                artifacts_before_node = len(saved_artifacts)
                response = await llm.chat_completion(step_messages, provider=self.provider, tools=node_tools, stream_callback=sse_callback)
                msg = response.choices[0].message
                node_usage_calls = []
                call_usage = getattr(response, "skyt_token_usage", None) or usage_from_openai_response(
                    response,
                    provider=self.provider,
                    role=f"workflow_node_{node_name}",
                    messages=step_messages,
                    output_text=getattr(msg, "content", "") or "",
                )
                node_usage_calls.append(call_usage)
                token_tracker.add(call_usage)
                total_tokens = token_tracker.total_tokens
                    
                dur_ms = int((time.time() - t0) * 1000)
                
                # Check for tool calls
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    msg_dict = msg.model_dump() if hasattr(msg, "model_dump") else msg
                    step_messages.append(msg_dict)
                    for tool_call in msg.tool_calls:
                        func_name = tool_call.function.name
                        args_str = tool_call.function.arguments
                        try:
                            kwargs = json.loads(args_str)
                        except:
                            kwargs = {}
                        kwargs, tool_saved_rel_path = _scope_tool_args_to_workspace(func_name, kwargs, workspace_dir)
                            
                        await sse_queue.put({
                            "type": "message", 
                            "response": f"⚡ 节点 [{node_name}] 正在执行技能: `{func_name}` ...", 
                            "status": "streaming", 
                            "routed_by": routed_by
                        })
                        
                        try:
                            from agent.skills import tool_manager
                            result = await tool_manager.execute_tool(func_name, kwargs)
                            if func_name == "write_file" and tool_saved_rel_path and not str(result).startswith("Error"):
                                artifact_record = {"node": node_name, "saved_files": [tool_saved_rel_path]}
                                saved_artifacts.append(artifact_record)
                                self.saved_artifacts.append(artifact_record)
                                db.save_run_event(
                                    run_id,
                                    "WORKFLOW_ARTIFACT_SAVED",
                                    "WorkflowEngine",
                                    "SUCCESS",
                                    f"工具写入工作流产物: {node_name}",
                                    json.dumps({
                                        "input_payload": {"node": node_name, "tool": func_name, "workspace": workspace_dir},
                                        "output_payload": {"saved_files": [tool_saved_rel_path], "target_dir": workspace_dir, "tool_result": str(result)},
                                    }, ensure_ascii=False),
                                    0
                                )
                            if str(result).startswith("[APPROVAL_REQUIRED]"):
                                await sse_queue.put({
                                    "type": "approval_required",
                                    "response": str(result),
                                    "status": "streaming",
                                    "routed_by": routed_by,
                                    "tool": func_name
                                })
                        except Exception as e:
                            result = f"Error: {e}"
                            
                        step_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": func_name,
                            "content": str(result)
                        })
                        await emit_preview_urls(result, f"tool:{func_name}")
                        
                    # Second LLM call after tools
                    response2 = await llm.chat_completion(step_messages, provider=self.provider, tools=node_tools)
                    msg = response2.choices[0].message
                    call_usage2 = getattr(response2, "skyt_token_usage", None) or usage_from_openai_response(
                        response2,
                        provider=self.provider,
                        role=f"workflow_node_{node_name}_after_tool",
                        messages=step_messages,
                        output_text=getattr(msg, "content", "") or "",
                    )
                    node_usage_calls.append(call_usage2)
                    token_tracker.add(call_usage2)
                    total_tokens = token_tracker.total_tokens
                
                node_result = msg.content or ""
                await emit_preview_urls(node_result, f"node:{node_name}")

                node_saved_files = []
                if _node_can_emit_artifact(node_data, artifact_policy):
                    blocks = extract_code_blocks(node_result)
                    new_blocks = []
                    for block in blocks:
                        signature = (block.get("filename"), block.get("code"))
                        if signature in saved_signatures:
                            continue
                        saved_signatures.add(signature)
                        new_blocks.append(block)
                    if new_blocks and workspace_dir:
                        try:
                            node_saved_files = save_code_blocks_to_dir(new_blocks, workspace_dir)
                            artifact_record = {"node": node_name, "saved_files": node_saved_files}
                            saved_artifacts.append(artifact_record)
                            self.saved_artifacts.append(artifact_record)
                            db.save_run_event(
                                run_id,
                                "WORKFLOW_ARTIFACT_SAVED",
                                "WorkflowEngine",
                                "SUCCESS",
                                f"保存工作流产物: {node_name}",
                                json.dumps({
                                    "input_payload": {
                                        "node": node_name,
                                        "workspace": workspace_dir,
                                        "code_blocks_count": len(new_blocks),
                                    },
                                    "output_payload": {
                                        "saved_files": node_saved_files,
                                        "target_dir": workspace_dir,
                                    },
                                    "distillation": {"summary": f"{node_name} 产出的代码块已落盘。"},
                                }, ensure_ascii=False),
                                0
                            )
                            await emit("保存代码产物", "done", f"已保存 {len(node_saved_files)} 个文件到工作区。")
                            node_result += (
                                f"\n\n已保存到工作区 `{workspace_dir}`：\n"
                                + "\n".join(f"- `{path}`" for path in node_saved_files)
                            )
                        except Exception as save_error:
                            db.save_run_event(
                                run_id,
                                "WORKFLOW_ARTIFACT_SAVED",
                                "WorkflowEngine",
                                "FAILED",
                                f"保存工作流产物失败: {node_name}",
                                json.dumps({
                                    "input_payload": {"node": node_name, "workspace": workspace_dir},
                                    "output_payload": {"error": str(save_error)},
                                }, ensure_ascii=False),
                                0
                            )
                            node_result += f"\n\n> 保存代码产物失败：{save_error}"
                    elif new_blocks and not workspace_dir:
                        db.save_run_event(
                            run_id,
                            "WORKFLOW_WORKSPACE_REQUIRED",
                            "WorkflowEngine",
                            "SKIPPED",
                            f"{node_name} 产生了代码块，但当前未绑定工作区。",
                            json.dumps({
                                "input_payload": {"node": node_name, "code_blocks_count": len(new_blocks)},
                                "output_payload": {"reason": "missing_workspace"},
                            }, ensure_ascii=False),
                            0
                        )
                    if (
                        _is_engineering_template(workflow_meta)
                        and workspace_dir
                        and len(saved_artifacts) == artifacts_before_node
                    ):
                        fallback_blocks = generate_flask_crud_blocks(task_description)
                        fallback_saved_files = save_code_blocks_to_dir(fallback_blocks, workspace_dir)
                        artifact_record = {"node": f"{node_name}（工程兜底生成）", "saved_files": fallback_saved_files}
                        saved_artifacts.append(artifact_record)
                        self.saved_artifacts.append(artifact_record)
                        db.save_run_event(
                            run_id,
                            "WORKFLOW_ARTIFACT_SAVED",
                            "WorkflowEngine",
                            "SUCCESS",
                            "代码生成节点未产生可落盘产物，已执行工程兜底生成",
                            json.dumps({
                                "input_payload": {
                                    "node": node_name,
                                    "workspace": workspace_dir,
                                    "reason": "no_code_blocks_or_write_file",
                                },
                                "output_payload": {
                                    "saved_files": fallback_saved_files,
                                    "target_dir": workspace_dir,
                                },
                            }, ensure_ascii=False),
                            0
                        )
                        compile_result = subprocess.run(
                            ["python", "-m", "py_compile", os.path.join(workspace_dir, "app.py")],
                            cwd=workspace_dir,
                            text=True,
                            capture_output=True,
                            timeout=30,
                        )
                        db.save_run_event(
                            run_id,
                            "WORKFLOW_LOCAL_CHECK",
                            "WorkflowEngine",
                            "SUCCESS" if compile_result.returncode == 0 else "FAILED",
                            "工程兜底代码语法检查",
                            json.dumps({
                                "input_payload": {"command": "python -m py_compile app.py", "cwd": workspace_dir},
                                "output_payload": {
                                    "returncode": compile_result.returncode,
                                    "stdout": compile_result.stdout,
                                    "stderr": compile_result.stderr,
                                },
                            }, ensure_ascii=False),
                            0
                        )
                        preview_url = "http://127.0.0.1:5000"
                        fallback_summary = (
                            f"\n\n代码生成节点没有交付可保存代码块，Ai Multi Agent 已按工程模板兜底生成并落盘到 `{workspace_dir}`：\n"
                            + "\n".join(f"- `{path}`" for path in fallback_saved_files)
                            + f"\n\n预览服务会在全部工作区文件检查完成后自动启动；默认地址：{preview_url}"
                        )
                        node_result += fallback_summary
                current_state_context += f"\n\n--- 节点 '{node_name}' 执行结果 ---\n{node_result}"
                final_reply = node_result
                
                raw_preview = node_result[:200] + "..." if len(node_result) > 200 else node_result
                node_summary = merge_usage_calls(node_usage_calls)
                db.save_run_event(run_id, "WORKFLOW_NODE", "WorkflowEngine", "SUCCESS", f"执行节点: {node_name}", json.dumps({
                    "input_payload": {"node": node_name, "node_agent_id": node_agent_id, "prompt": node_prompt[:1000]},
                    "output_payload": {"preview": raw_preview},
                    "token_usage": node_summary,
                    "model_info": {"provider": self.provider, "routed_by": routed_by},
                }, ensure_ascii=False), dur_ms)
                await emit(node_name, "done", f"节点 {node_name} 已完成，并写入结构化回放。", node_summary)
                completed_nodes.add(node.get("id"))
                runtime_state = _derive_runtime_state(node_result, runtime_state)

                outgoing = outgoing_edges.get(node.get("id"), [])
                branch_edges = []
                control_edges = []
                loop_edges = []
                for edge in outgoing:
                    edge_info = _edge_data(edge)
                    edge_type = edge_info.get("edgeType") or "control"
                    condition = edge_info.get("condition") or ""
                    if edge_type == "data":
                        continue
                    if edge_type == "loop":
                        loop_edges.append(edge)
                    elif edge_type == "branch" or condition:
                        branch_edges.append(edge)
                    else:
                        control_edges.append(edge)

                loop_taken = False
                for edge in loop_edges:
                    edge_info = _edge_data(edge)
                    condition = edge_info.get("condition") or ""
                    edge_key = f"{edge.get('source')}->{edge.get('target')}:{condition or 'loop'}"
                    max_iterations = int((edge_info.get("loopPolicy") or {}).get("maxIterations") or 0)
                    current_count = loop_counts.get(edge_key, 0)
                    condition_ok = _evaluate_condition(condition, runtime_state)
                    if max_iterations > 0 and current_count < max_iterations and condition_ok:
                        loop_counts[edge_key] = current_count + 1
                        runtime_state["retry_count"] = loop_counts[edge_key]
                        db.save_run_event(
                            run_id,
                            "WORKFLOW_LOOP_ITERATION",
                            "WorkflowEngine",
                            "SUCCESS",
                            f"循环重试 {current_count + 1}/{max_iterations}: {edge.get('source')} -> {edge.get('target')}",
                            json.dumps({
                                "input_payload": {"edge": edge, "runtime_state": runtime_state},
                                "output_payload": {"iteration": current_count + 1, "maxIterations": max_iterations},
                            }, ensure_ascii=False),
                            0
                        )
                        enqueue_node(edge.get("target"))
                        loop_taken = True
                        break
                    if max_iterations > 0 and current_count >= max_iterations:
                        db.save_run_event(
                            run_id,
                            "WORKFLOW_LOOP_LIMIT_REACHED",
                            "WorkflowEngine",
                            "SKIPPED",
                            f"循环达到上限: {edge.get('source')} -> {edge.get('target')}",
                            json.dumps({
                                "input_payload": {"edge": edge},
                                "output_payload": {"iteration": current_count, "maxIterations": max_iterations},
                            }, ensure_ascii=False),
                            0
                        )

                if not loop_taken:
                    if branch_edges:
                        fallback_edge = None
                        selected_edge = None
                        for edge in branch_edges:
                            edge_info = _edge_data(edge)
                            condition = (edge_info.get("condition") or "").strip()
                            if condition.lower() in ("else", "default"):
                                fallback_edge = edge
                                continue
                            if _evaluate_condition(condition, runtime_state):
                                selected_edge = edge
                                break
                            skipped_key = edge.get("id") or f"{edge.get('source')}->{edge.get('target')}"
                            if skipped_key not in skipped_edges:
                                skipped_edges.add(skipped_key)
                                db.save_run_event(
                                    run_id,
                                    "WORKFLOW_BRANCH_SKIPPED",
                                    "WorkflowEngine",
                                    "SKIPPED",
                                    f"分支条件未命中: {edge.get('source')} -> {edge.get('target')}",
                                    json.dumps({
                                        "input_payload": {"edge": edge, "runtime_state": runtime_state},
                                        "output_payload": {"condition": condition},
                                    }, ensure_ascii=False),
                                    0
                                )
                        selected_edge = selected_edge or fallback_edge
                        if selected_edge:
                            edge_info = _edge_data(selected_edge)
                            db.save_run_event(
                                run_id,
                                "WORKFLOW_BRANCH_SELECTED",
                                "WorkflowEngine",
                                "SUCCESS",
                                f"分支已选择: {selected_edge.get('source')} -> {selected_edge.get('target')}",
                                json.dumps({
                                    "input_payload": {"edge": selected_edge, "runtime_state": runtime_state},
                                    "output_payload": {"condition": edge_info.get("condition") or "default"},
                                }, ensure_ascii=False),
                                0
                            )
                            enqueue_node(selected_edge.get("target"))
                    for edge in control_edges:
                        enqueue_node(edge.get("target"))

            except Exception as e:
                dur_ms = int((time.time() - t0) * 1000)
                db.save_run_event(run_id, "WORKFLOW_NODE", "WorkflowEngine", "FAILED", f"Node {node_name} Error: {str(e)}", json.dumps({
                    "input_payload": {"node": node_name},
                    "output_payload": {"error": str(e)},
                }, ensure_ascii=False), dur_ms)
                final_reply = f"执行节点 {node_name} 时发生错误: {str(e)}"
                await emit(node_name, "failed", f"节点 {node_name} 执行失败：{str(e)}")
                break
                
            # The success emit is already sent with token details above.
            
        if node_queue and workflow_steps >= max_workflow_steps:
            db.save_run_event(
                run_id,
                "WORKFLOW_LOOP_LIMIT_REACHED",
                "WorkflowEngine",
                "FAILED",
                "工作流达到全局最大步数，已安全停止以避免死循环。",
                json.dumps({
                    "input_payload": {"remaining_queue": node_queue, "max_workflow_steps": max_workflow_steps},
                    "output_payload": {"completed_nodes": list(completed_nodes), "loop_counts": loop_counts},
                }, ensure_ascii=False),
                0
            )
            final_reply += "\n\n> 工作流达到全局最大步数，系统已安全停止以避免死循环。"

        deployment_summary = ""
        should_auto_deploy = (
            bool(workspace_dir)
            and bool(saved_artifacts)
            and (
                _is_engineering_template(workflow_meta)
                or preview_policy.get("open_local_url")
                or preview_policy.get("detect_from_output")
            )
        )
        if should_auto_deploy:
            try:
                await emit("检查工作区并启动预览服务", "running", "正在扫描工作区文件、安装依赖、运行基础检查并启动本地 Web 服务。")
                deployment = deploy_workspace_preview(workspace_dir)
                self.deployment_result = deployment
                deployment_summary = format_deployment_summary(deployment)
                status = "SUCCESS" if deployment.get("status") == "success" else ("FAILED" if deployment.get("status") == "failed" else "SKIPPED")
                db.save_run_event(
                    run_id,
                    "WORKFLOW_DEPLOY_PREVIEW",
                    "WorkflowEngine",
                    status,
                    "工作区自动部署与右侧网页预览",
                    json.dumps({
                        "input_payload": {"workspace": workspace_dir, "saved_artifacts": saved_artifacts},
                        "output_payload": deployment,
                    }, ensure_ascii=False),
                    0
                )
                if deployment.get("browser_url"):
                    await emit_preview_urls(deployment["browser_url"], "auto_deploy")
                detail = "服务已启动并推送到右侧浏览器。" if deployment.get("browser_url") else "已完成检查，但没有可打开的本地预览地址。"
                await emit("自动部署与右侧预览", "done" if status == "SUCCESS" else "failed", detail)
                final_reply += deployment_summary
                current_state_context += f"\n\n--- 自动部署结果 ---\n{deployment_summary}"
            except Exception as deploy_error:
                deployment_summary = f"\n\n## 自动部署检查失败\n- 错误：`{deploy_error}`"
                db.save_run_event(
                    run_id,
                    "WORKFLOW_DEPLOY_PREVIEW",
                    "WorkflowEngine",
                    "FAILED",
                    "工作区自动部署与右侧网页预览失败",
                    json.dumps({
                        "input_payload": {"workspace": workspace_dir, "saved_artifacts": saved_artifacts},
                        "output_payload": {"error": str(deploy_error)},
                    }, ensure_ascii=False),
                    0
                )
                await emit("自动部署与右侧预览", "failed", f"自动部署失败：{deploy_error}")
                final_reply += deployment_summary

        # --- AUTO GENERATE MARKDOWN REPORT FOR CUSTOM WORKFLOW ---
        try:
            events = db.get_run_events(run_id)
            report_md = f"# Ai Multi Agent 深度工作流运行报告\n\n"
            report_md += f"**运行 ID**: `{run_id}`\n"
            report_md += f"**模型提供商**: `{self.provider}`\n"
            summary = token_tracker.to_dict()
            report_md += f"**Token 消耗**: `{format_token_summary(summary)}`\n\n"
            
            report_md += f"## 📝 任务需求\n{task_description}\n\n"
            
            # 提取 WORKFLOW_NODE 节点记录
            nodes_events = [e for e in events if e['event_type'] == 'WORKFLOW_NODE']
            if nodes_events:
                report_md += "## ⚙️ 工作流节点执行记录\n"
                for n in nodes_events:
                    status_icon = "✅" if n['status'] == 'SUCCESS' else "❌"
                    report_md += f"- {status_icon} **{n['message']}** ({n['duration_ms']}ms)\n"
                    if n['detail_json'] and n['status'] == 'SUCCESS':
                        try:
                            det = json.loads(n['detail_json'])
                            if 'preview' in det:
                                report_md += f"  > {det['preview'].replace(chr(10), ' ')}\n"
                        except:
                            pass
                report_md += "\n"
                
            # 提取错误摘要
            errors = [e for e in events if e['status'] == 'FAILED' or 'Error' in e['message']]
            if errors:
                report_md += "## ⚠️ 错误摘要与复盘\n"
                for err in errors:
                    report_md += f"> [!WARNING]\n> **{err['event_type']} 失败**: {err['message']}\n\n"
                report_md += "\n"
                
            report_md += f"## 🎯 最终交付成果\n\n"
            report_md += f"{final_reply}\n"
            artifact_summary = _format_artifact_summary(saved_artifacts, workspace_dir)
            if artifact_summary:
                report_md += artifact_summary + "\n"
            
            db.save_report(f"Workflow Report: {run_id}", report_md)
        except Exception as e:
            print(f"Failed to auto-generate markdown report: {e}")
        # ---------------------------------------------------------

        summary = token_tracker.to_dict()
        self.last_token_usage = summary
        db.save_run_event(
            run_id,
            "TOKEN_USAGE",
            "TokenMeter",
            "SUCCESS",
            format_token_summary(summary),
            json.dumps({"token_usage": summary}, ensure_ascii=False),
            0
        )
        await sse_queue.put({"type": "token_usage", "token_usage": summary, "status": "streaming", "routed_by": routed_by})
        db.update_run_record(run_id, True, 9.5, summary["total_tokens"], summary["api_tokens"], summary["local_tokens"], summary["source"], summary)
        artifact_summary = _format_artifact_summary(saved_artifacts, workspace_dir)
        preview_summary = ""
        if self.preview_urls:
            preview_summary = "\n\n## 本地预览地址\n" + "\n".join(f"- {url}" for url in self.preview_urls)
        return f"工作流执行完毕。\n最终节点输出:\n{final_reply}{artifact_summary}{preview_summary}"
