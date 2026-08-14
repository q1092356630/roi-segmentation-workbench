# ROI 分割工作台（半自动精简版）

这是一个本地 HTML ROI 工作台，保留半自动 nnInteractive、手动勾画、三视图阅片、3D ROI 预览、标签管理、ROI 导入/导出、撤销/重做和病例安全保存。

本版本明确不包含：

- 血管模块（肝动脉、全腹动脉、vesselFM 及相关 API）；
- 肿瘤全自动模型和批处理入口；
- 任何模型权重、患者影像、运行缓存和本机私有路径。

## Windows 快速启动

需要 Python 3.9–3.12。首次使用先在 PowerShell 中执行：

```powershell
python -m pip install -r requirements-roi-workbench.txt
Copy-Item config/model_paths.example.json config/model_paths.json
```

然后双击 `start-windows.cmd`，或执行：

```powershell
.\run_roi_web.ps1
```

浏览器打开 <http://127.0.0.1:8877>。

### 一键安装并启动

Windows 用户也可以直接双击 `install-and-start-windows.cmd`。它会自动创建项目专用 `.venv`、安装依赖、生成 `config/model_paths.json` 并启动网页。这个脚本不会下载或提交模型权重。

如果使用 Codex，参见 [CODEX_DEPLOY.md](CODEX_DEPLOY.md)，把仓库链接和其中的部署提示一起发给 Codex 即可。

## macOS / Linux

```bash
python3 -m pip install -r requirements-roi-workbench.txt
cp config/model_paths.example.json config/model_paths.json
./start.sh
```

## 半自动模型

半自动功能通过 WSL 调用开源 nnInteractive。权重不在本仓库中分发；请在目标电脑按 nnInteractive 官方说明安装 Python 环境并下载模型，然后编辑 `config/model_paths.json`：

```json
{
  "wsl_distro": "你的 WSL 发行版名称",
  "python_path": "/你的环境/bin/python",
  "model_path": "/你的 nnInteractive_v1.0 模型目录"
}
```

也可以使用环境变量覆盖配置：`ROI_WSL_DISTRO`、`ROI_NNINTERACTIVE_PYTHON`、`ROI_NNINTERACTIVE_MODEL_PATH`。没有配置模型时，半自动按钮会提示模型不可用；手动勾画和 ROI 管理仍可使用。

## 患者数据安全

工作台只监听本机 loopback 地址，不上传影像。输入患者总文件夹后，病例文件仍保存在原目录；保存前会校验源影像几何和哈希。请不要把患者数据、NIfTI、DICOM 或 `config/model_paths.json` 提交到 GitHub。

## 已知限制

- nnInteractive 需要目标电脑自行安装 WSL/Python/开源模型，且需要与机器匹配的 CPU/GPU 环境。
- 本仓库不提供临床诊断、PACS、DICOMWeb 或云端服务。
- 公开发布前请由代码权利人选择项目许可证，并分别遵守 nnInteractive 及其模型的许可证。
