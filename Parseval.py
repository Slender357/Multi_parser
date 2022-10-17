from parseval import platon, wialon, autodor, onec
from parseval.partools.partools import sent_to_tbot

# При запуске Parseval идет добавление новых данных с даты на последней строке на соответствующей модулю странице Google Sheets
# Если добавить числовой аргумент в модули парсинга Platon, Wialon или Autodor, то глубина парсинга будет равна количеству заданных дней.
# Пример: platon(1) - глубина прасинга один день - вчера; platon(2) - глубина прасинга два дня - вчера и позавчера.
# Если модуль запущен с аргументом и в соответсвуюущей таблице уже есть хотя бы одна дата, как в данных парсинга, модуль выдаст исключение и остановится.
# Модуль Onec обрабатывает файл находящий на диске Google Drive в папке доступной системному аккаунту.
if __name__ == '__main__':
    funcs = [onec, autodor, wialon, platon]
    d = []
    for i in funcs:
        d.append(
            {
                i.__name__: i()
            }
        )
    sent_to_tbot(d)
