import requests
from urllib import parse
from datetime import datetime, timedelta, time
from .partools.partools import safe_to_sheet, Login, get_sheet_values, get_days, decorator, start_end, save_to_log,update_wialon_token,er_for_telegramm
from .partools.config import CONFIG


@decorator
def get_page(days, dic):
    replace_list = ['Iveco', 'MB', 'Scania', 'ДУТ', 'МАЗ', 'добавить', '(t°C)', 'ble', '(t°C)', '(', ')', ' ']
    token = CONFIG['token_wialon']
    url = 'https://hst-api.wialon.com/wialon/ajax.html?svc=token/login&params={"token":"' + token + '"}'
    r = requests.post(url=url, ).json()
    try:
        if 'error' in r:
            driver = Login('Wialon').login_to_site()
            token = parse.urlparse(driver.current_url).query.split("&")[1][13::]
            update_wialon_token(token,CONFIG)
            url = 'https://hst-api.wialon.com/wialon/ajax.html?svc=token/login&params={"token":"' + token + '"}'
            driver.close()
    except BaseException as r:
        save_to_log('Ошибка получения нового токена ' + str(r),'error')
    try:
        r = requests.post(url=url).json()
        eid = '&sid=' + r['eid']
        date_time_1 = int(datetime.combine(datetime.today() - timedelta(days=days), time(0)).timestamp())
        date_time_2 = int(datetime.combine(datetime.today() - timedelta(days=days), time(23, 59)).timestamp())
        url = 'https://hst-api.wialon.com/wialon/ajax.html?svc=report/exec_report&params={"reportResourceId":22719818,"reportTemplateId":19,"reportTemplate":null,"reportObjectId":25708863,"reportObjectSecId":0,"interval":{"from":' + str(
            date_time_1) + ',"to":' + str(date_time_2) + ',"flags":0}}' + eid
        r = requests.post(url=url).json()
        rows = r['reportResult']['tables'][0]['rows']
        url = 'https://hst-api.wialon.com/wialon/ajax.html?svc=report/get_result_rows&params={"tableIndex":0,"indexFrom":0,"indexTo":' + str(
            rows) + '}' + eid
        r = requests.post(url=url).json()
        toplivo = get_sheet_values(CONFIG['spravochnik_topliva'])
        try:
            for val in r:
                tyg = str(val['c'][0])
                for i in replace_list:
                    tyg = tyg.replace(i, '')
                p1 = float(val['c'][1].replace(' km', ''))
                p2 = float(val['c'][2].replace(' l', ''))
                p3 = float(val['c'][3].replace(' l', ''))
                p4 = float(val['c'][4].replace(' l/100 km', ''))
                p5 = float(val['c'][5].replace(' l/100 km', ''))
                p7 = 'Error'
                p8 = 'Error'
                p9 = None

                if (p5 < 18 or p5 > 40) and (p4 < 18 or p4 > 40):
                    p9 = 'ДАРТ и ДУТ некорректны'
                    er_for_telegramm(p9,'Wialon')
                elif (p5 < 18 or p5 > 40) and (p4 >= 18 or p4 <= 40):
                    p7 = 'ДУТ некорректный'
                elif (p4 < 18 or p4 > 40) and (p5 >= 18 or p5 <= 40):
                    p8 = 'ДАРТ некорректный'

                if p1 < 20:
                    p6 = None
                    p9 = 'Недостаточный пробег'
                    er_for_telegramm(p9,'Wialon')
                elif p9 == 'ДАРТ и ДУТ некорректны':
                    p6 = None
                elif p8 == 'ДАРТ некорректный':
                    p6 = p5
                    p9 = p8
                    er_for_telegramm(p9,'Wialon')
                elif p7 == 'ДУТ некорректный':
                    p6 = p4
                    p9 = p7
                    er_for_telegramm(p9,'Wialon')
                elif abs(p4 - p5) > 5:
                    if p4 > p5:
                        p6 = p4
                    else:
                        p6 = p5
                    p9 = 'Дельта ДАРТ/ДУТ больше 5л'
                    er_for_telegramm(p9,'Wialon')
                elif abs(p5 - p4) > 5:
                    p6 = p4
                    p9 = 'Дельта ДАРТ/ДУТ больше 5л'
                    er_for_telegramm(p9,'Wialon')
                else:
                    p6 = (p4 + p5) / 2
                if p6 is None:
                    p10 = 0
                else:
                    p10 = (p6 * p1 / 100)
                    p6 = round(p6, 2)
                date = datetime.today() - timedelta(days=days)
                toplivo_price = 0
                for i in toplivo:
                    if datetime.strptime(i['Месяц'], '%m.%Y').month == date.month:
                        if i['Цена'] != '':
                            toplivo_price = i['Цена']
                            break
                if toplivo_price != 0:
                    dic.append(
                        {
                            'Дата': date.strftime('%d.%m.%Y'),
                            'Тягач': tyg.upper(),
                            'Пробег в поездках': round(p1, 2),
                            'Потрачено по ДАРТ': round(p2, 2),
                            'Потрачено по ДУТ': round(p3, 2),
                            'Потрачено скорректированный': round(p10, 2),
                            'Стоимость топлива': round(-p10 * float(toplivo_price.replace(',', '.')), 2),
                            'Ср. расход по ДАРТ': round(p4, 2),
                            'Ср. расход по ДУТ': round(p5, 2),
                            'Скорректированный расход': p6,
                            'Комментарий': p9
                        }
                    )
                else:
                    save_to_log('Нет стоимости топлива за месяц ' + str(date.month),'error')
                    return False
            url = 'https://hst-api.wialon.com/wialon/ajax.html?svc=core/logout&params={}' + eid
            r = requests.post(url=url).json()
            return r
        except BaseException as r:
            save_to_log('Ошибка записи данных Wialon' + str(r),'error')
    except BaseException as r:
        save_to_log('Ошибка получения данных от Wialon' + str(r),'error')


@start_end
@decorator
def wialon(days=False, wialon_sheet=CONFIG['wialon_sheet']):
    if days is False:
        days = get_days(wialon_sheet)
    if days == 0:
        save_to_log('Все даты заполнены', 'warning')
        return False
    else:
        dic = []
        for i in range(1, days + 1):
            r = get_page(i, dic)
            if r != {'error': 0}:
                save_to_log('Ошибка модуля wialon','error')
                return False
        dic.reverse()

    return safe_to_sheet(dic, wialon_sheet, 1)


if __name__ == '__main__':
    wialon()
