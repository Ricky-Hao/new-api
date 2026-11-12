# 补丁维护

## 固定版本和应用边界

`manifest.json` 中的 `upstream`、完整 40 位 `base` 和 `patches` 数组共同定义应用源码，`application.ref/branch` 定义准确来源和应用分支。按数组顺序应用，每项只登记一次；不要再通过目录扫描、编号文件名或另一份列表定义顺序。维护 `main` 只保留补丁、工具、CI、Devcontainer 和必要说明/许可，不 merge 上游应用树到 main。

正式准备、CI 和复现入口为：

```bash
python3 tools/patchset.py branch --target .work/application
python3 tools/patchset.py verify --target .work/application
```

`branch` 在临时 clone 中核实 ref/base 并完整预检，成功后才在维护仓建立真实应用分支和 linked worktree。每个有效补丁按清单顺序生成独立实现提交，最后的维护提交记录上游 URL/ref/base、规范化 manifest 和有序补丁内容的 SHA-256 指纹、原补丁 tree 与 workflow 归档策略。提交使用固定生成器身份和 base 的时间，相同输入得到相同 commit/tree，不读取或修改用户 Git 身份。未提交的维护输入也能本地预览；发布必须从精确的已合并维护 SHA 重建。

应用分支保留完整上游历史和源码；原 `.github/workflows/` 文件原样移到 `.github/upstream-workflows/`，保留内容、模式和来源，同时避免该分支成为额外 Actions 入口。根 CI、开发环境和这项归档由维护层负责，不另立业务补丁。

命名只有两种准确来源，工具会验证：

- release：`application.ref` 为 `refs/tags/vX.Y.Z`（允许预发布后缀），tag 必须精确指向 `base`，`application.branch` 使用该版本名。
- 非 release：`application.ref` 为完整 base SHA，分支名为 `upstream-<base 前九位>`。首次迁移的 base 不属于 release，使用 `upstream-f3d8b737b`，不能把最近的 `v1.0.0-rc.49` 当作来源。

release 生成会将已校验的所选 tag 原样导入维护仓的共享 Git refs，供应用 worktree 后续离线 `branch/verify/test` 和准备末尾核验使用；annotated 与 lightweight tag 均支持，不导入其他上游 tags。同名 tag 对象不一致时直接拒绝，不覆盖原 tag，也不创建应用分支。后续核验仍要求 tag 存在且精确对应 base；缺失或被移动时应先查明来源，不跳过校验。

应用分支保持为不可覆盖的版本快照。同一上游版本修改补丁或清单时，保留 `ref/base`，将分支改为尚未使用的 `-patchset-N` 版本（N 从 2 开始），例如 `v1.2.3-patchset-2`；同步新上游则建立该新版本的分支。工具只复用提交完全相同的已有分支，拒绝覆盖已有分支、用户提交或修改，也不接管旧 detached checkout。

`generate` 仍用于补丁研究：它在独立 clone 中先完整 `check`、再 `apply`，成功后移到目标位置，保留 base HEAD 和已暂存补丁，不生成版本分支。`--only/--status` 选择只用于这些临时 checkout；`branch` 始终要求完整清单。也可对已有的干净 base checkout 使用：

```bash
python3 tools/patchset.py check --target .work/clean-application
python3 tools/patchset.py apply --target .work/clean-application
```

两者都要求目标是独立 Git checkout 根，`HEAD` 精确等于 base，且索引、工作树和非忽略的新文件均干净。预检使用私有索引完整试应用选定序列，后序失败不会落地前序补丁。正式落地把预检结果合并为一次 `git apply --index`。重复 apply 会拒绝；应使用新 checkout。`check` 不修改应用工作树或索引，可能在应用 Git 对象库写入预检树。

`verify` 在应用分支要求正确分支名、精确的重建提交和干净工作树；在研究 checkout 要求索引与补丁重放树一致。两者均允许忽略的依赖与构建产物。`branch/generate` 遇到已有目录只核验，不更新它。清单变化或源码未回写会明确失败；先保留原目录，再生成新目录，不用 reset/clean 覆盖工作。linked worktree 要用 `git worktree move` 移动；旧版独立 clone 可整体改名保留。

## 分组、顺序和实际依赖

一项能力拥有一组 diff，代码、回归测试和必要应用文档放在同组。每个改动只属于一个组，不把同一改动复制到多个 diff；共享文件的不同改动可以分组，但要审清各自 hunk，并在确实依赖前组实现或上下文时登记依赖。

`depends_on` 只能引用更早的 id，表示实际功能或应用依赖，不为方便排序添加虚假依赖。例如 `b` 需要 `a`，`c` 独立：

```json
[
  {"id": "a", "depends_on": []},
  {"id": "b", "depends_on": ["a"]},
  {"id": "c", "depends_on": []}
]
```

上例只展示顺序字段。完整项还需要 `status`、`patch`、`paths`、`tests`，以当前 manifest 为例。`--only b` 自动包含 `a`，按清单顺序各应用一次，不包含独立的 `c`；`--status local` 同样包含被选项的传递依赖。选择操作适用于隔离研究，发布和 CI 始终使用完整清单。

每组包含：

- `changes.patch`：标准 Git diff，可包含 binary diff，保留正常上下文和完整 blob id。
- `README.md`：能力、上游或原 fork 来源、保留原因、真实依赖和验证方式。
- `tests.json`：非空 `checks` 数组；每项定义 `name`、`tier`（`focused` 或 `project`）、应用相对 `cwd`、必须存在的应用文件 `requires` 和直接执行的 `command` 参数数组。

`paths` 必须精确覆盖该 diff 涉及的文件；新增测试也登记在内。`test` 先 verify，再从应用目录真实执行选定契约。命令失败、入口文件缺失和所选 tier 没有检查均报错；完全相同的契约只执行一次。它不安装依赖，也不把计划打印视为业务验证。

## 增加一组补丁

先生成完整应用分支，读应用规则，确认新能力在当前完整序列之后实现。另建编辑分支，保留已生成快照：

```bash
python3 tools/patchset.py branch --target .work/application
application_branch=$(python3 -c 'import json; print(json.load(open("manifest.json"))["application"]["branch"])')
git worktree add -b edit/new-capability .work/edit-new-capability "$application_branch"
before_tree=$(git -C .work/edit-new-capability rev-parse 'HEAD^{tree}')
```

在其中实现并验证，只暂存本组代码、测试和必要文档。然后导出相对于 `before_tree` 的本组增量，重定向的文件须位于维护根：

```bash
mkdir -p patches/new-capability
git -C .work/edit-new-capability add -- path/to/code path/to/test
git -C .work/edit-new-capability diff --cached --binary --full-index --no-ext-diff --no-renames "$before_tree" -- path/to/code path/to/test > patches/new-capability/changes.patch
```

补齐组 README 和测试契约，向 manifest 追加完整条目；仅填真实依赖，并选择新的应用快照分支名。检查 diff 不含其他组已存在的改动、workflow 归档、密钥、运行数据或构建产物。随后按下面的完整重放和检查流程验收。编辑分支可以保留开发提交，但其实现只有回写 patch 后才进入交付来源。

## 修改或回写已有补丁

不能在叠加了后续组的源码上直接对 base 导出整组，否则会混入其他能力。为第 k 组建立干净 base checkout，先通过工具应用其**全部前序组**（不是只选该组的依赖），记录前序 tree，再应用并编辑第 k 组：

```bash
base=$(python3 -c 'import json; print(json.load(open("manifest.json"))["base"])')
git clone --no-hardlinks .work/application .work/edit-response-interrupt
git -C .work/edit-response-interrupt checkout --detach "$base"
# 第 1 组没有前序；其他组在这里执行 apply --only <全部前序 id>
before_tree=$(git -C .work/edit-response-interrupt write-tree)
git -C .work/edit-response-interrupt apply --index --binary "$PWD/patches/response-interrupt/changes.patch"
```

在编辑目录读规则、修改并暂存本组文件。对 `before_tree` 导出完整替换 diff，先写临时文件再替换，避免失败时截断原补丁：

```bash
git -C .work/edit-response-interrupt add -- relay/responses_websocket.go controller/responses_websocket_test.go
git -C .work/edit-response-interrupt diff --cached --binary --full-index --no-ext-diff --no-renames "$before_tree" -- relay/responses_websocket.go controller/responses_websocket_test.go > patches/response-interrupt/changes.patch.next
mv patches/response-interrupt/changes.patch.next patches/response-interrupt/changes.patch
```

其他组替换为各自 id 和完整文件范围；新增文件同步更新 `paths`。从日常应用分支的编辑分支回写时，将尚未回写的改动按所属组带入对应编辑 checkout，仍按上述相邻 tree 导出，不复制整棵应用树。必要时逐组刷新后续 diff，保留每个改动的单一归属。

回写后更新 manifest 中的应用快照分支名，保留旧应用 worktree，再从清单完整生成新分支，检查与预期一致；不要把编辑 checkout 的暂存区当作已交付的维护补丁。日常 `.work/application` 的更新可使用：

```bash
git worktree move .work/application .work/application-before-refresh
python3 tools/patchset.py branch --target .work/application --source .work/application-before-refresh
bash tools/prepare.sh
```

使用尚未占用的备份目录名。离线 source 只提供 Git 对象，未提交修改不会被 clone；必须先把所需修改写回 patch。

## 退役或更新上游

保留中的状态为 `keep`、`feature`、`local`、`awaiting-upstream`，都实际应用。上游已实现或其他已包含提交替代时，条目改为 `upstream` 或 `replaced`，设 `patch: null`、`paths: []`，补充 `replacement.commit`（完整 SHA）与 `replacement.evidence`（具体来源及语义等价依据），删除失效 diff，保留 README 和有效的等价回归契约。工具会要求替代提交是当前固定 base 的祖先；仅有 PR 链接或未来提交不能跳过补丁。上游未包含等价回归时，应继续保留需要的测试补丁及其明确归属。

如果主动放弃一项能力，移除清单项和整组文件，处理引用它的依赖，并在变更说明解释行为变化；不能把没有替代实现的能力标记为已上游化。

更新上游是显式的独立维护变更：

1. 在应用对象仓获取并核实候选上游完整提交，阅读上游变更、许可和新规则；不 merge 上游应用树到维护 main。
2. 修改 manifest 的 base 和 `application.ref/branch`。选 release 时核实准确 tag 的提交，不用最近 tag 或浮动 main 代替；非 release 用完整 SHA。按顺序检查每组的保留、上游化或替代依据，冲突在对应组编辑 checkout 解决并重新导出，不在生成工具中加自动修复。
3. 在新目标从新 base 完整 check/apply，再用 `branch` 生成新的完整应用分支，保留以前的版本。清单之外不要再硬编码一个可漂移的 base；保留来源文档中的初次迁移历史记录。
4. 从新应用 worktree 运行全部项目检查和受影响回归；依赖、数据库、计费和认证变化遵守应用 AGENTS 的额外要求。审阅生成提交、净差异和每组归属后交付维护仓改动。

## 验证和发布边界

维护工具改动先运行：

```bash
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/patchset.py verify --target .work/application
GOWORK=off GOFLAGS=-timeout=20m python3 tools/patchset.py test --target .work/application
```

准备好依赖和 `web/dist` 后，三个模块分别运行 `GOWORK=off go vet ./...`、`GOWORK=off go build ./...`；应用根运行 `GOWORK=off GOFLAGS=-timeout=20m make test`，`web/` 运行 `bun check -b`、`bun run test`、`bun run build`。所有路径均相对生成应用，根维护仓没有 `go.mod` 或 `web/`。资源有限时按阶段串行。

独立重建须在另一维护 clone 从同一维护 SHA 运行 `branch`，核对 base/branch/commit/tree；同一仓库不能同时检出同一个应用分支。临时研究 checkout 可继续用 `generate --target .work/replay` 验证原始完整 check/apply 路径。

根 `git diff --check` 检查维护文本。`.gitattributes` 仅对原始 `*.patch` 关闭换行转换和外层 whitespace 检查，以保留 diff 空白上下文；实际应用分支差异另用 `git -C .work/application diff --find-renames --check "$base" HEAD` 检查。研究 checkout 使用 `diff --cached --check`。不能通过重排原 patch 字节掩盖源差异。

CI 的后端保留 `make test` 与 `GOFLAGS=-timeout=20m`；前端保留真实类型检查和测试。维护生成 job 输出 base/branch/commit/tree，其他检查与镜像 job 比较同一精确维护 SHA 重建的全部结果。应用分支没有活动 `.github/workflows/`，原上游文件在非活动归档目录中保留；该分支 push/tag/manual 不构成镜像发布入口。

镜像只在 PR 实际合并 main 的 closed 事件、该真实 merge SHA 的全部检查成功后发布。发布步骤在比对应用 commit/tree 后只写入 `VERSION`，使用应用原 Dockerfile 和 `.dockerignore`；镜像标签区分维护合并 SHA、固定上游 base、应用 branch/commit/tree，tree 记录版本写入前的源码。保留一次 build/load、两分钟有限重试且含 `--retry-all-errors` 的 readiness、`jq -s` 严格单 JSON `success=true` 校验，以及就绪后才登录/推送的顺序。不得增加发布入口、扩大 token 权限或恢复 `type=gha` 镜像缓存。

CI 不推 Git 分支，保留 `contents: read`。维护变更合并并检查成功后，由负责人发布应用快照：

1. 在独立维护 clone 检出该次精确合并 SHA，执行正式 `branch` 和 `verify`，核对与该 SHA 的 CI 输出 branch/commit/tree 完全相同。不要从仍有未提交维护修改的目录发布。
2. 核实远端同名分支不存在；若已经是相同 commit，无需再推；若不同，保留原分支，先查明来源或提交新的快照名，不覆盖它。
3. 在明确授权发布后，仅推应用分支，例如 `git push origin "refs/heads/$application_branch:refs/heads/$application_branch"`。不使用 force，不推上游 tags。这个分支保留完整可浏览源码及实现提交；镜像仍只来自对应维护合并 SHA 的检查流程。

workflow 自查使用可用的 actionlint。若使用 1.7.12，它尚不认识 `concurrency.queue: max`，只可在临时 lint 输入中去掉这一字段；源文件保留串行队列约定，并单独核实该字段。静态检查不代替真实远端发布和 Devcontainer 生命周期验证。
