#!/bin/bash

# 项目目录
PROJECT_DIR="/opt/compose-conf/tools"

cd "$PROJECT_DIR" || { echo "Directory $PROJECT_DIR not found"; exit 1; }

# 还原关键跟踪文件
echo "Resetting requirements.txt to remote version..."
git checkout -- requirements.txt update.sh

# 拉取最新代码
echo "Pulling latest code from GitHub..."
git fetch origin
git reset --hard origin/main

# 保留 type/ 和 logs/ 目录中的文件，不删除
# 所以不再使用 git clean -fd
# 可以清理其他未跟踪临时文件，如果需要的话，用 -e 排除 type/ logs/
echo "Cleaning other untracked files except type/ and logs/..."
git clean -fd -e type -e logs

# 构建 Docker Compose 并启动
echo "Building Docker Compose services and starting..."
docker-compose -f docker-compose.yml up -d --build

# 查看容器状态
echo "Current container status:"
docker-compose -f docker-compose.yml ps

echo "✅ Update complete!"
