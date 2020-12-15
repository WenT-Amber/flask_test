from typing import Dict

import cx_Oracle
import pandas
import pymysql
import sshtunnel
from sqlalchemy import create_engine
from sshtunnel import SSHTunnelForwarder
from urllib3.exceptions import MaxRetryError
from utils.Logger import create_logger
import redis, json, datetime, re, time

logger = create_logger(log_folder='/logger', log_name='Connection')


class OracleConnection:
    __slots__ = '_env_id', '_conn'

    def __init__(self, env_id: int):
        self._conn = None
        self._env_id = env_id

    def _get_oracle_conn(self):  # 連結數據庫 env 0: dev02 , 1:188
        if self._conn is not None:
            return self._conn
        if self._env_id == 2:
            username = 'rdquery'
            service_name = 'gamenxsXDB'
        else:
            username = 'firefog'
            service_name = ''
        oracle_ = {'password': ['LF64qad32gfecxPOJ603', 'JKoijh785gfrqaX67854', 'eMxX8B#wktFZ8V'],
                   'ip': ['10.13.22.161', '10.6.1.41', '10.6.1.31'],
                   'sid': ['firefog', 'game', '']}
        logger.info(f"oracle_.get('password')[0] = {oracle_.get('password')[0]}")
        logger.info(f"oracle_.get('password')[self._env_id] = {oracle_.get('password')[self._env_id]}")
        logger.info(f"  oracle_.get('ip')[self._env_id] + ':1521/' = {oracle_.get('ip')[self._env_id] + ':1521/'}")
        logger.info(
            f"  oracle_.get('sid')[self._env_id] + service_name = {oracle_.get('sid')[self._env_id] + service_name}")
        self._conn = cx_Oracle.connect(username, oracle_.get('password')[self._env_id],
                                       oracle_.get('ip')[self._env_id] + ':1521/' +
                                       oracle_.get('sid')[self._env_id] + service_name)
        return self._conn

    def get_sql_exec(self, sql):
        logger.info(f'get_sql_exec : sql = {sql}')
        cursor = self._get_oracle_conn().cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        result = []

        for i in rows:
            result.append(i[0])
        return result

    def select_domain_default_url(self, domain):
        cursor = self._get_oracle_conn().cursor()
        sql = "select GDL.domain, GDL.agent, UU.url, GDL.register_display, GDL.app_download_display, GDL.domain_type, GDL.status " \
              "from GLOBAL_DOMAIN_LIST GDL " \
              "inner join user_url UU on GDL.register_url_id = UU.id " \
              f"where GDL.domain like '%{domain}%'"
        logger.info(f'get_domain_default_url sql = {sql}')
        cursor.execute(sql)
        rows = cursor.fetchall()
        domain_urls = []
        for num, data in enumerate(rows):
            domain_urls.append(list(data))
        logger.info(f'get domain_urls = {domain_urls}')
        cursor.close()
        return domain_urls

    def select_url_token(self, token, joint_venture):  # 輸入 token 查詢 連結
        cursor = self._get_oracle_conn().cursor()
        if len(token) == 4:  # 代表是用 註冊碼  ,4位
            condition = f'%token={token}%'
        else:  # 使用id 去找 url
            condition = f'%id={token}%'
        sql = "select uc.account, uu.GMT_CREATED,uu.url,uu.days,uu.registers " \
              "from user_customer UC " \
              "inner join user_url UU  on UC.id= UU.creator " \
              f"where UU.url like  '%s' and UC.joint_venture = {joint_venture}" % condition
        print(sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        token_url = {}
        for num, user in enumerate(rows):
            token_url[num] = list(user)
        cursor.close()
        return token_url

    def select_sun_user(self, user, type_, domain):
        if domain == '1':  # 申博
            come_from = 'sunGame138'
            note = '申博138'
        elif domain == '0':  # 太陽城
            come_from = 'sunGame'
            note = '太阳城'
        else:
            raise Exception('get_sun_user 無對應domain')

        cursor = self._get_oracle_conn().cursor()
        if type_ == 1:  # 1 查詢轉移的用戶
            sql = "select account, cellphone, transfer_status, transfer_date " \
                  "from sun_game_user " \
                  f"where transfer_status = 1 and come_from = '{come_from}' " \
                  "order by transfer_date desc"
        elif type_ == 2:  # 查詢 指定domain flask_test. sun_user2()
            sql = "select GDL.domain,GDL.agent,b.url,GDL.register_display,GDL.status,GDL.note,b.days,b.registers " \
                  "from  GLOBAL_DOMAIN_LIST GDL " \
                  "inner join user_url b on GDL.register_url_id = b.id " \
                  f"where note = '{note}' " \
                  "order by GDL.status asc,b.registers desc"
        else:  # 查詢 指定用戶
            sql = "select * " \
                  "from sun_game_user " \
                  f"where account = '{user}' and come_from = '{come_from}'"
        print(f'get_sun_user - > sql = {sql}')
        cursor.execute(sql)
        rows = cursor.fetchall()
        sun_user = []
        for num, tuple_ in enumerate(rows):  # i 生成tuple
            sun_user[num] = list(tuple_)
        cursor.close()
        return sun_user

    def select_user_url(self, _user, _type=1, _joint_type=''):  # 用戶的 連結 ,type= 1 找用戶本身開戶連結, 0 找用戶的從哪個連結開出
        cursor = self._get_oracle_conn().cursor()
        user_url = []
        if _type == 1:  # 這邊user參數 為 userid , test_applycenter()方法使用
            sql = "select url " \
                  "from user_url " \
                  f"where url like '%{_user}%' and days=-1"
        elif _type == 2:  # user 為用戶名,這個表如果沒有, 有可能是 上級開戶連結 刪除,導致空 
            sql = "select UC.account, UU.url, UC.user_chain, UC.device, UU.days " \
                  "from user_customer UC " \
                  "inner join  user_url UU on UC.url_id = UU.id " \
                  f"where UC.account = '{_user}' and joint_venture = '{_joint_type}'"
        else:  # 最後才去用 user_customer. referer 去找, 這邊APP 開戶出來的會是null
            sql = "select account, referer, user_chain, device " \
                  "from user_customer " \
                  f"where account = '{_user}' and joint_venture = '{_joint_type}'"
        logger.info(f'select_user_url -> sql : {sql}')
        cursor.execute(sql)
        print(sql)
        rows = cursor.fetchall()
        for num, url in enumerate(rows):
            user_url.append(list(url))
        cursor.close()
        return user_url

    def select_user_id(self, account_: str, joint_type: int = None):
        cursor = self._get_oracle_conn().cursor()
        if joint_type is None:
            sql = "select id " \
                  "from user_customer " \
                  f"where account = '{account_}'"
        else:
            sql = "select id " \
                  "from user_customer " \
                  f"where account = '{account_}' and joint_venture = '{joint_type}'"
        print(f'get_user_id -> sql : {sql}')
        cursor.execute(sql)
        rows = cursor.fetchall()
        user_id = []

        for i in rows:
            print(f'i : {i}')
            user_id.append(i[0])
        cursor.close()
        return user_id

    def select_red_fund(self, user, type_=None):  # 充值 紅包 查尋  各充值表
        cursor = self._get_oracle_conn().cursor()
        if type_ == 0:  # 新手任務
            sql = "select UC.account,BM.cancel_reason " \
                  "from BEGIN_MISSION BM " \
                  "inner join user_customer UC on  BM.user_id = UC.id  " \
                  f"where UC.is_freeze = 0 and UC.account = '{user}'"
        elif type_ == 1:  # 活動充值表
            sql = "select UC.account, AFOR.THE_DAY " \
                  "from ACTIVITY_FUND_OPEN_RECORD  AFOR " \
                  "inner join user_customer UC on AFOR.user_id = UC.id " \
                  f"where UC.account = '{user}'"
        elif type_ == 2:  # 資金異動表'
            sql = "select UC.account,FCL.sn,FCL.GMT_CREATED " \
                  "from fund_change_log FCL " \
                  "inner join user_customer UC on FCL.user_id = UC.id " \
                  f"where UC.account = '{user}' and  FCL.reason like '%ADAL%'"
        elif type_ == 3:  # 資金異動表 搬動
            sql = "select UC.account,FCLH.sn,FCLH.GMT_CREATED " \
                  "from fund_change_log_hist FCLH " \
                  "inner join user_customer UC on FCLH.user_id = UC.id " \
                  f"where UC.account = '{user}' and  FCLH.reason like '%ADAL%'"
        else:  # - 判斷 是否有領過 首充附言鼓励金
            sql = "select REL.amount " \
                  "from  RED_ENVELOPE_LIST  REL " \
                  "inner join  user_customer UC on REL.user_id  = UC.id " \
                  f"where UC.account = '{user}' and note = '首充附言鼓励金'"
        logger.info(f'get_red_fund -> sql = {sql}')
        cursor.execute(sql)
        rows = cursor.fetchall()
        fund_ = []
        for index, data in enumerate(rows):
            fund_.append(list(data))
        cursor.close()
        return fund_

    def select_domain_url(self, domain) -> Dict[int, list]:  # 查詢 全局管理 後台設置的domain ,連結設置 (因為生產 沒權限,看不到)
        cursor = self._get_oracle_conn().cursor()
        sql = f"select a.domain,a.agent,b.url,a.register_display,a.app_download_display,a.domain_type,a.status from  \
        GLOBAL_DOMAIN_LIST a inner join user_url b \
        on a.register_url_id = b.id  where a.domain like '%{domain}%' "
        cursor.execute(sql)
        rows = cursor.fetchall()
        domain_url = {}
        for num, url in enumerate(rows):
            domain_url[num] = list(url)
        # print(domain_url)
        cursor.close()
        return domain_url

    def select_game_result(self, result) -> Dict[int, str]:  # 查詢用戶訂單號, 回傳訂單各個資訊
        cursor = self._get_oracle_conn().cursor()
        sql = f"select a.order_time,a.status,a.totamount,f.lottery_name,\
        c.group_code_title,c.set_code_title,c.method_code_title,\
        b.bet_detail,e.award_name,b.award_mode,b.ret_award,b.multiple,b.money_mode,b.evaluate_win\
        ,a.lotteryid,b.bet_type_code,c.theory_bonus,a.award_group_id,d.direct_ret,b.issue_code\
        from(((\
        (game_order a inner join game_slip b on\
        a.id = b.orderid and a.userid=b.userid and a.lotteryid=b.lotteryid) inner join \
        game_bettype_status c on \
        a.lotteryid = c.lotteryid and b.bet_type_code=c.bet_type_code) inner join\
        game_award_user_group d on\
        a.lotteryid = d.lotteryid and a.userid=d.userid) inner join \
        game_award_group e on \
        a.award_group_id = e.id and a.lotteryid =e.lotteryid) \
        inner join game_series f on  a.lotteryid = f.lotteryid where a.order_code = '{result}' and d.bet_type=1 \
        AND a.order_time > SYSDATE - INTERVAL '6' MONTH"
        cursor.execute(sql)
        print(sql)
        rows = cursor.fetchall()
        game_detail = {}  # 存放各細節
        # game_detail[result] = detail_list# 讓訂單為key,　value 為一個list 存放各訂單細節
        for index, tuple_ in enumerate(rows):
            game_detail[index] = tuple_
        cursor.close()
        return game_detail

    def select_game_order(self, play_type):  # 輸入玩法,找尋訂單
        cursor = self._get_oracle_conn().cursor()
        sql = f"select f.lottery_name,a.order_time,a.order_code,\
        c.group_code_title,c.set_code_title,c.method_code_title,a.status,g.account,b.bet_detail,h.number_record,b.award_mode\
        from((((((\
        game_order a inner join  game_slip b on \
        a.id = b.orderid and a.userid=b.userid and a.lotteryid=b.lotteryid) inner join game_bettype_status c on \
        a.lotteryid = c.lotteryid and b.bet_type_code=c.bet_type_code) \
        inner join game_award_user_group d on \
        a.lotteryid = d.lotteryid and a.userid=d.userid) \
        inner join game_award_group e on \
        a.award_group_id = e.id and a.lotteryid =e.lotteryid) \
        inner join game_series f on a.lotteryid = f.lotteryid) inner join user_customer g on\
        a.userid = g.id and d.userid = g.id) inner join game_issue h on\
        a.lotteryid = h.lotteryid and a.issue_code = h.issue_code\
        where a.order_time >sysdate - interval '6' month and \
        c.group_code_title||c.set_code_title||c.method_code_title like '%{play_type}%' and d.bet_type=1  and a.status !=1 \
        order by a.order_time desc"
        cursor.execute(sql)
        print(sql)
        rows = cursor.fetchall()
        game_order = {}
        len_order = len(rows)  # 需傳回去長度
        # print(rows,len(rows))#rows 為一個 list 包 tuple
        order_list = []  # 存放指定玩法 產生 的多少訂單
        for index, tuple_ in enumerate(rows):  # 取出 list長度 的各訂單 tuple
            order_list.append(list(tuple_))  # 把tuple 轉乘list  ,然後放入  order_list
            game_order[index] = order_list[index]  # 字典 index 為 key ,  order_list 為value
        # print(game_order)
        cursor.close()
        return [game_order, len_order]

    def select_active_app(self, user):  # 查詢APP 是否為有效用戶表
        cursor = self._get_oracle_conn().cursor()
        sql = f"select *  from USER_CENTER_THIRDLY_ACTIVE " \
              f"where create_date >=  trunc(sysdate,'mm') " \
              f"and user_id in (select id from user_customer where account = '{user}')"
        cursor.execute(sql)
        rows = cursor.fetchall()
        active_app = []
        for tuple_ in rows:
            for i in tuple_:
                # print(i)
                active_app.append(i)
        # print(active_app,len(active_app))
        cursor.close()
        return active_app

    def select_app_bet(self, user):  # 查詢APP 代理中心 銷量
        cursor = self._get_oracle_conn().cursor()
        app_bet = {}
        '''
        for third in ['ALL', 'LC', 'KY', 'CITY', 'GNS', 'FHLL', 'BBIN', 'IM', 'SB', 'AG']:
            if third == 'ALL':
                sql = f"select sum(cost) 用戶總有效銷量, sum(prize) ,sum(prize) - sum(cost) 用戶總盈虧 " \
                      f"from THIRDLY_AGENT_CENTER where account = '{user}' and create_date > trunc(sysdate,'mm')"
            else:
                sql = f"select sum(cost) 用戶總有效銷量, sum(prize) ,sum(prize) - sum(cost) 用戶總盈虧 " \
                      f"from THIRDLY_AGENT_CENTER where account = '{user}' " \
                      f"and create_date > trunc(sysdate,'mm') " \
                      f"and plat='{third}'"
        '''
        sql = f"SELECT SUM(cost) 用戶總有效銷量, SUM(prize), SUM(prize) - SUM(cost) 用戶總盈虧, plat " \
              f"FROM thirdly_agent_center WHERE account = '{user}'AND create_date > trunc(SYSDATE,'mm') group by plat "
        print(sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        print(rows)
        for tuple_, con in enumerate(rows):
            app_bet[tuple_] = con
        print(app_bet)
        cursor.close()
        return app_bet

    def select_active_card(self, user, envs):  # 查詢綁卡是否有重複綁
        cursor = self._get_oracle_conn().cursor()
        if envs == 2:  # 生產另外一張表
            sql = f"SELECT bank_number, count(id) FROM rd_view_user_bank " \
                  f"WHERE bank_number in (SELECT bank_number FROM rd_view_user_bank WHERE account = '{user}' ) " \
                  f"group BY bank_number"
        else:
            sql = f"SELECT BANK_NUMBER,count(user_id) FROM USER_BANK " \
                  f"WHERE BANK_NUMBER in " \
                  f"(SELECT BANK_NUMBER FROM USER_BANK WHERE USER_ID= " \
                  f"(SELECT ID FROM USER_CUSTOMER WHERE ACCOUNT='{user}')) " \
                  f"group by bank_number"
        cursor.execute(sql)
        rows = cursor.fetchall()
        card_num = {}
        for index, tuple_ in enumerate(rows):
            card_num[index] = list(tuple_)
        # print(card_num)
        cursor.close()
        return card_num

    def select_active_fund(self, user):  # 查詢當月充值金額
        cursor = self._get_oracle_conn().cursor()
        sql = f"select sum(real_charge_amt) from fund_charge " \
              f"where status=2 " \
              f"and apply_time > trunc(sysdate,'mm') " \
              f"and user_id in ( select id from user_customer where account = '{user}')"
        cursor.execute(sql)
        rows = cursor.fetchall()
        user_fund = []  # 當月充值金額
        print(rows)
        for tuple_ in rows:
            for i in tuple_:
                # print(i)
                user_fund.append(i)
        cursor.close()
        return user_fund

    def select_issue(self, lottery_id):  # 查詢正在銷售的 期號
        # Joy188Test.date_time()
        # today_time = '2019-06-10'#for 預售中 ,抓當天時間來比對,會沒獎期
        try:
            cursor = self._get_oracle_conn().cursor()
            sql = f"select web_issue_code,issue_code from game_issue " \
                  f"where lotteryid = '{lottery_id}' " \
                  f"and sysdate between sale_start_time " \
                  f"and sale_end_time"
            cursor.execute(sql)
            rows = cursor.fetchall()

            issueName = []
            issue = []

            if lottery_id in ['99112', '99306']:  # 順利秒彩,順利11選5  不需 講期. 隨便塞
                issueName.append('1')
                issue.append('1')
            else:
                for i in rows:  # i 生成tuple
                    issueName.append(i[0])
                    issue.append(i[1])
            cursor.close()
            return {'issueName': issueName, 'issue': issue}
        except:
            pass

    def select_red_id(self, user):  # 紅包加壁  的訂單號查詢 ,用來審核用
        cursor = self._get_oracle_conn().cursor()
        sql = f"SELECT ID FROM RED_ENVELOPE_LIST " \
              f"WHERE status=1 " \
              f"and USER_ID = (SELECT id FROM USER_CUSTOMER WHERE account ='{user}')"
        cursor.execute(sql)
        rows = cursor.fetchall()

        red_id = []
        for i in rows:  # i 生成tuple
            red_id.append(i[0])
        cursor.close()
        return red_id

    def select_red_bal(self, user) -> list:
        cursor = self._get_oracle_conn().cursor()
        sql = f"SELECT bal FROM RED_ENVELOPE " \
              f"WHERE USER_ID = (SELECT id FROM USER_CUSTOMER WHERE account ='{user}')"
        cursor.execute(sql)
        rows = cursor.fetchall()

        red_bal = []
        for i in rows:  # i 生成tuple
            red_bal.append(i[0])
        cursor.close()
        return red_bal

    def get_order_code_iapi(self, orderid):  # 從iapi投注的orderid對應出 order_code 方案編號
        cursor = self._get_oracle_conn().cursor()
        sql = f"select order_code from game_order where id in (select orderid from game_slip where orderid = '{orderid}')"

        cursor.execute(sql)
        rows = cursor.fetchall()

        order_code = []
        for i in rows:  # i 生成tuple
            order_code.append(i[0])
        cursor.close()
        return order_code

    def select_bet_type_code(self, lottery_id, game_type):  # 從game_type 去對應玩法的數字,給app投注使用
        cursor = self._get_oracle_conn().cursor()
        sql = f"select bet_type_code from game_bettype_status where lotteryid = '{lottery_id}' and group_code_name||set_code_name||method_code_name = '{game_type}'"

        cursor.execute(sql)
        rows = cursor.fetchall()

        bet_type = []
        for i in rows:  # i 生成tuple
            bet_type.append(i[0])
        cursor.close()
        return bet_type

    def select_lottery_issue_number(self, lottery_name):  # 從game_type 去對應玩法的數字,給app投注使用
        cursor = self._get_oracle_conn().cursor()
        sql = f"select ISSUE_NUMBER from GAME_EC_LOG where LOTTERY = '{lottery_name}' order by CREAT_TIME desc"
        logger.info(sql)

        cursor.execute(sql)
        rows = cursor.fetchall()

        issue_numbers = []
        for i in rows:  # i 生成tuple
            issue_numbers.append(i[0])
        cursor.close()
        return issue_numbers

    def select_game_slip(self, order_id):
        cursor = self._get_oracle_conn().cursor()
        sql = f"select * from GAME_SLIP where ORDERID = '{order_id}'"
        logger.info(sql)

        cursor.execute(sql)
        result = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in cursor.fetchall()]
        cursor.close()
        return result

    def select_game_order_data(self, order_code):
        cursor = self._get_oracle_conn().cursor()
        sql = f"select * from GAME_ORDER where ORDER_CODE = '{order_code}'"
        logger.info(sql)

        cursor.execute(sql)
        result = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in cursor.fetchall()]
        cursor.close()
        return result[0]

    def select_number_record(self, lotteryid, issue_code):
        cursor = self._get_oracle_conn().cursor()
        sql = f"select number_record from game_issue " \
              f"where issue_code = '{issue_code}' " \
              f"and lotteryid = '{lotteryid}'"
        print(sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        number_record = {}
        for index, tuple_ in enumerate(rows):
            number_record[index] = tuple_[0]
        cursor.close()
        return number_record

    def select_bonus(self, lottery_id, bet_type_code, detail=""):  # 用bet_type_code 找尋 平台獎金/理論獎金 ,detail 投注內容,
        cursor = self._get_oracle_conn().cursor()
        if detail == '':
            sql = f'select actual_bonus,lhc_theory_bonus from game_award ' \
                  f'where LOTTERYID = {lottery_id} ' \
                  f'and bet_type_code like \'%{bet_type_code}%\''
        elif detail == 'FF_bonus':  # 用平台獎金 去都出 理論獎金  , 目前 PCDD 賠率使用
            sql = f'SELECT lhc_code, actual_bonus, lhc_theory_bonus FROM game_award WHERE lotteryid = {lottery_id}'
        elif type(detail) == int:  # 使用 award_group_id  來看
            sql = f'select actual_bonus from game_award ' \
                  f'where LOTTERYID={lottery_id} ' \
                  f'and bet_type_code = \'{bet_type_code}\' ' \
                  f'and award_group_id = {detail}'
        else:
            sql = f'select actual_bonus,lhc_theory_bonus from game_award ' \
                  f'where LOTTERYID = {lottery_id} ' \
                  f'and  bet_type_code = \'{bet_type_code}\' ' \
                  f'and  lhc_code like \'%{detail}%\''
        logger.info(f'select_bonus: sql = {sql}')
        cursor.execute(sql)
        rows = cursor.fetchall()
        bonus = {}
        for index, tuple_ in enumerate(rows):
            # logger.info(f'index = {index}, tuple_ = {tuple_}')
            if detail == "FF_bonus":  # 抓出來需做 數值上的處理
                bonus[tuple_[0]] = [float(tuple_[1] / 10000), tuple_[2] / 10000]  # 用平台獎金當key : 理論獎金value
            else:
                bonus[index] = tuple_
        cursor.close()
        return bonus

    def select_fund_charge(self, date, type_=""):  # 查詢 動態時間  ,充值金額, 用來數據分溪用
        cursor = self._get_oracle_conn().cursor()
        if type_ == "month":  # 月份
            data_fund = {}
            year = date.split('/')[0]  # 年份
            month = date.split('/')[1]  # 月份
            day_31 = [1, 3, 5, 7, 8, 10, 12]
            today_day = datetime.datetime.now().day  # 現在日期
            today_month = datetime.datetime.now().month  # 現在月份
            if month == str(today_month):  # 頁面選的月份 是當前月份
                day_range = today_day - 1  # 今天的還不用抓出來
            else:
                if month in list(map(str, day_31)):
                    day_range = 31
                elif month == '2':
                    day_range = 29
                else:
                    day_range = 30
            for day in range(1, day_range + 1):
                date = '%s/%s/%s' % (year, month, day)
                sql = "select sum(REAL_CHARGE_AMT),sum(charge_fee),count(REAL_CHARGE_AMT) from fund_charge where status = 2 and apply_time between to_date('%s 00:00:00','YYYY/MM/DD HH24:MI:SS') \
                and to_date('%s 23:59:59','YYYY/MM/DD HH24:MI:SS')  order by apply_time desc" % (date, date)
                sql2 = "select count(id) from fund_charge where  apply_time between \
                to_date('%s 00:00:00','YYYY/MM/DD HH24:MI:SS') \
                and to_date('%s 23:59:59','YYYY/MM/DD HH24:MI:SS')  order by apply_time desc" % (date, date)
                cursor.execute(sql)
                rows = cursor.fetchall()
                for tuple_ in rows:
                    data_fund[date] = list(tuple_)
                cursor.execute(sql2)  # 總充值個數
                rows = cursor.fetchall()
                for tuple_ in rows:
                    for key in data_fund:
                        data_fund[key].append(tuple_[0])
        else:
            if type_ == "":
                sql = "select sum(REAL_CHARGE_AMT),sum(charge_fee),count(REAL_CHARGE_AMT) from fund_charge where status = 2 and apply_time between to_date('%s 00:00:00','YYYY/MM/DD HH24:MI:SS') \
                and to_date('%s 23:59:59','YYYY/MM/DD HH24:MI:SS')  order by apply_time desc" % (date, date)
            else:  # 找出總出直個數 ,不代 status
                sql = "select count(id) from fund_charge where  apply_time between \
                to_date('%s 00:00:00','YYYY/MM/DD HH24:MI:SS') \
                and to_date('%s 23:59:59','YYYY/MM/DD HH24:MI:SS')  order by apply_time desc" % (date, date)
            print(sql)
            cursor.execute(sql)
            rows = cursor.fetchall()
            data_fund = {}
            for index, tuple_ in enumerate(rows):
                data_fund[index] = tuple_
        cursor.close()
        return data_fund

    def select_fee(self, type_, user):  # 查詢 用戶 總代線 手續費
        cursor = self._get_oracle_conn().cursor()
        if type_ == 'fund':  # 充值
            sql = "SELECT fee.bank_id, fee.fee,fee.mobile,bank.name FROM TOP_AGENT_RECHARGE_FEE fee \
            INNER JOIN user_customer user_ ON fee.user_id = user_.id inner join FUND_BANK bank  on fee.bank_id = bank.code \
            WHERE user_.account in (select regexp_substr(user_chain,'[^/]+') from user_customer where account = '%s')" % user
        else:  # 提線
            sql = "SELECT fee.enable,fee.bank_fee,fee.bank_limit_count,fee.usdt_fee,fee.usdt_limit_count, \
            user_.vip_lvl,user_.new_vip_flag FROM top_agent_withdraw_fee fee \
            INNER JOIN user_customer user_ ON fee.user_id = user_.id WHERE \
            user_.account in (select regexp_substr(user_chain,'[^/]+') from user_customer where account = '%s')" % user
        print(sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        fund_fee = {}
        for num, index in enumerate(rows):
            fund_fee[num] = index
        cursor.close()
        return fund_fee

    def select_user_lvl(self, user):  # 用戶 vip 和是否為 星級
        cursor = self._get_oracle_conn().cursor()
        sql = "select vip_lvl,new_vip_flag from user_customer where account = '%s'" % user
        cursor.execute(sql)
        rows = cursor.fetchall()
        user_lvl = []
        for i in rows:
            user_lvl.append(i)
        cursor.close()
        return user_lvl

    def select_lottery_point(self, lotteryid, user):
        """
        用戶彩種反點, FF_Joy188  高獎金玩法,會拿來算獎金
        :param lotteryid:
        :param user:
        :return:
        """
        cursor = self._get_oracle_conn().cursor()
        sql = "SELECT  user_.account,user_.register_date,game_award.direct_ret,game_award_group.award_name \
        FROM game_award_user_group game_award INNER JOIN user_customer user_ ON game_award.userid = user_.id \
        INNER JOIN game_award_group ON game_award.sys_award_group_id = game_award_group.id \
        WHERE game_award.lotteryid = %s AND user_.account = '%s' and game_award.bet_type = 1" % (lotteryid, user)
        logger.info(f'select_lottery_point: sql={sql}')
        cursor.execute(sql)
        rows = cursor.fetchall()
        lottery_point = {}
        for index, content in enumerate(rows):
            lottery_point[index] = content
        cursor.close()
        return lottery_point

    def close_conn(self):
        if self._conn is not None:
            self._conn.close()


class MysqlConnection:
    __slots__ = '_env_id', '_conn', '_third'

    def __init__(self, env_id: int):
        self._env_id = env_id
        self._conn = None
        self._third = None

    def get_mysql_conn(self, third: str):  # 第三方  mysql連線
        if self._third == third:
            return self._conn
        self.close_conn()
        self._third = third
        third_dict = {'lc': ['lcadmin', ['cA28yF#K=yx*RPHC', 'XyH]#xk76xY6e+bV'], 'ff_lc'],
                      'ky': ['kyadmin', ['ALtfN#F7Zj%AxXgs=dT9', 'kdT4W3#dEug3$pMM#z7q'], 'ff_ky'],
                      'city': ['761cityadmin', ['KDpTqUeRH7s-s#D*7]mY', 'bE%ytPX$5nU3c9#d'], 'ff_761city'],
                      'im': ['imadmin', ['D97W#$gdh=b39jZ7Px', 'nxDe2yt7XyuZ@CcNSE'], 'ff_im'],
                      'shaba': ['sbadmin', ['UHRkbvu[2%N=5U*#P3JR', 'aR8(W294XV5KQ!Zf#"v9'], 'ff_sb'],
                      'bbin': ['bbinadmin', 'Csyh*P#jB3y}EyLxtg', 'ff_bbin'],
                      'gns': ['gnsadmin', 'Gryd#aCPWCkT$F4pmn', 'ff_gns']
                      }
        if self._env_id == 0:  # dev
            ip = '10.13.22.151'
        elif self._env_id == 1:  # 188
            ip = '10.6.32.147'
        else:
            raise Exception('evn 錯誤')

        user_ = third_dict[third][0]
        db_ = third_dict[third][2]

        if third == 'gns':  # gns只有一個 測試環境
            password_ = third_dict[third][1]
            ip = '10.6.32.147'  # gns Db 只有 188
        else:
            password_ = third_dict[third][1][self._env_id]

        self._conn = pymysql.connect(
            host=ip,
            user=user_,
            passwd=password_,
            db=db_)
        return self._conn

    def thirdly_tran(self, tran_type: int, third: str, user: str) -> list:
        logger.info(f'tran_type = {tran_type}, third = {third}, user = {user}')
        cur = self.get_mysql_conn(third).cursor()
        # third 判斷 第三方 是那個 ,gns table 名稱不同
        if third in ['lc', 'ky', 'city', 'im', 'shaba']:
            table_name = 'THIRDLY_TRANSCATION_LOG'
            if tran_type == 0:  # 轉入
                trans_name = 'FIREFROG_TO_THIRDLY'
            else:  # 轉出
                trans_name = 'THIRDLY_TO_FIREFROG'
        elif third == 'gns':
            table_name = 'GNS_TRANSCATION_LOG'
            if tran_type == 0:  # gns轉入
                trans_name = 'FIREFROG_TO_GNS'
            else:
                trans_name = 'GNS_TO_FIREFROG'
        else:
            print('第三方 名稱錯誤')
        sql = f"SELECT SN,STATUS FROM {table_name} " \
              f"WHERE FF_ACCOUNT = '{user}' AND TRANS_NAME= '{trans_name}'" \
              f"ORDER BY CREATE_DATE DESC LIMIT 1"
        logger.info(f'sql = {sql}')

        result = []
        cur.execute(sql)
        for row in cur.fetchall():
            result = [row[0], row[1]]
            logger.info(result)
        self.get_mysql_conn(third).commit()
        cur.close()
        return result

    def close_conn(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None


class PostgresqlConnection:

    def __init__(self):
        pass

    def _get_postgre_conn(self, sql):
        try:
            logger.info('get_postgre_conn start.')
            with SSHTunnelForwarder(
                    ('18.144.130.142', 22),
                    ssh_private_key="C:\\Users\\Wen\\Documents\\03_SQL\\YFT\\qa.pem",
                    ssh_username="centos",
                    remote_bind_address=('localhost', 5432)) as server:
                logger.info('SSHTunnelForwarder start.')
                # trace_logger = sshtunnel.create_logger(loglevel="TRACE")
                server.daemon_forward_servers = True
                server.start()
                logger.info("server connected")

                local_port = str(server.local_bind_port)
                logger.info(f'local_port = {local_port}')
                engine = create_engine(
                    'postgresql://admin:LfCnkYSHu4UCSPf49-Xy45Ymgvq1qY@127.0.0.1:' + local_port + '/lux')
                logger.info("database connected")

                response_list = []
                logger.info(f'sql = {sql}')
                result = pandas.read_sql(sql, engine)
                engine.dispose()
                for value in result.values:
                    response_list.append(value[0])
                server.stop()
                return response_list
        except sshtunnel.BaseSSHTunnelForwarderError:
            return 'SSH連線失敗'
        except MaxRetryError:
            return '連線逾時'

    def get_user_id_yft(self, user_name):
        id_list = self._get_postgre_conn(f"SELECT UID FROM USER_BASIC WHERE ACCOUNT = '{user_name}'")
        logger.info(f'user_id = {id_list}')
        return id_list

    def get_lottery_games(self, lottery):
        sql = f"select (play_type||bet_type) as games from lottery_play_info where lottery_type = '{lottery}' and delete_flag = 'no'"
        response = self._get_postgre_conn(sql)
        logger.info(f'{lottery} games = {response}')
        return response

    def close_conn(self):
        pass


class RedisConnection:  # redis連線
    def __init__(self):
        self.env_connect = {'ip': ['10.13.22.152', '10.6.1.82', '10.13.12.47']}  # 0:dev,1:188 ,2: 本地

    def get_rediskey(self, envs):  # env參數 決定是哪個環境
        # redis_dict = {'ip': ['10.13.22.152', '10.6.1.82','127.0.0.1']}  # 0:dev,1:188 ,2: 本地
        pool = redis.ConnectionPool(host=self.env_connect['ip'][envs], port=6379)
        r = redis.Redis(connection_pool=pool)
        return r

    @staticmethod
    def set_key(key_name, key_value):  # 存key
        r = RedisConnection().get_rediskey(2)  # 只有本基可存
        json_str = json.dumps(key_value)  # 轉成str 存入redis
        r.set(key_name, json_str)

    @staticmethod
    def get_key(envs, key_name):
        r = RedisConnection().get_rediskey(envs)
        key_ = r.get(key_name)
        if key_ is None:
            return 'not exist'
        else:
            return json.loads(key_)  # 取出來 byte 轉成 dict

    @staticmethod
    def get_token(envs, user):  # 查詢用戶 APP token 時間
        r = RedisConnection().get_rediskey(envs)
        r_keys = (r.keys('USER_TOKEN_%s*' % re.findall(r'[0-9]+|[a-z]+', user)[0]))
        for i in r_keys:
            if user in str(i):
                user_keys = (str(i).replace("'", '')[1:])
        print(user_keys)
        user_dict = r.get(user_keys)
        timestap = str(user_dict).split('timeOut')[1].split('"token"')[0][2:-4]  # 時間戳
        token_time = time.localtime(int(timestap))  # 到期時間
        print('token到期時間: %s-%s-%s %s:%s:%s' % (token_time.tm_year, token_time.tm_mon, token_time.tm_mday,
                                                token_time.tm_hour, token_time.tm_min, token_time.tm_sec))
