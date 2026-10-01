#!/bin/sh
# 容器启动入口: 生成 xray 配置 -> 启动 xray -> 启动前门服务
set -e

: "${PORT:=10000}"
: "${UUID:?Render 环境变量缺少 UUID}"
: "${WS_PATH:?Render 环境变量缺少 WS_PATH}"
: "${SUB_PATH:=/sub}"
export UUID WS_PATH SUB_PATH PORT

python3 /app/gen_config.py
/usr/local/bin/xray run -c /etc/xray/config.json &
exec python3 /app/frontdoor.py
