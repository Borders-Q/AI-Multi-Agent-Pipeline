# 天韬（SkyT） 流式输出链路

本文记录本地 GPU、API、执行步骤到前端的流式输出规则。

## API 流式

API 通过 `agent/llm_client.py::chat_completion(... stream_callback=...)` 流式返回。后端把每次 callback 转为 `/api/chat` 的 NDJSON 行：

```json
{"type":"message","status":"streaming","response":"..."}
```

结束后再统一写入 Token usage。流式过程中不要显示虚假的总 Token。

## 本地 GPU 流式

本地 Ollama 使用 `/api/chat` 的 `stream: true`。后端逐行读取 chunk，实时转发到前端。最终 chunk 中若包含 `prompt_eval_count` / `eval_count`，则记录为真实本地 Token；缺失时才估算。

如果 Ollama streaming 失败，后端会真实回退到一次性调用，不伪造逐字流式。

## 执行步骤流式

执行步骤使用：

```json
{"type":"execution_step","node":"...","state":"running|done","description":"..."}
```

每执行一步就展示一步。执行完成后，前端默认折叠步骤面板，用户可手动展开。

## 核心文件

- `server.py`：NDJSON 转发、Ollama streaming、`execution_step`。
- `agent/llm_client.py`：API streaming 和 usage 捕获。
- `frontend/src/App.jsx`：读取 NDJSON、渲染最终回答和执行步骤。

## 后续维护

新增模型 provider 时，先确认它是否支持流式 usage。不能支持时必须标记估算或回退原因。
