from utils import Logger
from utils.Config import LotteryData

logger = Logger.create_logger(log_folder='/logger', log_name='requestContent_FF')

award_mode = 1


def get_game_dict(lottery, game_methods, _award_mode: int, money_unit: float):
    """
    依照提供的玩法搜尋頭住內容，並替換t_a_w組成 balls 參數，同時統計總投注金額供 amount 使用.
    :param money_unit: 注單元角分模式單位。Ex: 1, 0.1, 0.01
    :param lottery: 彩種ID，用以處理部分彩種同玩法不同內容的例外
    :param game_methods: array, 取自 m/gameBet/***/dynamicConfig 回傳的 [data]['gamelimit'] 的 key
    :param _award_mode: award_mode
    :return: Array[Data, amount]`
    """
    logger.debug(f'Func: requestContent_FF > get_game_dict, lottery={lottery},'
                 f'game_methods={game_methods}, _award_mode={_award_mode}, money_unit={money_unit}')
    data = []
    amount = 0
    for game_name in game_methods:
        if game_name in game_dict:
            import copy
            temp_data = copy.deepcopy(game_dict[game_name])  # 複製一份game_dict, 避免修改異動到game_dict原始內容
            if lottery not in LotteryData.lottery_sb:  # 骰寶系列投注內容無award_mode
                if '2000' not in temp_data['type'] and 'longhudou' not in temp_data['type']:  # 超級2000與趣味龍虎不支持高獎金
                    temp_data['awardMode'] = _award_mode
                if money_unit != 1:  # 若非元模式
                    temp_data['moneyunit'] = money_unit

            temp_data['ball'] = ball_fix(lottery, temp_data['ball'])

            data.append(temp_data)
            amount += temp_data["num"] * 2 * money_unit
    # logger.info(f'get_game_dict>>>>>>>   amount = {amount}')
    return [data, amount]


def get_game_dict_smp(lottery: str, _award_mode: int, bonus_list: dict, user_point):
    """
    取得投注內容功能，因含 odds 參數需塞入高獎金數據。
    當前僅提供PC蛋蛋，後續整合雙面盤。
    :param lottery: 彩種名稱
    :param _award_mode: 獎金模式開關 (1: 一般獎金 / 2: 高獎金)
    :param bonus_list: 理論獎金清單 dict。格式：{'玩法名稱': ['平台獎金', '理論獎金'],...,'玩法名稱2': ['平台獎金2', '理論獎金2']}
    :param user_point: 使用者返點。Ex. 0.015 = 1.5%
    :return:　
    """
    # logger.info(f'Func: requestContent_FF > get_game_dict_ptcc, is_pcdd={is_pcdd},'
    #              f'_award_mode={_award_mode}, bonus_list={bonus_list}, user_point={user_point}')

    import copy
    amount = 0
    _ball_data = []

    if lottery == 'pcdd':
        _game_dict = copy.deepcopy(game_dict_pcdd)  # 複製一份玩法內容避免影響後續測試
        for game in _game_dict:
            if game['odds'] in bonus_list:  # 若當前玩法匹配到對應返點資料
                game["awardMode"] = _award_mode
                amount += game["amount"]
                method_data = bonus_list[game['odds']]
                if _award_mode == 1:  # 一般玩法, odds 就直接用平台獎金
                    game["odds"] = method_data['ACTUAL_BONUS']
                else:
                    _bonus = method_data['ACTUAL_BONUS'] + method_data['LHC_THEORY_BONUS'] * user_point
                    import math
                    game["odds"] = math.floor(_bonus * 100) / 100  # 高獎金抓出來, 需乘上自己返點
                _ball_data.append(game)

    else:
        _game_dict = copy.deepcopy(game_dict_smp)  # 複製一份玩法內容避免影響後續測試
        for game in _game_dict:  # 逐一尋找目標玩法內容
            if game['type'] in bonus_list:  # 若目標玩法存在於雙面盤彩種列表中
                if lottery == 'shssl' and ('第四' in game['ball'] or '第五' in game['ball']):  # 上海時時彩排除選號中第四第五列
                    continue
                game["awardMode"] = _award_mode
                amount += game["amount"]
                if _award_mode == 1:
                    game['odds'] = bonus_list[game['type']]['ACTUAL_BONUS']
                    game['type'] = 'shuangmienpan.zonghe.longhuhe' if 'longhuhe' in game['type'] else game['type']
                else:
                    _bonus = bonus_list[game['type']]['ACTUAL_BONUS'] + bonus_list[game['type']]['THEORY_BONUS'] * user_point
                    import math
                    game['odds'] = math.floor(_bonus * 100) / 100
                    game['type'] = 'shuangmienpan.zonghe.longhuhe' if 'longhuhe' in game['type'] else game['type']
                _ball_data.append(game)

    return [_ball_data, amount]


def ball_fix(lottery, ball_data):
    """
    調整同玩法ball參數.
    :param lottery: 當前測試彩種名稱
    :param ball_data: 投注內容的ball字串，判斷是否需調整
    :return: 若需調整，回傳調整後的字串。若不需調整，回傳原本字串
    """
    if lottery in ['shssl', 'n3d', 'fc3d', 'v3d']:  # 上海時時彩僅有三號
        return {
            '-,-,3,6,4': '3,6,4',
            '-,-,-,3,6': '-,3,6',
            '-,-,-,-,-,-,-,-,龙,-': '-,龙,-',
            '-,-,-,-,1': '-,-,1',
            '2,9,-,-,-': '2,9,-'
        }.get(ball_data, ball_data)
    elif lottery in ['txffc', 'ptxffc']:  # 騰訊分分龍虎不開放萬位
        return {
            '-,-,-,-,-,-,-,-,龙,-': '-,-,-,-,龙,-',
        }.get(ball_data, ball_data)
    else:
        return ball_data


game_dict = {
    # 時時彩系列
    'daxiaodanshuang.dxds.houer': {"id": 106, "ball": "双,大", "type": "daxiaodanshuang.dxds.houer", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'daxiaodanshuang.dxds.houyi': {"id": 105, "ball": "小", "type": "daxiaodanshuang.dxds.houyi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'daxiaodanshuang.dxds.qianer': {"id": 104, "ball": "小,双", "type": "daxiaodanshuang.dxds.qianer", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'daxiaodanshuang.dxds.qianyi': {"id": 103, "ball": "小", "type": "daxiaodanshuang.dxds.qianyi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'daxiaodanshuang.dxds.zonghe': {"id": 102, "ball": "小", "type": "daxiaodanshuang.dxds.zonghe", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer.zhixuan.danshi': {"id": 72, "ball": "49", "type": "houer.zhixuan.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer.zhixuan.fushi': {"id": 71, "ball": "-,-,-,3,6", "type": "houer.zhixuan.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer.zhixuan.hezhi': {"id": 73, "ball": "5", "type": "houer.zhixuan.hezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 6},
    'houer.zhixuan.kuadu': {"id": 74, "ball": "3", "type": "houer.zhixuan.kuadu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 14},
    'houer.zuxuan.baodan': {"id": 78, "ball": "3", "type": "houer.zuxuan.baodan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 9},
    'houer.zuxuan.danshi': {"id": 76, "ball": "57", "type": "houer.zuxuan.danshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer.zuxuan.fushi': {"id": 75, "ball": "6,9", "type": "houer.zuxuan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer.zuxuan.hezhi': {"id": 77, "ball": "17", "type": "houer.zuxuan.hezhi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer_2000.zhixuan.danshi': {"id": 94, "ball": "65", "type": "houer_2000.zhixuan.danshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer_2000.zhixuan.fushi': {"id": 93, "ball": "-,-,-,5,9", "type": "houer_2000.zhixuan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer_2000.zhixuan.hezhi': {"id": 95, "ball": "14", "type": "houer_2000.zhixuan.hezhi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 5},
    'houer_2000.zhixuan.kuadu': {"id": 96, "ball": "5", "type": "houer_2000.zhixuan.kuadu", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 10},
    'houer_2000.zuxuan.baodan': {"id": 100, "ball": "8", "type": "houer_2000.zuxuan.baodan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 9},
    'houer_2000.zuxuan.danshi': {"id": 98, "ball": "25", "type": "houer_2000.zuxuan.danshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer_2000.zuxuan.fushi': {"id": 97, "ball": "1,8", "type": "houer_2000.zuxuan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer_2000.zuxuan.hezhi': {"id": 99, "ball": "13", "type": "houer_2000.zuxuan.hezhi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 3},
    'housan.budingwei.ermabudingwei': {"id": 62, "ball": "1,2", "type": "housan.budingwei.ermabudingwei", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan.budingwei.yimabudingwei': {"id": 61, "ball": "5", "type": "housan.budingwei.yimabudingwei", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan.zhixuan.danshi': {"id": 51, "ball": "561", "type": "housan.zhixuan.danshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan.zhixuan.fushi': {"id": 50, "ball": "-,-,3,6,4", "type": "housan.zhixuan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan.zhixuan.hezhi': {"id": 52, "ball": "9", "type": "housan.zhixuan.hezhi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 55},
    'housan.zhixuan.kuadu': {"id": 53, "ball": "3", "type": "housan.zhixuan.kuadu", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 126},
    'housan.zuxuan.baodan': {"id": 58, "ball": "9", "type": "housan.zuxuan.baodan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 54},
    'housan.zuxuan.hezhi': {"id": 54, "ball": "26", "type": "housan.zuxuan.hezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan.zuxuan.hunhezuxuan': {"id": 57, "ball": "125", "type": "housan.zuxuan.hunhezuxuan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan.zuxuan.zuliu': {"id": 56, "ball": "2,3,9", "type": "housan.zuxuan.zuliu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan.zuxuan.zuliudanshi': {"id": 60, "ball": "078", "type": "housan.zuxuan.zuliudanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan.zuxuan.zusan': {"id": 55, "ball": "1,2", "type": "housan.zuxuan.zusan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 2},
    'housan.zuxuan.zusandanshi': {"id": 59, "ball": "577", "type": "housan.zuxuan.zusandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan_2000.budingwei.ermabudingwei': {"id": 92, "ball": "2,7", "type": "housan_2000.budingwei.ermabudingwei", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan_2000.budingwei.yimabudingwei': {"id": 91, "ball": "7", "type": "housan_2000.budingwei.yimabudingwei", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan_2000.zhixuan.danshi': {"id": 94, "ball": "65", "type": "houer_2000.zhixuan.danshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan_2000.zhixuan.fushi': {"id": 93, "ball": "-,-,-,5,9", "type": "houer_2000.zhixuan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan_2000.zhixuan.hezhi': {"id": 95, "ball": "14", "type": "houer_2000.zhixuan.hezhi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 5},
    'housan_2000.zhixuan.kuadu': {"id": 96, "ball": "5", "type": "houer_2000.zhixuan.kuadu", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 10},
    'housan_2000.zuxuan.baodan': {"id": 100, "ball": "8", "type": "houer_2000.zuxuan.baodan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 9},
    'housan_2000.zuxuan.hezhi': {"id": 99, "ball": "13", "type": "houer_2000.zuxuan.hezhi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 3},
    'housan_2000.zuxuan.danshi': {"id": 98, "ball": "25", "type": "houer_2000.zuxuan.danshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan_2000.zuxuan.fushi': {"id": 97, "ball": "1,8", "type": "houer_2000.zhixuan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan_2000.zuxuan.hunhezuxuan': {"id": 87, "ball": "024", "type": "housan_2000.zuxuan.hunhezuxuan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan_2000.zuxuan.zuliu': {"id": 86, "ball": "2,5,9", "type": "housan_2000.zuxuan.zuliu", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan_2000.zuxuan.zuliudanshi': {"id": 90, "ball": "047", "type": "housan_2000.zuxuan.zuliudanshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'housan_2000.zuxuan.zusan': {"id": 85, "ball": "5,9", "type": "housan_2000.zuxuan.zusan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 2},
    'housan_2000.zuxuan.zusandanshi': {"id": 89, "ball": "336", "type": "housan_2000.zuxuan.zusandanshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'longhu.longhudou.fushi': {"id": 107, "ball": "-,-,-,-,-,-,-,-,龙,-", "type": "longhu.longhudou.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qianer.zhixuan.danshi': {"id": 16, "ball": "67", "type": "qianer.zhixuan.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qianer.zhixuan.fushi': {"id": 63, "ball": "2,9,-,-,-", "type": "qianer.zhixuan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qianer.zhixuan.hezhi': {"id": 65, "ball": "13", "type": "qianer.zhixuan.hezhi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 6},
    'qianer.zhixuan.kuadu': {"id": 66, "ball": "4", "type": "qianer.zhixuan.kuadu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 12},
    'qianer.zuxuan.baodan': {"id": 70, "ball": "7", "type": "qianer.zuxuan.baodan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 9},
    'qianer.zuxuan.danshi': {"id": 68, "ball": "27", "type": "qianer.zuxuan.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qianer.zuxuan.fushi': {"id": 67, "ball": "1,6", "type": "qianer.zuxuan.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qianer.zuxuan.hezhi': {"id": 69, "ball": "8", "type": "qianer.zuxuan.hezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 4},
    'qiansan.budingwei.ermabudingwei': {"id": 36, "ball": "1,2", "type": "qiansan.budingwei.ermabudingwei", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qiansan.budingwei.yimabudingwei': {"id": 35, "ball": "5", "type": "qiansan.budingwei.yimabudingwei", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qiansan.zhixuan.danshi': {"id": 25, "ball": "037", "type": "qiansan.zhixuan.danshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qiansan.zhixuan.fushi': {"id": 24, "ball": "9,6,9,-,-", "type": "qiansan.zhixuan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qiansan.zhixuan.hezhi': {"id": 26, "ball": "2", "type": "qiansan.zhixuan.hezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 6},
    'qiansan.zhixuan.kuadu': {"id": 27, "ball": "6", "type": "qiansan.zhixuan.kuadu", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 144},
    'qiansan.zuxuan.baodan': {"id": 32, "ball": "9", "type": "qiansan.zuxuan.baodan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 54},
    'qiansan.zuxuan.hezhi': {"id": 28, "ball": "14", "type": "qiansan.zuxuan.hezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 15},
    'qiansan.zuxuan.hunhezuxuan': {"id": 31, "ball": "159", "type": "qiansan.zuxuan.hunhezuxuan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qiansan.zuxuan.zuliu': {"id": 30, "ball": "0,5,7", "type": "qiansan.zuxuan.zuliu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qiansan.zuxuan.zuliudanshi': {"id": 34, "ball": "147", "type": "qiansan.zuxuan.zuliudanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qiansan.zuxuan.zusan': {"id": 29, "ball": "2,3", "type": "qiansan.zuxuan.zusan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 2},
    'qiansan.zuxuan.zusandanshi': {"id": 33, "ball": "599", "type": "qiansan.zuxuan.zusandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sixing.budingwei.ermabudingwei': {"id": 23, "ball": "1,9", "type": "sixing.budingwei.ermabudingwei", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sixing.budingwei.yimabudingwei': {"id": 22, "ball": "8", "type": "sixing.budingwei.yimabudingwei", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sixing.zhixuan.danshi': {"id": 17, "ball": "6266", "type": "sixing.zhixuan.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sixing.zhixuan.fushi': {"id": 16, "ball": "-,9,4,6,4", "type": "sixing.zhixuan.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sixing.zuxuan.zuxuan12': {"id": 19, "ball": "9,04", "type": "sixing.zuxuan.zuxuan12", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sixing.zuxuan.zuxuan24': {"id": 18, "ball": "3,4,5,8", "type": "sixing.zuxuan.zuxuan24", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sixing.zuxuan.zuxuan4': {"id": 21, "ball": "5,0", "type": "sixing.zuxuan.zuxuan4", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sixing.zuxuan.zuxuan6': {"id": 20, "ball": "6,7", "type": "sixing.zuxuan.zuxuan6", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.budingwei.ermabudingwei': {"id": 10, "ball": "3,7", "type": "wuxing.budingwei.ermabudingwei", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.budingwei.sanmabudingwei': {"id": 11, "ball": "3,4,8", "type": "wuxing.budingwei.sanmabudingwei", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.budingwei.yimabudingwei': {"id": 9, "ball": "6", "type": "wuxing.budingwei.yimabudingwei", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.quwei.haoshichengshuang': {"id": 13, "ball": "7", "type": "wuxing.quwei.haoshichengshuang", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.quwei.sanxingbaoxi': {"id": 14, "ball": "8", "type": "wuxing.quwei.sanxingbaoxi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.quwei.sijifacai': {"id": 15, "ball": "8", "type": "wuxing.quwei.sijifacai", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.quwei.yifanfengshun': {"id": 12, "ball": "4", "type": "wuxing.quwei.yifanfengshun", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.zhixuan.danshi': {"id": 2, "ball": "32077", "type": "wuxing.zhixuan.danshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.zhixuan.fushi': {"id": 1, "ball": "1,7,1,0,6", "type": "wuxing.zhixuan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.zuxuan.zuxuan10': {"id": 7, "ball": "0,4", "type": "wuxing.zuxuan.zuxuan10", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.zuxuan.zuxuan120': {"id": 3, "ball": "1,2,5,6,8", "type": "wuxing.zuxuan.zuxuan120", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.zuxuan.zuxuan20': {"id": 6, "ball": "4,79", "type": "wuxing.zuxuan.zuxuan20", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.zuxuan.zuxuan30': {"id": 5, "ball": "01,3", "type": "wuxing.zuxuan.zuxuan30", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.zuxuan.zuxuan5': {"id": 8, "ball": "2,7", "type": "wuxing.zuxuan.zuxuan5", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'wuxing.zuxuan.zuxuan60': {"id": 4, "ball": "4,078", "type": "wuxing.zuxuan.zuxuan60", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'yixing.dingweidan.fushi': {"id": 79, "ball": "-,-,-,-,1", "type": "yixing.dingweidan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'yixing_2000.dingweidan.fushi': {"id": 101, "ball": "-,3,-,-,-", "type": "yixing_2000.dingweidan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'zhongsan.budingwei.ermabudingwei': {"id": 49, "ball": "2,4", "type": "zhongsan.budingwei.ermabudingwei", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'zhongsan.budingwei.yimabudingwei': {"id": 48, "ball": "6", "type": "zhongsan.budingwei.yimabudingwei", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'zhongsan.zhixuan.danshi': {"id": 38, "ball": "402", "type": "zhongsan.zhixuan.danshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'zhongsan.zhixuan.fushi': {"id": 37, "ball": "-,5,2,4,-", "type": "zhongsan.zhixuan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'zhongsan.zhixuan.hezhi': {"id": 39, "ball": "17", "type": "zhongsan.zhixuan.hezhi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 63},
    'zhongsan.zhixuan.kuadu': {"id": 40, "ball": "7", "type": "zhongsan.zhixuan.kuadu", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 126},
    'zhongsan.zuxuan.baodan': {"id": 45, "ball": "2", "type": "zhongsan.zuxuan.baodan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 54},
    'zhongsan.zuxuan.hezhi': {"id": 41, "ball": "20", "type": "zhongsan.zuxuan.hezhi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 8},
    'zhongsan.zuxuan.hunhezuxuan': {"id": 44, "ball": "018", "type": "zhongsan.zuxuan.hunhezuxuan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'zhongsan.zuxuan.zuliu': {"id": 43, "ball": "0,4,9", "type": "zhongsan.zuxuan.zuliu", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'zhongsan.zuxuan.zuliudanshi': {"id": 47, "ball": "179", "type": "zhongsan.zuxuan.zuliudanshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'zhongsan.zuxuan.zusan': {"id": 42, "ball": "0,9", "type": "zhongsan.zuxuan.zusan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 2},
    'zhongsan.zuxuan.zusandanshi': {"id": 46, "ball": "002", "type": "zhongsan.zuxuan.zusandanshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    # 快三
    'erbutonghao.biaozhun.biaozhuntouzhu': {"id": 8, "ball": "2,4", "type": "erbutonghao.biaozhun.biaozhuntouzhu", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    # 'erbutonghao.biaozhun.dantuotouzhu': {},
    'ertonghaodanxuan.ertonghaodanxuan.ertonghaodanxuan': {"id": 7, "ball": "11#3", "type": "ertonghaodanxuan.ertonghaodanxuan.ertonghaodanxuan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'ertonghaofuxuan.ertonghaofuxuan.ertonghaofuxuan': {"id": 6, "ball": "55*", "type": "ertonghaofuxuan.ertonghaofuxuan.ertonghaofuxuan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'hezhi.hezhi.hezhi': {"id": 1, "ball": "14", "type": "hezhi.hezhi.hezhi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sanbutonghao.biaozhun.biaozhuntouzhu': {"id": 4, "ball": "1,2,6", "type": "sanbutonghao.biaozhun.biaozhuntouzhu", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    # 'sanbutonghao.biaozhun.dantuotouzhu': {},
    'sanlianhaotongxuan.sanlianhaotongxuan.sanlianhaotongxuan': {"id": 5, "ball": "123 234 345 456", "type": "sanlianhaotongxuan.sanlianhaotongxuan.sanlianhaotongxuan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'santonghaodanxuan.santonghaodanxuan.santonghaodanxuan': {"id": 3, "ball": "111", "type": "santonghaodanxuan.santonghaodanxuan.santonghaodanxuan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'santonghaotongxuan.santonghaotongxuan.santonghaotongxuan': {"id": 2, "ball": "111 222 333 444 555 666", "type": "santonghaotongxuan.santonghaotongxuan.santonghaotongxuan", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'yibutonghao.yibutonghao.yibutonghao': {"id": 9, "ball": "6", "type": "yibutonghao.yibutonghao.yibutonghao", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    # 115
    'quwei.normal.caizhongwei': {"id": 37, "ball": "03", "type": "quwei.normal.caizhongwei", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'quwei.normal.dingdanshuang': {"id": 36, "ball": "4单1双", "type": "quwei.normal.dingdanshuang", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanba.renxuanbazhongwu.danshi': {"id": 34, "ball": "01 03 05 06 08 09 10 11", "type": "xuanba.renxuanbazhongwu.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanba.renxuanbazhongwu.dantuo': {"id": 35, "ball": "[胆02]  01,05,06,08,09,10,11", "type": "xuanba.renxuanbazhongwu.dantuo", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanba.renxuanbazhongwu.fushi': {"id": 33, "ball": "01,02,03,05,06,07,08,10", "type": "xuanba.renxuanbazhongwu.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuaner.qianerzhixuan.zhixuandanshi': {"id": 6, "ball": "02 04", "type": "xuaner.qianerzhixuan.zhixuandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuaner.qianerzhixuan.zhixuanfushi': {"id": 5, "ball": "07,02,-,-,-", "type": "xuaner.qianerzhixuan.zhixuanfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuaner.qianerzuxuan.zuxuandanshi': {"id": 8, "ball": "06 07", "type": "xuaner.qianerzuxuan.zuxuandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuaner.qianerzuxuan.zuxuandantuo': {"id": 9, "ball": "[胆 01] 08", "type": "xuaner.qianerzuxuan.zuxuandantuo", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuaner.qianerzuxuan.zuxuanfushi': {"id": 7, "ball": "02,03", "type": "xuaner.qianerzuxuan.zuxuanfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuaner.renxuanerzhonger.renxuandanshi': {"id": 11, "ball": "09 10", "type": "xuaner.renxuanerzhonger.renxuandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuaner.renxuanerzhonger.renxuandantuo': {"id": 12, "ball": "[胆 10] 09", "type": "xuaner.renxuanerzhonger.renxuandantuo", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuaner.renxuanerzhonger.renxuanfushi': {"id": 10, "ball": "02,06", "type": "xuaner.renxuanerzhonger.renxuanfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanliu.renxuanliuzhongwu.danshi': {"id": 28, "ball": "01 04 05 07 09 10", "type": "xuanliu.renxuanliuzhongwu.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanliu.renxuanliuzhongwu.dantuo': {"id": 29, "ball": "[胆10]  01,03,06,08,09", "type": "xuanliu.renxuanliuzhongwu.dantuo", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanliu.renxuanliuzhongwu.fushi': {"id": 27, "ball": "01,03,05,06,09,10", "type": "xuanliu.renxuanliuzhongwu.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanqi.renxuanqizhongwu.danshi': {"id": 31, "ball": "01 02 04 05 06 10 11", "type": "xuanqi.renxuanqizhongwu.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanqi.renxuanqizhongwu.dantuo': {"id": 32, "ball": "[胆01]  04,05,08,09,10,11", "type": "xuanqi.renxuanqizhongwu.dantuo", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanqi.renxuanqizhongwu.fushi': {"id": 30, "ball": "02,03,06,08,09,10,11", "type": "xuanqi.renxuanqizhongwu.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuansan.qiansanzhixuan.zhixuandanshi': {"id": 14, "ball": "08 09 06", "type": "xuansan.qiansanzhixuan.zhixuandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuansan.qiansanzhixuan.zhixuanfushi': {"id": 13, "ball": "10,01,02,-,-", "type": "xuansan.qiansanzhixuan.zhixuanfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuansan.qiansanzuxuan.zuxuandanshi': {"id": 16, "ball": "01 04 09", "type": "xuansan.qiansanzuxuan.zuxuandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuansan.qiansanzuxuan.zuxuandantuo': {"id": 17, "ball": "[胆02]  06,08", "type": "xuansan.qiansanzuxuan.zuxuandantuo", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuansan.qiansanzuxuan.zuxuanfushi': {"id": 15, "ball": "03,08,09", "type": "xuansan.qiansanzuxuan.zuxuanfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuansan.renxuansanzhongsan.renxuandanshi': {"id": 19, "ball": "01 07 08", "type": "xuansan.renxuansanzhongsan.renxuandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuansan.renxuansanzhongsan.renxuandantuo': {"id": 20, "ball": "[胆02]  01,11", "type":  "xuansan.renxuansanzhongsan.renxuandantuo", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuansan.renxuansanzhongsan.renxuanfushi': {"id": 18, "ball": "02,05,10", "type": "xuansan.renxuansanzhongsan.renxuanfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuansi.renxuansizhongsi.danshi': {"id": 22, "ball": "03 07 08 10", "type": "xuansi.renxuansizhongsi.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuansi.renxuansizhongsi.dantuo': {"id": 23, "ball": "[胆10]  03,08,09", "type": "xuansi.renxuansizhongsi.dantuo", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuansi.renxuansizhongsi.fushi': {"id": 21, "ball": "02,03,04,06", "type": "xuansi.renxuansizhongsi.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanwu.renxuanwuzhongwu.danshi': {"id": 25, "ball": "01 03 06 07 09", "type": "xuanwu.renxuanwuzhongwu.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanwu.renxuanwuzhongwu.dantuo': {"id": 26, "ball": "[胆10]  01,05,07,11", "type": "xuanwu.renxuanwuzhongwu.dantuo", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanwu.renxuanwuzhongwu.fushi': {"id": 24, "ball": "03,04,06,09,11", "type": "xuanwu.renxuanwuzhongwu.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanyi.dingweidan.fushi': {"id": 2, "ball": "04,-,-,-,-", "type": "xuanyi.dingweidan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanyi.qiansanyimabudingwei.fushi': {"id": 1, "ball": "02", "type": "xuanyi.qiansanyimabudingwei.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanyi.renxuanyizhongyi.danshi': {"id": 4, "ball": "05", "type": "xuanyi.renxuanyizhongyi.danshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'xuanyi.renxuanyizhongyi.fushi': {"id": 3, "ball": "05", "type": "xuanyi.renxuanyizhongyi.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    # 趣味
    'caipaiwei.dingweidan.houfushi': {"id": 22, "ball": "-,-,-,-,-,01 02 03 04 05,01 02 03 04 05,01 02 03 04 05,01 02 03 04 05,01 02 03 04 05", "type": "caipaiwei.dingweidan.houfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 50, "num": 25},
    # 'daxiaodanshuang.dxds.fushi': {},
    'guanya.caiguanya.danshi': {"id": 6, "ball": "01 02", "type": "guanya.caiguanya.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 2, "num": 1},
    'guanya.caiguanya.fushi': {"id": 5, "ball": "01 02 03 04 05,01 02 03 04 05,-,-,-,-,-,-,-,-", "type": "guanya.caiguanya.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 40, "num": 20},
    'guanya.hezhi.fushi': {"id": 4, "ball": "3,4,5,6,7,8,9,10,11", "type": "guanya.hezhi.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 100, "num": 50},
    'guanya.zhixuan.danshi': {"id": 1, "ball": "01 02", "type": "guanya.zhixuan.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 2, "num": 1},
    # 'guanya.zhixuan.fushi': {},
    'guanya.zuxuan.danshi': {"id": 3, "ball": "01 02", "type": "guanya.zuxuan.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 2, "num": 1},
    'guanya.zuxuan.fushi': {"id": 2, "ball": "01,02,03,04,05", "type": "guanya.zuxuan.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 20, "num": 10},
    'guanyaji.caiguanyaji.danshi': {"id": 12, "ball": "05 06 07", "type": "guanyaji.caiguanyaji.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 2, "num": 1},
    'guanyaji.caiguanyaji.fushi': {"id": 11, "ball": "01 02 03 04 05,01 02 03 04 05,01 02 03 04 05,-,-,-,-,-,-,-", "type": "guanyaji.caiguanyaji.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 120, "num": 60},
    'guanyaji.zhixuan.danshi': {"id": 8, "ball": "05 06 07", "type": "guanyaji.zhixuan.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 2, "num": 1},
    'guanyaji.zhixuan.fushi': {"id": 7, "ball": "01 02 03 04 05,01 02 03 04 05,01 02 03 04 05,-,-,-,-,-,-,-", "type": "guanyaji.zhixuan.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 120, "num": 60},
    'guanyaji.zuxuan.danshi': {"id": 10, "ball": "05 06 07", "type": "guanyaji.zuxuan.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 2, "num": 1},
    'guanyaji.zuxuan.fushi': {"id": 9, "ball": "01,02,03,04,05", "type": "guanyaji.zuxuan.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 20, "num": 10},
    'qiansi.zhixuan.danshi': {"id": 14, "ball": "06 07 08 09", "type": "qiansi.zhixuan.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 2, "num": 1},
    'qiansi.zuxuan.fushi': {"id": 15, "ball": "02,04,06,08,10", "type": "qiansi.zuxuan.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 10, "num": 5},
    'qianwu.zhixuan.danshi': {"id": 18, "ball": "01 04 05 06 07", "type": "qianwu.zhixuan.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 2, "num": 1},
    'qianwu.zhixuan.fushi': {"id": 17, "ball": "02 04 06 08 10,02 04 06 08 10,02 04 06 08 10,02 04 06 08 10,02 04 06 08 10,-,-,-,-,-", "type": "qianwu.zhixuan.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 240, "num": 120},
    'qianwu.zuxuan.danshi': {"id": 20, "ball": "02 06 07 08 09", "type": "qianwu.zuxuan.danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 2, "num": 1},
    'qianwu.zuxuan.fushi': {"id": 19, "ball": "06,07,08,09,10", "type": "qianwu.zuxuan.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "amount": 2, "num": 1},
    # 'longhu.lh.fushi': {"id":1,"ball":"第四名龙","type":"longhu.lh.fushi","moneyunit":1,"multiple":1,"awardMode":2,"amount":1,"num":1,"odds":1.96},
    # 沖天炮
    'chungtienpao.chungtienpao.chungtienpao': {"id": 1, "ball": "1.01", "type": "chungtienpao.chungtienpao.chungtienpao", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    # 北京快樂8
    'quwei.panmian.quweib': {"id": 1, "ball": "中", "type": "quwei.panmian.quweib", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'renxuan.putongwanfa.renxuan1': {"id": 2, "ball": "25", "type": "renxuan.putongwanfa.renxuan1", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'renxuan.putongwanfa.renxuan2': {"id": 3, "ball": "48,74", "type": "renxuan.putongwanfa.renxuan2", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'renxuan.putongwanfa.renxuan3': {"id": 4, "ball": "16,52,79", "type": "renxuan.putongwanfa.renxuan3", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'renxuan.putongwanfa.renxuan4': {"id": 5, "ball": "03,14,51,57", "type": "renxuan.putongwanfa.renxuan4", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'renxuan.putongwanfa.renxuan5': {"id": 6, "ball": "24,29,39,50,71", "type": "renxuan.putongwanfa.renxuan5", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'renxuan.putongwanfa.renxuan6': {"id": 7, "ball": "12,28,54,64,69,80", "type": "renxuan.putongwanfa.renxuan6", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'renxuan.putongwanfa.renxuan7': {"id": 8, "ball": "05,25,42,43,51,67,80", "type": "renxuan.putongwanfa.renxuan7", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    # 3D系列
    'houer.zhixuan.zhixuandanshi': {"id": 23, "ball": "58", "type": "houer.zhixuan.zhixuandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer.zhixuan.zhixuanfushi': {"id": 23, "ball": "58", "type": "houer.zhixuan.zhixuandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer.zhixuan.zhixuanhezhi': {"id": 24, "ball": "6", "type": "houer.zhixuan.zhixuanhezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 7},
    'houer.zhixuan.zhixuankuadu': {"id": 25, "ball": "1", "type": "houer.zhixuan.zhixuankuadu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 18},
    'houer.zuxuan.zuxuanbaodan': {"id": 29, "ball": "6", "type": "houer.zuxuan.zuxuanbaodan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 9},
    'houer.zuxuan.zuxuandanshi': {"id": 27, "ball": "28", "type": "houer.zuxuan.zuxuandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer.zuxuan.zuxuanfushi': {"id": 26, "ball": "6,8", "type": "houer.zuxuan.zuxuanfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'houer.zuxuan.zuxuanhezhi': {"id": 28, "ball": "12", "type": "houer.zuxuan.zuxuanhezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 3},
    'qianer.zhixuan.zhixuandanshi': {"id": 15, "ball": "23", "type": "qianer.zhixuan.zhixuandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qianer.zhixuan.zhixuanfushi': {"id": 14, "ball": "1,0,-", "type": "qianer.zhixuan.zhixuanfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qianer.zhixuan.zhixuanhezhi': {"id": 16, "ball": "11", "type": "qianer.zhixuan.zhixuanhezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 8},
    'qianer.zhixuan.zhixuankuadu': {"id": 17, "ball": "1", "type": "qianer.zhixuan.zhixuankuadu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 18},
    'qianer.zuxuan.zuxuanbaodan': {"id": 21, "ball": "3", "type": "qianer.zuxuan.zuxuanbaodan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 9},
    'qianer.zuxuan.zuxuandanshi': {"id": 19, "ball": "05", "type": "qianer.zuxuan.zuxuandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qianer.zuxuan.zuxuanfushi': {"id": 18, "ball": "1,7", "type": "qianer.zuxuan.zuxuanfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'qianer.zuxuan.zuxuanhezhi': {"id": 20, "ball": "11", "type": "qianer.zuxuan.zuxuanhezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 4},
    'sanxing.budingwei.ermabudingwei': {"id": 13, "ball": "4,7", "type": "sanxing.budingwei.ermabudingwei", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sanxing.budingwei.yimabudingwei': {"id": 12, "ball": "3", "type": "sanxing.budingwei.yimabudingwei", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sanxing.zhixuan.danshi': {"id": 2, "ball": "126", "type": "sanxing.zhixuan.danshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sanxing.zhixuan.fushi': {"id": 1, "ball": "4,4,3", "type": "sanxing.zhixuan.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sanxing.zhixuan.hezhi': {"id": 3, "ball": "25", "type": "sanxing.zhixuan.hezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 6},
    'sanxing.zhixuan.kuadu': {"id": 4, "ball": "6", "type": "sanxing.zhixuan.kuadu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 144},
    'sanxing.zuxuan.hunhezuxuan': {"id": 8, "ball": "248", "type": "sanxing.zuxuan.hunhezuxuan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sanxing.zuxuan.zuliu': {"id": 7, "ball": "3,7,8", "type": "sanxing.zuxuan.zuliu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sanxing.zuxuan.zuliudanshi': {"id": 11, "ball": "235", "type": "sanxing.zuxuan.zuliudanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sanxing.zuxuan.zusan': {"id": 6, "ball": "5,7", "type": "sanxing.zuxuan.zusan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 2},
    'sanxing.zuxuan.zusandanshi': {"id": 10, "ball": "388", "type": "sanxing.zuxuan.zusandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'sanxing.zuxuan.zuxuanbaodan': {"id": 9, "ball": "1", "type": "sanxing.zuxuan.zuxuanbaodan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 54},
    'sanxing.zuxuan.zuxuanhezhi': {"id": 5, "ball": "6", "type": "sanxing.zuxuan.zuxuanhezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 6},
    # 骰寶
    # 'caibuchu':
    'danshuang': {"ball": "单", "id": 1, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5, "type": "danshuang.danshuang"},
    'daxiao': {"ball": "大", "id": 0, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5, "type": "daxiao.daxiao"},
    'erbutonghao': {"ball": "5,6", "id": 31, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5, "type": "erbutonghao.erbutonghao"},
    'ertonghaofuxuan': {"ball": "66*", "id": 2, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5, "type": "ertonghaofuxuan.ertonghaofuxuan"},
    'hezhi': {"ball": "9", "id": 25, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5, "type": "hezhi.hezhi"},
    'santonghaodanxuan': {"ball": "444", "id": 7, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5, "type": "santonghaodanxuan.santonghaodanxuan"},
    'santonghaotongxuan': {"ball": "111 222 333 444 555 666", "id": 11, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5, "type": "santonghaotongxuan.santonghaotongxuan"},
    'yibutonghao': {"ball": "5", "id": 47, "moneyunit": 1, "multiple": 1, "amount": 10, "num": 5, "type": "yibutonghao.yibutonghao"},
    # 排列5
    'p3houer.zhixuan.zhixuanp3houerdanshi': {"id": 32, "ball": "02", "type": "p3houer.zhixuan.zhixuanp3houerdanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3houer.zhixuan.zhixuanp3houerfushi': {"id": 31, "ball": "-,2,7", "type": "p3houer.zhixuan.zhixuanp3houerfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3houer.zhixuan.zhixuanp3houerhezhi': {"id": 33, "ball": "5", "type": "p3houer.zhixuan.zhixuanp3houerhezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 6},
    'p3houer.zhixuan.zhixuanp3houerkuadu': {"id": 34, "ball": "9", "type": "p3houer.zhixuan.zhixuanp3houerkuadu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 2},
    'p3houer.zuxuan.zuxuanp3houerbaodan': {"id": 38, "ball": "2", "type": "p3houer.zuxuan.zuxuanp3houerbaodan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 9},
    'p3houer.zuxuan.zuxuanp3houerdanshi': {"id": 36, "ball": "38", "type": "p3houer.zuxuan.zuxuanp3houerdanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3houer.zuxuan.zuxuanp3houerfushi': {"id": 35, "ball": "0,7", "type": "p3houer.zuxuan.zuxuanp3houerfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3houer.zuxuan.zuxuanp3houerhezhi': {"id": 37, "ball": "6", "type": "p3houer.zuxuan.zuxuanp3houerhezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 3},
    'p3qianer.zhixuan.zhixuanp3qianerdanshi': {"id": 24, "ball": "48", "type": "p3qianer.zhixuan.zhixuanp3qianerdanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3qianer.zhixuan.zhixuanp3qianerfushi': {"id": 23, "ball": "7,2,-", "type": "p3qianer.zhixuan.zhixuanp3qianerfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3qianer.zhixuan.zhixuanp3qianerhezhi': {"id": 25, "ball": "18", "type": "p3qianer.zhixuan.zhixuanp3qianerhezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3qianer.zhixuan.zhixuanp3qianerkuadu': {"id": 26, "ball": "3", "type": "p3qianer.zhixuan.zhixuanp3qianerkuadu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 14},
    'p3qianer.zuxuan.zuxuanp3qianerbaodan': {"id": 30, "ball": "2", "type": "p3qianer.zuxuan.zuxuanp3qianerbaodan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 9},
    'p3qianer.zuxuan.zuxuanp3qianerdanshi': {"id": 28, "ball": "67", "type": "p3qianer.zuxuan.zuxuanp3qianerdanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3qianer.zuxuan.zuxuanp3qianerfushi': {"id": 27, "ball": "2,5", "type": "p3qianer.zuxuan.zuxuanp3qianerfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3qianer.zuxuan.zuxuanp3qianerhezhi': {"id": 29, "ball": "7", "type": "p3qianer.zuxuan.zuxuanp3qianerhezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 4},
    'p3sanxing.budingwei.ermabudingwei': {"id": 22, "ball": "3,8", "type": "p3sanxing.budingwei.ermabudingwei", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3sanxing.budingwei.yimabudingwei': {"id": 21, "ball": "1", "type": "p3sanxing.budingwei.yimabudingwei", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3sanxing.zhixuan.p3danshi': {"id": 11, "ball": "249", "type": "p3sanxing.zhixuan.p3danshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3sanxing.zhixuan.p3fushi': {"id": 10, "ball": "7,1,9", "type": "p3sanxing.zhixuan.p3fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3sanxing.zhixuan.p3hezhi': {"id": 12, "ball": "27", "type": "p3sanxing.zhixuan.p3hezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3sanxing.zhixuan.p3kuadu': {"id": 13, "ball": "0", "type": "p3sanxing.zhixuan.p3kuadu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 10},
    'p3sanxing.zuxuan.p3hunhezuxuan': {"id": 17, "ball": "179", "type": "p3sanxing.zuxuan.p3hunhezuxuan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3sanxing.zuxuan.p3zuliu': {"id": 16, "ball": "1,3,9", "type": "p3sanxing.zuxuan.p3zuliu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3sanxing.zuxuan.p3zuliudanshi': {"id": 20, "ball": "279", "type": "p3sanxing.zuxuan.p3zuliudanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3sanxing.zuxuan.p3zusan': {"id": 15, "ball": "7,8", "type": "p3sanxing.zuxuan.p3zusan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 2},
    'p3sanxing.zuxuan.p3zusandanshi': {"id": 19, "ball": "229", "type": "p3sanxing.zuxuan.p3zusandanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p3sanxing.zuxuan.p3zuxuanbaodan': {"id": 18, "ball": "6", "type": "p3sanxing.zuxuan.p3zuxuanbaodan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 54},
    'p3sanxing.zuxuan.p3zuxuanhezhi': {"id": 14, "ball": "23", "type": "p3sanxing.zuxuan.p3zuxuanhezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 4},
    'p5houer.zhixuan.zhixuanp5houerdanshi': {"id": 2, "ball": "64", "type": "p5houer.zhixuan.zhixuanp5houerdanshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p5houer.zhixuan.zhixuanp5houerfushi': {"id": 1, "ball": "-,-,-,7,4", "type": "p5houer.zhixuan.zhixuanp5houerfushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p5houer.zhixuan.zhixuanp5houerhezhi': {"id": 3, "ball": "14", "type": "p5houer.zhixuan.zhixuanp5houerhezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 5},
    'p5houer.zhixuan.zhixuanp5houerkuadu': {"id": 4, "ball": "4", "type": "p5houer.zhixuan.zhixuanp5houerkuadu", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 12},
    'p5houer.zuxuan.zuxuanp5houerbaodan': {"id": 8, "ball": "7", "type": "p5houer.zuxuan.zuxuanp5houerbaodan", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 9},
    'p5houer.zuxuan.zuxuanp5houerdanshi': {"id": 6, "ball": "03", "type": "p5houer.zuxuan.zuxuanp5houerdanshi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p5houer.zuxuan.zuxuanp5houerfushi': {"id": 5, "ball": "3,4", "type": "p5houer.zuxuan.zuxuanp5houerfushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'p5houer.zuxuan.zuxuanp5houerhezhi': {"id": 7, "ball": "9", "type": "p5houer.zuxuan.zuxuanp5houerhezhi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 5},
    'p5yixing.dingweidan.fushi': {"id": 9, "ball": "-,-,2,-,-", "type": "p5yixing.dingweidan.fushi", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    # 雙色球
    'biaozhuntouzhu.biaozhun.danshi': {"id": 2, "ball": "08,17,19,22,24,33+07", "type": "biaozhuntouzhu.biaozhun.danshi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'biaozhuntouzhu.biaozhun.dantuo': {"id": 3, "ball": "D: 18_T:01,03,06,26,33+13", "type": "biaozhuntouzhu.biaozhun.dantuo", "moneyunit": 1, "multiple": 1, "awardMode": award_mode, "num": 1},
    'biaozhuntouzhu.biaozhun.fushi': {"id": 1, "ball": "10,15,18,23,24,31+05", "type": "biaozhuntouzhu.biaozhun.fushi", "moneyunit":  1, "multiple": 1, "awardMode": award_mode, "num": 1}
    # 蛋蛋

}

game_dict_pcdd = [
    {"id": 1, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "0", "odds": 'HEZHI0', "awardMode": award_mode},
    {"id": 2, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "1", "odds": 'HEZHI1', "awardMode": award_mode},
    {"id": 3, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "2", "odds": 'HEZHI2', "awardMode": award_mode},
    {"id": 4, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "3", "odds": 'HEZHI3', "awardMode": award_mode},
    {"id": 6, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "4", "odds": 'HEZHI4', "awardMode": award_mode},
    {"id": 5, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "5", "odds": 'HEZHI5', "awardMode": award_mode},
    {"id": 7, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "6", "odds": 'HEZHI6', "awardMode": award_mode},
    {"id": 8, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "7", "odds": 'HEZHI7', "awardMode": award_mode},
    {"id": 9, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "8", "odds": 'HEZHI8', "awardMode": award_mode},
    {"id": 10, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "9", "odds": 'HEZHI9', "awardMode": award_mode},
    {"id": 11, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "10", "odds": 'HEZHI10', "awardMode": award_mode},
    {"id": 12, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "11", "odds": 'HEZHI11', "awardMode": award_mode},
    {"id": 13, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "12", "odds": 'HEZHI12', "awardMode": award_mode},
    {"id": 14, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "13", "odds": 'HEZHI13', "awardMode": award_mode},
    {"id": 15, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "14", "odds": 'HEZHI14', "awardMode": award_mode},
    {"id": 16, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "15", "odds": 'HEZHI15', "awardMode": award_mode},
    {"id": 17, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "16", "odds": 'HEZHI16', "awardMode": award_mode},
    {"id": 18, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "17", "odds": 'HEZHI17', "awardMode": award_mode},
    {"id": 19, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "18", "odds": 'HEZHI18', "awardMode": award_mode},
    {"id": 20, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1,"ball": "19", "odds": 'HEZHI19', "awardMode": award_mode},
    {"id": 21, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "20", "odds": 'HEZHI20', "awardMode": award_mode},
    {"id": 22, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "21", "odds": 'HEZHI21', "awardMode": award_mode},
    {"id": 23, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "22", "odds": 'HEZHI22', "awardMode": award_mode},
    {"id": 24, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "23", "odds": 'HEZHI23', "awardMode": award_mode},
    {"id": 25, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "24", "odds": 'HEZHI24', "awardMode": award_mode},
    {"id": 26, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "25", "odds": 'HEZHI25', "awardMode": award_mode},
    {"id": 27, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "26", "odds": 'HEZHI26', "awardMode": award_mode},
    {"id": 28, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.hezhi.hezhi", "amount": 1, "ball": "27", "odds": 'HEZHI27', "awardMode": award_mode},
    {"id": 29, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.quwei.baosan", "amount": 1, "ball": "0,1,2", "odds": 'BAOSAN', "awardMode": award_mode},
    {"id": 30, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.quwei.saibo", "amount": 1, "ball": "红", "odds": 'RED', "awardMode": award_mode},
    {"id": 31, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.quwei.saibo", "amount": 1, "ball": "绿", "odds": 'GREEN', "awardMode": award_mode},
    {"id": 32, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.quwei.baozi", "amount": 1, "ball": "豹子", "odds": 'BAOZI', "awardMode": award_mode},
    {"id": 33, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.quwei.saibo", "amount": 1, "ball": "蓝", "odds": 'BLUE', "awardMode": award_mode},
    {"id": 34, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.jizhi", "amount": 1, "ball": "极小", "odds": 'JIXIAO', "awardMode": award_mode},
    {"id": 35, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.zuhedaxiaodanshuang", "amount": 1, "ball": "大单", "odds": 'DADAN', "awardMode": award_mode},
    {"id": 36, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.zuhedaxiaodanshuang", "amount": 1, "ball": "大双", "odds": 'DASHUNG', "awardMode": award_mode},
    {"id": 37, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.jizhi", "amount": 1, "ball": "极大", "odds": 'JIDA', "awardMode": award_mode},
    {"id": 38, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.zuhedaxiaodanshuang", "amount": 1, "ball": "小单", "odds": 'XIAODAN', "awardMode": award_mode},
    {"id": 39, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.zuhedaxiaodanshuang", "amount": 1, "ball": "小双", "odds": 'XIAOSHUNG', "awardMode": award_mode},
    {"id": 40, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.daxiaodanshuang", "amount": 1, "ball": "双", "odds": 'SHUNG', "awardMode": award_mode},
    {"id": 41, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.daxiaodanshuang", "amount": 1, "ball": "单", "odds": 'DAN', "awardMode": award_mode},
    {"id": 42, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.daxiaodanshuang", "amount": 1, "ball": "小", "odds": 'XIAO', "awardMode": award_mode},
    {"id": 43, "moneyunit": 1, "multiple": 1, "num": 1, "type": "zhenghe.shuangmian.daxiaodanshuang", "amount": 1, "ball": "大", "odds": 'DA', "awardMode": award_mode}
]

game_dict_smp = [
    {"id": 1, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.zonghe.daxiao", "amount": 3, "ball": "大", "odds": 1.98, "awardMode": 2},
    {"id": 2, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第一球7", "odds": 9.9, "awardMode": 2},
    {"id": 3, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.danshuang", "amount": 3, "ball": "第一球双", "odds": 1.98, "awardMode": 2},
    {"id": 4, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.danshuang", "amount": 3, "ball": "第三球单", "odds": 1.98, "awardMode": 2},
    {"id": 5, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.daxiao", "amount": 3, "ball": "第四球小", "odds": 1.98, "awardMode": 2},
    {"id": 6, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第四球7", "odds": 9.9, "awardMode": 2},
    {"id": 7, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第五球8", "odds": 9.9, "awardMode": 2},
    {"id": 8, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第一球8", "odds": 9.9, "awardMode": 2},
    {"id": 9, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第一球4", "odds": 9.9, "awardMode": 2},
    {"id": 10, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第一球1", "odds": 9.9, "awardMode": 2},
    {"id": 11, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.daxiao", "amount": 3, "ball": "第一球大", "odds": 1.98, "awardMode": 2},
    {"id": 12, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.zonghe.danshuang", "amount": 3, "ball": "单", "odds": 1.98, "awardMode": 2},
    {"id": 13, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第五球9", "odds": 9.9, "awardMode": 2},
    {"id": 14, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第一球0", "odds": 9.9, "awardMode": 2},
    {"id": 15, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第二球3", "odds": 9.9, "awardMode": 2},
    {"id": 16, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第一球2", "odds": 9.9, "awardMode": 2},
    {"id": 17, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.danshuang", "amount": 3, "ball": "第三球双", "odds": 1.98, "awardMode": 2},
    {"id": 18, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第四球0", "odds": 9.9, "awardMode": 2},
    {"id": 19, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第二球4", "odds": 9.9, "awardMode": 2},
    {"id": 20, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第三球1", "odds": 9.9, "awardMode": 2},
    {"id": 21, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.zonghe.danshuang", "amount": 3, "ball": "双", "odds": 1.98, "awardMode": 2},
    {"id": 22, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.danshuang", "amount": 3, "ball": "第二球双", "odds": 1.98, "awardMode": 2},
    {"id": 23, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.qiansan.banshun", "amount": 3, "ball": "半顺", "odds": 2.27, "awardMode": 2},
    {"id": 24, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第二球5", "odds": 9.9, "awardMode": 2},
    {"id": 25, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第三球9", "odds": 9.9, "awardMode": 2},
    {"id": 26, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第一球3", "odds": 9.9, "awardMode": 2},
    {"id": 27, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.zhongsan.shunzi", "amount": 3, "ball": "顺子", "odds": 15.84, "awardMode": 2},
    {"id": 28, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.zonghe.daxiao", "amount": 3, "ball": "小", "odds": 1.98, "awardMode": 2},
    {"id": 29, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第四球3", "odds": 9.9, "awardMode": 2},
    {"id": 30, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第五球3", "odds": 9.9, "awardMode": 2},
    {"id": 31, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.housan.duizi", "amount": 3, "ball": "对子", "odds": 3.46, "awardMode": 2},
    {"id": 32, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.zhongsan.duizi", "amount": 3, "ball": "对子", "odds": 3.46, "awardMode": 2},
    {"id": 33, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.zonghe.longhuhe_70", "amount": 3, "ball": "龙", "odds": 2.19, "awardMode": 2},
    {"id": 34, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.zonghe.longhuhe_71", "amount": 3, "ball": "和", "odds": 9.9, "awardMode": 2},
    {"id": 35, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第二球9", "odds": 9.9, "awardMode": 2},
    {"id": 36, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第五球0", "odds": 9.9, "awardMode": 2},
    {"id": 37, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.daxiao", "amount": 3, "ball": "第五球大", "odds": 1.98, "awardMode": 2},
    {"id": 38, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第四球9", "odds": 9.9, "awardMode": 2},
    {"id": 39, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第五球1", "odds": 9.9, "awardMode": 2},
    {"id": 40, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第一球6", "odds": 9.9, "awardMode": 2},
    {"id": 41, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.danshuang", "amount": 3, "ball": "第五球单", "odds": 1.98, "awardMode": 2},
    {"id": 42, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.daxiao", "amount": 3, "ball": "第五球小", "odds": 1.98, "awardMode": 2},
    {"id": 43, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第三球2", "odds": 9.9, "awardMode": 2},
    {"id": 44, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.housan.baozi", "amount": 3, "ball": "豹子", "odds": 94.05, "awardMode": 2},
    {"id": 45, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第四球6", "odds": 9.9, "awardMode": 2},
    {"id": 46, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第一球5", "odds": 9.9, "awardMode": 2},
    {"id": 47, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第二球0", "odds": 9.9, "awardMode": 2},
    {"id": 48, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第五球6", "odds": 9.9, "awardMode": 2},
    {"id": 49, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第三球8", "odds": 9.9, "awardMode": 2},
    {"id": 50, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第四球5", "odds": 9.9, "awardMode": 2},
    {"id": 51, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.zonghe.longhuhe_70", "amount": 3, "ball": "虎", "odds": 2.19, "awardMode": 2},
    {"id": 52, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.daxiao", "amount": 3, "ball": "第四球大", "odds": 1.98, "awardMode": 2},
    {"id": 53, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第三球0", "odds": 9.9, "awardMode": 2},
    {"id": 54, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.housan.shunzi", "amount": 3, "ball": "顺子", "odds": 15.84, "awardMode": 2},
    {"id": 55, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第五球7", "odds": 9.9, "awardMode": 2},
    {"id": 56, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.zhongsan.zaliu", "amount": 3, "ball": "杂六", "odds": 2.37, "awardMode": 2},
    {"id": 57, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第二球2", "odds": 9.9, "awardMode": 2},
    {"id": 58, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第三球7", "odds": 9.9, "awardMode": 2},
    {"id": 59, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.zhongsan.baozi", "amount": 3, "ball": "豹子", "odds": 94.05, "awardMode": 2},
    {"id": 60, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.qiansan.shunzi", "amount": 3, "ball": "顺子", "odds": 15.84, "awardMode": 2},
    {"id": 61, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.housan.banshun", "amount": 3, "ball": "半顺", "odds": 2.27, "awardMode": 2},
    {"id": 62, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.daxiao", "amount": 3, "ball": "第二球小", "odds": 1.98, "awardMode": 2},
    {"id": 63, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.daxiao", "amount": 3, "ball": "第一球小", "odds": 1.98, "awardMode": 2},
    {"id": 64, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第四球4", "odds": 9.9, "awardMode": 2},
    {"id": 65, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第三球6", "odds": 9.9, "awardMode": 2},
    {"id": 66, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.zhongsan.banshun", "amount": 3, "ball": "半顺", "odds": 2.27, "awardMode": 2},
    {"id": 67, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第二球6", "odds": 9.9, "awardMode": 2},
    {"id": 68, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.daxiao", "amount": 3, "ball": "第三球大", "odds": 1.98, "awardMode": 2},
    {"id": 69, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.danshuang", "amount": 3, "ball": "第一球单", "odds": 1.98, "awardMode": 2},
    {"id": 70, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.housan.zaliu", "amount": 3, "ball": "杂六", "odds": 2.37, "awardMode": 2},
    {"id": 71, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第五球2", "odds": 9.9, "awardMode": 2},
    {"id": 72, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.danshuang", "amount": 3, "ball": "第四球双", "odds": 1.98, "awardMode": 2},
    {"id": 73, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第五球4", "odds": 9.9, "awardMode": 2},
    {"id": 74, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第四球2", "odds": 9.9, "awardMode": 2},
    {"id": 75, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.danshuang", "amount": 3, "ball": "第五球双", "odds": 1.98, "awardMode": 2},
    {"id": 76, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第三球3", "odds": 9.9, "awardMode": 2},
    {"id": 77, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第二球1", "odds": 9.9, "awardMode": 2},
    {"id": 78, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.qiansan.zaliu", "amount": 3, "ball": "杂六", "odds": 2.37, "awardMode": 2},
    {"id": 79, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第四球8", "odds": 9.9, "awardMode": 2},
    {"id": 80, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第三球4", "odds": 9.9, "awardMode": 2},
    {"id": 81, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.danshuang", "amount": 3, "ball": "第四球单", "odds": 1.98, "awardMode": 2},
    {"id": 82, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第二球7", "odds": 9.9, "awardMode": 2},
    {"id": 83, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第四球1", "odds": 9.9, "awardMode": 2},
    {"id": 84, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.qiansan.baozi", "amount": 3, "ball": "豹子", "odds": 94.05, "awardMode": 2},
    {"id": 85, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.danshuang", "amount": 3, "ball": "第二球单", "odds": 1.98, "awardMode": 2},
    {"id": 86, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.qiansan.duizi", "amount": 3, "ball": "对子", "odds": 3.46, "awardMode": 2},
    {"id": 87, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.daxiao", "amount": 3, "ball": "第三球小", "odds": 1.98, "awardMode": 2},
    {"id": 88, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第一球9", "odds": 9.9, "awardMode": 2},
    {"id": 89, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.daxiao", "amount": 3, "ball": "第二球大", "odds": 1.98, "awardMode": 2},
    {"id": 90, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第五球5", "odds": 9.9, "awardMode": 2},
    {"id": 91, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第三球5", "odds": 9.9, "awardMode": 2},
    {"id": 92, "moneyunit": 1, "multiple": 1, "num": 1, "type": "shuangmienpan.shiuanma.chiuhao", "amount": 3, "ball": "第二球8", "odds": 9.9, "awardMode": 2}
]

game_dollar_only = ['danshuang', 'daxiao', 'erbutonghao', 'ertonghaofuxuan', 'hezhi', 'santonghaodanxuan',
                    'santonghaotongxuan','yibutonghao', 'shuangmienpan.housan.banshun', 'shuangmienpan.housan.baozi',
                    'shuangmienpan.housan.duizi', 'shuangmienpan.housan.shunzi', 'shuangmienpan.housan.zaliu',
                    'shuangmienpan.qiansan.banshun', 'shuangmienpan.qiansan.baozi', 'shuangmienpan.qiansan.duizi',
                    'shuangmienpan.qiansan.shunzi', 'shuangmienpan.qiansan.zaliu', 'shuangmienpan.shiuanma.chiuhao',
                    'shuangmienpan.shiuanma.danshuang', 'shuangmienpan.shiuanma.daxiao', 'shuangmienpan.zhongsan.banshun',
                    'shuangmienpan.zhongsan.baozi', 'shuangmienpan.zhongsan.duizi', 'shuangmienpan.zhongsan.shunzi',
                    'shuangmienpan.zhongsan.zaliu', 'shuangmienpan.zonghe.danshuang', 'shuangmienpan.zonghe.daxiao',
                    'shuangmienpan.zonghe.longhuhe', 'longhu.lh.fushi'
                    ]

