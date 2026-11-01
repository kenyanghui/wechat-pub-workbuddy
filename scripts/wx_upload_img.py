#!/usr/bin/env python3
"""wx_upload_img.py — 上传图片到微信公众号素材库换 wx URL（图文内图必须走此步，本地路径草稿不显示）。

用法:
    python3 wx_upload_img.py <图片1> [图片2 ...]            # 上传并打印 JSON 映射
    python3 wx_upload_img.py --map url_map.json <图片...>   # 追加写入映射文件（推荐，配合 article.md 重建）

凭证: ~/.config/wechat/{appid,secret}（缺失时报错退出，不降级——配图是硬需求）
"""
import argparse
import json
import os
import sys
import time
import urllib.request

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
CRED = os.path.expanduser("~/.config/wechat")


def token():
    appid = open(os.path.join(CRED, "appid")).read().strip()
    secret = open(os.path.join(CRED, "secret")).read().strip()
    r = urllib.request.Request("https://api.weixin.qq.com/cgi-bin/stable_token",
        data=json.dumps({"grant_type": "client_credential", "appid": appid, "secret": secret}).encode(),
        headers={"Content-Type": "application/json"})
    d = json.loads(OPENER.open(r, timeout=15).read())
    if "access_token" not in d:
        print(f"❌ token 失败: {d.get('errcode')} {d.get('errmsg')}", file=sys.stderr)
        sys.exit(1)
    return d["access_token"]


def upload_img(tok, path):
    boundary = "----WbBoundary7MA4YWxk"
    with open(path, "rb") as f:
        img = f.read()
    fn = os.path.basename(path)
    ct = "image/png" if fn.lower().endswith(".png") else "image/jpeg"
    body = (f"--{boundary}\r\n" f'Content-Disposition: form-data; name="media"; filename="{fn}"; '
            f"Content-Type: {ct}\r\n\r\n").encode() + img + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={tok}",
        data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return json.loads(OPENER.open(req, timeout=60).read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--map", help="映射 json 文件（本地文件名→wx URL），存在则合并")
    args = ap.parse_args()

    if not (os.path.isfile(os.path.join(CRED, "appid")) and os.path.isfile(os.path.join(CRED, "secret"))):
        print("❌ 公众号凭证缺失 ~/.config/wechat/{appid,secret}", file=sys.stderr)
        sys.exit(1)

    tok = token()
    url_map = {}
    if args.map and os.path.isfile(args.map):
        try:
            url_map = json.load(open(args.map))
        except Exception:
            pass

    ok = 0
    for p in args.images:
        p = os.path.abspath(p)
        if not os.path.isfile(p):
            print(f"❌ 不存在: {p}")
            continue
        rep = upload_img(tok, p)
        if rep.get("url"):
            url_map[os.path.basename(p)] = rep["url"]
            print(f"✅ {os.path.basename(p)} → {rep['url'][:70]}…")
            ok += 1
        else:
            print(f"❌ {os.path.basename(p)}: {rep}")
        time.sleep(1)

    if args.map:
        json.dump(url_map, open(args.map, "w"), ensure_ascii=False, indent=2)
        print(f"=== {ok}/{len(args.images)} 已上传，映射写入 {args.map}（共 {len(url_map)} 条）===")
    else:
        print(json.dumps(url_map, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
