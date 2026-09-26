# coding: utf-8
import sys
import json
import requests
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    HOST = 'https://cn.bongacams.com'
    
    # 默认 Headers 参数
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Referer': HOST
    }

    def getName(self):
        return "BongaCams"

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        result = {}
        
        # 分类定义
        classes = [
            {"type_name": "新直播", "type_id": "new-models"},
            {"type_name": "所有", "type_id": ""},
            {"type_name": "女性", "type_id": "female"},
            {"type_name": "夫妻", "type_id": "couples"},
            {"type_name": "男性", "type_id": "male"},
            {"type_name": "变性人", "type_id": "trans"}
        ]
        
        # 筛选配置数据
        filters = {
            "": [
                {"key": "cateId", "name": "分类", "value": [{"v": "", "n": "全部"}, {"v": "玩具", "n": "玩具"}, {"v": "物神", "n": "物神"}, {"v": "褐发女郎", "n": "褐色女郎"}, {"v": "光头的阴户", "n": "剃光的阴户"}, {"v": "喷", "n": "潮吹"}, {"v": "肛交", "n": "肛交"}, {"v": "拉丁裔", "n": "拉丁裔"}, {"v": "大屁股", "n": "大屁股"}, {"v": "主妇", "n": "主妇"}, {"v": "中等山雀", "n": "中等乳房"}, {"v": "辣妹", "n": "辣妹"}, {"v": "白人女孩", "n": "白人女孩"}, {"v": "大学女生", "n": "大学生"}, {"v": "青少年18", "n": "青少年+18"}, {"v": "大山雀", "n": "波霸"}, {"v": "成熟", "n": "熟女"}, {"v": "捆绑", "n": "捆绑"}, {"v": "曲线美", "n": "曲线美"}, {"v": "小山雀", "n": "平胸女"}, {"v": "金发", "n": "金发女"}, {"v": "红发", "n": "红发"}, {"v": "丰满阴毛", "n": "阴毛茂密"}, {"v": "黑人", "n": "黑人"}, {"v": "bbw", "n": "BBW"}, {"v": "娇小型", "n": "娇小型"}, {"v": "波霸", "n": "波霸"}, {"v": "肌肉", "n": "肌肉"}, {"v": "亚裔", "n": "亚洲人"}, {"v": "大妈", "n": "大妈"}, {"v": "阿拉伯", "n": "阿拉伯"}, {"v": "女同", "n": "女同"}, {"v": "吸烟", "n": "吸烟"}, {"v": "印度", "n": "印度"}, {"v": "孕妇", "n": "孕妇"}, {"v": "情色明星", "n": "情色明星"}, {"v": "群交", "n": "群交"}]},
                {"key": "by", "name": "排序", "value": [{"v": "camscore", "n": "视频分数"}, {"v": "popular", "n": "最受欢迎"}, {"v": "logged", "n": "刚刚上线"}, {"v": "new", "n": "新模特"}, {"v": "lovers", "n": "爱人"}]}
            ],
            "male": [
                {"key": "cateId", "name": "分类", "value": [{"v": "male", "n": "全部"}, {"v": "male/双性", "n": "双性"}, {"v": "male/肛交", "n": "肛交"}, {"v": "male/大阴经", "n": "大阴茎"}, {"v": "male/肌肉", "n": "肌肉"}, {"v": "male/大学", "n": "大学"}, {"v": "male/异性", "n": "异性"}, {"v": "male/男同", "n": "男同"}, {"v": "male/伴侣", "n": "夫妻"}, {"v": "male/小熊", "n": "小熊"}]},
                {"key": "by", "name": "排序", "value": [{"v": "camscore", "n": "视频分数"}, {"v": "popular", "n": "最受欢迎"}, {"v": "logged", "n": "刚刚上线"}, {"v": "new", "n": "新模特"}, {"v": "lovers", "n": "爱人"}]}
            ],
            "trans": [
                {"key": "cateId", "name": "分类", "value": [{"v": "trans", "n": "全部"}, {"v": "trans/肛交", "n": "肛交"}, {"v": "trans/玩具", "n": "玩具"}, {"v": "trans/拉丁裔", "n": "拉丁裔"}, {"v": "trans/褐发女郎", "n": "褐色女郎"}, {"v": "trans/小山雀", "n": "平胸女"}, {"v": "trans/年轻人18", "n": "年轻人18+"}, {"v": "trans/大公鸡", "n": "大鸡鸡"}, {"v": "trans/大屁股", "n": "大屁股"}, {"v": "trans/金发", "n": "金发女"}, {"v": "trans/亚裔", "n": "亚洲人"}, {"v": "trans/红发", "n": "红发"}, {"v": "trans/大山雀", "n": "波霸"}, {"v": "trans/成熟", "n": "熟女"}, {"v": "trans/人妖相交", "n": "人妖相交"}]},
                {"key": "by", "name": "排序", "value": [{"v": "camscore", "n": "视频分数"}, {"v": "popular", "n": "最受欢迎"}, {"v": "logged", "n": "刚刚上线"}, {"v": "new", "n": "新模特"}, {"v": "lovers", "n": "爱人"}]}
            ],
            "female": [
                {"key": "by", "name": "排序", "value": [{"v": "camscore", "n": "视频分数"}, {"v": "popular", "n": "最受欢迎"}, {"v": "logged", "n": "刚刚上线"}, {"v": "new", "n": "新模特"}, {"v": "lovers", "n": "爱人"}]}
            ],
            "new-models": [
                {"key": "by", "name": "排序", "value": [{"v": "camscore", "n": "视频分数"}, {"v": "popular", "n": "最受欢迎"}, {"v": "logged", "n": "刚刚上线"}, {"v": "new", "n": "新模特"}, {"v": "lovers", "n": "爱人"}]}
            ]
        }

        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        # 按照规则 "是否开启获取首页数据": "0"，直接返回空
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        
        # 处理筛选逻辑
        sub_cate = extend.get('cateId', '')
        by = extend.get('by', 'camscore')
        
        # 优先使用二级分类的 cateId
        path_id = sub_cate if sub_cate else tid
        
        # 拼接 URL: https://cn.bongacams.com/{cateId}?sorting={by}&page={catePg}
        if path_id:
            url = f"{self.HOST}/{path_id}?sorting={by}&page={pg}"
        else:
            url = f"{self.HOST}/?sorting={by}&page={pg}"

        res = requests.get(url, headers=self.headers, timeout=10)
        doc = pq(res.text)

        videos = []
        # 分类列表数组规则: #mls_container .mls_item
        items = doc('#mls_container .mls_item')
        
        for item in items.items():
            # 标题: .mls_layer a
            title = item.find('.mls_layer a').text()
            # 链接: a -> href
            href = item.find('a').attr('href')
            # 图片: img -> src
            pic = item.find('img').attr('src')

            if not title or not href:
                continue

            # 链接加前缀
            if not href.startswith('http'):
                href = self.HOST + href

            videos.append({
                "vod_id": href,
                "vod_name": title,
                "vod_pic": pic if pic else "",
                "vod_remarks": ""
            })

        result['list'] = videos
        result['page'] = int(pg)
        result['pagecount'] = int(pg) + 1  # 根据流媒体网站特性动态推算下一页
        result['limit'] = len(videos)
        result['total'] = 9999
        return result

    def detailContent(self, array):
        # 原 JSON 中配置 "链接是否直接播放": "1"，将详情页面映射为直接播放入口
        vod_id = array[0]
        
        vod = {
            "vod_id": vod_id,
            "vod_name": "直播间/视频",
            "vod_pic": "",
            "type_name": "Live",
            "vod_year": "",
            "vod_area": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            # 线路与选集直接导向该链接进行播放
            "vod_play_from": "BongaCams",
            "vod_play_url": f"播放列表${vod_id}"
        }
        return {"list": [vod]}

    def searchContent(self, key, quick):
        # 搜索链接: https://cn.bongacams.com/index.php/ajax/suggest?mid=1&wd={wd}
        url = f"{self.HOST}/index.php/ajax/suggest?mid=1&wd={key}"
        
        search_headers = self.headers.copy()
        search_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'

        res = requests.get(url, headers=search_headers, timeout=10)
        videos = []

        try:
            data = res.json()
            # 规则: 搜索列表数组规则 "list"
            item_list = data.get('list', []) if isinstance(data, dict) else []

            for item in item_list:
                # 提取 JSON 中的 name, pic, id
                title = item.get('name', '')
                pic = item.get('pic', '')
                vid = item.get('id', '')

                if not vid:
                    continue

                # 搜索片单链接加前后缀: https://cn.bongacams.com/vodplay/{id}-1-1.html
                play_url = f"{self.HOST}/vodplay/{vid}-1-1.html"

                videos.append({
                    "vod_id": play_url,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": ""
                })
        except Exception as e:
            pass

        return {'list': videos}

    def playerContent(self, flag, id, vipFlags):
        # 规则: "链接是否直接播放": "1", "是否开启手动嗅探": "1"
        # 直接开启 WebView/嗅探 模式提取 .m3u8 直链
        result = {
            "parse": "1",          # 开启手动嗅探/解析
            "playUrl": "",
            "url": id,             # 目标网页 URL
            "header": json.dumps(self.headers)
        }
        return result

    def localProxy(self, param):
        pass
