# response.interrupt

状态：`keep`。基线由根 `manifest.json` 固定；本次提取基线为
`f3d8b737b64842df0365c2a6696c276fbc409193`，没有其他补丁依赖。

为 new-api 的持久 Responses WebSocket 连接保留 `response.interrupt` 控制事件，
中断后按已交付输出结算并继续接收下一请求；保留连接历史，隔离旧响应和旧控制错误，
避免其影响新请求。取消路径、结算边界及终态期间中断的原有回归随代码同组维护。

来源是 Ricky-Hao/new-api 的 `16c04caa5b0d8a0f748a247a947d1c6fef68e0ce`
相对上述基线在 `relay/responses_websocket.go`、
`controller/responses_websocket_test.go` 两个文件的完整净差异。
`changes.patch` 用 `git diff --binary --full-index --no-ext-diff --no-renames` 提取，
没有重放 merge 历史，也没有改写实现或测试。

用根 `tools/prepare.sh` 准备正式生成 checkout 后，从维护根执行：

```sh
GOWORK=off GOFLAGS=-timeout=20m python3 tools/patchset.py test --target .work/application
```

完整 Go CI 继续执行应用的 `make test`。本组修改须保留结算和历史隔离合同，
并遵守生成应用 `AGENTS.md`、`.agents/rules/billing.md`。
更新和回写按根 `MAINTENANCE.md` 操作；上游只有在所选固定 base 已包含等价实现及
相应回归后才能替代本组。记录替代提交、行为证据并运行真实回归后才退役载荷。
