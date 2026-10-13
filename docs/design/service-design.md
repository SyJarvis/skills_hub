# Skill Hub 服务化设计

- 状态：初稿
- 范围：将现有 `skills_hub` 仓库演进为可供 CLI、网站、MCP 客户端及其他应用接入的 Skill 分发服务

## 1. 背景与目标

当前仓库以 Git 管理 Skill，提供 `catalog.json`、安装脚本以及校验和文档生成工具。希望在此基础上提供统一服务，使用户能够浏览、搜索、下载和上传 Skill，同时支持终端直接拉取，并为网站和第三方应用保留接入能力。

本设计的核心决策是：**以协议无关的领域核心和 HTTP API 作为服务基础，CLI、网站及 MCP 均作为客户端或适配器。MCP 不作为唯一服务协议。**

### 目标

1. 可发现：通过列表、搜索、详情与版本信息发现 Skill。
2. 可分发：按 Skill 与版本下载完整、可校验的包。
3. 可发布：授权用户上传并发布经过校验的版本。
4. 可接入：TypeScript CLI、网站、MCP 客户端和其他应用共享同一套业务语义。
5. 可演进：存储、传输协议适配器与客户端实现相互解耦。
6. 保持兼容：继续支持现有 Skill 目录结构和本地安装工作流。

### 非目标（首期）

- 构建复杂的组织、团队和计费系统。
- 支持任意执行用户上传的脚本或 Skill 内容。
- 立即实现多租户审核工作流、评分、社交功能或依赖解析。
- 以 MCP 替代 HTTP API，或要求所有客户端使用 TypeScript。

## 2. 用户与使用场景

- **终端用户**：用 npm 安装 CLI，搜索并拉取 Skill 到 Codex、OpenCode 等工具目录。
- **浏览者**：在网站查看 Skill 描述、兼容性、版本和文件内容并下载。
- **作者/维护者**：验证并上传 Skill 包，创建新版本。
- **Agent 客户端**：通过可选 MCP 服务发现 Skill，并读取元数据或下载信息。
- **第三方应用**：直接通过公开 HTTP API 查询和下载，通过受保护 API 发布（经授权）。

## 3. 概念与数据模型

### 3.1 Skill 与版本

Skill 是逻辑条目；每次发布对应一个不可变版本。建议使用 `name` 作为首期唯一标识，名称遵循小写 kebab-case；未来如需组织命名空间，可扩展为 `namespace/name`，避免首期过早引入复杂身份模型。

```text
Skill
- name: string
- description: string
- category: string
- tags: string[]
- compatibility: string[]
- latestVersion: string
- createdAt / updatedAt

SkillVersion
- skillName: string
- version: SemVer
- manifest: Skill 元数据
- archiveUrl 或下载端点
- checksum: SHA-256
- size: integer
- publishedAt: timestamp
```

`SKILL.md` 的 frontmatter 是 Skill 内容的重要来源；服务端校验其存在和格式。目录字段可以由服务端从包内容提取，并与发布清单核对。`catalog.json` 作为现有仓库索引，在迁移期用于导入或生成，不应成为未来所有客户端必须直接读取的协议。

已发布的版本不可原地覆盖。更新必须使用新版本号。删除/撤回应采用状态或软删除策略，保留已有下载可审计性；具体保留政策待产品决策。

### 3.2 Skill 包格式

首期接受 ZIP 包，包内根目录直接包含 `SKILL.md`，及可选的 `references/`、`scripts/`、`assets/`、`tests/`。下载端返回同一规范包，并附 SHA-256、大小和版本信息。服务端应拒绝绝对路径、`..` 路径穿越、重复路径、超限文件和不允许的符号链接；上传和解压限制应可配置。

包格式应与存储后端无关。不要依赖 Git 仓库目录布局作为客户端协议。

## 4. 架构

```text
npm CLI ──────────────┐
网站 / Web 前端 ──────┼── HTTP API ── 应用服务/领域逻辑 ── 元数据存储
第三方应用 ──────────┤                         └────────── Skill 包存储
MCP Adapter（可选）──┘
```

### 4.1 分层职责

- **领域核心**：Skill、版本、校验、发布状态等规则；不依赖 HTTP、MCP 或具体数据库。
- **应用服务**：搜索、读取、上传、发布、下载等用例；定义存储接口并协调校验。
- **HTTP API**：稳定、版本化的通用接口，负责身份认证、参数解析、状态码与序列化。
- **MCP Adapter**：把有限的只读发现能力映射为 MCP tools/resources，调用同一应用服务；不得复制业务规则。
- **CLI**：npm 包，通过 HTTP API 完成发现和下载；本地负责目标路径选择、解包及安装。
- **网站**：HTTP API 客户端，不直接访问数据库或仓库文件。
- **存储适配器**：元数据存储和二进制包存储可独立替换。MVP 可以本地文件系统存包、SQLite/PostgreSQL 存元数据；部署环境与并发需求确认后选择具体组合。

### 4.2 协议与版本策略

HTTP JSON API 是首期公开接口。路径使用 `/api/v1`，响应采用 UTF-8 JSON；下载端点返回 `application/zip`。API schema 以 OpenAPI 文档描述，并作为生成客户端类型和契约测试的依据。业务逻辑不得散落在路由处理器中。

MCP 仅是可选接入适配器；首期可以在 HTTP API 稳定后再实现。它适合 Agent 工具调用，不是网站和通用客户端的必需协议。

## 5. HTTP API 草案

### 5.1 公开只读接口

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/api/v1/skills` | 分页列表；支持 `q`、`category`、`tag`、`compatibility`、`cursor`、`limit` |
| `GET` | `/api/v1/skills/{name}` | Skill 详情及默认版本信息 |
| `GET` | `/api/v1/skills/{name}/versions` | 版本列表 |
| `GET` | `/api/v1/skills/{name}/versions/{version}` | 指定版本元数据、校验和与下载链接 |
| `GET` | `/api/v1/skills/{name}/versions/{version}/download` | 下载 ZIP 包 |

列表响应应提供稳定分页游标和 `nextCursor`，不要依赖客户端遍历整个 catalog。不存在的资源返回 `404`；参数错误返回 `400`；限流返回 `429`。

### 5.2 写接口（需认证）

| 方法 | 路径 | 用途 |
|---|---|---|
| `POST` | `/api/v1/skills` | 创建 Skill 条目或开始首次发布 |
| `POST` | `/api/v1/skills/{name}/versions` | 上传一个新版本包与清单 |

创建与发布的事务语义、是否需要审核、认证提供方尚需确定。首期应只允许授权发布者写入。支持幂等键或明确处理重复请求；版本冲突返回 `409`，校验失败返回 `422`。上传成功后返回版本标识、校验和与状态。

### 5.3 错误格式

错误响应统一包含机器可读 `code`、面向开发者的 `message`、可选 `details` 和请求 `requestId`。不得将堆栈或内部存储路径返回给客户端。

## 6. CLI（npm 包）

包名暂定 `skills-hub`（发布前需检查 npm 名称可用性）。CLI 使用 TypeScript 编写，CLI 与 API 类型可由 OpenAPI 生成或校验。命令草案：

```text
skills-hub search <query> [--category ...]
skills-hub list [--json]
skills-hub info <name> [--version ...]
skills-hub pull <name> [--version ...] [--target codex|opencode|path]
skills-hub push <directory> [--version ...]
```

首期可优先实现 `search`、`info`、`pull`；`push` 在身份认证和发布流程明确后开放。拉取流程：查询版本元数据 → 下载归档 → 校验 SHA-256 → 安全解包到临时目录 → 校验包结构 → 原子移动至目标目录。默认目标规则应提供清晰预览并支持显式路径，避免静默覆盖；覆盖行为需要用户确认或明确的 `--force`。

CLI 应支持 `--json` 供脚本集成；服务 URL 可由 `--registry`、环境变量或默认公共服务配置，不将单一部署地址写死在业务代码中。

## 7. MCP 接入（可选阶段）

建议优先提供只读工具：

- `search_skills(query, filters)`
- `get_skill(name, version?)`
- `get_skill_download_info(name, version?)`

MCP adapter 调用与 HTTP API 相同的应用服务。上传/发布属于高影响写操作，暂不通过匿名 MCP 暴露；若将来支持，必须复用认证授权、审计和校验流程。MCP 工具输出需限制体积；完整文件优先返回下载地址和校验信息，而非把整个包塞进上下文。

## 8. 安全、可靠性与运维

- 上传端进行文件大小、解压后总大小、文件数、路径深度及压缩比限制。
- 防范 ZIP Slip、恶意符号链接、重复文件名、超大文件及资源耗尽。
- 将 Skill 内容视为不可信数据；服务不执行上传脚本，也不把内容当作 HTML 渲染。网站展示 Markdown 时必须安全消毒。
- 发布 API 使用认证和授权；写操作记录发布者、版本、时间和校验结果。凭证不得写入日志。
- 下载使用不可变版本地址和 SHA-256 校验；包文件名和响应头应安全处理。
- 公开查询接口设置合理的分页上限与速率限制；错误日志不泄漏秘密。
- 定义健康检查、结构化日志、请求 ID、备份与恢复策略。上传成功但元数据提交失败等部分失败应有明确清理/恢复机制。

## 9. 技术实现建议

- 语言：TypeScript。
- 运行时/HTTP 框架：保持可替换，首期选成熟、支持 schema 校验的轻量框架；框架选择不进入领域层。
- 包管理与 workspace：monorepo 可划分 `packages/core`、`packages/api`、`packages/cli`、后续 `packages/mcp`；初期若仓库体量小，也可采用单包内清晰模块，避免为了架构而过度拆分。
- API schema：OpenAPI 3.x；请求与响应运行时校验。
- 持久化：抽象元数据与包存储接口。开发环境使用本地存储；生产环境根据托管需求采用关系型数据库与对象存储。
- 测试：领域单元测试、API 集成测试、包安全校验测试、CLI 端到端测试及 OpenAPI 契约检查。

本节是技术方向，不锁定具体框架、数据库、认证供应商或云厂商；这些选择应在部署环境和产品需求明确后决定。

## 10. 迁移与阶段计划

### 阶段 0：契约与规范

- 确认 Skill 标识、SemVer 规则、ZIP 包格式、元数据来源与错误格式。
- 编写 OpenAPI 草案和包校验规则。
- 从现有 `skills/` 导入样本，检查兼容性与命名冲突。

### 阶段 1：只读 Registry MVP

- 实现列表、搜索、详情、版本和 ZIP 下载 API。
- 导入现有 Skill 与 catalog 元数据，生成不可变版本记录和校验和。
- 实现 TypeScript CLI 的 `search`、`info`、`pull`。
- 提供最小网站浏览/下载界面；网站与 CLI 共用 API。

### 阶段 2：受控发布

- 增加认证、授权上传、服务端校验、版本不可变性和审计。
- 实现 CLI `push` 与网站发布界面。
- 决定审核、撤回和账号模型。

### 阶段 3：扩展接入

- 实现可选 MCP adapter。
- 根据使用量评估缓存、对象存储、搜索能力及更多兼容客户端。

每一阶段应可独立部署和验证，不要求一次完成所有客户端。

## 11. 验收标准（MVP）

1. 客户端可通过 API 分页浏览、搜索和读取版本元数据。
2. 下载指定版本得到确定的 ZIP 包，SHA-256 一致。
3. CLI 可查询并将包安全安装到显式目标目录；校验失败不留下半成品。
4. HTTP API 不依赖具体前端，OpenAPI 描述可用于契约验证。
5. 非授权客户端不能上传；非法或危险包被拒绝并返回结构化错误。
6. 从现有仓库导入的 Skills 可按规范读取，原有本地 `install.sh` 在迁移阶段继续可用。

## 12. 待确认事项

- 服务是个人/局域网实例还是公网托管服务？
- 是否需要登录账号，首期发布者如何授权？
- 上传后立即发布还是审核后发布？
- Skill 名称是否全局唯一，是否需要组织命名空间？
- 目标客户端的默认安装路径和覆盖策略是什么？
- 首期部署环境、数据库与文件存储选型是什么？
- 公开服务是否需要下载统计、撤回策略与内容审核？
