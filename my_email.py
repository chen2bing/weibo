"""
    功能：发送邮件
    作者：cbb
    日期：2020/8/18
"""
import smtplib
from email.mime.text import MIMEText


class Email(object):
    def __init__(self, email_account, email_pwd):
        """
        初始化邮箱
        :param email_account: 邮件账号
        :param email_pwd: 密码/授权码
        """
        self.email = {
            "account": email_account,
            "pwd": email_pwd
        }

    def send_email(self, receiver, title, message):
        """
        发送邮件
        :param receiver: 收件人
        :param title: 邮件标题
        :param message: 邮件内容
        :return:
        """
        # 163邮箱服务器地址
        mail_host = 'smtp.163.com'
        # 163用户名
        mail_user = self.email["account"]
        # 密码(部分邮箱为授权码)
        mail_pass = self.email["pwd"]
        # 邮件发送方邮箱地址
        sender = self.email["account"]
        # 邮件接受方邮箱地址
        receivers = [str(receiver)]

        # 邮件内容设置
        message = MIMEText(message, 'plain', 'utf-8')
        # 邮件主题
        message['Subject'] = title
        # 发送方信息
        message['From'] = sender
        # 接受方信息
        message['To'] = receivers[0]

        try:
            smtpObj = smtplib.SMTP()
            # 连接到服务器
            smtpObj.connect(mail_host, 25)
            # 登录到服务器
            smtpObj.login(mail_user, mail_pass)
            # 发送
            smtpObj.sendmail(
                sender, receivers, message.as_string())
            # 退出
            smtpObj.quit()
            print("success(email)")
            return True
        except smtplib.SMTPException as e:
            print('error', e)
            return False
