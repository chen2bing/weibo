"""
    功能：定时查询某微博博主的微博，如果更新，发送邮件通知
    作者：cbb
    日期：2020/8/16
"""
import requests
from bs4 import BeautifulSoup
import time
import re
from my_email import Email


class WeiboMonitor(object):
    def __init__(self, wb_id, wb_cookie, account, password, letter_receiver, per=600):
        """
        初始化
        :param wb_id: 博主微博ID
        :param wb_cookie: 浏览器Cookie
        :param account: 邮箱账号
        :param password: 邮箱密码
        :param letter_receiver: 收件人
        :param per: 检查周期，默认为10分钟
        """
        self.id = wb_id
        self.cookie = wb_cookie
        self.my_email = Email(account, password)
        self.receiver = letter_receiver
        self.period = per
        self.date = time.time()

    def __get_html_from_weibo(self):
        """
        从微博的主页提取源码
        :return:
        """
        # 爬取首页
        url = 'https://weibo.com/u/' + str(self.id) + '?profile_ftype=1&is_all=1&display=0&retcode=6102'
        headers = {
            'Cookie': self.cookie,
            'user-agent': 'Mozilla/5.0'
        }
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.encoding = 'utf-8'
        except:
            print("抓取页面异常")
            return -1
        # 返回网页源码
        return r.text

    def __get_script_str(self):
        """
        获取首页包含微博主体内容的script
        :return: script(字符串)
        """
        # 获得网页源码
        html_text = self.__get_html_from_weibo()
        # 用正则表达式提取出目标script
        rst = re.search(r'<script>.*"Pl_Official_MyProfileFeed__20".*</script>', html_text)
        if rst:
            return rst.group(0)
        else:
            return -1

    @staticmethod
    def __get_html_from_script(script_str):
        """
        从script中提取出微博主体的html
        :param script_str: script的字符串表示
        :return: 微博主体html（字符串）
        """
        index = script_str.find('(')  # 查找第一个'('
        if index == -1:
            print("script提取失败，找不到(")
            return -1
        dic_str = script_str[16:-10]  # 截取出字典（字符串）
        dic = eval(dic_str)  # 转换为字典
        if "html" in dic.keys():
            dic_str = dic["html"]
            html_str = dic_str.replace("\\/", "/")
            return html_str
        else:
            print("script提取失败，字典中无html键")
            return -1

    @staticmethod
    def __get_info_from_weibo(html_str, index):
        """
        提取出某条微博的详细信息
        :param html_str: 微博主体html字符串
        :param index: 微博的序号，从0开始，第一条则为0
        :return: 首条微博详细信息（字典）
        """
        weibo_info = {
            "type": "",         # 微博类型：发表/点赞/转发
            "name": "",         # 博主的微博昵称
            "date": "",         # 时间
            "text": "",         # 微博自写内容
            "ori_name": "",     # 点赞微博/转发微博的微博昵称
            "ori_date": "",     # 点赞微博/转发微博的时间
            "ori_text": "",     # 点赞微博/转发微博的内容
        }
        # 更新博主昵称
        rst = re.search(r'\"feed_list_content\" nick-name=\".*\"', html_str)
        username = rst.group(0)[31:-1]
        weibo_info["name"] = username
        # 解析网页
        soup = BeautifulSoup(html_str, 'html.parser')
        # 判断微博类型
        main_div = soup.find_all('div', attrs={'action-data': 'cur_visible=0'})[index]
        type_test = main_div.find('div', attrs={'class': 'WB_cardtitle_b S_line2'})
        # 点赞
        if type_test is not None:
            # 修改类型
            weibo_info["type"] = "like"
            # 获取点赞时间
            like_date = main_div.find('a', attrs={'target': '_blank'}).string
            like_date = like_date.strip()
            weibo_info["date"] = like_date
            # 点赞的原微博内容
            like_detail = main_div.find('div', attrs={'class': 'WB_detail'})
            # 原微博博主昵称
            like_name = like_detail.find('a', attrs={'target': '_blank'}).string
            weibo_info["ori_name"] = like_name
            # 原微博发表时间
            like_date = like_detail.find('div', attrs={'class': 'WB_from S_txt2'}).find('a', attrs={'target': '_blank'})
            weibo_info["ori_date"] = like_date.attrs["title"]
            # 原微博内容
            like_text = like_detail.find('div', attrs={'class': 'WB_text W_f14'}).contents[0]
            like_text = like_text.strip()
            weibo_info["ori_text"] = like_text
        else:
            wb_detail = main_div.find('div', attrs={'class': 'WB_detail'})
            type_test = wb_detail.find('div', attrs={'class': 'WB_feed_expand'})
            # 转发
            if type_test is not None:
                # 修改微博类型
                weibo_info["type"] = "forward"
                # 获取转发的时间
                forward_date = wb_detail.find('div', attrs={'class': 'WB_from S_txt2'}).find('a', attrs={'target': '_blank'})
                weibo_info["date"] = forward_date.attrs["title"]
                # 获取转发的内容
                forward_all_element = wb_detail.find('div', attrs={'class': 'WB_text W_f14'})
                forward_text = ""
                for t in forward_all_element.contents:
                    tname = t.name
                    if tname is None:
                        forward_text += str(t).strip()
                    elif tname == "a":
                        # 获取a标签所有子标签中的文字
                        for at in t.contents:
                            if at.name is None:
                                forward_text += at.string.strip()
                    elif tname == "img":
                        forward_text += str(t.attrs["title"]).strip()
                weibo_info["text"] = forward_text
                # 获取原微博博主昵称
                forward_ori_div = wb_detail.find('div', attrs={'class': 'WB_feed_expand'})
                forward_ori_info = forward_ori_div.find('div', attrs={'class': 'WB_info'}).find('a', attrs={'class': 'W_fb S_txt1'})
                weibo_info["ori_name"] = forward_ori_info.attrs["nick-name"]
                # 获取原微博内容
                forward_ori_text_tag = forward_ori_div.find('div', attrs={'class': 'WB_text'})
                forward_ori_text = ""
                for t in forward_ori_text_tag.contents:
                    tname = t.name
                    if tname is None:
                        forward_ori_text += str(t).strip()
                    elif tname == "a":
                        # 获取a标签所有子标签中的文字
                        for at in t.contents:
                            if at.name is None:
                                forward_ori_text += at.string.strip()
                    elif tname == "img":
                        forward_ori_text += str(t.attrs["title"]).strip()
                weibo_info["ori_text"] = forward_ori_text
                # 获取原微博时间
                forward_ori_date_tag = forward_ori_div.find('div', attrs={'class': 'WB_func clearfix'}).find('div', attrs={'class': 'WB_from S_txt2'})\
                    .find('a', attrs={'target': '_blank'})
                forward_ori_date = forward_ori_date_tag.attrs["title"]
                weibo_info["ori_date"] = forward_ori_date
            # 发表
            else:
                # 修改类型
                weibo_info["type"] = "post"
                # 获取时间
                post_date_tag = wb_detail.find('div', attrs={'class': 'WB_from S_txt2'}).find('a', attrs={'class': 'S_txt2'})
                post_date = post_date_tag.attrs["title"]
                weibo_info["date"] = post_date
                # 获取内容
                post_text_tag = wb_detail.find('div', attrs={'class': 'WB_text W_f14'})
                post_text = ""
                for t in post_text_tag.contents:
                    tname = t.name
                    if tname is None:
                        post_text += str(t).strip()
                    elif tname == "a":
                        # 获取a标签所有子标签中的文字
                        for at in t.contents:
                            if at.name is None:
                                post_text += at.string.strip()
                    elif tname == "img":
                        post_text += str(t.attrs["title"]).strip()
                weibo_info["text"] = post_text

        # 全部提取结束，处理一下微博内容
        # 去除微博文本中的'\u200b'
        weibo_info["text"] = weibo_info["text"].replace('\u200b', '')
        weibo_info["ori_text"] = weibo_info["ori_text"].replace('\u200b', '')

        return weibo_info

    def __get_newest_weibo(self):
        """
        获取最新的微博
        :return: 微博内容（字典）
        """
        # 从网页源码中提取出包含微博主体的script
        script_str = self.__get_script_str()

        while script_str == -1:
            print("提取script异常")
            return -1

        # 从script中提取出微博主体html
        html_text = self.__get_html_from_script(script_str)
        if html_text == -1:
            print("解析script异常")
            return -1

        # 提取首条微博的主要内容
        weibo_info = self.__get_info_from_weibo(html_text, 0)

        # 返回
        return weibo_info

    def __check(self):
        """
        检查微博是否有新动态
        :return: True / False
        """
        # 获取script
        script_str = self.__get_script_str()
        while script_str == -1:
            print("提取script异常，已重新抓取网页")
            time.sleep(2)
            script_str = self.__get_script_str()
        # 用正则表达式提取最新的时间
        rst = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', script_str)
        date_str = rst.group(0)
        print("最近微博日期：", date_str)
        time_stamp = time.mktime(time.strptime(date_str, "%Y-%m-%d %H:%M"))
        # 和保存的时间做比较
        if time_stamp > self.date:
            return True
        else:
            return False

    def start(self):
        """
        开始运行
        :return:
        """
        # 根据设定的周期，定时检查最新微博的时间
        while True:
            # 检查最新的微博时间
            if self.__check():
                print("有新微博")
                # 高于保存的时间，获取最新的微博内容
                weibo_info = self.__get_newest_weibo()
                # 更新保存的时间
                date_str = weibo_info["date"]
                time_stamp = time.mktime(time.strptime(date_str, "%Y-%m-%d %H:%M"))
                self.date = time_stamp
                # 整理邮件内容
                email_title = weibo_info["name"] + "更新微博啦！"
                email_text = ""
                # 点赞
                if weibo_info["type"] == "like":
                    email_text += weibo_info["name"] + weibo_info["text"] + "\n"
                    email_text += "点赞的微博内容如下：\n"
                    email_text += "@" + weibo_info["ori_name"] + "于" + weibo_info["ori_date"] + ":"
                    email_text += weibo_info["ori_text"] + "\n"
                # 转发
                elif weibo_info["type"] == "forward":
                    email_text += weibo_info["name"] + "于" + weibo_info["date"] + "转发了" + weibo_info["ori_name"] + "的微博\n"
                    email_text += "转发内容：" + weibo_info["text"] + "\n"
                    email_text += "原微博内容: @" + weibo_info["ori_name"] + ": " + weibo_info["ori_text"] + "\n"
                # 发布
                elif weibo_info["type"] == "post":
                    email_text += weibo_info["name"] + "于" + weibo_info["date"] + "发布了新微博，内容如下：\n"
                    email_text += "@" + weibo_info["name"] + ": " + weibo_info["text"] + "\n"
                # 发送邮件
                self.my_email.send_email(self.receiver, email_title, email_text)
            else:
                print("无新微博")
            time.sleep(self.period)

    def test(self):
        """
        测试用
        :return:
        """
        weibo = self.__get_newest_weibo()
        print(weibo)


if __name__ == "__main__":
    # 微博Cookie
    weibo_cookie = ''
    # 邮箱的账号和密码（授权码）
    email_account = ""
    email_password = ""
    # 爬取周期
    period = 600
    # 博主数字ID
    weibo_id = 0
    # 邮件收件人
    receiver = ""

    wm = WeiboMonitor(weibo_id, weibo_cookie, email_account, email_password, receiver, period)
    wm.start()

