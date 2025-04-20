import pytest
import requests
from data_provider import DataProvider, APIPaths
import re
from datetime import datetime
import uuid
import json

paths = APIPaths()
dp = DataProvider("data/test_data.json")


def check_fields_existence(expected, actual):
    """Проверяет наличие всех ожидаемых полей в фактических данных, а также проверяет на отсутствие лишних.
    Возвращает список ошибок вида ['поле1 отсутствует', 'В поле2 отсутствуют вложенные поля, 'Присутствует лишнее поле поле3']
    """
    errors = []
    stack = [(expected, actual, "")]

    while stack:
        current_expected, current_actual, current_path = stack.pop()

        for key in current_expected.keys():
            full_path = f"{current_path}.{key}" if current_path else key
            if (
                current_expected[key] == "None"
            ):  # Не уверена, что все поля структуры ответа являются обязательными
                continue

            if key not in current_actual:
                errors.append(f"Поле '{full_path}' отсутствует")
            elif isinstance(current_expected[key], dict):
                if isinstance(current_actual[key], dict):
                    stack.append(
                        (current_expected[key], current_actual[key], full_path)
                    )
                else:
                    errors.append(f"В поле '{full_path}' отсутствуют вложенные поля")

    for key in actual.keys():
        if key not in expected:
            errors.append(f"Присутствует лишнее поле '{key}'")
    return errors


def check_types_compatibility(expected, actual):
    """Проверяет соответствие типов данных.
    Возвращает список ошибок вида ['поле1: ожидался тип X', 'поле2.субполе: ожидался тип Y']
    """
    errors = []
    stack = [(expected, actual, "")]

    while stack:
        current_expected, current_actual, current_path = stack.pop()

        for key, expected_type in current_expected.items():
            full_path = f"{current_path}.{key}" if current_path else key

            if key not in current_actual:
                continue  # Пропускаем отсутствующие поля (их уже проверила check_fields_existence)

            actual_value = current_actual[key]

            if isinstance(expected_type, dict) and isinstance(actual_value, dict):
                stack.append((expected_type, actual_value, full_path))
            else:
                if type(actual_value) != type(expected_type):
                    errors.append(
                        f"{full_path}: ожидался тип '{type(expected_type)}', получен '{type(actual_value)}'"
                    )

    return errors


def check_value_matches(expected, actual):
    """Проверяет соответствие значений данных.
    Возвращает список ошибок вида ['поле1 ожидалось значение1, получено значение2']
    """
    errors = []
    for key, expected_value in expected.items():
        if key not in actual:
            continue  # Пропускаем отсутствующие поля (их уже проверила check_fields_existence)

        if actual[key] != expected_value:
            if key == "createdAt":  # Проверка соответствия даты
                actual_date = actual[key].split()[0]
                if actual_date != expected_value:
                    errors.append(
                        f"Поле '{key}': ожидалось '{expected_value}', получено '{actual_date}'"
                    )

            else:
                errors.append(
                    f"Поле '{key}': ожидалось '{expected_value}', получено '{actual[key]}'"
                )
    return errors


def extract_ad_id(response_text):
    """Извлекает ID объявления из текста ответа"""
    try:
        if type(response_text["id"]) == str:
            uuid.UUID(response_text["id"])
            return response_text["id"], datetime.now().strftime("%Y-%m-%d")
        else:
            raise AssertionError(
                f"\n'id': ожидался тип данных '{str}', получено '{type(response_text["id"])}'"
            )
    except:
        match = re.search(
            r"Сохранили объявление - ([a-f0-9-]+)", response_text["status"]
        )
        if match:
            try:
                uuid.UUID(match.group(1))  # Проверка соответствия id формату UUID
                with open("data/test_data.json", "rb") as filename:
                    data = json.load(filename)
                data["valid_ids"].append(
                    {
                        "id": match.group(1),
                        "createdAt": datetime.now().strftime("%Y-%m-%d"),
                    }
                )
                with open("data/test_data.json", "w") as filename:
                    json.dump(data, filename)
                return match.group(1), datetime.now().strftime("%Y-%m-%d")
            except:
                raise AssertionError(f"\nПоле 'id' не соответствует формату UUID")


def assert_valid_response(response, body_type, create_ad, method):

    if response.status_code == create_ad["expected_status"]:
        if response.text:
            body = response.json()
            if type(body) == body_type:
                if method not in ("get_statistics_v1", "get_statistics_v2"):
                    expected_response = dp.fill_response(
                        create_ad["payload"],
                        dp.get_response(method, str(create_ad["expected_status"])),
                    )
                else:
                    expected_response = dp.fill_response(
                        create_ad["payload"]["statistics"],
                        dp.get_response(method, str(create_ad["expected_status"])),
                    )

                errors = []
                error_id = []
                fields_errors = []
                types_errors = []
                values_errors = []
                isFound = False
                if body_type == dict:
                    body = [body]
                for actual_body in body:
                    fields_errors = fields_errors + check_fields_existence(
                        expected_response, actual_body
                    )
                    types_errors = types_errors + check_types_compatibility(
                        expected_response, actual_body
                    )
                    if method == "get_by_seller_id":
                        if actual_body["id"] == expected_response["id"]:
                            values_errors = values_errors + check_value_matches(
                                expected_response, actual_body
                            )
                            isFound = True
                    else:
                        values_errors = values_errors + check_value_matches(
                            expected_response, actual_body
                        )
                if isFound == False and method == "get_by_seller_id":
                    error_id = [
                        f"Объявление с id = {expected_response["id"]} не найдено среди объявлений продавца с id = {expected_response["sellerId"]}"
                    ]
                errors = (
                    errors + fields_errors + types_errors + values_errors + error_id
                )

                if errors:
                    raise AssertionError("\n".join(errors))
            else:
                raise AssertionError(
                    f"\nТело ответа ожидалось {body_type}, получено {type(body)}"
                )
        else:
            raise AssertionError(f"\n Ожидалось тело ответа, но оно отсутствует")
    else:
        raise AssertionError(
            f"\n Ожидался статус-код '{create_ad["expected_status"]}', получен '{response.status_code}'"
        )


@pytest.fixture(params=dp.get("valid_ads"), scope="session")
def create_ad(request):
    payload = request.param
    response = requests.post(paths.create_path(), json=payload[0])
    ad_params = {
        "response": response,
        "payload": payload[0],
        "expected_status": payload[1],
    }
    if response.text:
        body = response.json()
        if response.status_code == ad_params["expected_status"]:
            id, date = extract_ad_id(body)
            ad_params["payload"].update({"id": id, "createdAt": date})

    return ad_params


class TestAPIValid:

    # Проверка сохранения объявления
    def test_create_ad(self, create_ad):
        assert_valid_response(create_ad["response"], dict, create_ad, "create")

    # Проверка получения объявления по его идентификатору
    def test_get_ad_by_id(self, create_ad):
        response = requests.get(paths.get_by_id(create_ad["payload"]["id"]))
        assert_valid_response(response, list, create_ad, "get_by_ad_id")

    # Проверка получения всех объявлений пользователя
    def test_get_ad_by_sellerid(self, create_ad):
        response = requests.get(
            paths.get_by_seller_id(create_ad["payload"]["sellerId"])
        )
        assert_valid_response(response, list, create_ad, "get_by_seller_id")

    # Проверка получения статистик по объявлению V1
    def test_get_ad_statistic_by_id_v1(self, create_ad):
        response = requests.get(paths.get_statistic_v1(create_ad["payload"]["id"]))
        assert_valid_response(response, list, create_ad, "get_statistics_v1")

    # Проверка получения статистик по объявлению V2
    def test_get_ad_statistic_by_id_v2(self, create_ad):
        response = requests.get(paths.get_statistic_v2(create_ad["payload"]["id"]))
        assert_valid_response(response, list, create_ad, "get_statistics_v2")

    # Проверка удаления объявления по его идентификатору
    def test_delete_ad(self, create_ad):
        response = requests.delete(paths.delete_path(create_ad["payload"]["id"]))
        if response.status_code == 200:
            assert (
                not response.text
            ), f"Тело ответа не должно присутствовать. Получено: '{response.text}'"
        assert response.status_code == 200

    # Проверка получения удаленного объявления по его идентификатору
    def test_get_ad_by_delete_id(self, create_ad):
        response = requests.get(paths.get_by_id(create_ad["payload"]["id"]))
        if response.status_code == 404:
            with open("data/test_data.json", "rb") as filename:
                data = json.load(filename)
            invalid_id = data["valid_ids"].pop(-1)
            # data["invalid_ids"].append([{"id": invalid_id["id"]}, 404])
            # # Сохранение идентификаторов удаленных объявлений для использования в негативных проверках
            with open("data/test_data.json", "w") as filename:
                json.dump(data, filename)
        assert response.status_code == 404


def assert_invalid_response(response, body_type, data, code, method):
    if response.status_code == code:
        if response.text:
            body = response.json()
            if type(body) == body_type:
                expected_statistics_response = dp.get_response(method, str(code))
                values_errors = []
                fields_errors = check_fields_existence(
                    expected_statistics_response, body
                )
                types_errors = check_types_compatibility(
                    expected_statistics_response, body
                )
                if code == 404:
                    values_errors = check_value_matches(
                        expected_statistics_response, body
                    )
                errors = fields_errors + types_errors + values_errors
                if errors:
                    raise AssertionError("\n".join(errors))
            else:
                raise AssertionError(
                    f"\nТело ответа ожидалось {body_type}, получено {type(body)}"
                )
        else:
            raise AssertionError(f"\n Ожидалось тело ответа, но оно отсутствует")
    else:
        raise AssertionError(
            f"\n Ожидался статус-код '{code}', получен '{response.status_code}'"
        )


class TestAPIInvalid:

    # Проверка сохранения объявления с невалидными данными
    @pytest.mark.parametrize("invalid_payload", dp.get("invalid_ads"))
    def test_create_ad_invalid(self, invalid_payload):
        """Тест создания объявления с невалидными данными"""
        response = requests.post(paths.create_path(), json=invalid_payload[0])
        assert_invalid_response(
            response, dict, invalid_payload[0], invalid_payload[1], "create"
        )

    # Проверка получения объявления по невалидным идентификаторам
    @pytest.mark.parametrize("invalid_id", dp.get("invalid_ids"))
    def test_get_nonexistent_ad(self, invalid_id):
        response = requests.get(paths.get_by_id(invalid_id[0]["id"]))
        assert_invalid_response(
            response, dict, invalid_id[0], invalid_id[1], "get_by_ad_id"
        )

    # Проверка получения всех объявлений невалидного пользователя
    @pytest.mark.parametrize("invalid_seller_id", dp.get("invalid_seller_ids"))
    def test_get_ads_invalid_seller(self, invalid_seller_id):
        """Тест получения объявлений несуществующего продавца"""
        response = requests.get(paths.get_by_id(invalid_seller_id[0]["sellerId"]))
        assert_invalid_response(
            response,
            dict,
            invalid_seller_id[0],
            invalid_seller_id[1],
            "get_by_seller_id",
        )

    # Проверка получения статистик по объявлениям по невалидным идентификаторам V1
    @pytest.mark.parametrize("invalid_id", dp.get("invalid_ids"))
    def test_get_statistics_invalid_id_v1(self, invalid_id):
        """Тест получения статистики по несуществующему ID (v1)"""
        response = requests.get(paths.get_statistic_v1(invalid_id[0]["id"]))
        assert_invalid_response(
            response, dict, invalid_id[0], invalid_id[1], "get_statistics_v1"
        )

    # Проверка получения статистик по объявлениям по невалидным идентификаторам V2
    @pytest.mark.parametrize("invalid_id", dp.get("invalid_ids"))
    def test_get_statistics_invalid_id_v2(self, invalid_id):
        """Тест получения статистики по несуществующему ID (v2)"""
        response = requests.get(paths.get_statistic_v2(invalid_id[0]["id"]))
        code = invalid_id[1]
        if invalid_id[1] == 400:
            code = 404
        assert_invalid_response(
            response, dict, invalid_id[0], code, "get_statistics_v2"
        )

    # Проверка удаления объявлений по невалидным идентификаторам
    @pytest.mark.parametrize("invalid_id", dp.get("invalid_ids"))
    def test_delete_nonexistent_ad(self, invalid_id):
        """Тест удаления несуществующего объявления"""
        response = requests.delete(paths.delete_path(invalid_id[0]["id"]))
        assert_invalid_response(response, dict, invalid_id[0], invalid_id[1], "delete")
