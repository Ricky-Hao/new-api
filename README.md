# new-api 补丁集

这是 [Ricky-Hao/new-api](https://github.com/Ricky-Hao/new-api) 的维护仓，应用来自 [QuantumNous/new-api](https://github.com/QuantumNous/new-api)。维护分支和默认分支继续使用 `main`。本仓保存固定上游版本、按能力分组的 Git diff、生成工具、开发环境和 CI；完整 new-api 源码由清单重建。

[`manifest.json`](manifest.json) 是上游完整 SHA、补丁顺序和依赖的唯一事实来源。当前只有 [`response-interrupt`](patches/response-interrupt/README.md) 一组，代码和原有回归测试一起保存。增加其他补丁、回写修改、退役补丁和更新上游的操作见 [MAINTENANCE.md](MAINTENANCE.md)。

```text
manifest.json                  固定 base 和唯一有序清单
patches/<能力>/                changes.patch、tests.json、README.md
tools/                         Python 标准库维护工具和准备入口
.devcontainer/                 维护仓开发环境
.github/workflows/ci.yml        从生成源码检查和发布
.work/application/             忽略的独立 Git checkout，可重新生成
```

## 新 clone 和开发

从 `main` clone 本仓后，使用根 `.devcontainer/devcontainer.json` 打开开发容器。容器提供项目所需 Go、Bun、Node、Python、Git 和 SSH 客户端；`post-create.sh` 调用下面的稳定入口，生成源码、下载三个 Go 模块依赖、按锁文件安装前端依赖并构建真实嵌入资源：

```bash
bash tools/prepare.sh
```

已有工具链也可直接运行该命令。只需要生成源码时：

```bash
python3 tools/patchset.py list
python3 tools/patchset.py generate --target .work/application
python3 tools/patchset.py verify --target .work/application
```

生成默认从 manifest 的上游 clone，随后检出固定完整 SHA。离线时可添加 `--source /path/to/existing/new-api`，该本地 Git 仓必须包含固定 base。生成目录拥有独立 `.git`，不借用维护仓的索引，也不创建应用提交。补丁应用在应用索引中暂存；`HEAD` 仍是 base。已有目录只核验，不会自动重置或覆盖修改。

VS Code 初次打开维护根；准备完成后，可打开根 `new-api.code-workspace` 同时查看维护仓和应用源码。默认终端进入 `.work/application`。Go、Bun 和应用配置都在应用目录中使用；修改前先读该目录的原始 `AGENTS.md`，前端还要读 `web/AGENTS.md`。

维护工具命令从维护根执行，例如：

```bash
GOWORK=off GOFLAGS=-timeout=20m python3 tools/patchset.py test --target .work/application
```

这会真实运行补丁组声明的定向测试。生成源码中的修改必须回写所属补丁，并从干净 checkout 完整重放验证后交付。`.work/`、依赖、构建产物和本地数据不提交。

## CI 与镜像

目标 `main` 的 PR 运行维护工具测试、完整补丁生成、三个 Go 模块的 vet/build/test，以及前端 typecheck/test。各 job 从同一维护 SHA 和 base 生成源码，并比较应用 tree。PR 清单和补丁修改会实际参与这些检查。

只有 PR **实际合并到 main** 的 `pull_request_target: closed` 事件会在检查通过后发布，使用事件中的真实 `merge_commit_sha`。没有直接 push、tag 或手动发布入口。镜像从生成应用的原始 Dockerfile 构建 `linux/amd64`，一次 build/load，经真实 `/api/status` 就绪校验后才登录并推送 GHCR。

`ghcr.io/ricky-hao/new-api:sha-<40 位 SHA>` 中的 SHA 是**维护 main 的合并提交**。镜像标签同时记录维护提交、固定上游 base、生成应用 tree；tree 指清单重建的源码，位于发布步骤写入 `VERSION=ricky-hao-sha-<维护 SHA>` 之前。只有远端 main 仍等于该维护 SHA 才更新 `latest`。发布队列串行且不取消进行中的推送。

## 来源与许可

new-api 由 **QuantumNous** 及其贡献者开发。应用及其补丁继续遵循原 [LICENSE](LICENSE)、[NOTICE](NOTICE) 和 [THIRD-PARTY-LICENSES.md](THIRD-PARTY-LICENSES.md)，包括 AGPL-3.0 与原有附加条款；生成源码保留这些文件、原始 README、版权、品牌和项目规则。使用及分发时须遵守原许可，包括适用的源码提供义务。本仓的固定 base 和补丁可用于重建相应应用源码。

维护工具改编自固定版本的 Ricky-Hao/LibreChat；借用代码的 MIT 许可仅适用于注明的工具文件，见 [SOURCES.md](SOURCES.md) 和 [tools/LICENSE.LibreChat](tools/LICENSE.LibreChat)。该 MIT 许可不改变 new-api 应用的许可。
