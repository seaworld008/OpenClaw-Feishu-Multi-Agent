# Open Source Productization Design

## Goal

把仓库从“交付手册集合”升级成“开源项目 + 交付产品”双入口仓库。

## Recommended Direction

采用双入口结构：

1. 开发者入口：快速理解、贡献、验证
2. 交付入口：直接按主线文档落地客户环境

## Design Decisions

1. 使用 `Apache-2.0` 作为默认开源许可证，降低复用摩擦。
2. 保留现有深度交付文档，但在 README 顶部补充更短的开源导航。
3. 增加最小治理文件与 GitHub 模板，提升外部协作体验。
4. 增加最小 CI，确保开源门面改动能被持续验证。
5. 增加 GitHub Topics 建议和 README 关键词，提升搜索可发现性。
