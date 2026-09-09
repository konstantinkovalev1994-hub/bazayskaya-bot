import hashlib

storage = {}

def generate_key(item):
    raw = f"{item['resource']}_{item['address'][:100]}"
    return hashlib.md5(raw.encode()).hexdigest()

def check_updates(new_items):
    global storage
    
    new_keys = {generate_key(item) for item in new_items}
    old_keys = set(storage.keys())
    
    updates = []
    
    for item in new_items:
        key = generate_key(item)
        if key not in storage:
            updates.append(('new', item))
        elif storage[key]['period'] != item['period']:
            updates.append(('changed', item, storage[key]['period']))
    
    deleted_keys = old_keys - new_keys
    for key in deleted_keys:
        del storage[key]
        print(f"🗑️ Удалено отключение")
    
    for item in new_items:
        key = generate_key(item)
        storage[key] = item
    
    return updates

def clear_cache(user_id=None):
    global storage
    storage = {}
    print(f"🧹 Кэш полностью очищен")