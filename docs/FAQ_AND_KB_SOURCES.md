# AI 客服助手 - 知识库与数据源

## 一、知识库来源

### 1.1 帮助中心文档

| 平台 | 来源 URL | 内容范围 |
|------|---------|---------|
| OKX | https://www.okx.com/zh-hans/help |
| Binance | https://www.binance.com/zh-CN/support |

**文档分类：**
- 账户与认证（注册/登录/2FA/实名认证/企业认证）
- 充值提现（充值/提现规则/状态说明）
- 交易相关（现货/合约/杠杆费率）
- 理财与结构化产品
- 费率说明（Maker/Taker/充值/提现手续费）
- API 使用说明
- 安全与防诈骗

**字段规范：**
```json
{
  "title": "文章标题",
  "url": "原始链接",
  "platform": "okx | binance",
  "category": "account | deposit | withdraw | fee | api | security | kyc",
  "tags": ["trc20", "usdt", "充值"],
  "content": "正文内容（清洗后）",
  "last_updated": "2026-01-15",
  "status": "active | deprecated"
}
```

---

### 1.2 公告数据

**公告类型：**
- 钱包维护（钱包维护通知，标注起止时间）
- 上下币（新增币种/交易对上线/暂停交易）
- 费率变更（手续费调整/新增费用类型）
- 产品变更（新功能上线/功能调整/下线）
- 安全公告（系统异常/风险提示）
- 活动规则（参与条件/奖励规则变更）

**字段规范：**
```json
{
  "title": "公告标题",
  "url": "公告链接",
  "platform": "okx | binance",
  "type": "wallet_maintenance | listing | delisting | fee_change | product_change | security | campaign",
  "published_at": "2026-03-20T08:00:00Z",
  "effective_at": "2026-03-21T00:00:00Z",
  "recovery_at": "2026-03-21T12:00:00Z",
  "affected_assets": ["USDT", "BTC"],
  "affected_networks": ["TRC20", "ERC20"],
  "content_summary": "公告摘要"
}
```

---

### 1.3 币链参数库

**核心参数：**

| 参数 | 说明 | 示例 |
|------|------|------|
| min_deposit | 最小充值量 | 0.001 ETH |
| min_withdraw | 最小提币量 | 0.01 ETH |
| deposit_confirmations | 充值确认数要求 | 20 |
| withdraw_confirmations | 提现确认数要求 | 20 |
| memo_required | 是否需要 Memo | true / false |
| tag_required | 是否需要 Tag | true / false |
| deposit_enabled | 充值是否开放 | true / false |
| withdraw_enabled | 提现是否开放 | true / false |
| withdraw_fee | 提现手续费 | "1 USDT" |
| network | 网络名 | "TRC20" / "ERC20" / "Arbitrum" |

**来源方式：**
- 优先从 OKX/Binance 公开 API 获取（见下方接口）
- 备份：帮助中心页面抓取
- 钱包维护期间参数可能变更，以公告为准

---

### 1.4 KYC/KYB 规则库

**KYC 资料要求（个人）：**
- 证件类型（身份证/护照）
- 证件要求（正反面/有效期）
- 人脸认证要求
- 地址证明要求（如有）
- 审核时长

**KYB 资料要求（企业）：**
- 公司注册证明
- 商业许可证
- 法人身份证
- 地址证明
- 受益人声明
- 授权书（如有）
- 审核时长

**状态枚举：**
`pending_review | material_missing | in_review | approved | rejected | expired`

---

### 1.5 故障排障库（FAQ）

| 场景 | 问题类型 | 常见原因 |
|------|---------|---------|
| 充值未到账 | confirmations 不足 | 等待链上确认 |
| 充值未到账 | Memo 缺失 | 需补工单 |
| 充值未到账 | 金额低于最低限额 | 低于最低充值门槛 |
| 充值未到账 | 钱包维护 | 等待恢复 |
| 充值未到账 | 网络选错 | 地址和网络不匹配 |
| 提现未到账 | 平台审核中 | pending / risk_review |
| 提现未到账 | 链上确认中 | 等待确认 |
| 提现未到账 | 目标地址错误 | TXID 对方链查不到 |
| KYC 被拒 | 材料过期 | 需重新提交有效期内材料 |
| KYC 被拒 | 材料不清晰 | 重新拍摄/上传 |
| KYC 被拒 | 主体不一致 | 企业名称与证件不符 |

---

## 二、状态接口来源

### 2.1 真实平台 API（第二阶段）

**OKX 公开 API（无需认证）：**
- 币种/网络充提状态：GET `/api/v5/asset/currencies`
- 充值状态查询：GET `/api/v5/asset/deposit-history`（需 API Key）
- 提现状态查询：GET `/api/v5/asset/withdrawal-history`（需 API Key）
- 费率查询：GET `/api/v5/account/trade-fee`

**OKX 状态页（公开）：**
- 系统状态：https://www.okx.com/zh-hans/help-center/section/notice

**Binance 公开 API：**
- 币种信息：GET `/api/v3/exchangeInfo`
- 充值状态：GET `/api/v3/depositHistory`（需 API Key）
- 提现状态：GET `/api/v3/withdrawHistory`（需 API Key）
- 系统状态：https://binance.statuspage.io

### 2.2 Demo 阶段 Mock 方案

第一阶段使用半结构化 Mock 数据，格式与 TOOLS_SPEC.md 中的返回完全一致。

**Mock 数据文件：**
```
data/
  mock/
    kyb_status.json       # KYB 状态 Mock
    withdraw_status.json  # 提现状态 Mock
    deposit_status.json   # 充值状态 Mock
    wallet_status.json    # 钱包/网络状态 Mock
    announcements.json    # 公告 Mock
```

**Mock 数据注入规则：**
- `is_mock: true` 标记所有模拟数据
- 覆盖 3 个主流币种（BTC/USDT/ETH）× 3 种主要网络（对于 USDT：TRC20/ERC20/Arbitrum）
- 覆盖 2 个平台（OKX/Binance）
- 每类状态至少覆盖 2 个正常 case + 1 个异常 case

---

## 三、知识库更新机制

| 数据类型 | 更新频率 | 更新方式 |
|---------|---------|---------|
| 帮助中心规则 | 月度 | 人工比对+告警 |
| 公告数据 | 实时 | 公告发布时同步 |
| 币链参数 | 周度 | 官方 API 拉取+人工确认 |
| KYB/KYC 规则 | 季度 | 人工review |
| 故障排障库 | 按场景 | 每次新问题出现时补充 |

---

## 四、知识库质量标准

**回答来源召回率：**
- 用户问题 80% 以上必须能召回相关文档/公告
- 无召回时必须明确告知用户"当前未查到"

**回答引用规范：**
- 每条回答必须附知识库来源（URL 或公告标题）
- 参数类回答必须附最新更新时间

**禁止：**
- 不引用已 deprecated 的规则
- 不引用超过 6 个月未更新的帮助中心内容（需标注"该内容可能已过期"）
