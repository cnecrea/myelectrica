"""
Coordinator pentru integrarea MyElectrica România.

Adună periodic datele de la API într-un singur dict (`self.data`)
pe care senzorii îl citesc fără a face request-uri directe.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import MyElectricaAPI
from .const import DEFAULT_UPDATE, DOMAIN

_LOGGER = logging.getLogger(__name__)

type MyElectricaConfigEntry = ConfigEntry[MyElectricaCoordinator]


class MyElectricaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """
    Coordinator central.

    `self.data` conține:
    {
        "contulmeu":        dict | None,
        "indexcurent":      dict | None,
        "conventie":        dict | None,
        "factura_restanta": dict | None,   # identic cu "facturi" (filtrat în senzor)
        "facturi":          dict | None,
    }
    """

    config_entry: MyElectricaConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        update_seconds = config_entry.data.get("update_interval", DEFAULT_UPDATE)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_seconds),
            config_entry=config_entry,
        )

        self.api = MyElectricaAPI(
            hass,
            username=config_entry.data["username"],
            password=config_entry.data["password"],
            cod_incasare=config_entry.data["cod_incasare"],
            cod_nlc=config_entry.data["cod_nlc"],
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch periodic — colectează toate endpoint-urile și returnează un dict."""
        _LOGGER.debug("[MyElectrica] Începe actualizarea datelor")

        try:
            contulmeu = await self.api.async_get_contul_meu()
            indexcurent = await self.api.async_get_index_curent()
            conventie = await self.api.async_get_conventie()
            facturi = await self.api.async_get_facturi()
        except Exception as err:
            _LOGGER.error("[MyElectrica] Eroare la actualizare: %s", err)
            raise UpdateFailed(f"Eroare la actualizarea datelor: {err}") from err

        data: dict[str, Any] = {
            "contulmeu": contulmeu,
            "indexcurent": indexcurent,
            "conventie": conventie,
            "factura_restanta": facturi,
            "facturi": facturi,
        }

        _LOGGER.debug("[MyElectrica] Actualizare completă")
        return data
