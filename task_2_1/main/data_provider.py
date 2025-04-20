import json


class DataProvider:
    """Класс DataProvider предназначен для загрузки и предоставления тестовых данных из JSON-файла.

    Он считывает данные из файла и позволяет извлекать их по ключам в формате, подходящем для тестов.
    """

    def __init__(self, filename: str) -> None:
        """Записывает содержимое файла filename в переменную self.data."""
        with open(filename) as filename:
            self.data = json.load(filename)

    def get(self, key):
        """Обращается к тестовым данным data по ключу key и возвращает список значений."""
        data_list = []
        for el in self.data.get(key):
            data_list.append(el)
        return data_list

    def get_response(self, method, status):
        return self.data["responses"][method][status]

    def fill_response(self, values, response):

        for key in values.keys():
            if key in response:
                response[key] = values[key]

        return response


class APIPaths:
    def __init__(self):
        self.BASE_URL = "https://qa-internship.avito.com"

    def create_path(self):
        CREATE_PATH = f"{self.BASE_URL}/api/1/item"
        return CREATE_PATH

    def get_by_id(self, ad_id):
        GET_BY_ID_PATH = f"{self.BASE_URL}/api/1/item/{ad_id}"
        return GET_BY_ID_PATH

    def get_statistic_v1(self, ad_id):
        GET_STATISTIC_V1_PATH = f"{self.BASE_URL}/api/1/statistic/{ad_id}"
        return GET_STATISTIC_V1_PATH

    def get_statistic_v2(self, ad_id):
        GET_STATISTICS_V2_PATH = f"{self.BASE_URL}/api/2/statistic/{ad_id}"
        return GET_STATISTICS_V2_PATH

    def get_by_seller_id(self, sellerId):
        GET_BY_SELLERID_PATH = f"{self.BASE_URL}/api/1/{sellerId}/item"
        return GET_BY_SELLERID_PATH

    def delete_path(self, ad_id):
        DELETE_PATH = f"{self.BASE_URL}/api/2/item/{ad_id}"
        return DELETE_PATH
