# coding:utf-8
import requests
import os
import sys
import logging
import parsel
import json
import datetime
import time

from telethon.sync import TelegramClient
from telethon import functions

username = 'ismdeep@live.com'
password = '512china'

client = None
channel = None

host_domain = 'www.ustravel.cloud'
host_domain_url = 'https://' + host_domain
login_post_url = host_domain_url + '/dologin.php'
home_page_url = host_domain_url + '/clientarea.php'
service_list_url = host_domain_url + '/clientarea.php?action=services'


def init_logging():
    logging.basicConfig(
        filename='product.log',
        level=logging.DEBUG,
        format='%(asctime)s %(filename)s[%(levelname)s][line:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def get_headers():
    headers = {
        'Host': 'www.ustravel.cloud',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/85.0.4183.83 Safari/537.36 '
    }
    return headers


def check_login(__cookie__):
    headers = get_headers()
    headers['Cookie'] = __cookie__
    req = requests.get(
        url=home_page_url,
        headers=headers
    )
    content = req.text
    return content.find("logout.php") >= 0


def get_cookie():
    cookie_path = 'cookie.txt'
    if not os.path.isfile(cookie_path):
        file = open(cookie_path, 'w')
        file.close()
    cookie = open(cookie_path, 'r').readline()
    if cookie == '' or not check_login(cookie):
        cookie = gen_new_cookie()
        f = open(cookie_path, 'w')
        f.write(cookie)
        f.flush()
        f.close()
    return cookie


def gen_new_cookie():
    logging.info("get_new_cookie()")
    req = requests.get(
        url=home_page_url
    )
    cookie = req.cookies.items()
    for key, value in req.cookies.items():
        cookie = "%s=%s" % (key, value)
    content = req.text
    csrf_token = content[content.find("var csrfToken = '") + len("var csrfToken = '"):]
    csrf_token = csrf_token[:csrf_token.find("'")]
    headers = get_headers()
    headers['Cookie'] = cookie
    login_req = requests.post(
        url=login_post_url,
        data={
            'token': csrf_token,
            'username': username,
            'password': password
        },
        headers=headers,
        allow_redirects=False
    )
    for key, value in login_req.headers.items():
        if key == "Set-Cookie":
            cookie = value[:value.find(';')]
    return cookie


def get_product_info(__url__, __cookie__):
    headers = get_headers()
    headers['Cookie'] = __cookie__
    req = requests.get(
        url=host_domain_url + __url__,
        headers=headers
    )
    content = req.text
    info_data = parsel.Selector(content)
    product_name = info_data.xpath('//div[@class="product-title"]/text()').extract()[0]
    renew_url = info_data.xpath('//a[@class="renew-btn"]/@href').extract()[0]
    next_pay_date = info_data.xpath('//div[@class="product-date"]/text()').extract()[1].strip()[len('下次付款 : '):]
    used_mount = info_data.xpath('//p[@class="traffic-text"]/text()').extract()[0].strip()[len('已用流量 : '):]
    used_mount = used_mount[:used_mount.find('GB')].strip()
    available_mount = info_data.xpath('//p[@class="traffic-text"]/text()').extract()[1].strip()[len('剩余流量  : '):]
    available_mount = available_mount[:available_mount.find('GB')].strip()
    return {
        'name': product_name,
        'renew_url': renew_url,
        'next_pay_date': next_pay_date,
        'used': used_mount,
        'available': available_mount
    }


def get_product_list(__cookie__):
    headers = get_headers()
    headers['Cookie'] = __cookie__
    req = requests.get(
        url=service_list_url,
        headers=headers
    )
    content = req.text
    html = parsel.Selector(content)
    items = html.xpath('//table[@id="tableServicesList"]//span[@class="label status status-active"]/../..').extract()
    products = []
    for item_raw in items:
        item_data = parsel.Selector(item_raw)
        href = item_data.xpath('//a[@class="btn btn-block btn-info"]/@href').extract()[0]
        product_id = href[href.find('&id=') + 4:]
        product_name = item_data.xpath('//strong/text()').extract()[0]
        product_port = int(item_data.xpath('//td[1]/a/text()').extract()[0])
        products.append({
            'url': '/clientarea.php?action=productdetails&id=' + product_id,
            'name': product_name,
            'port': product_port,
            'info': get_product_info('/clientarea.php?action=productdetails&id=' + product_id, __cookie__)
        })
    return products


def send_product_list(__products__):
    for product in __products__:
        message_text = "%s(%s)\n下次付款：%s\n已用流量：%s GB\n剩余流量：%s GB" % (
            product['name'], product['port'], product['info']['next_pay_date'],
            product['info']['used'], product['info']['available']
        )
        client(functions.messages.SendMessageRequest(
            peer=channel,
            message=message_text,
            no_webpage=True
        ))
    logging.info("Email sent successfully.")


def main():
    cookie = get_cookie()
    products = get_product_list(cookie)
    send_product_list(products)
    client.disconnect()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 ustravel-info.py {work_dir}')
        exit(0)
    os.chdir(sys.argv[1])
    init_logging()

    # Set Telegram Bot
    telegram_bot_config = json.load(open('telegram_bot.json', 'r'))
    client = TelegramClient('anon', telegram_bot_config['api_id'], telegram_bot_config['api_hash'])
    client.connect()
    channel = client.get_entity(telegram_bot_config['channel_share_link'])
    # Start main()
    main()
