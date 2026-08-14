# 用 Codex 一站式部署

把本仓库链接发给对方的 Codex，并发送：

> 请部署这个 ROI 分割工作台：运行 `install-and-start-windows.cmd`，自动创建隔离 Python 环境、安装 requirements、生成 `config/model_paths.json` 并启动本地网页。请检查 WSL 和 nnInteractive 模型路径；模型权重不要提交到 GitHub。如果路径未配置，请告诉我需要填写哪些路径。

Codex 可以自动完成项目内的安装和启动。安装 Python、启用 WSL、下载 nnInteractive 软件或模型权重属于操作系统/外部资源变更，首次执行时可能需要用户确认；这些权重不会写入 Git 仓库。
