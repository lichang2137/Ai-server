# Crypto Support MVP

加密平台 AI 客服助手 — AI Customer Service Agent for OKX / Binance.

## 项目概述

面向加密交易平台用户的"安全型客服 Agent"，核心能力：
- 知识问答（帮助中心/公告/规则/参数）
- 状态查询（KYB/充值/提现/钱包状态）
- 问题诊断（充值未到账/提现卡住/KYC失败）
- 操作引导（补材料/查进度/提交工单）

**不做：** 交易执行 / 账户权限修改 / 投资建议

## 目录结构

```
ai-customer-service/
├── docs/                   # 产品文档
│   ├── PRODUCT_OVERVIEW.md       # 产品定位
│   ├── SCENARIO_FLOWS.md        # 场景流程
│   ├── TOOLS_SPEC.md            # 工具协议
│   ├── SUPPORT_AGENT_PROMPT.md   # Agent System Prompt
│   ├── FAQ_AND_KB_SOURCES.md    # 知识库来源
│   └── DATA_INTEGRATION.md      # 真实数据接入指南
├── data/mock/               # Mock 数据（Phase 1）
│   ├── kyb_status.json           # KYB 状态
│   ├── withdraw_status.json      # 提现状态
│   ├── deposit_status.json       # 充值状态
│   ├── wallet_status.json        # 钱包/网络状态
│   └── announcements.json        # 公告
├── scripts/
│   └── mock_tools.py            # 工具 CLI（10个工具）
└── SPEC.md                  # 项目规格书
```

## 快速测试

```bash
# 查 KYB 状态
python3 scripts/mock_tools.py get_kyb_status --user_id uid_10002

# 查提现状态
python3 scripts/mock_tools.py get_withdraw_status --user_id uid_10001 --asset USDT

# 查充值状态
python3 scripts/mock_tools.py get_deposit_status --user_id uid_10003 --asset USDT

# 查钱包/网络状态
python3 scripts/mock_tools.py get_wallet_network_status --asset ATOM --network Cosmos

# 查币链参数
python3 scripts/mock_tools.py params_search_assets --asset USDT --network TRC20
```

## Mock 用户 UID

| UID | 场景 |
|-----|------|
| uid_10001 | KYB 已通过，正常充提记录 |
| uid_10002 | KYB 材料缺失（缺公司注册证明 + 地址证明过期） |
| uid_10003 | 充值 Memo 缺失，提现失败（网络错误） |
| uid_10004 | KYB 被拒（公司名称不一致），提现风控审核中 |

## Agent 调用

OpenClaw Agent ID: `customer`
绑定群: `oc_e1f960d3f17f6c2e0f2057c723dbc7d0`

在绑定群内 @mention 机器人即可触发客服助手。
