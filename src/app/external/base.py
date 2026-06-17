from __future__ import annotations

from typing import Any, Dict, List, Protocol, Union


class ExternalImporter(Protocol):
    """
    Интерфейс (контракт) для всех адаптеров внешних источников данных.
    """

    async def fetch_raw(self, **request_params: Any) -> Union[Dict, List]:
        """
        Отправляет запрос во внешнюю систему.

        Args:
            **request_params: Динамические параметры запроса (query, path params и т.д.).

        Returns:
            Сырой ответ API (JSON object или array).
        """
        ...

    def normalize(self, raw_data: Union[Dict, List], **context: Any) -> List[Dict[str, Any]]:
        """
        Приводит сырые данные к внутреннему формату приложения.

        Args:
            raw_data: Результат работы fetch_raw.
            **context: Дополнительные данные, необходимые для парсинга (например, iso_code).

        Returns:
            Список словарей, совместимых с TaskDict.
        """
        ...
