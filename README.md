# 远程开关机

手机不直接连电脑。手机只访问 NAS 上的中转，中转负责唤醒，再让电脑上的代理关机。

三部分是分开的仓库：`powerctl-agent`（本机代理）、`powerctl-relay`（NAS 中转）、`powerctl-android`（手机）。

## 架构

- 手机应用把中转地址和手机密码保存在本机，请求 `GET /status` 和 `POST /power`。
- 中转监听 `8787`。开机时向机器网卡发网络唤醒；关机时访问该机器代理的 `POST /shutdown`。
- 代理监听 `8790`，只应在局域网里。`GET /health` 报告系统，`POST /shutdown` 需要代理密钥。
- 同一块网卡只有一个 MAC。唤醒不能选择操作系统。

## 密钥放在哪里

不要把密码写进仓库。

- 手机密码的原文在中转的 `data/phone-password.txt`。NAS 上同一份在 `I:\powerctl\data\phone-password.txt`。
- 中转配置里的 `password_hash` 是这份密码的哈希。本机文件是 `relay/data/config.json`，NAS 上是 `I:\powerctl\data\config.json`（DSM 路径 `/volume2/SSD Volume/powerctl/data/config.json`）。
- 代理密钥在代理的 `config.json` 里，字段是 `secret`。中转配置里每台机器的 `agent_secret` 必须和它相同。
- 这些 `config.json`、`data/` 和 `.env` 都已忽略，不会提交。

生成中转密码哈希：

```text
python relay.py --hash
```

## 本机代理

Windows 11 或 Fedora 44。界面用 PySide6 和 QML。

```text
py -3 power_agent.py
```

无窗口后台用 `py -3 power_agent.py --headless`。先复制 `config.example.json` 为 `config.json`，把 `secret` 换成自己的密钥。监听地址保持 `0.0.0.0`，端口 `8790`。

窗口里可以保存地址、端口和密钥，开始或停止监听，并在本机试关机。Windows 上还有开机自启动、托盘和关闭行为。勾选「假关机」时只记录关机请求。

界面：

- 未监听是红色，正在监听是绿色。假关机时的状态和对应勾选是琥珀色。
- 底部按钮是紫色，文字是黑色。不可用时文字是灰色。
- 右上角关闭按钮是深色底、红色叉。
- 选项是圆形勾选框。输入框是圆角。密钥框右侧的眼睛在隐藏和明文之间切换，图片是 `hidden.png` 和 `show.png`。
- 鼠标停在选项和按钮上会显示说明。
- 窗口和托盘图标来自 `icon.ico`（16、32、48、256）。`icon.png` 是 256 的一档。

## 中转

用 Docker Compose，网络模式是 host，这样唤醒广播才能发出去。`restart: unless-stopped`，Docker 起来后容器会跟着启动。

```text
copy .env.example .env
copy config.example.json data/config.json
docker compose up -d --build
```

在 NAS 上，文件放在 `/volume2/SSD Volume/powerctl`。从 Windows 看是 `I:\powerctl`。更新程序后在该目录执行：

```text
sudo docker compose up -d --build
```

`data/config.json` 里写每台机器的名称、MAC、代理地址和代理密钥。当前这台台式机的 MAC 是 `00:90:51:15:D9:88`，代理地址是 `http://192.168.0.73:8790`。连续多次密码错误会锁定一段时间。

公网不要把明文 `8787` 映射出去。要从外面访问时使用 HTTPS。

## 手机应用

用 Kotlin 和 Jetpack Compose。可以保存多个中转。点进一个中转后，它管理的电脑按缩进列表显示，每台单独开关，发送前会确认。

```text
copy .env.example .env
```

`.env` 里的 `POWER_BASE_URL` 是编译时的默认中转地址。然后：

```text
gradlew :app:assembleDebug
```

- `app/build/outputs/apk/debug/app-debug.apk` 可以在家里用 HTTP。
- `app/build/outputs/apk/release/app-release-unsigned.apk` 是未签名的发布包，不允许明文 HTTP。
