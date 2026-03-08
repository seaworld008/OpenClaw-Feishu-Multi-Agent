# Default Expert Catalog Design

**Goal:** 在 README 中沉淀一套可直接复用的默认专家库，供多群配置时快速选择英文专家名称与中文职责描述。

## Design

- 章节名称固定为 `默认专家库 / Default Expert Catalog`
- 分类标题使用中英双语
- 专家名称使用英文，便于直接复用到 `agentId / roleKey / role seed`
- 专家描述使用中文，便于交付与业务人员快速理解
- 总量固定为 `30` 个，按 `10` 个分类、每类 `3` 个专家组织

## Why README

- 用户打开仓库首页就能看到
- 适合作为交付现场的参考词典
- 不引入新的 schema，也不影响当前 `V5.1 Hardening` 协议
