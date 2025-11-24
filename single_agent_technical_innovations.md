# Single LLM Agent 技术栈与创新方法总结

## 1. AgentMD: Clinical Language Agents

**核心创新**：大规模工具自动生成 + 智能选择框架

### 技术栈
- LLM: GPT-4/3.5
- 工具检索: MedCPT (dense retrieval)
- 工具执行: Python解释器
- 评估: RiskQA基准 + 真实患者数据

### 关键创新（避免"thin wrapper"）

1. **工具自动生成**：从PubMed摘要自动生成2000+临床计算工具，91.6%通过单元测试
2. **多阶段工具选择**：MedCPT检索top-10 → LLM选择，准确率82.3%
3. **三步工作流**：Tool Selection → Computation → Summarization
4. **真实世界评估**：698个急诊科患者记录，三个维度评估

**核心贡献**：工具自动生成 + 智能选择 + 系统化框架 + 全面评估

---

## 2. ChemCrow: Augmenting LLMs with Chemistry Tools

**核心创新**：ReAct框架 + 领域工具集成 + 物理实验室连接

### 技术栈
- 框架: ReAct (Reasoning + Acting)
- 工具: 18个化学工具
- 物理连接: 云连接的机器人合成平台

### 关键创新（避免"thin wrapper"）

1. **ReAct框架应用**：Thought-Action-Observation循环，将LLM从"hyperconfident but wrong"转变为"reasoning engine"
2. **领域深度集成**：18个专业工具，连接虚拟计算与物理实验室
3. **工具设计方法学**：可重用程序实现，可扩展架构
4. **多场景评估**：14个用例（合成、安全性控制等）

**核心贡献**：ReAct框架应用 + 领域集成 + 物理世界连接 + 工具设计方法学

---

## 3. TissueLab: ReAct Framework for Tissue Analysis

**核心创新**：ReAct框架在组织分析领域的应用

### 技术栈
- 框架: ReAct
- 领域: 组织分析

### 关键创新（避免"thin wrapper"）

1. **ReAct领域适配**：Thought-Action-Observation循环适配组织分析
2. **领域工具集成**：组织分析专业工具的系统化应用

**核心贡献**：ReAct框架的领域应用 + 领域工具集成

---

## 4. Clinical Calculations Agent: Planning Agent

**核心创新**：Planning Agent框架 + Scratchpad机制

### 技术栈
- 框架: Planning Agent
- 状态管理: LangChain
- LLM: GPT/LLaMa系列

### 关键创新（避免"thin wrapper"）

1. **Planning机制**：显式planning，scratchpad记录推理过程
2. **Robust错误处理**：100秒超时，最多5次失败后标记错误，最多4次重试
3. **结构化输出**：强制格式验证，LLM-based格式化提示
4. **多LLM支持**：统一框架接口

**核心贡献**：Planning机制 + Scratchpad可解释性 + Robust错误处理 + 结构化输出

---

## 总结：为什么不是"Thin Wrapper"？

### 共同特征

| 维度 | Thin Wrapper | 这些研究 |
|------|-------------|---------|
| **工具来源** | 调用现有工具 | 自动生成/深度集成 |
| **工作流** | 单次调用 | 系统化框架（ReAct/Planning） |
| **推理** | 无显式推理 | Thought-Action-Observation/Planning |
| **评估** | 简单demo | 基准测试+真实数据评估 |
| **领域** | 通用 | 领域深度集成 |
| **错误处理** | 基础 | Robust机制（重试/超时/验证） |

### 核心价值

1. **方法学创新**：新框架、机制、方法（ReAct、Planning、工具自动生成）
2. **领域贡献**：解决特定领域实际问题（临床、化学、组织分析）
3. **系统设计**：完整系统化设计（多阶段工作流、错误处理）
4. **实证验证**：全面评估验证（基准测试、真实数据、多场景）

**结论**：这些研究是**方法学创新 + 领域深度集成 + 系统化设计 + 全面评估**，而非简单的工具包装。
