<!--
Sync Impact Report:
Version change: N/A → 1.0.0 (Initial creation)
Modified principles: None (initial)
Added sections: All (initial creation)
Removed sections: None
Templates requiring updates:
  ✅ plan-template.md - Constitution Check section compatible
  ✅ spec-template.md - Requirements alignment compatible
  ✅ tasks-template.md - Task categorization compatible
Follow-up TODOs: None
-->

# FCloudVPN Constitution

## Core Principles

### I. 测试驱动开发 (TDD)

**非协商原则**：所有代码必须先有测试，再实现功能。

- 测试先行：编写测试 → 用户确认 → 测试失败 → 然后实现
- 严格遵循 Red-Green-Refactor 循环
- 单元测试覆盖核心业务逻辑，集成测试覆盖API契约
- 测试覆盖率目标：核心模块 ≥ 80%

**理由**：TDD确保代码可测试性，减少回归缺陷，提高代码质量和可维护性。

### II. 代码审查

所有代码变更必须经过审查才能合并到主分支。

- 每个Pull Request必须至少有一名审查者批准
- 审查重点：代码质量、安全性、性能、测试覆盖
- 审查者必须验证代码符合宪法原则
- 禁止自行批准自己的Pull Request

**理由**：代码审查是知识共享和质量保证的关键环节，能发现单人开发难以察觉的问题。

### III. 文档优先

所有公共API和核心模块必须有完整的文档。

- API文档必须在使用前完成（OpenAPI/Swagger规范）
- 每个模块必须有清晰的README或内联文档
- 文档必须包含：功能描述、使用示例、参数说明、返回值
- 文档更新与代码变更同步进行

**理由**：良好的文档降低学习成本，提高团队协作效率，便于后续维护和扩展。

### IV. 安全合规

安全是所有开发决策的首要考虑因素。

- 所有用户输入必须验证和清理
- 敏感数据必须加密存储和传输
- 认证和授权必须使用经过验证的标准方案
- 安全漏洞修复优先级最高
- 定期进行安全审计和依赖检查

**理由**：VPN服务涉及用户隐私和网络流量，安全漏洞可能导致严重后果。

### V. 效率与完备平衡

在代码执行效率和功能完备之间保持平衡。

- 性能优化必须有基准测试数据支撑
- 避免过早优化，优先保证功能正确性
- 关键路径必须有性能监控和告警
- 技术债务必须记录并定期清理
- 简洁设计优于过度工程

**理由**：过度追求性能可能导致代码复杂度增加，而忽视性能则影响用户体验。平衡是关键。

## 技术约束

### 技术栈要求

- **语言**: 根据项目需求确定（建议：Go/Rust/Python）
- **API框架**: RESTful API，遵循OpenAPI 3.0规范
- **数据库**: 关系型数据库优先（PostgreSQL/MySQL）
- **缓存**: Redis用于会话和热点数据
- **消息队列**: 异步任务处理

### 性能标准

- API响应时间：P95 < 200ms
- 并发连接：支持至少10,000并发连接
- 可用性目标：99.9%

### 部署要求

- 容器化部署（Docker）
- CI/CD自动化流水线
- 环境隔离（开发/测试/生产）

## 开发流程

### 分支策略

- `main`: 生产环境代码，受保护
- `develop`: 开发集成分支
- `feature/*`: 功能开发分支
- `hotfix/*`: 紧急修复分支

### 提交规范

- 使用语义化提交消息（Conventional Commits）
- 格式：`<type>(<scope>): <description>`
- 类型：feat, fix, docs, style, refactor, test, chore

### 发布流程

1. 功能开发完成并通过所有测试
2. 代码审查通过
3. 合并到develop分支
4. 集成测试通过
5. 合并到main分支
6. 自动部署到生产环境

## Governance

本宪法是FCloudVPN项目的最高指导原则，所有开发活动必须遵守。

### 修订流程

1. 提出修订建议并说明理由
2. 团队讨论并达成共识
3. 更新宪法文档
4. 通知所有相关人员
5. 更新相关模板和文档

### 版本控制

- 版本号格式：MAJOR.MINOR.PATCH
- MAJOR：不兼容的原则变更或删除
- MINOR：新增原则或重大扩展
- PATCH：澄清、措辞修正、非语义性改进

### 合规检查

- 每个Pull Request必须验证宪法合规性
- 定期进行宪法合规审计
- 复杂度必须有正当理由并记录

**Version**: 1.0.0 | **Ratified**: 2026-04-17 | **Last Amended**: 2026-04-17
