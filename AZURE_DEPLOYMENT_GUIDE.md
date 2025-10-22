# Azure 部署指南

## 概述

您的应用采用前后端分离架构，并通过 Docker 容器化：
- **后端**：FastAPI + R（谱排序算法），运行在 Docker 容器中。
- **前端**：NiceGUI（Python Web UI），运行在另一个 Docker 容器中。

我们将在Azure上使用 **Azure App Service for Containers** 进行部署，需要两个独立的App Service实例。

## 部署步骤

### 前提条件
1.  [安装 Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
2.  [安装 Docker Desktop](https://www.docker.com/products/docker-desktop)

### 1. 创建 Azure Container Registry (ACR)
ACR 是一个私有的 Docker 镜像仓库，用于存储您的前端和后端镜像。

```bash
# 登录 Azure
az login

# 创建资源组 (如果已有，可跳过)
az group create --name YourResourceGroup --location "East US"

# 创建 ACR 实例 (名称需全局唯一)
az acr create --resource-group YourResourceGroup --name youruniqueregistryname --sku Basic --admin-enabled true
```

### 2. 构建并推送 Docker 镜像

```bash
# 登录到您的 ACR
az acr login --name youruniqueregistryname

# 构建后端镜像并标记
docker build -t youruniqueregistryname.azurecr.io/ranking-backend:latest -f Dockerfile.backend .

# 推送后端镜像
docker push youruniqueregistryname.azurecr.io/ranking-backend:latest

# 构建前端镜像并标记
docker build -t youruniqueregistryname.azurecr.io/ranking-frontend:latest -f Dockerfile.frontend .

# 推送前端镜像
docker push youruniqueregistryname.azurecr.io/ranking-frontend:latest
```
**注意**: 请将 `youruniqueregistryname` 替换为您自己的ACR名称。

### 3. 创建并配置后端 App Service

#### a. 创建 App Service:
- **发布**: 选择 "Docker 容器"
- **操作系统**: Linux
- **定价层**: 推荐 B1 ($13/月) 或更高，因为F1免费层可能因资源限制导致R脚本运行失败。

#### b. 配置容器设置:
在 "部署" > "部署中心" (或 "容器设置") 中：
- **映像源**: Azure Container Registry
- **注册表**: 选择您创建的 `youruniqueregistryname`
- **映像**: `ranking-backend`
- **标记**: `latest`
- **启动命令**: (保持为空，将使用Dockerfile中的CMD)

#### c. 配置环境变量:
在 "设置" > "配置" > "应用程序设置" 中添加：
- `PORT`: `8001` (App Service会自动映射外部80/443端口到此端口)
- `OPENAI_API_KEY`: `your_openai_api_key_here`
- `OPENAI_MODEL`: `gpt-3.5-turbo`

### 4. 创建并配置前端 App Service

#### a. 创建 App Service:
- **发布**: 选择 "Docker 容器"
- **操作系统**: Linux
- **定价层**: F1 免费层即可

#### b. 配置容器设置:
- **映像源**: Azure Container Registry
- **注册表**: `youruniqueregistryname`
- **映像**: `ranking-frontend`
- **标记**: `latest`
- **启动命令**: (保持为空)

#### c. 配置环境变量:
- `PORT`: `8080`
- `API_BASE_URL`: `https://your-backend-app-name.azurewebsites.net` (**重要**: 替换为您的后端App Service的URL)

### 5. 持续部署 (CI/CD) - 可选但推荐
您可以设置 GitHub Actions，在每次推送到 `main` 分支时自动构建并推送新的Docker镜像到ACR，并触发App Service重新拉取最新镜像。

## 重要注意事项

- **启动时间**: 首次部署时，App Service需要一些时间从ACR拉取镜像。后续部署会更快。
- **端口**: Dockerfile中暴露的端口 (`8001` 和 `8080`) 会被App Service自动映射。您只需要通过标准的 `80` (http) 和 `443` (https) 端口访问您的应用。
- **存储**: `docker-compose.yml` 中定义的卷在Azure App Service中不会直接生效。如果您需要持久化存储，应配置 "路径映射" 将 `/app/jobs` 等目录挂载到Azure文件存储。
- **启动脚本**: `startup.sh` 和 `frontend_startup.sh` 已不再需要，所有启动逻辑都已包含在Dockerfile中。
