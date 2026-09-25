#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Porn87 - type_id 使用 cat_ 前缀，规避 hot/video 等保留字导致「暂无数据」

import re
import json
import html as html_lib
import urllib.request
import urllib.parse
import http.cookiejar
import gzip
import zlib
import ssl

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"


class Spider(SpiderBase):
    def __init__(self):
        super(Spider, self).__init__()
        self.siteUrl = "https://porn87.com"
        self._ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self.options = {}
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ctx),
        )
        self._tag_map = {
            "cat_hdjav": "高清日本AV",
            "cat_chinese": "中港台",
            "cat_wife": "人妻",
            "cat_bigtits": "巨乳",
            "cat_amateur": "素人",
            "cat_teen": "少女女友",
            "cat_bj": "口交",
            "cat_creampie": "中出",
            "cat_cam": "偷拍",
            "cat_uniform": "制服",
            "cat_celeb": "名人明星",
            "cat_gangbang": "多P",
        }

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.options = extend
        elif extend:
            try:
                self.options = json.loads(extend)
            except Exception:
                self.options = {}
        return True

    def getName(self):
        return "Porn87"

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".ts"))

    def manualVideoCheck(self):
        return False

    def _fetch(self, target_url, referer=""):
        if not target_url:
            return {"code": 0, "text": "", "err": ""}
        if target_url.startswith("//"):
            target_url = "https:" + target_url
        elif target_url.startswith("/"):
            target_url = self.siteUrl + target_url
        headers = {
            "User-Agent": self._ua,
            "Referer": referer or (self.siteUrl + "/"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        }
        for attempt in range(2):
            try:
                req = urllib.request.Request(target_url, headers=headers)
                with self.opener.open(req, timeout=15) as resp:
                    raw = resp.read()
                    enc = getattr(resp, "headers", {}).get("Content-Encoding", "")
                    if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                        raw = gzip.decompress(raw)
                    elif enc == "deflate":
                        try:
                            raw = zlib.decompress(raw)
                        except Exception:
                            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                    return {"code": resp.getcode(), "text": raw.decode("utf-8", "ignore"), "err": ""}
            except Exception as e:
                if attempt == 0:
                    continue
                return {"code": 0, "text": "", "err": str(e)}
        return {"code": 0, "text": "", "err": "fail"}

    def _clean(self, s):
        s = html_lib.unescape(str(s or ""))
        s = re.sub(r"<[^>]+>", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def _abs(self, url):
        if not url:
            return ""
        url = str(url).strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.siteUrl + url
        return url

    def _parse_cards(self, html_text):
        vod_list = []
        seen = set()
        for m in re.finditer(
            r'<a[^>]+href=["\'](/main/html\?id=(\d+))["\'][^>]*>([\s\S]*?)</a>',
            html_text or "",
            re.I,
        ):
            path, vid, block = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            if "video_thumbnail" not in block and "<img" not in block:
                continue
            seen.add(vid)
            img_m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block, re.I)
            pic = self._abs(img_m.group(1)) if img_m else ""
            if not pic or "image_not_found" in pic:
                pm = re.search(r'preview_image=["\']([^"\']+)["\']', block, re.I)
                if pm:
                    pic = self._abs(pm.group(1))
            title_m = re.search(r"<span[^>]*>([\s\S]*?)</span>", block, re.I)
            name = self._clean(title_m.group(1) if title_m else "") or ("视频" + vid)
            tips_m = re.search(r'class=["\']video_time["\'][^>]*>\s*<p>([^<]+)', block, re.I)
            tips = self._clean(tips_m.group(1)) if tips_m else ""
            vod_list.append({
                "vod_id": self._abs(path),
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": tips,
            })
        return vod_list

    def _cat_url(self, tid, page):
        page = max(1, int(page) if str(page).isdigit() else 1)
        tid = str(tid or "cat_latest")
        # 兼容旧 id
        legacy = {
            "latest": "cat_latest", "hot": "cat_hot", "create_time": "cat_latest",
            "recent_views": "cat_hot", "tag_hdjav": "cat_hdjav", "tag_chinese": "cat_chinese",
            "tag_wife": "cat_wife", "tag_bigtits": "cat_bigtits", "tag_amateur": "cat_amateur",
            "tag_teen": "cat_teen", "tag_bj": "cat_bj", "tag_creampie": "cat_creampie",
            "tag_cam": "cat_cam", "tag_uniform": "cat_uniform", "tag_celeb": "cat_celeb",
            "tag_gangbang": "cat_gangbang",
        }
        if tid in legacy:
            tid = legacy[tid]
        if tid in self._tag_map:
            name = urllib.parse.quote(self._tag_map[tid])
            if page <= 1:
                return "%s/main/tag?name=%s" % (self.siteUrl, name)
            return "%s/main/tag?name=%s&page=%d" % (self.siteUrl, name, page)
        lineup = "recent_views" if tid == "cat_hot" else "create_time"
        if page <= 1:
            return "%s/main/tag?lineup=%s" % (self.siteUrl, lineup)
        return "%s/main/tag?lineup=%s&page=%d" % (self.siteUrl, lineup, page)

    def homeContent(self, filter):
        classes = [
            {"type_id": "cat_latest", "type_name": "最新"},
            {"type_id": "cat_hot", "type_name": "热门"},
            {"type_id": "cat_hdjav", "type_name": "高清日本AV"},
            {"type_id": "cat_chinese", "type_name": "中港台"},
            {"type_id": "cat_wife", "type_name": "人妻"},
            {"type_id": "cat_bigtits", "type_name": "巨乳"},
            {"type_id": "cat_amateur", "type_name": "素人"},
            {"type_id": "cat_teen", "type_name": "少女女友"},
            {"type_id": "cat_bj", "type_name": "口交"},
            {"type_id": "cat_creampie", "type_name": "中出"},
            {"type_id": "cat_cam", "type_name": "偷拍"},
            {"type_id": "cat_uniform", "type_name": "制服"},
            {"type_id": "cat_celeb", "type_name": "名人明星"},
            {"type_id": "cat_gangbang", "type_name": "多P"},
        ]
        result = {"class": classes}
        if filter:
            result["filters"] = {}
        return result

    def homeVideoContent(self):
        res = self.categoryContent("cat_latest", 1, False, {})
        return {"list": res.get("list", [])[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        page = 1
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        url = self._cat_url(tid, page)
        res = self._fetch(url)
        vod_list = self._parse_cards(res.get("text", ""))
        if not vod_list and page == 1:
            res = self._fetch(self.siteUrl + "/")
            vod_list = self._parse_cards(res.get("text", ""))
        return {
            "page": page,
            "pagecount": page + 1 if len(vod_list) >= 12 else page,
            "limit": 24,
            "total": 9999 if vod_list else 0,
            "list": vod_list,
        }

    def _extract_m3u8(self, html_text):
        results = []
        seen = set()
        for m in re.finditer(
            r"https?://(cdn-\d+\.porn87\.com)/media/image_1/([a-z0-9]+)(?:_\d+)?\.(?:jpg|png|webp)",
            html_text or "", re.I,
        ):
            cdn, h = m.group(1), m.group(2)
            if h in seen:
                continue
            seen.add(h)
            results.append("https://%s/media/video_1/%s.mp4/index.m3u8" % (cdn, h))
            break
        if results:
            return results
        emb = re.search(r"/main/embed\?id=(\d+)", html_text or "")
        if emb:
            er = self._fetch(self.siteUrl + "/main/embed?id=" + emb.group(1))
            for m in re.finditer(r"https?://cdn[^\"'\s]+\.m3u8[^\"'\s]*", er.get("text", ""), re.I):
                if m.group(0) not in seen:
                    results.append(m.group(0))
                    break
        return results

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        target = str(raw).strip()
        if not target.startswith("http"):
            target = urllib.parse.urljoin(self.siteUrl, target)
        res = self._fetch(target)
        html_text = res.get("text", "")
        if not html_text:
            return {"list": []}
        title_m = re.search(r"<title>(.*?)</title>", html_text, re.I)
        name = self._clean(title_m.group(1) if title_m else "") or "精彩视频"
        name = name.split("|")[0].strip()
        pic_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html_text, re.I)
        pic = self._abs(pic_m.group(1)) if pic_m else ""
        m3u8s = self._extract_m3u8(html_text)
        if not m3u8s:
            m3u8s = [target]
        return {
            "list": [{
                "vod_id": target,
                "vod_name": name,
                "vod_pic": pic,
                "vod_content": name,
                "vod_play_from": "Porn87",
                "vod_play_url": "正片$%s" % m3u8s[0],
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        play_url = str(id).strip()
        return {
            "parse": 0 if self.isVideoFormat(play_url) else 1,
            "jx": 0,
            "url": play_url,
            "header": {
                "User-Agent": self._ua,
                "Referer": self.siteUrl + "/",
                "Origin": self.siteUrl,
                "Accept": "*/*",
            },
        }

    def searchContent(self, key, quick, pg="1"):
        page = 1
        try:
            page = int(pg)
        except Exception:
            page = 1
        q = urllib.parse.quote(key or "")
        url = "%s/main/search?name=%s" % (self.siteUrl, q)
        if page > 1:
            url += "&page=%d" % page
        res = self._fetch(url)
        vod_list = self._parse_cards(res.get("text", ""))
        return {
            "page": page,
            "pagecount": page + 1 if len(vod_list) >= 12 else page,
            "limit": 24,
            "total": 9999 if vod_list else 0,
            "list": vod_list,
        }

    def action(self, action):
        return {"msg": "ok"}

    def liveContent(self):
        return ""

    def localProxy(self, params):
        return [404, "text/plain", ""]

    def destroy(self):
        self.options = {}
