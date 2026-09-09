import requests
from bs4 import BeautifulSoup
import re
from config import URL

def parse_table(url=None):
    """
    Парсит таблицу отключений
    """
    if url is None:
        url = URL
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    try:
        print(f"📡 Запрос к {url}...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
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
    
    target_district = "Свердловский район"
    found_district = False
    planned_found = False
    
    print(f"📊 Обработка {len(rows)} строк таблицы...")
    
    for row in rows[2:]:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
        
        col1 = cols[0].text.strip()
        col2 = cols[1].text.strip()
        col3 = cols[2].text.strip()
        
        if target_district in col1:
            found_district = True
            planned_found = False
            continue
        
        if not found_district:
            continue
        
        if col1 and 'Запланированные' not in col1 and col1 != '':
            if re.search(r'[а-яА-Я]', col1) and not re.search(r'\d', col1) and len(col1) < 30:
                break
        
        if 'Запланированные отключения на завтра' in col1 or 'Запланированные отключения на завтра' in col2:
            planned_found = True
            continue
        
        if col2 == '' or col2 is None:
            continue
        if col1 == '' and col2 == '' and col3 == '':
            continue
        
        if 'Базайская' in col2:
            results.append({
                'resource': col1,
                'address': col2,
                'period': col3,
                'is_planned': planned_found,
                'day_type': 'завтра' if planned_found else 'сегодня'
            })
    
    print(f"✅ Найдено {len(results)} отключений")
    return results