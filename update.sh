#!/bin/bash

# 项目目录
PROJECT_DIR="/opt/compose-conf/tools"
CONTAINER_NAME="tools-osmtools-1"  # 根据 docker-compose ps 输出确认

cd "$PROJECT_DIR" || { echo "Directory $PROJECT_DIR not found"; exit 1; }

# 还原关键跟踪文件
echo "Resetting requirements.txt to remote version..."
git checkout -- requirements.txt update.sh

# 拉取最新代码
echo "Pulling latest code from GitHub..."
git fetch origin
git reset --hard origin/main

# 保留 type/ 和 logs/ 目录中的文件，不删除
echo "Cleaning other untracked files except type/ and logs/..."
git clean -fd -e type -e logs

# 构建 Docker Compose 并启动
echo "Building Docker Compose services and starting..."
docker-compose -f docker-compose.yml up -d --build

# 查看容器状态
echo "Current container status:"
docker-compose -f docker-compose.yml ps

# 监控容器日志，直到出现 Application startup complete
echo "Waiting for service to fully start..."
docker logs -f "$CONTAINER_NAME" | while read -r line; do
    echo "$line"
    if echo "$line" | grep -q "INFO:     Application startup complete."; then
        echo "✅ Service startup complete, update finished!"
        pkill -P $$ docker   # 停止 docker logs 进程
        break
    fi
done
