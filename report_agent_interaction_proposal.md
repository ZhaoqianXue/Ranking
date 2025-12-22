# Report与Agent对话框交互实施建议

## 核心目标

实现排名报告（Report）与Agent对话框之间的双向交互，让用户能够：
1. 基于报告数据向Agent提问
2. Agent能够引用报告中的具体数据回答问题
3. 从报告中直接触发对Agent的询问
4. Agent自动总结排名结果

---

## 代码组织要求 ⚠️ 重要

**为了便于代码管理和维护，环节2（Phase 2）的所有代码应该保存在单独的Python文件中，而不是放在 `code_app/backend/main.py` 中。**

### 文件结构

```
code_app/backend/
├── main.py                    # 主应用文件（环节1代码保留在这里）
├── phase2_agent.py           # 环节2的Agent功能（新增）
└── ...
```

### 代码分离原则

1. **环节1（Phase 1）代码**：保留在 `main.py` 中
   - `_check_tool_dependencies_phase1()`
   - `_dispatch_tool_call_with_retry_phase1()`
   - `_validate_tool_result_phase1()`
   - `_check_phase1_complete()`
   - `_classify_error_phase1()`
   - Phase 1相关的工具函数

2. **环节2（Phase 2）代码**：新建 `phase2_agent.py`
   - `prepare_phase2_messages()` - 准备环节2的消息
   - `manage_phase2_context()` - 管理环节2的对话上下文
   - `auto_summarize_results()` - 自动总结排名结果
   - `highlight_methods_in_response()` - 高亮方法名
   - `PHASE2_SYSTEM_PROMPT_ADDON` - 环节2系统提示
   - `PHASE2_QUESTION_TYPES` - 问题类型指导
   - 其他环节2相关的辅助函数

3. **共享代码**：保留在 `main.py` 中
   - `agent_chat()` - 主聊天端点（需要调用环节2函数）
   - `SYSTEM_PROMPT` - 基础系统提示
   - 工具函数（`tool_*`）
   - API端点定义

### 导入方式

在 `main.py` 中导入环节2函数：

```python
# 在 main.py 顶部添加
from code_app.backend.phase2_agent import (
    prepare_phase2_messages,
    manage_phase2_context,
    PHASE2_SYSTEM_PROMPT_ADDON,
    PHASE2_QUESTION_TYPES
)
```

### 文件职责划分

| 文件 | 职责 | 包含内容 |
|------|------|---------|
| `main.py` | 主应用、环节1、API端点 | FastAPI应用、环节1优化、工具函数、API路由 |
| `phase2_agent.py` | 环节2功能 | 环节2消息准备、上下文管理、结果总结、系统提示 |

---

## 实施方案

### 方案1：数据连接 + 环节2功能实现（推荐）⭐⭐⭐⭐⭐

**核心思路**：将报告数据存储到Agent上下文中，实现环节2的所有功能，让Agent能够访问和理解报告数据。

#### 1.1 数据存储和连接

**修改位置**：`code_app/frontend/main.py`

**在 `check_agent_job_status()` 中存储报告数据**：

```python
# 在获取结果后，存储到agent_context
results = await results_resp.json()

# 存储排名结果到agent_context
update_agent_context(
    stage='results_ready',
    data={
        'ranking_results': results,  # 完整排名结果
        'top_methods': sorted(results.get('methods', []), key=lambda x: x.get('rank', 999))[:5],  # Top 5方法
        'summary_stats': {
            'total_methods': len(results.get('methods', [])),
            'n_samples': results.get('metadata', {}).get('n_samples'),
            'runtime_sec': results.get('metadata', {}).get('runtime_sec'),
            'params': results.get('params', {})
        }
    }
)
```

**修改 `agent_context` 结构**（在 `get_client_state()` 中）：

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

#### 1.2 实现环节2核心功能

**1.2.1 结果总结优化**

**新建文件**：`code_app/backend/phase2_agent.py`

**新增常量**：

```python
PHASE2_SYSTEM_PROMPT_ADDON = """
**For ranking results analysis (Phase 2), your role is:**

1. **Summarize Results**: When ranking results are available, provide a clear, concise summary:
   - Highlight top-ranked methods/models (top 3-5)
   - Mention key statistics (confidence intervals, ranking scores)
   - Note any significant findings or patterns
   - Reference the analysis parameters (B, seed, ranking direction)

2. **Answer Questions**: When users ask about the results:
   - Reference specific methods/models by name
   - Provide quantitative answers with exact values (rank, theta_hat, confidence intervals)
   - Explain statistical concepts in simple terms
   - If asked about interpretation, provide domain-appropriate insights
   - Compare methods when asked

3. **Context Awareness**: 
   - Remember the original dataset characteristics
   - Consider the ranking direction (higher/lower is better)
   - Reference the analysis parameters used (B, seed, etc.)
   - Use the ranking results data provided in the context

**Example Summary Format:**
"The spectral ranking analysis has completed. Based on the results:
- Top 3 ranked methods: [method names with ranks]
- Key finding: [significant observation]
- Statistical confidence: [confidence intervals if available]

You can ask me about specific methods, rankings, comparisons, or interpretations."
"""
```

**1.2.2 结果数据访问优化**

**新建文件**：`code_app/backend/phase2_agent.py`

**新增函数**：

```python
def prepare_phase2_messages(
    user_message: str,
    ranking_results: Dict[str, Any],
    conversation_history: List[Dict]
) -> List[Dict]:
    """Prepare Phase 2 messages with ranking results context"""
    messages = []
    
    if ranking_results:
        methods = ranking_results.get('methods', [])
        sorted_methods = sorted(methods, key=lambda x: x.get('rank', 999))
        top_5 = sorted_methods[:5]
        
        # Build results summary for context
        results_summary = {
            'total_methods': len(methods),
            'top_5': [
                {
                    'name': m.get('name'),
                    'rank': m.get('rank'),
                    'theta_hat': m.get('theta_hat'),
                    'ci': m.get('ci_two_sided', [None, None])
                }
                for m in top_5
            ],
            'params': ranking_results.get('params', {}),
            'metadata': ranking_results.get('metadata', {})
        }
        
        # Format context message
        context_lines = [
            f"**Current Ranking Results Context:**",
            f"- Total methods ranked: {results_summary['total_methods']}",
            f"- Top 5 methods:",
        ]
        for method in results_summary['top_5']:
            ci_str = f"[{method['ci'][0]}, {method['ci'][1]}]" if method['ci'][0] is not None else "N/A"
            context_lines.append(
                f"  {method['rank']}. {method['name']} (θ={method['theta_hat']:.4f}, CI: {ci_str})"
            )
        context_lines.append(f"- Analysis parameters: B={results_summary['params'].get('B', 'N/A')}, "
                           f"direction={'higher' if results_summary['params'].get('bigbetter') else 'lower'}")
        
        system_context = "\n".join(context_lines)
        
        # Add system message with Phase 2 guidance
        messages.append({
            'role': 'system',
            'content': PHASE2_SYSTEM_PROMPT_ADDON + "\n\n" + system_context
        })
    
    # Add recent conversation history (last 10 messages)
    recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
    for msg in recent_history:
        if msg.get('role') != 'system':  # Skip system messages
            messages.append({
                'role': msg.get('role'),
                'content': msg.get('content')
            })
    
    # Add current user message
    messages.append({
        'role': 'user',
        'content': user_message
    })
    
    return messages
```

**1.2.3 对话上下文管理**

**新建文件**：`code_app/backend/phase2_agent.py`

**新增函数**：

```python
def manage_phase2_context(
    conversation_history: List[Dict],
    ranking_results: Dict[str, Any],
    max_history: int = 10
) -> List[Dict]:
    """Manage Phase 2 conversation context"""
    # Keep recent conversation
    recent_history = conversation_history[-max_history:] if len(conversation_history) > max_history else conversation_history
    
    # Check if summary exists in history
    has_summary = any(
        'summary' in str(msg.get('content', '')).lower() or 
        'top.*ranked' in str(msg.get('content', '')).lower()
        for msg in recent_history
        if msg.get('role') == 'assistant'
    )
    
    # If no summary and results available, add summary as first assistant message
    if not has_summary and ranking_results:
        methods = ranking_results.get('methods', [])
        sorted_methods = sorted(methods, key=lambda x: x.get('rank', 999))
        top_3 = sorted_methods[:3]
        
        summary_lines = [
            f"Ranking analysis completed. {len(methods)} methods were ranked.",
            "Top 3 methods:"
        ]
        for method in top_3:
            summary_lines.append(f"  {method.get('rank')}. {method.get('name')} (θ={method.get('theta_hat', 0):.4f})")
        
        summary = "\n".join(summary_lines)
        recent_history.insert(0, {
            'role': 'assistant',
            'content': summary
        })
    
    return recent_history
```

**1.2.4 问题类型识别**

**新建文件**：`code_app/backend/phase2_agent.py`

**新增常量**：

```python
PHASE2_QUESTION_TYPES = """
**Question Types and Answer Strategies:**

1. **Ranking Questions** (e.g., "Which method is ranked highest?", "What's the top method?")
   - Provide direct answer with method name
   - Include ranking position and theta_hat score
   - Reference confidence intervals if available

2. **Comparison Questions** (e.g., "How does method A compare to method B?", "Compare X and Y")
   - Provide quantitative comparison (ranks, scores, confidence intervals)
   - Mention statistical significance if confidence intervals overlap
   - Explain practical implications

3. **Interpretation Questions** (e.g., "What does this ranking mean?", "Explain the results")
   - Explain in domain-appropriate terms
   - Reference the ranking direction (higher/lower is better)
   - Provide context about the spectral ranking methodology
   - Mention confidence and statistical reliability

4. **Technical Questions** (e.g., "How was the ranking calculated?", "What is theta_hat?")
   - Explain the spectral ranking methodology
   - Reference parameters used (B, seed)
   - Keep explanation accessible but accurate

5. **Specific Method Questions** (e.g., "Tell me about method X", "What's the rank of Y?")
   - Provide exact rank, theta_hat, and confidence interval
   - Compare with other methods if relevant
   - Explain what the values mean
"""
```

**集成到系统提示中**：

```python
PHASE2_SYSTEM_PROMPT_ADDON = """
... (之前的内容) ...

{PHASE2_QUESTION_TYPES}
"""
```

#### 1.3 修改 `send_agent_message()` 函数

**检测环节2并应用优化**：

```python
async def send_agent_message(hidden_input, messages_container, status_area, api_key_input):
    # ... 现有代码 ...
    
    state = get_client_state()
    agent_context = state['agent_context']
    ranking_results = agent_context.get('ranking_results')  # 获取排名结果
    
    # 检测是否为环节2（有排名结果）
    is_phase2 = ranking_results is not None and len(ranking_results.get('methods', [])) > 0
    
    if is_phase2:
        # 使用环节2的消息准备函数
        conversation_history = state['agent_conversation_history']
        messages = prepare_phase2_messages(message, ranking_results, conversation_history)
        
        # 管理上下文
        managed_history = manage_phase2_context(conversation_history, ranking_results)
        # 更新conversation_history（如果需要）
    else:
        # 使用现有的消息准备逻辑
        messages = []
        # ... 现有代码 ...
    
    # 调用API
    # ... 现有代码 ...
```

---

### 方案2：UI交互增强（补充方案）⭐⭐⭐⭐

**核心思路**：在报告UI中添加交互元素，让用户可以直接从报告中触发Agent询问。

#### 2.1 在报告中添加"询问Agent"按钮

**修改位置**：`code_app/frontend/main.py` 的 `show_report()` 函数

**在排名表格的每一行添加交互按钮**：

```python
# 在表格行中添加"Ask Agent"按钮
for method in sorted_methods:
    method_name = method.get('name')
    rank = method.get('rank')
    
    # 添加可点击的"询问Agent"按钮
    ask_button_html = f'''
    <button onclick="askAgentAboutMethod('{method_name}')" 
            style="background: #011f5b; color: white; border: none; 
                   padding: 0.25rem 0.5rem; border-radius: 4px; 
                   cursor: pointer; font-size: 0.7rem;">
        Ask Agent
    </button>
    '''
    
    # 在表格单元格中添加按钮
```

**添加JavaScript函数**：

```python
ui.run_javascript(f'''
function askAgentAboutMethod(methodName) {{
    // 找到消息输入框并填入问题
    const input = document.getElementById("message-input");
    if (input) {{
        input.value = `Tell me about {{methodName}}. What is its rank and how does it compare to others?`;
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        
        // 触发发送（如果需要）
        // 或者显示提示让用户点击发送按钮
    }}
}}
''')
```

#### 2.2 在报告顶部添加"总结"按钮

**添加总结按钮**：

```python
# 在报告顶部添加
with ui.element('div').style('margin-bottom: 1rem;'):
    ui.button('📊 Ask Agent to Summarize Results', 
              on_click=lambda: trigger_agent_summary(ranking_results))
```

**实现总结函数**：

```python
def trigger_agent_summary(ranking_results):
    """触发Agent自动总结排名结果"""
    # 准备总结请求消息
    summary_request = "Please summarize the ranking results. Highlight the top methods and key findings."
    
    # 调用send_agent_message（需要传入必要的参数）
    # 或者直接调用API
```

#### 2.3 高亮显示Agent引用的方法

**在Agent回答中检测方法名并高亮**：

```python
def highlight_methods_in_response(content: str, methods: List[Dict]) -> str:
    """在Agent回答中高亮显示方法名"""
    method_names = [m.get('name') for m in methods]
    
    for method_name in method_names:
        # 使用正则表达式替换方法名为高亮版本
        pattern = re.compile(re.escape(method_name), re.IGNORECASE)
        highlighted = f'<span style="background: #fff4e1; padding: 0.1rem 0.3rem; border-radius: 3px; font-weight: 600;">{method_name}</span>'
        content = pattern.sub(highlighted, content)
    
    return content
```

---

### 方案3：自动结果总结（推荐优先实现）⭐⭐⭐⭐⭐

**核心思路**：当排名结果完成时，自动调用Agent生成总结。

#### 3.1 在 `check_agent_job_status()` 中添加自动总结

**修改位置**：`code_app/frontend/main.py:6126`（前端调用）

**实现位置**：`code_app/backend/phase2_agent.py`（后端函数）

**前端调用**：

```python
async def check_agent_job_status(messages_container, job_id):
    # ... 现有代码 ...
    
    if status == 'succeeded':
        results = await results_resp.json()
        
        # 存储排名结果
        update_agent_context(
            stage='results_ready',
            data={'ranking_results': results}
        )
        
        # 显示报告
        ui.timer(1.0, lambda: show_main_report(results), once=True)
        
        # 自动触发Agent总结（延迟2秒，等报告显示后）
        ui.timer(2.0, lambda: auto_summarize_results(results, messages_container, api_key_input), once=True)
```

**后端实现**（`code_app/backend/phase2_agent.py`）：

```python
async def auto_summarize_results(ranking_results, conversation_history, api_key: str):
    """Auto-generate summary of ranking results using Agent"""
    # 后端实现，返回总结文本
    # 前端调用此函数并显示结果
```

**前端调用函数**（`code_app/frontend/main.py`）：

```python
async def auto_summarize_results_frontend(ranking_results, messages_container, api_key_input):
    """自动调用Agent总结排名结果"""
    try:
        # 准备总结请求
        summary_request = "Please provide a concise summary of the ranking results. Highlight the top 3-5 methods and any key findings."
        
        # 使用环节2的消息准备
        state = get_client_state()
        conversation_history = state['agent_conversation_history']
        messages = prepare_phase2_messages(summary_request, ranking_results, conversation_history)
        
        # 调用API
        api_key = api_key_input.value.strip() if hasattr(api_key_input, 'value') else ""
        async with aiohttp.ClientSession() as session:
            payload = {'messages': messages, 'api_key': api_key}
            async with session.post(f'{API_BASE_URL}/api/agent/chat', json=payload, timeout=30) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    assistant_message = result.get('assistant_message', {})
                    content = assistant_message.get('content', '')
                    
                    if content:
                        # 高亮方法名
                        methods = ranking_results.get('methods', [])
                        content = highlight_methods_in_response(content, methods)
                        
                        # 显示总结
                        add_message_to_chat(messages_container, 'assistant', 
                                          f'<span class="material-symbols-outlined">summarize</span> {content}')
    except Exception as e:
        logger.error(f"Auto summarize error: {e}")
```

---

## 实施优先级

### 阶段1：核心数据连接（必须）⭐⭐⭐⭐⭐
1. ✅ 修改 `agent_context` 结构，添加 `ranking_results` 字段（前端）
2. ✅ 在 `check_agent_job_status()` 中存储排名结果（前端）
3. ✅ **新建 `code_app/backend/phase2_agent.py` 文件**
4. ✅ 实现 `prepare_phase2_messages()` 函数（后端，phase2_agent.py）
5. ✅ 修改 `send_agent_message()` 检测环节2并应用优化（前端）

### 阶段2：环节2功能实现（高优先级）⭐⭐⭐⭐
1. ✅ 实现 `PHASE2_SYSTEM_PROMPT_ADDON` 常量（后端，phase2_agent.py）
2. ✅ 实现 `manage_phase2_context()` 函数（后端，phase2_agent.py）
3. ✅ 实现 `PHASE2_QUESTION_TYPES` 常量（后端，phase2_agent.py）
4. ✅ 在 `main.py` 中导入环节2函数
5. ✅ 集成到 `send_agent_message()` 中（前端调用后端API）

### 阶段3：自动总结（高优先级）⭐⭐⭐⭐⭐
1. ✅ 实现 `auto_summarize_results()` 函数（后端，phase2_agent.py）
2. ✅ 实现 `highlight_methods_in_response()` 函数（后端，phase2_agent.py）
3. ✅ 在 `check_agent_job_status()` 中调用自动总结（前端）
4. ✅ 添加后端API端点用于自动总结（可选，或直接在前端调用agent_chat）

### 阶段4：UI交互增强（可选）⭐⭐⭐
1. ⏳ 在报告中添加"询问Agent"按钮
2. ⏳ 添加JavaScript交互函数
3. ⏳ 实现方法名高亮显示

---

## 预期效果

### 用户体验提升
1. **无缝交互**：报告和对话框无缝连接，用户可以直接询问报告内容
2. **智能总结**：报告显示后自动生成总结，用户快速了解关键信息
3. **精确回答**：Agent能够引用具体的排名、分数、置信区间等数据
4. **上下文理解**：Agent理解完整的排名结果上下文，回答更准确

### 功能增强
1. **数据访问**：Agent能够访问完整的排名结果数据
2. **问题理解**：Agent能够识别不同类型的问题并采用合适的回答策略
3. **交互便利**：用户可以从报告中直接触发询问

---

## 实施建议

**建议优先实施阶段1和阶段2**，这两个阶段实现了核心的数据连接和环节2功能，能够让Agent基于报告数据回答问题。

**阶段3（自动总结）**也非常重要，能够显著提升用户体验。

**阶段4（UI交互增强）**可以作为后续优化，提升交互便利性。

---

## 注意事项

1. **代码组织**：⚠️ **重要** - 环节2的所有代码必须保存在 `code_app/backend/phase2_agent.py` 中，不要放在 `main.py` 中
2. **导入管理**：在 `main.py` 中正确导入环节2函数，确保模块路径正确
3. **数据格式**：确保排名结果的数据格式一致，Agent能够正确解析
4. **上下文管理**：注意控制消息历史长度，避免token超限
5. **错误处理**：添加适当的错误处理，确保在数据缺失时也能正常工作
6. **性能优化**：自动总结可以异步执行，避免阻塞UI
7. **前后端分离**：环节2的核心逻辑在后端，前端主要负责调用和UI展示

---

## 文件创建清单

### 需要新建的文件
- [ ] `code_app/backend/phase2_agent.py` - 环节2的所有功能实现

### 需要修改的文件
- [ ] `code_app/backend/main.py` - 添加环节2函数的导入
- [ ] `code_app/frontend/main.py` - 调用环节2功能，存储排名结果到context

