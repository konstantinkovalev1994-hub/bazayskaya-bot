import requests
from bs4 import BeautifulSoup
from config import TABLE_URL

def parse_table():
    print("🔍 Парсер запущен")
    
    # Прямой запрос к HTML-файлу
    response = requests.get(TABLE_URL)
    response.encoding = 'windows-1251'
    html = response.text
    
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    
    if not table:
        print("❌ Таблица не найдена")
        return []
    
    rows = table.find_all('tr')
    results = []
    found = False
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
        
        col1 = cols[0].text.strip()
        col2 = cols[1].text.strip()
        col3 = cols[2].text.strip()
        
        # Ищем Свердловский район
        if 'Свердловский район' in col1:
            found = True
            continue
        
        if not found:
            continue
        
        # Выход из района — следующий район
        if col1 and 'район' in col1 and 'Свердловский' not in col1:
            break
        
        # Ищем "Южная"
        if 'Южная' in col2:
            print(f"✅ Найдено: {col2[:100]}")
            results.append({
                'resource': col1,
                'address': col2,
                'period': col3,
                'is_planned': False
            })
    
    print(f"✅ Найдено {len(results)} отключений")
    return results
