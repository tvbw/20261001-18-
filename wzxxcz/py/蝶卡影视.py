# coding=utf-8
"""
蝶卡影视网 www.diekawang.com | TVBox Python 爬虫
================================================================
本爬虫严格依据网站真实源码编写，所有结构均已实测验证：

【已验证的真实结构】
  1. 首页/分类聚合页为 SSR 渲染：curl 直接可取到卡片
     - 卡片容器: <div class="moon-list-item">
     - 卡片链接: <a href="/vod/player/0/{影片ID}" class="item goLinklist">
     - 封面图  : <img data-original="..." src="..." class="cmslazyload">
     - 标题    : <p class="name item-title ohv-ellipsis">影片名</p>
     - 评分    : <label class="rate ml-20">5.2</label>
     - 在看人数: <span>39135人次在看</span>

  2. 分类/筛选（已验证，关键！）：
     - 真实分类列表 URL : /vod/list/{页码}/{顶层tid}/{子分类id}
       第1位=页码(从1开始)，第2位=顶层分类ID，第3位=子分类ID(0=全部)
       例: /vod/list/1/1/0    → 电影第1页
           /vod/list/3/1/0    → 电影第3页
           /vod/list/1/1/9    → 电影-动作片第1页(9=动作片)
           /vod/list/2/2/22   → 电视剧-国产剧第2页(22=国产剧)
           /vod/list/1/457/541 → 短剧-玄幻第1页(541=玄幻)
     - SSR 渲染，每页固定 10 个卡片，curl 直接可取
     - 子分类 typeId 来自筛选栏 <a class="btn">，完整映射见 _FILTERS_MAP
     - 分类聚合入口(菜单): /vod/1/{顶层tid}/0

  3. 播放页解密（核心，已实测通过）：
     - 页面内 JS 变量: var temLineList = [ {...}, {...} ]
     - 每集字段: {"file":"j8UaHR0cHM6...", "name":"第01集", "tag":"1080zyk", "id":990024}
     - 解密算法:
         raw   = file[3:]                    # 去掉首部3个随机字符
         url   = base64_decode(raw)          # Base64 解码
         url   = urldecode(url)              # URL 解码 → 真实 m3u8
       实测: j8UaHR0cHM6JTJGJTJGY2RuLnZ2dmlwLXBsYXlzMzMuY2MlMkY...
             → https://cdn.vvvip-plays33.cc/20251215/2142_2a34abd6/index.m3u8

作者注: 如网站改版，需按上述真实字段重新对照源码调整正则。
"""

import re
import sys
import json
import base64
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

    class _BaseSpider(object):
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
                print("[diekawang]", *a)
            except Exception:
                pass

    Spider = _BaseSpider


# ===================== 站点常量 =====================
HOST = "https://www.diekawang.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
DEFAULT_PIC = HOST + "/data/uploadFile/cskhyj.webp"

INTRO_PREFIX = "🍊小橙子为您介绍剧情👉请不要相信视频中的广告，以免上当受骗！"

# 顶层分类（对应 /vod/1/{typeId}/0）
CLASSES = [
    {"type_id": "1",   "type_name": "电影"},
    {"type_id": "2",   "type_name": "电视剧"},
    {"type_id": "3",   "type_name": "综艺"},
    {"type_id": "4",   "type_name": "动漫"},
    {"type_id": "457", "type_name": "短剧"},
    {"type_id": "462", "type_name": "纪录片"},
]

# 各分类下的子分类筛选（typeId 来源：分类页 a.btn，已逐页实测）
# 分类页真实格式: /vod/list/{页码}/{typeId}/0
_FILTERS_MAP = {
    # 电影（tid=1）
    "1": [
        ("全部", 1), ("动作片", 9), ("喜剧片", 10), ("爱情片", 11),
        ("恐怖片", 12), ("剧情片", 13), ("科幻片", 14), ("惊悚片", 15),
        ("奇幻片", 16), ("动画片", 17), ("悬疑片", 18), ("冒险片", 19),
        ("纪录片", 20), ("战争片", 21), ("倫理片", 460),
    ],
    # 电视剧（tid=2）
    "2": [
        ("全部", 2), ("国产剧", 22), ("香港剧", 23), ("台湾剧", 24),
        ("欧美剧", 25), ("日本剧", 26), ("韩国剧", 27), ("泰国剧", 28),
        ("海外剧", 29),
    ],
    # 综艺（tid=3）
    "3": [
        ("全部", 3), ("大陆综艺", 30), ("港台综艺", 31), ("日韩综艺", 32),
        ("欧美综艺", 33), ("海外综艺", 34),
    ],
    # 动漫（tid=4）
    "4": [
        ("全部", 4), ("国产动漫", 35), ("日韩动漫", 36), ("欧美动漫", 37),
        ("海外动漫", 38), ("港台动漫", 459),
    ],
    # 短剧（tid=457）
    "457": [
        ("全部", 457), ("漫剧", 540), ("玄幻", 541), ("剧情", 542),
        ("女性成长", 543), ("权谋", 544), ("豪门", 545), ("齐幻", 546),
        ("宫斗", 547), ("脑洞", 548), ("科幻", 549), ("冒险", 550),
        ("仙侠", 551), ("喜剧", 552), ("动作", 553), ("悬疑", 554),
        ("战神", 555), ("刑侦", 556), ("求生", 557), ("商战", 558),
        ("恐怖", 559), ("武侠", 560), ("爱情", 561), ("AI漫剧", 562),
        ("擦边剧", 563),
    ],
    # 纪录片（tid=462）
    "462": [
        ("全部", 462),
    ],
}

FILTERS = {}
for c in CLASSES:
    tid = c["type_id"]
    _sub = _FILTERS_MAP.get(tid, [("全部", 0)])
    FILTERS[tid] = [
        {"key": "class", "name": "分类",
         "value": [{"n": n, "v": str(v)} for n, v in _sub]},
    ]


# ===================== 正则（全部依据真实源码） =====================
# 卡片块：<div class="moon-list-item"> ... </div>（用非贪婪跨行）
_RE_CARD_BLOCK = re.compile(
    r'<div[^>]*class="[^"]*moon-list-item[^"]*"[^>]*>(.*?)</div>\s*</div>\s*(?=<div[^>]*class="[^"]*moon-list-item|</div>\s*</div>|$)',
    re.S | re.I)
# 卡片链接
_RE_CARD_A = re.compile(r'<a\s+href="(/vod/player/0/\d+)"[^>]*>', re.I)
# 封面
_RE_CARD_PIC = re.compile(
    r'<img[^>]*?(?:data-original|data-src|src)="([^"]+)"', re.I)
# 标题
_RE_CARD_NAME = re.compile(
    r'<p[^>]*class="[^"]*item-title[^"]*"[^>]*>\s*([\s\S]*?)\s*</p>', re.I)
# 评分
_RE_CARD_RATE = re.compile(
    r'<label[^>]*class="[^"]*rate[^"]*"[^>]*>\s*([\d.]+)\s*</label>', re.I)
# 在看人数
_RE_CARD_WATCH = re.compile(r'>\s*([\d,]+)人次在看\s*<', re.I)

# 播放页核心数据
_RE_LINELIST = re.compile(r'var\s+temLineList\s*=\s*(\[[\s\S]*?\])\s*;', re.S)

# 详情页标题
_RE_H1 = re.compile(r'<h1[^>]*>([\s\S]*?)</h1>', re.I)
_RE_TITLE = re.compile(r'<title>([\s\S]*?)</title>', re.I)

# 线路 tag → 别名
_LINE_ALIAS = {
    "1080zyk": "1080资源", "lzm3u8": "量子M3U8", "bfzym3u8": "暴风资源",
    "dyttm3u8": "电影天堂", "ffm3u8": "非凡M3U8", "wjm3u8": "无尽M3U8",
    "modum3u8": "魔都M3U8", "jsm3u8": "极速M3U8", "mtm3u8": "茅台M3U8",
    "vip": "VIP线路", "wztv": "王者TV",
}
_LINE_PRIORITY = ["vip", "1080zyk", "wztv", "bfzym3u8", "dyttm3u8",
                  "ffm3u8", "lzm3u8", "modum3u8", "jsm3u8", "mtm3u8"]


class Spider(Spider):

    def getName(self):
        return "蝶卡影视"

    def init(self, extend=""):
        try:
            self.extend = json.loads(extend) if extend else {}
        except Exception:
            self.extend = {}

        self.site_url = (self.extend.get("site") or HOST).rstrip("/")
        self.headers = {
            "User-Agent": UA,
            "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
                       "image/avif,image/webp,*/*;q=0.8"),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.site_url + "/",
        }
        self.default_pic = DEFAULT_PIC
        self._play_cache = {}
        self.log("init: site=%s" % self.site_url)

    # ------------------ 基础工具 ------------------
    def _fetch(self, url, timeout=20, headers=None):
        try:
            h = dict(self.headers)
            if headers:
                h.update(headers)
            rsp = self.fetch(url, headers=h, timeout=timeout)
            if hasattr(rsp, "text"):
                return rsp.text or ""
            if hasattr(rsp, "content"):
                return rsp.content.decode("utf-8", "ignore")
            return str(rsp)
        except Exception as e:
            self.log("fetch FAIL %s -> %s" % (url, e))
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
        s = (s.replace("&nbsp;", " ").replace("\xa0", " ")
              .replace("&amp;", "&").replace("&quot;", '"')
              .replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">"))
        s = re.sub(r"[ \t\r\f\v]+", " ", s)
        s = re.sub(r"\n{2,}", "\n", s)
        return s.strip()

    # ------------------ 列表解析 ------------------
    def _extract_videos(self, html):
        """从 SSR HTML 中解析卡片列表（严格按真实 class 结构）"""
        videos = []
        seen = set()
        if not html:
            return videos

        # 按 moon-list-item 卡片块切分
        blocks = re.findall(
            r'<div[^>]*class="[^"]*moon-list-item[^"]*"[^>]*>([\s\S]*?)</a>\s*</div>',
            html, re.I)
        self.log("  卡片块: %d 个" % len(blocks))

        for blk in blocks:
            ma = _RE_CARD_A.search(blk)
            if not ma:
                continue
            href = ma.group(1)
            if href in seen:
                continue
            seen.add(href)

            mp = _RE_CARD_PIC.search(blk)
            pic = self._fix_url(mp.group(1)) if mp else self.default_pic

            mn = _RE_CARD_NAME.search(blk)
            name = self._clean(mn.group(1)) if mn else ""

            mr = _RE_CARD_RATE.search(blk)
            rate = mr.group(1) if mr else ""

            mw = _RE_CARD_WATCH.search(blk)
            watch = mw.group(1) if mw else ""

            remarks = ""
            if rate:
                remarks = "评分%s" % rate
            if watch:
                remarks = ("%s %s人在看" % (remarks, watch)).strip()

            videos.append({
                "vod_id": href,
                "vod_name": name or href.rsplit("/", 1)[-1],
                "vod_pic": pic or self.default_pic,
                "vod_remarks": remarks,
            })
        return videos

    # ------------------ 首页 ------------------
    def homeContent(self, filter=False):
        return {"class": CLASSES, "filters": FILTERS}

    def homeVideoContent(self):
        url = self.site_url + "/index.html"
        html = self._fetch(url)
        self.log("home HTML: %d" % len(html))
        return {"list": self._extract_videos(html)}

    # ------------------ 分类 ------------------
    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if isinstance(extend, str):
            try:
                extend = json.loads(extend)
            except Exception:
                extend = {}
        extend = extend or {}

        sub = extend.get("class")
        try:
            sub_id = int(sub) if sub not in (None, "", "全部") else 0
        except Exception:
            sub_id = 0

        # 真实格式: /vod/list/{页码}/{顶层tid}/{子分类id}
        #   子分类 id=0 表示全部；国产剧=22 等（extend["class"] 传入）
        type_id = sub_id if sub_id else 0

        url = "%s/vod/list/%d/%s/%d" % (self.site_url, page, tid, type_id)
        self.log("category: %s" % url)
        html = self._fetch(url)
        videos = self._extract_videos(html)

        # 从分页条解析真实总页数（/vod/list/{页}/{tid}/0）
        pagecount = 9999
        pages = re.findall(r'/vod/list/(\d+)/\d+/\d+', html or "")
        if pages:
            try:
                pagecount = max(int(p) for p in pages)
            except Exception:
                pass

        return {
            "list": videos, "page": page, "pagecount": pagecount,
            "limit": 10, "total": pagecount * 10,
        }

    # ------------------ 搜索 ------------------
    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        kw = urllib.parse.quote(key)
        # 真实搜索页: /search/index.html（结果由前端渲染）
        url = "%s/search/index.html?name=%s&page=%d" % (self.site_url, kw, page)
        self.log("search: %s" % url)
        html = self._fetch(url)
        videos = self._extract_videos(html)
        # 部分搜索走 /vod/search 兼容
        if not videos:
            alt = "%s/search/%s----------%d---.html" % (self.site_url, kw, page)
            html2 = self._fetch(alt)
            videos = self._extract_videos(html2)
        return {"list": videos, "page": page, "pagecount": 9999,
                "limit": 24, "total": 999999}

    def searchContentPage(self, key, quick, pg="1"):
        return self.searchContent(key, quick, pg)

    # ------------------ 详情 ------------------
    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = str(ids[0])
        url = vod_id if vod_id.startswith("http") else self._fix_url(vod_id)
        self.log("detail: %s" % url)

        html = self._fetch(url)
        self.log("  HTML: %d" % len(html))
        if not html:
            return {"list": []}

        # 标题
        name = ""
        m = _RE_H1.search(html)
        if m:
            name = self._clean(m.group(1))
        if not name:
            m = _RE_TITLE.search(html)
            if m:
                name = self._clean(m.group(1).split("_")[-1].split("-")[-1])
        name = re.sub(r"\s*\(\d{4}\)\s*$", "", name).strip() or vod_id

        # 封面
        pic = self.default_pic
        m = re.search(r'<img[^>]*?(?:data-original|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"',
                      html, re.I)
        if m:
            pic = self._fix_url(m.group(1))

        # 简介（优先 meta description）
        content = ""
        m = re.search(
            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
            html, re.I)
        if m:
            content = self._clean(m.group(1))
        content = INTRO_PREFIX + ("\n" + content if content else "")

        # 剧集：核心 temLineList
        lines = self._parse_lines(html)
        self.log("  线路: %s" % {k[0]: len(v) for k, v in lines.items()})

        if not lines:
            # 无剧集数据时，至少返回单集=当前页
            return {"list": [{
                "vod_id": vod_id, "vod_name": name, "vod_pic": pic,
                "vod_content": content, "vod_remarks": "单集",
                "vod_play_from": "默认",
                "vod_play_url": "%s$%s" % (name, url),
            }]}

        sorted_tags = sorted(
            lines.keys(),
            key=lambda x: (_LINE_PRIORITY.index(x[0])
                           if x[0] in _LINE_PRIORITY else 999))

        play_from = []
        play_url = []
        for tag_key in sorted_tags:
            tag = tag_key[0]
            eps = lines[tag_key]
            play_from.append(_LINE_ALIAS.get(tag, tag or "线路"))
            play_url.append("#".join("%s$%s" % (n, u) for n, u in eps))

        return {"list": [{
            "vod_id": vod_id,
            "vod_name": name,
            "vod_pic": pic,
            "vod_content": content,
            "vod_actor": "",
            "vod_director": "",
            "vod_remarks": "%d条线路" % len(play_from),
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url),
        }]}

    def _parse_lines(self, html):
        """解析 var temLineList，按 tag 分组，返回 {(tag,): [(集名, 播放页url), ...]}"""
        result = {}
        m = _RE_LINELIST.search(html)
        if not m:
            self.log("  未找到 temLineList")
            return result
        try:
            data = json.loads(m.group(1))
        except Exception as e:
            self.log("  temLineList JSON 解析失败: %s" % e)
            return result

        for item in data:
            tag = item.get("tag") or "line"
            ep_name = item.get("name") or item.get("subTitle") or ""
            vid = item.get("videoID") or ""
            line_id = item.get("id") or ""
            play_url = "%s/vod/player/%s/%s" % (self.site_url, line_id, vid)
            key = (tag,)
            result.setdefault(key, []).append((ep_name, play_url))
        return result

    # ------------------ 播放 ------------------
    def playerContent(self, flag, id, vipFlags):
        play_page = id if id.startswith("http") else self._fix_url(id)
        self.log("player: %s" % play_page)

        # 命中缓存
        if play_page in self._play_cache:
            return self._play_cache[play_page]

        html = self._fetch(play_page)
        m = _RE_LINELIST.search(html)

        if m:
            try:
                data = json.loads(m.group(1))
            except Exception:
                data = []
            # 精确定位当前集：用 URL 中的 line_id (/vod/player/{line_id}/{vid})
            target = None
            mm = re.search(r'/vod/player/(\d+)/', play_page)
            if mm:
                cur_id = mm.group(1)
                for it in data:
                    if str(it.get("id")) == cur_id:
                        target = it
                        break
            # 兜底：取第一条（播放页通常把当前集排在首位）
            if target is None and data:
                target = data[0]

            if target:
                raw_file = target.get("file") or ""
                real = self._decode_file(raw_file)
                if real:
                    res = {
                        "parse": 0,
                        "playUrl": "",
                        "url": real,
                        "header": {
                            "User-Agent": UA,
                            "Referer": self.site_url + "/",
                        },
                    }
                    self._play_cache[play_page] = res
                    self.log("  => m3u8: %s" % real[:160])
                    return res

        # 兜底：交给 TVBox 嗅探
        res = {"parse": 1, "playUrl": "", "url": play_page,
               "header": {"User-Agent": UA, "Referer": self.site_url + "/"}}
        self._play_cache[play_page] = res
        return res

    def _decode_file(self, raw_file):
        """真实解密: file[3:] -> Base64 -> URL解码 -> m3u8"""
        if not raw_file:
            return ""
        # 若本身已是明文 m3u8
        if raw_file.startswith("http") and ".m3u8" in raw_file.lower():
            return raw_file
        try:
            body = raw_file[3:]                      # 去掉首部3个随机字符
            body += "=" * (-len(body) % 4)           # 补齐 Base64 padding
            dec = base64.b64decode(body).decode("utf-8", "ignore")
            url = urllib.parse.unquote(dec)
            if url.startswith("//"):
                url = "https:" + url
            return url
        except Exception as e:
            self.log("  解密失败: %s" % e)
            return ""

    # ------------------ 图片代理 ------------------
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
            rsp = self.fetch(url, headers={
                "User-Agent": UA, "Referer": self.site_url + "/"}, timeout=15)
            content = rsp.content
            ctype = rsp.headers.get("Content-Type", "image/jpeg")
            if not ctype.startswith("image/"):
                ctype = "image/jpeg"
            return [200, ctype, content, ""]
        except Exception:
            return [200, "image/jpeg", b"", ""]

    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url or url.startswith("http")

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def close(self):
        self.destroy()
