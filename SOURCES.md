# 来源与许可范围

## new-api 应用

- 上游：[QuantumNous/new-api](https://github.com/QuantumNous/new-api)，完整版本由 `manifest.json` 唯一定义。
- 本次迁移基线：`f3d8b737b64842df0365c2a6696c276fbc409193`，tree `dd27bc10bca5de6ac0e564b2e010bb3177f3968b`。
- 原 fork 源版本：[Ricky-Hao/new-api@16c04caa5b0d8a0f748a247a947d1c6fef68e0ce](https://github.com/Ricky-Hao/new-api/commit/16c04caa5b0d8a0f748a247a947d1c6fef68e0ce)。`response-interrupt` 提取自该版本相对基线的两个业务文件净 diff，包含原回归测试，不重放 merge 历史。
- 初次完整重建的应用 tree：`9e02ac3fa93dd6fac6a43e897077f7134252c7c4`。这是迁移等价性记录，后续行为改动由当前 manifest 和生成结果定义。

迁移时原 fork 的 2677 个文件与生成应用逐文件比较：2673 个共同应用文件的字节和文件模式相同，包含全部业务代码、测试、原始 AGENTS、Dockerfile、锁文件及三个模块和前端的构建输入。只有以下九个维护路径有意不同：

- `.devcontainer/{Dockerfile,devcontainer.json,post-create.sh}` 留在维护根，生成应用使用固定上游树，未注入这些 fork 文件。
- `.github/workflows/ci.yml` 在维护根改为生成后检查/发布；生成应用保留原上游文件。
- 原 fork 删除的 `.github/workflows/{docker-build.yml,docker-image-branch.yml,electron-build.yml,release.yml,sync-release-to-gitcode.yml}` 在生成应用中保留为上游源码，不注册到维护根。

生成应用共有 2679 个文件，相对上游只变更 `relay/responses_websocket.go` 和 `controller/responses_websocket_test.go`。根目录大量应用文件的移出表示由固定 base 重建，未删除应用内的许可、版权、QuantumNous/new-api 名称或归属。

根 `LICENSE`、`NOTICE`、`THIRD-PARTY-LICENSES.md` 保留原文；生成应用也保留各自原文。应用继续使用原 AGPL-3.0 及附加条款，各第三方内容遵循其原许可。

## 维护工具

架构与工具参考固定为 [Ricky-Hao/LibreChat 的 patches 分支 f02d9b1d81a5e61661d69bea05e9278c162a3fd7](https://github.com/Ricky-Hao/LibreChat/tree/f02d9b1d81a5e61661d69bea05e9278c162a3fd7)。阅读了该版本的 README、AGENTS、manifest、maintenance 文档、维护工具/测试及镜像 workflow 后：

- `tools/patchset.py`、`tools/test_patchset.py` 改编其有序清单、选择/依赖闭包、私有索引预检、真实 Git 测试和测试契约实现；扩充独立应用生成、重放核验和整列一次落地，适配 Go/Bun。
- 保留完整 SHA、按能力分组、来源与退役依据；去掉 LibreChat 的 SDK vendoring、Jest/Playwright runner、业务 `--plan` 和本项目无用途的调度。
- 根 CI 保留本 fork 原有已合并发布、readiness 和标签保护合同，并适配生成路径；没有复制 LibreChat 的发布入口或权限。

借用的工具代码版权为 `Copyright (c) 2026 LibreChat`；原 MIT 许可全文位于 `tools/LICENSE.LibreChat`，适用于注明来源的两个 Python 工具文件。它不覆盖或重新许可 QuantumNous/new-api 应用及其补丁。
