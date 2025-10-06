#!/bin/bash

# 项目目录
PROJECT_DIR="/opt/compose-conf/tools"

# 进入项目目录
cd "$PROJECT_DIR" || { echo "Directory $PROJECT_DIR not found"; exit 1; }

# 清理未跟踪文件（谨慎操作）
echo "Cleaning untracked files..."
git clean -fd

# 拉取最新代码
echo "Pulling latest code from GitHub..."
git pull origin main

# 构建镜像并启动服务
echo "Building Docker Compose services and starting..."
docker-compose -f docker-compose.yml up -d --build

# 显示容器状态
echo "Current container status:"
docker-compose -f docker-compose.yml ps

echo "✅ Update complete!"
