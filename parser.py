import requests
from bs4 import BeautifulSoup
import re
from config import TABLE_URL

def parse_table(url=None):
    if url is None:
        url = TABLE_URL
    
    print(f"📡 Запрос к {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'windows-1251'
        html_content = response.text
        print(f"✅ Страница загружена, длина: {len(html_content)} символов")
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')
    
    if not table:
        print("❌ Таблица не найдена на странице")
        return []
    
    rows = table.find_all('tr')
    results = []
    found_district = False
    planned_found = False
    target_district = "Свердловский район"
    
    print(f"📊 Обработка {len(rows)} строк таблицы...")
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
        
        col1 = cols[0].text.strip()
        col2 = cols[1].text.strip()
        col3 = cols[2].text.strip()
        
        # Проверяем начало Свердловского района
        if target_district in col1:
            print(f"🏢 Найден район: {col1}")
            found_district = True
            planned_found = False
            continue
        
        if not found_district:
            continue
        
        # Проверяем новый район (выход)
        if col1 and 'Запланированные' not in col1 and col1 != '':
            if re.search(r'[а-яА-Я]', col1) and not re.search(r'\d', col1) and len(col1) < 30:
                print(f"🚪 Выход из района: {col1}")
                break
        
        # Проверяем маркер "Запланированные на завтра"
        if 'Запланированные отключения на завтра' in col1 or 'Запланированные отключения на завтра' in col2:
            planned_found = True
            print("📅 Запланированные на завтра")
            continue
        
        if col2 == '' or col2 is None:
            continue
        if col1 == '' and col2 == '' and col3 == '':
            continue
        
        # 🔥 Ищем "Южная"
        if 'Южная' in col2:
            print(f"✅ НАЙДЕНА ЮЖНАЯ! col1: {col1}, col2: {col2[:100]}")
            results.append({
                'resource': col1,
                'address': col2,
                'period': col3,
                'is_planned': planned_found,
                'day_type': 'завтра' if planned_found else 'сегодня'
            })
    
    print(f"✅ Найдено {len(results)} отключений")
    return results
