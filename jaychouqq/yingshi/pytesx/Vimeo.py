#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vimeo
JWT: https://vimeo.com/_next/viewer
列表: api.vimeo.com
播放: player.vimeo.com/video/{id}/config 或 embed 页 playerConfig
清晰度: progressive + 解析 HLS master playlist
"""
import json
import re
import sys
import time
import urllib.parse

try:
    import requests
except ImportError:
    requests = None

sys.path.append('../../')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.siteUrl = 'https://vimeo.com'
        self.api = 'https://api.vimeo.com'
        self.player = 'https://player.vimeo.com/video/'
        self.viewer = 'https://vimeo.com/_next/viewer'
        self.userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        self.jwt = ''
        self.jwt_ts = 0
        self.bearer = ''
        self.channels = {
            'staffpicks': {'name': 'Staff Picks'},
            'animation': {'name': 'Animation'},
            'documentary': {'name': 'Documentary'},
            'narrative': {'name': 'Narrative'},
            'music': {'name': 'Music'},
            'comedy': {'name': 'Comedy'},
            'experimental': {'name': 'Experimental'},
            'sports': {'name': 'Sports'},
            'travel': {'name': 'Travel'},
            'adsandcommercials': {'name': 'Ads'},
            'brandedcontent': {'name': 'Branded'},
        }

    def getName(self):
        return 'Vimeo'

    def init(self, extend=""):
        try:
            if isinstance(extend, str) and extend.strip().startswith(('eyJ', 'jwt ', 'bearer ', 'Bearer ')):
                raw = extend.strip()
                if raw.lower().startswith('bearer '):
                    self.bearer = raw.split(' ', 1)[1].strip()
                elif raw.lower().startswith('jwt '):
                    self.jwt = raw.split(' ', 1)[1].strip()
                    self.jwt_ts = time.time()
                else:
                    self.jwt = raw
                    self.jwt_ts = time.time()
            elif extend:
                ext = json.loads(extend) if isinstance(extend, str) else (extend or {})
                self.bearer = str(ext.get('bearer') or ext.get('token') or '')
                if ext.get('jwt'):
                    self.jwt = str(ext.get('jwt'))
                    self.jwt_ts = time.time()
        except Exception:
            pass
        self._ensure_jwt()

    def fetch(self, url, headers=None, params=None):
        if headers is None:
            headers = {
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'application/json, text/plain, */*',
            }
        try:
            if requests:
                resp = requests.get(url, headers=headers, params=params, timeout=20)
                resp.raise_for_status()
                return resp
            full = url
            if params:
                full += ('&' if '?' in url else '?') + urllib.parse.urlencode(params, doseq=True)
            from urllib.request import Request, urlopen
            raw = urlopen(Request(full, headers=headers), timeout=20).read()

            class R:
                def __init__(self, raw):
                    self.content = raw
                    self.text = raw.decode('utf-8', 'ignore')
                    self.status_code = 200

                def json(self):
                    return json.loads(self.text)

            return R(raw)
        except Exception as e:
            print('请求失败: %s, %s' % (url, e))
            return None

    def fetch_json(self, url, headers=None, params=None):
        resp = self.fetch(url, headers=headers, params=params)
        if not resp:
            return {}
        try:
            return resp.json()
        except Exception:
            return {}

    def fetch_text(self, url, headers=None):
        resp = self.fetch(url, headers=headers)
        if not resp:
            return ''
        return getattr(resp, 'text', '') or ''

    def _ensure_jwt(self):
        if self.bearer:
            return ''
        if self.jwt and (time.time() - self.jwt_ts) < 240:
            return self.jwt
        self.jwt = ''
        try:
            js = self.fetch_json(self.viewer, headers={
                'User-Agent': self.userAgent,
                'Referer': self.siteUrl + '/',
                'Accept': 'application/json',
            })
            if js.get('jwt'):
                self.jwt = js.get('jwt')
                self.jwt_ts = time.time()
                return self.jwt
        except Exception:
            pass
        html = self.fetch_text(self.siteUrl + '/channels/staffpicks')
        m = re.search(r'"jwt"\s*:\s*"([^"]+)"', html or '')
        if m:
            self.jwt = m.group(1)
            self.jwt_ts = time.time()
        return self.jwt

    def _auth_headers(self):
        headers = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Accept': 'application/vnd.vimeo.*+json;version=3.4',
            'Origin': self.siteUrl,
        }
        if self.bearer:
            headers['Authorization'] = 'bearer ' + self.bearer
        else:
            token = self._ensure_jwt()
            if token:
                headers['Authorization'] = 'jwt ' + token
        return headers

    def api_get(self, path, params=None):
        js = self.fetch_json(self.api + path, headers=self._auth_headers(), params=params)
        if not js or js.get('error') or js.get('error_code'):
            self.jwt = ''
            self.jwt_ts = 0
            js = self.fetch_json(self.api + path, headers=self._auth_headers(), params=params)
        return js or {}

    def _fmt_dur(self, sec):
        try:
            n = int(sec or 0)
        except Exception:
            return ''
        if n <= 0:
            return ''
        return '%d:%02d' % (n // 60, n % 60)

    def _pic(self, item):
        p = (item or {}).get('pictures') or {}
        if p.get('base_link'):
            return p.get('base_link')
        sizes = p.get('sizes') or []
        if sizes:
            return sizes[-1].get('link') or ''
        return ''

    def _vid(self, item):
        uri = str((item or {}).get('uri') or '')
        m = re.search(r'/videos/(\d+)', uri)
        if m:
            return m.group(1)
        link = str((item or {}).get('link') or '')
        m2 = re.search(r'vimeo\.com/(\d+)', link)
        return m2.group(1) if m2 else ''

    def _map(self, item):
        vid = self._vid(item)
        if not vid:
            return None
        return {
            'vod_id': vid,
            'vod_name': item.get('name') or vid,
            'vod_pic': self._pic(item),
            'vod_remarks': self._fmt_dur(item.get('duration')),
        }

    def homeContent(self, filter):
        classes = [{'type_id': k, 'type_name': v['name']} for k, v in self.channels.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        videos = []
        try:
            js = self.api_get('/channels/staffpicks/videos', {'per_page': 20, 'page': 1, 'sort': 'date'})
            for item in js.get('data') or []:
                v = self._map(item)
                if v:
                    videos.append(v)
        except Exception as e:
            print('获取首页视频失败: %s' % e)
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        cate = str(tid or 'staffpicks')
        videos = []
        total = 0
        try:
            if cate == 'staffpicks':
                path = '/channels/staffpicks/videos'
                params = {'per_page': 20, 'page': pg, 'sort': 'date'}
            else:
                path = '/categories/%s/videos' % urllib.parse.quote(cate)
                params = {'per_page': 20, 'page': pg, 'sort': 'likes'}
            js = self.api_get(path, params)
            total = int(js.get('total') or 0)
            for item in js.get('data') or []:
                v = self._map(item)
                if v:
                    videos.append(v)
        except Exception as e:
            print('获取分类内容失败: %s' % e)
        pagecount = min((total + 19) // 20, 200) if total else (pg + 1 if len(videos) >= 20 else pg)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 20,
            'total': total or len(videos),
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        videos = []
        total = 0
        try:
            m = re.search(r'(\d{6,})', str(key or ''))
            if m and pg == 1:
                js = self.api_get('/videos/' + m.group(1))
                v = self._map(js) if js else None
                if v:
                    return {'list': [v], 'page': 1, 'pagecount': 1, 'limit': 20, 'total': 1}
            js = self.api_get('/videos', {
                'query': key,
                'per_page': 20,
                'page': pg,
                'filter': 'content_rating',
                'filter_content_rating': 'safe',
            })
            total = int(js.get('total') or 0)
            for item in js.get('data') or []:
                v = self._map(item)
                if v:
                    videos.append(v)
        except Exception as e:
            print('搜索失败: %s' % e)
        pagecount = min((total + 19) // 20, 200) if total else (pg + 1 if videos else pg)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 20,
            'total': total or len(videos),
        }

    def _extract_json_obj(self, text, marker):
        """从 HTML 中按大括号匹配提取 JSON 对象"""
        m = re.search(re.escape(marker) + r'\s*=\s*', text or '')
        if not m:
            return {}
        start = m.end()
        if start >= len(text) or text[start] != '{':
            return {}
        depth = 0
        for i, c in enumerate(text[start:]):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:start + i + 1])
                    except Exception:
                        return {}
        return {}

    def _player_config(self, vid):
        """优先 /config，失败则走 embed 页 playerConfig"""
        headers = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/' + str(vid),
            'Accept': 'application/json',
        }
        cfg = self.fetch_json(self.player + str(vid) + '/config', headers=headers)
        if cfg.get('request'):
            return cfg

        # 带 h 参数的 embed
        js = self.api_get('/videos/' + str(vid))
        embed = js.get('player_embed_url') or (self.player + str(vid))
        h = re.search(r'[?&]h=([a-f0-9]+)', embed or '')
        if h:
            cfg = self.fetch_json(
                self.player + str(vid) + '/config?h=' + h.group(1),
                headers=headers,
            )
            if cfg.get('request'):
                return cfg

        html = self.fetch_text(embed, headers={
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/' + str(vid),
            'Accept': 'text/html',
        })
        cfg = self._extract_json_obj(html, 'playerConfig')
        if not cfg:
            cfg = self._extract_json_obj(html, 'window.playerConfig')
        return cfg or {}

    def _parse_hls_master(self, master_url):
        """解析 HLS 主列表，返回 [(height, url), ...] 高在前"""
        headers = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
        }
        text = self.fetch_text(master_url, headers=headers)
        if not text or text.startswith('<!'):
            return []
        base = master_url.rsplit('/', 1)[0] + '/'
        variants = []
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXT-X-STREAM-INF:'):
                h = 0
                m = re.search(r'RESOLUTION=\d+x(\d+)', line)
                if m:
                    h = int(m.group(1))
                # next non-empty non-tag line is uri
                j = i + 1
                while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith('#')):
                    j += 1
                if j < len(lines):
                    uri = lines[j].strip()
                    if uri and not uri.startswith('#'):
                        if not uri.startswith('http'):
                            uri = urllib.parse.urljoin(base, uri)
                        variants.append((h, uri))
                i = j
            i += 1
        variants.sort(key=lambda x: x[0], reverse=True)
        # 去重 height
        seen, out = set(), []
        for h, u in variants:
            key = h or u
            if key in seen:
                continue
            seen.add(key)
            out.append((h, u))
        return out

    def _collect_qualities(self, cfg):
        """返回 [(label, url), ...]，高清晰度优先"""
        result = []
        seen = set()
        files = ((cfg or {}).get('request') or {}).get('files') or {}

        # 1) progressive MP4
        prog = files.get('progressive') or []
        prog = sorted(
            [p for p in prog if isinstance(p, dict) and p.get('url')],
            key=lambda x: int(x.get('height') or 0),
            reverse=True,
        )
        for p in prog:
            h = int(p.get('height') or 0)
            label = (p.get('quality') or (str(h) + 'p' if h else 'MP4')).upper()
            if not label.endswith('P') and h:
                label = str(h) + 'p'
            url = p.get('url')
            if url and url not in seen:
                seen.add(url)
                result.append((label, url))

        # 2) HLS master + 分档
        hls = files.get('hls') or {}
        master = ''
        cdns = hls.get('cdns') or {}
        preferred = hls.get('default_cdn')
        order = ([preferred] if preferred else []) + list(cdns.keys())
        for name in order:
            if not name or name not in cdns:
                continue
            item = cdns.get(name) or {}
            master = item.get('url') or item.get('avc_url') or ''
            if master:
                break
        if not master:
            master = hls.get('url') or ''

        if master:
            variants = self._parse_hls_master(master)
            if variants:
                for h, u in variants:
                    label = ('%sp' % h) if h else 'HLS'
                    if u not in seen:
                        seen.add(u)
                        result.append((label, u))
            # 自适应总表
            if master not in seen:
                seen.add(master)
                result.append(('自适应', master))

        # 3) DASH 兜底
        if not result:
            dash = files.get('dash') or {}
            for item in (dash.get('cdns') or {}).values():
                u = (item or {}).get('url') or (item or {}).get('avc_url') or ''
                if u and u not in seen:
                    result.append(('DASH', u))
                    break

        return result

    def detailContent(self, ids):
        vid = str((ids or [''])[0]).split(':')[0]
        try:
            js = self.api_get('/videos/' + vid)
            if not js.get('name') and not js.get('uri'):
                js = {}
            user = (js.get('user') or {}).get('name') or ''
            desc = js.get('description') or ''
            if isinstance(desc, str):
                desc = re.sub(r'<[^>]+>', '', desc)[:600]

            cfg = self._player_config(vid)
            qualities = self._collect_qualities(cfg)
            if qualities:
                play_url = '#'.join('%s$%s' % (lab, url) for lab, url in qualities)
            else:
                play_url = '正片$%s' % vid

            return {
                'list': [{
                    'vod_id': vid,
                    'vod_name': js.get('name') or vid,
                    'vod_pic': self._pic(js),
                    'vod_remarks': self._fmt_dur(js.get('duration')),
                    'vod_year': str(js.get('created_time') or '')[:10],
                    'vod_actor': user,
                    'vod_content': desc,
                    'vod_play_from': 'Vimeo',
                    'vod_play_url': play_url,
                }]
            }
        except Exception as e:
            print('获取详情失败: %s' % e)
            return {
                'list': [{
                    'vod_id': vid,
                    'vod_name': vid,
                    'vod_play_from': 'Vimeo',
                    'vod_play_url': '正片$%s' % vid,
                }]
            }

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': self.userAgent,
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl,
        }
        play_id = str(id or '')
        if play_id.startswith('http') and self.isVideoFormat(play_id):
            return {'parse': 0, 'jx': '0', 'url': play_id, 'header': header}
        if play_id.startswith('http'):
            return {'parse': 0, 'jx': '0', 'url': play_id, 'header': header}

        vid = play_id.split('|')[0].split(':')[0]
        try:
            cfg = self._player_config(vid)
            qualities = self._collect_qualities(cfg)
            if qualities:
                # 默认最高清
                return {'parse': 0, 'jx': '0', 'url': qualities[0][1], 'header': header}
        except Exception as e:
            print('获取播放内容失败: %s' % e)
        return {
            'parse': 1,
            'jx': '1',
            'url': self.siteUrl + '/' + vid,
            'header': header,
        }

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        if any(x in u for x in ('.m3u8', '.mp4', '.mpd', '.m4s')):
            return True
        if 'vimeocdn.com' in u or 'vimeo.com' in u:
            return True
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


if __name__ == '__main__':
    spider = Spider()
    spider.init()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))
    r = spider.categoryContent('staffpicks', 1, {}, {})
    print('list', len(r.get('list') or []))
    if r.get('list'):
        vid = r['list'][0]['vod_id']
        d = spider.detailContent([vid])
        print('name', d['list'][0]['vod_name'])
        print('play_url', d['list'][0]['vod_play_url'][:300])
        token = d['list'][0]['vod_play_url'].split('#')[0].split('$')[-1]
        print(json.dumps(spider.playerContent('Vimeo', token, []), ensure_ascii=False)[:250])
