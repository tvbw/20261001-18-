# coding: utf-8
"""
JAV.SB Spider  v1.3.0
修复：无播放地址 → 增强 m3u8/mp4 提取 + 多分辨率列表
"""
import json
import sys
import re
import urllib.request
import urllib.parse
import ssl

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            pass

VERSION = '1.3.0'
SITE_URL = 'https://jav.sb'

# 固定分类（UTF-8 中文，避免乱码）
CATEGORIES = [
    {"type_id": "new", "type_name": "最近更新"},
    {"type_id": "uncensored", "type_name": "无码"},
    {"type_id": "reduce", "type_name": "无码破解"},
    {"type_id": "chinese", "type_name": "中文字幕"},
    {"type_id": "censored", "type_name": "有码"},
    {"type_id": "amateur", "type_name": "素人"},
    {"type_id": "vr", "type_name": "VR"},
    {"type_id": "idol", "type_name": "女优"},
    {"type_id": "big-tits", "type_name": "巨乳"},
    {"type_id": "anal", "type_name": "肛交"},
    {"type_id": "creampie", "type_name": "中出"},
    {"type_id": "lesbian", "type_name": "女同"},
    {"type_id": "mature", "type_name": "熟女"},
    {"type_id": "teen", "type_name": "少女"},
]


class Spider(BaseSpider):
    def getName(self):
        return "JAV.SB"

    def init(self, extend=""):
        self.host = SITE_URL
        if extend:
            try:
                if isinstance(extend, str) and extend.strip().startswith('{'):
                    conf = json.loads(extend)
                    self.host = conf.get('host', SITE_URL).rstrip('/')
                elif isinstance(extend, dict):
                    self.host = extend.get('host', SITE_URL).rstrip('/')
            except Exception:
                pass

        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Referer': self.host + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'identity',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

    def _get(self, url, params=None):
        try:
            if params:
                qs = urllib.parse.urlencode(params)
                url = url + ('&' if '?' in url else '?') + qs
            req = urllib.request.Request(url, headers=self.headers, method='GET')
            resp = urllib.request.urlopen(req, context=self._ssl_context, timeout=15)
            raw = resp.read()
            try:
                return raw.decode('utf-8')
            except UnicodeDecodeError:
                return raw.decode('utf-8', errors='ignore')
        except Exception as e:
            print('_get error: %s -> %s' % (url, e), file=sys.stderr)
            return ''

    def _abs(self, u):
        if not u:
            return ''
        u = u.strip().replace('\\/', '/')
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.host + u
        if not u.startswith('http'):
            return urllib.parse.urljoin(self.host + '/', u)
        return u

    def _parse_list(self, html):
        if not html or len(html) < 500:
            return []
        videos = []
        seen = set()

        # 模式1：带封面的卡片（常见 tube 结构）
        pattern1 = re.compile(
            r'href=["\']([^"\']*(?:/v/|/video/|/watch/|/jav/|[A-Za-z0-9]{2,15}-[0-9]{2,6}|[a-f0-9]{16,})[^"\']*)["\']'
            r'[^>]{0,400}'
            r'(?:title=["\']([^"\']{2,150})["\'])?'
            r'[\s\S]{0,800}?'
            r'(?:src|data-src|data-original|data-poster|data-lazy)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
            re.I
        )
        for m in pattern1.finditer(html):
            href = m.group(1).strip()
            title = (m.group(2) or '').strip()
            pic = (m.group(3) or '').strip()
            if not href or href in seen:
                continue
            # 过滤非视频链接
            if any(x in href.lower() for x in ('javascript:', 'mailto:', '#', '/tag/', '/category/', '/actor/')):
                continue
            seen.add(href)
            if not title or len(title) < 2:
                # 尝试从路径取番号
                code = re.search(r'([A-Za-z]{2,12}-\d{2,6})', href)
                title = code.group(1) if code else href.split('/')[-1][:40]
            vid = href if href.startswith('http') else urllib.parse.urljoin(self.host, href)
            videos.append({
                'vod_id': vid,
                'vod_name': re.sub(r'\s+', ' ', title)[:100],
                'vod_pic': self._abs(pic),
                'vod_remarks': ''
            })

        # 模式2：宽松链接（标题在 a 内）
        if len(videos) < 6:
            pattern2 = re.compile(
                r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*(?:<[^>]+>)*\s*([^<]{4,120}?)\s*<',
                re.I
            )
            for m in pattern2.finditer(html):
                href, title = m.group(1).strip(), m.group(2).strip()
                if not re.search(r'/v/|/video/|/watch/|/jav/|[A-Za-z]{2,12}-\d{2,6}|[a-f0-9]{16,}', href, re.I):
                    continue
                if href in seen or len(title) < 3:
                    continue
                if any(x in href.lower() for x in ('javascript:', 'mailto:', '#')):
                    continue
                seen.add(href)
                vid = href if href.startswith('http') else urllib.parse.urljoin(self.host, href)
                videos.append({
                    'vod_id': vid,
                    'vod_name': re.sub(r'\s+', ' ', title)[:100],
                    'vod_pic': '',
                    'vod_remarks': ''
                })

        return videos

    def _label_from_url(self, u):
        """根据 URL 推断清晰度标签"""
        ul = u.lower()
        if '.m3u8' in ul:
            if '1080' in ul or 'fhd' in ul or 'fullhd' in ul:
                return '1080P'
            if '720' in ul or 'hd' in ul:
                return '720P'
            if '480' in ul or 'sd' in ul:
                return '480P'
            if '360' in ul:
                return '360P'
            return 'HLS'
        if '1080' in ul or 'fhd' in ul:
            return '1080P'
        if '720' in ul:
            return '720P'
        if '480' in ul:
            return '480P'
        if '360' in ul:
            return '360P'
        return '播放'

    def _extract_play_urls(self, html, page_url=''):
        """
        提取真实播放地址，优先 m3u8，支持多分辨率列表。
        返回 [(label, url), ...] 按清晰度排序。
        """
        play_list = []
        seen = set()

        def add(u, label=None):
            if not u:
                return
            u = u.replace('\\/', '/').replace('&amp;', '&').replace('\\u0026', '&').strip()
            u = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), u)
            if not u.startswith('http') or u in seen:
                return
            # 过滤明显非视频
            if any(x in u.lower() for x in ('.js', '.css', '.png', '.jpg', '.gif', 'google', 'facebook', 'analytics')):
                return
            seen.add(u)
            if not label:
                label = self._label_from_url(u)
            play_list.append((label, u))

        if not html:
            return play_list

        # 1. 直接匹配 m3u8 / mp4 完整 URL
        for m in re.finditer(r'https?://[^"\'\s<>\\]+\.m3u8[^"\'\s<>\\]*', html, re.I):
            add(m.group(0), self._label_from_url(m.group(0)))
        for m in re.finditer(r'https?://[^"\'\s<>\\]+\.mp4[^"\'\s<>\\]*', html, re.I):
            add(m.group(0), self._label_from_url(m.group(0)))

        # 2. <source> / <video> 标签
        for m in re.finditer(r'<(?:source|video)[^>]+(?:src|data-src)=["\']([^"\']+)["\']', html, re.I):
            add(self._abs(m.group(1)))

        # 3. 常见 JS 变量 / 对象（单引号、双引号、无引号）
        js_keys = (
            'url', 'src', 'file', 'video', 'playurl', 'playUrl', 'videoUrl', 'video_url',
            'hls', 'm3u8', 'source', 'sources', 'stream', 'play_url', 'link', 'path',
            'hlsUrl', 'mp4Url', 'mediaUrl', 'contentUrl'
        )
        for key in js_keys:
            # "key": "https://..."
            for m in re.finditer(
                rf'["\']?{key}["\']?\s*[:=]\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
                html, re.I
            ):
                add(m.group(1))
            # key = "https://..."
            for m in re.finditer(
                rf'\b{key}\s*=\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
                html, re.I
            ):
                add(m.group(1))

        # 4. sources 数组形式  [{file:"..",label:"1080P"}, ...]
        for m in re.finditer(
            r'["\']?(?:file|src|url)["\']?\s*:\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']'
            r'[^}]{0,80}["\']?(?:label|type|res|quality)["\']?\s*:\s*["\']([^"\']+)["\']',
            html, re.I
        ):
            add(m.group(1), m.group(2).strip() or None)
        # 反过来 label 在前
        for m in re.finditer(
            r'["\']?(?:label|type|res|quality)["\']?\s*:\s*["\']([^"\']+)["\']'
            r'[^}]{0,80}["\']?(?:file|src|url)["\']?\s*:\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
            html, re.I
        ):
            add(m.group(2), m.group(1).strip() or None)

        # 5. iframe / embed 中的地址
        for m in re.finditer(r'<(?:iframe|embed)[^>]+src=["\']([^"\']+)["\']', html, re.I):
            src = m.group(1)
            # ?url= 真实地址
            um = re.search(r'[?&](?:url|src|file|v)=([^&"\']+)', src)
            if um:
                real = urllib.parse.unquote(um.group(1))
                if real.startswith('http'):
                    add(real)
            elif re.search(r'\.(m3u8|mp4)', src, re.I):
                add(self._abs(src))

        # 6. 尝试解析 master m3u8 中的多码率（若已拿到 master）
        extra = []
        for label, u in list(play_list):
            if '.m3u8' in u.lower() and 'master' not in label.lower():
                # 简单判断是否可能是 master：后续可扩展请求
                pass
        play_list.extend(extra)

        # 去重并排序：1080 > 720 > HLS > 480 > 其他
        def sort_key(item):
            label, u = item
            l = (label or '').upper()
            if '1080' in l or 'FHD' in l:
                return 0
            if '720' in l or 'HD' in l:
                return 1
            if 'HLS' in l or '.M3U8' in u.upper():
                return 2
            if '480' in l or 'SD' in l:
                return 3
            if '360' in l:
                return 4
            return 5

        # 同 URL 只保留一个
        uniq = []
        seen_u = set()
        for item in sorted(play_list, key=sort_key):
            if item[1] not in seen_u:
                seen_u.add(item[1])
                uniq.append(item)
        return uniq

    def _fetch_m3u8_variants(self, master_url):
        """若拿到 master playlist，解析其中多分辨率变体"""
        variants = []
        try:
            text = self._get(master_url)
            if not text or '#EXTM3U' not in text:
                return variants
            # #EXT-X-STREAM-INF:BANDWIDTH=...,RESOLUTION=1920x1080
            # https://.../index.m3u8
            lines = text.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('#EXT-X-STREAM-INF:'):
                    res_m = re.search(r'RESOLUTION=(\d+)x(\d+)', line, re.I)
                    bw_m = re.search(r'BANDWIDTH=(\d+)', line, re.I)
                    label = None
                    if res_m:
                        h = int(res_m.group(2))
                        if h >= 1080:
                            label = '1080P'
                        elif h >= 720:
                            label = '720P'
                        elif h >= 480:
                            label = '480P'
                        else:
                            label = '%sP' % h
                    elif bw_m:
                        bw = int(bw_m.group(1))
                        if bw >= 4000000:
                            label = '1080P'
                        elif bw >= 1500000:
                            label = '720P'
                        else:
                            label = '480P'
                    # 下一行是 URL
                    if i + 1 < len(lines):
                        u = lines[i + 1].strip()
                        if u and not u.startswith('#'):
                            if not u.startswith('http'):
                                u = urllib.parse.urljoin(master_url, u)
                            variants.append((label or 'HLS', u))
                i += 1
        except Exception as e:
            print('_fetch_m3u8_variants error:', e, file=sys.stderr)
        return variants

    def homeContent(self, filter):
        classes = []
        for c in CATEGORIES:
            classes.append({
                'type_id': c['type_id'],
                'type_name': c['type_name']
            })

        videos = []
        try:
            html = self._get(self.host + '/')
            videos = self._parse_list(html)
            if not videos:
                # 尝试 /en/ 或 /zh/
                for path in ('/en/', '/zh/', '/cn/'):
                    html = self._get(self.host + path)
                    videos = self._parse_list(html)
                    if videos:
                        break
        except Exception as e:
            print('homeContent list error:', e, file=sys.stderr)

        return {
            'class': classes,
            'list': videos[:24]
        }

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid or 'new')

        candidates = []
        # 常见路径组合
        base_paths = [
            f'/{tid}/',
            f'/c/{tid}/',
            f'/category/{tid}/',
            f'/genre/{tid}/',
            f'/tag/{tid}/',
            f'/en/{tid}/',
            f'/zh/{tid}/',
            f'/cn/{tid}/',
        ]
        for bp in base_paths:
            if pg <= 1:
                candidates.append(self.host + bp)
            candidates.append(self.host + bp + f'page/{pg}/')
            candidates.append(self.host + bp + f'?page={pg}')
            candidates.append(self.host + bp.rstrip('/') + f'-{pg}/')

        if pg == 1:
            candidates.append(self.host + '/')
            candidates.append(self.host + '/en/')
            candidates.append(self.host + '/zh/')

        videos = []
        for url in candidates:
            html = self._get(url)
            videos = self._parse_list(html)
            if len(videos) >= 6:
                break

        type_name = tid
        for c in CATEGORIES:
            if c['type_id'] == tid:
                type_name = c['type_name']
                break

        return {
            'page': pg,
            'pagecount': 9999 if len(videos) >= 10 else pg,
            'limit': 24,
            'total': 9999 if videos else 0,
            'type_name': type_name,
            'list': videos
        }

    def detailContent(self, array):
        result = {'list': []}
        if not array or not array[0]:
            return result

        page_url = str(array[0])
        if not page_url.startswith('http'):
            page_url = urllib.parse.urljoin(self.host, page_url)

        html = self._get(page_url)
        vod = {
            'vod_id': page_url,
            'vod_name': '视频详情',
            'vod_pic': '',
            'vod_remarks': '',
            'vod_content': '',
            'vod_play_from': 'JAV.SB',
            'vod_play_url': ''
        }

        # 标题
        m = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.I)
        if not m:
            m = re.search(r'<title>([^<]+)</title>', html, re.I)
        if m:
            name = re.sub(r'\s*[-|].*$', '', m.group(1)).strip()
            vod['vod_name'] = name[:100] if name else '视频详情'

        # 封面
        m = re.search(r'(?:og:image|twitter:image)["\']?\s*(?:content|href)?=["\']([^"\']+)["\']', html, re.I)
        if not m:
            m = re.search(r'(?:poster|data-poster)=["\']([^"\']+)["\']', html, re.I)
        if not m:
            m = re.search(r'(?:data-src|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', html, re.I)
        if m:
            vod['vod_pic'] = self._abs(m.group(1))

        # 简介
        m = re.search(r'(?:og:description|description)["\']?\s*content=["\']([^"\']+)["\']', html, re.I)
        if m:
            vod['vod_content'] = m.group(1).strip()[:300]

        # 播放地址（多分辨率）
        play_list = self._extract_play_urls(html, page_url)

        # 若只有一条 master m3u8，尝试展开分辨率
        if len(play_list) == 1 and '.m3u8' in play_list[0][1].lower():
            variants = self._fetch_m3u8_variants(play_list[0][1])
            if variants:
                play_list = variants

        if play_list:
            # 格式：清晰度1$url1#清晰度2$url2
            parts = ['%s$%s' % (label, url) for label, url in play_list[:8]]
            vod['vod_play_url'] = '#'.join(parts)
            # 多线路时用 $$$ 分隔（此处单线路多清晰度）
        else:
            # 无直链：返回页面让 playerContent 再解析
            vod['vod_play_url'] = '播放$%s' % page_url

        result['list'] = [vod]
        return result

    def searchContent(self, key, quick, pg='1'):
        pg = int(pg or 1)
        q = urllib.parse.quote(key)
        urls = [
            f'{self.host}/search/{q}/',
            f'{self.host}/search/{q}/page/{pg}/',
            f'{self.host}/search?keyword={q}&page={pg}',
            f'{self.host}/?s={q}&page={pg}',
            f'{self.host}/en/search/{q}/',
            f'{self.host}/zh/search/{q}/',
            f'{self.host}/cn/search?q={q}&page={pg}',
        ]
        videos = []
        for url in urls:
            html = self._get(url)
            videos = self._parse_list(html)
            if videos:
                break
        return {
            'page': pg,
            'pagecount': 9999 if len(videos) >= 10 else pg,
            'limit': 24,
            'total': 9999,
            'list': videos
        }

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.headers['User-Agent'],
            'Referer': self.host + '/',
            'Origin': self.host,
        }
        play = str(id or '').strip()

        # 已经是媒体地址
        if play.startswith('http') and re.search(r'\.(m3u8|mp4|flv|mpd)(\?|$)', play, re.I):
            return {
                'parse': 0,
                'jx': '0',
                'url': play,
                'header': header
            }

        # 页面地址 → 再提取一次
        if play.startswith('http'):
            html = self._get(play)
            play_list = self._extract_play_urls(html, play)
            if len(play_list) == 1 and '.m3u8' in play_list[0][1].lower():
                variants = self._fetch_m3u8_variants(play_list[0][1])
                if variants:
                    play_list = variants
            if play_list:
                # 返回清晰度最高的一条
                return {
                    'parse': 0,
                    'jx': '0',
                    'url': play_list[0][1],
                    'header': header
                }

        return {
            'parse': 1,
            'jx': '1',
            'url': play,
            'header': header
        }

    def isVideoFormat(self, url):
        if not url:
            return False
        return bool(re.search(r'\.(m3u8|mp4|flv|mpd)', url, re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return {}
