# -*- coding: utf-8 -*-
import sys
import re
import json
import base64
import html as htmlmod
from urllib.parse import quote, unquote, urljoin

try:
    import requests
except ImportError:
    requests = None

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def homeContent(self, filter): return {}
        def homeVideoContent(self): return {}
        def categoryContent(self, tid, pg, filter, extend): return {}
        def detailContent(self, ids): return {}
        def playerContent(self, flag, id, vipFlags): return {}
        def searchContent(self, key, quick, pg="1"): return {}
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False
        def localProxy(self, param): return [200, "text/plain", b""]
        def destroy(self): pass
        def getName(self): return "Base"

class Spider(BaseSpider):
    def __init__(self):
        self.host = "https://4tw3gy653a.bulunhufait.buzz"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host + "/"
        }
        self.session = None
        if requests:
            self.session = requests.Session()
            self.session.headers.update(self.headers)
        self.seen = set()

    def init(self, extend=""):
        if extend and extend.startswith("http"):
            self.host = extend.rstrip("/")
            self.headers["Referer"] = self.host + "/"
            if self.session:
                self.session.headers.update(self.headers)

    def getName(self):
        return "bulunhufait"

    def destroy(self):
        if self.session:
            self.session.close()

    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url or ".flv" in url or ".ts" in url

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [200, "video/MP2T", b"", {}]

    def _req(self, url):
        if not self.session:
            return ""
        try:
            r = self.session.get(url, headers=self.headers, timeout=15, verify=False)
            r.encoding = "utf-8"
            return r.text
        except Exception:
            return ""

    def _fix(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return urljoin(self.host, url)
        if url.startswith("http"):
            return url
        return urljoin(self.host, "/" + url)

    def _clean(self, text):
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", str(text))
        return htmlmod.unescape(text).strip()

    def _parse_list(self, html_text):
        """精准提取列表中的图片和标题"""
        vod_list = []
        if not html_text:
            return vod_list

        dl_blocks = re.findall(r'<dl[^>]*>(.*?)</dl>', html_text, re.S | re.I)
        
        for block in dl_blocks:
            try:
                # 1. 提取 ID / 链接
                href_m = re.search(r'href=["\']([^"\']*/voddetail/[^"\']+)["\']', block, re.I)
                if not href_m:
                    continue
                href = href_m.group(1)
                vid_m = re.search(r'/voddetail/([0-9]+)/', href)
                vid = vid_m.group(1) if vid_m else href

                if vid in self.seen:
                    continue

                # 2. 提取标题
                title = ""
                dd_m = re.search(r'<dd[^>]*>(.*?)</dd>', block, re.S | re.I)
                if dd_m:
                    dd_content = dd_m.group(1)
                    h3_m = re.search(r'<h3[^>]*>(.*?)</h3>', dd_content, re.S | re.I)
                    if h3_m:
                        title = self._clean(h3_m.group(1))
                    else:
                        title = self._clean(dd_content)

                if not title:
                    alt_m = re.search(r'alt=["\']([^"\']+)["\']', block, re.I)
                    if alt_m:
                        title = self._clean(alt_m.group(1))

                if not title:
                    title = "未知影片"

                # 3. 精准提取图片逻辑 (排除 loading.svg，优先获取 data-original / data-src)
                pic = ""
                orig_m = re.search(r'data-original=["\']([^"\']+)["\']', block, re.I)
                if orig_m:
                    pic = orig_m.group(1)
                else:
                    datasrc_m = re.search(r'data-src=["\']([^"\']+)["\']', block, re.I)
                    if datasrc_m:
                        pic = datasrc_m.group(1)
                    else:
                        src_m = re.search(r'src=["\']([^"\']+)["\']', block, re.I)
                        if src_m and not "loading" in src_m.group(1):
                            pic = src_m.group(1)

                pic = self._fix(pic)
                
                # 为图片追加 Referer Header 解决图片防盗链拦截问题
                if pic and not pic.endswith("@Referer=" + self.host + "/"):
                    pic = f"{pic}@Referer={self.host}/"

                self.seen.add(vid)
                vod_list.append({
                    "vod_id": str(vid),
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": ""
                })
            except Exception:
                continue

        return vod_list

    def homeContent(self, filter):
        classes = [
            {"type_name": "制服诱惑", "type_id": "27"},
            {"type_name": "网红头条", "type_id": "317"},
            {"type_name": "主播网红", "type_id": "59"},
            {"type_name": "精东影业", "type_id": "430"},
            {"type_name": "麻豆资源", "type_id": "423"},
            {"type_name": "欧美美女", "type_id": "506"},
            {"type_name": "闷骚护士", "type_id": "97"},
            {"type_name": "探花约炮", "type_id": "276"},
            {"type_name": "主播诱惑", "type_id": "275"},
            {"type_name": "AV明星", "type_id": "144"},
            {"type_name": "AV解说", "type_id": "312"},
            {"type_name": "欧美", "type_id": "52"},
            {"type_name": "国产裸聊", "type_id": "374"},
            {"type_name": "三级伦理", "type_id": "163"},
            {"type_name": "国产自拍", "type_id": "274"},
            {"type_name": "国产视频", "type_id": "297"},
            {"type_name": "杏吧原创", "type_id": "435"},
            {"type_name": "极品媚黑", "type_id": "315"},
            {"type_name": "貧乳小奶", "type_id": "179"},
            {"type_name": "明星换脸", "type_id": "307"},
            {"type_name": "韩国主播", "type_id": "319"},
            {"type_name": "映画传媒", "type_id": "165"},
            {"type_name": "兔子先生", "type_id": "434"},
            {"type_name": "少女萝莉", "type_id": "361"},
            {"type_name": "家庭乱伦", "type_id": "397"},
            {"type_name": "女优明星", "type_id": "287"},
            {"type_name": "可爱学生", "type_id": "93"},
            {"type_name": "国产精品", "type_id": "49"},
            {"type_name": "禁漫", "type_id": "53"},
            {"type_name": "素人自拍", "type_id": "80"},
            {"type_name": "SM调教", "type_id": "401"},
            {"type_name": "瑜伽裤", "type_id": "96"},
            {"type_name": "群交淫乱", "type_id": "367"},
            {"type_name": "日本无码", "type_id": "301"}
        ]
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        return self.categoryContent("27", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}
        prefix = "arttype" if tid == "506" else "vodtype"
        if int(pg) == 1:
            url = f"{self.host}/{prefix}/{tid}/"
        else:
            url = f"{self.host}/{prefix}/{tid}-{pg}/"

        html_text = self._req(url)
        self.seen.clear()
        result["list"] = self._parse_list(html_text)

        plinks = re.findall(r'/(?:vod|art)type/\d+-(\d+)/', html_text)
        maxpg = 1
        for p in plinks:
            if p.isdigit() and int(p) > maxpg:
                maxpg = int(p)

        result["pagecount"] = maxpg if maxpg > 1 else (int(pg) + 1 if len(result["list"]) >= 24 else int(pg))
        return result

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        result = {"list": []}
        url = f"{self.host}/voddetail/{vid}/"
        html_text = self._req(url)
        if not html_text:
            return result

        title = ""
        tm = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.S | re.I)
        if tm:
            title = self._clean(tm.group(1))
        if not title:
            tm = re.search(r'<title>([^<]+)</title>', html_text, re.I)
            if tm:
                title = self._clean(tm.group(1)).split("-")[0].split("_")[0]
        if not title:
            title = str(vid)

        pic = ""
        pm = re.search(r'data-original=["\']([^"\']+)["\']', html_text, re.I)
        if not pm:
            pm = re.search(r'data-src=["\']([^"\']+)["\']', html_text, re.I)
        if pm:
            pic = self._fix(pm.group(1))
            if pic:
                pic = f"{pic}@Referer={self.host}/"

        sources = ["默认线路"]
        play_urls = []
        
        eps = re.findall(r'<a[^>]+href=["\'](/vodplay/[^"\']+)["\'][^>]*>(.*?)</a>', html_text, re.S | re.I)
        if eps:
            ep_list = []
            for href, ep_title in eps:
                ep_title = self._clean(ep_title) or "播放"
                ep_list.append(f"{ep_title}${self._fix(href)}")
            if ep_list:
                play_urls.append("#".join(ep_list))

        if not play_urls:
            play_urls = [f"播放正片${self.host}/vodplay/{vid}-1-1/"]

        result["list"].append({
            "vod_id": str(vid),
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": "",
            "vod_play_from": "$$$".join(sources),
            "vod_play_url": "$$$".join(play_urls)
        })
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}

        if self.isVideoFormat(id):
            result["url"] = id
            result["header"] = json.dumps({"Referer": self.host + "/", "User-Agent": self.headers["User-Agent"]})
            return result

        if "/vodplay/" in id or "http" in id:
            html_text = self._req(id)
            if html_text:
                m = re.search(r'player_data\s*=\s*(\{.*?\});', html_text, re.DOTALL)
                if m:
                    try:
                        data = json.loads(m.group(1))
                        purl = data.get("url", "")
                        encrypt = data.get("encrypt", 0)
                        if str(encrypt) == "1":
                            purl = unquote(purl)
                        elif str(encrypt) == "2":
                            purl = unquote(base64.b64decode(purl).decode("utf-8"))
                        if purl:
                            result["url"] = purl
                            result["header"] = json.dumps({"Referer": self.host + "/", "User-Agent": self.headers["User-Agent"]})
                            return result
                    except Exception:
                        pass

                m3u8 = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html_text)
                if m3u8:
                    result["url"] = m3u8.group(1)
                    result["header"] = json.dumps({"Referer": self.host + "/", "User-Agent": self.headers["User-Agent"]})
                    return result

        result["parse"] = 1
        result["url"] = id
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}
        url = f"{self.host}/vodsearch/-------------/?wd={quote(key)}&page={pg}"
        html_text = self._req(url)
        self.seen.clear()
        result["list"] = self._parse_list(html_text)
        return result
