# coding=utf-8
"""
猫源 appapi 类爬虫 (由 cat.js 转换) | TVBox Python 爬虫
关键:
  - init/home/category/detail/play/search 全流程复刻
  - AES-CBC (Pkcs7, base64) 加解密，MD5 签名
  - 滑块验证 + 图形验证码 OCR 兜底
  - 弹幕 JSON -> XML 转换 (localProxy)
  - 自定义播放 UA (ua2)
  - 简介添加指定前缀
"""
import sys
import json
import time
import hashlib
import base64
import random
import re
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
            method = kw.pop('method', 'get').lower()
            data = kw.pop('data', None)
            if method == 'post':
                r = self._sess.post(url, headers=headers, data=data,
                                    timeout=timeout, **kw)
            else:
                r = self._sess.get(url, headers=headers, timeout=timeout, **kw)
            r.encoding = 'utf-8'
            return r

        def log(self, *a, **kw):
            try:
                print("[cat-py]", *a)
            except Exception:
                pass

    Spider = _BaseSpider

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    AES = None


# ===================== 配置 =====================
PREFIX_MAP = {
    '1': 'getappapi.index',
    '2': 'qijiappapi.index',
    '3': 'appapi',
}

DEFAULT_HEADERS = {
    'User-Agent': 'okhttp/3.10.0',
    'app-user-device-id': '291b226282010337c9443590d6457be15',
    'app-version-code': '112',
}

INTRO_PREFIX = "🍊小橙子为您介绍剧情👉请不要相信视频中的广告，以免上当受骗！"


class Spider(Spider):

    def getName(self):
        return "猫源appapi"

    # ------------------------- 初始化 -------------------------
    def init(self, extend=""):
        try:
            self.extend = json.loads(extend) if extend else {}
        except Exception:
            self.extend = {}

        self.site_url = ''
        self.key = ''
        self.iv = ''
        self.site_key = ''
        self.site_type = 3
        self.api_prefix = 'getappapi.index'
        self.init_suffix = 'init'
        self.has_custom_init = False
        self.enable_verify_time_sign = False
        self.force_verify_code = None
        self.custom_play_ua = ''
        self.third_danmu_base_url = ''
        self.search_api_suffix = ''
        self.sou_param_name = ''
        self.sou_salt = ''
        self.extra_search_headers = {}
        self.home_vods = []
        self.search_status = False
        self.parse_map = {}

        self.headers = dict(DEFAULT_HEADERS)

        ext = self.extend
        if not ext:
            return

        # 自定义 init 后缀
        init_val = ext.get('init')
        if isinstance(init_val, str) and init_val.startswith('V'):
            self.init_suffix = 'init' + init_val
            self.has_custom_init = True

        # 时间签名开关
        if ext.get('time') is not None:
            tv = str(ext.get('time'))
            self.enable_verify_time_sign = tv in ('1', 'true')

        # 强制验证码
        if ext.get('code') is not None:
            self.force_verify_code = str(ext.get('code')).strip()

        # 自定义播放 UA
        if ext.get('ua2') is not None:
            self.custom_play_ua = str(ext.get('ua2')).strip()

        # 自定义 header
        head = ext.get('head')
        if isinstance(head, str):
            head_str = head.strip()
            if head_str:
                for item in head_str.split(','):
                    trimmed = item.strip()
                    if not trimmed:
                        continue
                    colon = trimmed.find(':')
                    if colon > 0:
                        hk = trimmed[:colon].strip()
                        hv = trimmed[colon + 1:].strip()
                        if hk and hv:
                            self.headers[hk] = hv

        # host（支持远程 txt 列表）
        host = ext.get('host') or ''
        if host:
            if host.startswith('http') and (host.endswith('.txt') or host.endswith('.json')):
                resp = self._request(host, None, self.headers, 'get')
                urls = [ln.strip() for ln in (resp or '').split('\n')
                        if ln.strip() and ln.strip().startswith('http')]
                if urls:
                    host = urls[0]
            self.site_url = host.rstrip('/')
            if 'php' not in self.site_url:
                self.site_url += '/api.php'

        self.key = ext.get('key') or ''
        self.iv = ext.get('iv') or self.key

        if ext.get('api') and PREFIX_MAP.get(str(ext['api'])):
            self.api_prefix = PREFIX_MAP[str(ext['api'])]

        if ext.get('version'):
            self.headers['app-version-code'] = str(ext['version'])
        if ext.get('id'):
            self.headers['app-user-device-id'] = str(ext['id'])
        if ext.get('token'):
            self.headers['app-user-token'] = str(ext['token'])
        if ext.get('ua'):
            self.headers['User-Agent'] = str(ext['ua'])

        self.log("init: site=%s api=%s init=%s" %
                 (self.site_url, self.api_prefix, self.init_suffix))

    # ------------------------- 加解密工具 -------------------------
    def _aes_key(self, s):
        b = s.encode('utf-8')
        if len(b) not in (16, 24, 32):
            b = (b + b'\x00' * 16)[:16]
        return b

    def aes_decode(self, data, key_str, iv_str, typ='b64'):
        if AES is None:
            return ''
        try:
            key = self._aes_key(key_str)
            iv = self._aes_key(iv_str)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            if typ == 'hex':
                raw = bytes.fromhex(data)
            else:
                raw = base64.b64decode(data)
            out = unpad(cipher.decrypt(raw), AES.block_size)
            return out.decode('utf-8', 'ignore')
        except Exception as e:
            self.log("aesDecode fail: %s" % e)
            return ''

    def aes_encode(self, s, key_str, iv_str, typ='b64'):
        if AES is None:
            return ''
        try:
            key = self._aes_key(key_str)
            iv = self._aes_key(iv_str)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            enc = cipher.encrypt(pad(s.encode('utf-8'), AES.block_size))
            if typ == 'hex':
                return enc.hex()
            return base64.b64encode(enc).decode('utf-8')
        except Exception as e:
            self.log("aesEncode fail: %s" % e)
            return ''

    def md5(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    # ------------------------- 请求封装 -------------------------
    def _request(self, req_url, data=None, header=None, method='get'):
        final_headers = dict(self.headers)
        if self.enable_verify_time_sign:
            ts = str(int(time.time()))
            sign = self.aes_encode(ts, self.key, self.iv)
            final_headers['app-api-verify-time'] = ts
            final_headers['app-api-verify-sign'] = sign
        if header:
            final_headers.update(header)

        try:
            if (method or 'get').lower() == 'post':
                rsp = self.fetch(req_url, headers=final_headers,
                                 method='post', data=data or {}, timeout=10)
            else:
                rsp = self.fetch(req_url, headers=final_headers, timeout=10)
            return rsp.text if hasattr(rsp, 'text') else str(rsp)
        except Exception as e:
            self.log("request fail %s -> %s" % (req_url, e))
            return ''

    def _request_text(self, req_url, data=None, header=None,
                      method='get', tobase64=False):
        final_headers = dict(self.headers)
        if self.enable_verify_time_sign:
            ts = str(int(time.time()))
            sign = self.aes_encode(ts, self.key, self.iv)
            final_headers['app-api-verify-time'] = ts
            final_headers['app-api-verify-sign'] = sign
        if header:
            final_headers.update(header)

        try:
            if (method or 'get').lower() == 'post':
                rsp = self.fetch(req_url, headers=final_headers,
                                 method='post', data=data, timeout=10)
            else:
                rsp = self.fetch(req_url, headers=final_headers, timeout=10)
            if tobase64:
                content = rsp.content if hasattr(rsp, 'content') else b''
                return base64.b64encode(content).decode('utf-8')
            return rsp.text if hasattr(rsp, 'text') else str(rsp)
        except Exception as e:
            self.log("request_text fail %s -> %s" % (req_url, e))
            return ''

    # ------------------------- 首页 -------------------------
    def homeContent(self, filter=False):
        init_url = "%s/%s/%s" % (self.site_url, self.api_prefix, self.init_suffix)
        raw = self._request(init_url)
        try:
            rets = json.loads(raw).get('data', '')
        except Exception:
            self.log("home init 解析失败")
            return {'class': [], 'filters': {}}

        decoded = self.aes_decode(rets, self.key, self.iv)
        try:
            data = json.loads(decoded)
        except Exception:
            self.log("home data 解密失败")
            return {'class': [], 'filters': {}}

        # 弹幕地址
        raw_danmu = (data.get('config') or {}).get('third_danmu_url', '')
        if isinstance(raw_danmu, list):
            raw_danmu = next((u for u in raw_danmu
                              if isinstance(u, str) and u.strip()), '')
        elif not isinstance(raw_danmu, str):
            raw_danmu = ''
        if raw_danmu:
            self.third_danmu_base_url = raw_danmu.strip()
            lower = self.third_danmu_base_url.lower()
            if not re.search(r'[?&]url=$', lower):
                self.third_danmu_base_url += ('&' if '?' in self.third_danmu_base_url else '?') + 'url='
        else:
            self.third_danmu_base_url = 'https://dmku.hls.one/?ac=dm&url='

        # box_config 解密
        box_config = data.get('box_config')
        if box_config:
            original_key = self.key
            swapped_key = original_key[::-1]
            md5_key = self.md5(swapped_key)
            dynamic_iv = md5_key[:16]
            decrypted = self.aes_decode(box_config, swapped_key, dynamic_iv)
            try:
                box_json = json.loads(decrypted)
            except Exception:
                box_json = {}
            if box_json.get('search_name'):
                self.search_api_suffix = box_json['search_name']
            if box_json.get('signature_name') and box_json.get('signature_value'):
                self.sou_param_name = box_json['signature_name']
                self.sou_salt = self._process_signature_value(box_json['signature_value'])
            api_header = box_json.get('api_header') or {}
            if api_header.get('key') and api_header.get('value'):
                self.extra_search_headers[api_header['key']] = api_header['value']
        else:
            self.search_api_suffix = 'searchList'
            self.sou_param_name = ''
            self.sou_salt = ''

        self.search_status = bool((data.get('config') or {}).get('system_search_verify_status', False))

        filters = {}
        classes = []
        self.home_vods = []

        for item in data.get('type_list') or []:
            tid = item.get('type_id')
            if tid is not None and int(tid) > 0:
                rec = item.get('recommend_list')
                if isinstance(rec, list):
                    self.home_vods.extend(rec)

            classes.append({
                'type_id': tid,
                'type_name': item.get('type_name'),
            })

            filter_list = []
            for f in item.get('filter_type_list') or []:
                name = f.get('name')
                if name not in ('class', 'area', 'lang', 'year', 'sort'):
                    continue
                cn = {'class': '分类', 'area': '区域', 'lang': '语言',
                      'year': '年份', 'sort': '排序'}[name]
                filter_list.append({
                    'name': cn,
                    'key': name,
                    'value': [{'v': i, 'n': i} for i in (f.get('list') or [])],
                })
            if filter_list:
                filters[str(tid)] = filter_list

        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        return {'list': self.home_vods}

    @staticmethod
    def _process_signature_value(sig):
        if len(sig) < 8:
            return sig[::-1]
        rear = sig[-8:][::-1]
        front = sig[:-8][::-1]
        return front + rear

    # ------------------------- 分类 -------------------------
    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if page <= 0:
            page = 1
        if isinstance(extend, str):
            try:
                extend = json.loads(extend)
            except Exception:
                extend = {}
        if not extend:
            extend = {}

        url = "%s/%s/typeFilterVodList" % (self.site_url, self.api_prefix)
        params = {
            "area": extend.get('area') or "全部",
            "sort": extend.get('sort') or "最新",
            "class": extend.get('class') or "全部",
            "type_id": tid,
            "year": extend.get('year') or "全部",
            "lang": extend.get('lang') or '全部',
            "page": page,
        }
        raw = self._request(url, params, '', 'post')
        try:
            enc_data = json.loads(raw).get('data', '')
        except Exception:
            return {'list': [], 'page': page, 'pagecount': 0, 'limit': 24, 'total': 0}

        decoded = self.aes_decode(enc_data, self.key, self.iv)
        try:
            videos = json.loads(decoded).get('recommend_list') or []
        except Exception:
            videos = []

        return {
            'list': videos,
            'page': page,
            'pagecount': 9999,
            'limit': 24,
            'total': 9999 * 24,
        }

    # ------------------------- 详情 -------------------------
    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        vod_id = str(ids[0])
        url = "%s/%s/vodDetail" % (self.site_url, self.api_prefix)
        raw = self._request(url, {'vod_id': vod_id}, '', 'post')
        try:
            enc_data = json.loads(raw).get('data', '')
        except Exception:
            return {'list': []}
        decoded = self.aes_decode(enc_data, self.key, self.iv)
        try:
            info = json.loads(decoded)
        except Exception:
            return {'list': []}

        vod = info.get('vod') or {}

        # ===== 简介加前缀 =====
        original_content = vod.get('vod_content') or ''
        if original_content:
            vod_content = INTRO_PREFIX + "\n" + original_content
        else:
            vod_content = INTRO_PREFIX

        videos = {
            'vod_id': vod.get('vod_id'),
            'vod_name': vod.get('vod_name'),
            'vod_area': vod.get('vod_area'),
            'vod_director': vod.get('vod_director'),
            'vod_actor': vod.get('vod_actor'),
            'vod_pic': vod.get('vod_pic'),
            'vod_content': vod_content,
            'type_name': vod.get('vod_class'),
            'vod_year': vod.get('vod_year'),
        }

        play_sources = []
        for item in info.get('vod_play_list') or []:
            player_info = item.get('player_info') or {}
            parse = player_info.get('parse') or ''
            ua = player_info.get('user_agent') or self.custom_play_ua or ''
            name_urls_list = []
            for item2 in item.get('urls') or []:
                name = item2.get('name', '')
                url2 = item2.get('url', '')
                token = item2.get('token', '')
                parse_api_url = item2.get('parse_api_url', '')
                nid = item2.get('nid', 1)
                name_urls_list.append(
                    "%s$%s@@%s@@%s@@%s@@%s@@%s@@%s" % (
                        name, url2, parse, token, parse_api_url, ua,
                        vod.get('vod_id'), nid))
            play_sources.append({
                'show': player_info.get('show') or 'Unknown',
                'urls': '#'.join(name_urls_list),
            })

        # 同名去重
        show_count = {}
        for src in play_sources:
            show_name = src['show']
            if show_name in show_count:
                show_count[show_name] += 1
                src['show'] = "%s%d" % (show_name, show_count[show_name])
            else:
                show_count[show_name] = 1

        # 线路排序
        def _priority(show):
            s = show.lower()
            if '4k' in s: return 1
            if 'k' in s: return 2
            if '独家' in s: return 3
            if '秒播' in s: return 4
            if '自建' in s: return 5
            if '蓝光' in s: return 6
            if '专线' in s: return 7
            return 8

        play_sources.sort(key=lambda x: _priority(x['show']))

        froms = [s['show'] for s in play_sources]
        urls = [s['urls'] for s in play_sources]
        videos['vod_play_from'] = '$$$'.join(froms)
        videos['vod_play_url'] = '$$$'.join(urls)

        return {'list': [videos]}

    # ------------------------- 播放 -------------------------
    def playerContent(self, flag, id, vipFlags=None):
        parts = str(id).split('@@')
        play_url = parts[0] if len(parts) > 0 else ''
        parse = parts[1] if len(parts) > 1 else ''
        token = parts[2] if len(parts) > 2 else ''
        parse_api_url = parts[3] if len(parts) > 3 else ''
        ua = parts[4] if len(parts) > 4 else ''
        vod_id = parts[5] if len(parts) > 5 else ''
        nid_str = parts[6] if len(parts) > 6 else '1'

        # 弹幕
        danmaku_url = ''
        if self.third_danmu_base_url and vod_id:
            try:
                nid = int(nid_str)
            except Exception:
                nid = 1
            if nid < 1:
                nid = 1
            danmu_params = {
                'url_position': str(nid - 1),
                'vod_id': vod_id,
            }
            danmu_ret = self._request(
                "%s/%s/danmuList" % (self.site_url, self.api_prefix),
                danmu_params, '', 'post')
            try:
                danmu_resp = json.loads(danmu_ret)
                if danmu_resp.get('data'):
                    dec = self.aes_decode(danmu_resp['data'], self.key, self.iv)
                    dec_json = json.loads(dec) if dec else {}
                    official = (dec_json or {}).get('official_url')
                    if official:
                        real = self.third_danmu_base_url + official
                        # Python 侧没有 js2Proxy, 直接给出拼接后的 URL,
                        # 由 TVBox 的 danmaku 字段消费 / 或走 localProxy
                        danmaku_url = urllib.parse.quote(real, safe='')
            except Exception as e:
                self.log("danmu fail: %s" % e)

        # 情况 1: 直链
        is_direct = (
            ('http://' in play_url or 'https://' in play_url) and
            ('.m3u8' in play_url or '.mp4' in play_url or '.mkv' in play_url) and
            not parse_api_url
        )
        if is_direct:
            res = {'parse': 0, 'url': play_url, 'danmaku': danmaku_url}
            if ua:
                res['header'] = {'User-Agent': ua}
            return res

        # 情况 2: parse 是 http 解析接口
        if parse.startswith('http'):
            parse_url = parse + play_url
            if token:
                parse_url += '&token=' + token
            req_headers = {}
            if ua:
                req_headers['User-Agent'] = ua
            rets = self._request(parse_url, None, req_headers, 'get')
            if 'DOCTYPE html' in (rets or ''):
                res = {'parse': 1, 'url': parse_url, 'danmaku': danmaku_url}
                if ua:
                    res['header'] = {'User-Agent': ua}
                return res
            try:
                parse_json = json.loads(rets)
                url2 = parse_json.get('url') or (parse_json.get('data') or {}).get('url') or ''
            except Exception:
                url2 = ''
            res = {'parse': 0, 'url': url2, 'danmaku': danmaku_url}
            if ua:
                res['header'] = {'User-Agent': ua}
            return res

        # 情况 3: 走站内 vodParse
        params = {
            'parse_api': parse,
            'url': self.aes_encode(play_url, self.key, self.iv),
            'token': token,
        }
        req_headers = {}
        if ua:
            req_headers['User-Agent'] = ua
        rets = self._request(
            "%s/%s/vodParse" % (self.site_url, self.api_prefix),
            params, req_headers, 'post')
        final_play_url = ''
        try:
            data = json.loads(rets).get('data', '')
            url_decoded = self.aes_decode(data, self.key, self.iv)
            parsed = json.loads(url_decoded)
            final_play_url = json.loads(parsed.get('json', '{}')).get('url', '')
        except Exception as e:
            self.log("vodParse fail: %s" % e)

        res = {'parse': 0, 'url': final_play_url, 'danmaku': danmaku_url}
        if ua:
            res['header'] = {'User-Agent': ua}
        return res

    # ------------------------- 搜索 -------------------------
    def searchContent(self, key, quick, pg="1"):
        if self.has_custom_init:
            self.homeContent()

        search_path = self.search_api_suffix or 'searchList'
        url = "%s/%s/%s" % (self.site_url, self.api_prefix, search_path)

        params = {
            'page': '1',
            'type_id': '0',
            'keywords': key,
        }

        if self.sou_param_name and self.sou_salt:
            ts = str(int(time.time()))
            sou_string = "/%s-%s-sb-0-%s" % (self.sou_param_name, ts, self.sou_salt)
            md5_value = self.md5(sou_string)
            params[self.sou_param_name] = "%s-sb-0-%s" % (ts, md5_value)

        search_headers = dict(self.headers)
        search_headers.update(self.extra_search_headers)

        if self.force_verify_code:
            params['code'] = self.force_verify_code
            params['key'] = self._generate_uuid()

        videos = []
        attempted_captcha = False
        attempted_slider = False
        slider_verified = False
        wait_retry_count = 0
        max_wait_retries = 2
        max_retries = 1
        retry_count = 0

        while True:
            enc_data = self._request(url, params, search_headers, 'post')
            try:
                response = json.loads(enc_data)
            except Exception:
                break

            code = response.get('code')

            # 滑块验证
            if code == 1001 and response.get('need_slider') is True and not attempted_slider:
                attempted_slider = True
                slider_ok = self._handle_slider(search_headers)
                if slider_ok:
                    slider_verified = True
                    continue

                if not slider_verified:
                    if (not self.force_verify_code) and (
                            self.search_status or
                            (code == 0 and '验证码' in (response.get('msg') or ''))):
                        if attempted_captcha:
                            break
                        attempted_captcha = True
                        self._handle_captcha(params)
                        retry_count += 1
                        continue
                    else:
                        break

            msg = response.get('msg') or ''

            # 等待类提示
            if (code == 0 and
                    (not response.get('data') or len(response.get('data') or []) == 0) and
                    re.search(r'等.*秒|等待.*秒|等|搜|请等待|稍等|稍候', msg, re.I)):
                if wait_retry_count >= max_wait_retries:
                    break
                wait_seconds = self._extract_wait_time(msg)
                if wait_seconds < 1:
                    wait_seconds = 2
                if wait_seconds > 30:
                    wait_seconds = 30
                time.sleep(wait_seconds + 1)
                wait_retry_count += 1
                continue

            # 正常返回数据
            data_field = response.get('data')
            if data_field:
                decoded = self.aes_decode(data_field, self.key, self.iv)
                try:
                    videos = (json.loads(decoded) or {}).get('search_list') or []
                except Exception:
                    videos = []
                break

            # 需要图形验证码
            elif (not self.force_verify_code) and (
                    self.search_status or
                    (code == 0 and '验证码' in msg)):
                if attempted_captcha:
                    break
                attempted_captcha = True
                self._handle_captcha(params)
                retry_count += 1
                continue
            else:
                break

        return {'list': videos}

    def searchContentPage(self, key, quick, pg="1"):
        return self.searchContent(key, quick, pg)

    def _handle_slider(self, search_headers):
        """滑块验证, 成功返回 True"""
        try:
            get_slider_url = "%s/%s/getSlider" % (self.site_url, self.api_prefix)
            slider_resp = self._request(get_slider_url, {}, search_headers, 'post')
            slider_json = json.loads(slider_resp)
            if slider_json.get('code') != 1 or not slider_json.get('data'):
                return False

            slider_dec = self.aes_decode(slider_json['data'], self.key, self.iv)
            slider_data = json.loads(slider_dec)
            slider_id = slider_data.get('slider_id', '')
            target_x = int(slider_data.get('target_x') or 0)

            if not slider_id or target_x <= 0:
                return False

            pos_x = target_x
            random_offset = random.randint(-1, 1)
            pos_x = target_x + random_offset
            bg_width = int(slider_data.get('bg_width') or 280)
            if pos_x < 1:
                pos_x = 1
            if pos_x > bg_width:
                pos_x = bg_width

            timestamp = int(time.time() * 1000)
            time.sleep(1)

            verify_params = {
                'pos_x': str(pos_x),
                'slider_id': slider_id,
                'timestamp': str(timestamp),
            }
            verify_url = "%s/%s/verifySlider" % (self.site_url, self.api_prefix)
            verify_resp = self._request(verify_url, verify_params, search_headers, 'post')
            verify_json = json.loads(verify_resp)
            if verify_json.get('code') == 1 and verify_json.get('data'):
                verify_dec = self.aes_decode(verify_json['data'], self.key, self.iv)
                verify_result = json.loads(verify_dec)
                if verify_result.get('verified') is True:
                    return True
        except Exception as e:
            self.log("slider fail: %s" % e)
        return False

    def _handle_captcha(self, params):
        """图形验证码 + OCR"""
        random_uuid = self._generate_uuid()
        modified_prefix = self.api_prefix.replace('.index', '')
        verify_url = "%s/%s.verify/create?key=%s" % (
            self.site_url, modified_prefix, random_uuid)
        base64_img = self._request_text(verify_url, None, self.headers, 'get', True)
        base64_img = (base64_img or '').replace('\n', '')
        ocr_result = self._request_text(
            'https://api.nn.ci/ocr/b64/text',
            base64_img,
            {'User-Agent': 'okhttp/3.10.0'},
            'post')
        params['code'] = (ocr_result or '').strip()
        params['key'] = random_uuid

    @staticmethod
    def _generate_uuid():
        chars = '0123456789abcdef'
        template = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
        out = []
        for c in template:
            if c == 'x':
                out.append(chars[random.randint(0, 15)])
            elif c == 'y':
                r = random.randint(0, 15)
                out.append(chars[(r & 0x3) | 0x8])
            else:
                out.append(c)
        return ''.join(out)

    # ------------------------- 等待时间解析 -------------------------
    _CN_NUM = {
        '零': 0, '〇': 0, '一': 1, '壹': 1, '二': 2, '贰': 2, '两': 2,
        '三': 3, '叁': 3, '四': 4, '肆': 4, '五': 5, '伍': 5,
        '六': 6, '陆': 6, '七': 7, '柒': 7, '八': 8, '捌': 8,
        '九': 9, '玖': 9, '十': 10, '拾': 10,
    }

    def _chinese_to_number(self, s):
        m = self._CN_NUM
        if len(s) == 1:
            return m.get(s, 2)
        if s.startswith('十') and len(s) == 2:
            return 10 + (m.get(s[1]) or 0)
        if s.endswith('十') and len(s) == 2:
            return (m.get(s[0]) or 0) * 10
        if len(s) == 3 and '十' in s:
            tens = m.get(s[0])
            units = m.get(s[2])
            if tens and units:
                return tens * 10 + units
            return (tens or 0) * 10
        return 2

    def _extract_wait_time(self, message):
        m = re.search(r'(\d+)\s*秒', message)
        if m:
            return int(m.group(1))
        m = re.search(r'([零一二三四五六七八九十两壹贰叁肆伍陆柒捌玖拾〇]+)\s*秒', message)
        if m:
            return self._chinese_to_number(m.group(1))
        if re.search(r'几秒|数秒|若干秒', message, re.I):
            return 3
        return 2

    # ------------------------- 弹幕代理 -------------------------
    def localProxy(self, param):
        try:
            url = ''
            if isinstance(param, dict):
                url = param.get('url') or param.get('danmaku') or ''
            else:
                for pair in str(param).split('&'):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        if k in ('url', 'danmaku'):
                            url = v
            if url and '%' in url:
                url = urllib.parse.unquote(url)
            if not url or not url.startswith('http'):
                return [200, 'text/plain; charset=utf-8',
                        b'missing danmaku url', '']

            json_content = self._request_text(url, None, self.headers, 'get')
            json_obj = json.loads(json_content)
            xml = self._json_danmaku_to_xml(json_obj)
            return [200, 'text/xml; charset=utf-8',
                    xml.encode('utf-8'), '']
        except Exception as e:
            self.log("localProxy fail: %s" % e)
            return [200, 'text/xml; charset=utf-8',
                    b'<?xml version="1.0" encoding="utf-8"?><i><code>0</code><id>error</id></i>', '']

    @staticmethod
    def _escape_xml(s):
        if not isinstance(s, str):
            return ''
        return (s.replace('&', '&amp;').replace('<', '&lt;')
                 .replace('>', '&gt;').replace('"', '&quot;')
                 .replace("'", '&apos;'))

    @staticmethod
    def _hex_to_dec(hex_str):
        h = (hex_str or '#FFFFFF').lstrip('#').upper()
        if len(h) != 6:
            h = h.ljust(6, '0')[:6]
        try:
            return int(h, 16)
        except Exception:
            return 0xFFFFFF

    def _json_danmaku_to_xml(self, js):
        if not js or not isinstance(js.get('danmuku'), list):
            return ('<?xml version="1.0" encoding="utf-8"?>'
                    '<i><code>0</code><id>error_no_danmaku</id></i>')
        lines = ['<?xml version="1.0" encoding="utf-8"?>', '<i>']
        lines.append(' <code>%s</code>' % (js.get('code') or 0))
        lines.append(' <id>%s</id>' % self._escape_xml(js.get('name') or '12345'))
        position_map = {'top': 5, 'right': 1, 'bottom': 4, 'left': 6, 'scroll': 1}
        for danmu in js['danmuku']:
            if not isinstance(danmu, list) or len(danmu) < 5:
                continue
            tm = danmu[0] if len(danmu) > 0 else 0
            mode = danmu[1] if len(danmu) > 1 else 'scroll'
            text = danmu[4] if len(danmu) > 4 else ''
            fs_raw = danmu[7] if len(danmu) > 7 else '24px'
            color_hex = '#' + ''.join(random.choice('0123456789ABCDEF') for _ in range(6))
            pos = position_map.get(mode, 1)
            color_dec = self._hex_to_dec(color_hex)
            try:
                fs = int(str(fs_raw).replace('px', '').replace('PX', '')) or 24
            except Exception:
                fs = 24
            p = "%.3f,%d,%d,%d,,,,," % (float(tm), pos, fs, color_dec)
            lines.append(' <d p="%s">%s</d>' % (p, self._escape_xml(text)))
        lines.append('</i>')
        return '\n'.join(lines)

    # ------------------------- 其他 -------------------------
    def isVideoFormat(self, url):
        return '.m3u8' in url or '.mp4' in url or url.startswith('http')

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def close(self):
        self.destroy()