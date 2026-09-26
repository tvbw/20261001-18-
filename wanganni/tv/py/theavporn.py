import json
import re
import sys
from bs4 import BeautifulSoup

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        pass


class Spider(Spider):
    def getName(self):
        return "TheAV"

    def init(self, extend=""):
        self.siteUrls = [
            "https://theav03.com",
            "https://theav04.com",
            "https://theav05.com",
            "https://theavporn.com",
            "https://theav02.com"
        ]
        self.siteUrl = self.siteUrls[0]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": self.siteUrl
        }

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def fetch_with_fallback(self, path, parse_func):
        candidates = [self.siteUrl] + [u for u in self.siteUrls if u != self.siteUrl]

        for host in candidates:
            req_path = path if path.startswith('/') else f"/{path}"
            req_url = f"{host}{req_path}"
            headers = self.headers.copy()
            headers["Referer"] = host

            try:
                rsp = self.fetch(req_url, headers=headers, timeout=8)
                if not rsp or not rsp.text:
                    continue

                soup = BeautifulSoup(rsp.text, 'html.parser')
                data, vod_list = parse_func(soup, host, rsp.text)

                if vod_list and len(vod_list) > 0:
                    self.siteUrl = host
                    self.headers["Referer"] = host
                    return data
            except Exception:
                continue

        return {'list': []}

    def homeContent(self, filter):
        result = {}
        classes = [
            {"type_name": "最新", "type_id": "/new/"},
            {"type_name": "热门", "type_id": "/most-popular/"},
            {"type_name": "相册", "type_id": "/albums/"},
            {"type_name": "分类", "type_id": "/categories/"},
            {"type_name": "影星", "type_id": "/models/"}
        ]
        result['class'] = classes
        return result

    def homeVideoContent(self):
        return self.categoryContent('/new/', 1, None, None)

    # -------------------------------------------------------------------------
    # 原版 categoryContent（确保分类列表副标题如播放数/时长正常）
    # -------------------------------------------------------------------------
    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)
        req_path = tid if tid.startswith('/') else f"/{tid}"
        clean_path = req_path.split('?')[0].rstrip('/')

        is_catalog_root = clean_path in ["/models", "/categories"]
        is_album_page = clean_path.startswith("/albums")

        if is_album_page:
            sub_path = f"/albums/{page}/" if page > 1 else "/albums/"
        else:
            sub_path = f"{clean_path}/?from={page}" if page > 1 else f"{clean_path}/"

        def parse_page(soup, current_host, raw_html):
            vod_list = []

            if is_catalog_root:
                cat_items = soup.select("div.thumbs div.thumb") or \
                            soup.select("#list_categories_categories_list_items div.thumb") or \
                            soup.select("#list_models_models_list_items div.thumb")

                for item in cat_items:
                    a_tag = item.select_one("a.item") or item.select_one("a.th") or item.select_one("a")
                    if not a_tag:
                        continue
                    href = a_tag.get("href", "").strip()
                    if not href:
                        continue

                    sub_tid = href.replace(current_host, "") if href.startswith(current_host) else href
                    title_elem = item.select_one(".thumb_title") or item.select_one(".name_item")
                    title = title_elem.text.strip() if title_elem else a_tag.get("title", "").strip()

                    img_tag = item.select_one("img")
                    pic = ""
                    if img_tag:
                        pic = img_tag.get("src", "") or img_tag.get("data-original", "") or img_tag.get("data-src", "")
                        if pic.startswith("//"):
                            pic = "https:" + pic
                        elif pic.startswith("/"):
                            pic = current_host + pic

                    count_text = ""
                    video_icon = item.select_one("i.icon-video")
                    if video_icon:
                        column_div = video_icon.find_parent("div", class_="column") or video_icon.parent
                        if column_div:
                            span_tag = column_div.select_one("span")
                            if span_tag:
                                count_text = span_tag.text.strip()

                    if not count_text:
                        count_elem = item.select_one(".count_item") or item.select_one(".tools_column")
                        if count_elem:
                            nums = re.findall(r'\d+', count_elem.get_text(strip=True))
                            if nums:
                                count_text = nums[0]

                    remarks = f"{count_text}个视频" if count_text else "进入列表"

                    vod_list.append({
                        "vod_id": sub_tid,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": remarks,
                        "type": "folder",
                        "vod_tag": "folder"
                    })

                return {'list': vod_list, 'page': page, 'pagecount': page + 1, 'limit': len(vod_list), 'total': 9999}, vod_list

            items = soup.select("#list_albums_common_albums_list_items div.thumb") or \
                    soup.select("#list_videos_latest_videos_list_items div.item.thumb") or \
                    soup.select("div.thumbs div.thumb") or \
                    soup.select("div.item.thumb")

            for item in items:
                a_tag = item.select_one("a.th") or item.select_one("a")
                if not a_tag:
                    continue

                href = a_tag.get("href", "").strip()
                if not href or href == "#":
                    continue

                vod_id = href.replace(current_host, "") if href.startswith(current_host) else href
                title = a_tag.get("title", "").strip() or (item.select_one(".thumb_title").text.strip() if item.select_one(".thumb_title") else "未知项目")

                img_tag = item.select_one("img.lazy-load") or item.select_one("img")
                pic = ""
                if img_tag:
                    pic = img_tag.get("data-original", "") or img_tag.get("data-webp", "") or img_tag.get("data-src", "") or img_tag.get("src", "")

                if pic.startswith("//"):
                    pic = "https:" + pic
                elif pic.startswith("/"):
                    pic = current_host + pic

                remarks = ""
                if is_album_page:
                    info_parts = []
                    view_icon = item.select_one("i.icon-view") or item.select_one("i.icon-views")
                    if view_icon:
                        view_col = view_icon.find_parent("div", class_="column") or view_icon.parent
                        if view_col and view_col.select_one("span"):
                            info_parts.append(f"👁 {view_col.select_one('span').text.strip()}")

                    remarks = " · ".join(info_parts) if info_parts else "图集"
                else:
                    time_elem = item.select_one(".duration") or item.select_one(".sticky_time")
                    if time_elem and time_elem.text.strip():
                        remarks = time_elem.text.strip()

                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                    "style": {"type": "rect", "ratio": 1.33}
                })

            return {'list': vod_list, 'page': page, 'pagecount': page + 1, 'limit': len(vod_list), 'total': 9999}, vod_list

        return self.fetch_with_fallback(sub_path, parse_page)

    # -------------------------------------------------------------------------
    # 强化 detailContent：相册解析 + 视频全自动多模式地址抓取
    # -------------------------------------------------------------------------
    def detailContent(self, array):
        tid = array[0]
        path = tid if tid.startswith('/') else f"/{tid}"

        def parse_detail(soup, current_host, raw_html):
            url = f"{current_host}{path}"
            title_elem = soup.select_one("h1") or soup.select_one(".title")
            title = title_elem.text.strip() if title_elem else "详情"

            # 默认提取封面
            poster_tag = soup.select_one("video") or soup.select_one("img")
            default_pic = poster_tag.get("poster", "") or poster_tag.get("src", "") if poster_tag else ""
            if default_pic.startswith("//"):
                default_pic = "https:" + default_pic
            elif default_pic.startswith("/"):
                default_pic = current_host + default_pic

            is_album = "/album/" in url or "/albums/" in url or "album" in path

            if is_album:
                # =================== 【相册处理模式】 ===================
                img_list = []
                img_items = soup.select("#list_albums_images_list_items div.thumb") or \
                            soup.select(".album_images img") or \
                            soup.select("div.thumbs div.thumb") or \
                            soup.select("a.image_thumb") or \
                            soup.select("a.th")

                for item in img_items:
                    a_tag = item if item.name == 'a' else item.select_one("a")
                    img_tag = item if item.name == 'img' else item.select_one("img")

                    img_url = ""
                    if a_tag and a_tag.get("href"):
                        href = a_tag.get("href")
                        if re.search(r'\.(jpg|jpeg|png|webp|gif)', href, re.I):
                            img_url = href

                    if not img_url and img_tag:
                        img_url = img_tag.get("data-original") or \
                                  img_tag.get("data-src") or \
                                  img_tag.get("data-lazy-src") or \
                                  img_tag.get("data-webp") or \
                                  img_tag.get("src") or ""

                    if not img_url or img_url.startswith("data:"):
                        continue

                    if img_url.startswith("//"):
                        img_url = "https:" + img_url
                    elif img_url.startswith("/"):
                        img_url = current_host + img_url

                    if img_url not in img_list:
                        img_list.append(img_url)

                if not img_list:
                    raw_matches = re.findall(r'https?://[^\s"\'<>]+?\.(?:jpg|jpeg|png|webp)', raw_html, re.I)
                    for pic in raw_matches:
                        if not any(k in pic.lower() for k in ["logo", "avatar", "icon", "thumb_", "favicon"]):
                            if pic not in img_list:
                                img_list.append(pic)

                if img_list:
                    pics_concat = "&&".join(img_list)
                    play_from = "全屏画廊$$$图集选集"
                    play_url = f"全屏浏览(共{len(img_list)}张)${pics_concat}$$$" + "#".join([f"第{idx}张${src}" for idx, src in enumerate(img_list, 1)])

                    vod = {
                        "vod_id": tid,
                        "vod_name": title,
                        "vod_pic": img_list[0],
                        "vod_remarks": f"共 {len(img_list)} 张",
                        "vod_content": f"包含了 {len(img_list)} 张高清图片。",
                        "style": {"type": "rect", "ratio": 1.33},
                        "vod_play_from": play_from,
                        "vod_play_url": play_url
                    }
                else:
                    vod = {
                        "vod_id": tid,
                        "vod_name": title,
                        "vod_pic": default_pic,
                        "vod_remarks": "未解析到图片",
                        "vod_play_from": "画廊",
                        "vod_play_url": f"解析失败${url}"
                    }
            else:
                # =================== 【视频处理模式】 ===================
                video_url = ""

                # 1. 匹配 JS 脚本块中的 video_url、video_alt_url 或 mp4/m3u8 变量定义
                js_patterns = [
                    r'video_url\s*:\s*[\'"]([^\'"]+)[\'"]',
                    r'video_alt_url\s*:\s*[\'"]([^\'"]+)[\'"]',
                    r'https?://[^\s"\'<>]+\.(?:mp4|m3u8)[^\s"\'<>]*',
                    r'/get_file/[^\s"\'<>]+'
                ]

                for pat in js_patterns:
                    matches = re.findall(pat, raw_html, re.I)
                    if matches:
                        v_target = matches[0]
                        if v_target.startswith("//"):
                            video_url = "https:" + v_target
                        elif v_target.startswith("/"):
                            video_url = current_host + v_target
                        else:
                            video_url = v_target
                        break

                # 2. HTML5 video / source 标签提取
                if not video_url:
                    video_tag = soup.select_one("video source") or soup.select_one("video")
                    if video_tag and video_tag.get("src"):
                        v_src = video_tag.get("src")
                        if v_src.startswith("//"):
                            video_url = "https:" + v_src
                        elif v_src.startswith("/"):
                            video_url = current_host + v_src
                        else:
                            video_url = v_src

                # 3. 检查 og:video / embedUrl 或 iframe 嵌入播放器
                if not video_url:
                    embed_match = re.search(r'property="og:video"\s+content="([^"]+)"', raw_html, re.I) or \
                                  re.search(r'"embedUrl":\s*"([^"]+)"', raw_html, re.I)
                    if embed_match:
                        embed_url = embed_match.group(1)
                        try:
                            embed_rsp = self.fetch(embed_url, headers=self.headers, timeout=8)
                            if embed_rsp and embed_rsp.text:
                                for pat in js_patterns:
                                    m = re.findall(pat, embed_rsp.text, re.I)
                                    if m:
                                        v_target = m[0]
                                        video_url = "https:" + v_target if v_target.startswith("//") else (current_host + v_target if v_target.startswith("/") else v_target)
                                        break
                                if not video_url:
                                    video_url = embed_url
                        except Exception:
                            pass

                # 4. 终极保底：如果都没抓到直链，则传递内嵌 iframe 链接或页面 URL 供客户端嗅探
                if not video_url:
                    iframe = soup.select_one("iframe[src*='embed']") or soup.select_one("iframe")
                    if iframe and iframe.get("src"):
                        v_src = iframe.get("src")
                        video_url = "https:" + v_src if v_src.startswith("//") else (current_host + v_src if v_src.startswith("/") else v_src)
                    else:
                        video_url = url

                vod = {
                    "vod_id": tid,
                    "vod_name": title,
                    "vod_pic": default_pic,
                    "vod_play_from": "TheAV",
                    "vod_play_url": f"立即播放${video_url}"
                }

            return {"list": [vod]}, [vod]

        return self.fetch_with_fallback(path, parse_detail)

    def searchContent(self, key, quick):
        path = f"/search/{key}/"
        
        def parse_search(soup, current_host, raw_html):
            vod_list = []
            items = soup.select("#list_videos_common_videos_list_items div.thumb") or \
                    soup.select("div.thumbs div.thumb") or \
                    soup.select("div.item.thumb")
            
            for item in items:
                a_tag = item.select_one("a.th") or item.select_one("a")
                if not a_tag:
                    continue
                href = a_tag.get("href", "").strip()
                if not href or href == "#":
                    continue

                vod_id = href.replace(current_host, "") if href.startswith(current_host) else href
                title = a_tag.get("title", "").strip() or (item.select_one(".thumb_title").text.strip() if item.select_one(".thumb_title") else key)

                img_tag = item.select_one("img.lazy-load") or item.select_one("img")
                pic = ""
                if img_tag:
                    pic = img_tag.get("data-original", "") or img_tag.get("data-webp", "") or img_tag.get("data-src", "") or img_tag.get("src", "")
                if pic.startswith("//"):
                    pic = "https:" + pic
                elif pic.startswith("/"):
                    pic = current_host + pic

                remarks = ""
                time_elem = item.select_one(".duration") or item.select_one(".sticky_time")
                if time_elem and time_elem.text.strip():
                    remarks = time_elem.text.strip()

                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                    "style": {"type": "rect", "ratio": 1.33}
                })

            return {'list': vod_list}, vod_list

        return self.fetch_with_fallback(path, parse_search)

    # -------------------------------------------------------------------------
    # 修复 playerContent：实现智能协议与嗅探模式切换
    # -------------------------------------------------------------------------
    def playerContent(self, flag, id, vipFlags):
        clean_id = id.split("@Referer=")[0] if "@Referer=" in id else id

        # 判断是否属于相册/画廊请求
        is_image = (
            flag in ["全屏画廊", "图集选集"] or
            "&&" in clean_id or
            bool(re.search(r'\.(jpg|jpeg|png|webp|gif)', clean_id, re.I))
        )

        if is_image:
            final_url = "pics://" + clean_id if (flag == "全屏画廊" or "&&" in clean_id) and not clean_id.startswith("pics://") else clean_id
            return {
                "parse": 0,
                "playUrl": "",
                "url": final_url,
                "header": {
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.siteUrl + "/"
                }
            }
        else:
            # 判断视频地址是直链（.mp4 / .m3u8 / get_file）还是网页 URL
            is_direct = bool(re.search(r'(\.mp4|\.m3u8|/get_file/)', clean_id, re.I))

            return {
                "parse": 0 if is_direct else 1, # 直链直接发给播放器；网页链接开启客户端嗅探(parse=1)
                "playUrl": "",
                "url": clean_id,
                "header": {
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.siteUrl + "/"
                }
            }

    def localProxy(self, param):
        pass
