# -*- coding: utf-8 -*-
import json
import re
import urllib.parse
from bs4 import BeautifulSoup
from base.spider import Spider


class Spider(Spider):
    # 默认备用主域名
    siteUrl = "https://seajav.com"

    # 轮询域名候选列表
    domainList = [
        #"https://seajav.com",
        "https://seajav1.xyz",
        "https://seajav2.xyz",
        "https://seajav3.xyz",
        "https://seajav4.xyz",
        "https://seajav5.xyz",
        "https://seajav6.xyz",
        "https://seajav7.xyz",
        "https://seajav8.xyz",
        "https://seajav9.xyz",
    ]

    # 动态 Header (Referer 会随着当前生效的主域名自动更新)
    @property
    def header(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{self.siteUrl}/",
        }

    def getName(self):
        return "seajav"

    # 初始化：依次轮询测试域名可用性，锁定第一个成功响应的域名
    def init(self, extend=""):
        for domain in self.domainList:
            try:
                test_header = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": f"{domain}/",
                }
                rsp = self.fetch(domain, headers=test_header, timeout=5)
                if rsp and rsp.status_code == 200:
                    self.siteUrl = domain
                    break
            except Exception:
                continue

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def action(self, action):
        pass

    # 1. 首页分类与筛选设置
    def homeContent(self, filter):
        result = {}
        classes = [
            {"type_name": "最新", "type_id": "99"},
            {"type_name": "国产自拍", "type_id": "1"},
            {"type_name": "日本AV", "type_id": "2"},
            {"type_name": "91porn", "type_id": "3"},
            {"type_name": "国产AV", "type_id": "4"},
        ]

        sort_options = [
            {"n": "发行日期", "v": "time"},
            {"n": "最近更新", "v": "score"},
            {"n": "浏览数", "v": "hits"},
        ]

        filters = {
            "99": [{"key": "by", "name": "排序", "value": sort_options}],
            "1": [
                {
                    "key": "cateId",
                    "name": "子分类",
                    "value": [
                        {"n": "全部", "v": "1"},
                        {"n": "91探花", "v": "38"},
                        {"n": "自拍流出", "v": "13"},
                    ],
                },
                {"key": "by", "name": "排序", "value": sort_options},
            ],
            "2": [
                {
                    "key": "cateId",
                    "name": "子分类",
                    "value": [
                        {"n": "全部", "v": "2"},
                        {"n": "高清AV", "v": "6"},
                        {"n": "无码AV", "v": "7"},
                        {"n": "中文字幕AV", "v": "8"},
                        {"n": "无码流出", "v": "9"},
                        {"n": "三上悠亚AV", "v": "10"},
                        {"n": "FC2PPV", "v": "11"},
                        {"n": "素人AV", "v": "40"},
                    ],
                },
                {"key": "by", "name": "排序", "value": sort_options},
            ],
            "3": [
                {
                    "key": "cateId",
                    "name": "子分类",
                    "value": [
                        {"n": "全部", "v": "3"},
                        {"n": "91视频", "v": "20"},
                        {"n": "福利姬", "v": "14"},
                        {"n": "AI明星", "v": "41"},
                    ],
                },
                {"key": "by", "name": "排序", "value": sort_options},
            ],
            "4": [
                {
                    "key": "cateId",
                    "name": "子分类",
                    "value": [
                        {"n": "全部", "v": "4"},
                        {"n": "麻豆视频", "v": "21"},
                        {"n": "91制片厂", "v": "22"},
                        {"n": "天美传媒", "v": "23"},
                        {"n": "蜜桃传媒", "v": "24"},
                        {"n": "星空传媒", "v": "26"},
                        {"n": "精东影业", "v": "27"},
                        {"n": "糖心Vlog", "v": "37"},
                        {"n": "杏吧视频", "v": "39"},
                    ],
                },
                {"key": "by", "name": "排序", "value": sort_options},
            ],
        }

        result["class"] = classes
        if filter:
            result["filters"] = filters
        return result

    # 2. 首页推荐内容
    def homeVideoContent(self):
        try:
            rsp = self.fetch(self.siteUrl, headers=self.header)
            root = BeautifulSoup(rsp.text, "html.parser")
            return {"list": self._parse_vod_list(root)}
        except Exception:
            return {"list": []}

    # 3. 分类/筛选列表加载
    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        page = int(pg)

        cate_id = tid
        if extend and "cateId" in extend and extend["cateId"]:
            cate_id = extend["cateId"]

        by = "time"
        if extend and "by" in extend and extend["by"]:
            by = extend["by"]

        url = f"{self.siteUrl}/show/{cate_id}/by/{by}/page/{page}.html"

        rsp = self.fetch(url, headers=self.header)
        root = BeautifulSoup(rsp.text, "html.parser")

        vod_list = self._parse_vod_list(root)

        result["page"] = page
        result["pagecount"] = page + 1 if len(vod_list) > 0 else page
        result["limit"] = 20
        result["total"] = 999
        result["list"] = vod_list
        return result

    # 4. 关键字搜索
    def searchContent(self, key, quick, pg="1"):
        result = {}
        page = int(pg)
        encoded_key = urllib.parse.quote(key)
        url = f"{self.siteUrl}/search/page/{page}/wd/{encoded_key}.html"

        rsp = self.fetch(url, headers=self.header)
        root = BeautifulSoup(rsp.text, "html.parser")

        vod_list = self._parse_vod_list(root)

        result["page"] = page
        result["pagecount"] = page + 1 if len(vod_list) > 0 else page
        result["limit"] = 20
        result["total"] = 999
        result["list"] = vod_list
        return result

    # 5. 影片详情页
    def detailContent(self, array):
        tid = array[0]
        url = tid if tid.startswith("http") else f"{self.siteUrl}{tid}"
        rsp = self.fetch(url, headers=self.header)
        html = rsp.text
        root = BeautifulSoup(html, "html.parser")

        title_el = root.select_one("h1.text-nord6") or root.select_one("h1") or root.select_one("title")
        title = title_el.get_text(strip=True) if title_el else "未知视频"

        img_el = root.select_one("div.aspect-w-16 img") or root.select_one("img")
        pic = self._extract_img_url(img_el, card_node=root)

        play_url = f"立即播放${url}"

        vod = {
            "vod_id": tid,
            "vod_name": title,
            "vod_pic": pic,
            "type_name": "视频",
            "vod_play_from": "SeaJAV",
            "vod_play_url": play_url,
        }

        return {"list": [vod]}

    # 6. 播放节点解析
    def playerContent(self, flag, id, vipFlags):
        url = id if id.startswith("http") else f"{self.siteUrl}{id}"

        pure_header = self.header

        rsp = self.fetch(url, headers=pure_header)
        html = rsp.text

        # 1. 优先捕获并解析 JS 中的 player_aaaa 配置
        player_json_match = re.search(r"var\s+player_aaaa\s*=\s*(\{.*?\}|\{.*?\n.*?\});", html, re.DOTALL)
        if player_json_match:
            try:
                config_data = json.loads(player_json_match.group(1))
                play_url = config_data.get("url", "").replace("\\/", "/")
                if play_url and (play_url.endswith(".m3u8") or play_url.endswith(".mp4") or play_url.startswith("http")):
                    return {
                        "parse": 0,
                        "url": play_url,
                        "header": pure_header,
                    }
            except Exception:
                pass

        # 2. 备用正则提取
        media_match = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4))', html)
        if media_match:
            return {
                "parse": 0,
                "url": media_match.group(1).replace("\\/", "/"),
                "header": pure_header,
            }

        # 3. 尝试提取 iframe 嵌入网页
        root = BeautifulSoup(html, "html.parser")
        iframe = root.select_one("iframe")
        if iframe and iframe.get("src"):
            iframe_url = iframe.get("src")
            if not iframe_url.startswith("http"):
                iframe_url = urllib.parse.urljoin(self.siteUrl, iframe_url)

            return {
                "parse": 1,
                "url": iframe_url,
                "header": {
                    "User-Agent": pure_header["User-Agent"],
                    "Referer": iframe_url,
                },
            }

        # 4. 兜底逻辑
        return {
            "parse": 1,
            "url": url,
            "header": pure_header,
        }

    # 内部公用图片提取辅助函数
    def _extract_img_url(self, img_tag, card_node=None):
        placeholder_keywords = ["cover.jpg", "placeholder", "loading", "blank", "default", "static/picture"]

        candidates = []
        if img_tag:
            attrs_to_check = [
                "data-original",
                "data-lazy-src",
                "data-src",
                "data-srcset",
                "srcset",
                "src",
            ]
            for attr in attrs_to_check:
                val = img_tag.get(attr, "")
                if val:
                    if " " in val.strip():
                        val = val.strip().split()[0]
                    candidates.append(val)

        if card_node:
            style_tags = card_node.find_all(style=True)
            for el in style_tags:
                style_str = el.get("style", "")
                bg_match = re.search(r'url\((["\']?)([^"\'\)]+)\1\)', style_str)
                if bg_match:
                    candidates.append(bg_match.group(2))

        valid_pic = ""
        for url in candidates:
            url_clean = url.strip()
            if not url_clean:
                continue

            is_placeholder = any(kw in url_clean.lower() for kw in placeholder_keywords)
            if not is_placeholder:
                valid_pic = url_clean
                break

        if not valid_pic and candidates:
            valid_pic = candidates[0].strip()

        if valid_pic:
            valid_pic = urllib.parse.urljoin(self.siteUrl, valid_pic)

        return valid_pic

    # 内部公用节点解析方法
    def _parse_vod_list(self, root):
        vod_list = []
        seen_ids = set()

        cards = root.select("div.thumbnail") or root.select("div.grid > div")

        for card in cards:
            a_tag = card.select_one("a[href]")
            if not a_tag:
                continue

            href = a_tag.get("href", "").strip()
            if not href or href == "#" or href.startswith("javascript") or href in seen_ids:
                continue

            seen_ids.add(href)

            title_tag = (
                card.select_one("div.truncate a")
                or card.select_one("div.my-2 a")
                or card.select_one("a.title")
                or a_tag
            )
            title = title_tag.get_text(strip=True) if title_tag else ""

            img_tag = card.select_one("img")
            if not title and img_tag and img_tag.get("alt"):
                title = img_tag.get("alt", "").strip()

            if not title:
                title = "未知标题"

            pic = self._extract_img_url(img_tag, card_node=card)

            remark_tag = card.select_one("span.absolute, span.badge")
            remark = remark_tag.get_text(strip=True) if remark_tag else ""

            vod_list.append(
                {
                    "vod_id": href,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remark,
                }
            )

        return vod_list
