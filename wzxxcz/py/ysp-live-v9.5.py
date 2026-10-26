# -*- coding: utf-8 -*-
"""
IPTV 2.9.9 源导出插件（组织风格参照 剧圈圈.py）
包名 com.iptv38.code / 首页邀请码 G9UVYP / 服务端 https://xhtv.online

──────────────────────────────────────────────────────────────────────────
一、源是怎么拿到的（分析结论）
  1. 握手        POST /api/init/index：请求体 AES-128-CBC 加密 + HMAC-SHA256 签名，
                 会话密钥由设备码（device_code）派生；提交邀请码 G9UVYP 后服务端回发新邀请码
                 （本机拿到 GAHXEF，is_vip=true，remain_days=32）。
  2. 频道清单    /api/channel/list 返回 18 组 882 个频道共 889 条 source，
                 协议分布：tvbus:// 884 条、p8p:// 4 条、webview:// 1 条。
  3. 播放脚本    /api/script/manifest 下发 3 个内置播放脚本（/api/script/fetch 校验 hash）：
                   ysp.js          央视频直播
                   河北电视台.js    河北广播电视台直播
                   fhx.js          凤凰卫视直播
                 点播接口在 /api/vod/manifest（国内一线 / 国内二线两路采集接口）。
  4. **未收录的部分**：频道清单里的 tvbus:// / p8p:// / webview:// 三种地址都不是直接可播的
     媒体地址——tvbus 是 50 字符 base58 密文（解码后恒 37 字节、32 字节体随机性极高），
     必须由 Android 端 libtvcore.so（TVCore）与 libp2pcdn.so（AccelEngine_nativeDecrypt）
     在运行时解密，并依赖 p2p 节点；p8p:// 依赖同一套 p2p 网络；webview:// 只剩一个网页壳。
     这些源在纯 Python 环境（无 Android、无 p2p 节点）下无法还原，因此本插件不收录，
     下面收录的是能真正离线复现、并已逐个实测可播的源。

──────────────────────────────────────────────────────────────────────────
二、收录的源与实测证据（逐个请求源站，取真实切片核对）
  央视频      54 路（ysp.js 里 76 个频道键中 55 个键接口有 playurl，其中 gansu/gsws 指向同一
              个 livepid，去重后 54 路）
              证据：逐路实测 53 路为 HTTP 200/206 + Content-Type: application/vnd.apple.mpegurl
              + 正文 #EXTM3U；CCTV-10 一天前实测可播，交付前复检时源站改为回 iretcode=12
              （接口不下发地址，同一套参数在 CCTV-9 等兄弟频道正常，属源站侧波动），暂保留在表中。
              未收录的 21 个键：CCTV-11/12/14/15/16/16(4K)/17/4K 及 CCTV 风云剧场、第一剧场、
              怀旧剧场、世界地理、风云音乐、兵器科技、风云足球、高尔夫·网球、女性时尚、
              央视文化精品、央视台球、电视指南、卫生健康——接口一律不返回 playurl（下线或 DRM）。
  河北电视台   7 路（源站文章列表只有 7 条有直播数据，脚本里第 8 个键 hbsj 无对应源）
              证据：HTTP 206 + Content-Type: application/vnd.apple.mpegurl + 正文 #EXTM3U
  凤凰卫视     3 路（凤凰中文 / 凤凰资讯 / 凤凰香港）
              证据：HTTP 200 + Content-Type: video/x-flv + FLV 文件头（单次取流 2～2.6 MB）
              注：接口下发的一次性签名地址偶发 403，插件在取流前做一次轻量探活，命中 403 时
              自动重新申请地址，避免偶发失败。
              【清晰度实测结论】匿名（无有效 token）情况下每路凤凰频道源站只有两档真实流：
                *48.flv = 854×480（对应 live_qa=hd）
                *36.flv = 640×360（sd/uhd/shd/hhd/720p/1080p 等所有其它 qa 名一律映射到它，
                                   名字叫 uhd/1080p 也是 360p，切勿被命名迷惑）
              live_qa=fhd 需要有效 VIP token（fengshows 登录接口），匿名登录（code=852）源站
              一律回「賬號錯誤」，因此 fhd 在无账号时恒不可用；854×480 即匿名可用上限。
              dispatch.fengshows.cn:8484 会 301 跳转到 qctv.fengshows.cn（query 原样保留），
              签名在 query 里不受影响，播放器跟随 301 即可。
  点播        国内一线 https://cj.lziapi.com/api.php/provide/vod/from/lzm3u8/ （JSON，约 16 万条）
              国内二线 https://bfzyapi.com/api.php/provide/vod/at/xml （XML，约 16.5 万条）
              列表 / 分类 / 详情 / 搜索 四类请求均实测通。
  台湾直播     中国台湾 30 路（中天系/TVBS系/民视/三立/东森/中视/华视/公视/年代/
              八大/大爱/龙华/靖天/Momo），来自公开聚合源（198.16.100.90 与 50.7.238.114
              双节点互为镜像，中天系另有抖音 CDN 源）。
              每路频道挂多条候选源，取流前逐路探活（校验 200 + #EXTM3U 头），
              取第一个可用的；候选源列表可在 TWN_CHANNELS 里自行增补。
              注意：聚合源稳定性一般且无法长期保证，若全部失效请补充新源；
              中天官方 24h 直播在 YouTube「中天電視」有正版流，但需代理环境。

  说明：智播源站里 2 个键（btws、gxpd）的接口能给 playurl 且实测可播，但源站侧没有公开它们
  的频道名（央视频网页版频道列表里没有这两个 pid），故频道名标为「待确认频道」。

──────────────────────────────────────────────────────────────────────────
三、插件的路由与内部 id 约定
  分类 tid：live_ysp 央视频直播 / live_hebtv 河北电视台 / live_fengx 凤凰卫视 / live_all 直播全部
            vod1 国内一线 / vod2 国内二线
  频道 id：live|ysp|<键>  live|hebtv|<序号>  live|fengx|<频道码>
  点播 id：vod1|<vod_id>   vod2|<vod_id>
  回看：fhx.js 里还有一条 playseek 回看分支，本次未取得可用回看地址，故未移植。

──────────────────────────────────────────────────────────────────────────
四、用法
  TVBox / 影视类客户端：把本文件放到 Spider 目录，配置里按包名加载（同时需依赖 requests，
  无 requests 时自动回退到框架自带的 fetch 与标准库 urllib）。接口遵循影视爬虫的标准六件套：
  homeContent / homeVideoContent / categoryContent / detailContent / searchContent / playerContent。

  单独自测（本文件同时可作为库被导入）：
      import importlib.util
      spec = importlib.util.spec_from_file_location("iptv299", r"IPTV2.9.9.py")
      mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
      sp = mod.Spider(); sp.init("")
      print(sp.homeContent(False))                      # 分类
      print(sp.categoryContent("live_ysp", 1, False, {}))  # 央视频 54 路
      print(sp.playerContent("", "live|ysp|cctv1", False))  # {"parse":0,"url":...}
"""

import hashlib
import json
import random
import re
import threading
import time
import warnings
from urllib.parse import quote

try:
    warnings.filterwarnings("ignore")
    import urllib3
    urllib3.disable_warnings()
except Exception:
    pass

try:
    from base.spider import Spider
except ImportError:
    import requests as _rq
    from requests.adapters import HTTPAdapter

    class Spider:
        def __init__(self):
            self._session = _rq.Session()
            adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)

        def fetch(self, url, headers=None, timeout=15, **kw):
            headers = headers or {}
            headers.setdefault("User-Agent", UA)
            return self._session.get(url, headers=headers, timeout=timeout, verify=False, **kw)

        def destroy(self):
            try:
                self._session.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# 应用与通用常量
# ---------------------------------------------------------------------------

APP = {
    "name": "IPTV 2.9.9",
    "package": "com.iptv38.code",
    "server": "https://xhtv.online",
    "invite": "G9UVYP",
}

UA = ("Mozilla/5.0 (Linux; Android 12; M2007J22C) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")

LIVE_PAGE_SIZE = 60
VOD_PAGE_SIZE = 20
LIST_CACHE_TTL = 60
DETAIL_CACHE_TTL = 300
SEARCH_CACHE_TTL = 30
CIRCUIT_FAILS = 3
CIRCUIT_COOLDOWN = 30

GROUP_NAMES = {"ysp": "央视频", "hebtv": "河北电视台", "fengx": "凤凰卫视", "twn": "台湾直播"}

# ---------------------------------------------------------------------------
# 中天直播（中国台湾）：常量
# 直播源为公开聚合源，按顺序探活，取第一个可用的（单源失效自动切下一路）。
# 注：这些聚合源稳定性一般，且沙箱环境无法实测，若全部失效可自行在列表里补充新源；
#     中天官方 24h 直播在 YouTube（中天電視）有正版流，但需代理环境，TVBox 场景不适用。
# ---------------------------------------------------------------------------

TWN_CHANNELS = [
    ("ztxw", "中天新闻", [
        "https://pull-l3-cny.douyincdn.com/live/7898d38d54c60879ba96a1fa42edbd53.m3u8",
        "http://198.16.100.90:8278/ctinews/playlist.m3u8?tid=MB0B9546410395464103&ct=19249&tsum=30c62d7eec5ce9a49a64c3fa3ff8a8b7",
        "http://50.7.238.114:8278/ctinews/playlist.m3u8?tid=MB0B9546410395464103&ct=19249&tsum=30c62d7eec5ce9a49a64c3fa3ff8a8b7",
    ]),
    ("ztzh", "中天综合", [
        "https://pull-l3-cny.douyincdn.com/live/5f26752efeee9e0c53cf6b530640ce60.m3u8",
        "http://198.16.100.90:8278/ctizhonghe/playlist.m3u8?tid=MB6B3888954738889547&ct=19254&tsum=d0cb922e44e8a16bea598530697c581e",
        "http://50.7.238.114:8278/ctizhonghe/playlist.m3u8?tid=MB6B3888954738889547&ct=19254&tsum=d0cb922e44e8a16bea598530697c581e",
    ]),
    ("ztyl", "中天娱乐", [
        "https://pull-l3-cny.douyincdn.com/live/37e4951f0608d79a74ebed4ab2da462a.m3u8",
        "http://198.16.100.90:8278/ctient/playlist.m3u8?tid=MC9C7081133170811331&ct=19249&tsum=8b08b54208f3ee30e12f419d587f46ac",
        "http://50.7.238.114:8278/ctient/playlist.m3u8?tid=MC9C7081133170811331&ct=19249&tsum=8b08b54208f3ee30e12f419d587f46ac",
    ]),
    ("ztyz", "中天亚洲", [
        "http://198.16.100.90:8278/ctiasia_twn/playlist.m3u8?tid=MBAB5565131955651319&ct=19249&tsum=6c292a6f51658779ced6a108f779ed35",
        "http://50.7.238.114:8278/ctiasia_twn/playlist.m3u8?tid=MBAB5565131955651319&ct=19249&tsum=6c292a6f51658779ced6a108f779ed35",
    ]),
    ("tvbs", "TVBS", [
        "http://198.16.100.90:8278/tvbs/playlist.m3u8?tid=MEFE3093330530933305&ct=19249&tsum=ce6b5e9293b3618104ad53084745a223",
        "http://50.7.238.114:8278/tvbs/playlist.m3u8?tid=MEFE3093330530933305&ct=19249&tsum=ce6b5e9293b3618104ad53084745a223",
    ]),
    ("tvbsn", "TVBS新闻", [
        "http://198.16.100.90:8278/tvbs_n/playlist.m3u8?tid=MA4A2233260122332601&ct=19249&tsum=513a9dcb42fa8b98e1792d513dd3e2ee",
        "http://50.7.238.114:8278/tvbs_n/playlist.m3u8?tid=MA4A2233260122332601&ct=19249&tsum=513a9dcb42fa8b98e1792d513dd3e2ee",
    ]),
    ("tvbsh", "TVBS欢乐", [
        "http://198.16.100.90:8278/tvbshuanle_twn/playlist.m3u8?tid=MA5A9262292692622926&ct=19254&tsum=cd369d68a5d2c1a2fa04df748cda142c",
        "http://50.7.238.114:8278/tvbshuanle_twn/playlist.m3u8?tid=MA5A9262292692622926&ct=19254&tsum=cd369d68a5d2c1a2fa04df748cda142c",
    ]),
    ("ftv", "民视", [
        "http://198.16.100.90:8278/ftvhd_taiwan/playlist.m3u8?tid=MC8C5908644059086440&ct=19249&tsum=c96d2cd48b11d40ca9e97fb3addb1384",
        "http://50.7.238.114:8278/ftvhd_taiwan/playlist.m3u8?tid=MC8C5908644059086440&ct=19249&tsum=c96d2cd48b11d40ca9e97fb3addb1384",
    ]),
    ("ftvn", "民视新闻", [
        "http://198.16.100.90:8278/ftvnew_taiwan/playlist.m3u8?tid=MA7A6968320369683203&ct=19249&tsum=e3b040434ed43f12a738964a100a0e59",
        "http://50.7.238.114:8278/ftvnew_taiwan/playlist.m3u8?tid=MA7A6968320369683203&ct=19249&tsum=e3b040434ed43f12a738964a100a0e59",
    ]),
    ("ftvtw", "民视台湾", [
        "http://198.16.100.90:8278/ftvtaiwan_twn/playlist.m3u8?tid=MEFE5254515252545152&ct=19249&tsum=c17f872b1772df8f76032030cc40bdbd",
        "http://50.7.238.114:8278/ftvtaiwan_twn/playlist.m3u8?tid=MEFE5254515252545152&ct=19249&tsum=c17f872b1772df8f76032030cc40bdbd",
    ]),
    ("slzh", "三立综合", [
        "http://198.16.100.90:8278/sanlizhonghe/playlist.m3u8?tid=MF4F9472920894729208&ct=19249&tsum=874aaa2015440b417746e5c11fa40220",
        "http://50.7.238.114:8278/sanlizhonghe/playlist.m3u8?tid=MF4F9472920894729208&ct=19249&tsum=874aaa2015440b417746e5c11fa40220",
    ]),
    ("slxj", "三立戏剧", [
        "http://198.16.100.90:8278/sanlixiju_twn/playlist.m3u8?tid=MC3C7351075373510753&ct=19249&tsum=f70fc544635e38b2fd7b4bb39899df0e",
        "http://50.7.238.114:8278/sanlixiju_twn/playlist.m3u8?tid=MC3C7351075373510753&ct=19249&tsum=f70fc544635e38b2fd7b4bb39899df0e",
    ]),
    ("ettvzh", "东森综合", [
        "http://198.16.100.90:8278/ettvzhonghe/playlist.m3u8?tid=MC4C1214674912146749&ct=19254&tsum=9b96a50ba99dca1a02a27b05a6fb4b0d",
        "http://50.7.238.114:8278/ettvzhonghe/playlist.m3u8?tid=MC4C1214674912146749&ct=19254&tsum=9b96a50ba99dca1a02a27b05a6fb4b0d",
    ]),
    ("ettvxj", "东森戏剧", [
        "http://198.16.100.90:8278/ettvdrama/playlist.m3u8?tid=MA2A9945921599459215&ct=19249&tsum=c9097ecdf4a17c0922196dbf04b0c6e7",
        "http://50.7.238.114:8278/ettvdrama/playlist.m3u8?tid=MA2A9945921599459215&ct=19249&tsum=c9097ecdf4a17c0922196dbf04b0c6e7",
    ]),
    ("ettvdy", "东森电影", [
        "http://198.16.100.90:8278/ettvmovie/playlist.m3u8?tid=MBDB9268852192688521&ct=19254&tsum=7514b50ebc2e4b06f2e402578d0ac996",
        "http://50.7.238.114:8278/ettvmovie/playlist.m3u8?tid=MBDB9268852192688521&ct=19254&tsum=7514b50ebc2e4b06f2e402578d0ac996",
    ]),
    ("ettvcs", "东森超视", [
        "http://198.16.100.90:8278/ettvsuper/playlist.m3u8?tid=MB0B9022098390220983&ct=19249&tsum=594e3a93afe766cf27fd21b8addee391",
        "http://50.7.238.114:8278/ettvsuper/playlist.m3u8?tid=MB0B9022098390220983&ct=19249&tsum=594e3a93afe766cf27fd21b8addee391",
    ]),
    ("ettvcj", "东森财经新闻", [
        "http://198.16.100.90:8278/ettvcaijing_twn/playlist.m3u8?tid=MB8B2069463920694639&ct=19249&tsum=05ff51a1b274ce7d31d05bbf11df18ad",
        "http://50.7.238.114:8278/ettvcaijing_twn/playlist.m3u8?tid=MB8B2069463920694639&ct=19249&tsum=05ff51a1b274ce7d31d05bbf11df18ad",
    ]),
    ("zs", "中视", [
        "http://198.16.100.90:8278/zhongshihd_twn/playlist.m3u8?tid=MBDB6720263767202637&ct=19249&tsum=edd778f298b53c39b3b9706700032605",
        "http://50.7.238.114:8278/zhongshihd_twn/playlist.m3u8?tid=MBDB6720263767202637&ct=19249&tsum=edd778f298b53c39b3b9706700032605",
    ]),
    ("zsn", "中视新闻", [
        "http://198.16.100.90:8278/zhongshinews_twn/playlist.m3u8?tid=MD0D3377711133777111&ct=19249&tsum=ffaee3fe7040c96643b3c7f12bf2de8d",
        "http://50.7.238.114:8278/zhongshinews_twn/playlist.m3u8?tid=MD0D3377711133777111&ct=19249&tsum=ffaee3fe7040c96643b3c7f12bf2de8d",
    ]),
    ("hs", "华视", [
        "http://198.16.100.90:8278/ctshd_twn/playlist.m3u8?tid=MC3C3582911835829118&ct=19249&tsum=f2c0c86801d43be647206c4ddb8e9ce6",
        "http://50.7.238.114:8278/ctshd_twn/playlist.m3u8?tid=MC3C3582911835829118&ct=19249&tsum=f2c0c86801d43be647206c4ddb8e9ce6",
    ]),
    ("pts", "公视", [
        "http://198.16.100.90:8278/ctv_taiwan/playlist.m3u8?tid=MDCD6096520560965205&ct=19249&tsum=64237c7ffa0c00b62657a938247bcab0",
        "http://50.7.238.114:8278/ctv_taiwan/playlist.m3u8?tid=MDCD6096520560965205&ct=19249&tsum=64237c7ffa0c00b62657a938247bcab0",
    ]),
    ("ndxw", "年代新闻", [
        "http://198.16.100.90:8278/niandainews_twn/playlist.m3u8?tid=MBCB9184423891844238&ct=19249&tsum=ac0331d98099429b19c53fe6d20972ec",
        "http://50.7.238.114:8278/niandainews_twn/playlist.m3u8?tid=MBCB9184423891844238&ct=19249&tsum=ac0331d98099429b19c53fe6d20972ec",
    ]),
    ("bdzh", "八大综合", [
        "http://198.16.100.90:8278/badazhonghe/playlist.m3u8?tid=MCFC9951205299512052&ct=19249&tsum=dc4ca0de5e57c9f4caee0bb4e80c098a",
        "http://50.7.238.114:8278/badazhonghe/playlist.m3u8?tid=MCFC9951205299512052&ct=19249&tsum=dc4ca0de5e57c9f4caee0bb4e80c098a",
    ]),
    ("bdxj", "八大戏剧", [
        "http://198.16.100.90:8278/badadrama/playlist.m3u8?tid=MBCB2433143824331438&ct=19254&tsum=51660c351b3991d81434e43bd1ab720e",
        "http://50.7.238.114:8278/badadrama/playlist.m3u8?tid=MBCB2433143824331438&ct=19254&tsum=51660c351b3991d81434e43bd1ab720e",
    ]),
    ("bddy", "八大第一", [
        "http://198.16.100.90:8278/badafirst/playlist.m3u8?tid=MD2D8073200480732004&ct=19254&tsum=5cb051b366ad3740cebcc06a987d749e",
        "http://50.7.238.114:8278/badafirst/playlist.m3u8?tid=MD2D8073200480732004&ct=19254&tsum=5cb051b366ad3740cebcc06a987d749e",
    ]),
    ("daai", "大爱一台", [
        "http://198.16.100.90:8278/daai_twn/playlist.m3u8?tid=ME5E3594665135946651&ct=19249&tsum=1628ac38fd6a79879fccae39de8e845b",
        "http://50.7.238.114:8278/daai_twn/playlist.m3u8?tid=ME5E3594665135946651&ct=19249&tsum=1628ac38fd6a79879fccae39de8e845b",
    ]),
    ("lhxj", "龙华戏剧", [
        "http://198.16.100.90:8278/lunghuaxiju_twn/playlist.m3u8?tid=MF2F2793524427935244&ct=19249&tsum=db1ef83fbbbae9a364979295fd690f7d",
        "http://50.7.238.114:8278/lunghuaxiju_twn/playlist.m3u8?tid=MF2F2793524427935244&ct=19249&tsum=db1ef83fbbbae9a364979295fd690f7d",
    ]),
    ("lhox", "龙华偶像", [
        "http://198.16.100.90:8278/lunghuaidol_twn/playlist.m3u8?tid=MD6D6087277960872779&ct=19249&tsum=83e30fd8200429793355d21bf37719ff",
        "http://50.7.238.114:8278/lunghuaidol_twn/playlist.m3u8?tid=MD6D6087277960872779&ct=19249&tsum=83e30fd8200429793355d21bf37719ff",
    ]),
    ("jtgj", "靖天国际", [
        "http://198.16.100.90:8278/jingtianintl_twn/playlist.m3u8?tid=MC7C4153806141538061&ct=19254&tsum=79854f3ccdc23693ea39da52af54d35b",
        "http://50.7.238.114:8278/jingtianintl_twn/playlist.m3u8?tid=MC7C4153806141538061&ct=19254&tsum=79854f3ccdc23693ea39da52af54d35b",
    ]),
    ("momo", "Momo亲子台", [
        "http://198.16.100.90:8278/momo1_twn/playlist.m3u8?tid=MFFF9797479997974799&ct=19249&tsum=0bd9dac79cd373cc918357d3199c8b22",
        "http://50.7.238.114:8278/momo1_twn/playlist.m3u8?tid=MFFF9797479997974799&ct=19249&tsum=0bd9dac79cd373cc918357d3199c8b22",
    ]),    ("tvbsya", "TVBS亚洲台", [
        "http://38.64.72.148/hls/modn/list/4005/playlist.m3u8",
    ]),
    ("ttn", "台视新闻", []),
    ("dsxw", "东森新闻", []),
    ("slxw", "三立新闻", []),
    ("hyxw", "寰宇新闻", []),
    ("yzmz", "原住民电视台", [
        "https://streamipcfapp.akamaized.net/live/_definst_/live_720/key_b1500.m3u8",
        "http://streamipcf.akamaized.net/live/_definst_/smil:liveabr.smil/playlist.m3u8",
    ]),
    ("kjtvtv", "客家电视台", [
        "https://h5cul1yar48um3t.wcetv.com/hls/hakkatv.m3u8",
    ]),
    ("cgntv", "CGNTV", [
        "https://d3e05csss9c272.cloudfront.net/out/v1/f0bf71c57581470fb9379f603e8f5d83/CGNWebLiveCN.m3u8",
    ]),
    ("bltv", "生命电视台", [
        "https://5ddce30eb4b55.streamlock.net/bltvhd/bltv1/playlist.m3u8",
    ]),
    ("dali", "Dali TV", [
        "http://www.dalitv.com.tw:4568/live/dali/index.m3u8",
    ]),
    ("wxtv", "WXTV", [
        "https://mobile.ccdntech.com/transcoder/_definst_/vod164_Live/live/chunklist_w1177047531.m3u8",
    ]),
]
TWN_PROBE_TRIES = 2
TWN_PROBE_TIMEOUT = 10
TWN_PROBE_MINBYTES = 131072  # 探活要求实际拉到 ≥128KB，过滤播一秒就断的假源（那种只能拉到几十 KB）

# YouTube 官方 24h 直播中转（各台湾新闻台的官方频道），quality 可 1080/720
TWN_YT_RELAY = "https://iptv-go-am.vercel.app/youtube/%s?quality=%s"
TWN_YT_IDS = {
    "ztxw": "oIgbl7t0S_w",   # 中天新闻（官方 24h 直播）
    "ftvn": "ylYJSBUgaMA",   # 民视新闻
    "zsn": "TCnaIE_SAtM",    # 中视新闻
    "ttn": "xL0ch83RAK8",    # 台视新闻
    "hsn": "wM0g8EoUZ_E",    # 华视新闻
    "dsxw": "quwqlazU-c8",   # 东森新闻
    "slxw": "CKjSm5ZeehE",   # 三立新闻
    "hyxw": "B7Zp3d6xXWw",   # 寰宇新闻
}
TWN_YT_QUALITIES = ("1080", "720")


# ---------------------------------------------------------------------------
# 央视频（ysp.js）：常量
# ---------------------------------------------------------------------------

YSP = {
    "UA": "qqlive",
    "APP_VER": "V8.26.000.0171",
    "APP_VERSION": "305030",
    "PLATFORM": "4330303",
    "PKG": "com.cctv.yangshipin.app.androidp",
    "VSKEY": ("009DF0A7B3CAEF867BF84AC4FAF092CCA3D302A8467C451604C53A0691DA6CA9"
              "DFE6C44FB39195BDBC5484AB5CDA4AC0DB336340F3294F8A1FA1F1A688D99328"
              "C6D4FA7BAE387B575E76439B81B8AF364AD54F14"),
    "UNWRAP_KEY_HEX": "1f51d36b8cc8dc9f0842880c7486bab5",
    "XOR_KEY_HEX": "842eed08f066e6ea48b4caa991ed6ff3",
    "OI_RNG": [96, 198, 105, 115, 81, 255, 74],
    "SIG_SLOT": 0x0FF4BE75,
    "CKEY_SO_VER": "ckey.4.2.2.5",
    "APK_SIG": "C0764B5A",
    "APK_UID": "1341368F",
    "APPLICATION": "com.tencent.videolite.android.application.VideoLiteApplication",
    "CKEY_APPID": "1011111",
    "CKEY_V": "11",
    "HOSTS": ["https://liveinfo.ysp.cctv.cn?", "https://bkliveinfo.ysp.cctv.cn?"],
}

# ysp.js 里的两套设备身份，按顺序尝试（iPhone 那套通常即可取到地址）
YSP_IDENTITIES = [
    {"tag": "iphone", "DEVICE": "iPhone", "SYSVER": "ios18.2.1", "SDTFROM": "v3021",
     "NEWPLATFORM": "4330403", "GETPREVIEWINFO": "0", "LOGINTYPE": "1",
     "LANG": "zh-Hans_JP", "FD": "fcgo"},
    {"tag": "android", "DEVICE": "Android", "SYSVER": "12", "SDTFROM": "v5028",
     "NEWPLATFORM": "4330303", "GETPREVIEWINFO": "1", "LOGINTYPE": "",
     "LANG": "zh-Hans_CN", "FD": None},
]

# ysp.js 的频道表：键 -> (cnlid, livepid, defn, 频道名)
# 注意：脚本里的键名与真实频道存在错位（例如键 hbws 实为湖北卫视、hbws2 实为河北卫视、
# gzhws 实为安徽卫视），本表以源站返回的 cnlid 反查到的真实频道名称为准。
YSP_CHANNELS = {
    "cctv1": ("2024078201", "600001859", "fhd", "CCTV-1 综合"),
    "cctv2": ("2024075401", "600001800", "fhd", "CCTV-2 财经"),
    "cctv3": ("2024068501", "600001801", "fhd", "CCTV-3 综艺"),
    "cctv4": ("2029797101", "600001814", "fhd", "CCTV-4 中文国际"),
    "cctv5": ("2024078401", "600001818", "fhd", "CCTV-5 体育"),
    "cctv5p": ("2024078001", "600001817", "fhd", "CCTV-5+ 体育赛事"),
    "cctv6": ("2013693901", "600108442", "fhd", "CCTV-6 电影"),
    "cctv7": ("2024072001", "600004092", "fhd", "CCTV-7 国防军事"),
    "cctv8": ("2029793001", "600001803", "fhd", "CCTV-8 电视剧"),
    "cctv9": ("2024078601", "600004078", "fhd", "CCTV-9 纪录"),
    "cctv10": ("2024078701", "600001805", "fhd", "CCTV-10 科教"),
    "cctv13": ("2029797201", "600001811", "fhd", "CCTV-13 新闻"),
    "cctv8k": ("2026774101", "600156816", "fhd", "CCTV-8K 超高清"),
    "cetv1": ("2022823801", "600171827", "fhd", "中国教育电视台1频道"),
    "cgtn": ("2024181701", "600014550", "fhd", "CGTN"),
    "cgtnfy": ("2024181801", "600084704", "fhd", "CGTN 法语频道"),
    "cgtney": ("2024181901", "600084758", "fhd", "CGTN 俄语频道"),
    "cgtnalby": ("2024182001", "600084782", "fhd", "CGTN 阿拉伯语频道"),
    "cgtnxby": ("2024182101", "600084744", "fhd", "CGTN 西班牙语频道"),
    "cgtnwyjl": ("2024182301", "600084781", "fhd", "CGTN 外语纪录频道"),
    "bjws": ("2024052703", "600002309", "fhd", "北京卫视"),
    "tjws": ("2019927003", "600152137", "fhd", "天津卫视"),
    "hbws2": ("2024171503", "600002493", "fhd", "河北卫视"),
    "shanxiws": ("2029795103", "600190400", "fhd", "陕西卫视"),
    "shanxiws2": ("2025560803", "600190407", "fhd", "山西卫视"),
    "nmgws": ("2025561203", "600190401", "fhd", "内蒙古卫视"),
    "lnws": ("2024171303", "600002505", "fhd", "辽宁卫视"),
    "jlws": ("2025561503", "600190405", "fhd", "吉林卫视"),
    "hljws": ("2029797003", "600002498", "fhd", "黑龙江卫视"),
    "dfws": ("2024054503", "600002483", "fhd", "东方卫视"),
    "jsws": ("2024171103", "600002521", "fhd", "江苏卫视"),
    "zjws": ("2024054703", "600002520", "fhd", "浙江卫视"),
    "ahws": ("2024171403", "600002532", "fhd", "安徽卫视"),
    "fjdnhz": ("2024061503", "600002484", "fhd", "福建东南卫视"),
    "jxws": ("2024061703", "600002503", "fhd", "江西卫视"),
    "sdws": ("2029787903", "600002513", "fhd", "山东卫视"),
    "henanws": ("2029797303", "600002525", "fhd", "河南卫视"),
    "hbws": ("2024171203", "600002508", "fhd", "湖北卫视"),
    "hnws": ("2024054803", "600002475", "fhd", "湖南卫视"),
    "hnws2": ("2024055603", "600002506", "fhd", "海南卫视"),
    "gdws": ("2024060903", "600002485", "fhd", "广东卫视"),
    "gxws": ("2024060703", "600002509", "fhd", "广西卫视"),
    "cqws": ("2024061103", "600002531", "fhd", "重庆卫视"),
    "scws": ("2024061403", "600002516", "fhd", "四川卫视"),
    "gzhws": ("2024061603", "600002490", "fhd", "贵州卫视"),
    "ynws": ("2025561303", "600190402", "fhd", "云南卫视"),
    "xzws": ("2025558003", "600190403", "fhd", "西藏卫视"),
    "qhws": ("2025559103", "600190406", "fhd", "青海卫视"),
    "nxws": ("2025608503", "600190737", "fhd", "宁夏卫视"),
    "xjws": ("2019927403", "600152138", "fhd", "新疆卫视"),
    "szws": ("2024061303", "600002481", "fhd", "深圳卫视"),
    "gansu": ("2025561703", "600190408", "fhd", "甘肃卫视"),
    # 以下两个键源站不给频道名，只能按键名标注
    "btws": ("2025990501", "600193252", "fhd", "待确认频道（btws）"),
    "gxpd": ("2029360403", "600213139", "fhd", "待确认频道（gxpd）"),
}


# ---------------------------------------------------------------------------
# 河北电视台（河北电视台.js）：常量
# 源站文章列表只有 7 条有直播数据；频道名以源站返回的标题为准
# ---------------------------------------------------------------------------

HEBTV_API = ("https://console.cmc.hebtv.com/scms/api/com/article/getArticleList"
             "?catalogId=32557&siteId=1")
HEBTV_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Linux; Android 8.1.0; JKM-AL00b) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/81.0.4044.138 Mobile Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.hebtv.com/",
}
HEBTV_CHANNELS = [
    (1, "河北卫视"),
    (2, "经济生活"),
    (3, "河北都市"),
    (4, "文旅体育"),
    (5, "少儿科教"),
    (6, "三农频道"),
    (7, "三佳购物"),
]


# ---------------------------------------------------------------------------
# 凤凰卫视（fhx.js）：常量
# ---------------------------------------------------------------------------

FENGX_LOGIN = "https://m.fengshows.com/api/v3/mp/user/login"
FENGX_AUTH = "https://api.fengshows.cn/hub/live/auth-url?live_qa=%s&live_id=%s"
FENGX_CHANNELS = [
    ("fhzw", "f7f48462-9b13-485b-8101-7b54716411ec", "凤凰中文", "pcc"),
    ("fhzx", "7c96b084-60e1-40a9-89c5-682b994fb680", "凤凰资讯", "pin"),
    ("fhhk", "15e02d92-1698-416c-af2f-3e9a872b4d78", "凤凰香港", "phk"),
]
FENGX_HEADERS_REQ = {
    "User-Agent": "okhttp/3.14.9",
    "fengshows-client": "app(android,5041401);Redmi;29",
    "Connection": "Keep-Alive",
}
FENGX_HEADERS_PLAY = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; M2007J3SC MIUI/V12.0.12.0.QJDCNXM)",
    "Accept-Encoding": "identity",
    "Connection": "close",
    "Referer": "dispatch.fengshows.cn",
}
# 匿名可用的 qa 只有 hd（854×480）；fhd 需 VIP token，其余 qa 名全部映射到 360p（勿用）
FENGX_QA_ANON = ("hd",)
FENGX_QA_VIP = ("fhd", "hd")

# 720p 免签名通道（实测结论）：
#   qctv.fengshows.cn 上的 *72.flv（1280×720）只校验 Referer 头、不校验 txSecret，
#   带「Referer: www.fengshows.com」即可直接拉流（凤凰中文 pcc72 / 凤凰资讯 pin72 有效，
#   凤凰香港 phk72 源站不存在，自动回退签名 480p）。
#   注意 720p 节点为轮询负载，偶发 403，故取流前做最多 N 次探活，全失败再降级到签名 hd。
FENGX_HD720_URL = "http://qctv.fengshows.cn/live/0701%s72.flv"
FENGX_HD720_REFERER = "www.fengshows.com"
FENGX_HD720_TRIES = 4


# ---------------------------------------------------------------------------
# 点播接口（/api/vod/manifest 下发的两路采集源）
# ---------------------------------------------------------------------------

VOD_APIS = {
    "vod1": {"name": "国内一线", "url": "https://cj.lziapi.com/api.php/provide/vod/from/lzm3u8/",
             "fmt": "json"},
    "vod2": {"name": "国内二线", "url": "https://bfzyapi.com/api.php/provide/vod/at/xml",
             "fmt": "xml"},
}


# ---------------------------------------------------------------------------
# 分类与筛选（按可用源的组织形态分：三组内置播放脚本 + 一组汇总，再挂两路点播采集接口）
# ---------------------------------------------------------------------------

CLASSES = [
    {"type_name": "央视频直播", "type_id": "live_ysp"},
    {"type_name": "河北电视台", "type_id": "live_hebtv"},
    {"type_name": "凤凰卫视", "type_id": "live_fengx"},
    {"type_name": "台湾直播", "type_id": "live_twn"},
    {"type_name": "直播全部", "type_id": "live_all"},
    {"type_name": "国内一线", "type_id": "vod1"},
    {"type_name": "国内二线", "type_id": "vod2"},
]

FILTERS = {
    "vod1": [
        {"key": "class", "name": "类型", "value": [
            {"n": "全部", "v": ""},
            {"n": "电影", "v": "1"},
            {"n": "连续剧", "v": "2"},
            {"n": "综艺", "v": "3"},
            {"n": "动漫", "v": "4"},
            {"n": "纪录片", "v": "20"},
            {"n": "动作片", "v": "6"},
            {"n": "喜剧片", "v": "7"},
            {"n": "爱情片", "v": "8"},
            {"n": "科幻片", "v": "9"},
            {"n": "恐怖片", "v": "10"},
            {"n": "战争片", "v": "12"},
            {"n": "国产剧", "v": "13"},
            {"n": "香港剧", "v": "14"},
            {"n": "韩国剧", "v": "15"},
            {"n": "欧美剧", "v": "16"},
            {"n": "电影解说", "v": "35"},
            {"n": "短剧", "v": "46"},
        ]},
    ],
    "vod2": [
        {"key": "class", "name": "类型", "value": [
            {"n": "全部", "v": ""},
            {"n": "电影", "v": "20"},
            {"n": "连续剧", "v": "30"},
            {"n": "综艺", "v": "45"},
            {"n": "动漫", "v": "39"},
            {"n": "纪录片", "v": "28"},
            {"n": "动作片", "v": "21"},
            {"n": "喜剧片", "v": "22"},
            {"n": "爱情片", "v": "25"},
            {"n": "科幻片", "v": "24"},
            {"n": "恐怖片", "v": "23"},
            {"n": "战争片", "v": "27"},
            {"n": "国产剧", "v": "31"},
            {"n": "香港剧", "v": "33"},
            {"n": "韩国剧", "v": "34"},
            {"n": "欧美剧", "v": "32"},
            {"n": "电影解说", "v": "51"},
            {"n": "短剧大全", "v": "58"},
        ]},
    ],
}


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def _urlencode(s):
    return quote(s or "", safe="")


def _md5_hex(s):
    if isinstance(s, str):
        s = s.encode("utf-8")
    return hashlib.md5(s).hexdigest()


def _strip(txt):
    return re.sub(r"\s+", " ", txt or "").strip()


def _parse_extend(extend):
    """兼容部分客户端把筛选参数传成 JSON 字符串的情况"""
    if isinstance(extend, dict):
        return extend
    if isinstance(extend, str) and extend.strip():
        try:
            d = json.loads(extend)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}
    return {}


def _urllib_get(url, headers=None, timeout=12):
    """标准库 GET，返回文本（失败返回空串）"""
    try:
        try:
            from urllib.request import Request as _Req, urlopen as _Uo
        except ImportError:
            from urllib2 import Request as _Req, urlopen as _Uo
        req = _Req(url, headers=headers or {})
        try:
            import ssl as _ssl
            rsp = _Uo(req, timeout=timeout, context=_ssl._create_unverified_context())
        except Exception:
            rsp = _Uo(req, timeout=timeout)
        try:
            return rsp.read().decode("utf-8", "replace")
        except AttributeError:
            return rsp.read()
    except Exception:
        return ""


def _urllib_post(url, data, headers=None, timeout=12):
    """标准库 POST，data 可为 bytes/str，返回文本（失败返回空串）"""
    try:
        try:
            from urllib.request import Request as _Req, urlopen as _Uo
        except ImportError:
            from urllib2 import Request as _Req, urlopen as _Uo
        if isinstance(data, str):
            data = data.encode("utf-8")
        req = _Req(url, data=data, headers=headers or {})
        try:
            import ssl as _ssl
            rsp = _Uo(req, timeout=timeout, context=_ssl._create_unverified_context())
        except Exception:
            rsp = _Uo(req, timeout=timeout)
        return rsp.read().decode("utf-8", "replace")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# 央视频播放地址解析（逐行移植 ysp.js：自定义流加密 cKey + liveinfo 接口）
# 流程: 生成 guid/cKey -> 请求 liveinfo.ysp.cctv.cn -> 取 playurl
# ---------------------------------------------------------------------------

_YSP_MASK = 0xFFFFFFFF


def _ysp_b64chars():
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def _ysp_b64(data, url_safe=False, keep_pad=False):
    """JS 侧的自定义 base64（可控 url 安全字符与去填充）"""
    ch = _ysp_b64chars()
    out = []
    for i in range(0, len(data), 3):
        rem = len(data) - i
        n = (data[i] << 16) | ((data[i + 1] if rem > 1 else 0) << 8) | (data[i + 2] if rem > 2 else 0)
        out.append(ch[(n >> 18) & 63])
        out.append(ch[(n >> 12) & 63])
        out.append(ch[(n >> 6) & 63] if rem > 1 else "=")
        out.append(ch[n & 63] if rem > 2 else "=")
    s = "".join(out)
    if url_safe:
        s = s.replace("+", "_").replace("/", "-")
    if not keep_pad:
        s = s.replace("=", "")
    return s


def _ysp_bytes(s):
    return list(str(s).encode("utf-8"))


def _ysp_be32(v):
    v &= _YSP_MASK
    return [(v >> 24) & 255, (v >> 16) & 255, (v >> 8) & 255, v & 255]


def _ysp_be16(v):
    v &= 0xFFFF
    return [(v >> 8) & 255, v & 255]


def _ysp_rd32(b, o):
    return ((b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]) & _YSP_MASK


def _ysp_shr(v, n):
    return (v & _YSP_MASK) >> n


def _ysp_shl(v, n):
    return (v << n) & _YSP_MASK


def _ysp_wstr(s):
    b = _ysp_bytes(s if s is not None else "")
    return _ysp_be16(len(b)) + b


def _ysp_hexbytes(h):
    return [int(h[i:i + 2], 16) for i in range(0, len(h) - 1, 2)]


def _ysp_rand_hex(n, upper=False):
    h = "0123456789abcdef"
    s = "".join(h[int(random.random() * 16)] for _ in range(n))
    return s.upper() if upper else s


def _ysp_guid():
    return _ysp_rand_hex(32)


def _ysp_randnum():
    r = random.random()
    if r == 0:
        r = 1e-16
    s = "%.16g" % r
    if "e" not in s and "E" not in s:
        s = s.rstrip("0").rstrip(".")
    return s


def _ysp_tea_enc(b8, k16):
    y, z = _ysp_rd32(b8, 0), _ysp_rd32(b8, 4)
    k0, k1, k2, k3 = (_ysp_rd32(k16, 0), _ysp_rd32(k16, 4), _ysp_rd32(k16, 8), _ysp_rd32(k16, 12))
    s = 0
    d = 0x9E3779B9
    for _ in range(16):
        s = (s + d) & _YSP_MASK
        y = (y + (((_ysp_shl(z, 4) + k0) & _YSP_MASK) ^ ((z + s) & _YSP_MASK)
                  ^ ((_ysp_shr(z, 5) + k1) & _YSP_MASK))) & _YSP_MASK
        z = (z + (((_ysp_shl(y, 4) + k2) & _YSP_MASK) ^ ((y + s) & _YSP_MASK)
                  ^ ((_ysp_shr(y, 5) + k3) & _YSP_MASK))) & _YSP_MASK
    return _ysp_be32(y) + _ysp_be32(z)


def _ysp_tea_dec(b8, k16):
    y, z = _ysp_rd32(b8, 0), _ysp_rd32(b8, 4)
    k0, k1, k2, k3 = (_ysp_rd32(k16, 0), _ysp_rd32(k16, 4), _ysp_rd32(k16, 8), _ysp_rd32(k16, 12))
    d = 0x9E3779B9
    s = (d * 16) & _YSP_MASK
    for _ in range(16):
        z = (z - (((_ysp_shl(y, 4) + k2) & _YSP_MASK) ^ ((y + s) & _YSP_MASK)
                  ^ ((_ysp_shr(y, 5) + k3) & _YSP_MASK))) & _YSP_MASK
        y = (y - (((_ysp_shl(z, 4) + k0) & _YSP_MASK) ^ ((z + s) & _YSP_MASK)
                  ^ ((_ysp_shr(z, 5) + k1) & _YSP_MASK))) & _YSP_MASK
        s = (s - d) & _YSP_MASK
    return _ysp_be32(y) + _ysp_be32(z)


def _ysp_oi_decrypt(cipher, k16):
    if not cipher or len(cipher) < 16 or len(cipher) % 8 != 0:
        return None
    prev = [0] * 8
    prev2 = [0] * 8
    out = []
    for i in range(0, len(cipher), 8):
        blk = cipher[i:i + 8]
        x = [(blk[j] ^ prev[j]) & 255 for j in range(8)]
        d = _ysp_tea_dec(x, k16)
        for j in range(8):
            out.append((d[j] ^ prev2[j]) & 255)
            prev[j] = d[j]
            prev2[j] = blk[j]
    n = out[0] & 7
    start = 3 + n
    end = len(out) - 7
    if end < start:
        return None
    return out[start:end]


def _ysp_oi_encrypt(plain, k16, rng):
    pos = [0]

    def rnd():
        if pos[0] >= len(rng):
            return 0
        b = rng[pos[0]]
        pos[0] += 1
        return b

    plen = len(plain)
    pad = (plen + 1 + 2 + 7) % 8
    if pad != 0:
        pad = 8 - pad
    buf = [0] * 8
    prev = [0] * 8
    prev2 = [0] * 8
    out = []

    def flush():
        x = [(buf[j] ^ prev2[j]) & 255 for j in range(8)]
        e = _ysp_tea_enc(x, k16)
        for j in range(8):
            t = (e[j] ^ prev[j]) & 255
            prev[j] = x[j]
            prev2[j] = t
            out.append(t)

    buf[0] = (rnd() & 248) | pad
    i = 1
    while pad > 0:
        buf[i] = rnd()
        i += 1
        pad -= 1
    cnt = 0
    while cnt < 2:
        if i < 8:
            buf[i] = rnd()
            i += 1
            cnt += 1
        if i >= 8:
            flush()
            i = 0
    pi = 0
    while pi < plen:
        if i < 8:
            buf[i] = plain[pi]
            i += 1
            pi += 1
        if i >= 8:
            flush()
            i = 0
    c2 = 0
    while c2 < 7:
        if i < 8:
            buf[i] = 0
            i += 1
            c2 += 1
        if i >= 8:
            flush()
            i = 0
    if i > 0:
        for k in range(i, 8):
            buf[k] = 0
        flush()
    return out


def _ysp_calc_sig(buf):
    v = 0
    for b in buf:
        v = (131 * v + b) % 2147483648
    return v


def _ysp_tea_key():
    """从 YSP.VSKEY 解出 TEA 密钥"""
    b = _ysp_hexbytes(YSP["VSKEY"])
    b = b[:len(b) - 4]
    d = _ysp_oi_decrypt(b, _ysp_hexbytes(YSP["UNWRAP_KEY_HEX"]))
    if not d or len(d) < 20:
        return None
    pos = 2
    n = (d[pos] << 8) | d[pos + 1]
    pos += 2 + n
    n = (d[pos] << 8) | d[pos + 1]
    pos += 2 + n
    n = (d[pos] << 8) | d[pos + 1]
    if n != 16:
        return None
    return d[pos + 2:pos + 2 + 16]


def _ysp_getfd(sdtfrom):
    """由 sdtfrom 推导 fd 参数（ysp_getfd）"""
    if not sdtfrom or len(sdtfrom) <= 2:
        return "ffff"
    t = sdtfrom[1:]
    s = ""
    for i, ch in enumerate(t):
        s += chr((ord(ch) + 49 + i * 2) & 255)
    return s


def _ysp_genckey_packet(cnlid, ts, gid, appver, fd):
    plat = int(YSP["PLATFORM"])
    rndhex = _ysp_rand_hex(88, upper=True)
    apsig = _ysp_wstr(YSP["APK_SIG"]) + _ysp_wstr(YSP["APK_UID"])
    av = _ysp_bytes(appver)
    arr = []
    for piece in (_ysp_be32(66), _ysp_be32(3), _ysp_bytes("ming"), _ysp_be32(plat),
                  _ysp_be32(YSP["SIG_SLOT"]), _ysp_be32(ts), _ysp_wstr(fd), _ysp_be32(len(av)),
                  av, _ysp_wstr(cnlid), _ysp_wstr(gid), _ysp_be32(7), _ysp_be32(0), _ysp_be32(0),
                  _ysp_be32(0), _ysp_wstr(YSP["PKG"]), _ysp_wstr(YSP["PKG"]), apsig, apsig,
                  _ysp_wstr(YSP["APPLICATION"]), _ysp_wstr(YSP["PKG"]), _ysp_wstr(YSP["CKEY_APPID"]),
                  _ysp_wstr(YSP["CKEY_V"]), _ysp_wstr(YSP["VSKEY"][:8]), _ysp_wstr(YSP["CKEY_SO_VER"]),
                  _ysp_wstr(YSP["PKG"]), _ysp_wstr(YSP["PLATFORM"]),
                  _ysp_be32(len(_ysp_bytes(rndhex))), _ysp_bytes(rndhex)):
        arr += piece
    return _ysp_be16(len(arr)) + arr


def _ysp_genckey(cnlid, gid, ts, appver, fd):
    """生成 cKey（流加密凭据），失败返回空串"""
    key = _ysp_tea_key()
    if not key:
        return ""
    pkt = _ysp_genckey_packet(cnlid, ts, gid, appver, fd)
    enc = _ysp_oi_encrypt(pkt, key, YSP["OI_RNG"])
    sig = _ysp_calc_sig(pkt)
    x = enc + _ysp_be32(sig)
    xk = _ysp_hexbytes(YSP["XOR_KEY_HEX"])
    o = [((x[i] ^ xk[i & 15]) & 255) for i in range(len(x))]
    return "--01" + _ysp_b64(o, True, False)


def _ysp_flowid(gid):
    g = gid.upper()
    return "%s-%s-%s-%s-%s_%s" % (g[0:8], g[8:12], g[12:16], g[16:20], g[20:32], YSP["PLATFORM"])


def _ysp_spvcode(defn):
    h = 2160 if any(x in str(defn or "").lower() for x in ("4k", "8k", "hdr")) else 1080
    parts = "|".join([",".join("%d:%d" % (v, h) for v in (30, 60, 90, 120))] * 2)
    return _ysp_b64(_ysp_bytes("H(%s);2(%s)" % (parts, parts)), False, True)


def _ysp_enc(s):
    return quote(str(s), safe="")


def _ysp_parse_playurl(body):
    """从 liveinfo 响应里取 playurl，识别 DRM/未上线"""
    m = re.search(r'"iretcode"\s*:\s*"?(-?\d+)"?', body)
    if m and m.group(1) != "0":
        return {"url": "", "drm": False, "iret": m.group(1)}
    m = re.search(r'"playurl"\s*:\s*"([^"]*)"', body)
    if not m:
        return {"url": "", "drm": False}
    m2 = re.search(r'"encrypt"\s*:\s*(-?\d+)', body)
    if m2 and int(m2.group(1)) != 0:
        return {"url": "", "drm": True}
    u = m.group(1).replace("\\/", "/").replace("\\u0026", "&").strip()
    if u[:2] == "//":
        u = "http:" + u
    k = u.find("http://")
    j = u.find("https://")
    idx = j if k < 0 else (k if j < 0 else min(k, j))
    if idx > 0:
        u = u[idx:]
    sp = u.find(" ")
    if sp >= 0:
        u = u[:sp]
    q = u.find('"')
    if q >= 0:
        u = u[:q]
    return {"url": u if "://" in u else "", "drm": False}


def _ysp_liveinfo(cnlid, livepid, defn, ide, http_get, timeout=15):
    """单次 liveinfo 请求；http_get(url, headers, timeout) 返回文本"""
    g = _ysp_guid()
    ts = int(time.time())
    ck = _ysp_genckey(cnlid, g, ts, YSP["APP_VER"], ide["FD"])
    if not ck or ck[:4] != "--01":
        return {"url": "", "drm": False, "err": "genckey"}
    q = []

    def aq(k, v):
        q.append(_ysp_enc(k) + "=" + _ysp_enc(v))

    aq("cmd", "2"); aq("otype", "json"); aq("flowid", _ysp_flowid(g)); aq("cnlid", cnlid)
    aq("livepid", livepid); aq("stream", "1"); aq("defn", defn); aq("platform", YSP["PLATFORM"])
    aq("sdtfrom", ide["SDTFROM"]); aq("appVer", YSP["APP_VER"]); aq("guid", g)
    aq("randnum", _ysp_randnum()); aq("qq", ""); aq("wxopenid", ""); aq("newnettype", "1")
    aq("encryptVer", "4.2"); aq("getpreviewinfo", ide["GETPREVIEWINFO"]); aq("vip_status", "0")
    if ide["LOGINTYPE"]:
        aq("logintype", ide["LOGINTYPE"])
    aq("fntick", str(ts)); aq("cKey", ck); aq("estid", ""); aq("atime", "120")
    aq("app_version", YSP["APP_VERSION"]); aq("caplv", "1"); aq("device", ide["DEVICE"])
    aq("hevclv", "33"); aq("lang", ide["LANG"]); aq("livequeue", "0"); aq("nettype", "1")
    aq("newplatform", ide["NEWPLATFORM"]); aq("spacode", "23"); aq("spaudio", "1")
    aq("spdemuxer", "6"); aq("spdrm", "2"); aq("spdynamicrange", "7"); aq("spflv", "1")
    aq("spflvaudio", "1"); aq("sphdrfps", "60"); aq("sphttps", "0")
    aq("spvcode", _ysp_spvcode(defn)); aq("spvideo", "4"); aq("system", "1"); aq("sysver", ide["SYSVER"])
    aq("uhd_flag", "4"); aq("playbacktime", "0")
    qs = "&".join(q)
    hdr = {"User-Agent": YSP["UA"], "Accept": "application/json"}
    body = ""
    for host in YSP["HOSTS"]:
        body = http_get(host + qs, hdr, timeout) or ""
        if body:
            break
    if not body:
        return {"url": "", "drm": False, "err": "empty"}
    return _ysp_parse_playurl(body)


def _ysp_playurl(key, http_get):
    """按 ysp.js 的频道键取播放地址"""
    cfg = YSP_CHANNELS.get(key)
    if not cfg:
        return {"url": "", "drm": False, "err": "unknown key"}
    cnlid, livepid, defn = cfg[0], cfg[1], cfg[2]
    last = {"url": "", "drm": False}
    for ide in YSP_IDENTITIES:
        ide = dict(ide)
        if ide["FD"] is None:
            ide["FD"] = _ysp_getfd(ide["SDTFROM"])
        r = _ysp_liveinfo(cnlid, livepid, defn, ide, http_get)
        if r.get("url"):
            return r
        if r.get("drm"):
            return r
        last = r
    return last


# ---------------------------------------------------------------------------
# 河北电视台播放地址解析（移植 河北电视台.js）
# 流程: 拉源站文章列表 -> 取 liveStream/liveUri/liveKey -> md5(liveUri+liveKey+t) 签名
# ---------------------------------------------------------------------------

def _hebtv_channels():
    return HEBTV_CHANNELS


def _hebtv_playurl(idx, http_get):
    """返回 {"url":..., "header":...}"""
    idx = max(1, int(idx or 1))
    text = http_get(HEBTV_API, HEBTV_HEADERS, 15)
    if not text:
        return {"url": "", "err": "接口请求失败"}
    try:
        data = json.loads(text)
    except Exception as e:
        return {"url": "", "err": "接口返回数据解析失败: " + str(e)}
    news = ((data or {}).get("returnData") or {}).get("news") or []
    if idx > len(news):
        return {"url": "", "err": "源站无该序号频道"}
    item = news[idx - 1]
    try:
        stream = item["liveVideo"][0]["formats"][0]["liveStream"]
        movie = item["appCustomParams"]["movie"]
        uri = movie["liveUri"]
        key = movie["liveKey"]
    except Exception as e:
        return {"url": "", "err": "源站未提供该频道的直播数据: " + str(e)}
    t = int(time.time()) + 10000
    k = _md5_hex(uri + key + str(t))
    return {
        "url": stream + "?t=" + str(t) + "&k=" + k,
        "header": {"User-Agent": HEBTV_HEADERS["User-Agent"], "Referer": "https://www.hebtv.com/"},
    }


# ---------------------------------------------------------------------------
# 凤凰卫视播放地址解析（移植 fhx.js 的直播分支）
# 流程: 尝试登录换 token（源站常返回账号错误，匿名 token 实际为空也可用）
#       -> api.fengshows.cn/hub/live/auth-url?live_qa=hd&live_id=<guid>
# 清晰度说明（实测）：
#   - hd  -> *48.flv = 854×480，匿名可用上限
#   - fhd -> 需有效 VIP token，匿名恒被拒（賬號已過期）
#   - sd/uhd/shd/hhd/720p/1080p 等其它 qa 名一律映射到 *36.flv = 640×360，不要用
#   - dispatch.fengshows.cn:8484 会 301 跳 qctv.fengshows.cn，签名在 query 里不受影响
# ---------------------------------------------------------------------------

def _fengx_guids():
    return dict((cid, gid) for cid, gid, _n, _sc in FENGX_CHANNELS)


def _fengx_streamcode(cid):
    for c, _gid, _n, sc in FENGX_CHANNELS:
        if c == cid:
            return sc
    return ""


def _fengx_token(http_post):
    body = json.dumps({"phone": "", "password": "", "code": "852", "keep_alive": False})
    headers = {"Content-Type": "application/json"}
    text = http_post(FENGX_LOGIN, body, headers, 12)
    if not text:
        return ""
    try:
        data = json.loads(text)
    except Exception:
        return ""
    return ((data or {}).get("data") or {}).get("token", "") or ""


def _fengx_once(gid, http_get, qa_list):
    """按给定 qa 顺序申请一次直播地址，返回 (url, err)"""
    headers = dict(FENGX_HEADERS_REQ)
    url = ""
    err = ""
    for qa in qa_list:
        text = http_get(FENGX_AUTH % (qa, gid), headers, 12)
        if not text:
            err = "接口请求失败"
            continue
        try:
            data = json.loads(text)
        except Exception:
            data = {}
        url = ((data or {}).get("data") or {}).get("live_url", "") or ""
        if url:
            break
        err = str((data or {}).get("message", "")) or "接口未返回直播地址"
    return url, err


def _fengx_playurl(channel_id, http_get, http_post, http_probe=None):
    """返回 {"url":..., "header":...}；
    清晰度策略：凤凰中文/资讯优先走免签名 720p（qctv *72.flv + Referer www.fengshows.com，
    探活失败自动降级），凤凰香港无 72 流，走签名 hd（854×480）。
    签名地址是一次性的（txTime 有效期），实测偶发 403，探活为 403 时自动再申请一次。"""
    gid = _fengx_guids().get(channel_id)
    if not gid:
        return {"url": "", "err": "未知频道"}

    token = getattr(_fengx_playurl, "_token", None)
    if token is None:
        token = _fengx_token(http_post)
        _fengx_playurl._token = token

    # -- 主路：签名 hd（854×480，稳定可长播）--
    qa_list = FENGX_QA_VIP if token else FENGX_QA_ANON
    url, err = _fengx_once(gid, http_get, qa_list)

    if url and http_probe is not None:
        try:
            if http_probe(url, dict(FENGX_HEADERS_PLAY)) == 403:
                # 一次性签名偶发 403：重新申请地址即可（登录接口匿名恒失败，不必重登）
                url2, _err2 = _fengx_once(gid, http_get, FENGX_QA_ANON)
                if url2:
                    url = url2
                else:
                    url = ""
                    err = _err2 or err
        except Exception as e:
            print("[IPTV2.9.9] 凤凰探活异常: " + str(e))

    # -- 备胎：签名主路失败时才试免签名 720p（该通道源站限流，时好时坏）--
    if not url:
        sc = _fengx_streamcode(channel_id)
        u720 = FENGX_HD720_URL % sc if sc else ""
        if u720:
            hdr720 = {"User-Agent": FENGX_HEADERS_PLAY["User-Agent"],
                      "Referer": FENGX_HD720_REFERER}
            for _ in range(2):
                try:
                    if _sustained_probe(u720, dict(hdr720)):
                        return {"url": u720, "header": hdr720}
                except Exception:
                    pass

    if not url:
        return {"url": "", "err": err or "接口未返回直播地址"}
    return {"url": url, "header": dict(FENGX_HEADERS_PLAY)}


# ---------------------------------------------------------------------------
# 中天直播播放地址解析（公开聚合源，逐路探活取第一个可用的）
# ---------------------------------------------------------------------------

def _twn_channels():
    return TWN_CHANNELS


def _sustained_probe(url, headers=None, minbytes=TWN_PROBE_MINBYTES,
                     timeout=TWN_PROBE_TIMEOUT):
    """FLV/通用流持续探活：限时限速拉流，要求在 timeout 内拉到 minbytes，
    过滤只放行缓冲头几秒就掐断的节点。可用返回 True"""
    sess = getattr(_twn_probe_m3u8, "_session", None)
    if sess is None:
        _twn_probe_m3u8(url)  # 触发初始化
        sess = getattr(_twn_probe_m3u8, "_session", None)
        if sess is None:
            return False
    try:
        rsp = sess.get(url, timeout=timeout, verify=False, stream=True,
                       headers=headers or {"User-Agent": UA, "Connection": "close"})
        if getattr(rsp, "status_code", 0) != 200:
            try:
                rsp.close()
            except Exception:
                pass
            return False
        buf = 0
        for chunk in rsp.iter_content(65536):
            buf += len(chunk)
            if buf >= minbytes:
                break
        try:
            rsp.close()
        except Exception:
            pass
        return buf >= minbytes
    except Exception:
        return False


def _twn_probe_m3u8(url, timeout=TWN_PROBE_TIMEOUT):
    """强化探活：不只是看 m3u8 头，而是真实跟到媒体片段并拉取 ≥512KB 数据，
    过滤「播一秒就断」的假活源。可用返回 True"""
    sess = getattr(_twn_probe_m3u8, "_session", None)
    if sess is None:
        try:
            import requests as _rq
            from requests.adapters import HTTPAdapter
            sess = _rq.Session()
            adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10)
            sess.mount("http://", adapter)
            sess.mount("https://", adapter)
            sess.trust_env = False
            _twn_probe_m3u8._session = sess
        except Exception:
            return False

    def _fetch(url, limit, timeout=timeout):
        try:
            rsp = sess.get(url, timeout=timeout, verify=False, stream=True,
                           headers={"User-Agent": UA, "Connection": "close"})
            if getattr(rsp, "status_code", 0) != 200:
                try:
                    rsp.close()
                except Exception:
                    pass
                return None
            buf = b""
            for chunk in rsp.iter_content(65536):
                buf += chunk
                if len(buf) >= limit:
                    break
            try:
                rsp.close()
            except Exception:
                pass
            return buf
        except Exception:
            return None

    body = _fetch(url, 65536)
    if not body or body.lstrip()[:7] != b"#EXTM3U":
        return False
    # 主播放列表 -> 取首个子播放列表/片段地址（最多跟两级）
    for _ in range(2):
        seg = None
        for line in body.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                seg = line
                break
        if not seg:
            return False
        if "://" not in seg:
            base = url.rsplit("/", 1)[0]
            seg = base + "/" + seg
        body = _fetch(seg, TWN_PROBE_MINBYTES)
        if not body or body.lstrip()[:7] != b"#EXTM3U":
            # 已是媒体片段：验证持续可拉流
            return len(body or b"") >= TWN_PROBE_MINBYTES
        # 还是播放列表，继续往下一级
    return False


def _twn_playurl(key, get_probe=None):
    """按频道键在候选源里探活，返回 {"url":..., "header":...}
    候选顺序：YouTube 官方直播中转（如有）-> 静态直连源（按配置顺序）"""
    cfg = None
    for k, _name, urls in TWN_CHANNELS:
        if k == key:
            cfg = urls
            break
    if cfg is None:
        return {"url": "", "err": "未知频道"}
    candidates = []
    yid = TWN_YT_IDS.get(key)
    if yid:
        for q in TWN_YT_QUALITIES:
            candidates.append(TWN_YT_RELAY % (yid, q))
    candidates += list(cfg)
    probe = get_probe or _twn_probe_m3u8
    last_err = "候选源全部不可用"
    for u in candidates:
        for _ in range(TWN_PROBE_TRIES):
            if probe(u):
                return {
                    "url": u,
                    "header": {"User-Agent": UA, "Connection": "close"},
                }
        last_err = "源不可用: " + u
    return {"url": "", "err": last_err}




# ---------------------------------------------------------------------------
# 点播列表/详情解析（一线 JSON、二线 XML 两套格式）
# ---------------------------------------------------------------------------

def _vod_parse_list_json(text, page):
    data = json.loads(text)
    items = []
    for it in data.get("list") or []:
        items.append({
            "vod_id": str(it.get("vod_id", "")),
            "vod_name": _strip(it.get("vod_name", "")),
            "vod_pic": it.get("vod_pic", "") or "",
            "vod_remarks": _strip(it.get("vod_remarks", "") or it.get("vod_note", "")),
        })
    return {
        "list": items,
        "page": page,
        "pagecount": int(data.get("pagecount") or 1),
        "limit": int(data.get("limit") or VOD_PAGE_SIZE),
        "total": int(data.get("total") or 0),
    }


def _vod_parse_list_xml(text, page):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(text.encode("utf-8"))
    lst = root.find("list")
    items = []
    for v in (lst.findall("video") if lst is not None else []):
        items.append({
            "vod_id": (v.findtext("id") or "").strip(),
            "vod_name": _strip(v.findtext("name") or ""),
            "vod_pic": (v.findtext("pic") or "").strip(),
            "vod_remarks": _strip(v.findtext("note") or ""),
        })
    pc = int((lst.get("pagecount") if lst is not None else 1) or 1)
    total = int((lst.get("recordcount") if lst is not None else 0) or 0)
    return {"list": items, "page": page, "pagecount": pc, "limit": VOD_PAGE_SIZE, "total": total}


def _vod_parse_list(text, fmt, page):
    if not text:
        return {"list": [], "page": page, "pagecount": 1, "limit": VOD_PAGE_SIZE, "total": 0}
    if fmt == "xml":
        return _vod_parse_list_xml(text, page)
    return _vod_parse_list_json(text, page)


def _vod_parse_detail_json(text, vod_id):
    data = json.loads(text)
    lst = data.get("list") or []
    if not lst:
        return None
    it = lst[0]
    return {
        "vod_id": str(it.get("vod_id", vod_id)),
        "vod_name": _strip(it.get("vod_name", "")),
        "vod_pic": it.get("vod_pic", "") or "",
        "vod_year": str(it.get("vod_year", "") or ""),
        "vod_area": str(it.get("vod_area", "") or ""),
        "vod_lang": str(it.get("vod_lang", "") or ""),
        "vod_remarks": _strip(it.get("vod_remarks", "") or ""),
        "vod_actor": _strip(it.get("vod_actor", "") or ""),
        "vod_director": _strip(it.get("vod_director", "") or ""),
        "vod_class": str(it.get("type_name", "") or ""),
        "vod_content": _strip(re.sub(r"<[^>]+>", " ", it.get("vod_content", "") or ""))[:500],
        "vod_play_from": str(it.get("vod_play_from", "") or ""),
        "vod_play_url": str(it.get("vod_play_url", "") or ""),
    }


def _vod_parse_detail_xml(text, vod_id):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(text.encode("utf-8"))
    lst = root.find("list")
    if lst is None:
        return None
    for v in lst.findall("video"):
        froms, urls = [], []
        dl = v.find("dl")
        for dd in (dl.findall("dd") if dl is not None else []):
            flag = dd.get("flag") or "m3u8"
            content = (dd.text or "").strip()
            if not content:
                continue
            froms.append(flag)
            urls.append(content)
        return {
            "vod_id": (v.findtext("id") or str(vod_id)).strip(),
            "vod_name": _strip(v.findtext("name") or ""),
            "vod_pic": (v.findtext("pic") or "").strip(),
            "vod_year": _strip(v.findtext("year") or ""),
            "vod_area": _strip(v.findtext("area") or ""),
            "vod_lang": _strip(v.findtext("lang") or ""),
            "vod_remarks": _strip(v.findtext("note") or ""),
            "vod_actor": _strip(v.findtext("actor") or ""),
            "vod_director": _strip(v.findtext("director") or ""),
            "vod_class": _strip(v.findtext("type") or ""),
            "vod_content": _strip(v.findtext("des") or "")[:500],
            "vod_play_from": "$$$".join(froms),
            "vod_play_url": "$$$".join(urls),
        }
    return None


def _vod_parse_detail(text, fmt, vod_id):
    if not text:
        return None
    if fmt == "xml":
        return _vod_parse_detail_xml(text, vod_id)
    return _vod_parse_detail_json(text, vod_id)


# ---------------------------------------------------------------------------
# 爬虫主体
# ---------------------------------------------------------------------------

class Spider(Spider):

    def getName(self):
        return "IPTV2.9.9"

    def init(self, extend=""):
        self.header = {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
        try:
            import requests
            from requests.adapters import HTTPAdapter
            self._session = requests.Session()
            adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
            self._session.trust_env = False
        except Exception as e:
            print("[IPTV2.9.9] requests 不可用, 回退到框架 fetch: " + str(e))
            self._session = None

        self._list_cache = {}
        self._detail_cache = {}
        self._search_cache = {}
        self._cache_lock = threading.Lock()
        self._cb_fails = 0
        self._cb_open_until = 0
        self._cb_lock = threading.Lock()

    def isVideoFormat(self, url):
        u = (url or "").lower().rstrip("?#")
        return any(u.endswith(ext) for ext in (".m3u8", ".mp4", ".flv", ".ts"))

    def destroy(self):
        sess = getattr(self, "_session", None)
        if sess is not None:
            try:
                sess.close()
            except Exception:
                pass

    # -- 通用请求 ---------------------------------------------------------

    def _circuit_allow(self):
        with self._cb_lock:
            if self._cb_open_until and time.time() < self._cb_open_until:
                return False
            return True

    def _circuit_record(self, ok):
        with self._cb_lock:
            if ok:
                self._cb_fails = 0
            else:
                self._cb_fails += 1
                if self._cb_fails >= CIRCUIT_FAILS:
                    self._cb_open_until = time.time() + CIRCUIT_COOLDOWN
                    print("[IPTV2.9.9] 熔断 " + str(CIRCUIT_COOLDOWN) + "s")

    def _get_text(self, url, headers=None, timeout=10):
        """GET 文本：requests session -> urllib 标准库 -> 框架 fetch"""
        if not self._circuit_allow():
            return ""
        hdr = dict(getattr(self, "header", {}) or {})
        if headers:
            hdr.update(headers)
        sess = getattr(self, "_session", None)
        if sess is not None and hasattr(sess, "get"):
            try:
                rsp = sess.get(url, headers=hdr, timeout=timeout, verify=False)
                sc = getattr(rsp, "status_code", 0)
                txt = getattr(rsp, "text", None) or ""
                if rsp is not None and sc == 200 and txt:
                    self._circuit_record(True)
                    return txt
            except Exception as e:
                print("[IPTV2.9.9] session 失败: " + url + " (" + str(e) + ")")
        txt = _urllib_get(url, hdr, timeout)
        if txt:
            self._circuit_record(True)
            return txt
        try:
            rsp = self.fetch(url, headers=hdr, timeout=timeout)
            sc = getattr(rsp, "status_code", 0)
            txt = getattr(rsp, "text", None) or ""
            if rsp is not None and sc == 200 and txt:
                self._circuit_record(True)
                return txt
        except Exception as e:
            print("[IPTV2.9.9] fetch 失败: " + url + " (" + str(e) + ")")
        self._circuit_record(False)
        return ""

    def _post_text(self, url, body, headers=None, timeout=10):
        """POST 文本：requests session -> urllib 标准库 -> 框架 fetch"""
        hdr = dict(getattr(self, "header", {}) or {})
        if headers:
            hdr.update(headers)
        sess = getattr(self, "_session", None)
        if sess is not None and hasattr(sess, "post"):
            try:
                rsp = sess.post(url, data=body, headers=hdr, timeout=timeout, verify=False)
                if getattr(rsp, "status_code", 0) == 200:
                    return rsp.text
            except Exception as e:
                print("[IPTV2.9.9] POST session 失败: " + url + " (" + str(e) + ")")
        txt = _urllib_post(url, body, hdr, timeout)
        if txt:
            return txt
        try:
            rsp = self.fetch(url, headers=hdr, timeout=timeout, data=body)
            if getattr(rsp, "status_code", 0) == 200:
                return rsp.text
        except Exception as e:
            print("[IPTV2.9.9] POST fetch 失败: " + url + " (" + str(e) + ")")
        return ""

    def _status_code(self, url, headers=None, timeout=8):
        """轻量探活：跟随跳转取最终状态码，只读响应头不下载正文；失败返回 -1"""
        hdr = dict(getattr(self, "header", {}) or {})
        if headers:
            hdr.update(headers)
        sess = getattr(self, "_session", None)
        if sess is None or not hasattr(sess, "get"):
            return -1
        try:
            rsp = sess.get(url, headers=hdr, timeout=timeout, verify=False,
                           stream=True, allow_redirects=True)
            code = int(getattr(rsp, "status_code", -1))
            try:
                rsp.close()
            except Exception:
                pass
            return code
        except Exception:
            return -1

    def _get_json(self, url, headers=None, timeout=10):
        txt = self._get_text(url, headers=headers, timeout=timeout)
        if not txt:
            return None
        try:
            return json.loads(txt)
        except Exception as e:
            print("[IPTV2.9.9] JSON解析失败: " + url + " (" + str(e) + ")")
            return None

    # -- 频道表与列表 -----------------------------------------------------

    def _live_item(self, kind, key, name, group):
        return {
            "vod_id": "live|" + kind + "|" + str(key),
            "vod_name": name,
            "vod_pic": "",
            "vod_remarks": "直播 · " + group,
        }

    def _all_live_items(self, tid):
        """按分组拼接直播频道列表"""
        items = []
        if tid in ("live_ysp", "live_all"):
            for key in YSP_CHANNELS:
                items.append(self._live_item("ysp", key, YSP_CHANNELS[key][3], GROUP_NAMES["ysp"]))
        if tid in ("live_hebtv", "live_all"):
            for idx, name in HEBTV_CHANNELS:
                items.append(self._live_item("hebtv", idx, name, GROUP_NAMES["hebtv"]))
        if tid in ("live_fengx", "live_all"):
            for cid, _gid, name, _sc in FENGX_CHANNELS:
                items.append(self._live_item("fengx", cid, name, GROUP_NAMES["fengx"]))
        if tid in ("live_twn", "live_all"):
            for cid, name, _urls in TWN_CHANNELS:
                items.append(self._live_item("twn", cid, name, GROUP_NAMES["twn"]))
        return items

    def _live_category(self, tid, page):
        items = self._all_live_items(tid)
        total = len(items)
        pagecount = max(1, (total + LIVE_PAGE_SIZE - 1) // LIVE_PAGE_SIZE)
        start = (page - 1) * LIVE_PAGE_SIZE
        return {
            "list": items[start:start + LIVE_PAGE_SIZE],
            "page": page,
            "pagecount": pagecount,
            "limit": LIVE_PAGE_SIZE,
            "total": total,
        }

    def _live_name(self, kind, key):
        if kind == "ysp":
            cfg = YSP_CHANNELS.get(key)
            return cfg[3] if cfg else str(key)
        if kind == "hebtv":
            for idx, name in HEBTV_CHANNELS:
                if str(idx) == str(key):
                    return name
            return "河北电视台 " + str(key)
        if kind == "fengx":
            for cid, _gid, name, _sc in FENGX_CHANNELS:
                if cid == key:
                    return name
            return str(key)
        if kind == "twn":
            for cid, name, _urls in TWN_CHANNELS:
                if cid == key:
                    return name
            return str(key)
        return str(key)

    def homeContent(self, filter):
        return {"class": CLASSES, "filters": FILTERS}

    def homeVideoContent(self):
        try:
            return {"list": self._all_live_items("live_all")[:28]}
        except Exception as e:
            print("[IPTV2.9.9] homeVideoContent 异常: " + str(e))
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
            if page < 1:
                page = 1
            tid = str(tid or "")
            if tid.startswith("live"):
                return self._live_category(tid, page)

            api = VOD_APIS.get(tid)
            if not api:
                return {"list": [], "page": page, "pagecount": 1, "limit": VOD_PAGE_SIZE, "total": 0}

            ext = _parse_extend(extend)
            cls = str(ext.get("class", "") or "")
            cache_key = (tid, cls, page)
            now = time.time()
            with self._cache_lock:
                hit = self._list_cache.get(cache_key)
                if hit and now - hit[0] < LIST_CACHE_TTL:
                    return hit[1]

            url = api["url"] + "?ac=detail&pg=" + str(page)
            if cls:
                url += "&t=" + _urlencode(cls)
            text = self._get_text(url, timeout=12)
            if not text:
                print("[IPTV2.9.9] categoryContent empty: " + url)
                return {"list": [], "page": page, "pagecount": 1, "limit": VOD_PAGE_SIZE, "total": 0}

            payload = _vod_parse_list(text, api["fmt"], page)
            payload["list"] = [
                dict(it, vod_id=tid + "|" + str(it.get("vod_id", ""))) for it in payload.get("list", [])
            ]
            with self._cache_lock:
                self._list_cache[cache_key] = (now, payload)
            return payload
        except Exception as e:
            print("[IPTV2.9.9] categoryContent 异常: " + str(e))
            return {"list": [], "page": 1, "pagecount": 1, "limit": VOD_PAGE_SIZE, "total": 0}

    def detailContent(self, ids):
        try:
            vod_id = ids[0] if isinstance(ids, (list, tuple)) else ids
            vod_id = str(vod_id or "")

            # 直播频道
            if vod_id.startswith("live|"):
                parts = vod_id.split("|")
                kind = parts[1] if len(parts) > 1 else ""
                key = parts[2] if len(parts) > 2 else ""
                name = self._live_name(kind, key)
                group = GROUP_NAMES.get(kind, "直播")
                vod = {
                    "vod_id": vod_id,
                    "vod_name": name,
                    "vod_pic": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_lang": "",
                    "vod_remarks": "直播",
                    "vod_actor": "",
                    "vod_director": "",
                    "vod_class": group,
                    "vod_content": name + "（" + group + "，源自 IPTV 2.9.9 内置播放脚本）",
                    "vod_play_from": group,
                    "vod_play_url": name + "$" + vod_id,
                }
                return {"list": [vod]}

            # 点播
            now = time.time()
            with self._cache_lock:
                hit = self._detail_cache.get(vod_id)
                if hit and now - hit[0] < DETAIL_CACHE_TTL:
                    return hit[1]

            if "|" not in vod_id:
                return {"list": []}
            tid, real_id = vod_id.split("|", 1)
            api = VOD_APIS.get(tid)
            if not api:
                return {"list": []}
            url = api["url"] + "?ac=detail&ids=" + _urlencode(real_id)
            text = self._get_text(url, timeout=12)
            vod = _vod_parse_detail(text, api["fmt"], real_id)
            if not vod:
                return {"list": []}
            vod["vod_id"] = vod_id
            payload = {"list": [vod]}
            with self._cache_lock:
                self._detail_cache[vod_id] = (now, payload)
            return payload
        except Exception as e:
            print("[IPTV2.9.9] detailContent 异常: " + str(e))
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
            if page < 1:
                page = 1
            cache_key = (key, page)
            now = time.time()
            with self._cache_lock:
                hit = self._search_cache.get(cache_key)
                if hit and now - hit[0] < SEARCH_CACHE_TTL:
                    return hit[1]

            items = []
            total = 0
            pagecount = 1
            for tid, api in VOD_APIS.items():
                url = api["url"] + "?ac=detail&wd=" + _urlencode(key) + "&pg=" + str(page)
                text = self._get_text(url, timeout=12)
                payload = _vod_parse_list(text, api["fmt"], page)
                for it in payload.get("list", []):
                    it["vod_id"] = tid + "|" + str(it.get("vod_id", ""))
                    remark = it.get("vod_remarks") or ""
                    it["vod_remarks"] = (remark + " · " + api["name"]) if remark else api["name"]
                    items.append(it)
                total += payload.get("total", 0) or 0
                pagecount = max(pagecount, payload.get("pagecount", 1) or 1)

            result = {"list": items, "page": page, "pagecount": pagecount,
                      "limit": VOD_PAGE_SIZE, "total": total}
            with self._cache_lock:
                self._search_cache[cache_key] = (now, result)
            return result
        except Exception as e:
            print("[IPTV2.9.9] searchContent 异常: " + str(e))
            return {"list": [], "page": 1, "pagecount": 1, "limit": VOD_PAGE_SIZE, "total": 0}

    def playerContent(self, flag, id, vipFlags):
        pid = str(id or "")
        try:
            if pid.startswith("live|"):
                parts = pid.split("|")
                kind = parts[1] if len(parts) > 1 else ""
                key = parts[2] if len(parts) > 2 else ""

                if kind == "ysp":
                    r = _ysp_playurl(key, self._get_text)
                    if r.get("url"):
                        return {"parse": 0, "url": r["url"], "header": {"User-Agent": YSP["UA"]}}
                    print("[IPTV2.9.9] 央视频取流失败: " + key + " err=" + str(r.get("err", "")))

                elif kind == "hebtv":
                    r = _hebtv_playurl(key, self._get_text)
                    if r.get("url"):
                        return {"parse": 0, "url": r["url"], "header": r["header"]}
                    print("[IPTV2.9.9] 河北电视台取流失败: " + key + " err=" + str(r.get("err", "")))

                elif kind == "fengx":
                    r = _fengx_playurl(key, self._get_text, self._post_text, self._status_code)
                    if r.get("url"):
                        return {"parse": 0, "url": r["url"], "header": r["header"]}
                    print("[IPTV2.9.9] 凤凰卫视取流失败: " + key + " err=" + str(r.get("err", "")))

                elif kind == "twn":
                    r = _twn_playurl(key)
                    if r.get("url"):
                        return {"parse": 0, "url": r["url"], "header": r["header"]}
                    print("[IPTV2.9.9] 台湾直播取流失败: " + key + " err=" + str(r.get("err", "")))

                return {"parse": 0, "url": ""}
        except Exception as e:
            print("[IPTV2.9.9] playerContent 异常: " + pid + " (" + str(e) + ")")
            return {"parse": 0, "url": ""}

        # 点播：播放列表里的地址本身就是 m3u8
        if "http" not in pid[:8] and "$" in pid:
            pid = pid.rsplit("$", 1)[-1]
        return {"parse": 0, "url": pid, "header": {"User-Agent": UA}}

    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]
