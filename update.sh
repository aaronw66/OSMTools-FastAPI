#!/bin/bash

# 项目目录
PROJECT_DIR="/opt/compose-conf/tools"

cd "$PROJECT_DIR" || { echo "Directory $PROJECT_DIR not found"; exit 1; }

# 还原 requirements.txt
echo "Resetting requirements.txt to remote version..."
git checkout -- requirements.txt

# 清理未跟踪文件（logs 等）
echo "Cleaning untracked files..."
git clean -fd

# 拉取最新代码
echo "Pulling latest code from GitHub..."
git pull origin main

# 构建 Docker Compose 并启动
echo "Building Docker Compose services and starting..."
docker-compose -f docker-compose.yml up -d --build

# 查看容器状态
echo "Current container status:"
docker-compose -f docker-compose.yml ps

echo "✅ Update complete!"
