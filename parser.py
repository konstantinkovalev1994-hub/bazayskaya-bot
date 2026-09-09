from requests_html import HTMLSession
import re
from config import URL
from bs4 import BeautifulSoup

def parse_table(url=None):
    if url is None:
        url = URL
    
    print(f"📡 Запрос к {url} с рендерингом JavaScript...")
    
    session = HTMLSession()
    try:
        response = session.get(url)
        response.html.render(timeout=20, sleep=2)
        html_content = response.html.html
        print(f"✅ Страница загружена, длина: {len(html_content)} символов")
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        # Пробуем просто получить HTML без рендеринга
        try:
            response = session.get(url)
            html_content = response.html.html
            print(f"⚠️ Загружено без рендеринга, длина: {len(html_content)}")
        except Exception as e2:
            print(f"❌ Ошибка при повторной попытке: {e2}")
            return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')
    
    if not table:
        print("❌ Таблица не найдена на странице")
        # Сохраняем HTML для отладки
        with open('debug.html', 'w', encoding='utf-8') as f:
            f.write(html_content[:5000])
        print("📄 Сохранён debug.html для отладки")
        return []
    
    rows = table.find_all('tr')
    results = []
    found_district = False
    planned_found = False
    target_district = "Свердловский район"
    
    print(f"📊 Обработка {len(rows)} строк таблицы...")
    
    for row in rows[2:]:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
        
        col1 = cols[0].text.strip()
        col2 = cols[1].text.strip()
        col3 = cols[2].text.strip()
        
        if target_district in col1:
            print(f"🏢 Найден район: {col1}")
            found_district = True
            planned_found = False
            continue
        
        if not found_district:
            continue
        
        if col1 and 'Запланированные' not in col1 and col1 != '':
            if re.search(r'[а-яА-Я]', col1) and not re.search(r'\d', col1) and len(col1) < 30:
                print(f"🚪 Выход из района: {col1}")
                break
        
        if 'Запланированные отключения на завтра' in col1 or 'Запланированные отключения на завтра' in col2:
            planned_found = True
            print("📅 Запланированные на завтра")
            continue
        
        if col2 == '' or col2 is None:
            continue
        if col1 == '' and col2 == '' and col3 == '':
            continue
        
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
