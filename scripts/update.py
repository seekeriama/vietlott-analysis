#!/usr/bin/env python3
"""Tải kết quả Power 6/55 và Mega 6/45 từ xskt.com.vn và gộp vào data/vietlott.json.
Chỉ dùng thư viện chuẩn. Thoát với mã lỗi nếu không đọc được dữ liệu của một loại vé."""
import json, re, sys, datetime, html, urllib.request

DATA = "data/vietlott.json"
GAMES = {
    "655": {"url": "https://xskt.com.vn/xspower/30-ngay", "fallback": "https://xskt.com.vn/xspower",
            "N": 55, "bonus": True, "min_draw": 1423},
    "645": {"url": "https://xskt.com.vn/xsmega645/30-ngay", "fallback": "https://xskt.com.vn/xsmega645",
            "N": 45, "bonus": False, "min_draw": 1588},
}
NOW = datetime.datetime.now(datetime.timezone.utc)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (vietlott-analysis updater)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")

def to_text(raw):
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw))

def infer_date(day, month):
    """Trang chỉ ghi ngày/tháng; chọn năm sao cho ngày không nằm trong tương lai."""
    today = NOW.date() + datetime.timedelta(days=1)
    for y in (today.year, today.year - 1):
        try:
            d = datetime.date(y, month, day)
        except ValueError:
            continue
        if d <= today:
            return d
    return None

def parse(text, g):
    need = 7 if g["bonus"] else 6
    out = {}
    for m in re.finditer(r"#\s*0*(\d{3,5})\b", text):
        draw = int(m.group(1))
        if draw in out:
            continue
        back = text[max(0, m.start() - 80):m.start()]
        dm = re.findall(r"(\d{1,2})\s*/\s*(\d{1,2})(?!\d)", back)
        fwd = text[m.end():m.end() + 260]
        if not dm:
            dm = re.findall(r"(\d{1,2})\s*/\s*(\d{1,2})(?!\d)", fwd[:60])
        if not dm:
            continue
        dd = infer_date(int(dm[-1][0]), int(dm[-1][1]))
        nums = [int(x) for x in re.findall(r"(?<!\d)(\d{2})(?!\d)", re.sub(r"\d{1,2}\s*/\s*\d{1,2}(\s*/\s*\d{2,4})?", " ", fwd))][:need]
        if dd is None or len(nums) != need:
            continue
        main = nums[:6]
        if len(set(main)) != 6 or any(not 1 <= n <= g["N"] for n in nums):
            continue
        if g["bonus"] and nums[6] in main:
            continue
        rec = {"draw": draw, "date": dd.strftime("%d-%m-%Y"), "nums": sorted(main),
               "source": "xskt.com.vn", "fetchedAt": NOW.strftime("%Y-%m-%dT%H:%M:%SZ")}
        if g["bonus"]:
            rec["bonus"] = nums[6]
        out[draw] = rec
    return out

def main():
    try:
        store = json.load(open(DATA, encoding="utf-8"))
    except FileNotFoundError:
        store = {"655": [], "645": [], "meta": {}}
    failed = False
    for gid, g in GAMES.items():
        have = {d["draw"]: d for d in store.get(gid, [])}
        found = {}
        for url in (g["url"], g["fallback"]):
            try:
                found = parse(to_text(fetch(url)), g)
            except Exception as e:
                print(f"[{gid}] lỗi tải {url}: {e}", file=sys.stderr)
                continue
            if found:
                break
        if not found:
            failed = True
            store.setdefault("meta", {})[gid] = {"lastRun": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "result": "error",
                "message": "Không đọc được kết quả từ xskt.com.vn", "lastDraw": max(have, default=g["min_draw"])}
            continue
        new = [d for k, d in sorted(found.items()) if k > g["min_draw"] and k not in have]
        for d in new:
            have[d["draw"]] = d
        store[gid] = [have[k] for k in sorted(have)]
        last = max(have, default=g["min_draw"])
        store.setdefault("meta", {})[gid] = {"lastRun": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "result": "ok", "lastDraw": last,
            "message": ("Đã thêm kỳ " + ", ".join("#%d" % d["draw"] for d in new)) if new else "Chưa có kỳ mới"}
        print(f"[{gid}] đọc được {len(found)} kỳ, thêm {len(new)}: {[d['draw'] for d in new]}")
    json.dump(store, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
