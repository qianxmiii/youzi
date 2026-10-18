# iPhone 局域网 HTTPS 验收

个人账号登录已由本人确认通过。经本人明确授权，当前家庭网络已设为 Private，并添加 `YouziMobile-HTTPS-3443` 入站规则：仅限 `192.168.1.6`、TCP 3443、Private 网络、LocalSubnet 来源及实际 Python 可执行文件。HTTPS 服务已启动并通过本机证书校验；iPhone 证书安装、完全信任及手机连通性仍待本人验收。未安装 Windows 根证书。

当前地址：`https://192.168.1.6:3443/`。当前服务证书位于 `youzi_v2/data/mobile/tls/server-20261018-152522-527d7959/`。此地址与规则仅适用当前家庭网络，换 Wi-Fi 后须重新核对，不自动放宽规则。

## 证书与网络地址

在仓库根目录，用当前电脑获准使用的 Wi-Fi IPv4 地址生成服务证书：

```powershell
python -m youzi_v2.mobile.backend.tls --ip 192.168.1.6
```

此地址只是首次检查时的地址。切换家庭/公司 Wi-Fi 后先检查 `ipconfig`，不要照抄旧 IP。工具只接受具体 RFC1918 IPv4 地址，不接受 `0.0.0.0`、公网或回环地址作为局域网地址。

证书文件在 `youzi_v2/data/mobile/tls/`，不在公开静态目录，全部被 Git 忽略。工具复用现有 CA，每次签发到一个新服务证书目录；不覆盖旧证书，不自动安装信任或删除文件。叶证书有效期 180 天，换 IP 或到期时重新签发。使用同一个 CA 时，通常不必重新安装根证书。

- `authority/youzi-mobile-root.cer`：公开根证书，只将这一份传到 iPhone。
- `authority/root.pem`：同一公开根证书的 PEM 格式，供桌面验证使用。
- `authority/root-key.pem`：CA 私钥，绝不可传到手机、上传或分享。
- `server-*/server-key.pem`：服务私钥，绝不可分享。

生成工具输出根证书 SHA-256 指纹，安装前核对文件来源及指纹。信任根证书后，该 CA 签发的证书可以被设备信任；因此仅安装自己的公开根证书，保护 CA 私钥。

## iPhone 手动安装

通过你信任的文件传输方式，将公开的 `youzi-mobile-root.cer` 传到 iPhone 并打开。

1. 按系统提示，到“设置”中的“已下载描述文件”，或“通用 → VPN 与设备管理”，安装该证书。
2. 到“设置 → 通用 → 关于本机 → 证书信任设置”，对名称以 `Youzi Mobile Local CA` 开头的对应根证书启用完全信任。
3. 手动安装不会自动获得 SSL 信任，需完成上一步。参见 [Apple 官方说明](https://support.apple.com/zh-cn/102390)。

不要通过“忽略证书警告”来代替正确安装。受管理的设备若不允许安装或公司网络禁止设备互访，不绕过管理策略，先在获准的家庭网络验收。

## 启动检查

将实际输出的服务证书和服务私钥完整路径带入命令。推荐手机 HTTPS 使用端口 3443，原本机 HTTP 3002 和原电脑端保持不变。

```powershell
.\youzi_v2\mobile\scripts\start-mobile.cmd --port 3443 --lan-ip 192.168.1.6 --tls-cert "服务证书完整路径" --tls-key "服务私钥完整路径" --check
```

检查通过仅代表本机配置、账号、证书、地址与端口条件满足，不代表手机信任或防火墙已配置。

获准开放局域网后，去掉 `--check` 启动；监听仅绑定指定 IP，不是所有网卡。业务入口为 `https://该IP:3443/`。账号必须提前初始化；缺少 TLS、地址不是本机地址、证书与 IP 不匹配或已过期时拒绝启动。不信任代理传来的 `X-Forwarded-*` 头。

## 防火墙边界

当前防火墙规则已通过 Windows 管理员提升配置。规则只允许手机 HTTPS 端口 3443、当前本地地址、可信的 Private 网络、LocalSubnet 来源和 Python 程序。不关闭整个防火墙，不配置路由器端口转发，不开放旧电脑端 API 端口。公司网络如果不是获准的可信网络，不擅自改变网络类别。

未来需要停用该规则时，在获准的管理员 PowerShell 执行 `Disable-NetFirewallRule -Name 'YouziMobile-HTTPS-3443'`；本轮未执行停用或删除操作。

## 真机验收

- [ ] iPhone 与电脑连接同一个获准的 Wi-Fi。
- [ ] Safari 打开 HTTPS 地址，没有证书警告。
- [ ] 登录和退出正常；手机未登录不能访问受保护接口。
- [ ] 普通 HTTP 不能在该 HTTPS 端口取得业务页面。
- [ ] 配置、认证库、业务库、日志及私钥不可通过 URL 下载。
- [ ] 切换 Wi-Fi 后检查 IP，并按需重新签发服务证书。
- [ ] 把网页添加到 iPhone 主屏幕后，再验证会话过期和退出行为。

HTTPS 本机链路已由显式信任该 CA 的测试客户端验证；iPhone 信任尚需本人完成。只用手机访问不要求先在 Windows 系统中安装根证书。
