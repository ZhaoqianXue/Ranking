# Azure 部署指南

## 概述

您的应用采用前后端分离架构：
- **后端**：FastAPI + R（谱排序算法）
- **前端**：NiceGUI（Python Web UI）

需要在Azure上创建两个App Service实例。

## 部署步骤

### 1. 创建后端 App Service

#### 配置基本信息：
- **运行时栈**：Python 3.10
- **操作系统**：Linux
- **定价层**：F1 Free Tier 或 B1 ($13/月)

#### 应用设置：
在 "Configuration" > "Application settings" 中添加：

```
PYTHONPATH = /home/site/wwwroot
PORT = 8000
OPENAI_API_KEY = your_openai_api_key_here
OPENAI_MODEL = gpt-3.5-turbo
```

#### 启动命令：
```
./startup.sh
```

#### 部署方式：
推荐使用 GitHub Actions：
1. 转到 "Deployment Center" > "GitHub"
2. 连接您的仓库
3. 选择主分支，启用持续部署

### 2. 创建前端 App Service

#### 配置基本信息：
- **运行时栈**：Python 3.10
- **操作系统**：Linux
- **定价层**：F1 Free Tier

#### 应用设置：
```
PYTHONPATH = /home/site/wwwroot
API_BASE_URL = https://your-backend-app-name.azurewebsites.net
```

#### 启动命令：
```
python code_app/frontend/main.py
```

#### 部署方式：
同样使用 GitHub Actions 部署。

### 3. 配置自定义域名（可选）

如果需要自定义域名：
1. 在每个 App Service 的 "Custom domains" 中添加域名
2. 更新DNS记录指向Azure提供的IP
3. 启用HTTPS（Azure提供免费证书）

## 架构说明

```
/ (前端: https://frontend-app.azurewebsites.net)
├── 主页面和仪表板 (NiceGUI)
└── 调用后端API

/backend (后端: https://backend-app.azurewebsites.net)
├── /api/ranking/* - 排序API
├── /api/agent/* - Agent API
└── R谱排序算法执行
```

## 重要注意事项

### R环境配置
- Azure App Service 默认不包含R
- `startup.sh` 脚本会自动安装R和必要包
- 首次部署可能需要5-10分钟安装依赖

### 免费额度限制
- F1层：每月60 CPU分钟
- 如果R计算量大，可能需要升级付费层级

### 存储考虑
- 当前使用本地文件系统
- 生产环境建议使用Azure Blob Storage
- App Service重启时本地文件会丢失

### 安全配置
- 不要在代码中硬编码API密钥
- 使用环境变量存储敏感信息
- 考虑使用Azure Key Vault

## 测试部署

1. 部署完成后，访问前端URL
2. 检查前后端通信是否正常
3. 测试文件上传和排序功能
4. 查看应用日志排查问题

## 故障排除

### 常见问题：
1. **R安装失败**：检查 `startup.sh` 日志
2. **依赖安装失败**：确认 `requirements.txt` 完整
3. **API调用失败**：检查 `API_BASE_URL` 配置
4. **端口问题**：确保使用 `$PORT` 环境变量

### 查看日志：
- "App Service logs" > "Application logging" > "File System"
- "Log stream" 查看实时日志

## 后续优化

1. **性能监控**：设置Application Insights
2. **备份策略**：配置自动备份
3. **CI/CD**：完善GitHub Actions工作流
4. **缓存**：添加Redis缓存层
5. **数据库**：迁移到Azure Database
