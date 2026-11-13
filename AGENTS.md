# new-api 补丁维护规则

DO NOT send optional commentary

本仓是 Ricky-Hao/new-api 的补丁维护仓；应用来自 QuantumNous/new-api。先读根 README、MAINTENANCE 和相关补丁组 README。维护分支与默认分支为 main。

## 生命周期入口

- 新建补丁：[增加一组补丁](MAINTENANCE.md#增加一组补丁)。
- 更新或回写补丁：[修改或回写已有补丁](MAINTENANCE.md#修改或回写已有补丁)。
- 应用补丁、生成应用分支：[固定版本和应用边界](MAINTENANCE.md#固定版本和应用边界)。
- 淘汰补丁：[退役或更新上游](MAINTENANCE.md#退役或更新上游)中的退役、替代和主动放弃规则。
- 更新上游：[退役或更新上游](MAINTENANCE.md#退役或更新上游)中的上游同步步骤。
- 验证与发布：[验证和发布边界](MAINTENANCE.md#验证和发布边界)。

## 目录和事实来源

- `manifest.json` 唯一定义上游 URL、完整 base SHA、准确 ref、应用分支名、补丁顺序、状态、真实依赖和文件范围；不得维护第二份应用顺序或浮动 base。release 名必须精确对应 base，非 release 使用上游 SHA 命名。
- `patches/<能力>/` 保存标准 Git diff、原有及新增回归、测试契约和维护原因。代码、测试及必要应用文档归同组，同一改动只归属一组。
- `tools/`、根 `.devcontainer/` 和根 `.github/workflows/` 只负责维护和生成。
- `branch` 入口从完整清单创建真实应用分支，保留上游历史、逐组实现提交和来源记录；`.work/application/` 是该分支的忽略 linked worktree，拥有独立索引。根没有 go.mod/web，所有应用命令从应用 worktree 运行。完整应用树只归应用分支；依赖、构建产物、数据或凭据不提交。
- 应用分支是可重建快照，不覆盖已有分支。开发另建编辑分支或 checkout，回写补丁后生成新的版本或 `-patchset-N` 分支。上游 workflow 原文归档到应用分支的 `.github/upstream-workflows/`，活动 CI 归维护 main 管理。

应用变更前必须先读生成 checkout 的原始 `AGENTS.md`，以及适用的子目录规则和按索引要求读取的文档。前端、计费、认证、数据库及任务插件要求继续适用；不要把根维护规则当作绕过应用规则的理由。上游许可、版权、new-api 和 QuantumNous 标识与归属必须保留。

## 修改和验证

优先使用已有工具与项目能力。应用源码修改必须回写所属 patch，并按 MAINTENANCE 中相邻 tree 的办法导出，避免混入前后组改动。清单变化后在干净目标完整 check/apply 并生成应用分支，再核验来源、提交和净差异，运行受影响真实测试。应用分支不得成为脱离补丁的另一份业务事实来源。

维护工具使用 Python 标准库；变更运行 `python3 -m unittest discover -s tools -p 'test_*.py' -v`。保留错误 base/脏目标拒绝、传递依赖与清单顺序、完整预检和后序失败不落地前序修改的合同。不得通过自动 reset/clean 丢弃已有工作。应用三个 Go 模块分别 `GOWORK=off` vet/build/test；前端使用 Bun，检查从生成目录执行。遵循应用自己的额外必跑项，低影响维护文本修改不重复昂贵业务验证。

根开发环境只准备项目依赖与必要 SSH 能力，不安装或改写 coding agent、执行器或全局 Git 身份。根 Docker build context 只构建开发工具链，应用镜像使用生成 checkout 的原 Dockerfile 和 .dockerignore。

CI 的 PR 检查必须实际生成新清单对应的应用分支，各 job 核对同一维护 SHA 的 base/branch/commit/tree。只允许真实 merged 到 main 的 pull_request_target closed 事件，在实际 merge_commit_sha 检查通过后发布镜像。保留最小权限、发布串行队列、一次 build/load、readiness 严格单 JSON 成功校验，以及 main 仍等于该 SHA 才更新 latest 的保护；不要增加 push/tag/manual 发布入口或 type=gha 镜像缓存。CI 不推 Git 分支；应用分支由负责人在合并检查成功后核对精确来源并发布，不扩大 contents 权限。

工具来源与许可范围见 SOURCES.md；LibreChat 的 MIT 不改变 new-api 应用许可。交付前自查改动、`git diff --check` 和实际应用差异，报告真实执行的检查、必要边界及未完成项。

## 文档规范

- 使用自然、清楚的简体中文，优先常用词和主动短句。代码、路径、专名和术语保持准确、一致。
- [README.md](README.md) 是维护入口；[MAINTENANCE.md](MAINTENANCE.md) 负责通用操作；`patches/<能力>/README.md` 说明具体行为、保留理由、来源、真实依赖、验证方式和替代条件。同一主题只保留一个主要来源，其他文档引用它。
- 行为、命令、字段或流程变化时，同步更新相应文档和入口索引。维护文档放根或补丁组 README，不在 `docs/` 或 `plugins/` 下新建文档。
- 历史验收记录与当前操作规范分开，注明对应版本和实际检查结果。未执行或未验证的项目如实说明，不把历史通过写成当前验证。
