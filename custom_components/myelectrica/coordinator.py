"""
Coordinator pentru integrarea MyElectrica România.
"""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from datetime import timedelta

from .api import MyElectricaAPI
from .const import DEFAULT_UPDATE

_LOGGER = logging.getLogger(__name__)

class MyElectricaCoordinator(DataUpdateCoordinator):
    """
    Coordinator care adună toate datele necesare într-un singur loc.
    `self.data` va fi un dicționar cu chei relevante pentru fiecare tip de informație:
      {
        "contulmeu": ...,
        "indexcurent": ...,
        "conventie": ...,
        "factura_restanta": ...,
        "facturi": ...
      }
    """

    def __init__(self, hass: HomeAssistant, config_entry):
        self.hass = hass
        self.config_entry = config_entry

        self.api = MyElectricaAPI(
            hass,
            username=config_entry.data["username"],
            password=config_entry.data["password"],
            cod_incasare=config_entry.data["cod_incasare"],
            cod_nlc=config_entry.data["cod_nlc"],
        )

        update_interval_seconds = config_entry.data.get("update_interval", DEFAULT_UPDATE)
        update_interval = timedelta(seconds=update_interval_seconds)

        super().__init__(
            hass,
            _LOGGER,
            name="MyElectricaCoordinator",
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """
        Metodă apelată periodic de Coordinator (sau la cerere).
        Întoarce un dict cu toate datele, astfel încât senzorii să le poată folosi.
        """
        try:
            contulmeu_data = await self.api.async_get_contul_meu()
            indexcurent_data = await self.api.async_get_index_curent()
            conventie_data = await self.api.async_get_conventie()
            facturi_data = await self.api.async_get_facturi()

            # Putem separa "factura_restanta" de "facturi" dacă dorim
            # facturile restante pot fi filtrate din facturi_data
            # DAR pentru a păstra EXACT structura existentă din senzori,
            # punem tot obiectul complet la "facturi", și încă unul la "factura_restanta".
            data = {
                "contulmeu": contulmeu_data,
                "indexcurent": indexcurent_data,
                "conventie": conventie_data,
                "factura_restanta": facturi_data,
                "facturi": facturi_data,
            }
            return data
        except Exception as err:
            # Orice excepție apare, o marcăm drept UpdateFailed
            _LOGGER.error("Eroare în _async_update_data: %s", err)
            raise UpdateFailed(f"Eroare la actualizarea datelor: {err}")
