# 远程开关机

手机不直接连电脑。手机只访问 NAS 上的中转；中转负责唤醒网卡，并让电脑上的代理关机。

三个仓库各管一件事，合在一起才是完整系统：

- 本机代理：[powerctl-agent](https://github.com/EugeneXXXie/powerctl-agent)。装在要开关的 Windows 或 Fedora 电脑上，监听 `8790`。
- NAS 中转：[powerctl-relay](https://github.com/EugeneXXXie/powerctl-relay)。家里一直开着，监听 `8787`。手机只认识它。
- 手机应用：[powerctl-android](https://github.com/EugeneXXXie/powerctl-android)。保存一个或多个中转，列出每台电脑，并发送开机或关机。

调用方向是固定的：手机 → 中转 → 代理。代理不要暴露到公网。同一块网卡只有一个 MAC，唤醒不能选择操作系统。

# Remote power

The phone never talks to the computer. It talks only to the relay on the NAS. The relay sends Wake-on-LAN, and asks the agent on the computer to shut down.

Three repositories, one system:

- Agent: [powerctl-agent](https://github.com/EugeneXXXie/powerctl-agent). Runs on the Windows or Fedora machine and listens on `8790`.
- Relay: [powerctl-relay](https://github.com/EugeneXXXie/powerctl-relay). Stays on at home and listens on `8787`. The phone knows only this service.
- Android app: [powerctl-android](https://github.com/EugeneXXXie/powerctl-android). Stores one or more relays, lists each computer, and sends power on or off.

The call path is fixed: phone → relay → agent. Do not expose the agent to the internet. One network card has one MAC, so wake cannot choose an operating system.

## 三者怎么接上

1. 代理在 `config.json` 里设置密钥，并在 `0.0.0.0:8790` 监听。
2. 中转的 `data/config.json` 写下这台机器的名称、MAC、`agent_url` 和同一个 `agent_secret`。当前台式机的 MAC 是 `00:90:51:15:D9:88`，代理地址是 `http://192.168.0.73:8790`。
3. 手机里添加中转地址（家里是 `http://192.168.0.6:8787`）和手机密码。密码原文不在这里，见下一节。
4. 手机点开机时，中转向该 MAC 发网络唤醒。点关机时，中转带着代理密钥调用代理的 `POST /shutdown`。

## How the three connect

1. The agent stores its key in `config.json` and listens on `0.0.0.0:8790`.
2. The relay’s `data/config.json` lists that machine’s name, MAC, `agent_url`, and the same `agent_secret`. This desktop’s MAC is `00:90:51:15:D9:88` and its agent URL is `http://192.168.0.73:8790`.
3. The phone stores the relay address (at home, `http://192.168.0.6:8787`) and the phone password. The password itself is not written here; see the next section.
4. Power on makes the relay send a magic packet to that MAC. Power off makes the relay call the agent’s `POST /shutdown` with the agent key.

## 密钥放在哪里

不要把密码写进 Git。

- 手机密码的原文在中转的 `data/phone-password.txt`。NAS 上同一份在 `I:\powerctl\data\phone-password.txt`。
- 中转用来核对的是哈希，不是原文。本机文件是 `relay/data/config.json` 的 `password_hash`。NAS 上是 `I:\powerctl\data\config.json`，DSM 路径为 `/volume2/SSD Volume/powerctl/data/config.json`。
- 代理密钥在代理的 `config.json` 里，字段名是 `secret`。中转里每台机器的 `agent_secret` 必须和它相同。
- `config.json`、`data/` 和 `.env` 都已忽略。

生成中转密码哈希：

```text
python relay.py --hash
```

## Where the secrets live

Do not commit passwords.

- The phone password text is `data/phone-password.txt` in the relay project. On the NAS the same file is `I:\powerctl\data\phone-password.txt`.
- The relay checks a hash, not the text. Locally that hash is `password_hash` in `relay/data/config.json`. On the NAS it is `I:\powerctl\data\config.json`, which is `/volume2/SSD Volume/powerctl/data/config.json` on DSM.
- The agent key is `secret` in the agent’s `config.json`. Each machine’s `agent_secret` in the relay config must match it.
- `config.json`, `data/`, and `.env` are gitignored.

Create the relay password hash with:

```text
python relay.py --hash
```

## 本机代理

仓库：[powerctl-agent](https://github.com/EugeneXXXie/powerctl-agent)。

Windows 11 或 Fedora 44。窗口用 PySide6 和 QML，语言跟随系统，已包含英文、简体中文、日文、韩文、西班牙文、葡萄牙文和法文。没有对应语言时用英文。

```text
py -3 power_agent.py
```

无窗口后台：`py -3 power_agent.py --headless`。先把 `config.example.json` 复制为 `config.json`，再改 `secret`。

窗口可以保存地址、端口和密钥，开始或停止监听，并在本机试关机。Windows 上还有开机自启动、托盘和关闭行为。「假关机」只记录请求。

界面：未监听为红色，正在监听为绿色，假关机为琥珀色。底部按钮为紫色、黑字，不可用时字为灰色。关闭按钮为深色底、红色叉。选项是圆形勾选框，输入框是圆角。密钥框右侧的眼睛在隐藏和明文之间切换。鼠标停在选项和按钮上会显示说明。

窗口和托盘图标是 `icon.ico`（16、32、48、256）。`icon.png` 是 256 的一档。

## Agent

Repository: [powerctl-agent](https://github.com/EugeneXXXie/powerctl-agent).

Windows 11 or Fedora 44. The window uses PySide6 and QML. It follows the system language and ships English, Simplified Chinese, Japanese, Korean, Spanish, Portuguese, and French. Anything else falls back to English.

```text
py -3 power_agent.py
```

Background with no window: `py -3 power_agent.py --headless`. Copy `config.example.json` to `config.json` and set `secret`.

The window saves the address, port, and key, starts or stops listening, and can shut this computer down. On Windows it also covers sign-in startup, the tray, and what closing the window does. Fake shutdown only records the request.

Not listening is red, listening is green, and fake shutdown is amber. The bottom buttons are purple with black text; disabled text is gray. The close button is a dark disc with a red X. Options are circular checks, and inputs have rounded corners. The eye at the end of the key field switches between hidden and plain text. Hovering an option or button shows a short note.

The window and tray icon is `icon.ico` (16, 32, 48, and 256). `icon.png` is the 256 size.

## NAS 中转

仓库：[powerctl-relay](https://github.com/EugeneXXXie/powerctl-relay)。

用 Docker Compose，网络模式是 host，唤醒广播才能发出去。`restart: unless-stopped`，Docker 起来后容器会跟着启动。

```text
copy .env.example .env
copy config.example.json data/config.json
docker compose up -d --build
```

在 NAS 上，目录是 `/volume2/SSD Volume/powerctl`。从 Windows 看是 `I:\powerctl`。更新程序后在该目录执行：

```text
sudo docker compose up -d --build
```

连续多次密码错误会锁定一段时间。公网不要映射明文 `8787`。要从外面访问时使用 HTTPS。

## Relay

Repository: [powerctl-relay](https://github.com/EugeneXXXie/powerctl-relay).

Docker Compose uses the host network so wake broadcasts can leave the container. `restart: unless-stopped` brings the container up with Docker.

```text
copy .env.example .env
copy config.example.json data/config.json
docker compose up -d --build
```

On the NAS the directory is `/volume2/SSD Volume/powerctl`, which Windows sees as `I:\powerctl`. After updating the program, run this there:

```text
sudo docker compose up -d --build
```

Repeated wrong passwords lock the relay for a while. Do not publish plaintext port `8787`. Use HTTPS if the phone must reach it from outside the home.

## 手机应用

仓库：[powerctl-android](https://github.com/EugeneXXXie/powerctl-android)。

Kotlin 和 Jetpack Compose。可以保存多个中转。点进一个中转后，它管理的电脑按缩进列表显示，每台单独开关，发送前会确认。界面语言跟随系统，和代理使用同一组七种语言。

```text
copy .env.example .env
```

`.env` 里的 `POWER_BASE_URL` 是编译时的默认中转地址。然后：

```text
gradlew :app:assembleDebug
```

- `app/build/outputs/apk/debug/app-debug.apk` 可以在家里用 HTTP。
- `app/build/outputs/apk/release/app-release-unsigned.apk` 是未签名的发布包，不允许明文 HTTP。

## Android app

Repository: [powerctl-android](https://github.com/EugeneXXXie/powerctl-android).

Kotlin and Jetpack Compose. The app stores several relays. Opening one shows its computers in an indented list. Each machine has its own power button, and the app asks before sending. The interface follows the system language and uses the same seven languages as the agent.

```text
copy .env.example .env
```

`POWER_BASE_URL` in `.env` is the default relay address baked in at build time. Then:

```text
gradlew :app:assembleDebug
```

- `app/build/outputs/apk/debug/app-debug.apk` may use HTTP on the home network.
- `app/build/outputs/apk/release/app-release-unsigned.apk` is an unsigned release build and rejects cleartext HTTP.
