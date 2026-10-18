"""本机密码恢复：python -m youzi_v2.mobile.backend.reset_password。"""

import getpass
import sys

from .auth import AuthError, AuthStore
from .settings import load_settings


def main():
    if not sys.stdin.isatty():
        print("请在本机交互式终端运行，密码不接受命令行参数或管道输入。", file=sys.stderr)
        return 1
    settings = load_settings()
    settings.validate_files()
    store = AuthStore(settings.auth_database_path)
    if not store.initialized():
        print("尚未初始化个人账号，请先打开本机手机模块页面。", file=sys.stderr)
        return 1
    try:
        password = getpass.getpass("新密码（至少 12 个字符，输入不回显）：")
        if password != getpass.getpass("再次输入新密码："):
            raise AuthError(400, "两次密码不一致")
        store.reset_password_locally(password)
    except (AuthError, EOFError, KeyboardInterrupt) as exc:
        print(f"未完成重置：{exc}", file=sys.stderr)
        return 1
    print("密码已重置，原有登录会话全部失效；业务数据库未修改。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
