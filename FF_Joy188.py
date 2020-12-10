from bs4 import BeautifulSoup
import json, cx_Oracle, requests, hashlib, time, urllib3, time
from fake_useragent import UserAgent

from utils import Logger
from utils.Config import LotteryData, EnvConfig
from utils.Connection import OracleConnection

logger = Logger.create_logger(r"\AutoTest", 'FF_')


class FF_:  # 4.0專案

    def __init__(self):
        self.dev_url = ['dev02', 'dev03', 'fh82dev02', '88hlqpdev02', 'teny2020dev02']
        self.uat_url = ['joy188', 'joy188.195353']
        self.user_agent = {
            'Pc': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
        Chrome/68.0.3440.100 Safari/537.36",
            'Ios': "Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 \
        (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1",
            'Andorid': "Mozilla/5.0 (Linux; Android 5.0; SM-G900P Build/LRX21T) AppleWebKit/537.36 \
        (KHTML, like Gecko) Chrome/70.0.3538.110 Mobile Safari/537.36",
            'Fake': UserAgent(verify_ssl=False).random
        }

        self.param = b'ba359dddc3c5dfd979169d056de72638',  # 固定寫死即可
        self.session = requests.Session()
        self.session.proxies = {"http": "http://127.0.0.1:8888"}
        self.lottery_dict = LotteryData.lottery_dict  # 吃config ,後續只需增加一邊

    def session_post(self, request_url, request_func, postData, header):
        """
        共用 request.post方式 ,url 為動態 請求url ,source預設走PC
        :param request_url:
        :param request_func:
        :param postData:
        :param header:
        :return:
        """
        logger.info(f'session_post: request_url = {request_url}, request_func={request_func}, getData={postData}, header={header}')
        urllib3.disable_warnings()
        response = self.session.post(request_url + request_func, data=postData, headers=header, verify=False)
        logger.info(f'session_post : response = {response.text}')
        return response

    def session_get(self, request_url, request_func, getData, header):
        """
        共用 request.get方法 ,url 為動態 請求url ,source預設走PC
        :param request_url:
        :param request_func:
        :param getData:
        :param header:
        :return:
        """
        logger.info(f'session_get: request_url = {request_url}, request_func={request_func}, getData={getData}, header={header}')
        urllib3.disable_warnings()
        response = self.session.get(request_url + request_func, data=getData, headers=header, verify=False)
        # logger.info(f'session_get : response = {response.text}')
        return response

    def get_conn(self, env):  # 連結數據庫 env 0: dev02 , 1:188 ,2: 生產
        if env == 2:
            username = 'rdquery'
            service_name = 'gamenxsXDB'
        else:
            username = 'firefog'
            service_name = ''
        oracle_ = {'password': ['LF64qad32gfecxPOJ603', 'JKoijh785gfrqaX67854', 'eMxX8B#wktFZ8V'],
                   'ip': ['10.13.22.161', '10.6.1.41', '10.6.1.31'],
                   'sid': ['firefog', 'game', '']}
        conn = cx_Oracle.connect(username, oracle_['password'][env], oracle_['ip'][env] + ':1521/' +
                                 oracle_['sid'][env] + service_name)
        return conn

    def plan_return(self, type_, issue_list):  # 根據 type_ 判斷是不是追號, 生成動態的 動態order
        plan_ = []
        try:
            for i in range(type_):
                plan_.append({"number": 'test', "issueCode": issue_list[i]['issueCode'], "multiple": 1})
            # print(plan_)
            return plan_
        except IndexError as e:
            print(e)

    @staticmethod
    def web_plan_issue(lottery, em_url, header):  # 從頁面  dynamicConfig 皆口去獲得
        """
        取得彩種獎期
        :param lottery: 彩種名稱
        :param em_url: em網域
        :param header: request header
        :return: 回傳['data']['gamenumbers']
        """
        logger.info(f'web_plan_issue: lottery={lottery}, em_url={em_url}, header={header}')
        now_time = int(time.time())
        response = FF_().session_get(em_url, '/gameBet/%s/dynamicConfig?_=%s' % (lottery, now_time), '',
                                     header)  # dynamicConfig 有歷史獎其資訊
        try:
            return response.json()['data']['gamenumbers']
        except KeyError:
            print(response.text)
            return None
        except Exception as e:
            print(e)
            return None

    def submit_json(self, em_url, account, lottery, award_mode, trace_issue_num: int, is_trace_win_stop: bool, envs,
                    header):
        """
        各彩種對應的投注格式, 受pc_submit呼叫
        :param em_url: 投注接口
        :param account: 用戶帳號
        :param lottery: 投注彩種
        :param award_mode: 獎金模式
        :param trace_issue_num: 追號與否
        :param is_trace_win_stop: 追中即停與否
        :param envs: 環境
        :param header: 封包header
        :return: None
        """
        logger.info(f'em_url = {em_url}, account = {account}, lottery = {lottery}, award_mode = {award_mode},'
                    f' trace_issue_num = {trace_issue_num}, is_trace_win_stop = {is_trace_win_stop}, envs = {envs}, header = {header}')
        # issueCode = FF_().select_issue(FF_().get_conn(envs),lottery,type_)[lottery]# 奖期api , 為一個dict ,key為彩種
        issue_code = FF_().web_plan_issue(lottery, em_url, header)  # 追號獎期
        print(f'彩種: {lottery}')
        trace_stop_value = 1 if trace_issue_num > 1 and is_trace_win_stop else -1
        trace_value = 1 if trace_issue_num else 0
        is_trace_win_stop = 1 if is_trace_win_stop else 0
        data_ = None


        """
        自 dynamicConfig 取得當前彩種開放的玩法列表，
        並傳遞至 requestContent_FF，組出 balls 參數，
        投注金額也由 requestContent_FF 提供。
        
        若需判斷元角分模式，則在 requestContent_FF 內添加判斷調整即可。
        """
        from utils.requestContent_FF import get_game_dict
        now_time = int(time.time())
        keys = []
        r = self.session.get(em_url + f'/gameBet/{lottery}/dynamicConfig?_={now_time}', headers=header)
        for games in r.json()["data"]["gamelimit"]:
            for key in games:
                keys.append(key)
        logger.info(f'web_plan_issue: keys = {keys}')
        logger.info(f'submit_json: award_mode = {award_mode}')
        game_dict = get_game_dict(keys, award_mode)

        if trace_issue_num > 1 and issue_code:  # 追號
            issue_list = issue_code[:trace_value]
            order_plan = FF_().plan_return(trace_value, issue_list)  # 生成 order 的投注奖期列表
            len_order = len(order_plan)
            print('追號期數:%s' % len_order)
        else:  # 一般投注
            if issue_code:
                issue_code = issue_code[0]['issueCode']
            else:
                issue_code = 1
            order_plan = [{"number": 'test', "issueCode": issue_code, "multiple": 1}]  # 一般投注
            len_order = 1
        if lottery == 'btcctp':
            data_ = {"gameType": lottery, "isTrace": trace_value, "traceWinStop": is_trace_win_stop,
                     "traceStopValue": trace_stop_value, "balls": [
                    {"id": 1, "ball": "1.01", "type": "chungtienpao.chungtienpao.chungtienpao", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1}], "orders": order_plan,
                     "amount": 1.00 * len_order}
        elif lottery in ['cqssc', 'hljssc', 'xjssc', 'tjssc', 'fhjlssc', 'fhcqc', 'fhxjc', 'hnffc', '360ffc', '3605fc', 'hn5fc']:
            logger.info(f'game_dict = {game_dict}')
            data_ = {"gameType": lottery, "isTrace": trace_value, "traceWinStop": is_trace_win_stop,
                     "traceStopValue": trace_stop_value, "balls": game_dict[0], "orders": order_plan, "amount": game_dict[1] * len_order}
        elif lottery in ['ahk3', 'jsk3']:
            data_ = {"gameType": lottery, "isTrace": trace_value, "traceWinStop": is_trace_win_stop,
                     "traceStopValue": trace_stop_value, "balls": game_dict[0], "orders": order_plan, "amount": game_dict[1] * len_order}
        elif lottery in ['sd115', 'jx115', 'gd115', 'sl115']:
            data_ = {"gameType": lottery, "isTrace": trace_value, "traceWinStop": is_trace_win_stop,
                     "traceStopValue": trace_stop_value, "balls": [
                    {"id": 37, "ball": "03", "type": "quwei.normal.caizhongwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 36, "ball": "4单1双", "type": "quwei.normal.dingdanshuang", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 35, "ball": "[胆02]  01,05,06,08,09,10,11", "type": "xuanba.renxuanbazhongwu.dantuo",
                     "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 34, "ball": "01 03 05 06 08 09 10 11", "type": "xuanba.renxuanbazhongwu.danshi",
                     "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 33, "ball": "01,02,03,05,06,07,08,10", "type": "xuanba.renxuanbazhongwu.fushi",
                     "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 32, "ball": "[胆01]  04,05,08,09,10,11", "type": "xuanqi.renxuanqizhongwu.dantuo",
                     "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 31, "ball": "01 02 04 05 06 10 11", "type": "xuanqi.renxuanqizhongwu.danshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 30, "ball": "02,03,06,08,09,10,11", "type": "xuanqi.renxuanqizhongwu.fushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 29, "ball": "[胆10]  01,03,06,08,09", "type": "xuanliu.renxuanliuzhongwu.dantuo",
                     "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 28, "ball": "01 04 05 07 09 10", "type": "xuanliu.renxuanliuzhongwu.danshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 27, "ball": "01,03,05,06,09,10", "type": "xuanliu.renxuanliuzhongwu.fushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 26, "ball": "[胆10]  01,05,07,11", "type": "xuanwu.renxuanwuzhongwu.dantuo", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 25, "ball": "01 03 06 07 09", "type": "xuanwu.renxuanwuzhongwu.danshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 24, "ball": "03,04,06,09,11", "type": "xuanwu.renxuanwuzhongwu.fushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 23, "ball": "[胆10]  03,08,09", "type": "xuansi.renxuansizhongsi.dantuo", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 22, "ball": "03 07 08 10", "type": "xuansi.renxuansizhongsi.danshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 21, "ball": "02,03,04,06", "type": "xuansi.renxuansizhongsi.fushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 20, "ball": "[胆02]  01,11", "type": "xuansan.renxuansanzhongsan.renxuandantuo",
                     "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 19, "ball": "01 07 08", "type": "xuansan.renxuansanzhongsan.renxuandanshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 18, "ball": "02,05,10", "type": "xuansan.renxuansanzhongsan.renxuanfushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 17, "ball": "[胆02]  06,08", "type": "xuansan.qiansanzuxuan.zuxuandantuo", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 16, "ball": "01 04 09", "type": "xuansan.qiansanzuxuan.zuxuandanshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 15, "ball": "03,08,09", "type": "xuansan.qiansanzuxuan.zuxuanfushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 14, "ball": "08 09 06", "type": "xuansan.qiansanzhixuan.zhixuandanshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 13, "ball": "10,01,02,-,-", "type": "xuansan.qiansanzhixuan.zhixuanfushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 12, "ball": "[胆 10] 09", "type": "xuaner.renxuanerzhonger.renxuandantuo", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 11, "ball": "09 10", "type": "xuaner.renxuanerzhonger.renxuandanshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 10, "ball": "02,06", "type": "xuaner.renxuanerzhonger.renxuanfushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 9, "ball": "[胆 01] 08", "type": "xuaner.qianerzuxuan.zuxuandantuo", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 8, "ball": "06 07", "type": "xuaner.qianerzuxuan.zuxuandanshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 7, "ball": "02,03", "type": "xuaner.qianerzuxuan.zuxuanfushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 6, "ball": "02 04", "type": "xuaner.qianerzhixuan.zhixuandanshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 5, "ball": "07,02,-,-,-", "type": "xuaner.qianerzhixuan.zhixuanfushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 4, "ball": "05", "type": "xuanyi.renxuanyizhongyi.danshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 3, "ball": "05", "type": "xuanyi.renxuanyizhongyi.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 2, "ball": "04,-,-,-,-", "type": "xuanyi.dingweidan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 1, "ball": "02", "type": "xuanyi.qiansanyimabudingwei.fushi", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1}], "orders": order_plan, "amount": 74 * len_order}
        elif lottery in ['pk10', 'xyft', 'xyft168']:
            data_ = {"gameType": lottery, "isTrace": trace_value, "traceWinStop": is_trace_win_stop,
                     "traceStopValue": trace_stop_value, "balls": [{"id": 22,
                                                                    "ball": "-,-,-,-,-,01 02 03 04 05,01 02 03 04 05,01 02 03 04 05,01 02 03 04 05,01 02 03 04 05",
                                                                    "type": "caipaiwei.dingweidan.houfushi",
                                                                    "moneyunit": 1, "multiple": 1,
                                                                    "awardMode": award_mode,
                                                                    "amount": 50, "num": 25}, {"id": 21,
                                                                                               "ball": "06 07 08 09 10,06 07 08 09 10,06 07 08 09 10,06 07 08 09 10,06 07 08 09 10,-,-,-,-,-",
                                                                                               "type": "caipaiwei.dingweidan.qianfushi",
                                                                                               "moneyunit": 1,
                                                                                               "multiple": 1,
                                                                                               "awardMode": award_mode,
                                                                                               "amount": 50, "num": 25},
                                                                   {"id": 20, "ball": "02 06 07 08 09",
                                                                    "type": "qianwu.zuxuan.danshi", "moneyunit": 1,
                                                                    "multiple": 1, "awardMode": award_mode, "amount": 2,
                                                                    "num": 1}, {"id": 19, "ball": "06,07,08,09,10",
                                                                                "type": "qianwu.zuxuan.fushi",
                                                                                "moneyunit": 1, "multiple": 1,
                                                                                "awardMode": award_mode, "amount": 2,
                                                                                "num": 1},
                                                                   {"id": 18, "ball": "01 04 05 06 07",
                                                                    "type": "qianwu.zhixuan.danshi", "moneyunit": 1,
                                                                    "multiple": 1, "awardMode": award_mode, "amount": 2,
                                                                    "num": 1}, {"id": 17,
                                                                                "ball": "02 04 06 08 10,02 04 06 08 10,02 04 06 08 10,02 04 06 08 10,02 04 06 08 10,-,-,-,-,-",
                                                                                "type": "qianwu.zhixuan.fushi",
                                                                                "moneyunit": 1, "multiple": 1,
                                                                                "awardMode": award_mode, "amount": 240,
                                                                                "num": 120},
                                                                   {"id": 16, "ball": "06 07 08 09",
                                                                    "type": "qiansi.zuxuan.danshi", "moneyunit": 1,
                                                                    "multiple": 1, "awardMode": award_mode, "amount": 2,
                                                                    "num": 1}, {"id": 15, "ball": "02,04,06,08,10",
                                                                                "type": "qiansi.zuxuan.fushi",
                                                                                "moneyunit": 1, "multiple": 1,
                                                                                "awardMode": award_mode, "amount": 10,
                                                                                "num": 5},
                                                                   {"id": 14, "ball": "06 07 08 09",
                                                                    "type": "qiansi.zhixuan.danshi", "moneyunit": 1,
                                                                    "multiple": 1, "awardMode": award_mode, "amount": 2,
                                                                    "num": 1}, {"id": 13,
                                                                                "ball": "02 04 06 08 10,02 04 06 08 10,02 04 06 08 10,02 04 06 08 10,-,-,-,-,-,-",
                                                                                "type": "qiansi.zhixuan.fushi",
                                                                                "moneyunit": 1, "multiple": 1,
                                                                                "awardMode": award_mode, "amount": 240,
                                                                                "num": 120},
                                                                   {"id": 12, "ball": "05 06 07",
                                                                    "type": "guanyaji.caiguanyaji.danshi",
                                                                    "moneyunit": 1,
                                                                    "multiple": 1, "awardMode": award_mode, "amount": 2,
                                                                    "num": 1}, {"id": 11,
                                                                                "ball": "01 02 03 04 05,01 02 03 04 05,01 02 03 04 05,-,-,-,-,-,-,-",
                                                                                "type": "guanyaji.caiguanyaji.fushi",
                                                                                "moneyunit": 1, "multiple": 1,
                                                                                "awardMode": award_mode, "amount": 120,
                                                                                "num": 60},
                                                                   {"id": 10, "ball": "05 06 07",
                                                                    "type": "guanyaji.zuxuan.danshi",
                                                                    "moneyunit": 1,
                                                                    "multiple": 1,
                                                                    "awardMode": award_mode,
                                                                    "amount": 2, "num": 1},
                                                                   {"id": 9, "ball": "01,02,03,04,05",
                                                                    "type": "guanyaji.zuxuan.fushi", "moneyunit": 1,
                                                                    "multiple": 1, "awardMode": award_mode,
                                                                    "amount": 20,
                                                                    "num": 10}, {"id": 8, "ball": "05 06 07",
                                                                                 "type": "guanyaji.zhixuan.danshi",
                                                                                 "moneyunit": 1, "multiple": 1,
                                                                                 "awardMode": award_mode, "amount": 2,
                                                                                 "num": 1}, {"id": 7,
                                                                                             "ball": "01 02 03 04 05,01 02 03 04 05,01 02 03 04 05,-,-,-,-,-,-,-",
                                                                                             "type": "guanyaji.zhixuan.fushi",
                                                                                             "moneyunit": 1,
                                                                                             "multiple": 1,
                                                                                             "awardMode": award_mode,
                                                                                             "amount": 120, "num": 60},
                                                                   {"id": 6, "ball": "01 02",
                                                                    "type": "guanya.caiguanya.danshi", "moneyunit": 1,
                                                                    "multiple": 1, "awardMode": award_mode, "amount": 2,
                                                                    "num": 1}, {"id": 5,
                                                                                "ball": "01 02 03 04 05,01 02 03 04 05,-,-,-,-,-,-,-,-",
                                                                                "type": "guanya.caiguanya.fushi",
                                                                                "moneyunit": 1, "multiple": 1,
                                                                                "awardMode": award_mode, "amount": 40,
                                                                                "num": 20},
                                                                   {"id": 4, "ball": "3,4,5,6,7,8,9,10,11",
                                                                    "type": "guanya.hezhi.fushi", "moneyunit": 1,
                                                                    "multiple": 1, "awardMode": award_mode,
                                                                    "amount": 100,
                                                                    "num": 50}, {"id": 3, "ball": "01 02",
                                                                                 "type": "guanya.zuxuan.danshi",
                                                                                 "moneyunit": 1, "multiple": 1,
                                                                                 "awardMode": award_mode, "amount": 2,
                                                                                 "num": 1},
                                                                   {"id": 2, "ball": "01,02,03,04,05",
                                                                    "type": "guanya.zuxuan.fushi", "moneyunit": 1,
                                                                    "multiple": 1, "awardMode": award_mode,
                                                                    "amount": 20,
                                                                    "num": 10}, {"id": 1, "ball": "01 02",
                                                                                 "type": "guanya.zhixuan.danshi",
                                                                                 "moneyunit": 1, "multiple": 1,
                                                                                 "awardMode": award_mode, "amount": 2,
                                                                                 "num": 1}], "orders": order_plan,
                     "amount": 1032 * len_order}
        elif lottery in ['llssc', 'jlffc', 'btcffc', 'slmmc']:
            data_ = {"gameType": lottery, "isTrace": trace_value, "traceWinStop": is_trace_win_stop,
                     "traceStopValue": trace_stop_value, "balls": [
                    {"id": 85, "ball": "-,和,-,-,-,-,-,-,-,-", "type": "longhu.longhudou.fushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 84, "ball": "双,大", "type": "daxiaodanshuang.dxds.houer", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 83, "ball": "小", "type": "daxiaodanshuang.dxds.houyi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 82, "ball": "大,单", "type": "daxiaodanshuang.dxds.qianer", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 81, "ball": "大", "type": "daxiaodanshuang.dxds.qianyi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 80, "ball": "双", "type": "daxiaodanshuang.dxds.zonghe", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 79, "ball": "-,-,-,5,-", "type": "yixing.dingweidan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 78, "ball": "5", "type": "houer.zuxuan.baodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 9},
                    {"id": 77, "ball": "11", "type": "houer.zuxuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 4},
                    {"id": 76, "ball": "46", "type": "houer.zuxuan.danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 75, "ball": "2,4", "type": "houer.zuxuan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 74, "ball": "3", "type": "houer.zhixuan.kuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 14},
                    {"id": 73, "ball": "5", "type": "houer.zhixuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 6},
                    {"id": 72, "ball": "49", "type": "houer.zhixuan.danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 71, "ball": "-,-,-,3,6", "type": "houer.zhixuan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 70, "ball": "7", "type": "qianer.zuxuan.baodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 9},
                    {"id": 69, "ball": "8", "type": "qianer.zuxuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 4},
                    {"id": 68, "ball": "27", "type": "qianer.zuxuan.danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 67, "ball": "1,6", "type": "qianer.zuxuan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 66, "ball": "4", "type": "qianer.zhixuan.kuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 12},
                    {"id": 65, "ball": "8", "type": "qianer.zhixuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 9},
                    {"id": 64, "ball": "31", "type": "qianer.zhixuan.danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 63, "ball": "3,5,-,-,-", "type": "qianer.zhixuan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 62, "ball": "3,5", "type": "housan.budingwei.ermabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 61, "ball": "7", "type": "housan.budingwei.yimabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 60, "ball": "078", "type": "housan.zuxuan.zuliudanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 59, "ball": "577", "type": "housan.zuxuan.zusandanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 58, "ball": "9", "type": "housan.zuxuan.baodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 54},
                    {"id": 57, "ball": "125", "type": "housan.zuxuan.hunhezuxuan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 56, "ball": "2,3,9", "type": "housan.zuxuan.zuliu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 55, "ball": "1,2", "type": "housan.zuxuan.zusan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 54, "ball": "26", "type": "housan.zuxuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 53, "ball": "1", "type": "housan.zhixuan.kuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 54},
                    {"id": 52, "ball": "6", "type": "housan.zhixuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 28},
                    {"id": 51, "ball": "794", "type": "housan.zhixuan.danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 50, "ball": "-,-,0,3,8", "type": "housan.zhixuan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 49, "ball": "5,8", "type": "zhongsan.budingwei.ermabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 48, "ball": "1", "type": "zhongsan.budingwei.yimabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 47, "ball": "025", "type": "zhongsan.zuxuan.zuliudanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 46, "ball": "338", "type": "zhongsan.zuxuan.zusandanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 45, "ball": "5", "type": "zhongsan.zuxuan.baodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 54},
                    {"id": 44, "ball": "149", "type": "zhongsan.zuxuan.hunhezuxuan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 43, "ball": "4,5,7", "type": "zhongsan.zuxuan.zuliu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 42, "ball": "0,3", "type": "zhongsan.zuxuan.zusan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 41, "ball": "14", "type": "zhongsan.zuxuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 15},
                    {"id": 40, "ball": "5", "type": "zhongsan.zhixuan.kuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 150},
                    {"id": 39, "ball": "15", "type": "zhongsan.zhixuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 73},
                    {"id": 38, "ball": "669", "type": "zhongsan.zhixuan.danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 37, "ball": "-,6,9,1,-", "type": "zhongsan.zhixuan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 36, "ball": "0,9", "type": "qiansan.budingwei.ermabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 35, "ball": "3", "type": "qiansan.budingwei.yimabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 34, "ball": "147", "type": "qiansan.zuxuan.zuliudanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 33, "ball": "599", "type": "qiansan.zuxuan.zusandanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 32, "ball": "2", "type": "qiansan.zuxuan.baodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 54},
                    {"id": 31, "ball": "159", "type": "qiansan.zuxuan.hunhezuxuan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 30, "ball": "0,5,7", "type": "qiansan.zuxuan.zuliu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 29, "ball": "2,3", "type": "qiansan.zuxuan.zusan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 28, "ball": "14", "type": "qiansan.zuxuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 15},
                    {"id": 27, "ball": "4", "type": "qiansan.zhixuan.kuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 144},
                    {"id": 26, "ball": "2", "type": "qiansan.zhixuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 6},
                    {"id": 25, "ball": "582", "type": "qiansan.zhixuan.danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 24, "ball": "0,5,8,-,-", "type": "qiansan.zhixuan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 23, "ball": "1,9", "type": "sixing.budingwei.ermabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 22, "ball": "8", "type": "sixing.budingwei.yimabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 21, "ball": "4,0", "type": "sixing.zuxuan.zuxuan4", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 20, "ball": "4,5", "type": "sixing.zuxuan.zuxuan6", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 19, "ball": "7,28", "type": "sixing.zuxuan.zuxuan12", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 18, "ball": "1,2,5,9", "type": "sixing.zuxuan.zuxuan24", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 17, "ball": "6266", "type": "sixing.zhixuan.danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 16, "ball": "-,9,4,6,4", "type": "sixing.zhixuan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 15, "ball": "6", "type": "wuxing.quwei.sijifacai", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 14, "ball": "6", "type": "wuxing.quwei.sanxingbaoxi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 13, "ball": "8", "type": "wuxing.quwei.haoshichengshuang", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 12, "ball": "4", "type": "wuxing.quwei.yifanfengshun", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 11, "ball": "0,3,7", "type": "wuxing.budingwei.sanmabudingwei", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 10, "ball": "5,8", "type": "wuxing.budingwei.ermabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 9, "ball": "3", "type": "wuxing.budingwei.yimabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 8, "ball": "2,7", "type": "wuxing.zuxuan.zuxuan5", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 7, "ball": "0,4", "type": "wuxing.zuxuan.zuxuan10", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 6, "ball": "4,79", "type": "wuxing.zuxuan.zuxuan20", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 5, "ball": "01,3", "type": "wuxing.zuxuan.zuxuan30", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 4, "ball": "4,078", "type": "wuxing.zuxuan.zuxuan60", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 3, "ball": "1,2,5,6,8", "type": "wuxing.zuxuan.zuxuan120", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 2, "ball": "74993", "type": "wuxing.zhixuan.danshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 1, "ball": "9,9,6,4,8", "type": "wuxing.zhixuan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1}], "orders": order_plan, "redDiscountAmount": 0,
                     "amount": 1566 * len_order}
        elif lottery == 'txffc':
            data_ = {"gameType": lottery, "isTrace": trace_value, "traceWinStop": is_trace_win_stop,
                     "traceStopValue": trace_stop_value, "balls": [
                    {"id": 85, "ball": "-,-,-,龙,-,-", "type": "longhu.longhudou.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 84, "ball": "大,双", "type": "daxiaodanshuang.dxds.houer", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 83, "ball": "单", "type": "daxiaodanshuang.dxds.houyi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 82, "ball": "小", "type": "daxiaodanshuang.dxds.houyi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 81, "ball": "双", "type": "daxiaodanshuang.dxds.houyi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 80, "ball": "大", "type": "daxiaodanshuang.dxds.houyi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 79, "ball": "-,-,-,-,1", "type": "yixing.dingweidan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 78, "ball": "3", "type": "houer.zuxuan.baodan", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 9},
                    {"id": 77, "ball": "17", "type": "houer.zuxuan.hezhi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 76, "ball": "57", "type": "houer.zuxuan.danshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 75, "ball": "6,9", "type": "houer.zuxuan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 74, "ball": "4", "type": "houer.zhixuan.kuadu", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 12},
                    {"id": 73, "ball": "1", "type": "houer.zhixuan.hezhi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 72, "ball": "04", "type": "houer.zhixuan.danshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 71, "ball": "-,-,-,2,2", "type": "houer.zhixuan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 70, "ball": "7", "type": "qianer.zuxuan.baodan", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 9},
                    {"id": 69, "ball": "17", "type": "qianer.zuxuan.hezhi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 68, "ball": "05", "type": "qianer.zuxuan.danshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 67, "ball": "5,7", "type": "qianer.zuxuan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 66, "ball": "3", "type": "qianer.zhixuan.kuadu", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 14},
                    {"id": 65, "ball": "13", "type": "qianer.zhixuan.hezhi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 6},
                    {"id": 64, "ball": "94", "type": "qianer.zhixuan.danshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 63, "ball": "2,9,-,-,-", "type": "qianer.zhixuan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 62, "ball": "0,9", "type": "housan.budingwei.ermabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 61, "ball": "5", "type": "housan.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 60, "ball": "346", "type": "housan.zuxuan.zuliudanshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 59, "ball": "455", "type": "housan.zuxuan.zusandanshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 58, "ball": "2", "type": "housan.zuxuan.baodan", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 54},
                    {"id": 57, "ball": "346", "type": "housan.zuxuan.hunhezuxuan", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 56, "ball": "1,4,7", "type": "housan.zuxuan.zuliu", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 55, "ball": "4,9", "type": "housan.zuxuan.zusan", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 54, "ball": "2", "type": "housan.zuxuan.hezhi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 53, "ball": "2", "type": "housan.zhixuan.kuadu", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 96},
                    {"id": 52, "ball": "1", "type": "housan.zhixuan.hezhi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 3},
                    {"id": 51, "ball": "207", "type": "housan.zhixuan.danshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 50, "ball": "-,-,2,5,3", "type": "housan.zhixuan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 49, "ball": "2,4", "type": "zhongsan.budingwei.ermabudingwei", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 48, "ball": "6", "type": "zhongsan.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 47, "ball": "017", "type": "zhongsan.zuxuan.zuliudanshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 46, "ball": "779", "type": "zhongsan.zuxuan.zusandanshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 45, "ball": "9", "type": "zhongsan.zuxuan.baodan", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 54},
                    {"id": 44, "ball": "156", "type": "zhongsan.zuxuan.hunhezuxuan", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 43, "ball": "1,4,9", "type": "zhongsan.zuxuan.zuliu", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 42, "ball": "1,6", "type": "zhongsan.zuxuan.zusan", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 41, "ball": "20", "type": "zhongsan.zuxuan.hezhi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 8},
                    {"id": 40, "ball": "7", "type": "zhongsan.zhixuan.kuadu", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 126},
                    {"id": 39, "ball": "17", "type": "zhongsan.zhixuan.hezhi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 63},
                    {"id": 38, "ball": "402", "type": "zhongsan.zhixuan.danshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 37, "ball": "-,5,2,4,-", "type": "zhongsan.zhixuan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 36, "ball": "2,3", "type": "qiansan.budingwei.ermabudingwei", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 35, "ball": "3", "type": "qiansan.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 34, "ball": "179", "type": "qiansan.zuxuan.zuliudanshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 33, "ball": "007", "type": "qiansan.zuxuan.zusandanshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 32, "ball": "3", "type": "qiansan.zuxuan.baodan", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 54},
                    {"id": 31, "ball": "034", "type": "qiansan.zuxuan.hunhezuxuan", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 30, "ball": "3,4,5", "type": "qiansan.zuxuan.zuliu", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 29, "ball": "0,1", "type": "qiansan.zuxuan.zusan", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 28, "ball": "3", "type": "qiansan.zuxuan.hezhi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 27, "ball": "6", "type": "qiansan.zhixuan.kuadu", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 144},
                    {"id": 26, "ball": "16", "type": "qiansan.zhixuan.hezhi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 69},
                    {"id": 25, "ball": "338", "type": "qiansan.zhixuan.danshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 24, "ball": "8,8,2,-,-", "type": "qiansan.zhixuan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 23, "ball": "4,6", "type": "sixing.budingwei.ermabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 22, "ball": "2", "type": "sixing.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 21, "ball": "5,0", "type": "sixing.zuxuan.zuxuan4", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 20, "ball": "6,7", "type": "sixing.zuxuan.zuxuan6", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 19, "ball": "9,04", "type": "sixing.zuxuan.zuxuan12", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 18, "ball": "3,4,5,8", "type": "sixing.zuxuan.zuxuan24", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 17, "ball": "8360", "type": "sixing.zhixuan.danshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 16, "ball": "-,8,8,3,4", "type": "sixing.zhixuan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 15, "ball": "6", "type": "wuxing.quwei.sijifacai", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 14, "ball": "6", "type": "wuxing.quwei.sanxingbaoxi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 13, "ball": "8", "type": "wuxing.quwei.haoshichengshuang", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 12, "ball": "6", "type": "wuxing.quwei.yifanfengshun", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 11, "ball": "3,4,8", "type": "wuxing.budingwei.sanmabudingwei", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 10, "ball": "3,7", "type": "wuxing.budingwei.ermabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 9, "ball": "6", "type": "wuxing.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 8, "ball": "3", "type": "wuxing.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 7, "ball": "4", "type": "wuxing.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 6, "ball": "2", "type": "wuxing.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 5, "ball": "6", "type": "wuxing.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 4, "ball": "1", "type": "wuxing.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 3, "ball": "5", "type": "wuxing.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 2, "ball": "0", "type": "wuxing.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 1, "ball": "8", "type": "wuxing.budingwei.yimabudingwei", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1}], "orders": order_plan, "amount": 1594 * len_order}
        elif lottery in ['bjkl8', 'fckl8']:
            data_ = {"gameType": lottery, "isTrace": trace_value, "traceWinStop": is_trace_win_stop,
                     "traceStopValue": trace_stop_value, "balls": [
                    {"id": 8, "ball": "05,25,42,43,51,67,80", "type": "renxuan.putongwanfa.renxuan7", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 7, "ball": "12,28,54,64,69,80", "type": "renxuan.putongwanfa.renxuan6", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 6, "ball": "24,29,39,50,71", "type": "renxuan.putongwanfa.renxuan5", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 5, "ball": "03,14,51,57", "type": "renxuan.putongwanfa.renxuan4", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 4, "ball": "16,52,79", "type": "renxuan.putongwanfa.renxuan3", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 3, "ball": "48,74", "type": "renxuan.putongwanfa.renxuan2", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 2, "ball": "25", "type": "renxuan.putongwanfa.renxuan1", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 1, "ball": "中", "type": "quwei.panmian.quweib", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1}], "orders": order_plan, "amount": 16 * len_order}
        elif lottery == 'shssl':
            data_ = {"gameType": lottery, "isTrace": trace_value, "traceWinStop": is_trace_win_stop,
                     "traceStopValue": trace_stop_value, "balls": [
                    {"id": 34, "ball": "-,-,龙", "type": "longhu.longhudou.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 33, "ball": "小,双", "type": "daxiaodanshuang.dxds.houer", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 32, "ball": "双", "type": "daxiaodanshuang.dxds.houyi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 31, "ball": "7,-,-", "type": "yixing.dingweidan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 30, "ball": "2", "type": "houer.zuxuan.baodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 9},
                    {"id": 29, "ball": "16", "type": "houer.zuxuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 28, "ball": "34", "type": "houer.zuxuan.danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 27, "ball": "4,8", "type": "houer.zuxuan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 26, "ball": "4", "type": "houer.zhixuan.kuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 12},
                    {"id": 25, "ball": "17", "type": "houer.zhixuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 24, "ball": "95", "type": "houer.zhixuan.danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 23, "ball": "-,0,1", "type": "houer.zhixuan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 22, "ball": "1", "type": "qianer.zuxuan.baodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 9},
                    {"id": 21, "ball": "6", "type": "qianer.zuxuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 3},
                    {"id": 20, "ball": "04", "type": "qianer.zuxuan.danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 19, "ball": "2,3", "type": "qianer.zuxuan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 18, "ball": "9", "type": "qianer.zhixuan.kuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 17, "ball": "10", "type": "qianer.zhixuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 9},
                    {"id": 16, "ball": "67", "type": "qianer.zhixuan.danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 15, "ball": "1,2,-", "type": "qianer.zhixuan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 14, "ball": "4,9", "type": "housan.budingwei.ermabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 13, "ball": "7", "type": "housan.budingwei.yimabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 12, "ball": "078", "type": "housan.zuxuan.zuliudanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 11, "ball": "338", "type": "housan.zuxuan.zusandanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 10, "ball": "3", "type": "housan.zuxuan.baodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 54},
                    {"id": 9, "ball": "026", "type": "housan.zuxuan.hunhezuxuan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 8, "ball": "1,4,8", "type": "housan.zuxuan.zuliu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 7, "ball": "3,9", "type": "housan.zuxuan.zusan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 6, "ball": "12", "type": "housan.zuxuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 14},
                    {"id": 5, "ball": "6", "type": "housan.zhixuan.kuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 144},
                    {"id": 4, "ball": "18", "type": "housan.zhixuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 55},
                    {"id": 3, "ball": "035", "type": "housan.zhixuan.danshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 2, "ball": "4,5,7", "type": "housan.zhixuan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1}], "orders": order_plan, "redDiscountAmount": 0,
                     "amount": 672 * len_order}
        elif lottery in ['v3d', 'fc3d', 'n3d', 'np3']:
            data_ = {"gameType": lottery, "isTrace": trace_value, "traceWinStop": is_trace_win_stop,
                     "traceStopValue": trace_stop_value, "balls": [
                    {"id": 30, "ball": "-,1,-", "type": "yixing.dingweidan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 29, "ball": "6", "type": "houer.zuxuan.zuxuanbaodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 9},
                    {"id": 28, "ball": "12", "type": "houer.zuxuan.zuxuanhezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 3},
                    {"id": 27, "ball": "28", "type": "houer.zuxuan.zuxuandanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 26, "ball": "6,8", "type": "houer.zuxuan.zuxuanfushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 25, "ball": "1", "type": "houer.zhixuan.zhixuankuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 18},
                    {"id": 24, "ball": "6", "type": "houer.zhixuan.zhixuanhezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 7},
                    {"id": 23, "ball": "58", "type": "houer.zhixuan.zhixuandanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 22, "ball": "-,4,3", "type": "houer.zhixuan.zhixuanfushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 21, "ball": "3", "type": "qianer.zuxuan.zuxuanbaodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 9},
                    {"id": 20, "ball": "11", "type": "qianer.zuxuan.zuxuanhezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 4},
                    {"id": 19, "ball": "05", "type": "qianer.zuxuan.zuxuandanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 18, "ball": "1,7", "type": "qianer.zuxuan.zuxuanfushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 17, "ball": "1", "type": "qianer.zhixuan.zhixuankuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 18},
                    {"id": 16, "ball": "11", "type": "qianer.zhixuan.zhixuanhezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 8},
                    {"id": 15, "ball": "23", "type": "qianer.zhixuan.zhixuandanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 14, "ball": "1,0,-", "type": "qianer.zhixuan.zhixuanfushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 13, "ball": "4,7", "type": "sanxing.budingwei.ermabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 12, "ball": "3", "type": "sanxing.budingwei.yimabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 11, "ball": "235", "type": "sanxing.zuxuan.zuliudanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 10, "ball": "388", "type": "sanxing.zuxuan.zusandanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 9, "ball": "1", "type": "sanxing.zuxuan.zuxuanbaodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 54},
                    {"id": 8, "ball": "248", "type": "sanxing.zuxuan.hunhezuxuan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 7, "ball": "3,7,8", "type": "sanxing.zuxuan.zuliu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 6, "ball": "5,7", "type": "sanxing.zuxuan.zusan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 5, "ball": "6", "type": "sanxing.zuxuan.zuxuanhezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 6},
                    {"id": 4, "ball": "6", "type": "sanxing.zhixuan.kuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 144},
                    {"id": 3, "ball": "25", "type": "sanxing.zhixuan.hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 6},
                    {"id": 2, "ball": "126", "type": "sanxing.zhixuan.danshi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 1, "ball": "4,4,3", "type": "sanxing.zhixuan.fushi", "moneyunit": "1", "multiple": 1,
                     "awardMode": award_mode, "num": 1}], "orders": order_plan, "amount": 610 * len_order}
        elif lottery in ['jsdice', 'jldice  1', 'jldice2']:
            data_ = {"gameType": lottery, "isTrace": trace_value, "multiple": 1, "trace": 1, "amount": "520.00",
                     "balls": [
                         {"ball": "大", "id": 0, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "daxiao.daxiao"},
                         {"ball": "单", "id": 1, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "danshuang.danshuang"},
                         {"ball": "66*", "id": 2, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "ertonghaofuxuan.ertonghaofuxuan"},
                         {"ball": "55*", "id": 3, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "ertonghaofuxuan.ertonghaofuxuan"},
                         {"ball": "44*", "id": 4, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "ertonghaofuxuan.ertonghaofuxuan"},
                         {"ball": "666", "id": 5, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "santonghaodanxuan.santonghaodanxuan"},
                         {"ball": "555", "id": 6, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "santonghaodanxuan.santonghaodanxuan"},
                         {"ball": "444", "id": 7, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "santonghaodanxuan.santonghaodanxuan"},
                         {"ball": "333", "id": 8, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "santonghaodanxuan.santonghaodanxuan"},
                         {"ball": "222", "id": 9, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "santonghaodanxuan.santonghaodanxuan"},
                         {"ball": "111", "id": 10, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "santonghaodanxuan.santonghaodanxuan"},
                         {"ball": "111 222 333 444 555 666", "id": 11, "moneyunit": 1, "multiple": 1, "amount": 10,
                          "num": 5,
                          "type": "santonghaotongxuan.santonghaotongxuan"},
                         {"ball": "33*", "id": 12, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "ertonghaofuxuan.ertonghaofuxuan"},
                         {"ball": "22*", "id": 13, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "ertonghaofuxuan.ertonghaofuxuan"},
                         {"ball": "11*", "id": 14, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "ertonghaofuxuan.ertonghaofuxuan"},
                         {"ball": "小", "id": 15, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "daxiao.daxiao"},
                         {"ball": "双", "id": 16, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "danshuang.danshuang"},
                         {"ball": "17", "id": 17, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "16", "id": 18, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "15", "id": 19, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "14", "id": 20, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "13", "id": 21, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "12", "id": 22, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "11", "id": 23, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "10", "id": 24, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "9", "id": 25, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "8", "id": 26, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "7", "id": 27, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "6", "id": 28, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "5", "id": 29, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "4", "id": 30, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "hezhi.hezhi"},
                         {"ball": "5,6", "id": 31, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "4,6", "id": 32, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "4,5", "id": 33, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "3,6", "id": 34, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "3,5", "id": 35, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "3,4", "id": 36, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "2,6", "id": 37, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "2,5", "id": 38, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "2,4", "id": 39, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "2,3", "id": 40, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "1,6", "id": 41, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "1,5", "id": 42, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "1,4", "id": 43, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "1,3", "id": 44, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "1,2", "id": 45, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "erbutonghao.erbutonghao"},
                         {"ball": "6", "id": 46, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "yibutonghao.yibutonghao"},
                         {"ball": "5", "id": 47, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "yibutonghao.yibutonghao"},
                         {"ball": "4", "id": 48, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "yibutonghao.yibutonghao"},
                         {"ball": "3", "id": 49, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "yibutonghao.yibutonghao"},
                         {"ball": "2", "id": 50, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "yibutonghao.yibutonghao"},
                         {"ball": "1", "id": 51, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5,
                          "type": "yibutonghao.yibutonghao"}], "orders": order_plan}
        elif lottery == 'p5':
            data_ = {"gameType": lottery, "isTrace": trace_value, "traceWinStop": is_trace_win_stop,
                     "traceStopValue": trace_stop_value, "balls": [
                    {"id": 38, "ball": "2", "type": "p3houer.zuxuan.zuxuanp3houerbaodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 9},
                    {"id": 37, "ball": "6", "type": "p3houer.zuxuan.zuxuanp3houerhezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 3},
                    {"id": 36, "ball": "38", "type": "p3houer.zuxuan.zuxuanp3houerdanshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 35, "ball": "0,7", "type": "p3houer.zuxuan.zuxuanp3houerfushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 34, "ball": "9", "type": "p3houer.zhixuan.zhixuanp3houerkuadu", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 2},
                    {"id": 33, "ball": "5", "type": "p3houer.zhixuan.zhixuanp3houerhezhi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 6},
                    {"id": 32, "ball": "02", "type": "p3houer.zhixuan.zhixuanp3houerdanshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 31, "ball": "-,2,7", "type": "p3houer.zhixuan.zhixuanp3houerfushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 30, "ball": "2", "type": "p3qianer.zuxuan.zuxuanp3qianerbaodan", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 9},
                    {"id": 29, "ball": "7", "type": "p3qianer.zuxuan.zuxuanp3qianerhezhi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 4},
                    {"id": 28, "ball": "67", "type": "p3qianer.zuxuan.zuxuanp3qianerdanshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 27, "ball": "2,5", "type": "p3qianer.zuxuan.zuxuanp3qianerfushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 26, "ball": "3", "type": "p3qianer.zhixuan.zhixuanp3qianerkuadu", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 14},
                    {"id": 25, "ball": "18", "type": "p3qianer.zhixuan.zhixuanp3qianerhezhi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 24, "ball": "48", "type": "p3qianer.zhixuan.zhixuanp3qianerdanshi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 23, "ball": "7,2,-", "type": "p3qianer.zhixuan.zhixuanp3qianerfushi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 22, "ball": "3,8", "type": "p3sanxing.budingwei.ermabudingwei", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 21, "ball": "1", "type": "p3sanxing.budingwei.yimabudingwei", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 20, "ball": "279", "type": "p3sanxing.zuxuan.p3zuliudanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 19, "ball": "229", "type": "p3sanxing.zuxuan.p3zusandanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 18, "ball": "6", "type": "p3sanxing.zuxuan.p3zuxuanbaodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 54},
                    {"id": 17, "ball": "179", "type": "p3sanxing.zuxuan.p3hunhezuxuan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 16, "ball": "1,3,9", "type": "p3sanxing.zuxuan.p3zuliu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 15, "ball": "7,8", "type": "p3sanxing.zuxuan.p3zusan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 2},
                    {"id": 14, "ball": "23", "type": "p3sanxing.zuxuan.p3zuxuanhezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 4},
                    {"id": 13, "ball": "0", "type": "p3sanxing.zhixuan.p3kuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 10},
                    {"id": 12, "ball": "27", "type": "p3sanxing.zhixuan.p3hezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 11, "ball": "249", "type": "p3sanxing.zhixuan.p3danshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 10, "ball": "7,1,9", "type": "p3sanxing.zhixuan.p3fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 9, "ball": "-,-,2,-,-", "type": "p5yixing.dingweidan.fushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 8, "ball": "7", "type": "p5houer.zuxuan.zuxuanp5houerbaodan", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 9},
                    {"id": 7, "ball": "9", "type": "p5houer.zuxuan.zuxuanp5houerhezhi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 5},
                    {"id": 6, "ball": "03", "type": "p5houer.zuxuan.zuxuanp5houerdanshi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 5, "ball": "3,4", "type": "p5houer.zuxuan.zuxuanp5houerfushi", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 1},
                    {"id": 4, "ball": "4", "type": "p5houer.zhixuan.zhixuanp5houerkuadu", "moneyunit": 1, "multiple": 1,
                     "awardMode": award_mode, "num": 12},
                    {"id": 3, "ball": "14", "type": "p5houer.zhixuan.zhixuanp5houerhezhi", "moneyunit": 1,
                     "multiple": 1, "awardMode": award_mode, "num": 5},
                    {"id": 2, "ball": "64", "type": "p5houer.zhixuan.zhixuanp5houerdanshi", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 1, "ball": "-,-,-,7,4", "type": "p5houer.zhixuan.zhixuanp5houerfushi", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1}], "orders": order_plan,
                     "amount": 342 * len_order}
        elif lottery == 'ssq':
            data_ = {"gameType": lottery, "isTrace": trace_value, "traceWinStop": is_trace_win_stop,
                     "traceStopValue": trace_stop_value, "balls": [
                    {"id": 3, "ball": "D:18_T:01,03,06,26,33+13", "type": "biaozhuntouzhu.biaozhun.dantuo",
                     "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 2, "ball": "08,17,19,22,24,33+07", "type": "biaozhuntouzhu.biaozhun.danshi",
                     "moneyunit": "1", "multiple": 1, "awardMode": award_mode, "num": 1},
                    {"id": 1, "ball": "10,15,18,23,24,31+05", "type": "biaozhuntouzhu.biaozhun.fushi", "moneyunit": "1",
                     "multiple": 1, "awardMode": award_mode, "num": 1}], "orders": order_plan, "amount": 6 * len_order}
        elif lottery == 'pcdd':
            # 需查出用戶反點, 如果是高獎金的話, odds 需用 平台獎金 * 用戶反點
            conn = OracleConnection(env_id=envs)
            lottery_point = conn.select_lottery_point(self.lottery_dict[lottery][1], account)
            logger.info(lottery_point)  # {0: ('autotest101', datetime.datetime(2020, 12, 2, 17, 11, 54, 328000), 450, '奖金组1800')}
            user_point = lottery_point[0][2] / 10000
            bonus = conn.select_bonus(self.lottery_dict[lottery][1], '', 'FF_bonus')
            # print(bonus)
            assert award_mode in [1, 2]  # 確保award_mode正確性

            if award_mode == 1:  # 一般玩法, odds 就直接用 bonus 的key
                list_keys = list(bonus.keys())
            else:
                list_keys = [int((bonus_[0] + bonus_[1] * user_point) * 100) / 100 for bonus_ in
                             bonus.items()]  # 高獎金抓出來, 需呈上自己返點
            # print(list_keys)
            data_ = {"balls": [
                {"id": 1, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "0",
                 "odds": list_keys[0], "awardMode": award_mode},
                {"id": 2, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "1", "odds": list_keys[1], "awardMode": award_mode},
                {"id": 3, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "2", "odds": list_keys[2], "awardMode": award_mode},
                {"id": 4, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "3", "odds": list_keys[3], "awardMode": award_mode},
                {"id": 5, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "5", "odds": list_keys[5], "awardMode": award_mode},
                {"id": 6, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "4", "odds": list_keys[4], "awardMode": award_mode},
                {"id": 7, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "6", "odds": list_keys[6], "awardMode": award_mode},
                {"id": 8, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "13", "odds": list_keys[13], "awardMode": award_mode},
                {"id": 9, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "12", "odds": list_keys[12], "awardMode": award_mode},
                {"id": 10, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "11", "odds": list_keys[11], "awardMode": award_mode},
                {"id": 11, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "10", "odds": list_keys[10], "awardMode": award_mode},
                {"id": 12, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "9", "odds": list_keys[9], "awardMode": award_mode},
                {"id": 13, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "8", "odds": list_keys[8], "awardMode": award_mode},
                {"id": 14, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "7", "odds": list_keys[7], "awardMode": award_mode},
                {"id": 15, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "14", "odds": list_keys[13], "awardMode": award_mode},
                {"id": 16, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "15", "odds": list_keys[12], "awardMode": award_mode},
                {"id": 17, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "16", "odds": list_keys[11], "awardMode": award_mode},
                {"id": 18, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "17", "odds": list_keys[10], "awardMode": award_mode},
                {"id": 19, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "18", "odds": list_keys[9], "awardMode": award_mode},
                {"id": 20, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "19", "odds": list_keys[8], "awardMode": award_mode},
                {"id": 21, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "20", "odds": list_keys[7], "awardMode": award_mode},
                {"id": 22, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "27", "odds": list_keys[0], "awardMode": award_mode},
                {"id": 23, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "26", "odds": list_keys[1], "awardMode": award_mode},
                {"id": 24, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "25", "odds": list_keys[2], "awardMode": award_mode},
                {"id": 25, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "24", "odds": list_keys[3], "awardMode": award_mode},
                {"id": 26, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "23", "odds": list_keys[4], "awardMode": award_mode},
                {"id": 27, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "22", "odds": list_keys[5], "awardMode": award_mode},
                {"id": 28, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,
                 "ball": "21", "odds": list_keys[6], "awardMode": award_mode},
                {"id": 29, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.quwei.baosan", "amount": 1,
                 "ball": "0,1,2", "odds": list_keys[20], "awardMode": award_mode},
                {"id": 30, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.quwei.saibo", "amount": 1,
                 "ball": "红", "odds": list_keys[18], "awardMode": award_mode},
                {"id": 31, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.quwei.saibo", "amount": 1,
                 "ball": "绿", "odds": list_keys[19], "awardMode": award_mode},
                {"id": 32, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.quwei.baozi", "amount": 1,
                 "ball": "豹子", "odds": list_keys[3], "awardMode": award_mode},
                {"id": 33, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.quwei.saibo", "amount": 1,
                 "ball": "蓝", "odds": list_keys[19], "awardMode": award_mode},
                {"id": 34, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.jizhi", "amount": 1,
                 "ball": "极小", "odds": list_keys[17], "awardMode": award_mode},
                {"id": 35, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.zuhedaxiaodanshuang",
                 "amount": 1, "ball": "大单", "odds": list_keys[16], "awardMode": award_mode},
                {"id": 36, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.zuhedaxiaodanshuang",
                 "amount": 1, "ball": "大双", "odds": list_keys[15], "awardMode": award_mode},
                {"id": 37, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.jizhi", "amount": 1,
                 "ball": "极大", "odds": list_keys[17], "awardMode": award_mode},
                {"id": 38, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.zuhedaxiaodanshuang",
                 "amount": 1, "ball": "小单", "odds": list_keys[15], "awardMode": award_mode},
                {"id": 39, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.zuhedaxiaodanshuang",
                 "amount": 1, "ball": "小双", "odds": list_keys[16], "awardMode": award_mode},
                {"id": 40, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.daxiaodanshuang",
                 "amount": 1, "ball": "双", "odds": list_keys[14], "awardMode": award_mode},
                {"id": 41, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.daxiaodanshuang",
                 "amount": 1, "ball": "单", "odds": list_keys[14], "awardMode": award_mode},
                {"id": 42, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.daxiaodanshuang",
                 "amount": 1, "ball": "小", "odds": list_keys[14], "awardMode": award_mode},
                {"id": 43, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.daxiaodanshuang",
                 "amount": 1, "ball": "大", "odds": list_keys[14], "awardMode": award_mode}], "orders": order_plan,
                "redDiscountAmount": 0, "amount": 43 * len_order, "isTrace": trace_value,
                "traceWinStop": is_trace_win_stop,
                "traceStopValue": trace_stop_value}
        return data_

    def pc_submit(self, account, envs: EnvConfig, em_url, header, lottery, award_mode, trace_issue_num: int,
                  win_stop: bool = True):
        """
        PC投注
        :param account: 用戶帳號
        :param envs: 環境物件
        :param em_url:
        :param header:
        :param lottery: 彩種
        :param award_mode: 獎金組
        :param trace_issue_num: 追號期數，>2則判定為追號，否則為一般投注
        :param win_stop: 是否追中即停
        :return:
        """
        logger.info(f'pc_submit: account={account}, envs={envs}, em_url={em_url}, header={header}, lottery={lottery},'
                    f' award_mode={award_mode}, trace_issue_num={trace_issue_num},win_stop={win_stop}')
        if trace_issue_num <= 1:  # 若非追號單，追中即停更改為False
            win_stop = False
        postData = FF_().submit_json(em_url=em_url, account=account, lottery=lottery, award_mode=award_mode,
                                     trace_issue_num=trace_issue_num, is_trace_win_stop=win_stop, envs=envs,
                                     header=header)
        # 呼叫各彩種 投注data api
        r = FF_().session_post(em_url, '/gameBet/%s/submit' % lottery, json.dumps(postData), header)
        print('%s投注,彩種: %s' % (account, self.lottery_dict[lottery][0]))
        # print(r.json())
        try:
            print(r.json()['msg'])
            print(r.json()['data']['projectId'] + "\n")
        except KeyError as k:
            print(r.text)
            print(k)
        except Exception as e:
            from utils.TestTool import trace_log
            trace_log(e)
