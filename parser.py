import requests
from bs4 import BeautifulSoup
from config import TABLE_URL

def parse_table():
    print("🔍 Парсер запущен (поиск по всей строке)")

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
    results = []
    found_district = False

    for row in rows:
        # Берем ВЕСЬ текст строки
        row_text = row.get_text(strip=True)
        
        # Ищем начало Свердловского района
        if 'Свердловский район' in row_text:
            found_district = True
            print(f"🏢 Найден Свердловский район в строке: {row_text[:50]}")
            continue

        if not found_district:
            continue

        # Выход из района - если встречаем другой район
        if 'район' in row_text and 'Свердловский' not in row_text:
            print(f"🚪 Выход: найден другой район")
            break

        # Ищем "Южная" во всей строке
        if 'Южная' in row_text:
            print(f"🎯 НАЙДЕНА ЮЖНАЯ в строке: {row_text[:200]}")
            
            # Пытаемся извлечь данные из ячеек
            cols = row.find_all('td')
            if len(cols) >= 3:
                col1 = cols[0].text.strip()
                col2 = cols[1].text.strip()
                col3 = cols[2].text.strip()
            else:
                # Если ячеек нет - сохраняем всю строку
                col1 = ''
                col2 = row_text
                col3 = ''
            
            results.append({
                'resource': col1,
                'address': col2 if col2 else row_text,
                'period': col3,
                'is_planned': False,
                'day_type': 'сегодня'
            })

    print(f"✅ Найдено {len(results)} отключений")
    return results
