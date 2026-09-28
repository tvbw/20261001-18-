# -*- coding: utf-8 -*-
# 聚合平台3 - 影视资源 API 聚合
# 对应 聚合平台3 (2).js；结构参考 ppnix.py
import json
import re
import sys
from urllib.parse import quote, urlencode

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""):
            pass

try:
    import requests
except ImportError:
    requests = None


class Spider(BaseSpider):
    def init(self, extend=""):
        self._first_cate = {}

    def getName(self):
        return '聚合平台3'

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        if any(x in u for x in ('.mp4', '.m3u8', '.flv', '.mkv')):
            return True
        if u.startswith('magnet:') or u.startswith('ed2k:'):
            return True
        return False

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    UA = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    headers = {'User-Agent': UA}

    # type: 0=XML旧版  1=JSON标准(默认)  2=代理源  3=大地feifei2
    SOURCES = {
        's1': {'name': '🎬电影天堂', 'api': 'http://caiji.dyttzyapi.com/api.php/provide/vod/from/dyttm3u8/at/json'},
        's2': {'name': '💧无水印', 'api': 'https://api.wsyzy.net/api.php/provide/vod'},
        's3': {'name': '🧸量子', 'api': 'https://cj.lziapi.com/api.php/provide/vod'},
        's4': {'name': '📺1080资源', 'api': 'https://api.yyzy-tv.vip/inc/apijson.php'},
        's5': {'name': '🔥大众资源', 'api': 'https://cdn.dzzyapi.com/api.php/provide/vod/'},
        's6': {'name': '📺天涯', 'api': 'https://tyyszy.com/api.php/provide/vod'},
        's7': {'name': '📺暴风', 'api': 'https://bfzyapi.com/api.php/provide/vod'},
        's8': {'name': '⚡闪电', 'api': 'https://xsd.sdzyapi.com/api.php/provide/vod'},
        's9': {'name': '📺索尼', 'api': 'https://suoniapi.com/api.php/provide/vod'},
        's10': {'name': '📺红牛', 'api': 'https://www.hongniuzy2.com/api.php/provide/vod'},
        's11': {'name': '📺茅台', 'api': 'https://caiji.maotaizy.cc/api.php/provide/vod'},
        's12': {'name': '🐯虎牙', 'api': 'https://www.huyaapi.com/api.php/provide/vod'},
        's13': {'name': '📺猫眼', 'api': 'https://api.maoyanapi.top/api.php/provide/vod/'},
        's14': {'name': '📺豆瓣', 'api': 'https://dbzy.tv/api.php/provide/vod'},
        's15': {'name': '📺豪华', 'api': 'https://hhzyapi.com/api.php/provide/vod'},
        's16': {'name': '📺CK资源', 'api': 'https://ckzy.me/api.php/provide/vod'},
        's17': {'name': '📺U酷', 'api': 'https://api.ukuapi88.com/api.php/provide/vod'},
        's18': {'name': '📺ikun', 'api': 'https://ikunzyapi.com/api.php/provide/vod'},
        's19': {'name': '📺无尽', 'api': 'https://api.wujinapi.cc/api.php/provide/vod'},
        's20': {'name': '🌕光速', 'api': 'https://api.guangsuapi.com/api.php/provide/vod'},
        's21': {'name': '📺西瓜', 'api': 'https://caiji.xgzyapi.com/api.php/provide/vod/'},
        's22': {'name': '📺新浪', 'api': 'https://api.xinlangapi.com/xinlangapi.php/provide/vod'},
        's23': {'name': '📺旺旺', 'api': 'https://zhangqun66.xyz/ww.php'},
        's24': {'name': '📺最大', 'api': 'https://api.zuidapi.com/api.php/provide/vod'},
        's25': {'name': '🌸樱花', 'api': 'https://m3u8.apiyhzy.com/api.php/provide/vod'},
        's26': {'name': '🐮牛牛', 'api': 'https://api.niuniuzy.me/api.php/provide/vod'},
        's27': {'name': '☁️百度云', 'api': 'https://api.apibdzy.com/api.php/provide/vod'},
        's28': {'name': '🏎速播', 'api': 'https://subocaiji.com/api.php/provide/vod'},
        's29': {'name': '🦅金鹰', 'api': 'https://jyzyapi.com/provide/vod/'},
        's30': {'name': '⚡闪电', 'api': 'https://sdzyapi.com/api.php/provide/vod'},
        's31': {'name': '👑非凡', 'api': 'https://cj.ffzyapi.com/api.php/provide/vod'},
        's32': {'name': '🍃飘零', 'api': 'https://p2100.net/api.php/provide/vod'},
        's33': {'name': '🐾360', 'api': 'https://360zyzz.com/api.php/provide/vod/'},
        's34': {'name': '🐾淘片', 'api': 'https://taopianapi.com/cjapi/mc/vod/json.html'},
        's35': {'name': '🐾快车', 'api': 'https://caiji.kuaichezy.org/api.php/provide/vod/'},
        's36': {'name': '🐾奇异', 'api': 'https://iqiyizyapi.com/api.php/provide/vod/'},
        's37': {'name': '🐾鸭鸭', 'api': 'https://cj.yayazy.net/api.php/provide/vod/'},
        's38': {'name': '🐾极速', 'api': 'https://jszyapi.com/api.php/provide/vod/'},
        's39': {'name': '🐾如意', 'api': 'https://cj.rycjapi.com/api.php/provide/vod/'},
        's40': {'name': '🐾火狐', 'api': 'https://hhzyapi.com/api.php/provide/vod/'},
        's41': {'name': '🐾刺桐', 'api': 'http://pg.cttv.vip/api.php/provide/vod/'},
        's42': {'name': '🐾巨量', 'api': 'https://api.juliang.live/api/provide/vod/'},
        's43': {'name': '🐾荐片', 'api': 'http://192.129.140.23:5757/api/荐片[优]?pwd=dzyyds', 'type': 2},
        's44': {'name': '🐾tvbx', 'api': 'https://dy.7772888.xyz/api.php/tvbox', 'type': 1},
        's45': {'name': '📺魔都', 'api': 'https://www.mdzyapi.com/api.php/provide/vod'},
    }

    def _text(self, v):
        return str(v if v is not None else '').strip()

    def _build_url(self, base, params=None):
        url = self._text(base).strip(' "\'')
        params = params or {}
        keys = [k for k, v in params.items() if v is not None and str(v) != '']
        if not keys:
            return url
        qs = urlencode({k: str(params[k]) for k in keys})
        return url + ('&' if '?' in url else '?') + qs

    def _request(self, url):
        try:
            if requests is None:
                import urllib.request
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
                    return r.read().decode('utf-8', 'ignore')
            r = requests.get(url, headers=self.headers, timeout=12, verify=False)
            r.encoding = 'utf-8'
            return r.text if r.status_code == 200 else ''
        except Exception as e:
            print('request error', url, e)
            return ''

    def _safe_json(self, s):
        try:
            if not s:
                return None
            # 大整数 id 保精度
            s2 = re.sub(
                r'"(vod_id|id|type_id|list_id|vodId)"\s*:\s*(\d{16,})',
                r'"\1":"\2"',
                str(s),
            )
            return json.loads(s2)
        except Exception:
            try:
                return json.loads(s)
            except Exception:
                return None

    def _fix_pic(self, url):
        url = self._text(url)
        if not url:
            return ''
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('http://') or url.startswith('https://'):
            return url
        return ''

    def _extract_cdata(self, s):
        if not s:
            return ''
        m = re.search(r'<!\[CDATA\[([\s\S]*?)\]\]>', s)
        if m:
            return m.group(1).strip()
        return re.sub(r'<[^>]+>', '', s).strip()

    def _normalize_vod(self, item):
        if not item or not isinstance(item, dict):
            return item
        o = dict(item)
        if not o.get('vod_play_from') and o.get('vod_play'):
            o['vod_play_from'] = o['vod_play']
        if not o.get('vod_play_url') and o.get('vod_url'):
            o['vod_play_url'] = o['vod_url']
        if not o.get('vod_id') and o.get('id'):
            o['vod_id'] = o['id']
        if not o.get('vod_name') and o.get('name'):
            o['vod_name'] = o['name']
        if not o.get('vod_name') and o.get('title'):
            o['vod_name'] = o['title']
        if not o.get('vod_pic') and o.get('pic'):
            o['vod_pic'] = o['pic']
        if not o.get('vod_pic') and o.get('cover'):
            o['vod_pic'] = o['cover']
        if not o.get('vod_remarks') and o.get('remarks'):
            o['vod_remarks'] = o['remarks']
        if not o.get('vod_remarks') and o.get('note'):
            o['vod_remarks'] = o['note']
        if not o.get('vod_remarks') and o.get('vod_continu'):
            o['vod_remarks'] = o['vod_continu']
        if not o.get('vod_content') and o.get('content'):
            o['vod_content'] = o['content']
        if not o.get('vod_content') and o.get('des'):
            o['vod_content'] = o['des']
        if not o.get('vod_actor') and o.get('actor'):
            o['vod_actor'] = o['actor']
        if not o.get('vod_director') and o.get('director'):
            o['vod_director'] = o['director']
        if not o.get('vod_year') and o.get('year'):
            o['vod_year'] = o['year']
        if not o.get('vod_year') and o.get('d_year'):
            o['vod_year'] = o['d_year']
        if not o.get('vod_area') and o.get('area'):
            o['vod_area'] = o['area']
        if not o.get('type_name') and o.get('list_name'):
            o['type_name'] = o['list_name']
        if not o.get('type_name') and o.get('type'):
            o['type_name'] = o['type']
        o['vod_pic'] = self._fix_pic(o.get('vod_pic'))
        return o

    def _parse_xml(self, html):
        empty = {'list': [], 'page': 1, 'pagecount': 1, 'pagesize': 20, 'total': 0, 'class': []}
        if not html or ('<rss' not in html and '<video>' not in html):
            return empty
        page, pagecount, pagesize, total = 1, 1, 20, 0
        lm = re.search(r'<list\s+[^>]*>', html, re.I)
        if lm:
            attrs = lm.group(0)
            m = re.search(r'page="(\d+)"', attrs, re.I)
            if m:
                page = int(m.group(1))
            m = re.search(r'pagecount="(\d+)"', attrs, re.I)
            if m:
                pagecount = int(m.group(1))
            m = re.search(r'pagesize="(\d+)"', attrs, re.I)
            if m:
                pagesize = int(m.group(1))
            m = re.search(r'recordcount="(\d+)"', attrs, re.I)
            if m:
                total = int(m.group(1))
        classes = []
        cb = re.search(r'<class>([\s\S]*?)</class>', html, re.I)
        if cb:
            for m in re.finditer(r'<ty\s+id=["\']?(\d+)["\']?>([^<]+)</ty>', cb.group(1), re.I):
                classes.append({'type_id': m.group(1), 'type_name': m.group(2).strip()})
        lst = []
        for vm in re.finditer(r'<video>([\s\S]*?)</video>', html, re.I):
            v = vm.group(1)

            def get(tag):
                m = re.search(r'<%s[^>]*>([\s\S]*?)</%s>' % (tag, tag), v, re.I)
                return self._extract_cdata(m.group(1)) if m else ''

            vid, name = get('id'), get('name')
            if not vid or not name:
                continue
            dt = get('dt')
            play_from, play_url = [], []
            dl = re.search(r'<dl>([\s\S]*?)</dl>', v, re.I)
            if dl:
                for dm in re.finditer(
                    r'<dd[^>]*?(?:flag=["\']([^"\']+)["\']|flag=([^\s>]+))[^>]*>([\s\S]*?)</dd>',
                    dl.group(1), re.I
                ):
                    flag = self._text(dm.group(1) or dm.group(2) or dt or '播放')
                    content = self._extract_cdata(dm.group(3) or '')
                    if content:
                        play_from.append(flag)
                        play_url.append(content)
            if not play_from and dt:
                play_from.append(dt)
                play_url.append('')
            lst.append(self._normalize_vod({
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': get('pic'),
                'vod_remarks': get('note') or get('type') or '',
                'vod_year': get('year'),
                'vod_area': get('area'),
                'vod_actor': get('actor'),
                'vod_director': get('director'),
                'vod_content': get('des'),
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_url),
                'type_name': get('type'),
            }))
        return {
            'list': lst, 'page': page, 'pagecount': pagecount,
            'pagesize': pagesize, 'total': total, 'class': classes,
        }

    def _parse_response(self, html):
        empty = {'list': [], 'page': 1, 'pagecount': 1, 'pagesize': 20, 'total': 0, 'class': []}
        if not html:
            return empty
        j = self._safe_json(html)
        if j:
            # 大地 feifei2
            if j.get('status') is not None and (isinstance(j.get('data'), list) or j.get('page')):
                page_obj = j.get('page') or {}
                classes = []
                if isinstance(j.get('list'), list) and j['list']:
                    first = j['list'][0]
                    if first and (first.get('list_id') is not None or first.get('list_name')):
                        classes = [{
                            'type_id': self._text(c.get('list_id') or c.get('type_id') or c.get('id')),
                            'type_name': self._text(c.get('list_name') or c.get('type_name') or c.get('name')),
                        } for c in j['list']]
                raw = j['data'] if isinstance(j.get('data'), list) else []
                return {
                    'list': [self._normalize_vod(x) for x in raw],
                    'page': int(page_obj.get('pageindex') or page_obj.get('page') or 1),
                    'pagecount': int(page_obj.get('pagecount') or 1),
                    'pagesize': int(page_obj.get('pagesize') or 20),
                    'total': int(page_obj.get('recordcount') or page_obj.get('total') or len(raw)),
                    'class': classes,
                }
            if isinstance(j.get('list'), list) or isinstance(j.get('class'), list) or j.get('filters'):
                raw = j['list'] if isinstance(j.get('list'), list) else []
                classes = j['class'] if isinstance(j.get('class'), list) else []
                if raw and raw[0] and raw[0].get('list_id') is not None and not raw[0].get('vod_id') and not raw[0].get('vod_name'):
                    classes = [{
                        'type_id': self._text(c.get('list_id') or c.get('type_id')),
                        'type_name': self._text(c.get('list_name') or c.get('type_name')),
                    } for c in raw]
                    raw = []
                else:
                    raw = [self._normalize_vod(x) for x in raw]
                classes = [{
                    'type_id': self._text(c.get('type_id') or c.get('list_id') or c.get('id')),
                    'type_name': self._text(c.get('type_name') or c.get('list_name') or c.get('name')),
                } for c in (classes or [])]
                return {
                    'list': raw,
                    'page': int(j.get('page') or 1),
                    'pagecount': int(j.get('pagecount') or 1),
                    'pagesize': int(j.get('limit') or j.get('pagesize') or 20),
                    'total': int(j.get('total') or 0),
                    'class': classes,
                }
        return self._parse_xml(html)

    def _clean_item(self, item, source_key, source_name, is_detail=False):
        o = self._normalize_vod(dict(item))
        o['vod_id'] = self._text(o.get('vod_id'))
        if not is_detail:
            o['vod_id'] = '%s@@%s' % (source_key, o['vod_id'])
        rem = self._text(o.get('vod_remarks'))
        o['vod_remarks'] = '%s | %s' % (source_name, rem)
        from_arr = [s.strip() for s in self._text(o.get('vod_play_from')).split('$$$') if s.strip()]
        url_arr = [s.strip() for s in self._text(o.get('vod_play_url')).split('$$$')]
        if from_arr:
            from_arr = [x if x.startswith(source_name) else '%s-%s' % (source_name, x) for x in from_arr]
        if not from_arr and any(url_arr):
            from_arr = ['%s-线路%d' % (source_name, i + 1) for i in range(len(url_arr))]
        if from_arr and url_arr:
            while len(url_arr) < len(from_arr):
                url_arr.append('')
            while len(from_arr) < len(url_arr):
                from_arr.append('%s-线路%d' % (source_name, len(from_arr) + 1))
        o['vod_play_from'] = '$$$'.join(from_arr)
        o['vod_play_url'] = '$$$'.join(url_arr)
        o.pop('vod_down_from', None)
        o.pop('vod_down_url', None)
        return o

    def _load_filter(self, source_key, source_obj):
        stype = source_obj.get('type') or 1
        if stype == 2:
            url = self._build_url(source_obj['api'], {})
        else:
            url = self._build_url(source_obj['api'], {'ac': 'list'})
        data = self._parse_response(self._request(url))
        vals = [{'n': '全部(最新)', 'v': ''}]
        first_cate = ''
        for c in (data.get('class') or []):
            cid = self._text(c.get('type_id'))
            name = self._text(c.get('type_name'))
            if cid or name:
                vals.append({'n': name or cid, 'v': cid})
                if not first_cate and cid:
                    first_cate = cid
        return vals, first_cate

    def homeContent(self, filter):
        classes = []
        filters = {}
        self._first_cate = {}
        for sk, so in self.SOURCES.items():
            classes.append({'type_id': sk, 'type_name': so['name']})
            try:
                vals, first = self._load_filter(sk, so)
                if first:
                    self._first_cate[sk] = first
            except Exception:
                vals = [{'n': '全部(最新)', 'v': ''}]
            filters[sk] = [{'key': 'cateId', 'name': '分类', 'value': vals}]
        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        source = self.SOURCES.get(str(tid))
        if not source:
            return {'list': [], 'page': pg, 'pagecount': 0}
        cate_id = ''
        if isinstance(extend, dict):
            cate_id = self._text(extend.get('cateId'))
        elif isinstance(filter, dict):
            cate_id = self._text(filter.get('cateId'))
        stype = source.get('type') or 1
        if not cate_id and stype == 2 and self._first_cate.get(tid):
            cate_id = self._first_cate[tid]
        if stype in (0, 3):
            params = {'ac': 'videolist', 'pg': pg}
            if cate_id:
                params['t'] = cate_id
            url = self._build_url(source['api'], params)
        elif stype == 2:
            params = {'pg': pg}
            if cate_id:
                params['t'] = cate_id
            url = self._build_url(source['api'], params)
        else:
            params = {'ac': 'detail', 'pg': pg}
            if cate_id:
                params['t'] = cate_id
            url = self._build_url(source['api'], params)
        data = self._parse_response(self._request(url))
        if stype == 2 and not data.get('list'):
            fc = self._first_cate.get(tid)
            if fc and fc != cate_id:
                data = self._parse_response(
                    self._request(self._build_url(source['api'], {'pg': pg, 't': fc}))
                )
        out = []
        for it in (data.get('list') or []):
            cleaned = self._clean_item(it, tid, source['name'], False)
            cleaned['vod_pic'] = self._fix_pic(cleaned.get('vod_pic'))
            out.append(cleaned)
        return {
            'list': out,
            'page': int(data.get('page') or pg),
            'pagecount': int(data.get('pagecount') or 1),
            'limit': int(data.get('pagesize') or 20),
            'total': int(data.get('total') or len(out)),
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else ids
        if '@@' not in str(raw):
            return {'list': []}
        source_key, real_id = str(raw).split('@@', 1)
        source = self.SOURCES.get(source_key)
        if not source:
            return {'list': []}
        stype = source.get('type') or 1
        if stype == 0:
            html = self._request(self._build_url(source['api'], {'ac': 'videolist', 'ids': real_id}))
        elif stype == 3:
            html = self._request(self._build_url(source['api'], {'ac': 'videolist', 'ids': real_id}))
            tmp = self._parse_response(html)
            first = (tmp.get('list') or [None])[0]
            if not first or not self._text(first.get('vod_play_url') or first.get('vod_url')):
                html2 = self._request(self._build_url(source['api'], {'ac': 'detail', 'ids': real_id}))
                if html2:
                    html = html2
        else:
            html = self._request(self._build_url(source['api'], {'ac': 'detail', 'ids': real_id}))
            if stype == 2:
                tmp = self._parse_response(html)
                first = (tmp.get('list') or [None])[0]
                no_play = not first or not self._text(first.get('vod_play_url') or first.get('vod_url'))
                if no_play and re.search(r'https?://', real_id, re.I):
                    nm = re.search(r'/(\d+)/?$', real_id) or re.search(r'(\d{4,})', real_id)
                    if nm:
                        html3 = self._request(
                            self._build_url(source['api'], {'ac': 'detail', 'ids': nm.group(1)})
                        )
                        if html3:
                            d3 = self._parse_response(html3)
                            if (d3.get('list') or [None])[0] and self._text(
                                (d3['list'][0].get('vod_play_url') or d3['list'][0].get('vod_url') or '')
                            ):
                                html = html3
        data = self._parse_response(html)
        out = []
        for it in (data.get('list') or []):
            cleaned = self._clean_item(it, source_key, source['name'], True)
            cleaned['vod_id'] = str(raw)
            cleaned['vod_pic'] = self._fix_pic(cleaned.get('vod_pic'))
            if not self._text(cleaned.get('vod_play_from')) and self._text(cleaned.get('vod_play_url')):
                segs = self._text(cleaned.get('vod_play_url')).split('$$$')
                cleaned['vod_play_from'] = '$$$'.join(
                    ['%s-线路%d' % (source['name'], i + 1) for i in range(len(segs))]
                )
            out.append(cleaned)
        return {'list': out}

    def searchContent(self, key, quick, pg='1'):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg=1):
        pg = int(pg or 1)
        result = []
        max_page = 1
        for sk, so in self.SOURCES.items():
            try:
                stype = so.get('type') or 1
                if stype in (0, 3):
                    url = self._build_url(so['api'], {'ac': 'videolist', 'wd': key, 'pg': pg})
                elif stype == 2:
                    url = self._build_url(so['api'], {'wd': key, 'pg': pg})
                else:
                    url = self._build_url(so['api'], {'ac': 'detail', 'wd': key, 'pg': pg})
                data = self._parse_response(self._request(url))
                for it in (data.get('list') or []):
                    cleaned = self._clean_item(it, sk, so['name'], False)
                    cleaned['vod_pic'] = self._fix_pic(cleaned.get('vod_pic'))
                    result.append(cleaned)
                pc = int(data.get('pagecount') or 1)
                if pc > max_page:
                    max_page = pc
            except Exception as e:
                print('search skip', sk, e)
        return {
            'list': result,
            'page': pg,
            'pagecount': max_page,
            'limit': 40,
            'total': 9999,
        }

    def playerContent(self, flag, id, vipFlags):
        play_url = self._text(id)
        if ';' in play_url and re.search(r'https?://', play_url, re.I):
            first = play_url.split(';')[0]
            if re.match(r'^https?://', first, re.I):
                play_url = first
        need_parse = not self.isVideoFormat(play_url)
        return {
            'parse': 1 if need_parse else 0,
            'jx': 0,
            'url': play_url,
            'header': {
                'User-Agent': self.UA,
                'Referer': 'https://api.juliang.live/',
            },
        }

    def localProxy(self, param):
        return None
