# -*- coding: utf-8 -*-
# 4K影视 https://www.4kvm.tv/
# 结构参考爱奇艺源；播放走页面 parse=1（站点 WASM 加密直链）
import re
import sys
from urllib.parse import quote, unquote

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def init(self, extend=''):
            pass


class Spider(Spider):

    def init(self, extend=""):
        pass

    def getName(self):
        return '4K影视'

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.flv', '.mkv'))

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    rhost = 'https://www.4kvm.tv'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Referer': 'https://www.4kvm.tv/',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    cateManual = {
        '电影': 'movie',
        '剧集': 'tv',
        '动漫': 'anime',
    }

    def fetch(self, url, headers=None):
        import requests
        r = requests.get(url, headers=headers or self.headers, timeout=20)
        return r

    def homeContent(self, filter):
        classes = [{'type_name': k, 'type_id': v} for k, v in self.cateManual.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        html = self.fetch(self.rhost + '/').text
        return {'list': self._parse_list(html)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid)
        url = f'{self.rhost}/{tid}'
        if pg > 1:
            url += f'?page={pg}'
        html = self.fetch(url).text
        videos = self._parse_list(html)
        # 站点翻页较弱，有列表则保留下一页入口
        pagecount = pg + 1 if len(videos) >= 20 else pg
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 24,
            'total': 999999,
        }

    def _parse_list(self, html):
        videos = []
        seen = set()
        if not html:
            return videos
        # <a href="/play/xxx" class="block"> ... data-src="pic" alt="名" ... <h3>名</h3>
        pat = (
            r'<a href="(/play/([a-z0-9]+))" class="block">\s*'
            r'<div[^>]*>\s*<img[^>]+data-src="([^"]*)"[^>]*alt="([^"]*)"[\s\S]*?'
            r'<h3[^>]*>\s*([^<]+?)\s*</h3>'
        )
        for m in re.finditer(pat, html, re.I):
            path, pid, pic, alt, name = m.groups()
            if pid in seen:
                continue
            seen.add(pid)
            title = (name or alt or pid).strip()
            pic = (pic or '').replace('&amp;', '&')
            if pic.startswith('//'):
                pic = 'https:' + pic
            videos.append({
                'vod_id': path,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': '',
            })
        return videos

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else ids
        path = str(raw)
        if not path.startswith('/'):
            path = '/play/' + path
        if not path.startswith('/play/'):
            path = '/play/' + path.split('/')[-1]
        url = self.rhost + path
        html = self.fetch(url).text

        title = ''
        tm = re.search(r'<h1[^>]*>([^<]+)</h1>', html) or re.search(r'<title>([^<]+)</title>', html)
        if tm:
            title = tm.group(1).replace('-4k影视', '').replace(' -4k影视', '').strip()
            title = re.sub(r'\s*-\s*第\d+集\s*$', '', title).strip()

        pic = ''
        pm = re.search(r'data-poster="([^"]+)"', html) or re.search(
            r'property="og:image"\s+content="([^"]+)"', html
        )
        if pm:
            pic = pm.group(1).replace('&amp;', '&')

        # 线路
        lines = re.findall(r"lineName:\s*'([^']+)'\s*,\s*episodeCount:\s*(\d+)", html)
        if not lines:
            lines = [('默认', 1)]

        # data-line + data-episode + dataid
        ep_map = {}  # line -> [(ep, dataid), ...]
        for m in re.finditer(
            r'data-line="(\d+)"[^>]*data-episode="(\d+)"\s+dataid="(\d+)"',
            html,
        ):
            line_i, ep_i, dataid = m.group(1), m.group(2), m.group(3)
            ep_map.setdefault(line_i, []).append((int(ep_i), dataid))

        play_from = []
        play_urls = []
        for idx, (line_name, ep_count) in enumerate(lines, start=1):
            play_from.append(line_name)
            eps = ep_map.get(str(idx), [])
            if not eps:
                # 无 dataid 时按集数构造同页链接
                parts = []
                for i in range(1, max(int(ep_count), 1) + 1):
                    parts.append(f'第{i}集${path}?line={idx}&ep={i}')
                play_urls.append('#'.join(parts))
            else:
                parts = []
                for ep_i, dataid in sorted(eps, key=lambda x: x[0]):
                    parts.append(f'第{ep_i}集${path}?line={idx}&ep={ep_i}&dataid={dataid}')
                play_urls.append('#'.join(parts))

        return {
            'list': [{
                'vod_id': path,
                'vod_name': title or path,
                'vod_pic': pic,
                'vod_content': title,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_urls),
            }]
        }

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg or 1)
        url = f'{self.rhost}/search?q={quote(key)}'
        if pg > 1:
            url += f'&page={pg}'
        html = self.fetch(url).text
        videos = self._parse_list(html)
        return {'list': videos, 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        play = str(id or '').strip()
        if play.startswith('/'):
            play = self.rhost + play
        # 去掉 query 仅保留播放页（WASM 播放器在页面内选线选集）
        page = play.split('?')[0]
        if self.isVideoFormat(page):
            return {
                'parse': 0,
                'url': page,
                'header': self.headers,
            }
        return {
            'parse': 1,
            'jx': '1',
            'url': page if page.startswith('http') else (self.rhost + '/' + page.lstrip('/')),
            'header': {
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.rhost + '/',
            },
        }

    def localProxy(self, param):
        pass
