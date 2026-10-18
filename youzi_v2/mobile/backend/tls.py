"""使用已有 OpenSSL 生成本地证书文件；不安装或信任证书、不修改防火墙。"""

import argparse
from datetime import datetime
import ipaddress
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import uuid

from .settings import REPO_ROOT

TLS_ROOT = REPO_ROOT / "youzi_v2/data/mobile/tls"


def private_ipv4(value: str) -> str:
    address = ipaddress.IPv4Address(value)
    # 只接受 RFC1918 网段，排除公网、回环、链路本地及通配地址。
    ranges = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
    if not any(address in ipaddress.ip_network(network) for network in ranges):
        raise ValueError("局域网地址须为 10.x、172.16–31.x 或 192.168.x 的具体 IPv4 地址")
    return str(address)


def find_openssl() -> str:
    executable = shutil.which("openssl")
    if executable:
        return executable
    git = shutil.which("git")
    if git:
        for parent in Path(git).resolve().parents:
            candidate = parent / "usr/bin/openssl.exe"
            if candidate.is_file():
                return str(candidate)
    raise ValueError("未找到 OpenSSL，请指定已安装的 Git/OpenSSL 的可执行文件路径")


def run_openssl(*args: str, executable: str | None = None) -> str:
    try:
        result = subprocess.run([executable or find_openssl(), *args], capture_output=True, text=True, timeout=45)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("OpenSSL 操作超时，请保留现有证书文件后重试") from exc
    if result.returncode:
        raise ValueError("OpenSSL 操作失败：" + result.stderr.strip()[-1200:])
    return result.stdout.strip()


def validate_tls(cert: Path, key: Path, ip: str | None = None) -> None:
    if not cert.is_file() or not key.is_file():
        raise ValueError("TLS 证书或私钥文件不存在")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(cert), str(key))
    run_openssl("x509", "-in", str(cert), "-checkend", "0", "-noout")
    if ip:
        run_openssl("x509", "-in", str(cert), "-checkip", ip, "-noout")


def prepare(ip: str, *, root: Path = TLS_ROOT, executable: str | None = None) -> tuple[Path, Path, Path]:
    ip = private_ipv4(ip)
    openssl = executable or find_openssl()
    authority = root / "authority"
    ca_key = authority / "root-key.pem"
    ca_cert = authority / "root.pem"
    ca_public = authority / "youzi-mobile-root.cer"
    if not authority.exists():
        authority.mkdir(parents=True)
        run_openssl("req", "-x509", "-newkey", "rsa:3072", "-nodes", "-sha256", "-days", "3650", "-subj", f"/CN=Youzi Mobile Local CA {uuid.uuid4().hex[:8]}", "-addext", "basicConstraints=critical,CA:TRUE,pathlen:0", "-addext", "keyUsage=critical,keyCertSign,cRLSign", "-addext", "subjectKeyIdentifier=hash", "-keyout", str(ca_key), "-out", str(ca_cert), executable=openssl)
        run_openssl("x509", "-in", str(ca_cert), "-outform", "DER", "-out", str(ca_public), executable=openssl)
    elif not all(path.is_file() for path in (ca_key, ca_cert, ca_public)):
        raise ValueError("现有 CA 目录不完整；保留原文件，不自动覆盖或重新生成根证书")
    run_openssl("verify", "-CAfile", str(ca_cert), str(ca_cert), executable=openssl)
    leaf = root / f"server-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
    leaf.mkdir(parents=True, exist_ok=False)
    cert, key, csr = leaf / "server.pem", leaf / "server-key.pem", leaf / "server.csr"
    extension = leaf / "extensions.cnf"
    extension.write_text(f"[server]\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost,IP:127.0.0.1,IP:{ip}\n", encoding="ascii")
    run_openssl("req", "-new", "-newkey", "rsa:2048", "-nodes", "-sha256", "-subj", "/CN=Youzi Mobile", "-keyout", str(key), "-out", str(csr), executable=openssl)
    run_openssl("x509", "-req", "-in", str(csr), "-CA", str(ca_cert), "-CAkey", str(ca_key), "-set_serial", "0x" + uuid.uuid4().hex, "-days", "180", "-sha256", "-extfile", str(extension), "-extensions", "server", "-out", str(cert), executable=openssl)
    run_openssl("verify", "-CAfile", str(ca_cert), "-verify_ip", ip, "-purpose", "sslserver", str(cert), executable=openssl)
    return cert, key, ca_public


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ip", required=True)
    parser.add_argument("--openssl")
    args = parser.parse_args()
    try:
        cert, key, public = prepare(args.ip, executable=args.openssl)
        print(f"证书文件已生成，未安装信任、未开放端口。\n服务证书：{cert}\n服务私钥（勿分享）：{key}\niPhone 仅安装此公开根证书：{public}")
        print(run_openssl("x509", "-in", str(public.parent / "root.pem"), "-noout", "-fingerprint", "-sha256", executable=args.openssl))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"证书准备失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
