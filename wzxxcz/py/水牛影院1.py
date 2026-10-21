# coding=utf-8
"""
火龙果影视 | TVBox Python 爬虫
自动生成于 Spider AutoGen — 请按需微调正则后再上线
生成状态: 列表已命中 / 详情已命中 / 播放页 direct-m3u8
"""
import re
import sys
import json
import time
import hashlib
import urllib.parse

sys.path.append('..')

try:
    from base.spider import Spider
except ImportError:
    import requests as _rq
    try:
        import urllib3
        urllib3.disable_warnings()
    except Exception:
        pass

    class _BaseSpider:
        def __init__(self):
            self._session = None

        @property
        def _sess(self):
            if self._session is None:
                self._session = _rq.Session()
                self._session.verify = False
                adapter = _rq.adapters.HTTPAdapter(
                    pool_connections=10, pool_maxsize=10, max_retries=0)
                self._session.mount('https://', adapter)
                self._session.mount('http://', adapter)
            return self._session

        def fetch(self, url, headers=None, **kw):
            timeout = kw.pop('timeout', 15)
            r = self._sess.get(url, headers=headers, timeout=timeout, **kw)
            r.encoding = 'utf-8'
            return r

        def log(self, *a, **kw):
            try:
                print("[spider]", *a)
            except Exception:
                pass

    Spider = _BaseSpider


HOST = 'https://www.gljade.com'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
DEFAULT_PIC = HOST + '/favicon.ico'

INTRO_PREFIX = '🍊小橙子为您介绍剧情👉请不要相信视频中的广告，以免上当受骗！'

CLASSES = [
    {"type_id": 'rss', "type_name": 'Sogou'},
    {"type_id": 'map', "type_name": '网站地图'},
    {"type_id": 'medialist', "type_name": '更多'},
    {"type_id": 'label', "type_name": '最近更新'},
    {"type_id": 'cat', "type_name": '短剧'},
]

_YEARS = [{"n": "全部", "v": ""}] + [{"n": y, "v": y} for y in ('2018', '2017', '2016', '2015', '2014', '2013', '2012', '2011', '2010', '2019', '2020', '2021', '2022', '2023', '2024', '2025', '2026')]
_AREAS = [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in ('中国大陆', '美国', '日本', '韩国', '中国香港', '中国台湾', '英国', '法国', '德国', '印度', '泰国')]
_SORTS = [{"n": "热度最高", "v": 'play_hot'}, {"n": "最新更新", "v": 'time'}]

FILTERS = {
    c["type_id"]: [
        {"key": "class", "name": "分类", "value": [{"n": "全部", "v": ""}]},
        {"key": "area", "name": "地区", "value": _AREAS},
        {"key": "year", "name": "年份", "value": _YEARS},
        {"key": "sort_field", "name": "排序", "value": _SORTS},
    ] for c in CLASSES
}


# ===================== 正则 =====================
# 列表卡片片段: <a class="text-overflow" href="/video/957168.html" title="余红旧事">余红旧事</a>
_RE_CARD = re.compile(
    r'href="(/video/[^"]+?\.html)[^"]*"[^>]*>'
    r'[\s\S]{0,200}?'
    r'<img[^>]*?alt="([^"]*)"[^>]*?src="([^"]*)"',
    re.S | re.I)
_RE_HREF = re.compile(r'href="(/video/[^"]+?\.html)', re.I)
_RE_IMG = re.compile(
    r'<img[^>]*?alt="([^"]*)"[^>]*?src="([^"]*)"',
    re.S | re.I)

_RE_EPISODE_A = re.compile(r'<a\s+href="([^"]+)"([^>]*?)>(.*?)</a>', re.S | re.I)
_RE_DATA_ORIGIN = re.compile(r'data-origin="([^"]+)"', re.I)
_RE_DATA_TITLE = re.compile(r'data-title="([^"]+)"', re.I)
_RE_BTN_TITLE = re.compile(r'<button[^>]*>([^<]+)</button>', re.I)

_RE_H1 = re.compile(r'<h1[^>]*>([\s\S]*?)</h1>', re.I)
_RE_OG_IMG = re.compile(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)', re.I)
_RE_INTRO = re.compile(r'<span[^>]*>\s*简介\s*[:：]\s*</span>\s*([\s\S]*?)</div>', re.S | re.I)
_RE_META_DESC = re.compile(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', re.I)
_RE_DIRECTOR = re.compile(r'导演\s*[:：]\s*([^\s\n主]{1,40})')
_RE_ACTOR = re.compile(r'主演\s*[:：]\s*([^\n]{1,100})')
_RE_SCORE = re.compile(r'(?:score|rating|badge)[^>]*>\s*([\d.]{1,4})\s*<', re.I)

# PoW 挑战页特征
_RE_POW_HASH = re.compile(r"var\s+hash\s*=\s*['\"]([a-f0-9]{40})['\"]")
_RE_POW_TARGET = re.compile(r"var\s+target\s*=\s*['\"]([a-f0-9]{40})['\"]")

_LINE_PRIORITY = ['vip', '1080zyk', 'bfzym3u8', 'ffm3u8', 'lzm3u8', 'modum3u8', 'jsm3u8', 'mtm3u8']
_LINE_ALIAS = {
    'vip': 'VIP线路', '1080zyk': '1080资源', 'bfzym3u8': '暴风资源',
    'ffm3u8': '非凡M3U8', 'lzm3u8': '量子M3U8', 'modum3u8': '魔都M3U8',
    'jsm3u8': '极速M3U8', 'mtm3u8': '茅台M3U8',
}


class Spider(Spider):

    def getName(self):
        return '火龙果影视'

    def init(self, extend=""):
        try:
            self.extend = json.loads(extend) if extend else {}
        except Exception:
            self.extend = {}
        self.site_url = (self.extend.get("site") or HOST).rstrip("/")
        self.headers = {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.site_url + "/",
        }
        self.default_pic = DEFAULT_PIC
        self._play_cache = {}
        self.log("init:", self.site_url)

    def _solve_pow(self, html):
        m1 = _RE_POW_HASH.search(html)
        m2 = _RE_POW_TARGET.search(html)
        if not m1 or not m2:
            return None
        prefix_b = m1.group(1).encode()
        target = m2.group(1)
        start = time.time()
        for i in range(10 * 1000 * 1000):
            if hashlib.sha1(prefix_b + str(i).encode()).hexdigest() == target:
                self.log("PoW 破解成功:", i, "耗时 %.2fs" % (time.time() - start))
                return i
            if (i + 1) % 1000000 == 0 and time.time() - start > 60:
                self.log("PoW 超时")
                return None
        return None

    def _fetch(self, url, timeout=30, headers=None):
        try:
            h = dict(self.headers)
            if headers:
                h.update(headers)
            rsp = self.fetch(url, headers=h, timeout=timeout)
            text = rsp.text if hasattr(rsp, "text") else (
                rsp.content.decode("utf-8", "ignore") if hasattr(rsp, "content") else str(rsp))
            if "attack_key" in text and "sha1(hash" in text:
                self.log("遇到 PoW 挑战")
                key = self._solve_pow(text)
                if key is not None:
                    sep = "&" if "?" in url else "?"
                    text = self._fetch(url + sep + "attack_key=" + str(key), timeout, headers)
                return text
            return text
        except Exception as e:
            self.log("fetch FAIL", url, e)
            return ""

    def _fix_url(self, url):
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.site_url + url
        return urllib.parse.urljoin(self.site_url + "/", url)

    def _clean(self, s):
        if not s:
            return ""
        s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
        s = re.sub(r"<[^>]+>", "", s)
        s = s.replace("&nbsp;", " ").replace("\xa0", " ").replace("&amp;", "&")
        s = s.replace('&quot;', '"').replace('&#39;', "'").replace('&lt;', '<').replace('&gt;', '>')
        return re.sub(r"[ \t\r\f\v]+", " ", s).strip()

    def _extract_videos(self, html):
        videos, seen = [], set()
        if not html:
            return videos

        def _pair(a, b):
            return self._clean(a)[:100], b

        for href, a, b in _RE_CARD.findall(html):
            href = href.replace("&amp;", "&")
            if href in seen:
                continue
            seen.add(href)
            name, pic = _pair(a, b)
            videos.append({"vod_id": href, "vod_name": name or href,
                           "vod_pic": self._fix_url(pic) or self.default_pic,
                           "vod_remarks": ""})
        if videos:
            return videos
        hrefs, imgs = _RE_HREF.findall(html), _RE_IMG.findall(html)
        for i, href in enumerate(hrefs):
            if href in seen:
                continue
            seen.add(href)
            name, pic = _pair(*(imgs[i] if i < len(imgs) else ("", "")))
            videos.append({"vod_id": href, "vod_name": name or href,
                           "vod_pic": self._fix_url(pic) or self.default_pic,
                           "vod_remarks": ""})
        return videos

    def _page_count(self, html):
        pages = re.findall(r"page=(\d+)", html)
        if pages:
            try:
                return max(int(p) for p in pages) + 1
            except Exception:
                pass
        return 9999

    def homeContent(self, filter=False):
        return {"class": CLASSES, "filters": FILTERS}

    def homeVideoContent(self):
        html = self._fetch(self.site_url + "/")
        return {"list": self._extract_videos(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if isinstance(extend, str):
            try:
                extend = json.loads(extend)
            except Exception:
                extend = {}
        extend = extend or {}
        for k in list(extend.keys()):
            if extend[k] in ("", None, "全部"):
                del extend[k]
        params = {"page": page - 1}
        for k in ("class", "year", "area", "sort_field"):
            if extend.get(k):
                params[k] = extend[k]
        url = self.site_url + "/" + tid + ".html?" + urllib.parse.urlencode(params)
        html = self._fetch(url)
        videos = self._extract_videos(html)
        pc = self._page_count(html)
        return {"list": videos, "page": page, "pagecount": pc, "limit": 24, "total": pc * 24}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        url = self.site_url + "/search?wd=" + urllib.parse.quote(key) + "&page=" + str(page)
        html = self._fetch(url)
        return {"list": self._extract_videos(html), "page": page,
                "pagecount": self._page_count(html), "limit": 24, "total": 999}

    def searchContentPage(self, key, quick, pg="1"):
        return self.searchContent(key, quick, pg)

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = str(ids[0])
        url = vod_id if vod_id.startswith("http") else self._fix_url(vod_id)
        html = self._fetch(url)
        if not html:
            return {"list": []}
        name = ""
        m = _RE_H1.search(html)
        if m:
            name = self._clean(m.group(1))
        if not name:
            m = re.search(r"<title>(.*?)</title>", html, re.S)
            if m:
                name = self._clean(m.group(1).split("_")[0].split("-")[0])
        name = re.sub(r"\s*\(\d{4}\)\s*$", "", name).strip() or vod_id
        pic = self.default_pic
        m = _RE_OG_IMG.search(html)
        if m:
            pic = self._fix_url(m.group(1))
        content = ""
        for rx in (_RE_INTRO, _RE_META_DESC):
            m = rx.search(html)
            if m and self._clean(m.group(1)):
                content = self._clean(m.group(1))
                break
        content = (INTRO_PREFIX + "\n" + content) if content else INTRO_PREFIX
        director = actor = score = ""
        plain = self._clean(html)
        m = _RE_DIRECTOR.search(plain)
        if m:
            director = m.group(1).strip()
        m = _RE_ACTOR.search(plain)
        if m:
            actor = m.group(1).strip()
        m = _RE_SCORE.search(html)
        if m:
            score = m.group(1)
        groups = {}
        for m in _RE_EPISODE_A.finditer(html):
            href, attrs, inner = m.group(1), m.group(2), m.group(3)
            mo = _RE_DATA_ORIGIN.search(attrs)
            if mo:
                origin = mo.group(1)
            elif "/play/" in href:
                origin = (href.split("/play/")[-1].split("/")[0]) or "line1"
            else:
                continue
            href = href.replace("&amp;", "&")
            if href.startswith("/"):
                href = self.site_url + href
            ep = ""
            mt = _RE_DATA_TITLE.search(attrs)
            if mt:
                ep = self._clean(mt.group(1))
            if not ep:
                mt = _RE_BTN_TITLE.search(inner)
                if mt:
                    ep = self._clean(mt.group(1))
            if not ep:
                ep = "第%d集" % (len(groups.get(origin, [])) + 1)
            groups.setdefault(origin, []).append((ep, href))
        if not groups:
            return {"list": []}
        origins = sorted(groups.keys(),
                         key=lambda x: _LINE_PRIORITY.index(x) if x in _LINE_PRIORITY else 999)
        play_from, play_url = [], []
        for o in origins:
            play_from.append(_LINE_ALIAS.get(o, o))
            play_url.append("#".join("%s$%s" % (n, h) for n, h in groups[o]))
        return {"list": [{
            "vod_id": vod_id, "vod_name": name, "vod_pic": pic,
            "vod_content": content, "vod_actor": actor, "vod_director": director,
            "vod_score": score, "vod_remarks": "%d条线路" % len(groups),
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url),
        }]}

    def playerContent(self, flag, id, vipFlags):
        play_page = id if id.startswith("http") else self._fix_url(id)
        now = int(time.time())
        if play_page in self._play_cache:
            ts, res = self._play_cache[play_page]
            if now - ts < 600:
                return res
        html = self._fetch(play_page)
        api_url = self._extract_api(html)

        if api_url:
            if api_url.startswith("http") and ".m3u8" in api_url.lower():
                res = {"parse": 0, "playUrl": "", "url": api_url,
                       "header": {"User-Agent": UA, "Referer": self.site_url + "/"}}
                self._play_cache[play_page] = (now, res)
                return res
            if api_url.startswith("/"):
                api_url = self.site_url + api_url
            real = self._resolve_to_real_m3u8(api_url, referer=play_page)
            if real:
                res = {"parse": 0, "playUrl": "", "url": real,
                       "header": {"User-Agent": UA, "Referer": self._box_referer()}}
                self._play_cache[play_page] = (now, res)
                return res
        res = {"parse": 1, "playUrl": "", "url": play_page,
               "header": {"User-Agent": UA, "Referer": self.site_url + "/"}}
        self._play_cache[play_page] = (now, res)
        return res

    def _box_referer(self):
        return self.site_url + "/"

    def _extract_api(self, html):
        if not html:
            return ""
        m = re.search(r"JSON\.parse\(\s*'([\s\S]{10,4000}?)'\s*\)", html)
        if m:
            raw = m.group(1).replace("\\u0026", "&").replace("\\/", "/")
            try:
                return json.loads(raw).get("url", "")
            except Exception:
                m2 = re.search(r'"url"\s*:\s*"([^"]+)"', raw)
                if m2:
                    return m2.group(1).replace("&amp;", "&")
        m = re.search(r"player_\w*\s*=\s*\{[\s\S]{0,3000}?\}", html)
        if m:
            m2 = re.search(r'"url"\s*:\s*"([^"]+)"', m.group(0))
            if m2:
                return m2.group(1).replace("&amp;", "&")
        m = re.search(r"(?:src|url|source|video)\s*[:=]\s*['\"]([^'\"]*(?:\.m3u8|/api/m3u8)[^'\"]*)", html, re.I)
        return m.group(1).replace("&amp;", "&") if m else ""

    def _resolve_to_real_m3u8(self, api_url, referer=None):
        try:
            rsp = self.fetch(api_url, headers={"User-Agent": UA,
                                              "Referer": referer or (self.site_url + "/")},
                             timeout=15, allow_redirects=False)
        except TypeError:
            rsp = self.fetch(api_url, headers={"User-Agent": UA,
                                              "Referer": referer or (self.site_url + "/")}, timeout=15)
        except Exception as e:
            self.log("resolve fail", e)
            return ""
        loc = ""
        if hasattr(rsp, "headers") and rsp.headers:
            loc = rsp.headers.get("Location") or rsp.headers.get("location") or ""
        if not loc:
            txt = getattr(rsp, "text", "") or ""
            return api_url if "#EXTM3U" in txt else ""
        if loc.startswith("//"):
            loc = "https:" + loc
        loc = loc.replace("&amp;", "&")
        try:
            rsp2 = self.fetch(loc, headers={"User-Agent": UA, "Referer": api_url}, timeout=15)
            txt2 = getattr(rsp2, "text", "") or ""
        except Exception as e:
            self.log("master fail", e)
            return loc
        if "#EXTM3U" not in txt2:
            return loc
        lines = [x.strip() for x in txt2.split("\n") if x.strip()]
        base = self._box_referer()[:-1] or loc.rsplit("/", 1)[0]
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF") and i + 1 < len(lines):
                sub = lines[i + 1].strip()
                if sub.startswith("http"):
                    return sub
                return base + "/" + sub.lstrip("/")
        return loc

    def localProxy(self, param):
        try:
            url = ""
            if isinstance(param, dict):
                url = param.get("url", "")
            else:
                for pair in str(param).split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        if k == "url":
                            url = v
            if not url:
                return [200, "image/jpeg", b"", ""]
            url = urllib.parse.unquote(url) if "%" in url else url
            url = self._fix_url(url)
            rsp = self.fetch(url, headers={"User-Agent": UA,
                                    "Referer": self.site_url + "/"}, timeout=15)
            ctype = rsp.headers.get("Content-Type", "image/jpeg") if hasattr(rsp, "headers") else "image/jpeg"
            if not ctype.startswith("image/"):
                ctype = "image/jpeg"
            return [200, ctype, rsp.content, ""]
        except Exception:
            return [200, "image/jpeg", b"", ""]

    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def close(self):
        self.destroy()

