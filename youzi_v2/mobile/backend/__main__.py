"""python -m youzi_v2.mobile.backend [--check] [--port 3002]"""

import argparse
from dataclasses import replace
import socket
import sys

from .settings import load_settings, resolve_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="检查配置及端口，不启动服务、不读取业务记录")
    parser.add_argument("--port", type=int)
    parser.add_argument("--lan-ip", help="明确指定一个获准使用的局域网 IPv4 地址；须同时配置 HTTPS")
    parser.add_argument("--tls-cert")
    parser.add_argument("--tls-key")
    args = parser.parse_args(argv)
    try:
        settings = load_settings(port=args.port)
        settings = replace(settings, lan_ip=args.lan_ip, tls_cert=resolve_path(args.tls_cert) if args.tls_cert else None, tls_key=resolve_path(args.tls_key) if args.tls_key else None)
        settings.validate_files()
        if settings.lan_ip:
            # 确认当前电脑确实拥有该地址，避免换 Wi-Fi 后检查通过却无法启动。
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as address_probe:
                address_probe.bind((settings.lan_ip, 0))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            if probe.connect_ex((settings.host, settings.port)) == 0:
                raise ValueError(f"端口 {settings.port} 已被占用；请先确认服务是否已启动，或指定其他端口")
        from .app import create_app
        import uvicorn

        scheme = "https" if settings.tls_cert else "http"
        mode = "指定局域网地址模式" if settings.lan_ip else "本机模式"
        print(f"手机模块：{mode}\n地址：{scheme}://{settings.host}:{settings.port}")
        print(f"数据库路径：{settings.database_path}\n配置路径：{settings.config_path}")
        print("业务接口需个人登录；查单只读，可更新异常跟进通知状态，不启动同步任务。", flush=True)
        if args.check:
            print("检查通过；未启动服务，未创建或迁移数据库。")
            return 0
        uvicorn.run(create_app(settings), host=settings.host, port=settings.port, workers=1, reload=False, proxy_headers=False, ssl_certfile=str(settings.tls_cert) if settings.tls_cert else None, ssl_keyfile=str(settings.tls_key) if settings.tls_key else None)
        return 0
    except (ValueError, OSError, ImportError) as exc:
        print(f"手机模块启动失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
