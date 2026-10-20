# coding=utf-8
"""
枫叶影院 926dy.com | TVBox Python 爬虫 
关键:
  - 真实分类结构：完美还原 /type/{id}/area/{area}/year/{year}/page/{page}.html 的拼接逻辑
  - 真实筛选栏：严格根据顶级分类动态生成真实的“地区”和“年份”选项
  - 真实卡片提取：解析静态 HTML (匹配 a.thumb、img[data-original]、span.state)
  - 真实播放页：解析 JS 变量 player_aaaa，提取 url 字段并用 unquote 解码真实的 m3u8 直链
  - 真实搜索接口：POST 提交到 /search/-------------.html，参数 wd
"""
import re
import sys
import json
import time
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
                adapter = _rq.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=0)
                self._session.mount('https://', adapter)
                self._session.mount('http://', adapter)
            return self._session

        def fetch(self, url, headers=None, **kw):
            timeout = kw.pop('timeout', 15)
            r = self._sess.get(url, headers=headers, timeout=timeout, **kw)
            r.encoding = 'utf-8'
            return r
            
        def post(self, url, data=None, headers=None, **kw):
            timeout = kw.pop('timeout', 15)
            r = self._sess.post(url, data=data, headers=headers, timeout=timeout, **kw)
            r.encoding = 'utf-8'
            return r

        def log(self, *a, **kw):
            try:
                print("[926dy]", *a)
            except Exception:
                pass

    Spider = _BaseSpider

HOST = "https://www.926dy.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

INTRO_PREFIX = "🍊小橙子为您介绍剧情👉请不要相信视频中的广告，以免上当受骗！"

CLASSES = [
    {"type_id": "1",  "type_name": "电影"},
    {"type_id": "2",  "type_name": "连续剧"},
    {"type_id": "3",  "type_name": "综艺"},
    {"type_id": "4",  "type_name": "动漫"},
    {"type_id": "34", "type_name": "短剧"},
]

# 严格提取自真实网页的筛选选项
_FILTERS_MAP = {
    "1": {
        "area": ["大陆", "香港", "台湾", "美国", "法国", "英国", "日本", "韩国", "德国", "泰国", "印度", "意大利", "西班牙", "加拿大", "其他"],
        "year": [str(y) for y in range(2026, 1999, -1)]
    },
    "2": {
        "area": ["内地", "韩国", "香港", "台湾", "日本", "美国", "泰国", "英国", "新加坡", "其他"],
        "year": [str(y) for y in range(2026, 1999, -1)]
    },
    "3": {
        "area": ["内地", "港台", "日韩", "欧美"],
        "year": [str(y) for y in range(2026, 1999, -1)]
    },
    "4": {
        "area": ["国产", "日本", "欧美", "其他"],
        "year": [str(y) for y in range(2026, 1999, -1)]
    },
    "34": {
        "year": [str(y) for y in range(2026, 2020, -1)]
    }
}

FILTERS = {}
for tid in _FILTERS_MAP:
    f_list = []
    if "area" in _FILTERS_MAP[tid]:
        f_list.append({
            "key": "area", "name": "地区",
            "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in _FILTERS_MAP[tid]["area"]]
        })
    if "year" in _FILTERS_MAP[tid]:
        f_list.append({
            "key": "year", "name": "年份",
            "value": [{"n": "全部", "v": ""}] + [{"n": y, "v": y} for y in _FILTERS_MAP[tid]["year"]]
        })
    FILTERS[tid] = f_list

# 真实列表卡片结构
_RE_CARD = re.compile(
    r'<a\s+href="(/post/\d+\.html)"\s+class="thumb"[^>]*>\s*'
    r'<img[^>]*?data-original="([^"]+)"[^>]*>\s*'
    r'<span\s+class="state">([^<]*)</span>[\s\S]*?'
    r'<h5\s+class="subject">\s*<a[^>]*>([^<]+)</a>',
    re.I
)

class Spider(Spider):
    def getName(self):
        return "枫叶影院"

    def init(self, extend=""):
        self.headers = {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Referer": HOST + "/",
        }

    def _fetch(self, url, headers=None, post_data=None):
        try:
            h = dict(self.headers)
            if headers: h.update(headers)
            
            if post_data:
                rsp = self.post(url, data=post_data, headers=h, timeout=15)
            else:
                rsp = self.fetch(url, headers=h, timeout=15)
            return rsp.text if hasattr(rsp, "text") else str(rsp)
        except Exception as e:
            self.log("fetch FAIL %s -> %s" % (url, e))
            return ""

    def _clean(self, s):
        if not s: return ""
        s = re.sub(r"<[^>]+>", "", s)
        s = (s.replace("&nbsp;", " ").replace("\xa0", " ")
              .replace("&amp;", "&").replace("&quot;", '"')
              .replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">"))
        return s.strip()

    def _extract_videos(self, html):
        videos = []
        seen = set()
        for m in _RE_CARD.finditer(html):
            href, pic, state, name = m.groups()
            if href in seen: continue
            seen.add(href)
            videos.append({
                "vod_id": href,
                "vod_name": self._clean(name),
                "vod_pic": pic if pic.startswith("http") else HOST + pic,
                "vod_remarks": self._clean(state)
            })
        return videos

    def homeContent(self, filter=False):
        return {"class": CLASSES, "filters": FILTERS}

    def homeVideoContent(self):
        html = self._fetch(HOST + "/")
        return {"list": self._extract_videos(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if isinstance(extend, str):
            try: extend = json.loads(extend)
            except Exception: extend = {}
        
        area = extend.get("area", "")
        year = extend.get("year", "")
        
        # 严格按照真实网页 URL 结构拼接
        url = f"{HOST}/type/{tid}"
        if area: url += f"/area/{urllib.parse.quote(area)}"
        if year: url += f"/year/{year}"
        if page > 1: url += f"/page/{page}"
        url += ".html"

        self.log(f"Category URL: {url}")
        html = self._fetch(url)
        videos = self._extract_videos(html)

        # 解析最大页码
        pagecount = 1
        m = re.search(r'href="[^"]*?/page/(\d+)/[^"]*?" title="末页"', html)
        if m:
            pagecount = int(m.group(1))
        else:
            pages = re.findall(r'/page/(\d+)', html)
            if pages: pagecount = max(int(p) for p in pages)

        return {
            "list": videos, "page": page, "pagecount": pagecount,
            "limit": 24, "total": pagecount * 24,
        }

    def searchContent(self, key, quick, pg="1"):
        url = f"{HOST}/search/-------------.html"
        post_data = {"wd": key}
        html = self._fetch(url, post_data=post_data)
        videos = self._extract_videos(html)
        return {
            "list": videos, "page": 1, "pagecount": 1, "limit": 24, "total": len(videos)
        }

    def detailContent(self, ids):
        if not ids: return {"list": []}
        vod_id = ids[0]
        url = vod_id if vod_id.startswith("http") else HOST + vod_id
        
        html = self._fetch(url)
        if not html: return {"list": []}

        # 标题
        name = ""
        m = re.search(r'<h1 class="article-subject-m">([^<]+)</h1>', html)
        if m: name = self._clean(m.group(1))

        # 封面
        pic = ""
        m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if m: pic = m.group(1)

        # 简介
        content = ""
        m = re.search(r'<div style="text-indent: 28px;">([\s\S]*?)</div>', html)
        if m: content = self._clean(m.group(1))
        content = INTRO_PREFIX + "\n" + content if content else INTRO_PREFIX

        # 导演与演员
        director, actor = "", ""
        m = re.search(r'<label>导演：</label><span>([^<]+)</span>', html)
        if m: director = self._clean(m.group(1))
        m = re.search(r'<label>主演：</label><span>([^<]+)</span>', html)
        if m: actor = self._clean(m.group(1))

        # 线路与剧集
        play_from = []
        play_url = []
        
        nav_match = re.search(r'<ul class="nav nav-tabs swiper-wrapper">([\s\S]*?)</ul>', html)
        if nav_match:
            lines = re.findall(r'class="tab-nav">([^<]+)</a>', nav_match.group(1))
            for line in lines:
                play_from.append(line.strip())
        
        rb_items = re.findall(r'<div class="rb-item"[^>]*>([\s\S]*?)</div>', html)
        for rb in rb_items:
            eps = re.findall(r'<li><a href="(/watch/[^"]+)">([^<]+)</a></li>', rb)
            if eps:
                play_url.append("#".join(f"{name}${HOST}{href}" for href, name in eps))
            else:
                play_url.append("")

        if len(play_from) != len(play_url):
            play_from = [f"线路{i+1}" for i in range(len(play_url))]

        return {"list": [{
            "vod_id": vod_id,
            "vod_name": name,
            "vod_pic": pic,
            "vod_content": content,
            "vod_director": director,
            "vod_actor": actor,
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url)
        }]}

    def playerContent(self, flag, id, vipFlags):
        url = id if id.startswith("http") else HOST + id
        html = self._fetch(url, headers={"Referer": HOST + "/"})

        m = re.search(r'var player_aaaa=(\{.*?\})</script>', html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                if "url" in data:
                    real_url = urllib.parse.unquote(data["url"])
                    return {
                        "parse": 0,
                        "playUrl": "",
                        "url": real_url,
                        "header": {"User-Agent": UA, "Referer": HOST + "/"}
                    }
            except Exception as e:
                self.log(f"JSON 解析失败: {e}")

        return {"parse": 1, "playUrl": "", "url": url, "header": {"User-Agent": UA}}

    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def close(self):
        self.destroy()
