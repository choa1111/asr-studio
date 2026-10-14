# 第三方依赖与授权检查

## 项目自身

项目发布者已选择 [MIT License](LICENSE)，适用于 ASR Studio 有权按此许可证发布的原创代码。版权行采用 `ASR Studio contributors`，不代替或删除任何已有第三方版权声明。

MIT 许可证不能为来源未明的代码或材料补足再发布权。发布者仍须确认原创代码归属、第三方复制代码来源及再发布权，保留依法要求的版权、许可证和 NOTICE；匿名化开发路径不等于删除法律署名。本文件记录第三方授权边界，不替代各组件的许可证。

## 依赖清单与核验来源

- Python 基础运行依赖：`requirements.txt`；开发检查：`requirements-dev.txt`。
- Docker CUDA 约束：`docker/constraints.txt`。
- 可选模型 SDK 及约束：`requirements-asr-*.txt`。
- 前端及其传递依赖：`frontend/package.json`、`frontend/package-lock.json`；锁文件中的第三方 license / funding / 官方仓库信息应保留。
- 系统依赖：Dockerfile 安装的 ffmpeg、Poppler、libgomp 等，以及 Node.js / Python 基础镜像中的组件。

公开源码应排除下载的依赖、模型权重、输入材料和构建产物。分发 Docker 镜像或前端构建产物会涉及其中的第三方组件，不能只附本项目许可证了事；发布镜像前应针对实际版本汇总包内许可证、版权和适用的源代码提供义务。

## 重点检查

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)：核对所安装版本及 CTranslate2、PyAV / FFmpeg 的许可。
- [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR)：分别检查 SDK、模型权重和对齐器的许可，不能从 SDK 推断模型授权。
- [FunASR](https://github.com/modelscope/FunASR)：分别检查 Paraformer、热词资源和 Fun-ASR-Nano 的模型卡与许可。
- Vue、Vue Router、Naive UI、Vite、TypeScript 等：以锁定版本包内的 LICENSE 为准。
- FFmpeg / Poppler 与基础镜像：具体编译选项和分发方式会影响义务，镜像发布前单独核验。
- 参考书籍、提示词素材、词表、截图和录音：确认来源和再分发授权；未经确认的个人材料不要纳入公开源码。

## 本地可核验的许可线索

以下来自当前本地 Python 包元数据和前端锁文件，仅适用于所列版本，不替代包内完整 LICENSE / NOTICE，也不覆盖所有传递依赖或可选模型：

| 组件及版本 | 本地声明的许可证 |
| --- | --- |
| FastAPI 0.135.4、faster-whisper 1.2.1、CTranslate2 4.8.2、Pydantic 2.12.5、PyYAML 6.0.3、RapidFuzz 3.14.6、pytest 8.4.2 | MIT |
| Uvicorn 0.41.0、PyAV 16.1.0、pypdf 5.9.0 | BSD-3-Clause |
| Vue 3.5.30、Vue Router 4.6.4、Naive UI 2.44.1、Vite 6.4.1 | MIT |
| TypeScript 5.9.3 | Apache-2.0 |

PyAV 自身的 BSD 许可不能代替其使用的 FFmpeg 库的许可。本地系统 FFmpeg 构建启用了 GPL；Poppler 工具也包含必须保留的第三方版权声明。它们作为外部命令使用不等于本项目原创代码自动变成 GPL，但分发包含这些程序的镜像时，仍需履行具体组件的 GPL / LGPL 等义务。本地系统工具与 Docker 镜像内的包并非同一构建，应分别核验。

## MIT 许可证的适用边界

- MIT 允许使用、复制、修改及商业分发，但分发软件副本或实质部分时，须包含其版权声明和许可声明；完整条款见根目录 `LICENSE`。Dockerfile 同样将项目许可证和本说明复制到运行镜像。
- 上述已检查的宽松依赖未显示必须将本项目统一为 GPL 的理由，但这不是对全部源码、可选 SDK、模型权重、提示词或词表的完整授权结论。依赖许可不能为来源未明的项目代码提供再发布权。
- 第三方组件不因本项目采用 MIT 而被重新授权。须继续保留各组件要求的许可证、署名与 NOTICE，并履行镜像分发中适用的源代码提供等义务。

## 提示词与用户词表

公开源码仅提供 `config/default_prompts/` 中的英文通用提示词，不附带用户自定义词库，也不自动加载领域词表。私人提示词和词库目录 `config/prompts/`、`config/glossaries/` 均排除在 Git 跟踪及 Docker 构建上下文之外。使用者通过本地配置或 `--glossary-file` 显式提供自有材料，其来源、隐私及再分发权应由使用者确认。

本轮仅使用本地许可线索，没有上传源码或联网核验；以上不是完整的法律审计结论。
