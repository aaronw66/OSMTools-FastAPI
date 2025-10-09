#!/bin/bash

# 项目目录
PROJECT_DIR="/opt/compose-conf/tools"
CONTAINER_NAME="tools-osmtools-1"

cd "$PROJECT_DIR" || { echo "❌ Directory $PROJECT_DIR not found"; exit 1; }

# 还原关键跟踪文件
echo "🔄 Resetting requirements.txt and update.sh to remote version..."
git checkout -- requirements.txt update.sh

# 拉取最新代码
echo "📥 Pulling latest code from GitHub..."
git fetch origin
git reset --hard origin/main

# 保留 type/ 和 logs/ 目录中的文件，不删除
echo "🧹 Cleaning other untracked files except type/ and logs/..."
git clean -fd -e type -e logs

# 构建 Docker Compose 并启动
echo "🔨 Building Docker Compose services and starting..."
docker-compose -f docker-compose.yml up -d --build

# 查看容器状态
echo ""
echo "📊 Current container status:"
docker-compose -f docker-compose.yml ps

# 等待启动完成 - 简单轮询方式
echo ""
echo "⏳ Waiting for service to start..."

TIMEOUT=120
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    if docker logs "$CONTAINER_NAME" 2>&1 | grep -q "Application startup complete"; then
        echo ""
        echo "✅ Service startup complete! (took ${ELAPSED}s)"
        echo ""
        exit 0
    fi
    echo -n "."
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

echo ""
echo "⚠️  Timeout after ${TIMEOUT} seconds"
echo "Check logs with: docker logs -f $CONTAINER_NAME"
exit 1