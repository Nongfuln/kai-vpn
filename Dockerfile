FROM alpine:3.20

# 安装依赖 + 下载 xray-core
RUN apk add --no-cache ca-certificates curl python3 unzip && \
    curl -fsSL -o /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip && \
    unzip -o /tmp/xray.zip xray -d /usr/local/bin && \
    chmod +x /usr/local/bin/xray && \
    rm /tmp/xray.zip && \
    apk del curl unzip

WORKDIR /app
COPY gen_config.py frontdoor.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

CMD ["/app/entrypoint.sh"]
