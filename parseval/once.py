import pandas as pd
import numpy as np
from .partools.partools import safe_to_sheet, chek_date, get_tclist, save_file_for_1c, get_sheet_values, decorator, \
    start_end, \
    save_to_log, er_for_telegramm
from .partools.config import CONFIG


@start_end
@decorator
def onec(days=None, onec_sheet=CONFIG['onec_sheet']):
    save_file_for_1c('./' + CONFIG['file_1c'])
    try:
        pd.set_option('display.max_rows', None)

        # Импорт исходных данных
        raw_data = pd.read_excel('./' + CONFIG['file_1c'])
        raw_data = raw_data.rename(columns={'Заявка': 'Номер', 'Unnamed: 1': 'Заявка'})

        # Отбор нужных признаков
        df = raw_data[['Заявка', 'Дата погрузки', 'Заказчик', 'Маршрут', 'Перевозчик',
                       'Водитель', 'Тягач (а/м)', 'Тип', 'Сумма заказчик', 'Сумма перевозчик',
                       'Дата окончания заявки']][
             :-1]
        df['Тягач (а/м)'] = df['Тягач (а/м)'].str.replace(' ', '')
        df['Заявка'] = df['Заявка'].str.replace(' ', '').astype(int)
        df = df[df['Заказчик'] != 'МТК ООО']

        # Заполнение направления
        napravleni = get_sheet_values(CONFIG['spravochnik_napravleni'])
        region_list = []
        far_region_list = []
        for i in napravleni:
            region_list.append(i[list(i.keys())[0]])
            if list(i.values())[1] != '':
                far_region_list.append(i[list(i.keys())[0]])
        df["direction"] = df["Маршрут"].str.extract(f"({'|'.join(region_list)})")
        df["direction"] = df["direction"].fillna('Москва и МО')
        df.loc[df["direction"] != 'Москва и МО', 'direction'] = 'Межгород'

        # Заполнение направления для расчета зп
        df["direction_salary_calc"] = df["Маршрут"].str.extract(f"({'|'.join(far_region_list)})")
        df["direction_salary_calc"] = df["direction_salary_calc"].fillna('Москва и МО')
        df.loc[df["direction_salary_calc"] != 'Москва и МО', 'direction_salary_calc'] = 'Межгород'

        # Конвертация текста в число
        df['Сумма заказчик'] = df['Сумма заказчик'].str.replace(' ', '')
        df['Сумма заказчик'] = df['Сумма заказчик'].str.replace(',', '.')
        df['Сумма заказчик'] = df['Сумма заказчик'].astype(float)

        df['Сумма перевозчик'] = df['Сумма перевозчик'].str.replace(' ', '')
        df['Сумма перевозчик'] = df['Сумма перевозчик'].str.replace(',', '.')
        df['Сумма перевозчик'] = df['Сумма перевозчик'].astype(float)

        # Заполнение группы заказчиков
        df.loc[df['Заказчик'] == 'ЯНДЕКС ООО', 'client_group'] = 'ЯНДЕКС ООО'
        df.loc[df['Заказчик'] == 'ИНТЕРНЕТ РЕШЕНИЯ ООО', 'client_group'] = 'ИНТЕРНЕТ РЕШЕНИЯ ООО'
        df['client_group'].fillna('Другое', inplace=True)


        own_park, renters, hiredcar = get_tclist(CONFIG['spravochnik_tc'])

        own_park = pd.DataFrame(data=own_park).squeeze()
        renters = pd.DataFrame(data=renters).squeeze()
        hired_car = pd.DataFrame(data=hiredcar)['ТС'].squeeze()

        # Заполнение группы машин
        df.loc[df['Тягач (а/м)'].isin(own_park), 'vehicle_group'] = 'Собственный парк'
        df.loc[df['Тягач (а/м)'].isin(renters), 'vehicle_group'] = 'Арендаторы'
        df.loc[df['Тягач (а/м)'] == 'Х921РТ190', 'vehicle_group'] = 'МАЗ ВБД'
        df.loc[df['Тягач (а/м)'].isin(hired_car), 'vehicle_group'] = 'Наемники'

        """order_count = df.groupby(['Тягач (а/м)', 'Дата погрузки'])['Заявка'].count().reset_index(name="order_count")
        df = pd.merge(df, order_count, how='left',
                      left_on=['Тягач (а/м)', 'Дата погрузки'],
                      right_on=['Тягач (а/м)', 'Дата погрузки'])"""

        # Подчсчет рейсов в сутки
        oc = pd.DataFrame(df[['Заявка', 'Тягач (а/м)', 'Дата погрузки', 'vehicle_group']])
        oc = oc[(oc['vehicle_group'] != 'Наемники') & (oc['vehicle_group'] != 'Арендаторы') & (
                df['direction_salary_calc'] != 'Межгород')]
        oc['count'] = oc.groupby(['Тягач (а/м)', 'Дата погрузки']).cumcount() + 1
        oc.drop('vehicle_group', axis=1, inplace=True)

        df = pd.merge(df, oc, how='left', on=['Заявка', 'Тягач (а/м)', 'Дата погрузки']
                      )
        order_count = df.groupby(['Тягач (а/м)', 'Дата погрузки'])['Заявка'].count().reset_index(name="order_count")
        df = pd.merge(df, order_count, how='left',
                      left_on=['Тягач (а/м)', 'Дата погрузки'],
                      right_on=['Тягач (а/м)', 'Дата погрузки'])

        # Заполнение ставки водителям
        df.loc[df['direction_salary_calc'] == 'Межгород', 'drivers_salary'] = 4200
        df.loc[(df['count'] == 1) & (df['order_count'] == 1), 'drivers_salary'] = 4000
        df.loc[(df['count'] == 1) & (df['order_count'] > 1), 'drivers_salary'] = 2500
        df.loc[(df['count'] > 1) & (df['order_count'] > 1), 'drivers_salary'] = 2000
        df.loc[df['vehicle_group'] == 'Наемники', 'drivers_salary'] = 0
        df.loc[(df['vehicle_group'] == 'Арендаторы') & (df['direction'] == 'Москва и МО'), 'drivers_salary'] = 4000
        df.loc[(df['vehicle_group'] == 'Арендаторы') & (df['direction'] == 'Межгород'), 'drivers_salary'] = 8000

        dic = df.replace({np.nan: ''}).values.tolist()
        try:
            perevozchiki = []
            for i in range(len(hiredcar['ТС'])):
                perevozchiki.append([hiredcar['ТС'][i], hiredcar['Перевозчик'][i]])
            d2 = []
            for i in dic:
                s15 = ''
                yr = ''
                s9 = i[8]
                s10 = ''
                s14 = i[4]
                if s9 != '':
                    if s9 < 3000 or s9 > 100000:
                        s15 = 'Некоректная ставка'
                        er_for_telegramm(s15, '1C')
                else:
                    s15 = 'Некоректная ставка'
                    er_for_telegramm(s15, '1C')
                if i[14] == 'Наемники':
                    if i[9] != '':
                        if i[9] < 4000 or i[9] > 20000:
                            s15 = 'Некоректная ставка'
                            er_for_telegramm(s15, '1C')
                        s10 = -i[9]
                    else:
                        s15 = 'Некоректная ставка'
                        er_for_telegramm(s15, '1C')
                if i[14] == '':
                    s15 = 'Неопознаное тс'
                    er_for_telegramm(s15, '1C')
                if i[14] == 'Наемники':
                    if s14 == '':
                        for k in perevozchiki:
                            if k[0] == i[6]:
                                s14 = k[1]
                if i[17] != '':
                    s17 = -i[17]
                else:
                    s17 = ''
                    s15 = 'Некоректная ставка'
                    er_for_telegramm(s15, '1C')
                if i[1] != '':
                    yr, s2 = chek_date(i[1], i[0])
                else:
                    s2 = ''
                if i[10] != '':
                    yr2, s11 = chek_date(i[10], i[0])
                else:
                    s11 = ''

                d2.append(
                    {
                        'Заявка': i[0],
                        'Год заявки': yr,
                        'Дата погрузки': s2,
                        'Заказчик': i[2],
                        'Группа клиентов': i[13],
                        'Маршрут': i[3],
                        'Группа направлений': i[11],
                        'Группа ТС': i[14],
                        'Перевозчик': s14,
                        'Водитель': i[5],
                        'ТС': i[6],
                        'Тип': i[7],
                        'Сумма заказчик': s9,
                        'Ставка водителю': s17,
                        'Кол-во заказов за день': i[16],
                        'Дата окончания заявки': s11,
                        'Сумма перевозчик': s10,
                        'Комментарий': s15
                    }
                )
            return safe_to_sheet(d2, onec_sheet, 2)
        except BaseException as r:
            save_to_log('Ошибка записи в словарь ' + str(r), 'error')
            return False
    except BaseException as r:
        save_to_log('Ошибка чтения файла ' + str(r), 'error')
        return False


if __name__ == '__main__':
    onec()
