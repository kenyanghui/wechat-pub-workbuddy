#!/usr/bin/env python3
"""diagnose.py — 一键诊断：依赖 / 凭证 / IP 白名单 / IMA 连通（含写链路探针） / 公众号 API / 代理干扰 / 配置。

用法：python3 scripts/diagnose.py [--deep]
--deep 会额外做 IMA create_media 探针（写链路验证，不留垃圾数据——探针不 add_knowledge）。
"""
import json
import os
import re
import shutil
import urllib.request

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
IMA_BASE = "https://ima.qq.com/openapi/wiki/v1/"
DEEP = "--deep" in os.sys.argv


def read_cred(path):
    p = os.path.expanduser(path)
    return open(p).read().strip() if os.path.isfile(p) else None


def main():
    print("=" * 52)
    print(" rsi-wechat-publisher 一键诊断")
    print("=" * 52)

    # 0. 系统代理（502 干扰源）
    proxies = urllib.request.getproxies()
    if proxies:
        print(f"[代理] ⚠️ 检测到系统代理 {proxies.get('https') or proxies.get('http')}（本技能脚本已内置直连绕过）")
    else:
        print("[代理] ✅ 无（直连）")

    # 1. 命令依赖
    for cmd in ("git", "python3"):
        print(f"[依赖] {cmd}: {'✅ ' + shutil.which(cmd) if shutil.which(cmd) else '❌ 未安装'}")

    # 2. IMA
    cid, key = read_cred("~/.config/ima/client_id"), read_cred("~/.config/ima/api_key")
    if not (cid and key):
        print("[IMA] ❌ 凭证缺失 ~/.config/ima/{client_id,api_key}")
    else:
        try:
            cfg_kb = _cfg_kb()
            probe_kb = cfg_kb or "probe"
            req = urllib.request.Request(IMA_BASE + "get_knowledge_list",
                data=json.dumps({"knowledge_base_id": probe_kb, "limit": 1}).encode(), method="POST",
                headers={"Content-Type": "application/json",
                         "ima-openapi-clientid": cid, "ima-openapi-apikey": key})
            with OPENER.open(req, timeout=15) as r:
                rep = json.loads(r.read())
            print(f"[IMA] ✅ 读链路通（get_knowledge_list code={rep.get('code')}，探测库: {probe_kb[:24]}）")
            if DEEP:
                cfg_kb = _cfg_kb()
                if cfg_kb:
                    req2 = urllib.request.Request(IMA_BASE + "create_media",
                        data=json.dumps({"file_name": "probe.md", "file_size": 10, "content_type": "text/markdown",
                                          "knowledge_base_id": cfg_kb, "file_ext": "md"}).encode(), method="POST",
                        headers={"Content-Type": "application/json",
                                 "ima-openapi-clientid": cid, "ima-openapi-apikey": key})
                    with OPENER.open(req2, timeout=15) as r:
                        rep2 = json.loads(r.read())
                    print(f"[IMA] {'✅' if rep2.get('code') == 0 else '⚠️'} 写链路探针 create_media code={rep2.get('code')}")
        except Exception as e:
            print(f"[IMA] ❌ API 失败：{str(e)[:120]}")

    # 3. 公众号 + IP
    appid, secret = read_cred("~/.config/wechat/appid"), read_cred("~/.config/wechat/secret")
    if not (appid and secret):
        print("[公众号] ⚠️ 凭证缺失（将本地打包降级）")
    else:
        try:
            payload = json.dumps({"grant_type": "client_credential", "appid": appid, "secret": secret}).encode()
            req = urllib.request.Request("https://api.weixin.qq.com/cgi-bin/stable_token",
                                         data=payload, headers={"Content-Type": "application/json"})
            with OPENER.open(req, timeout=15) as r:
                rep = json.loads(r.read())
            if "access_token" in rep:
                print("[公众号] ✅ token 成功（凭证+IP 白名单正常）")
            else:
                ec = rep.get("errcode")
                if ec == 40164:
                    m = re.search(r"invalid ip (\d+\.\d+\.\d+\.\d+)", rep.get("errmsg", ""))
                    print(f"[公众号] ❌ IP 不在白名单{': ' + m.group(1) if m else ''} → 公众号后台「基本配置→IP白名单」加该 IP")
                    print("        💡 家宽动态 IP 建议：加白常见网段内 IP，或每次流水线前跑本诊断")
                else:
                    print(f"[公众号] ❌ errcode={ec}: {rep.get('errmsg')}")
        except Exception as e:
            print(f"[公众号] ❌ 请求失败：{e}")

    # 4. 配置
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    if os.path.isfile(cfg_path):
        cfg = json.load(open(cfg_path, encoding="utf-8"))
        print(f"[配置] ✅ config.json（库: {cfg.get('ima_kb_name') or cfg.get('ima_kb_id') or '未填'}；作者: {cfg.get('author_name', '?')}；配图策略: {(cfg.get('images') or {}).get('policy', '未设')}）")
    else:
        print("[配置] ❌ config.json 不存在 → 跑 scripts/setup_wizard.py")
    print("=" * 52)


def _cfg_kb():
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    try:
        return json.load(open(cfg_path, encoding="utf-8")).get("ima_kb_id", "")
    except Exception:
        return ""


if __name__ == "__main__":
    main()
