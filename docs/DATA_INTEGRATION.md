# AI 客服助手 - 数据处理与真实数据接入指南

## 一、数据架构

```
数据层
├── Mock 数据（Phase 1）
│   └── data/mock/*.json          ← 本地 JSON，人工维护
│
└── 真实数据（Phase 2）
    ├── OKX 公开 API              ← 无需认证，币种/公告/参数
    ├── OKX 账户 API（需 Key）    ← 充提状态/KYB 状态
    ├── Binance 公开 API          ← 同上
    └── Binance 账户 API（需 Key）  ← 同上
```

---

## 二、Mock 数据使用方式

所有工具调用通过 `scripts/mock_tools.py` 统一出口：

```bash
# 查 KYB 状态
python3 scripts/mock_tools.py get_kyb_status --user_id uid_10002

# 查提现状态
python3 scripts/mock_tools.py get_withdraw_status --user_id uid_10001 --asset USDT

# 查充值状态
python3 scripts/mock_tools.py get_deposit_status --user_id uid_10003 --asset USDT

# 查钱包/网络状态
python3 scripts/mock_tools.py get_wallet_network_status --asset ATOM --network Cosmos

# 检索帮助中心
python3 scripts/mock_tools.py docs_search_helpcenter --query "充值未到账"

# 检索公告
python3 scripts/mock_tools.py docs_search_announcements --query USDT

# 查币链参数
python3 scripts/mock_tools.py params_search_assets --asset USDT --network TRC20

# 生成工单摘要
python3 scripts/mock_tools.py create_support_summary \
  --user_id uid_10003 \
  --problem_type deposit_delay \
  --platform okx \
  --diagnosis "Memo缺失" \
  --asset USDT --network TRC20 \
  --txid "txid_no_memo_abc999bbb"
```

---

## 三、Mock 用户 UID 清单（Demo 用）

| UID | 场景 |
|-----|------|
| uid_10001 | KYB 已通过 / 有正常提现记录 / 有正常充值记录 |
| uid_10002 | KYB 材料缺失（缺公司注册证明 + 地址证明过期） |
| uid_10003 | 充值 Memo 缺失导致未入账 / 提现失败（网络错误） |
| uid_10004 | KYB 被拒（公司名称不一致）/ 提现风控审核中 / 充值金额低于最低限额 |

---

## 四、真实数据接入（Phase 2）

### 4.1 OKX 公开 API（无需认证）

```python
import requests

# 币种/网络充提状态
def okx_get_currency_info():
    resp = requests.get(
        "https://www.okx.com/api/v5/asset/currencies",
        params={"ccy": "USDT"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15
    )
    return resp.json()
```

### 4.2 OKX 账户 API（需 API Key）

```python
import hmac, base64, datetime, requests

def okx_get_deposit_history(api_key, secret_key, passphrase):
    """查充值历史"""
    now = datetime.datetime.utcnow()
    sign = hmac.new(secret_key.encode(),
                    f"GET/api/v5/asset/deposit-history{now.isoformat()}Z".encode(),
                    "sha256").digest()
    headers = {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": base64.b64encode(sign).decode(),
        "OK-ACCESS-TIMESTAMP": now.isoformat() + "Z",
        "OK-ACCESS-PASSPHRASE": passphrase,
    }
    resp = requests.get(
        "https://www.okx.com/api/v5/asset/deposit-history",
        headers=headers, timeout=15
    )
    return resp.json()
```

### 4.3 Binance 公开 API

```python
import requests

# 币种信息
def binance_get_exchange_info():
    resp = requests.get(
        "https://api.binance.com/api/v3/exchangeInfo",
        timeout=15
    )
    return resp.json()

# 币种详情
def binance_get_asset_details(asset: str):
    resp = requests.get(
        "https://api.binance.com/wapi/v3/assetDetail.html",
        params={"asset": asset},
        timeout=15
    )
    return resp.json()
```

---

## 五、真实数据接入步骤

### Step 1：替换 params_search_assets（最简单，无认证）

```python
# scripts/real_tools.py
import requests

def params_search_assets_real(asset: str, network: str = None) -> dict:
    """从 OKX 公开 API 获取真实币链参数"""
    resp = requests.get(
        "https://www.okx.com/api/v5/asset/currencies",
        params={"ccy": asset.upper()},
        timeout=15
    )
    data = resp.json()
    # 解析 OKX 格式，映射到 asset_params 结构
    ...
```

### Step 2：替换 get_wallet_network_status

从 OKX `/api/v5/asset/currencies` 获取 deposit_enabled / withdraw_enabled，从公告 API 获取维护状态。

### Step 3：替换 get_kyb_status / get_withdraw_status / get_deposit_status

需要账户级 API Key，分为：
- **只读 Key**：可以查充值/提现/KYB 状态
- **交易 Key**：可以查余额等，不能用于本项目

**建议：** 第一阶段只接入只读 Key，Key 权限最小化。

### Step 4：替换 docs_search_helpcenter / docs_search_announcements

两种方案：
- **方案 A（推荐）：** 定时爬取 OKX/Binance 帮助中心和公告，存储到 Bitable，定期增量更新
- **方案 B：** 直接接入 OKX/Binance 的 CMS API（如果有）

---

## 六、Bitable 知识库方案（推荐）

用飞书 Bitable 作为知识库存储层：

| Bitable | 内容 |
|---------|------|
| `kb_announcements` | 公告库（标题/类型/时间/内容摘要/链接） |
| `kb_rules` | 规则库（账户/充值/提现/费率/KYC） |
| `kb_params` | 参数库（币种/网络/最低限额/确认数） |
| `kb_faq` | 故障排障库（问题/原因/解决方案） |

每条记录包含：
```
title / category / tags / platform / content / source_url / updated_at / status
```

---

## 七、第一阶段数据缺口（需要你补充）

目前 Mock 数据里缺少：

1. **帮助中心文档原文** — 需要你提供 OKX/Binance 帮助中心链接，我来写爬取脚本
2. **真实 KYB 审核拒绝原因** — 以真实业务场景为准，可补充到 Mock
3. **公告原始内容** — 目前只有摘要，需要原文可爬取
4. **OKX/Binance API Key** — Phase 2 接入真实状态时需要（只读权限即可）

---

## 八、快速验证命令

```bash
cd /root/.openclaw/workspace/memory/projects/ai-customer-service

# 验证所有工具可用
python3 scripts/mock_tools.py docs_search_helpcenter --query "充值"
python3 scripts/mock_tools.py params_search_assets --asset USDT --network TRC20
python3 scripts/mock_tools.py get_kyb_status --user_id uid_10002
python3 scripts/mock_tools.py get_withdraw_status --user_id uid_10001
python3 scripts/mock_tools.py get_deposit_status --user_id uid_10003
python3 scripts/mock_tools.py get_wallet_network_status --asset ATOM --network Cosmos
python3 scripts/mock_tools.py get_ticket_status --user_id uid_10002
```
