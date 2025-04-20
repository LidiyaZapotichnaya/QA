import requests
from data_provider import DataProvider, APIPaths

# Удаляет все объявления продавца
paths = APIPaths()
response = requests.get(paths.get_by_seller_id(567890))
body = response.json()
for b in body:
    response = requests.delete(paths.delete_path(b["id"]))
