# Kindle Dashboard 系统使用说明

把 Kindle Paperwhite 2 (KPW2) 变成横放的常亮仪表盘，显示天气、待办、DeepSeek消费。

> **⚠️ 部署前必读**：`config.json` 已加入 `.gitignore`（含Token等隐私）。首次使用请复制模板：
> ```bash
> cp config.example.json config.json
> # 然后编辑 config.json 填入 Kindle IP 和 DeepSeek Token
> ```

## 〇、越狱与KUAL安装（首次准备）

> 本项目**需要已越狱的Kindle**，不支持未越狱设备。以下步骤参考 [kindle2workbuddy](https://github.com/MWang-TS/kindle2workbuddy) 与书伴教程，按顺序完成。

### 1. 检查型号和固件
- Kindle 主页 → 菜单 → 设置 → 设备选项 → 设备信息
- 记下**设备型号**（如 KPW2、KT2）和**固件版本**（如 5.12.2.2）
- 到 [书伴·Kindle越狱支持一览](https://bookfere.com/post/1053.html) 确认你的设备+固件组合是否支持越狱
- 本项目测试设备：KPW2（Paperwhite 2），固件 5.12.2.2，越狱方法 WatchThis

### 2. 越狱 Kindle
1. 到 [书伴·Kindle越狱教程](https://bookfere.com/) 下载对应型号的越狱包（KPW2 用 WatchThis 方法）
2. 复制 `.bin` 文件到 Kindle 根目录
3. Kindle 上：设置 → 菜单 → **更新你的 Kindle**
4. 重启后确认越狱成功（出现 "You are JailBroken" 书籍或 KUAL 入口）

### 3. 安装 KUAL + MRPI（核心插件）
- **MRPI**（MR Package Installer）：用于安装 USBNetwork 等 hack 包
- **KUAL**（Kindle Unified Application Launcher）：用于在 Kindle 上启动各种 hack 和工具

1. 到 [书伴·KUAL + MRPI 安装教程](https://bookfere.com/) 下载 MRPI 包，解压后复制 `extensions/` 文件夹到 Kindle 根目录
2. 下载 KUAL 包（KUAL-KUAL-*.zip），复制其中 `extensions/` 内容到 Kindle 根目录
3. 弹出/拔出 Kindle（安全移除硬件）
4. Kindle 首页应出现 **KUAL** 入口（"Kindle Unified Application Launcher"）

### 4. 安装 USBNetwork（SSH支持，本项目核心依赖）
1. 到 [书伴·USBNetwork 安装教程](https://bookfere.com/) 下载 USBNetwork hack 包（.zip 格式）
2. 解压后把 `usbnet/` 文件夹复制到 Kindle 根目录
3. 打开 Kindle 上的 **KUAL → USBNetwork**，将连接模式切换为 **WiFi**
4. 编辑 `/mnt/us/usbnet/etc/config` 确保：
   ```ini
   USE_WIFI="true"
   USE_WIFI_SSHD_ONLY="true"
   ```
5. KUAL → USBNetwork → 选择 "auto"（开机自动启用SSH）
6. Kindle 搜索框输入 `;711` 查看当前 WiFi IP

### 5. 验证 SSH
```bash
ssh root@<KINDLE_IP>   # 默认密码：kindle
# 或配置免密登录：
ssh-copy-id root@<KINDLE_IP>
```

## 一、系统架构

```
┌── 电脑端 ──────────────────────────┐
│ GUI面板 (http://localhost:8080)    │
│   ├─ 修改配置 (config.json)        │
│   ├─ 立即刷新 / 启停守护进程        │
│   └─ 状态监控 / 推送日志            │
│ render.py → refresh.py → SSH推送   │
└───────────────────────────────────┘
            ↕ SSH (base64+stdin)
┌── Kindle端 (KPW2) ────────────────┐
│ keepalive.sh（开机自启+防待机）    │
│   └─ deferSuspend 永不待机        │
│ eips 刷新 E-ink 屏幕               │
└───────────────────────────────────┘
```

## 二、日常使用

### 启动控制面板
1. 双击 `D:\kindle-dashboard\start_gui.bat`
2. 浏览器访问 **http://localhost:8080**
3. 在页面中可：修改配置、立即刷新、开启/停止自动刷新、查看日志

### 常用操作
| 操作 | 方式 |
|---|---|
| 立即刷新 | GUI页面点"立即刷新" |
| 开启自动刷新 | GUI页面点"开启自动刷新"（每240秒推送） |
| 停止自动刷新 | GUI页面点"停止自动刷新" |
| 修改Kindle IP | GUI配置表单 → 保存 |
| 手动刷新 | 双击 `manual_refresh.bat` |

## 三、配置文件

### config.json（GUI修改入口）
```json
{
  "kindle_host": "192.168.x.x",     // Kindle IP（复制config.example.json修改）
  "kindle_port": 22,
  "kindle_user": "root",
  "ssh_key": "~/.ssh/id_kindle",
  "refresh_interval": 240,          // 刷新周期（秒）
  "ssh_timeout": 15,
  "ssh_retries": 3,
  "ssh_retry_delay": 15,
  "deepseek_token": ""              // DeepSeek网页端Token（真实消费数据）
}
```

### 数据源
- **待办**：金鱼本 `D:\WorkBuddyData\Claw\todos_data.json`
- **天气**：Open-Meteo API（佛山，免费无需Key）
- **DeepSeek消费**：真实数据（网页端Token，platform.deepseek.com）
  - Token获取：登录 platform.deepseek.com → F12 → Network → 请求头 Authorization
  - 填入GUI配置表单或config.json的deepseek_token字段
  - 数据5分钟缓存，未配置Token时显示示例数据

## 四、Kindle端部署

### 1. 部署文件（通过SSH或USB）
```bash
# 通过SSH传输（项目根目录下执行）
scp -r kindle-scripts/dashboard/bin/keepalive.sh root@<KINDLE_IP>:/mnt/us/dashboard/bin/
scp -r kindle-scripts/dashboard root@<KINDLE_IP>:/mnt/us/extensions/
scp kindle-scripts/usbnetwork.sh root@<KINDLE_IP>:/mnt/us/usbnet/bin/usbnetwork.sh
ssh root@<KINDLE_IP> "chmod +x /mnt/us/dashboard/bin/keepalive.sh; touch /mnt/us/dashboard/keepalive_autostart"
```

### 2. 防待机守护（keepalive.sh）
- **位置**：`/mnt/us/dashboard/bin/keepalive.sh`
- **开机自启**：已配置（usbnetwork.sh + keepalive_autostart标志，开机45秒延迟后自动启动）
- **手动启停**：
  - 启动：`nohup /mnt/us/dashboard/bin/keepalive.sh --no-delay > /dev/null 2>&1 &`
  - 停止：`pkill -f keepalive.sh`，然后 `echo 0 > /sys/class/rtc/rtc0/wakealarm`

### 3. KUAL扩展（可选，手动管理仪表盘模式）
- `/mnt/us/extensions/dashboard/`（重启Kindle后KUAL显示 Dashboard 菜单）
- **启动仪表盘模式** / **退出仪表盘模式**

### 4. 恢复Kindle正常使用
```bash
ssh root@<IP> "/etc/init.d/framework start"
```
或长按电源键7秒重启（重启后 keepalive 若已配置自启会再次进入仪表盘模式）。

## 五、故障排查

| 问题 | 解决 |
|---|---|
| SSH连不上 | 检查Kindle WiFi；确认keepalive在运行 |
| GUI报Permission denied | 必须用 start_gui.bat 正常环境启动，勿用WorkBuddy后台 |
| Kindle待机 | 重启Kindle后等45秒（keepalive自启延迟），检查`pidof lipc-wait-event` |
| IP变了 | GUI配置修改或改config.json |
| dropbear崩溃 | 重启Kindle；keepalive会拉起dropbear |

## 六、项目文件（D:\kindle-dashboard\）

| 文件 | 说明 |
|---|---|
| `gui.py` | 控制面板服务（8080端口） |
| `render.py` | 渲染引擎（1024×758横屏） |
| `refresh.py` | 推送脚本（base64+stdin+eips） |
| `daemon.py` | 守护进程（240秒循环） |
| `settings.py` | 配置（从config.json读取） |
| `config.json` | GUI可写配置 |
| `app_old.py` | 旧版HTTP图片服务（已废弃，勿用） |
| `start_gui.bat` | 一键启动控制面板 |
| `start_daemon.bat` | 单独启动守护进程 |
| `manual_refresh.bat` | 手动刷新 |
| `templates/index.html` | 控制面板网页 |
| `kindle-scripts/` | Kindle端脚本（keepalive等） |
| `output/` | 日志与状态文件 |
