#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import ssl
import sys
import urllib.request
import urllib.parse
from urllib.parse import quote, unquote, urljoin, parse_qs

try:
    from base.spider import Spider
except Exception:
    class Spider:
        def init(self, extend=""): pass
        def homeContent(self, filter=False): return {}
        def homeVideoContent(self): return {}
        def categoryContent(self, tid, pg, filter=None, extend=None): return {}
        def detailContent(self, ids): return {}
        def searchContent(self, key, quick, pg="1"): return {}
        def playerContent(self, flag, id, vipFlags): return {}
        def localProxy(self, param): return []
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False


class Spider(Spider):

    HOST = 'https://mdav1.net'
    # ImgDecypt.js / imgEncrypt 中提取的密钥
    KEY = b"2019ysapp7527"

    def __init__(self):
        super().__init__()
        self.host = self.HOST
        self.ext = ''

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; 2407FRK8EC Build/AP3A.240617.008; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/128.0.6613.127 Mobile Safari/537.36',
            'Origin': self.HOST,
            'Referer': f"{self.HOST}/",
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        }

    def getName(self):
        return '麻豆av'

    def getDependence(self):
        return []

    def init(self, extend=''):
        if extend:
            self.ext = extend

    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def _get_bytes(self, url):
        """原生网络请求获取二进制数据（带完整的防盗链请求头）"""
        try:
            req_headers = self.headers.copy()
            req_headers['Referer'] = f"{self.HOST}/"
            
            req = urllib.request.Request(url, headers=req_headers)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
                return response.read(), response.status
        except Exception:
            return b'', 500

    def _get_html(self, url):
        """原生网络请求获取 HTML 文本"""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
                html_text = response.read().decode('utf-8', errors='ignore')
                return html_text, response.status, response.geturl()
        except Exception as e:
            return '', 500, str(e)

    def decrypt_image(self, encrypted_bytes: bytes) -> bytes:
        """
        严格匹配前端 JS imgEncrypt / ImgDecypt 逻辑：
        无条件将图片前 100 个字节（且不超过实际长度）与 '2019ysapp7527' 循环异或还原
        """
        if not encrypted_bytes:
            return b''
        
        data = bytearray(encrypted_bytes)
        key_len = len(self.KEY)
        limit = min(100, len(data))

        for i in range(limit):
            data[i] ^= self.KEY[i % key_len]

        return bytes(data)

    def localProxy(self, param):
        """
        全壳子兼容的本地代理接口
        全面适配字典传参、Query 传参和纯字符串传参
        """
        target_url = ""
        
        # 1. 字典传参解析 (如 {"url": "..."} 或 {"param": "..."})
        if isinstance(param, dict):
            target_url = param.get('url', '')
            if not target_url and 'param' in param:
                target_url = param.get('param', '')

        # 2. 字符串传参解析 (如 "url=http..." 或 "do=js&url=http...")
        elif isinstance(param, str):
            query = parse_qs(param)
            if 'url' in query:
                target_url = query['url'][0]
            elif 'param' in query:
                target_url = query['param'][0]
            else:
                # 正则抽离 url 参数，防止整体被 urlencode 导致 parse_qs 失败
                match = re.search(r'url=([^&]+)', param)
                if match:
                    target_url = match.group(1)
                elif param.startswith('http'):
                    target_url = param

        if target_url:
            target_url = unquote(target_url)
            raw_bytes, code = self._get_bytes(target_url)
            if code == 200 and raw_bytes:
                # 异或解密图片
                decrypted_bytes = self.decrypt_image(raw_bytes)
                
                # 返回符合 TVBox 规范的列表形式 [status, contentType, bytes, headers]
                return [
                    200, 
                    "image/png", 
                    decrypted_bytes, 
                    {
                        "Content-Type": "image/png",
                        "Content-Length": str(len(decrypted_bytes)),
                        "Access-Control-Allow-Origin": "*"
                    }
                ]

        return [404, "text/plain", b"Not Found", {}]

    def homeContent(self, filter=False):
        """原生字符串 Split 提取分类"""
        classes = []
        filters = {}

        html, _, _ = self._get_html(self.host)
        if html and 'navigationList' in html:
            try:
                nav_part = html.split('navigationList')[1].split('官方信息')[0]
                items = nav_part.split('<div class="nav-item">')[1:]
                for item in items:
                    item_str = item.split('</a>')[0]
                    
                    if 'href="/' in item_str:
                        cate_id = item_str.split('href="/')[1].split('"')[0].strip()
                    else:
                        continue
                        
                    if '<div>' in item_str and '</div>' in item_str:
                        name = item_str.split('<div>')[1].split('</div>')[0].strip()
                    else:
                        name = cate_id

                    if cate_id and name:
                        classes.append({'type_name': name, 'type_id': cate_id})
            except Exception:
                pass

        filter_config = [
            {
                "key": "by",
                "name": "排序",
                "value": [
                    {"v": "newest", "n": "最新"},
                    {"v": "promoted", "n": "推荐"},
                    {"v": "hottest", "n": "热门🔥"},
                    {"v": "mostlike", "n": "最多点赞👍"}
                ]
            }
        ]

        for cls in classes:
            filters[cls['type_id']] = filter_config

        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        html, status_code, _ = self._get_html(self.host)
        videos = self._parse_list_items(html)

        return {
            'page': 1,
            'pagecount': 1,
            'limit': 20,
            'total': len(videos),
            'list': videos,
        }

    def categoryContent(self, tid, pg, filter=None, extend=None):
        page = str(pg) if pg else '1'
        clean_tid = str(tid).strip()
        extend = extend or {}

        by_param = extend.get('by', '')
        if by_param:
            url = f"{self.host}/{clean_tid}?by={by_param}&page={page}"
        else:
            url = f"{self.host}/{clean_tid}/{page}" if page != '1' else f"{self.host}/{clean_tid}"

        html, status_code, _ = self._get_html(url)
        videos = self._parse_list_items(html)

        p_num = int(page) if page.isdigit() else 1
        return {
            'page': p_num,
            'pagecount': p_num + 1 if len(videos) > 0 else p_num,
            'limit': 20,
            'total': 999,
            'list': videos,
        }

    def searchContent(self, key, quick, pg='1'):
        page = str(pg) if pg else '1'
        encoded_key = quote(str(key or '').strip())
        url = f"{self.host}/search/{encoded_key}/{page}"

        html, _, _ = self._get_html(url)
        videos = self._parse_list_items(html)

        p_num = int(page) if page.isdigit() else 1
        return {
            'page': p_num,
            'pagecount': p_num + 1 if len(videos) > 0 else p_num,
            'limit': 20,
            'total': 999,
            'list': videos,
        }

    def detailContent(self, ids):
        """播放地址与详情信息解析"""
        rel_id = ids[0] if ids else ''
        if not rel_id:
            return {'list': []}

        url = rel_id if rel_id.startswith('http') else urljoin(self.host, rel_id)
        html, _, _ = self._get_html(url)
        if not html:
            return {'list': []}

        try:
            title = "麻豆视频"
            if '<div class="videoTitle"' in html:
                title = html.split('<div class="videoTitle"')[1].split('>')[1].split('</div>')[0].strip()
            elif '<h1' in html:
                title = html.split('<h1')[1].split('>')[1].split('</h1>')[0].strip()

            pic = self._extract_pic_url(html)

            play_url = ""
            if '__ARCHIVE_PLAYER__' in html:
                try:
                    raw_block = html.split('__ARCHIVE_PLAYER__')[1].split(';')[0]
                    if '=' in raw_block:
                        json_str = raw_block.split('=', 1)[1].strip()
                    else:
                        json_str = raw_block.strip()

                    player_data = json.loads(json_str)
                    play_url = player_data.get('rawPath', '')
                    
                    if not play_url and 'stream' in player_data:
                        urls_map = player_data.get('stream', {}).get('urls', {})
                        play_url = urls_map.get('auto') or urls_map.get('480p') or urls_map.get('720p', '')
                except Exception:
                    pass

            if not play_url and '"rawPath"' in html:
                try:
                    play_url = html.split('"rawPath"')[1].split('"')[1].replace('\\/', '/')
                except Exception:
                    pass

            if not play_url:
                play_url = url

            vod = {
                'vod_id': rel_id,
                'vod_name': title,
                'vod_pic': pic,
                'vod_actor': '',
                'vod_remarks': '',
                'vod_content': title,
                'vod_play_from': '麻豆源码',
                'vod_play_url': f"高清${play_url}",
            }
            return {'list': [vod]}
        except Exception:
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        """播放器配置"""
        url = id

        if self.isVideoFormat(url):
            return {
                'parse': 0,
                'url': url,
                'header': self.headers,
            }

        return {
            'parse': 1,
            'url': url,
            'header': self.headers,
            'jx': 0,
        }

    def _extract_pic_url(self, html_snippet):
        """抽取图片地址并格式化为标准代理 URL"""
        if not html_snippet:
            return ""
        
        pic = ""
        data_src_match = re.search(r'data-src=["\']([^"\']+)["\']', html_snippet)
        if data_src_match:
            pic = data_src_match.group(1).strip()

        if not pic or 'placeholder' in pic:
            src_match = re.search(r'src=["\']([^"\']+)["\']', html_snippet)
            if src_match:
                pic = src_match.group(1).strip()

        if not pic or 'placeholder' in pic:
            return ""

        full_pic_url = pic if pic.startswith('http') else urljoin(self.host, pic)

        # 格式化为通用的 proxy:// 代理格式，方便 localProxy 拦截并无损解密
        encoded_url = quote(full_pic_url)
        return f"proxy://do=js&url={encoded_url}"

    def _parse_list_items(self, html):
        """列表页列表项解析"""
        if not html or len(html) < 200:
            return []

        videos = []
        try:
            if '<article' in html:
                items = html.split('<article')[1:]
            elif 'class="videoList"' in html:
                items = html.split('class="videoList"')[1:]
            elif 'class="videoCoverBox"' in html:
                items = html.split('class="videoCoverBox"')[1:]
            else:
                items = []

            for item in items:
                if 'href="' not in item:
                    continue
                href = item.split('href="')[1].split('"')[0]

                title = ""
                if 'class="videoTitle"' in item:
                    title = item.split('class="videoTitle"')[1].split('>')[1].split('</div>')[0].strip()
                elif 'alt="' in item:
                    title = item.split('alt="')[1].split('"')[0].strip()
                elif 'title="' in item:
                    title = item.split('title="')[1].split('"')[0].strip()

                if not title:
                    continue

                pic = self._extract_pic_url(item)

                videos.append({
                    'vod_id': urljoin(self.host, href),
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': '',
                })
        except Exception:
            pass

        seen = set()
        return [x for x in videos if not (x['vod_id'] in seen or seen.add(x['vod_id']))]


spider = Spider()
