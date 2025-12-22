# 环节2（Phase 2）实现总结

## ✅ 已完成的工作

### 1. 创建了 `code_app/backend/phase2_agent.py` 文件

包含以下功能：

- **PHASE2_SYSTEM_PROMPT_ADDON**: 环节2系统提示，指导Agent如何总结和回答排名结果相关问题
- **PHASE2_QUESTION_TYPES**: 问题类型识别和回答策略指导
- **prepare_phase2_messages()**: 准备环节2的消息，添加排名结果上下文
- **manage_phase2_context()**: 管理环节2的对话上下文，确保包含结果总结
- **highlight_methods_in_response()**: 高亮显示方法名（用于前端显示）
- **extract_ranking_results_from_messages()**: 从消息历史中提取排名结果
- **is_phase2_request()**: 检测是否为环节2请求

### 2. 修改了 `code_app/backend/main.py`

- ✅ 添加了环节2函数的导入
- ✅ 修改了 `ChatRequest` 模型，添加 `ranking_results` 字段（可选）
- ✅ 修改了 `agent_chat()` 函数，集成环节2检测和处理逻辑
- ✅ 修改了 `_call_openai()` 函数，支持无工具调用（纯对话模式）

### 3. 核心功能

**环节2检测逻辑**：
- 如果请求中包含 `ranking_results`，自动检测为环节2
- 如果没有显式提供，会尝试从消息历史中提取
- 使用 `is_phase2_request()` 函数进行智能检测

**环节2处理流程**：
1. 检测到环节2请求后，使用 `prepare_phase2_messages()` 准备消息
2. 添加排名结果上下文（Top 5方法、参数、统计信息）
3. 调用OpenAI API，**不使用工具**（纯对话模式）
4. 返回Agent的回答

---

## ⏳ 待完成的工作（前端）

### 1. 修改前端 `agent_context` 结构

**文件**: `code_app/frontend/main.py`

**位置**: `get_client_state()` 函数

需要添加 `ranking_results` 字段：

```python
'agent_context': {
    'conversation_history': [],
    'current_stage': 'awaiting_upload',
    'user_preferences': {},
    'data_insights': {},
    'ranking_results': None,  # 新增：存储完整排名结果
    'last_activity': None
}
```

### 2. 在 `check_agent_job_status()` 中存储排名结果

**文件**: `code_app/frontend/main.py`

**位置**: 约第6146行，获取结果后

```python
# 在获取结果后，存储到agent_context
results = await results_resp.json()

# 存储排名结果到agent_context
update_agent_context(
    stage='results_ready',
    data={
        'ranking_results': results,  # 完整排名结果
    }
)
```

### 3. 修改 `send_agent_message()` 函数

**文件**: `code_app/frontend/main.py`

**位置**: 约第5039行

需要检测环节2并传递 `ranking_results`：

```python
async def send_agent_message(hidden_input, messages_container, status_area, api_key_input):
    # ... 现有代码 ...
    
    state = get_client_state()
    agent_context = state['agent_context']
    ranking_results = agent_context.get('ranking_results')  # 获取排名结果
    
    # 检测是否为环节2（有排名结果）
    is_phase2 = ranking_results is not None and len(ranking_results.get('methods', [])) > 0
    
    # ... 准备消息 ...
    
    # 调用API时传递ranking_results
    payload = {
        'messages': messages, 
        'api_key': api_key,
        'ranking_results': ranking_results if is_phase2 else None  # 传递排名结果
    }
    
    async with session.post(f'{API_BASE_URL}/api/agent/chat', json=payload, timeout=30) as resp:
        # ... 处理响应 ...
```

### 4. 可选：实现自动总结功能

**文件**: `code_app/frontend/main.py`

**位置**: `check_agent_job_status()` 函数中，显示报告后

```python
# 显示报告后，自动触发Agent总结
if results:
    # 存储排名结果
    update_agent_context(
        stage='results_ready',
        data={'ranking_results': results}
    )
    
    # 自动触发总结（延迟2秒，等报告显示后）
    ui.timer(2.0, lambda: auto_summarize_results_frontend(results, messages_container, api_key_input), once=True)
```

**实现 `auto_summarize_results_frontend()` 函数**：

```python
async def auto_summarize_results_frontend(ranking_results, messages_container, api_key_input):
    """自动调用Agent总结排名结果"""
    try:
        summary_request = "Please provide a concise summary of the ranking results. Highlight the top 3-5 methods and any key findings."
        
        state = get_client_state()
        conversation_history = state['agent_conversation_history']
        
        # 准备消息
        messages = []
        messages.append({
            'role': 'user',
            'content': summary_request
        })
        
        # 调用API
        api_key = api_key_input.value.strip() if hasattr(api_key_input, 'value') else ""
        async with aiohttp.ClientSession() as session:
            payload = {
                'messages': messages, 
                'api_key': api_key,
                'ranking_results': ranking_results  # 传递排名结果
            }
            async with session.post(f'{API_BASE_URL}/api/agent/chat', json=payload, timeout=30) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    assistant_message = result.get('assistant_message', {})
                    content = assistant_message.get('content', '')
                    
                    if content:
                        # 高亮方法名（可选）
                        methods = ranking_results.get('methods', [])
                        # content = highlight_methods_in_response(content, methods)  # 如果需要高亮
                        
                        # 显示总结
                        add_message_to_chat(messages_container, 'assistant', 
                                          f'<span class="material-symbols-outlined">summarize</span> {content}')
    except Exception as e:
        logger.error(f"Auto summarize error: {e}")
```

---

## 测试建议

### 1. 后端测试

测试环节2检测逻辑：

```python
# 测试用例1：显式传递ranking_results
payload = ChatRequest(
    messages=[{"role": "user", "content": "What's the top method?"}],
    ranking_results={
        "methods": [
            {"name": "Method A", "rank": 1, "theta_hat": 0.5},
            {"name": "Method B", "rank": 2, "theta_hat": 0.3}
        ]
    }
)

# 测试用例2：从消息中提取
payload = ChatRequest(
    messages=[
        {"role": "tool", "name": "get_results", "content": json.dumps({"results": {...}})},
        {"role": "user", "content": "Tell me about the results"}
    ]
)
```

### 2. 前端测试

1. 上传文件并完成排名分析
2. 检查 `agent_context['ranking_results']` 是否正确存储
3. 在对话框中提问关于排名结果的问题
4. 验证Agent是否能够引用具体数据回答问题

---

## 文件清单

### 已创建/修改的文件

- ✅ `code_app/backend/phase2_agent.py` - 新建文件
- ✅ `code_app/backend/main.py` - 已修改

### 待修改的文件

- ⏳ `code_app/frontend/main.py` - 需要修改以下函数：
  - `get_client_state()` - 添加 `ranking_results` 字段
  - `check_agent_job_status()` - 存储排名结果
  - `send_agent_message()` - 传递 `ranking_results` 到API
  - `auto_summarize_results_frontend()` - 可选，实现自动总结

---

## 注意事项

1. **数据格式**: 确保排名结果的格式与后端期望一致
   ```python
   {
       "methods": [
           {"name": "...", "rank": 1, "theta_hat": 0.5, "ci_two_sided": [1, 3]}
       ],
       "params": {"bigbetter": True, "B": 2000, "seed": 42},
       "metadata": {"n_samples": 100, "runtime_sec": 1.5}
   }
   ```

2. **错误处理**: 如果环节2功能不可用（`PHASE2_AVAILABLE = False`），系统会回退到环节1处理

3. **性能**: 环节2不使用工具调用，响应速度应该更快

4. **上下文管理**: 注意控制消息历史长度，避免token超限

---

## 下一步

1. 完成前端代码修改
2. 测试环节2功能
3. 根据测试结果调整和优化
4. 可选：实现UI交互增强（在报告中添加"询问Agent"按钮）

