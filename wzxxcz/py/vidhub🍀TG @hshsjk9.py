# coding=utf-8
"""
Vidhub视频库 vidhub.tv | TVBox Python 爬虫
网站结构 (MacCMS 自定义 mx 模板) :
  - 分类聚合页 /vodtype/{id}.html(无分页), 真正片库列表 /vodshow/{id}-{地区}-{排序}-{类型}-{语言}-{字母}---{页码}---{年份}.html
  - 详情页 /voddetail/{id}.html, 播放页 /vodplay/{id}-{sid}-{nid}.html
  - 播放页内 iframe /player/?u=... , 其返回页 var config={"url": 真实 m3u8} 明文
  - 搜索结果页有验证码, 改用 MacCMS 官方 JSON 接口 /index.php/ajax/suggest?mid=1&wd=&limit=
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
                print("[vidhub]", *a)
            except Exception:
                pass

    Spider = _BaseSpider


HOST = "https://vidhub.tv"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
DEFAULT_PIC = HOST + "/mxstatic/image/logo2.png"

INTRO_PREFIX = "🍊小橙子为您介绍剧情👉请不要相信视频中的广告，以免上当受骗！"

# 主导航(真实 tid)
CLASSES = [
    {"type_id": "1", "type_name": "电影"},
    {"type_id": "2", "type_name": "连续剧"},
    {"type_id": "3", "type_name": "综艺"},
    {"type_id": "4", "type_name": "动漫"},
]

_YEARS = [{"n": "全部", "v": ""}] + \
         [{"n": str(y), "v": str(y)} for y in range(2026, 1999, -1)]

_SORTS = [
    {"n": "最新", "v": "time"},
    {"n": "人气", "v": "hits"},
    {"n": "评分", "v": "score"},
]

# 筛选地区/语言/类型均来自片库页真实链接
_AREAS = ["", "大陆", "香港", "台湾", "美国", "法国", "英国", "日本", "韩国",
          "德国", "泰国", "印度", "意大利", "西班牙", "加拿大", "其他"]
_LANGS = ["", "国语", "英语", "粤语", "闽南语", "韩语", "日语", "法语",
          "德语", "其它", "汉语普通话"]

# 各主分类下的真实子类型(/vodshow/1---类型)
_CLASS_MAP = {
    "1": ["喜剧", "爱情", "恐怖", "动作", "科幻", "剧情", "战争", "警匪",
          "犯罪", "动画", "奇幻", "武侠", "冒险", "枪战", "悬疑", "惊悚",
          "经典", "青春", "文艺", "微电影", "古装", "历史", "运动", "农村",
          "儿童", "网络电影"],
    "2": ["大陆", "香港", "台湾", "日本", "韩国", "欧美", "泰国", "印度",
          "英国", "美国", "法国", "加拿大", "其他", "剧情", "喜剧", "爱情",
          "古装", "奇幻", "武侠", "科幻", "悬疑", "战争", "历史", "都市"],
    "3": ["大陆综艺", "港台综艺", "日韩综艺", "欧美综艺", "真人秀", "脱口秀",
          "音乐", "舞蹈", "美食", "旅行", "游戏", "晚会"],
    "4": ["国产动漫", "欧美动漫", "日韩动漫", "动漫电影", "热血", "搞笑",
          "恋爱", "少女", "科幻", "治愈", "冒险", "校园"],
}


def _opt(values):
    return [{"n": "全部", "v": ""}] + [{"n": x, "v": x} for x in values]


FILTERS = {}
for c in CLASSES:
    tid = c["type_id"]
    FILTERS[tid] = [
        {"key": "class", "name": "类型", "value": _opt(_CLASS_MAP.get(tid, []))},
        {"key": "area", "name": "地区", "value": _opt([a for a in _AREAS if a])},
        {"key": "lang", "name": "语言", "value": _opt([x for x in _LANGS if x])},
        {"key": "year", "name": "年份", "value": _YEARS},
        {"key": "sort", "name": "排序", "value": _SORTS},
    ]


# ===================== 正则 =====================
# 列表卡片(module-item): pic链接 + 标题 + 封面 + 备注
_RE_ITEM_START = re.compile(r'<div class="module-item">')
_RE_DETAIL_HREF = re.compile(
    r'<div class="module-item-pic">\s*<a[^>]*href="(/voddetail/\d+\.html)"[^>]*'
    r'(?:title="([^"]*)")?', re.S)
_RE_IMG = re.compile(r'<img[^>]*?(?:data-src|data-original|src)="([^"]+)"', re.S)
_RE_TITLEBOX = re.compile(
    r'<div class="module-item-titlebox">\s*<a[^>]*title="([^"]*)"', re.S)
_RE_REMARK = re.compile(r'<div class="module-item-text">([^<]*)</div>', re.S)

# 详情
_RE_H1 = re.compile(r'<h1[^>]*class="page-title"[^>]*>(.*?)</h1>', re.S | re.I)
_RE_TITLE_GEN = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S | re.I)
_RE_COVER = re.compile(r'<div class="video-cover">[\s\S]{0,800}?<img[^>]*?'
                       r'(?:data-src|data-original|src)="([^"]+)"', re.S)
_RE_OG_IMG = re.compile(r'property="og:image"[^>]*content="([^"]+)"', re.I)
# 信息行: 每个 <div class="video-info-items"> 以紧邻的下一个同级 items 切分
_RE_INFO_ITEM = re.compile(
    r'<span class="video-info-itemtitle">([^<]*)：</span>'
    r'<div class="video-info-item[^"]*">(.*?)</div></div>', re.S)
_RE_META_DESC = re.compile(
    r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', re.I)
# aux 标签区(类型/年份/地区)
_RE_AUX = re.compile(r'class="video-info-aux[^"]*"[^>]*>(.*?)</div>\s*</div>',
                     re.S)
# 播放节点 tab (线路名, 按出现顺序对应 sid=1..N)
_RE_TAB_ITEM = re.compile(
    r'<div class="module-tab-item tab-item"[^>]*data-dropdown-value="([^"]+)"',
    re.S)
# 每个播放列表 glist-N, 以下一个 glist 或选集播放区之后的模块为界
_RE_GLIST_HEAD = re.compile(r'id="glist-(\d+)"')
_RE_EP = re.compile(
    r'<a[^>]*href="(/vodplay/(\d+)-(\d+)-(\d+)\.html)"[^>]*>(.*?)</a>', re.S)

# 播放页 iframe
_RE_IFRAME = re.compile(r'<iframe[^>]*id="player_if"[^>]*src="([^"]+)"', re.I)
# /player/ 页 config
_RE_CONFIG_URL = re.compile(r'"url"\s*:\s*"([^"]+)"')


def _parse_config_url(raw):
    """解析 /player/ 返回页 config JSON 里的真实地址, 兼容 \\/ 转义。"""
    if not raw:
        return ""
    s = raw.strip()
    # 先直接 json 片段
    m = re.search(r'var\s+config\s*=\s*(\{.*?\})\s*;', s, re.S)
    target = m.group(1) if m else s
    target = target.replace('\\/', '/')
    mm = _RE_CONFIG_URL.search(target)
    return mm.group(1) if mm else ""


class Spider(Spider):

    def getName(self):
        return "Vidhub视频库"

    def init(self, extend=""):
        try:
            self.extend = json.loads(extend) if extend else {}
        except Exception:
            self.extend = {}
        self.site_url = (self.extend.get("site") or HOST).rstrip("/")
        self.headers = {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.site_url + "/",
            "Upgrade-Insecure-Requests": "1",
        }
        self.default_pic = DEFAULT_PIC
        self._play_cache = {}
        self.log("init: site=%s" % self.site_url)

    def _fetch(self, url, timeout=30, headers=None, encoding="utf-8"):
        try:
            h = dict(self.headers)
            if headers:
                h.update(headers)
            rsp = self.fetch(url, headers=h, timeout=timeout)
            if hasattr(rsp, "apparent_encoding") and rsp.apparent_encoding:
                try:
                    rsp.encoding = rsp.apparent_encoding
                except Exception:
                    pass
            if hasattr(rsp, "text"):
                return rsp.text or ""
            if hasattr(rsp, "content"):
                return rsp.content.decode(encoding, "ignore")
            return str(rsp)
        except Exception as e:
            self.log("fetch FAIL %s -> %s" % (url, e))
            return ""

    def _fix_url(self, url):
        if not url:
            return ""
        url = url.strip().replace("&amp;", "&")
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
        s = re.sub(r"&#(\d+);",
                   lambda m: chr(int(m.group(1)))
                   if int(m.group(1)) < 0x110000 else m.group(0), s)
        s = re.sub(r"&#x([0-9a-fA-F]+);",
                   lambda m: chr(int(m.group(1), 16))
                   if int(m.group(1), 16) < 0x110000 else m.group(0), s)
        s = re.sub(r"[ \t\r\f\v]+", " ", s)
        s = re.sub(r"\n{2,}", "\n", s)
        return s.strip()

    # ============ 列表卡片解析 ============
    def _extract_videos(self, html):
        videos = []
        seen = set()
        if not html:
            return videos
        # 以 module-item 切块, 规避卡片顺序/可选字段差异
        starts = [m.start() for m in _RE_ITEM_START.finditer(html)]
        for idx, st in enumerate(starts):
            ed = starts[idx + 1] if idx + 1 < len(starts) else st + 4000
            block = html[st:ed]

            mh = _RE_DETAIL_HREF.search(block)
            if not mh:
                continue
            href = mh.group(1)
            if href in seen:
                continue
            seen.add(href)

            name = ""
            mt = _RE_TITLEBOX.search(block)
            if mt:
                name = self._clean(mt.group(1))
            if not name and mh.group(2):
                name = self._clean(mh.group(2))
            if not name:
                mi = _RE_IMG.search(block)
                if mi:
                    name = self._clean(mi.group(0))

            pic = ""
            mi = _RE_IMG.search(block)
            if mi:
                pic = mi.group(1)
            # 丢掉懒加载占位图(百度 bkimg 占位)
            if "bkimg.cdn.bcebos.com" in pic or "loading" in pic:
                pic = ""
                mm = re.search(r'data-src="([^"]+)"', block)
                if mm:
                    pic = mm.group(1)

            remark = ""
            mr = _RE_REMARK.search(block)
            if mr:
                remark = self._clean(mr.group(1))

            videos.append({
                "vod_id": href,
                "vod_name": name[:100] or href,
                "vod_pic": self._fix_url(pic) or self.default_pic,
                "vod_remarks": remark,
            })
        return videos

    def _max_page(self, html):
        """片库页尾页: vodshow 12段中第8段(index=8)为页码"""
        nums = []
        for u in re.findall(r'/vodshow/([^"#\s]+\.html)', html):
            core = u[:-5] if u.endswith('.html') else u
            parts = core.split('-')
            if len(parts) >= 12 and parts[8].isdigit():
                nums.append(int(parts[8]))
        return max(nums) if nums else 1

    # ============ TVBox 接口 ============
    def homeContent(self, filter=False):
        return {"class": CLASSES, "filters": FILTERS}

    def homeVideoContent(self):
        html = self._fetch(self.site_url + "/")
        videos = self._extract_videos(html)
        return {"list": videos}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if isinstance(extend, str):
            try:
                extend = json.loads(extend)
            except Exception:
                extend = {}
        extend = extend or {}

        # vodshow 12 段: tid-地区-排序-类型-语言-字母---页码---年份
        seg = [""] * 12
        seg[0] = str(tid)
        if extend.get("area"):
            seg[1] = urllib.parse.quote(extend["area"])
        if extend.get("sort"):
            seg[2] = extend["sort"]
        if extend.get("class"):
            seg[3] = urllib.parse.quote(extend["class"])
        if extend.get("lang"):
            seg[4] = urllib.parse.quote(extend["lang"])
        # seg[5] 字母, seg[6][7] 保留
        seg[8] = str(page)
        # seg[9][10] 保留
        if extend.get("year"):
            seg[11] = str(extend["year"])

        path = "/vodshow/%s.html" % "-".join(seg)
        url = self.site_url + path
        self.log("category: %s" % url)
        html = self._fetch(url)
        videos = self._extract_videos(html)
        pagecount = self._max_page(html)
        self.log("  列表 %d 条, pagecount=%d" % (len(videos), pagecount))
        return {
            "list": videos, "page": page, "pagecount": pagecount,
            "limit": 72, "total": pagecount * 72,
        }

    def _suggest(self, wd, limit=100):
        url = ("%s/index.php/ajax/suggest?mid=1&wd=%s&limit=%d"
               % (self.site_url, urllib.parse.quote(wd), limit))
        txt = self._fetch(url, headers={"X-Requested-With": "XMLHttpRequest"})
        try:
            data = json.loads(txt)
        except Exception:
            return []
        out = []
        for it in (data.get("list") or []):
            pic = it.get("pic") or ""
            out.append({
                "vod_id": "/voddetail/%s.html" % it.get("id"),
                "vod_name": it.get("name") or str(it.get("id")),
                "vod_pic": self._fix_url(pic) or self.default_pic,
                "vod_remarks": "",
            })
        return out

    def searchContent(self, key, quick, pg="1"):
        # 搜索结果页有验证码, 用官方 suggest JSON 接口(单页返回全部匹配)
        videos = self._suggest(key)
        self.log("search '%s' -> %d 条" % (key, len(videos)))
        return {"list": videos, "page": 1, "pagecount": 1,
                "limit": len(videos) or 1, "total": len(videos)}

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

        # 标题
        name = ""
        m = _RE_H1.search(html)
        if m:
            name = self._clean(m.group(1))
        if not name:
            m = _RE_TITLE_GEN.search(html)
            if m:
                name = self._clean(m.group(1))
        if not name:
            m = re.search(r"<title>(.*?)</title>", html, re.S)
            if m:
                name = self._clean(
                    re.split(r"[-_|]", m.group(1))[0]).strip("《》 ")
        name = name or vod_id

        # 封面
        pic = self.default_pic
        m = _RE_COVER.search(html)
        if m:
            pic = self._fix_url(m.group(1))
        if not pic or pic == self.default_pic:
            m = _RE_OG_IMG.search(html)
            if m:
                pic = self._fix_url(m.group(1))

        # 信息行: 逐项解析 title / body
        director = actor = year = area = type_name = remarks = ""
        content = ""
        for label, body in _RE_INFO_ITEM.findall(html):
            label = label.strip()
            if label in ("剧情", "简介"):
                # 剧情 body 内含"收起/展开"链接, 清理掉
                c = re.sub(r'<a[^>]*>.*?</a>', "", body, flags=re.S)
                c = self._clean(c)
                if c:
                    content = c
                continue
            text = self._clean(body)
            text = re.sub(r"^[/\s]+", "", text)
            text = re.sub(r"\s*/\s*", ", ", text).strip(" /,，")
            if label == "导演":
                director = text
            elif label == "主演":
                actor = text
            elif label in ("上映", "年份"):
                if not year:
                    year = text
            elif label == "地区":
                area = text
            elif label == "类型":
                if not type_name:
                    type_name = text
            elif label == "备注":
                remarks = text
            # 更新 / 集数 / 总集数 / 评分 不进入基础字段

        # 年份规范化为 4 位
        my = re.search(r"(?:19|20)\d{2}", year)
        year = my.group(0) if my else ""

        # aux 区: 按 vodshow 链接的参数段位置精确定位
        # 12段: tid-地区-排序-类型-语言-字母---页码---年份
        maux = _RE_AUX.search(html)
        if maux:
            aux_types, aux_area = [], ""
            for href, txt in re.findall(
                    r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                    maux.group(1), re.S):
                t = self._clean(txt)
                if not t or "/vodshow/" not in href:
                    continue
                core = href.split("/vodshow/")[-1].replace(".html", "")
                p = core.split("-")
                if len(p) >= 12:
                    if p[3]:
                        aux_types.append(urllib.parse.unquote(p[3]))
                    if p[1] and not aux_area:
                        aux_area = urllib.parse.unquote(p[1])
                    if p[11] and not year:
                        year = p[11]
            if not type_name and aux_types:
                # 去掉与主分类同名的大类标签, 只留具体子类型
                subs = [x for x in aux_types if x not in
                        ("电影", "连续剧", "电视剧", "综艺", "动漫", "动画")]
                type_name = ",".join(subs or aux_types)
            if not area and aux_area:
                area = aux_area

        # 剧情兜底
        if not content or content in ("内详", "暂无"):
            m = _RE_META_DESC.search(html)
            if m:
                dc = self._clean(m.group(1))
                if dc and "为您提供" not in dc:
                    content = dc
        if content and content not in ("内详", "暂无"):
            vod_content = INTRO_PREFIX + "\n" + content
        else:
            vod_content = INTRO_PREFIX

        # ===== 线路 + 剧集 =====
        tab_names = [self._clean(x) for x in _RE_TAB_ITEM.findall(html)]

        # 以所有 glist-N 锚点切分, 边界为下一个 glist 或选集播放区结束
        heads = [(m.start(), int(m.group(1)))
                 for m in _RE_GLIST_HEAD.finditer(html)]
        groups = {}
        for idx, (st, sid) in enumerate(heads):
            ed = heads[idx + 1][0] if idx + 1 < len(heads) else st + 200000
            seg = html[st:ed]
            eps = []
            seen_ep = set()
            for em in _RE_EP.finditer(seg):
                ep_vid, ep_sid, ep_nid = em.group(2), em.group(3), em.group(4)
                if int(ep_sid) != sid:
                    continue
                ep_href = em.group(1)
                if ep_href in seen_ep:
                    continue
                seen_ep.add(ep_href)
                ep_name = self._clean(em.group(5)) or ("第%s集" % ep_nid)
                eps.append((ep_name, self._fix_url(ep_href)))
            if eps:
                groups[sid] = eps

        # 线路名: tab 按文档顺序与 sid=1..N 对应
        play_from, play_url = [], []
        for idx, sid in enumerate(sorted(groups.keys())):
            line = (tab_names[idx] if idx < len(tab_names)
                    else "线路%d" % sid)
            eps = groups[sid]
            play_from.append(line)
            play_url.append("#".join("%s$%s" % (n, h) for n, h in eps))

        vod_remarks = remarks or ("%d条线路" % len(groups))

        return {"list": [{
            "vod_id": vod_id,
            "vod_name": name,
            "vod_pic": pic or self.default_pic,
            "vod_content": vod_content,
            "vod_actor": actor,
            "vod_director": director,
            "vod_year": year,
            "vod_area": area,
            "vod_type": type_name,
            "vod_remarks": vod_remarks,
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url),
        }]}

    # ============ 播放 ============
    def playerContent(self, flag, id, vipFlags):
        play_page = id if str(id).startswith("http") else self._fix_url(id)
        now = int(time.time())
        if play_page in self._play_cache:
            ts, res = self._play_cache[play_page]
            if now - ts < 600:
                return res

        res = {"parse": 1, "playUrl": "", "url": play_page,
               "header": {"User-Agent": UA, "Referer": self.site_url + "/"}}

        html = self._fetch(play_page)
        iframe = ""
        if html:
            m = _RE_IFRAME.search(html)
            if m:
                iframe = m.group(1).replace("&amp;", "&")

        if iframe:
            iframe_url = self._fix_url(iframe)
            sub = self._fetch(
                iframe_url,
                headers={"Referer": play_page,
                         "Accept": "text/html,application/xhtml+xml,*/*"})
            real = _parse_config_url(sub)
            if real:
                real = real.replace("\\/", "/")
                real = urllib.parse.unquote(real)
                if real.startswith("http"):
                    res = {
                        "parse": 0,
                        "playUrl": "",
                        "url": real,
                        "header": {
                            "User-Agent": UA,
                            "Referer": self.site_url + "/",
                        },
                    }
        self._play_cache[play_page] = (now, res)
        return res
