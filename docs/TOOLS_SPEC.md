# AI 客服助手 - 工具协议规范

## 概述

工具分三类：
- **知识工具**：检索帮助中心、公告、规则、参数库
- **状态工具**：查询 KYB/充值/提现/钱包/工单状态
- **交互工具**：生成工单摘要、触发人工升级

所有工具返回字段均为**内部字段**，由 Agent 翻译成用户语言后输出，不直接暴露给用户。

---

## 一、知识工具

### 1.1 docs_search_helpcenter

检索帮助中心文档。

**输入参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 自然语言搜索词 |
| platform | string | 否 | okx / binance（默认全部） |
| category | string | 否 | account / deposit / withdraw / kyc / fee |
| limit | int | 否 | 返回数量，默认 3 |

**返回：**
```json
{
  "docs": [
    {
      "title": "帮助中心文章标题",
      "url": "https://...",
      "snippet": "相关段落",
      "platform": "okx",
      "category": "withdraw",
      "updated_at": "2026-01-15"
    }
  ]
}
```

---

### 1.2 docs_search_announcements

检索公告（上下币、钱包维护、活动规则变更）。

**输入参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 搜索词（币种/网络/事件） |
| platform | string | 否 | okx / binance |
| type | string | 否 | wallet_maintenance / listing / delisting / fee_change |
| date_from | string | 否 | YYYY-MM-DD |
| date_to | string | 否 | YYYY-MM-DD |
| limit | int | 否 | 默认 5 |

**返回：**
```json
{
  "announcements": [
    {
      "title": "公告标题",
      "content": "公告摘要",
      "url": "https://...",
      "platform": "binance",
      "type": "wallet_maintenance",
      "published_at": "2026-03-20",
      "effective_at": "2026-03-21T08:00:00Z",
      "recovery_at": "2026-03-21T12:00:00Z"
    }
  ]
}
```

---

### 1.3 params_search_assets

查询币链参数（最小充值量、最小提币量、确认数、Memo 要求等）。

**输入参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| asset | string | 是 | 币种符号，如 USDT / BTC |
| network | string | 否 | 网络，如 TRC20 / ERC20 |
| platform | string | 否 | okx / binance |

**返回：**
```json
{
  "asset_params": {
    "asset": "USDT",
    "network": "TRC20",
    "platform": "okx",
    "min_deposit": "1",
    "min_withdraw": "10",
    "deposit_confirmations": "1",
    "withdraw_confirmations": "1",
    "memo_required": false,
    "tag_required": false,
    "withdraw_fee": "1",
    "deposit_enabled": true,
    "withdraw_enabled": true,
    "updated_at": "2026-03-01"
  }
}
```

---

## 二、状态工具

### 2.1 get_kyb_status

查询用户 KYB/KYC 认证状态。

**输入参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 用户 UID |

**返回：**
```json
{
  "kyb_status": {
    "user_id": "uid_123456",
    "platform": "okx",
    "current_status": "material_missing",
    "submitted_at": "2026-03-20T10:00:00Z",
    "reviewed_at": null,
    "rejection_reason": null,
    "items": [
      {
        "doc_type": "business_license",
        "status": "approved",
        "submitted_url": "https://...",
        "submitted_at": "2026-03-20"
      },
      {
        "doc_type": "address_proof",
        "status": "rejected",
        "submitted_url": "https://...",
        "submitted_at": "2026-03-20",
        "rejection_reason": "文件过期，请提供90天内有效版本",
        "rejection_code": "DOC_EXPIRED"
      },
      {
        "doc_type": "incorporation_cert",
        "status": "missing",
        "submitted_url": null,
        "submitted_at": null
      }
    ],
    "next_action": "请补充地址证明（有效期内）和公司注册证明",
    "estimated_review_time": "1-3个工作日"
  }
}
```

**status 状态枚举：**
- `pending_review` — 等待审核
- `material_missing` — 材料缺失
- `in_review` — 审核中
- `approved` — 已通过
- `rejected` — 已拒绝（需看 rejection_reason）
- `expired` — 已过期

---

### 2.2 get_withdraw_status

查询用户提现单状态。

**输入参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 用户 UID |
| asset | string | 否 | 币种（如不填则返回最近 5 笔） |
| network | string | 否 | 网络 |
| limit | int | 否 | 返回数量，默认 5 |

**返回：**
```json
{
  "withdrawals": [
    {
      "order_id": "wd_8827391823",
      "asset": "USDT",
      "network": "TRC20",
      "amount": "1000",
      "fee": "1",
      "to_address": "TJY.../0x...",
      "submit_time": "2026-03-25T22:00:00Z",
      "internal_status": "broadcasted",
      "internal_status_desc": "已广播，待链上确认",
      "txid": "abc123...def456",
      "chain_status": "confirming",
      "confirmations": 5,
      "required_confirmations": 20,
      "risk_review_status": "passed",
      "last_update_time": "2026-03-25T23:40:00Z",
      "failure_reason": null
    }
  ]
}
```

**internal_status 枚举：**
- `pending` — 等待平台处理
- `risk_review` — 风控审核中
- `approved` — 已通过审核
- `broadcasted` — 已广播，等待链上确认
- `confirming` — 链上确认中
- `completed` — 已完成（对方平台已入账）
- `failed` — 失败（见 failure_reason）
- `cancelled` — 用户取消

---

### 2.3 get_deposit_status

查询用户充值状态。

**输入参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 用户 UID |
| asset | string | 否 | 币种 |
| network | string | 否 | 网络 |
| limit | int | 否 | 默认 5 |

**返回：**
```json
{
  "deposits": [
    {
      "order_id": "dp_8827391824",
      "asset": "USDT",
      "network": "TRC20",
      "amount": "500",
      "from_address": "TJY...",
      "to_address": "TM...",
      "txid": "txid_hash...",
      "submit_time": "2026-03-25T20:00:00Z",
      "chain_confirmations": 3,
      "required_confirmations": 20,
      "credit_status": "pending",
      "credit_status_desc": "链上确认中，平台待入账",
      "memo_required": false,
      "memo_received": null,
      "wallet_maintenance": false,
      "last_update_time": "2026-03-25T23:40:00Z",
      "failure_reason": null
    }
  ]
}
```

**credit_status 枚举：**
- `pending` — 链上确认中
- `credited` — 已入账
- `failed` — 失败（见 failure_reason）
- `memo_missing` — Memo/Tag 缺失

---

### 2.4 get_wallet_network_status

查询币种某网络的充提状态。

**输入参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| asset | string | 是 | 币种，如 USDT |
| network | string | 否 | 网络，如 TRC20（不填则返回该币所有网络） |
| platform | string | 否 | okx / binance |

**返回：**
```json
{
  "wallet_status": {
    "asset": "USDT",
    "network": "TRC20",
    "platform": "okx",
    "deposit_enabled": true,
    "withdraw_enabled": true,
    "maintenance_status": "normal",
    "maintenance_reason": null,
    "estimated_recovery_time": null,
    "notice_url": null,
    "alternative_networks": [
      {"network": "ERC20", "deposit_enabled": true, "withdraw_enabled": true},
      {"network": "Arbitrum", "deposit_enabled": true, "withdraw_enabled": true}
    ],
    "updated_at": "2026-03-26T00:00:00Z"
  }
}
```

---

### 2.5 get_ticket_status

查询工单状态。

**输入参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 用户 UID |
| status | string | 否 | open / pending / resolved / closed |
| limit | int | 否 | 默认 5 |

**返回：**
```json
{
  "tickets": [
    {
      "ticket_id": "TK_8827391",
      "type": "充值未到账",
      "status": "pending",
      "status_desc": "等待补充材料",
      "created_at": "2026-03-24T10:00:00Z",
      "updated_at": "2026-03-25T14:00:00Z",
      "latest_reply": "请提供转出平台的截图和 TXID",
      "missing_info": ["txid", "screenshot"],
      "sla_deadline": "2026-03-27T10:00:00Z"
    }
  ]
}
```

---

## 三、交互工具

### 3.1 create_support_summary

生成结构化工单摘要，供人工客服或工单系统使用。

**输入参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 用户 UID |
| problem_type | string | 是 | deposit_delay / withdraw_delay / kyc_issue / account_limit / other |
| platform | string | 是 | okx / binance |
| asset | string | 否 | 币种 |
| network | string | 否 | 网络 |
| amount | string | 否 | 金额 |
| txid | string | 否 | 交易哈希 |
| order_id | string | 否 | 订单号 |
| diagnosis | string | 是 | AI 诊断结论 |
| evidence | array | 否 | 依据列表（知识库链接/状态字段） |
| user_description | string | 否 | 用户原始描述 |
| attempted_actions | array | 否 | 已尝试的排查动作 |

**返回：**
```json
{
  "summary": {
    "ticket_id": null,
    "user_id": "uid_123456",
    "problem_type": "withdraw_delay",
    "platform": "okx",
    "priority": "medium",
    "asset": "USDT",
    "network": "TRC20",
    "amount": "1000",
    "txid": "abc123",
    "diagnosis": "链上确认数为 5/20，对方平台尚未入账，建议等待",
    "evidence": [
      {"type": "chain_status", "value": "confirming 5/20"},
      {"type": "wallet_status", "value": "提现enabled"}
    ],
    "user_description": "昨晚提了1000 USDT 还没到账",
    "attempted_actions": ["已查询平台状态", "已查询链上状态"],
    "suggested_next_step": "建议等待，如超过24小时链上确认完成仍未到账，提交工单",
    "auto_escalate": false,
    "created_at": "2026-03-26T12:00:00Z"
  }
}
```

### 3.2 escalate_to_human

触发人工升级。

**输入参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| reason | string | 是 | 升级原因 |
| conversation_summary | string | 是 | 对话摘要 |
| user_id | string | 是 | 用户 UID |
| urgency | string | 是 | low / medium / high / critical |

**返回：**
```json
{
  "escalation": {
    "escalation_id": "es_8827391",
    "reason": "高风险账户异常，需人工审核",
    "urgency": "high",
    "assigned_to": "人工客服",
    "estimated_response_time": "30分钟内",
    "user_notified": true
  }
}
```

---

## 四、工具返回错误码约定

| 错误码 | 说明 | Agent 行为 |
|--------|------|-----------|
| TOOL_ERROR_USER_NOT_FOUND | 用户不存在 | 请用户确认 UID |
| TOOL_ERROR_ASSET_NOT_SUPPORTED | 该币种平台不支持 | 说明支持币种列表 |
| TOOL_ERROR_NETWORK_NOT_SUPPORTED | 该网络不支持 | 提供替代网络建议 |
| TOOL_ERROR_KYB_NOT_FOUND | 无 KYB 记录 | 说明可能未提交认证 |
| TOOL_ERROR_ORDER_NOT_FOUND | 找不到对应订单 | 请用户核对订单信息 |
| TOOL_ERROR_MAINTENANCE | 状态接口维护中 | 说明查询范围受限 |
| TOOL_ERROR_RATE_LIMITED | 查询频率超限 | 稍后重试 |
