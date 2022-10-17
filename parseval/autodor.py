from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from .partools.partools import safe_to_sheet, reform_date, int_value_from_ru_month, Login, get_days, decorator, start_end, \
    save_to_log
from .partools.config import CONFIG


@decorator
def get_page(driver, tdate, to_scroll):
    for i in range(5):
        driver.execute_script("arguments[0].scrollTop = " + str(to_scroll),
                              driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[2]/div/div/div[2]'))
        time.sleep(1)
    while True:
        sp = BeautifulSoup(driver.page_source, 'html.parser').select('tr', class_="el-table__row")
        if sp == []:
            time.sleep(10)
            continue
        else:
            tr3 = sp[len(sp) - 1].find('td', class_='el-table_1_column_4').find('div', class_='el-tooltip').find(
                'span').get_text().replace("\t", " ").replace("\n", " ")
            break

    if reform_date(tr3) >= tdate:
        to_scroll += 500000
        del sp
        items = get_page(driver, tdate, to_scroll)
    else:
        items = []
        for tr in sp:
            if tr.find('b', class_='mr-5') is None:
                trassa = None
            else:
                trassa = tr.find('b', class_='mr-5').get_text()
            if tr.find('td', class_='el-table_1_column_3') is None:
                tr1 = None
            else:
                tr1 = tr.find('td', class_='el-table_1_column_3').find('div', class_='el-tooltip').find(
                    'span').find(
                    'span').get_text()
            if tr.find('td', class_='el-table_1_column_3') is None:
                tr2 = None
            else:
                tr2 = tr.find('td', class_='el-table_1_column_3').find('div', class_='el-table__sub-item').find(
                    'div',
                    class_='el-tooltip').find(
                    'span').find('span').get_text()
            if tr.find('td', class_='el-table_1_column_4') is None:
                tr3 = None
            else:
                tr3 = tr.find('td', class_='el-table_1_column_4').find('div', class_='el-tooltip').find(
                    'span').get_text().replace("\t", " ").replace("\n", " ")
            if tr.find('td', class_='el-table_1_column_5') is None:
                tr5 = None
            else:
                tr5 = tr.find('td', class_='el-table_1_column_5').find('div', class_='el-tooltip').find(
                    'span').get_text().replace("\t", " ").replace("\n", " ")
            if trassa is None:
                continue
            else:
                items.append({'Дата': datetime.strftime(reform_date(tr3), '%d.%m.%Y'),
                              'Номер авто': tr2,
                              'Трасса': trassa,
                              'Номер транспондера': tr1,
                              'Время': datetime.strftime(
                                  datetime.strptime(int_value_from_ru_month(tr3), "       %d %m %H:%M      "),
                                  '%H:%M'),
                              'Списание': -float(tr5.replace(' ', '').replace(',', '.'))})
        return items
    return items


@start_end
@decorator
def autodor(days=False, autodor_sheet=CONFIG['autodor_sheet']):
    if days is False:
        days = get_days(autodor_sheet)
    if days == 0:
        save_to_log('Все даты заполнены', 'warning')
        return False
    else:
        driver = Login('Autodor').login_to_site()
        tdate = datetime.strptime(str(datetime.today() - timedelta(days=days))[:10], '%Y-%m-%d')
        to_scroll = 100000
        time.sleep(15)
        items = get_page(driver, tdate, to_scroll)
        dic = []
        for k in range(1, days + 1):
            for i in items:
                if datetime.strptime(i['Дата'], '%d.%m.%Y') == datetime.strptime(
                        str(datetime.today() - timedelta(days=k))[:10], '%Y-%m-%d'):
                    dic.append(i)
        driver.close()
        dic.reverse()
        return safe_to_sheet(dic, autodor_sheet, 1)


if __name__ == '__main__':
    autodor()
