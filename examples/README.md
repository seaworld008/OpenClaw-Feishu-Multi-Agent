# Examples

这里放的是最小可复制示例，方便外部开发者和交付团队快速理解这个仓库怎么落地。

适合的使用方式：

- 先从最小示例理解结构
- 再根据自己的群、账号、角色去替换占位值
- 最后回到主线文档完成完整交付

## Included Examples

1. `two-worker-minimal.json`
   - 最小可复制
   - `supervisor + ops + finance`
   - 适合第一次理解 `accounts + roleCatalog + teams`

2. `parallel-three-worker.json`
   - 展示并行 stage + `publishOrder`
   - `ops + finance + legal`
   - 适合验证“多角色并行分析，主管统一收口”

3. `four-worker-decision-rollup.json`
   - 展示 `4` 个 worker 的组合
   - `tech + product + ops + finance`
   - 适合说明 supervisor 决策型终稿并不依赖固定角色

## Notes

- 所有 `appSecret` 都是占位符
- 所有 `peerId` 都是示意值
- 这些示例不是 live 配置，不能直接拿去上生产
