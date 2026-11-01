#!/usr/bin/env python3
"""stock_image.py — 网络免费图库配图工具（Pexels CDN，Pexels License 可免费商用）。

按关键词/已知 ID 下载高赞图，输出本地文件。配合 wx_upload_img.py 上传公众号素材库换 URL 后嵌入文章。

用法:
    python3 stock_image.py --query-id 546819                    # 已知 ID 下载
    python3 stock_image.py --query-id 546819,373543 --out dir   # 批量
    python3 stock_image.py --suggest workflow                   # 打印该主题的高赞 ID 清单（内置精选库）

内置精选库（Pexels 高赞，主题→ID）:
    workflow/collaboration : 546819, 3184292, 1181675
    laptop/writing/desk    : 373543, 4164418, 1181244
    teamwork/meeting       : 3184292, 3184465, 1595388
    growth/planning        : 669615, 356056, 6444216

说明:
    - Pexels CDN 直链格式: https://images.pexels.com/photos/<id>/pexels-photo-<id>.jpeg?auto=compress&cs=tinysrgb&w=1200
    - 无需 API key；失败多为网络问题，重试即可
    - 许可: Pexels License（免费商用、无需署名，但不可转售原图）
"""
import argparse
import os
import sys
import urllib.request

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
CDN = "https://images.pexels.com/photos/{pid}/pexels-photo-{pid}.jpeg?auto=compress&cs=tinysrgb&w=1200"

SUGGEST = {
    "workflow": [546819, 3184292, 1181675, 3183150],
    "collaboration": [3184292, 3184465, 1595388, 546819],
    "laptop": [373543, 4164418, 1181244, 1181671],
    "writing": [373543, 4164418, 669615, 261662],
    "desk": [373543, 4050315, 669615, 2058128],
    "teamwork": [3184292, 3184465, 1595388, 1000423],
    "meeting": [3184292, 1181406, 260689, 4164052],
    "growth": [669615, 356056, 6444216, 886336],
    "planning": [669615, 356056, 4065876],
    "ai": [8386440, 3729464, 2228562],
}


def download(pid: int, outdir: str) -> str:
    url = CDN.format(pid=pid)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with OPENER.open(req, timeout=30) as r:
        data = r.read()
    if len(data) < 5000 or not data[:3] == b"\xff\xd8\xff":
        raise RuntimeError(f"非 JPEG 内容（{len(data)}B），ID 可能无效")
    path = os.path.join(outdir, f"pexels-{pid}.jpg")
    open(path, "wb").write(data)
    return path


def main():
    ap = argparse.ArgumentParser(description="Pexels 免费配图下载")
    ap.add_argument("--query-id", help="图片 ID，逗号分隔（从 --suggest 拿）")
    ap.add_argument("--suggest", help="按主题打印高赞 ID 清单（workflow/laptop/teamwork/growth/ai…）")
    ap.add_argument("--out", default=".", help="输出目录（默认当前目录）")
    args = ap.parse_args()

    if args.suggest:
        key = args.suggest.lower()
        ids = SUGGEST.get(key) or [v for k, v in SUGGEST.items() if key in k][0]
        print(f"主题「{key}」高赞 ID: {', '.join(map(str, ids))}")
        return

    if not args.query_id:
        ap.print_help()
        return

    os.makedirs(args.out, exist_ok=True)
    ok, fail = [], []
    for pid in [x.strip() for x in args.query_id.split(",") if x.strip()]:
        try:
            p = download(int(pid), args.out)
            ok.append(p)
            print(f"✅ {pid} → {p}（{os.path.getsize(p)//1024}KB）")
        except Exception as e:
            fail.append(pid)
            print(f"❌ {pid}: {e}")
    print(f"=== 成功 {len(ok)} / 失败 {len(fail)} ===")
    sys.exit(1 if fail and not ok else 0)


if __name__ == "__main__":
    main()
