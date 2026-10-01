#!/usr/bin/env python3
"""根据环境变量生成 xray 配置: VLESS + WS, 监听 127.0.0.1:10001."""
import json
import os

UUID = os.environ["UUID"]
WS_PATH = os.environ["WS_PATH"]

config = {
    "log": {"loglevel": "warning"},
    "inbounds": [
        {
            "port": 10001,
            "listen": "127.0.0.1",
            "protocol": "vless",
            "settings": {
                "clients": [{"id": UUID}],
                "decryption": "none",
            },
            "streamSettings": {
                "network": "ws",
                "wsSettings": {"path": WS_PATH},
            },
        }
    ],
    "outbounds": [{"protocol": "freedom", "tag": "direct"}],
}

os.makedirs("/etc/xray", exist_ok=True)
with open("/etc/xray/config.json", "w") as f:
    json.dump(config, f)
print("xray config written", flush=True)
