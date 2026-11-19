# Houdini 顶部资源监控条

适用于 **Windows + Houdini 21 / 22** 的轻量界面插件，实时显示整机 **CPU、GPU、RAM、VRAM** 使用量。
通过 Houdini Package 自动加载，使用宿主自带的 Python / PySide6，不是 HDA，不依赖特定 HIP 工程。

## 最终版界面

![v005 实际界面截图：CPU、GPU、RAM、VRAM](docs/images/ui-v005.png)

上图来自实际 Houdini 窗口中的监控控件，显示的是采样时刻的数据。
监控条放在 Houdini 顶部 **Main 右侧空白区域，与菜单并排**；不透明背景避免底层文字透出。

## 下载与安装

下载 [便携安装包](../../releases/latest) 中的 `HoudiniResourceMonitor_v005_Portable.zip`，或使用仓库 [dist 目录中的 ZIP](dist/HoudiniResourceMonitor_v005_Portable.zip)。

1. 完整解压 ZIP。
2. 双击 **安装.cmd**，看到“安装成功”。
3. 启动或重启 Houdini 21 / 22。

无需管理员权限、无需联网、无需另外安装 Python 或 PySide6。
安装器将文件复制到 `%LOCALAPPDATA%\HoudiniResourceMonitor\v005\plugin`，并为 Windows“文档”中的两个 Houdini 版本写入 Package 配置。
**安装后可以删除解压目录或拔出 U 盘。** 安装只对当前 Windows 用户生效。

直接下载仓库源码 ZIP 也可以：完整解压后双击根目录的“安装.cmd”。

## 使用

- CPU、GPU 显示整机利用率，RAM、VRAM 显示已用容量 / 总容量，并配合占用色条。
- 默认每秒刷新，右键可选择 0.5、1、2、5 秒刷新周期和显卡。
- 鼠标停留在 GPU 可查看显卡型号、温度；读数异常时显示原因。
- 菜单或桌面选择器较宽时，右键“调整菜单行左侧留白…”增加保留宽度。
- 监控条随主窗口移动和最小化，窗口过窄时自动隐藏。
- 重复加载只保留一个监控条，采样在后台线程执行。

## 卸载

双击 **卸载.cmd**，然后重启 Houdini。
没有原始安装包时，也可使用 `%LOCALAPPDATA%\HoudiniResourceMonitor` 中保留的卸载器。
安装前若有同名 Package 配置，会备份并在卸载时恢复；配置被其他程序修改时予以保留。
卸载不会删除场景、其他插件或用户目录。若恢复的是旧版插件配置，旧版可能仍会加载。

## 兼容性

| 环境 | 说明 |
| --- | --- |
| 操作系统 | Windows |
| Houdini 21 | 本机验证 21.0.729，Python 3.11，PySide6 6.5.3 |
| Houdini 22 | 本机验证 22.0.368，Python 3.13，PySide6 6.8.3 |
| CPU / RAM | Windows 原生接口，无额外采样库 |
| GPU / VRAM | NVIDIA 显卡及可用驱动，使用 nvidia-smi |
| AMD / Intel 显卡 | GPU / VRAM 显示不可用，CPU / RAM 仍可使用 |

Houdini 21、22 均已做过实际宿主验证；最终便携版在 Houdini 22 中额外验证了独立安装路径导入与单实例复用。
便携安装器已在真实 Windows PowerShell 中验证中文、空格、中括号路径、重复安装、移走解压目录、卸载恢复及损坏文件检查。
尚未在另一台物理电脑或所有 Houdini 小版本上逐一实测。

若使用自定义 `HOUDINI_USER_PREF_DIR`，可向 `manage.ps1` 传入 `-DocumentsRoot`；指定目录应包含 `houdini21.0` / `houdini22.0` 子目录。
GPU 数据为 NVIDIA 整卡统计，与任务管理器单引擎曲线可能不同。
主界面线程长时间忙碌时，界面重绘可能暂停。

## 目录与原理

```text
plugin/
  python3.11libs/
    pythonrc.py / uiready.py
    hrm/
      metrics.py       Windows / NVIDIA 采样
      ui.py            PySide6 界面和后台线程
      startup.py       自动启动与重复加载保护
  python3.13libs/       Houdini 22 启动入口，共享纯 Python 源码
manage.ps1             中文安装、卸载与文件校验
manifest.json          插件源码 SHA256 校验清单
dist/                  便携安装 ZIP
docs/images/           最终版实际界面截图
```

不请求网络、不上传数据、不读取场景或凭据；安装脚本不修改系统执行策略。`requirements.txt` 用于记录宿主依赖版本，**不要对 Houdini 直接安装或替换 Qt**。

## 官方接口参考

- [Houdini Package](https://www.sidefx.com/docs/houdini/ref/plugins.html)
- [Python 启动脚本](https://www.sidefx.com/docs/houdini/hom/locations.html)
- [Qt 主窗口接口](https://www.sidefx.com/docs/houdini/hom/hou/qt/mainWindow.html)
