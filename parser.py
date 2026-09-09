import requests
from bs4 import BeautifulSoup
from config import TABLE_URL

def parse_table():
    print("🔍 Парсер запущен (прямой вывод)")

    try:
        response = requests.get(TABLE_URL, timeout=30)
        response.encoding = 'windows-1251'
        html = response.text
        print(f"✅ Страница загружена, длина: {len(html)} символов")
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')

    if not table:
        print("❌ Таблица не найдена")
        return []

    rows = table.find_all('tr')
    print(f"📊 Найдено строк: {len(rows)}")

    # Выводим ВСЕ строки таблицы в логи
    for index, row in enumerate(rows):
        cols = row.find_all('td')
        if len(cols) >= 3:
            col1 = cols[0].text.strip()[:50]
            col2 = cols[1].text.strip()[:100]
            col3 = cols[2].text.strip()[:50]
            print(f"📌 Строка {index}: col1='{col1}', col2='{col2}', col3='{col3}'")
        elif len(cols) == 1 and row.text.strip():
            print(f"📌 Строка {index}: ОДНА КОЛОНКА: '{row.text.strip()}'")

    # Теперь пробуем найти "Южная" и Свердловский район
    print("\n🔍 Ищем Свердловский район и Южную...")
    found_district = False

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
        
        col1 = cols[0].text.strip()
        col2 = cols[1].text.strip()
        col3 = cols[2].text.strip()
        
        if 'Свердловский район' in col1:
            print(f"🏢 Найден Свердловский район в строке!")
            found_district = True
            continue

        if found_district and 'Южная' in col2:
            print(f"🎯 НАЙДЕНА ЮЖНАЯ в col2: '{col2}'")
            return [{
                'resource': col1,
                'address': col2,
                'period': col3,
                'is_planned': False,
                'day_type': 'сегодня'
            }]

        # Если нашли следующий район, выходим
        if found_district and col1 and 'район' in col1 and 'Свердловский' not in col1:
            print(f"🚪 Выход: найден следующий район - '{col1}'")
            break

    print("❌ Ничего не найдено.")
    return []
