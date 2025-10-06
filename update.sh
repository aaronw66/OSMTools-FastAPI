#!/bin/bash
cd /opt/compose-conf/tools || exit 1

# 丢弃本地 update.sh 和 requirements.txt 修改
git checkout -- update.sh requirements.txt

# 清理未跟踪文件（logs 等）
git clean -fd

# 拉取最新代码
git pull origin main

# Build Docker Compose
docker-compose -f docker-compose.yml up -d --build

docker-compose -f docker-compose.yml ps
