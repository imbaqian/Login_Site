# -*- conding:utf-8 -*-

'''爬知乎妹子图片
'''

import requests
import http.cookiejar
import re
import os.path
import time
import json
import threading
class zhihu(object):
    '''知乎模拟登陆
    '''
    def __init__(self, username, password):
        #username password
        self. __username = username
        self.__password = password
        # headers
        self. headers = {'Host': 'www.zhihu.com',
           'Upgrade-Insecure-Requests': '1',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36'
        }
        #session
        self.session = requests.Session()
        self.session.cookies = http.cookiejar.LWPCookieJar(filename='zhihu_cookies')
        try:
            self.session.cookies.load(ignore_discard=True)
        except:
            print('There is not cookies file!')
        #object url
        self.url = 'https://www.zhihu.com'
    def isLogin(self):
        '''判断是否登陆
        '''
        url = self.url + '/settings/profile'
        self.headers['Refere'] = 'https://www.zhihu.com/'
        login_code = self.session.get(url, allow_redirects=False, headers=self.headers).status_code
        self.headers.pop('Refere')
        if login_code == 200:
            return True
        else:
            return False
    def __get_xsrf(self):
        response = self.session.get(self.url, headers=self.headers)
        html = response.text
        pattern = r'name="_xsrf" value="(.*?)"'
        _xsrf = re.findall(pattern, html)
        if _xsrf:
            return _xsrf[0]
        else:
            print('_xsrf not found!')

    def __get_captcha(self):
        '''获取验证码，并手动输入
        '''
        captcha_time = int(time.time()*1000)
        captcha_url = self.url + '/captcha.gif?r=%d&type=login&lang=cn' % captcha_time
        response = self.session.get(captcha_url, headers=self.headers)
        with open('captcha.jpg', 'wb') as fp:
            fp.write(response.content)
            print(u'请到 %s 目录找到captcha.jpg 手动输入' % os.path.abspath('captcha.jpg'))
        
        captcha_position = [[33.25/2, 44.52/2], [78.34/2, 51.23/2], [131.53/2, 53.26/2], [183.34/2, 49.53/2], [224.34/2, 50.43/2], [265.43/2, 49.45/2], [312.34/2, 46.76/2]]
        cap_num  = input('图中有几个倒立的字？\n')
        word_pos = input('图中倒立字是第几个？\n')
        word_pos = word_pos.replace(' ', '')
        word_pos = list(word_pos)
        points = []
        for n in range(int(cap_num)):
            points.append(captcha_position[int(word_pos[n])-1])
        captcha = {
            'img_size' : [200, 44],
            'input_points' : points
        }

        #json
        captcha = json.dumps(captcha)
        return captcha

    def login(self):
        self.__xsrf = self.__get_xsrf()
        self.headers['X-Xsrftoken'] = self.__xsrf
        self.headers['X-Requested-With'] = 'XMLHttpRequest'
        self.headers['Origin'] = 'https://www.zhihu.com'

        login_url = self.url + '/login/phone_num'

        #登陆post数据包（没有验证码）
        login_data = {
            '_xsrf': self.__xsrf,
            'password': self.__password,
            'captcha_type': 'cn',
            'phone_num': self.__username
        }
        login_page = self.session.post(login_url, data=login_data, headers=self.headers)
        login_code = login_page.json()        
        #没有验证码登陆失败,需要验证码
        if login_code['r'] == 1:
            #多一个验证码的数据
            login_data['captcha'] = self.__get_captcha()
            login_page = self.session.post(login_url, data=login_data, headers=self.headers)
            
        #登陆成功后保存cookies
        self.session.cookies.save()

#  任务分配
def coroutine(func):
    def wrapper(*args, **kwargs):
        cr = func(*args, **kwargs)  
        try:
            next(cr)
        except StopIteration: 
            pass
        return cr
    return wrapper

@coroutine
def downloader_dispatch():
    thread_list = []
    while True:
        pic_url_list, pagenum = (yield)
        if pagenum == 0:
            break;
        t = threading.Thread(target=downloader,args=(pic_url_list, pagenum))
        thread_list.append(t)
        t.start()
    for t in thread_list:
        t.join()
    
# 下载器
def downloader(url_list, pagenum):
    headers = { 'authority': 'pic2.zhimg.com',
                'method': 'GET',
                'scheme': 'https',
                'referer': 'https://www.zhihu.com/collection/38624707?page=%d' % (pagenum),
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36'}
    for url in url_list:
        headers['path'] = url[22:]
        response = requests.get(url, headers=headers,timeout=10)
        with open('./pic' + headers['path'], 'wb') as fp:
            fp.write(response.content)
    print('第%d页图片下载完毕！' % pagenum)

if __name__ == '__main__':
    zh = zhihu('输入你的手机号', '密码')
    if zh.isLogin():
        print('login')
    else:
        print('notlogin')
        zh.login()
    #图片存储目录
    if not os.path.exists('pic'):
        os.mkdir('pic')

    #目标页面
    objurl = 'https://www.zhihu.com/collection/38624707?page=1'
    response = zh.session.get(objurl, headers=zh.headers)
    pattern_num = r'href="\?page=(.*?)"'
    page_num = re.findall(pattern_num, response.text)
    #最大页面数
    pageMax = int(page_num[-2])
    print('总共%d页图片' % (pageMax))
    downdis = downloader_dispatch()
    for pagenum in range(pageMax):
        objurl = 'https://www.zhihu.com/collection/38624707?page=%d' % (pagenum+1)
        response = zh.session.get(objurl, headers=zh.headers)
        pattern_pic_url = r'data-original=&quot;(.*?)&quot'
        pic_url_list = re.findall(pattern_pic_url, response.text)
        downdis.send((pic_url_list, pagenum+1))
    #结束标志
    downdis.send([],0)