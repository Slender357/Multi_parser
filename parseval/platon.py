import requests
from datetime import datetime, timedelta
from .partools.partools import safe_to_sheet, Login, get_days, decorator, start_end, save_to_log
from bs4 import BeautifulSoup
from .partools.config import CONFIG


@decorator
def get_headers(headers, td, tdz, driver):
    for request in driver.requests:
        if str(request.url) == 'https://lk.platon.ru/accounts/49853/operations?start_date=' + td.strftime(
                '%d.%m.%Y') + '&end_date=' + tdz.strftime(
            '%d.%m.%Y') \
                + '&operation_type=all&grnz_search_submit=&grnz=&page=1':
            XCSRFToken = request.headers['X-CSRF-Token']
            Cookie = request.headers['Cookie']
            IfNoneMatch = request.headers['If-None-Match']
            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Cookie': Cookie,
                'Host': 'lk.platon.ru',
                'If-None-Match': IfNoneMatch,
                'Referer': 'https://lk.platon.ru/accounts/49853',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
                'X-CSRF-Token': XCSRFToken,
                'X-Requested-With': 'XMLHttpRequest',
                'sec-ch-ua': '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': 'macOS'
            }
    return headers


@decorator
def get_page(start_date, end_date, page, headers, dic):
    url = 'https://lk.platon.ru/accounts/49853/operations?start_date=' + start_date.strftime(
        '%d.%m.%Y') + '&end_date=' + end_date.strftime(
        '%d.%m.%Y') + '&operation_type=all&grnz_search_submit=&grnz=&page=' + str(page)
    r = requests.get(url=url, headers=headers).json()
    total_pages = r['total_pages']
    for val in r['operations']:
        if val['operation_type_name'] != 'Начисление Платы (БУ)' and val['operation_type_name'] != 'Charging (OBU)':
            # print(val['operation_type_name'])
        # if val['operation_type_name'] != 'Начисление Платы (БУ)':
            continue
        else:
            dic.append(
                {
                    'Дата': val['operation_dt'],
                    'ГРЗ': val['vehicle_grnz'],
                    'ПУТЬ ПО ФЕД. ТРАССАМ, КМ': val['distance'],
                    'СПИСАНИЕ': -float(val['debit_amount'])
                }
            )
    if total_pages > page:
        get_page(start_date, end_date, page + 1, headers, dic)



@start_end
@decorator
def platon(days=False, platon_sheet=CONFIG['platon_sheet']):
    if days is False:
        days = get_days(platon_sheet)
    if days == 0:
        save_to_log('Все даты заполнены', 'warning')
        return False
    else:
        first_date = datetime.strptime((datetime.today() - timedelta(days=days)).strftime('%d.%m.%Y'), '%d.%m.%Y')
        last_date = datetime.strptime(datetime.today().strftime('%d.%m.%Y'), '%d.%m.%Y')
        driver = Login('Platon').login_to_site()
        sp = BeautifulSoup(driver.page_source, 'html.parser')
        serchdate = sp.find('input', class_='b-form-group__input')['value']
        td = datetime.strptime(serchdate, '%d.%m.%Y')
        tdz = datetime.strptime(serchdate, '%d.%m.%Y') + timedelta(days=1)
        headers = get_headers({}, td, tdz, driver)
        dic = []
        while first_date != last_date:
            start_date = first_date
            end_date = first_date + timedelta(days=1)
            get_page(start_date, end_date, 1, headers, dic)
            first_date = first_date + timedelta(days=1)
        driver.close()
        return safe_to_sheet(dic, platon_sheet, 1)


if __name__ == '__main__':
    platon()
