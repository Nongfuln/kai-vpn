#!/usr/bin/env python3
"""前门服务(监听 $PORT):
- GET /          -> 健康检查 200 (平台用它判断服务存活)
- GET $SUB_PATH  -> 订阅接口, 返回 base64 的 vless 节点
- WS 握手到 $WS_PATH -> 透传给本地 xray (127.0.0.1:10001)
"""
import base64
import os
import socket
import threading
from urllib.parse import quote

PORT = int(os.environ.get("PORT", "10000"))
UUID = os.environ["UUID"]
WS_PATH = os.environ["WS_PATH"]
SUB_PATH = os.environ.get("SUB_PATH", "/sub")
HOST = (
    os.environ.get("PUBLIC_HOST")
    or os.environ.get("KOYEB_PUBLIC_DOMAIN")
    or os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    or "localhost"
)
XRAY_HOST, XRAY_PORT = "127.0.0.1", 10001


def vless_link(host):
    host = host.split(":")[0]  # 去掉 Host 头里可能带的端口
    return (
        f"vless://{UUID}@{host}:443?encryption=none&security=tls"
        f"&sni={host}&type=ws&host={host}&path={quote(WS_PATH, safe='')}"
        "#Kai"
    )


def subscription(host):
    return base64.b64encode(vless_link(host).encode()).decode()


def send_simple(conn, code, body, ctype="text/plain; charset=utf-8"):
    head = (
        f"HTTP/1.1 {code}\r\nContent-Type: {ctype}\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    ).encode()
    conn.sendall(head + body)


def relay(a, b):
    try:
        while True:
            chunk = a.recv(65536)
            if not chunk:
                break
            b.sendall(chunk)
    except OSError:
        pass


def close_quiet(s):
    try:
        s.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        s.close()
    except OSError:
        pass


def handle_ws(conn, initial):
    try:
        upstream = socket.create_connection((XRAY_HOST, XRAY_PORT), timeout=10)
    except OSError:
        send_simple(conn, "502 Bad Gateway", b"bad gateway")
        return
    try:
        # 把原始升级请求原样转发给 xray, 由 xray 完成 WS 握手
        upstream.sendall(initial)
        t1 = threading.Thread(target=relay, args=(conn, upstream), daemon=True)
        t2 = threading.Thread(target=relay, args=(upstream, conn), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    finally:
        close_quiet(conn)
        close_quiet(upstream)


def handle_client(conn):
    ws_handled = False
    try:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                return
            data += chunk
            if len(data) > 65536:
                return
        head = data.split(b"\r\n\r\n", 1)[0].decode("iso-8859-1")
        lines = head.split("\r\n")
        try:
            method, target, _ = lines[0].split(" ", 2)
        except ValueError:
            return
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        path = target.split("?", 1)[0]

        if path == "/" and method in ("GET", "HEAD"):
            body = b"Kai VPN running" if method == "GET" else b""
            send_simple(conn, "200 OK", body)
        elif path == SUB_PATH and method == "GET":
            # 用请求 Host 头生成订阅链接, 换平台/换域名都不用改代码
            send_simple(conn, "200 OK", subscription(headers.get("host", HOST)).encode())
        elif path == WS_PATH and headers.get("upgrade", "").lower() == "websocket":
            ws_handled = True
            handle_ws(conn, data)
        else:
            send_simple(conn, "404 Not Found", b"not found")
    except OSError:
        pass
    finally:
        if not ws_handled:
            close_quiet(conn)


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(128)
    print(f"frontdoor listening on {PORT}, host={HOST}", flush=True)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle_client, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
