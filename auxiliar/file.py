import os
import json
from dotenv import load_dotenv


def save_json(file_path, data):
    file_path = f'{file_path}.json'
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    

def load_json(file_path):
    if exists_file(file_path):
        file_path = f'{file_path}.json'
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    else:
        return None


def year_exists_in_file(year, data):
    if str(year) in data:
        return True
    return False


def exists_file(file_path):
    return os.path.exists(f'{file_path}.json')


def load_partial_data(file_path, year):
    data = load_json(file_path)
    return data[str(year)]


def api_key_in_env():
    load_dotenv()
    api_key = os.getenv("S2_API_KEY", None)
    return api_key