from textwrap import dedent


def _code(source: str) -> str:
    return dedent(source).strip() + "\n"


def _credential_connector_code(function_name: str, display_name: str, service_name: str, env_vars: list[str], action_description: str) -> str:
    return _code(f'''
        import os
        import json

        REQUIRED_ENV = {env_vars!r}

        def {function_name}(payload: str = ""):
            missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
            if missing:
                return (
                    "【{display_name}】已从云端应用市场拉取，但运行前需要配置凭据。\\n"
                    "缺少环境变量：" + ", ".join(missing) + "\\n"
                    "用途：{action_description}\\n"
                    "当前未执行外部请求，避免伪造成功结果。"
                )
            return (
                "【{display_name}】凭据检查通过。\\n"
                "服务：{service_name}\\n"
                "请求载荷摘要：" + (payload[:500] if payload else "未提供 payload") + "\\n"
                "说明：该连接器已安装，可在后续版本接入真实业务 API 调用。"
            )

        SCHEMA = {{
            "name": "{function_name}",
            "description": "{display_name} 连接器。{action_description}；未配置凭据时只返回配置提示，不伪造执行成功。",
            "parameters": {{
                "type": "object",
                "properties": {{
                    "payload": {{"type": "string", "description": "要发送给 {service_name} 的文本或 JSON 载荷", "default": ""}}
                }}
            }}
        }}
    ''')


MARKET_SKILLS = {
    "JSON_Formatter": {
        "id": "json_formatter",
        "name": "JSON_Formatter",
        "description": "格式化、压缩和校验 JSON 文本，适合整理 API 返回、运行事件和 I/O Payload。",
        "icon": "🧩",
        "category": "开发辅助",
        "code": _code(r'''
            import json

            def json_formatter(json_text: str, mode: str = "pretty"):
                try:
                    data = json.loads(json_text)
                except Exception as exc:
                    return "JSON 解析失败：" + str(exc)
                if mode == "compact":
                    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
                if mode == "keys":
                    if isinstance(data, dict):
                        return "顶层字段：" + ", ".join(map(str, data.keys()))
                    if isinstance(data, list):
                        return "数组长度：" + str(len(data))
                    return "JSON 类型：" + type(data).__name__
                return json.dumps(data, ensure_ascii=False, indent=2)

            SCHEMA = {
                "name": "json_formatter",
                "description": "格式化、压缩和校验 JSON 文本",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "json_text": {"type": "string", "description": "需要处理的 JSON 字符串"},
                        "mode": {"type": "string", "description": "pretty / compact / keys", "enum": ["pretty", "compact", "keys"], "default": "pretty"}
                    },
                    "required": ["json_text"]
                }
            }
        '''),
    },
    "Regex_Extractor": {
        "id": "regex_extractor",
        "name": "Regex_Extractor",
        "description": "按正则表达式从文本中提取信息，适合处理日志、报错、URL 和结构化片段。",
        "icon": "🔎",
        "category": "开发辅助",
        "code": _code(r'''
            import re
            import json

            def regex_extractor(text: str, pattern: str, max_results: int = 20):
                try:
                    matches = re.findall(pattern, text, flags=re.MULTILINE)
                except Exception as exc:
                    return "正则表达式无效：" + str(exc)
                limited = matches[:max(1, min(int(max_results or 20), 100))]
                return json.dumps({"count": len(matches), "results": limited}, ensure_ascii=False, indent=2)

            SCHEMA = {
                "name": "regex_extractor",
                "description": "按正则表达式从文本中提取信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "待提取文本"},
                        "pattern": {"type": "string", "description": "Python re 正则表达式"},
                        "max_results": {"type": "integer", "description": "最多返回条数", "default": 20}
                    },
                    "required": ["text", "pattern"]
                }
            }
        '''),
    },
    "Markdown_Table_Builder": {
        "id": "markdown_table_builder",
        "name": "Markdown_Table_Builder",
        "description": "把 CSV 风格文本转换为 Markdown 表格，用于报告、答辩材料和运行记录整理。",
        "icon": "📋",
        "category": "文档与比赛材料",
        "code": _code(r'''
            import csv
            import io

            def markdown_table_builder(csv_text: str):
                rows = list(csv.reader(io.StringIO(csv_text.strip())))
                rows = [[cell.strip() for cell in row] for row in rows if row]
                if not rows:
                    return "没有可转换的数据。"
                width = max(len(row) for row in rows)
                rows = [row + [""] * (width - len(row)) for row in rows]
                header = rows[0]
                body = rows[1:]
                lines = [
                    "| " + " | ".join(header) + " |",
                    "| " + " | ".join(["---"] * width) + " |",
                ]
                for row in body:
                    lines.append("| " + " | ".join(row) + " |")
                return "\n".join(lines)

            SCHEMA = {
                "name": "markdown_table_builder",
                "description": "把 CSV 风格文本转换为 Markdown 表格",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "csv_text": {"type": "string", "description": "逗号分隔文本，第一行为表头"}
                    },
                    "required": ["csv_text"]
                }
            }
        '''),
    },
    "Text_Insight_Counter": {
        "id": "text_insight_counter",
        "name": "Text_Insight_Counter",
        "description": "统计文本字数、行数、关键词频次，适合分析需求文档、运行日志和演讲稿。",
        "icon": "📊",
        "category": "文档与比赛材料",
        "code": _code(r'''
            def text_insight_counter(text: str, keyword: str = ""):
                lines = text.splitlines()
                non_empty = [line for line in lines if line.strip()]
                chinese_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
                ascii_words = len([part for part in text.replace("\n", " ").split(" ") if part.strip()])
                result = [
                    "总字符数：" + str(len(text)),
                    "中文字符数：" + str(chinese_chars),
                    "英文/符号词片段数：" + str(ascii_words),
                    "总行数：" + str(len(lines)),
                    "非空行数：" + str(len(non_empty)),
                ]
                if keyword:
                    result.append("关键词 `" + keyword + "` 出现次数：" + str(text.count(keyword)))
                return "\n".join(result)

            SCHEMA = {
                "name": "text_insight_counter",
                "description": "统计文本字数、行数、关键词频次",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "待统计文本"},
                        "keyword": {"type": "string", "description": "可选关键词", "default": ""}
                    },
                    "required": ["text"]
                }
            }
        '''),
    },
    "Requirement_Summarizer": {
        "id": "requirement_summarizer",
        "name": "Requirement_Summarizer",
        "description": "把用户需求整理为目标、功能、技术栈、风险和下一步，适合 GPU 辅助 API 前置压缩。",
        "icon": "🧠",
        "category": "运行分析",
        "code": _code(r'''
            def requirement_summarizer(requirement: str):
                text = requirement.strip()
                tech_keywords = ["flask", "fastapi", "sqlite", "react", "vite", "python", "html", "css", "js", "ts", "typescript", "gpu", "api"]
                matched = [kw for kw in tech_keywords if kw.lower() in text.lower()]
                lines = [
                    "# 需求整理",
                    "## 原始目标",
                    text[:800] if text else "未提供需求。",
                    "## 识别到的技术要素",
                    "、".join(matched) if matched else "未明确指定技术栈。",
                    "## 建议下一步",
                    "1. 确认必须落盘的文件范围。",
                    "2. 生成可审查计划。",
                    "3. 再进入代码生成、检查与报告。",
                ]
                return "\n".join(lines)

            SCHEMA = {
                "name": "requirement_summarizer",
                "description": "整理用户需求为结构化 Markdown",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "requirement": {"type": "string", "description": "用户原始需求"}
                    },
                    "required": ["requirement"]
                }
            }
        '''),
    },
    "Markdown_Report_Outline": {
        "id": "markdown_report_outline",
        "name": "Markdown_Report_Outline",
        "description": "根据任务主题生成中文 Markdown 报告大纲，用于比赛展示和历史工作记录。",
        "icon": "📝",
        "category": "文档与比赛材料",
        "code": _code(r'''
            def markdown_report_outline(title: str, context: str = ""):
                title = title.strip() or "天韬（SkyT）任务报告"
                return "\n".join([
                    "# " + title,
                    "## 1. 任务背景",
                    context[:500] if context else "说明任务来源、目标和约束。",
                    "## 2. 执行过程",
                    "- 需求理解",
                    "- 工作流编排",
                    "- 工具调用与验证",
                    "## 3. 产出结果",
                    "- 生成文件",
                    "- 运行地址",
                    "- 报告结论",
                    "## 4. 风险与后续优化",
                    "- 需要人工确认的内容",
                    "- 后续可扩展方向",
                ])

            SCHEMA = {
                "name": "markdown_report_outline",
                "description": "生成中文 Markdown 报告大纲",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "报告标题"},
                        "context": {"type": "string", "description": "任务上下文", "default": ""}
                    },
                    "required": ["title"]
                }
            }
        '''),
    },
    "Log_Error_Analyzer": {
        "id": "log_error_analyzer",
        "name": "Log_Error_Analyzer",
        "description": "从日志中提取错误类型、最后报错位置和建议动作。",
        "icon": "🧯",
        "category": "开发辅助",
        "code": _code(r'''
            import re

            def log_error_analyzer(log_text: str):
                lines = [line for line in log_text.splitlines() if line.strip()]
                error_lines = [line for line in lines if re.search(r"error|exception|traceback|failed|失败|报错", line, re.I)]
                tail = "\n".join(lines[-20:])
                return "\n".join([
                    "# 日志错误分析",
                    "错误相关行数：" + str(len(error_lines)),
                    "最后一条错误：" + (error_lines[-1] if error_lines else "未识别到明显错误行"),
                    "## 最近日志片段",
                    tail,
                    "## 建议",
                    "优先检查最后一条错误附近的文件、端口、依赖和环境变量。"
                ])

            SCHEMA = {
                "name": "log_error_analyzer",
                "description": "分析日志错误并输出中文诊断摘要",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_text": {"type": "string", "description": "日志文本"}
                    },
                    "required": ["log_text"]
                }
            }
        '''),
    },
    "API_Payload_Inspector": {
        "id": "api_payload_inspector",
        "name": "API_Payload_Inspector",
        "description": "检查 API Payload 的字段、大小和潜在空值，适合深度回放 I/O 排查。",
        "icon": "📦",
        "category": "运行分析",
        "code": _code(r'''
            import json

            def api_payload_inspector(payload: str):
                size = len(payload.encode("utf-8"))
                try:
                    data = json.loads(payload)
                except Exception as exc:
                    return "Payload 大小：" + str(size) + " bytes\nJSON 解析失败：" + str(exc)
                if isinstance(data, dict):
                    empty = [k for k, v in data.items() if v in (None, "", [], {})]
                    return "\n".join([
                        "Payload 大小：" + str(size) + " bytes",
                        "顶层字段数：" + str(len(data)),
                        "顶层字段：" + ", ".join(map(str, data.keys())),
                        "空值字段：" + (", ".join(map(str, empty)) if empty else "无明显空值")
                    ])
                if isinstance(data, list):
                    return "Payload 大小：" + str(size) + " bytes\n数组长度：" + str(len(data))
                return "Payload 大小：" + str(size) + " bytes\nJSON 类型：" + type(data).__name__

            SCHEMA = {
                "name": "api_payload_inspector",
                "description": "检查 API Payload 字段、大小和空值",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "payload": {"type": "string", "description": "JSON 或文本 Payload"}
                    },
                    "required": ["payload"]
                }
            }
        '''),
    },
    "File_Tree_Summarizer": {
        "id": "file_tree_summarizer",
        "name": "File_Tree_Summarizer",
        "description": "压缩目录树文本，提取核心文件类型和可展示重点。",
        "icon": "🌳",
        "category": "开发辅助",
        "code": _code(r'''
            import os
            from collections import Counter

            def file_tree_summarizer(tree_text: str):
                files = []
                for line in tree_text.splitlines():
                    token = line.strip().split(" ")[-1].strip("`|+-")
                    if "." in token and not token.endswith("."):
                        files.append(token)
                ext_counter = Counter(os.path.splitext(name)[1].lower() or "[无扩展名]" for name in files)
                top = "\n".join(["- " + ext + ": " + str(count) for ext, count in ext_counter.most_common(10)])
                return "\n".join([
                    "# 目录树摘要",
                    "识别文件数：" + str(len(files)),
                    "## 扩展名分布",
                    top if top else "未识别到文件。",
                    "## 建议展示重点",
                    "优先展示入口文件、配置文件、模板页面、静态资源和 README。"
                ])

            SCHEMA = {
                "name": "file_tree_summarizer",
                "description": "压缩目录树文本并提取文件类型分布",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tree_text": {"type": "string", "description": "目录树文本"}
                    },
                    "required": ["tree_text"]
                }
            }
        '''),
    },
    "Code_Snippet_Packager": {
        "id": "code_snippet_packager",
        "name": "Code_Snippet_Packager",
        "description": "给代码片段补 Markdown 文件名代码块，便于工作流落盘和报告展示。",
        "icon": "🧱",
        "category": "开发辅助",
        "code": _code(r'''
            def code_snippet_packager(file_name: str, code: str, language: str = ""):
                language = language.strip() or (file_name.rsplit(".", 1)[-1] if "." in file_name else "")
                return "```" + language + " " + file_name + "\n" + code.rstrip() + "\n```"

            SCHEMA = {
                "name": "code_snippet_packager",
                "description": "把代码片段包装为带文件名的 Markdown 代码块",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_name": {"type": "string", "description": "文件名，例如 app.py"},
                        "code": {"type": "string", "description": "代码内容"},
                        "language": {"type": "string", "description": "代码语言，可选", "default": ""}
                    },
                    "required": ["file_name", "code"]
                }
            }
        '''),
    },
    "Run_Record_Summarizer": {
        "id": "run_record_summarizer",
        "name": "Run_Record_Summarizer",
        "description": "把运行记录 JSON 或文本压缩为中文工作记录摘要。",
        "icon": "🗂️",
        "category": "运行分析",
        "code": _code(r'''
            import json

            def run_record_summarizer(run_data: str):
                try:
                    data = json.loads(run_data)
                except Exception:
                    data = {"raw": run_data}
                title = data.get("title") or data.get("run_id") or "未命名运行"
                status = data.get("status") or data.get("state") or "未知"
                tokens = data.get("total_tokens") or data.get("tokens") or "未记录"
                return "\n".join([
                    "# 运行记录摘要",
                    "- 标题：" + str(title),
                    "- 状态：" + str(status),
                    "- Token：" + str(tokens),
                    "- 建议：在深度回放中优先查看失败事件、工具调用和最终报告。"
                ])

            SCHEMA = {
                "name": "run_record_summarizer",
                "description": "压缩运行记录为中文工作记录摘要",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "run_data": {"type": "string", "description": "运行记录 JSON 或文本"}
                    },
                    "required": ["run_data"]
                }
            }
        '''),
    },
    "Token_Usage_Summarizer": {
        "id": "token_usage_summarizer",
        "name": "Token_Usage_Summarizer",
        "description": "整理 API / 本地 GPU Token 消耗，突出真实值与估算值。",
        "icon": "🪙",
        "category": "运行分析",
        "code": _code(r'''
            import json

            def token_usage_summarizer(token_usage_json: str):
                try:
                    data = json.loads(token_usage_json)
                except Exception:
                    return "Token 数据不是标准 JSON：\n" + token_usage_json[:1000]
                api = data.get("api_tokens", 0)
                local = data.get("local_tokens", 0)
                total = data.get("total_tokens", api + local)
                source = data.get("source") or data.get("token_source") or "未知"
                return "\n".join([
                    "# Token 消耗摘要",
                    "- API Token：" + str(api),
                    "- 本地 Token：" + str(local),
                    "- 总计：" + str(total),
                    "- 来源：" + str(source),
                    "- 建议：优先让本地 GPU 做上下文压缩，再把高价值上下文交给 API。"
                ])

            SCHEMA = {
                "name": "token_usage_summarizer",
                "description": "整理 API / 本地 GPU Token 消耗",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token_usage_json": {"type": "string", "description": "Token usage JSON"}
                    },
                    "required": ["token_usage_json"]
                }
            }
        '''),
    },
    "Replay_Event_Summarizer": {
        "id": "replay_event_summarizer",
        "name": "Replay_Event_Summarizer",
        "description": "将深度回放事件列表整理成可讲解的中文时间线。",
        "icon": "🎞️",
        "category": "运行分析",
        "code": _code(r'''
            import json

            def replay_event_summarizer(events_json: str, max_items: int = 8):
                try:
                    events = json.loads(events_json)
                except Exception:
                    return "事件数据不是标准 JSON：\n" + events_json[:1000]
                if not isinstance(events, list):
                    return "事件数据应为数组。"
                lines = ["# 深度回放时间线摘要"]
                for idx, event in enumerate(events[:max(1, min(int(max_items or 8), 30))], 1):
                    event_type = event.get("event_type") or event.get("type") or "UNKNOWN"
                    summary = event.get("summary") or event.get("message") or event.get("detail") or ""
                    lines.append(str(idx) + ". " + str(event_type) + " - " + str(summary)[:160])
                return "\n".join(lines)

            SCHEMA = {
                "name": "replay_event_summarizer",
                "description": "整理深度回放事件为中文时间线",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "events_json": {"type": "string", "description": "事件数组 JSON"},
                        "max_items": {"type": "integer", "description": "最多摘要条数", "default": 8}
                    },
                    "required": ["events_json"]
                }
            }
        '''),
    },
    "Failure_Reason_Digest": {
        "id": "failure_reason_digest",
        "name": "Failure_Reason_Digest",
        "description": "从失败文本中归纳原因、影响和修复优先级。",
        "icon": "🧭",
        "category": "运行分析",
        "code": _code(r'''
            def failure_reason_digest(error_text: str):
                text = error_text.strip()
                lower = text.lower()
                hints = []
                if "port" in lower or "端口" in text:
                    hints.append("端口占用或服务启动冲突")
                if "module not found" in lower or "no module named" in lower:
                    hints.append("依赖缺失")
                if "syntaxerror" in lower:
                    hints.append("语法错误")
                if "permission" in lower or "access" in lower:
                    hints.append("权限或文件占用")
                return "\n".join([
                    "# 失败原因归纳",
                    "可能原因：" + ("、".join(hints) if hints else "需要结合日志继续确认"),
                    "错误片段：",
                    text[:1000],
                    "建议优先级：1. 复现错误 2. 检查依赖/端口/语法 3. 重新运行验证。"
                ])

            SCHEMA = {
                "name": "failure_reason_digest",
                "description": "归纳失败原因和修复优先级",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "error_text": {"type": "string", "description": "错误文本"}
                    },
                    "required": ["error_text"]
                }
            }
        '''),
    },
    "Env_Var_Checklist": {
        "id": "env_var_checklist",
        "name": "Env_Var_Checklist",
        "description": "把需要配置的环境变量整理成检查清单，适合部署依赖和密钥准备。",
        "icon": "🔐",
        "category": "开发辅助",
        "code": _code(r'''
            def env_var_checklist(env_names: str):
                names = [name.strip() for name in env_names.replace("\n", ",").split(",") if name.strip()]
                if not names:
                    return "未提供环境变量名称。"
                lines = ["# 环境变量检查清单"]
                for name in names:
                    lines.append("- [ ] " + name + "：待配置")
                lines.append("\n建议：密钥类变量不要写入仓库，优先放入 .env 或系统环境变量。")
                return "\n".join(lines)

            SCHEMA = {
                "name": "env_var_checklist",
                "description": "生成环境变量配置检查清单",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "env_names": {"type": "string", "description": "环境变量名称，逗号或换行分隔"}
                    },
                    "required": ["env_names"]
                }
            }
        '''),
    },
    "Port_Conflict_Diagnoser": {
        "id": "port_conflict_diagnoser",
        "name": "Port_Conflict_Diagnoser",
        "description": "根据端口和日志生成端口占用排查建议，适合右侧网页预览失败场景。",
        "icon": "🔌",
        "category": "运行分析",
        "code": _code(r'''
            def port_conflict_diagnoser(port: int, log_text: str = ""):
                port = int(port)
                return "\n".join([
                    "# 端口冲突诊断",
                    "- 目标端口：" + str(port),
                    "- 常见原因：旧服务未关闭、端口被系统进程占用、服务启动后立即崩溃。",
                    "- 建议命令：netstat -ano | findstr :" + str(port),
                    "- 建议策略：不要强杀未知进程，优先切换到下一个可用端口并更新右侧预览地址。",
                    "## 日志片段",
                    (log_text[:800] if log_text else "未提供日志。")
                ])

            SCHEMA = {
                "name": "port_conflict_diagnoser",
                "description": "生成端口占用排查建议",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "port": {"type": "integer", "description": "端口号"},
                        "log_text": {"type": "string", "description": "可选日志文本", "default": ""}
                    },
                    "required": ["port"]
                }
            }
        '''),
    },
    "Localhost_URL_Extractor": {
        "id": "localhost_url_extractor",
        "name": "Localhost_URL_Extractor",
        "description": "从输出文本中提取 localhost / 127.0.0.1 预览地址。",
        "icon": "🖥️",
        "category": "运行分析",
        "code": _code(r'''
            import re
            import json

            def localhost_url_extractor(text: str):
                pattern = r"https?://(?:127\.0\.0\.1|localhost):\d+(?:/[^\s`)]*)?"
                urls = sorted(set(re.findall(pattern, text)))
                return json.dumps({"count": len(urls), "urls": urls}, ensure_ascii=False, indent=2)

            SCHEMA = {
                "name": "localhost_url_extractor",
                "description": "提取本地预览 URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "输出文本"}
                    },
                    "required": ["text"]
                }
            }
        '''),
    },
    "Requirements_Generator": {
        "id": "requirements_generator",
        "name": "Requirements_Generator",
        "description": "根据项目类型生成基础 requirements.txt 建议。",
        "icon": "📦",
        "category": "开发辅助",
        "code": _code(r'''
            def requirements_generator(project_type: str = "flask"):
                key = project_type.lower()
                deps = ["python-dotenv", "requests"]
                if "fastapi" in key:
                    deps = ["fastapi", "uvicorn", "pydantic", "python-dotenv", "requests"]
                elif "flask" in key:
                    deps = ["flask", "jinja2", "python-dotenv", "requests"]
                elif "ai" in key or "agent" in key:
                    deps = ["fastapi", "uvicorn", "openai", "requests", "python-dotenv", "pydantic"]
                return "\n".join(deps)

            SCHEMA = {
                "name": "requirements_generator",
                "description": "生成基础 Python requirements.txt 建议",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_type": {"type": "string", "description": "项目类型，例如 flask / fastapi / ai-agent", "default": "flask"}
                    }
                }
            }
        '''),
    },
    "SQL_Schema_Draft": {
        "id": "sql_schema_draft",
        "name": "SQL_Schema_Draft",
        "description": "根据实体名称生成 SQLite 建表草稿，用于管理系统类项目演示。",
        "icon": "🗄️",
        "category": "开发辅助",
        "code": _code(r'''
            def sql_schema_draft(entity_name: str, fields: str = ""):
                table = entity_name.strip().lower().replace(" ", "_") or "records"
                field_names = [f.strip() for f in fields.replace("\n", ",").split(",") if f.strip()]
                lines = ["CREATE TABLE IF NOT EXISTS " + table + " (", "  id INTEGER PRIMARY KEY AUTOINCREMENT,"]
                if field_names:
                    for name in field_names:
                        safe = name.lower().replace(" ", "_")
                        lines.append("  " + safe + " TEXT,")
                else:
                    lines.extend(["  name TEXT NOT NULL,", "  category TEXT,", "  status TEXT,", "  remark TEXT,"])
                lines.append("  created_at TEXT DEFAULT CURRENT_TIMESTAMP")
                lines.append(");")
                return "\n".join(lines)

            SCHEMA = {
                "name": "sql_schema_draft",
                "description": "生成 SQLite 建表草稿",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_name": {"type": "string", "description": "实体或表名"},
                        "fields": {"type": "string", "description": "字段名，逗号或换行分隔", "default": ""}
                    },
                    "required": ["entity_name"]
                }
            }
        '''),
    },
    "HTML_Form_Checker": {
        "id": "html_form_checker",
        "name": "HTML_Form_Checker",
        "description": "检查 HTML 表单是否包含 label、name、必填项和提交按钮。",
        "icon": "🧾",
        "category": "开发辅助",
        "code": _code(r'''
            import re

            def html_form_checker(html: str):
                form_count = len(re.findall(r"<form\b", html, re.I))
                input_count = len(re.findall(r"<input\b|<textarea\b|<select\b", html, re.I))
                label_count = len(re.findall(r"<label\b", html, re.I))
                submit_count = len(re.findall(r"type=['\"]submit['\"]|<button\b", html, re.I))
                return "\n".join([
                    "# HTML 表单检查",
                    "- form 数量：" + str(form_count),
                    "- 输入控件数量：" + str(input_count),
                    "- label 数量：" + str(label_count),
                    "- 提交按钮线索：" + str(submit_count),
                    "- 建议：" + ("结构基本完整。" if form_count and input_count and submit_count else "请补齐 form、输入控件和提交按钮。")
                ])

            SCHEMA = {
                "name": "html_form_checker",
                "description": "检查 HTML 表单结构完整性",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "html": {"type": "string", "description": "HTML 文本"}
                    },
                    "required": ["html"]
                }
            }
        '''),
    },
    "CSS_Theme_Inspector": {
        "id": "css_theme_inspector",
        "name": "CSS_Theme_Inspector",
        "description": "粗略检查 CSS 颜色、变量和响应式媒体查询数量。",
        "icon": "🎨",
        "category": "开发辅助",
        "code": _code(r'''
            import re

            def css_theme_inspector(css: str):
                hex_colors = re.findall(r"#[0-9a-fA-F]{3,8}\b", css)
                variables = re.findall(r"--[a-zA-Z0-9_-]+", css)
                media = re.findall(r"@media\b", css)
                return "\n".join([
                    "# CSS 主题检查",
                    "- 十六进制颜色数量：" + str(len(hex_colors)),
                    "- CSS 变量数量：" + str(len(set(variables))),
                    "- 媒体查询数量：" + str(len(media)),
                    "- 建议：核心颜色优先抽成变量，深浅色适配避免写死单一颜色。"
                ])

            SCHEMA = {
                "name": "css_theme_inspector",
                "description": "检查 CSS 颜色、变量和响应式线索",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "css": {"type": "string", "description": "CSS 文本"}
                    },
                    "required": ["css"]
                }
            }
        '''),
    },
    "CSV_Summarizer": {
        "id": "csv_summarizer",
        "name": "CSV_Summarizer",
        "description": "统计 CSV 行列数量和空值情况，用于快速理解数据文件。",
        "icon": "📑",
        "category": "文档与比赛材料",
        "code": _code(r'''
            import csv
            import io

            def csv_summarizer(csv_text: str):
                rows = list(csv.reader(io.StringIO(csv_text.strip())))
                if not rows:
                    return "CSV 为空。"
                width = max(len(row) for row in rows)
                empty_cells = sum(1 for row in rows for cell in row if not cell.strip())
                return "\n".join([
                    "# CSV 摘要",
                    "- 行数：" + str(len(rows)),
                    "- 最大列数：" + str(width),
                    "- 空单元格数：" + str(empty_cells),
                    "- 表头：" + ("、".join(rows[0]) if rows else "无")
                ])

            SCHEMA = {
                "name": "csv_summarizer",
                "description": "统计 CSV 行列和空值情况",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "csv_text": {"type": "string", "description": "CSV 文本"}
                    },
                    "required": ["csv_text"]
                }
            }
        '''),
    },
    "Competition_Demo_Script": {
        "id": "competition_demo_script",
        "name": "Competition_Demo_Script",
        "description": "根据功能点生成比赛演示讲解顺序，适合答辩前快速整理。",
        "icon": "🎤",
        "category": "文档与比赛材料",
        "code": _code(r'''
            def competition_demo_script(project_name: str, features: str):
                items = [item.strip() for item in features.replace("\n", "、").split("、") if item.strip()]
                lines = ["# " + project_name + " 演示讲解顺序"]
                lines.append("1. 用一句话说明项目价值。")
                for idx, item in enumerate(items, 2):
                    lines.append(str(idx) + ". 展示：" + item)
                lines.append(str(len(items) + 2) + ". 回到运行历史、深度回放和报告，强调可复盘闭环。")
                return "\n".join(lines)

            SCHEMA = {
                "name": "competition_demo_script",
                "description": "生成比赛演示讲解顺序",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "项目名称"},
                        "features": {"type": "string", "description": "功能点，顿号或换行分隔"}
                    },
                    "required": ["project_name", "features"]
                }
            }
        '''),
    },
    "Test_Case_Generator": {
        "id": "test_case_generator",
        "name": "Test_Case_Generator",
        "description": "根据功能生成简洁测试用例清单，用于工作流验证报告。",
        "icon": "✅",
        "category": "开发辅助",
        "code": _code(r'''
            def test_case_generator(feature: str):
                return "\n".join([
                    "# 测试用例：" + feature,
                    "- 正常路径：输入合法数据，确认功能成功。",
                    "- 空数据路径：输入为空，确认页面或接口给出提示。",
                    "- 异常路径：输入非法数据，确认不会崩溃。",
                    "- 回归路径：刷新页面或重启服务后，确认数据仍可用。",
                    "- 展示路径：准备一条适合比赛演示的最短闭环。"
                ])

            SCHEMA = {
                "name": "test_case_generator",
                "description": "生成简洁测试用例清单",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feature": {"type": "string", "description": "要测试的功能"}
                    },
                    "required": ["feature"]
                }
            }
        '''),
    },
    "Install_Command_Builder": {
        "id": "install_command_builder",
        "name": "Install_Command_Builder",
        "description": "按国内网络生成 pip/npm 清华源安装命令。",
        "icon": "⚙️",
        "category": "开发辅助",
        "code": _code(r'''
            def install_command_builder(python_packages: str = "", npm_packages: str = ""):
                py = " ".join([p.strip() for p in python_packages.replace(",", " ").split() if p.strip()])
                npm = " ".join([p.strip() for p in npm_packages.replace(",", " ").split() if p.strip()])
                lines = ["# 国内网络安装命令"]
                if py:
                    lines.append("python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple " + py)
                if npm:
                    lines.append("npm install --registry https://mirrors.tuna.tsinghua.edu.cn/npm/ " + npm)
                if not py and not npm:
                    lines.append("未提供依赖名称。")
                return "\n".join(lines)

            SCHEMA = {
                "name": "install_command_builder",
                "description": "生成清华源 pip/npm 安装命令",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "python_packages": {"type": "string", "description": "Python 包名，空格或逗号分隔", "default": ""},
                        "npm_packages": {"type": "string", "description": "npm 包名，空格或逗号分隔", "default": ""}
                    }
                }
            }
        '''),
    },
    "Webpage_Title_Fetcher": {
        "id": "webpage_title_fetcher",
        "name": "Webpage_Title_Fetcher",
        "description": "联网读取网页标题和描述，适合快速检查本地预览或公开页面。",
        "icon": "🌐",
        "category": "联网可选",
        "requires_network": True,
        "code": _code(r'''
            import urllib.request
            import re

            def webpage_title_fetcher(url: str):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        html = response.read(200000).decode("utf-8", errors="ignore")
                    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
                    desc_match = re.search(r"<meta[^>]+name=['\\\"]description['\\\"][^>]+content=['\\\"](.*?)['\\\"]", html, re.I | re.S)
                    title = re.sub(r"\\s+", " ", title_match.group(1)).strip() if title_match else "未找到 title"
                    desc = re.sub(r"\\s+", " ", desc_match.group(1)).strip() if desc_match else "未找到 description"
                    return "标题：" + title + "\n描述：" + desc
                except Exception as exc:
                    return "网页读取失败：" + str(exc)

            SCHEMA = {
                "name": "webpage_title_fetcher",
                "description": "联网读取网页标题和描述",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "网页 URL"}
                    },
                    "required": ["url"]
                }
            }
        '''),
    },
    "Github_Repo_Analyzer": {
        "id": "github_analyzer",
        "name": "Github_Repo_Analyzer",
        "description": "获取指定 GitHub 仓库的基础信息，如 Stars、Forks、主要语言和描述。",
        "icon": "🐙",
        "category": "联网可选",
        "requires_network": True,
        "code": _code(r'''
            import urllib.request
            import json

            def analyze_github_repo(repo_name: str):
                try:
                    url = "https://api.github.com/repos/" + repo_name
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=12) as response:
                        data = json.loads(response.read().decode())
                    return (
                        "仓库：" + str(data.get("full_name")) + "\n"
                        "描述：" + str(data.get("description")) + "\n"
                        "Stars：" + str(data.get("stargazers_count")) + "\n"
                        "Forks：" + str(data.get("forks_count")) + "\n"
                        "主要语言：" + str(data.get("language"))
                    )
                except Exception as exc:
                    return "查询 GitHub 仓库失败，请确保格式为 owner/repo：" + str(exc)

            SCHEMA = {
                "name": "analyze_github_repo",
                "description": "获取 GitHub 仓库信息，如 Stars、Forks 和描述",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string", "description": "仓库名称，格式 owner/repo"}
                    },
                    "required": ["repo_name"]
                }
            }
        '''),
    },
    "Crypto_Price_Tracker": {
        "id": "crypto_tracker",
        "name": "Crypto_Price_Tracker",
        "description": "查询加密货币实时美元价格，使用 CoinGecko 公开接口。",
        "icon": "💰",
        "category": "联网可选",
        "requires_network": True,
        "code": _code(r'''
            import urllib.request
            import json

            def get_crypto_price(coin_id: str):
                try:
                    url = "https://api.coingecko.com/api/v3/simple/price?ids=" + coin_id + "&vs_currencies=usd"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=12) as response:
                        data = json.loads(response.read().decode())
                    if coin_id in data:
                        return coin_id.upper() + " 当前价格为 $" + str(data[coin_id]["usd"])
                    return "未找到代币：" + coin_id
                except Exception as exc:
                    return "查询币价失败：" + str(exc)

            SCHEMA = {
                "name": "get_crypto_price",
                "description": "获取指定加密货币的最新美元价格",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coin_id": {"type": "string", "description": "CoinGecko ID，如 bitcoin / ethereum"}
                    },
                    "required": ["coin_id"]
                }
            }
        '''),
    },
    "Slack_Notifier": {
        "id": "slack_notifier",
        "name": "Slack_Notifier",
        "description": "向 Slack Channel 发送通知；需要配置 SLACK_WEBHOOK_URL。",
        "icon": "💬",
        "category": "需密钥连接器",
        "requires_network": True,
        "credential_required": True,
        "credential_note": "需要环境变量 SLACK_WEBHOOK_URL。",
        "code": _credential_connector_code("slack_notifier", "Slack_Notifier", "Slack", ["SLACK_WEBHOOK_URL"], "发送工作流完成通知或失败提醒"),
    },
    "Notion_Page_Sync": {
        "id": "notion_page_sync",
        "name": "Notion_Page_Sync",
        "description": "同步或创建 Notion 页面；需要配置 Notion Token 和父页面 ID。",
        "icon": "📓",
        "category": "需密钥连接器",
        "requires_network": True,
        "credential_required": True,
        "credential_note": "需要 NOTION_TOKEN、NOTION_PARENT_PAGE_ID。",
        "code": _credential_connector_code("notion_page_sync", "Notion_Page_Sync", "Notion", ["NOTION_TOKEN", "NOTION_PARENT_PAGE_ID"], "把任务总结或报告同步到 Notion"),
    },
    "Jira_Ticket_Creator": {
        "id": "jira_ticket_creator",
        "name": "Jira_Ticket_Creator",
        "description": "创建 Jira 工单；需要配置 Jira 地址、邮箱和 API Token。",
        "icon": "🎫",
        "category": "需密钥连接器",
        "requires_network": True,
        "credential_required": True,
        "credential_note": "需要 JIRA_BASE_URL、JIRA_EMAIL、JIRA_API_TOKEN。",
        "code": _credential_connector_code("jira_ticket_creator", "Jira_Ticket_Creator", "Jira", ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"], "把失败运行或修复任务转成 Jira 工单"),
    },
    "AWS_S3_Manager": {
        "id": "aws_s3_manager",
        "name": "AWS_S3_Manager",
        "description": "管理 S3 对象；需要 AWS 凭据和 Bucket 配置。",
        "icon": "☁️",
        "category": "需密钥连接器",
        "requires_network": True,
        "credential_required": True,
        "credential_note": "需要 AWS_ACCESS_KEY_ID、AWS_SECRET_ACCESS_KEY、AWS_DEFAULT_REGION、AWS_S3_BUCKET。",
        "code": _credential_connector_code("aws_s3_manager", "AWS_S3_Manager", "AWS S3", ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION", "AWS_S3_BUCKET"], "上传或列出工作流产物"),
    },
    "PostgreSQL_Query": {
        "id": "postgresql_query",
        "name": "PostgreSQL_Query",
        "description": "PostgreSQL 只读查询连接器；需要 DATABASE_URL。",
        "icon": "🐘",
        "category": "需密钥连接器",
        "requires_network": True,
        "credential_required": True,
        "credential_note": "需要 DATABASE_URL，且环境中安装 psycopg/psycopg2 后才能真实查询。",
        "code": _credential_connector_code("postgresql_query", "PostgreSQL_Query", "PostgreSQL", ["DATABASE_URL"], "执行只读 SQL 查询和结构分析"),
    },
    "MySQL_Analyzer": {
        "id": "mysql_analyzer",
        "name": "MySQL_Analyzer",
        "description": "MySQL 结构分析连接器；需要 MySQL 连接环境变量。",
        "icon": "🐬",
        "category": "需密钥连接器",
        "requires_network": True,
        "credential_required": True,
        "credential_note": "需要 MYSQL_HOST、MYSQL_USER、MYSQL_PASSWORD、MYSQL_DATABASE。",
        "code": _credential_connector_code("mysql_analyzer", "MySQL_Analyzer", "MySQL", ["MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"], "分析数据库表结构与查询性能线索"),
    },
}
