import requests
from bs4 import BeautifulSoup
from config import TABLE_URL

def parse_table():
    print("🔍 Парсер запущен (финальная версия)")

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
        row_text = row.get_text(strip=True)
        
        if 'Свердловский район' in row_text:
            found_district = True
            continue

        if not found_district:
            continue

        if 'район' in row_text and 'Свердловский' not in row_text:
            break

        # Ищем "Базайская" во всей строке
        if 'Базайская' in row_text:
            cols = row.find_all('td')
            if len(cols) >= 3:
                col1 = ' '.join(cols[0].text.split())
                col2 = ' '.join(cols[1].text.split())
                col3 = ' '.join(cols[2].text.split())
            else:
                col1 = ''
                col2 = ' '.join(row_text.split())
                col3 = ''
            
            # Чистим текст
            col1 = ' '.join(col1.split())
            col2 = ' '.join(col2.split())
            col3 = ' '.join(col3.split())
            
            results.append({
                'resource': col1,
                'address': col2,
                'period': col3,
                'is_planned': False,
                'day_type': 'сегодня'
            })

    print(f"✅ Найдено {len(results)} отключений")
    return results
