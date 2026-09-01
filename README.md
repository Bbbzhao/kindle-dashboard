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
┌── 电脑端 ─────────────────────────────────────┐
│ kindle-daemon.py（守护进程，常驻+开机自启）    │
│   ├─ 自动拉起GUI控制面板 (http://localhost:8080)│
│   │   修改配置 / 立即刷新 / 启停守护进程        │
│   │   SSH测试 / 局域网扫描找Kindle             │
│   │   退出仪表盘模式 / 状态监控 / 日志          │
│   └─ 每240秒 render.py → refresh.py → SSH推送  │
└──────────────────────────────────────────────┘
            ↕ SSH (base64+stdin)
┌── Kindle端 (KPW2) ───────────────────────────┐
│ keepalive.sh（防待机守护）                    │
│   └─ deferSuspend 永不待机，SSH永远可用       │
│ eips 刷新 E-ink 屏幕                          │
│ KUAL扩展：Dashboard（启动/退出仪表盘模式）     │
└──────────────────────────────────────────────┘
```

## 二、日常使用

### 全自动运行（无需手动操作）
守护进程 `kindle-daemon.py` 开机自启，**启动时自动拉起GUI控制面板**：

| 操作 | 方式 |
|---|---|
| 打开控制面板 | 浏览器访问 **http://localhost:8080** |
| 启动守护进程 | 双击 `kindle-daemon-start.bat` |
| 停止守护进程 | 双击 `kindle-daemon-stop.bat`（**保留GUI**，可继续看状态） |
| 手动开启GUI | 双击 `start_gui.bat`（可选，守护进程会自动拉起） |

### GUI功能一览
| 功能 | 说明 |
|---|---|
| **立即刷新** | 立即推送一次仪表盘 |
| **开启/停止自动刷新** | 启停守护进程（停止后GUI保留） |
| **测试SSH连接** | 检测当前IP的SSH连通性（TCP+握手+延迟） |
| **扫描局域网找Kindle** | IP变化后自动发现新IP（约10秒） |
| **退出仪表盘模式** | Kindle从仪表盘回到原生界面（约30秒） |
| **参数配置** | Kindle IP、刷新周期、SSH、DeepSeek Token |
| **状态监控/日志** | 守护进程状态、Kindle状态、推送日志（15秒刷新） |

### 常用操作
| 操作 | 方式 |
|---|---|
| Kindle重启后IP变了 | GUI → 测试SSH连接 → 扫描局域网 → 更新IP保存 |
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

### 1. 部署文件（通过SSH）
```bash
# 从项目根目录执行
scp -r kindle-scripts/dashboard root@<KINDLE_IP>:/mnt/us/extensions/
scp kindle-scripts/dashboard/bin/keepalive.sh root@<KINDLE_IP>:/mnt/us/dashboard/bin/
scp kindle-scripts/usbnetwork.sh root@<KINDLE_IP>:/mnt/us/usbnet/bin/usbnetwork.sh
ssh root@<KINDLE_IP> "chmod +x /mnt/us/dashboard/bin/keepalive.sh /mnt/us/extensions/dashboard/bin/*.sh"
```
> 注意：KUAL扩展需包含 `config.xml`（KUAL识别必需），缺失则KUAL不显示菜单。

### 2. 防待机守护（keepalive.sh）
- **位置**：`/mnt/us/dashboard/bin/keepalive.sh`
- **原理**：监听 `readyToSuspend` 事件 → `deferSuspend 999999999` 无限延迟待机，SSH永远可用
- **开机自启**：`usbnetwork.sh` + `keepalive_autostart` 标志（开机45秒延迟后自动启动）
- **手动启停**：
  - 启动：`nohup /mnt/us/dashboard/bin/keepalive.sh --no-delay > /dev/null 2>&1 &`
  - 停止：`pkill -f keepalive.sh`，然后 `echo 0 > /sys/class/rtc/rtc0/wakealarm`

### 3. KUAL扩展（Dashboard菜单）
- `/mnt/us/extensions/dashboard/`（config.xml + menu.json + bin/）
- **启动仪表盘模式**：创建自启标志 + 运行keepalive（重启后自动进仪表盘）
- **退出仪表盘模式**：停止keepalive + 删除自启标志 + 恢复framework（重启后保持原生界面）

### 4. 恢复Kindle正常使用
```bash
ssh root@<IP> "/sbin/start framework"
```
> KPW2的framework由upstart管理，命令在 `/sbin`（SSH shell的PATH不含/sbin，需用完整路径）。
> 或长按电源键7秒重启。

## 五、故障排查

| 问题 | 解决 |
|---|---|
| SSH连不上 | GUI点"测试SSH连接"诊断；IP变了就"扫描局域网找Kindle" |
| IP频繁变化 | 路由器设置DHCP静态租约（绑定Kindle MAC固定IP） |
| GUI报Permission denied | 必须用 start_gui.bat 正常环境启动，勿用WorkBuddy后台 |
| GUI改代码后不生效 | 需重启GUI（改代码后进程加载旧版） |
| Kindle待机 | 检查`pidof lipc-wait-event`；keepalive未运行时手动启动 |
| dropbear崩溃 | 重启Kindle；keepalive会拉起dropbear |
| KUAL不显示Dashboard | 确认extensions/dashboard/有config.xml |
| 退出仪表盘屏幕不刷新 | 确认framework是start/running（/sbin/start framework） |

## 六、项目文件（D:\kindle-dashboard\）

| 文件 | 说明 |
|---|---|
| `gui.py` | 控制面板服务（8080端口，SSH测试/扫描/退出仪表盘） |
| `kindle-daemon.py` | 守护进程（自动拉起GUI，停止保留GUI） |
| `render.py` | 渲染引擎（1024×758横屏，标题居中） |
| `refresh.py` | 推送脚本（base64+stdin+eips，Git Bash ssh） |
| `deepseek_data.py` | DeepSeek真实消费数据（网页端Token） |
| `settings.py` | 配置（从config.json读取） |
| `config.json` | 可写配置（gitignore排除，含Token） |
| `config.example.json` | 配置模板（无隐私） |
| `kindle-daemon-start.bat` | 启动守护进程 |
| `kindle-daemon-stop.bat` | 停止守护进程（保留GUI） |
| `start_gui.bat` / `stop_gui.bat` | 手动启停GUI（可选） |
| `manual_refresh.bat` | 手动刷新 |
| `install_task.ps1` | 计划任务安装（可选） |
| `templates/index.html` | 控制面板网页 |
| `kindle-scripts/` | Kindle端脚本（keepalive/dashboard/usbnetwork） |
| `output/` | 日志与状态文件 |

## 七、GitHub 私有库

- 仓库：https://github.com/Bbbzhao/kindle-dashboard.git
- `config.json`（含Token）、`output/`、`.cleanup_backup/` 已加入 `.gitignore`，不会泄露隐私
