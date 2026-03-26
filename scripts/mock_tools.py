#!/usr/bin/env python3
"""
Crypto Support MVP - Mock 工具脚本
实现 TOOLS_SPEC.md 中定义的所有工具
第一阶段使用本地 JSON Mock 数据
第二阶段替换为真实 API 调用
"""
import sys
import os
import json
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "mock")


def _load_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _error_response(code: str, message: str) -> dict:
    return {"error": code, "message": message}


# ============================================================
# 知识工具
# ============================================================

def docs_search_helpcenter(query: str, platform: str = None,
                            category: str = None, limit: int = 3) -> dict:
    """检索帮助中心文档（Mock 实现）"""
    # Mock 返回基于 query 关键词的模拟文档
    docs = []
    q = query.lower()

    all_docs = [
        {
            "title": "USDT 充值未到账排查指南",
            "url": "https://www.okx.com/zh-hans/help/section/deposit",
            "snippet": "如果您的 USDT 充值未到账，请按以下步骤排查：1. 确认网络选择正确；2. 确认 Memo（如需要）；3. 确认最低充值限额；4. 查看链上确认状态。",
            "platform": "okx",
            "category": "deposit",
            "updated_at": "2026-03-15"
        },
        {
            "title": "如何进行企业认证（KYB）",
            "url": "https://www.okx.com/zh-hans/help/section/kyb",
            "snippet": "企业认证需要提交：营业执照、公司注册证明、地址证明、法人身份证。审核时长通常为 1-3 个工作日。",
            "platform": "okx",
            "category": "kyc",
            "updated_at": "2026-03-01"
        },
        {
            "title": "充值说明 - Binance",
            "url": "https://www.binance.com/zh-CN/support/deposit",
            "snippet": "Binance 充值说明：不同币种网络不同最低充值限额，请确认转账时选择的网络与充值页显示一致。",
            "platform": "binance",
            "category": "deposit",
            "updated_at": "2026-03-10"
        },
        {
            "title": "提现常见问题FAQ",
            "url": "https://www.okx.com/zh-hans/help/section/withdraw",
            "snippet": "提现状态说明：Pending-审核中 / Broadcasted-已广播 / Completed-已完成 / Failed-失败。链上确认需要一定时间，请耐心等待。",
            "platform": "okx",
            "category": "withdraw",
            "updated_at": "2026-03-12"
        },
        {
            "title": "什么是 Memo/Tag，为什么充值需要填写？",
            "url": "https://www.okx.com/zh-hans/help/section/memo",
            "snippet": "Memo（备注/Tag）是某些币种用于识别充值来源的附加字段，如 XRP、XLM、EOS 等必须填写正确的 Memo，否则充值无法到账。",
            "platform": "okx",
            "category": "account",
            "updated_at": "2026-02-20"
        },
        {
            "title": "Binance KYC 认证流程",
            "url": "https://www.binance.com/zh-CN/support/kyc",
            "snippet": "Binance KYC 分三级：L1基础认证（姓名+证件）、L2高级认证（人脸+地址证明）、企业认证（KYB）。",
            "platform": "binance",
            "category": "kyc",
            "updated_at": "2026-03-08"
        }
    ]

    for doc in all_docs:
        if platform and doc["platform"] != platform:
            continue
        if category and doc["category"] != category:
            continue
        # 简单的关键词匹配
        if any(k in q for k in [doc["title"].lower(), doc["snippet"].lower()]):
            docs.append(doc)

    return {"docs": docs[:limit], "is_mock": True}


def docs_search_announcements(query: str, platform: str = None,
                               type: str = None, date_from: str = None,
                               date_to: str = None, limit: int = 5) -> dict:
    """检索公告"""
    data = _load_json("announcements.json")
    announcements = data.get("announcements", [])
    q = query.lower()
    results = []

    for ann in announcements:
        if platform and ann.get("platform") != platform:
            continue
        if type and ann.get("type") != type:
            continue
        if any(k in ann["title"].lower() or k in ann.get("content_summary", "").lower()
               for k in [q, q.upper(), q.replace(" ", "")]):
            results.append(ann)

    return {"announcements": results[:limit], "is_mock": True}


def params_search_assets(asset: str, network: str = None, platform: str = None) -> dict:
    """查询币链参数"""
    data = _load_json("wallet_status.json")
    asset_upper = asset.upper()

    if asset_upper not in data:
        return _error_response(
            "TOOL_ERROR_ASSET_NOT_SUPPORTED",
            f"平台暂不支持 {asset}，或该币种尚未开放"
        )

    if network:
        network_key = _normalize_network(asset_upper, network, data)
        if not network_key:
            return _error_response(
                "TOOL_ERROR_NETWORK_NOT_SUPPORTED",
                f"{asset} 不支持 {network} 网络，请查看替代网络"
            )
        asset_data = data[asset_upper]
        if network_key in asset_data:
            params = asset_data[network_key].copy()
            params["asset"] = asset_upper
            params["network"] = network_key
            params["platform"] = platform or "okx"
            return {"asset_params": params, "is_mock": True}
        else:
            # 返回该币所有网络 + 错误
            all_networks = list(asset_data.keys())
            return _error_response(
                "TOOL_ERROR_NETWORK_NOT_SUPPORTED",
                f"{asset} 不支持 {network}。支持的网络：{', '.join(all_networks)}"
            )
    else:
        # 返回该币所有网络
        all_networks = []
        for net, params in data[asset_upper].items():
            p = params.copy()
            p["network"] = net
            all_networks.append(p)
        return {"asset_params": all_networks, "is_mock": True}


def _normalize_network(asset: str, network: str, data: dict) -> str:
    """规范化网络名称到 Mock 数据中的 Key"""
    mapping = {
        "usdt": {
            "trc20": "TRC20", "trx": "TRC20", "trc": "TRC20",
            "erc20": "ERC20", "eth": "ERC20", "ethereum": "ERC20",
            "arbitrum": "Arbitrum", "arb": "Arbitrum",
            "sol": "Solana", "solana": "Solana",
            "polygon": "Polygon", "matic": "Polygon", "poly": "Polygon",
        },
        "btc": {"btc": "Bitcoin", "bitcoin": "Bitcoin"},
        "eth": {"erc20": "ERC20", "eth": "ERC20", "ethereum": "ERC20",
                "arbitrum": "Arbitrum", "optimism": "Optimism", "polygon": "Polygon"},
        "atom": {"cosmos": "Cosmos", "atom": "Cosmos", "cosmos-sdk": "Cosmos"}
    }
    net_map = mapping.get(asset.lower(), {})
    return net_map.get(network.lower(), network)


# ============================================================
# 状态工具
# ============================================================

def get_kyb_status(user_id: str) -> dict:
    """查询 KYB/KYC 状态"""
    data = _load_json("kyb_status.json")
    if user_id not in data:
        return _error_response("TOOL_ERROR_KYB_NOT_FOUND",
                               "未找到该用户的 KYB 记录，可能尚未提交认证申请")
    result = data[user_id].copy()
    return {"kyb_status": result, "is_mock": True}


def get_withdraw_status(user_id: str, asset: str = None,
                         network: str = None, limit: int = 5) -> dict:
    """查询提现状态"""
    data = _load_json("withdraw_status.json")
    if user_id not in data:
        # 演示：未注册用户也返回空列表，模拟"无提现记录"
        return {"withdrawals": [], "is_mock": True}

    withdrawals = data[user_id]["withdrawals"]
    if asset:
        withdrawals = [w for w in withdrawals if w["asset"].upper() == asset.upper()]
    if network:
        withdrawals = [w for w in withdrawals
                       if w["network"].lower() == network.lower()]

    return {"withdrawals": withdrawals[:limit], "is_mock": True}


def get_deposit_status(user_id: str, asset: str = None,
                        network: str = None, limit: int = 5) -> dict:
    """查询充值状态"""
    data = _load_json("deposit_status.json")
    if user_id not in data:
        return {"deposits": [], "is_mock": True}

    deposits = data[user_id]["deposits"]
    if asset:
        deposits = [d for d in deposits if d["asset"].upper() == asset.upper()]
    if network:
        deposits = [d for d in deposits
                    if d["network"].lower() == network.lower()]

    return {"deposits": deposits[:limit], "is_mock": True}


def get_wallet_network_status(asset: str, network: str = None,
                               platform: str = None) -> dict:
    """查询钱包/网络充提状态"""
    data = _load_json("wallet_status.json")
    asset_upper = asset.upper()

    if asset_upper not in data:
        return _error_response("TOOL_ERROR_ASSET_NOT_SUPPORTED",
                               f"暂不支持 {asset}，或该币种尚未开放")

    net_key = _normalize_network(asset_upper, network, data) if network else None

    if network:
        if net_key not in data[asset_upper]:
            all_nets = list(data[asset_upper].keys())
            return _error_response(
                "TOOL_ERROR_NETWORK_NOT_SUPPORTED",
                f"{asset} 不支持 {network} 网络。支持：{', '.join(all_nets)}"
            )
        p = data[asset_upper][net_key].copy()
        p["asset"] = asset_upper
        p["network"] = net_key
        p["platform"] = platform or "okx"
        return {"wallet_status": p, "is_mock": True}
    else:
        # 返回该币所有网络状态
        statuses = []
        for net, params in data[asset_upper].items():
            p = params.copy()
            p["asset"] = asset_upper
            p["network"] = net
            p["platform"] = platform or "okx"
            statuses.append(p)
        return {"wallet_status": statuses, "is_mock": True}


def get_ticket_status(user_id: str, status: str = None, limit: int = 5) -> dict:
    """查询工单状态（简化 Mock）"""
    # 演示用 Mock 工单数据
    tickets_db = {
        "uid_10001": [
            {
                "ticket_id": "TK_8827301",
                "type": "充值未到账",
                "status": "resolved",
                "status_desc": "已解决",
                "created_at": "2026-03-20T10:00:00Z",
                "updated_at": "2026-03-21T15:00:00Z",
                "latest_reply": "经核实，链上确认数为 18/20，充值已到账，感谢反馈。",
                "missing_info": [],
                "sla_deadline": "2026-03-22T10:00:00Z"
            }
        ],
        "uid_10002": [
            {
                "ticket_id": "TK_8827302",
                "type": "KYB材料补充",
                "status": "pending",
                "status_desc": "等待补充材料",
                "created_at": "2026-03-25T08:00:00Z",
                "updated_at": "2026-03-26T09:00:00Z",
                "latest_reply": "请补充公司注册证明和有效期内地址证明。",
                "missing_info": ["incorporation_cert", "address_proof_valid"],
                "sla_deadline": "2026-03-28T08:00:00Z"
            }
        ]
    }
    tickets = tickets_db.get(user_id, [])
    if status:
        tickets = [t for t in tickets if t["status"] == status]
    return {"tickets": tickets[:limit], "is_mock": True}


# ============================================================
# 交互工具
# ============================================================

def create_support_summary(
    user_id: str,
    problem_type: str,
    platform: str,
    diagnosis: str,
    asset: str = None,
    network: str = None,
    amount: str = None,
    txid: str = None,
    order_id: str = None,
    evidence: list = None,
    user_description: str = None,
    attempted_actions: list = None
) -> dict:
    """生成结构化工单摘要"""
    import uuid
    summary_id = f"TK_{uuid.uuid4().hex[:7].upper()}"

    # 估算优先级
    priority = "medium"
    auto_escalate = False
    if problem_type in ["account_limit", "security_incident"]:
        priority = "high"
        auto_escalate = True

    return {
        "summary": {
            "ticket_id": summary_id,
            "user_id": user_id,
            "problem_type": problem_type,
            "platform": platform,
            "priority": priority,
            "asset": asset,
            "network": network,
            "amount": amount,
            "txid": txid,
            "order_id": order_id,
            "diagnosis": diagnosis,
            "evidence": evidence or [],
            "user_description": user_description,
            "attempted_actions": attempted_actions or [],
            "suggested_next_step": _suggest_next_step(problem_type, diagnosis),
            "auto_escalate": auto_escalate,
            "created_at": "2026-03-26T12:00:00Z",
            "is_mock": True
        }
    }


def _suggest_next_step(problem_type: str, diagnosis: str) -> str:
    """根据问题类型给出建议下一步"""
    suggestions = {
        "withdraw_delay": "如链上确认已完成但超过24小时仍未到账，建议提交工单并附 TXID",
        "deposit_delay": "如链上确认已完成但平台未入账，建议提交工单",
        "kyc_issue": "请按上述要求补充缺失材料，材料齐全后重新提交审核",
        "account_limit": "建议联系人工客服，说明具体情况",
        "other": "如问题持续，建议提交工单跟进"
    }
    return suggestions.get(problem_type, "如问题未解决，建议提交工单")


def escalate_to_human(reason: str, conversation_summary: str,
                       user_id: str, urgency: str = "medium") -> dict:
    """触发人工升级"""
    import uuid
    escalation_id = f"es_{uuid.uuid4().hex[:7].upper()}"
    response_times = {
        "critical": "15分钟内",
        "high": "30分钟内",
        "medium": "2小时内",
        "low": "24小时内"
    }
    return {
        "escalation": {
            "escalation_id": escalation_id,
            "reason": reason,
            "urgency": urgency,
            "assigned_to": "人工客服",
            "estimated_response_time": response_times.get(urgency, "2小时内"),
            "user_notified": True,
            "is_mock": True
        }
    }


# ============================================================
# CLI 接口（用于 OpenClaw exec 模式）
# ============================================================

TOOL_MAP = {
    "docs_search_helpcenter": docs_search_helpcenter,
    "docs_search_announcements": docs_search_announcements,
    "params_search_assets": params_search_assets,
    "get_kyb_status": get_kyb_status,
    "get_withdraw_status": get_withdraw_status,
    "get_deposit_status": get_deposit_status,
    "get_wallet_network_status": get_wallet_network_status,
    "get_ticket_status": get_ticket_status,
    "create_support_summary": create_support_summary,
    "escalate_to_human": escalate_to_human,
}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Crypto Support MVP Mock Tools")
    parser.add_argument("tool", choices=list(TOOL_MAP.keys()), help="工具名称")
    parser.add_argument("--query", default="")
    parser.add_argument("--platform", default=None)
    parser.add_argument("--category", default=None)
    parser.add_argument("--type", dest="type_", default=None)
    parser.add_argument("--asset", default=None)
    parser.add_argument("--network", default=None)
    parser.add_argument("--user_id", default=None)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--problem_type", default=None)
    parser.add_argument("--diagnosis", default=None)
    parser.add_argument("--reason", default=None)
    parser.add_argument("--urgency", default="medium")
    parser.add_argument("--user_description", default=None)
    args = parser.parse_args()

    import inspect
    tool = TOOL_MAP[args.tool]
    # 只传递目标函数接受的参数
    sig = inspect.signature(tool)
    valid_keys = set(sig.parameters.keys())
    kwargs = {}
    for k, v in vars(args).items():
        if k in valid_keys and v is not None:
            kwargs[k] = v
    if hasattr(args, "type_") and args.type_:
        kwargs["type"] = args.type_

    result = tool(**kwargs)
    print(json.dumps(result, ensure_ascii=False, indent=2))
