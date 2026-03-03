"""
Coordinator pentru integrarea MyElectrica România.

Adună periodic datele de la API într-un singur dict (`self.data`)
pe care senzorii îl citesc fără a face request-uri directe.

Structura ierarhică descoperită automat:
  Cont → Coduri client → Contracte (ContractAccount) → NLC-uri (LocConsum)

Doar NLC-urile selectate de utilizator sunt preluate.
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


def _extract_nlc_mappings(
    hierarchy: list[dict],
    selected_nlcs: list[str] | None = None,
) -> tuple[dict[str, str], dict[str, str], list[str], list[str]]:
    """
    Extrage din ierarhie mapările necesare.

    Dacă selected_nlcs este furnizat, filtrează doar NLC-urile din listă.
    Codurile client returnate sunt doar cele care au cel puțin un NLC selectat.

    Returnează:
        nlc_to_client:           {nlc: client_code}
        nlc_to_contract_account: {nlc: contract_account}
        needed_client_codes:     [client_code, ...]
        filtered_nlcs:           [nlc, ...]
    """
    nlc_to_client: dict[str, str] = {}
    nlc_to_contract_account: dict[str, str] = {}
    needed_client_codes: list[str] = []
    filtered_nlcs: list[str] = []

    for client in hierarchy:
        cc = client.get("ClientCode", "")

        for contract in client.get("to_ContContract", []):
            ca = contract.get("ContractAccount", "")
            for loc in contract.get("to_LocConsum", []):
                nlc = loc.get("IdLocConsum", "")
                if not nlc:
                    continue

                # Filtrare: dacă avem selecție, includem doar NLC-urile selectate
                if selected_nlcs and nlc not in selected_nlcs:
                    continue

                if nlc not in filtered_nlcs:
                    filtered_nlcs.append(nlc)
                nlc_to_client[nlc] = cc
                nlc_to_contract_account[nlc] = ca

                if cc and cc not in needed_client_codes:
                    needed_client_codes.append(cc)

    return nlc_to_client, nlc_to_contract_account, needed_client_codes, filtered_nlcs


class MyElectricaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """
    Coordinator central.

    `self.data` conține:
    {
        "hierarchy":               list[dict],       # raw details array
        "client_data":             {cc: dict},        # 3.2 per client_code
        "invoices":                {cc: list[dict]},  # 4.1 per client_code
        "payments":                {cc: list[dict]},  # 5.1 per client_code
        "contract_details":        {nlc: dict},       # 3.3 per NLC
        "meter_list":              {nlc: dict},       # 6.1 per NLC
        "readings":                {nlc: list[dict]}, # 7.1 per NLC
        "convention":              {nlc: list[dict]}, # 8.1 per NLC
        "nlc_to_client":           {nlc: cc},
        "nlc_to_contract_account": {nlc: ca},
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
        )

        # NLC-urile selectate de utilizator (None = toate)
        self._selected_nlcs: list[str] | None = config_entry.data.get(
            "selected_nlcs"
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch periodic — colectează doar endpoint-urile pentru NLC-urile selectate."""
        _LOGGER.debug("[MyElectrica] Începe actualizarea datelor")

        try:
            # ── 3.1 Ierarhie (descoperire structură) ──
            hierarchy_raw = await self.api.async_get_hierarchy()
            if not hierarchy_raw:
                raise UpdateFailed("Nu s-a putut obține ierarhia contului")

            hierarchy = hierarchy_raw.get("details", [])
            if not hierarchy:
                raise UpdateFailed("Ierarhia contului este goală")

            (
                nlc_to_client,
                nlc_to_contract_account,
                needed_client_codes,
                filtered_nlcs,
            ) = _extract_nlc_mappings(hierarchy, self._selected_nlcs)

            _LOGGER.debug(
                "[MyElectrica] Descoperite %s coduri client, %s NLC-uri "
                "(selectate: %s)",
                len(needed_client_codes),
                len(filtered_nlcs),
                len(self._selected_nlcs) if self._selected_nlcs else "toate",
            )

            # ── Date per cod client (doar cele necesare) ──
            client_data: dict[str, Any] = {}
            invoices: dict[str, Any] = {}
            payments: dict[str, Any] = {}

            for cc in needed_client_codes:
                client_data[cc] = await self.api.async_get_client_data(cc)
                invoices[cc] = await self.api.async_get_invoices(cc)
                payments[cc] = await self.api.async_get_payments(cc)

            # ── Date per NLC (doar cele selectate) ──
            contract_details: dict[str, Any] = {}
            meter_list: dict[str, Any] = {}
            readings: dict[str, Any] = {}
            convention: dict[str, Any] = {}

            for nlc in filtered_nlcs:
                cc = nlc_to_client.get(nlc, "")
                contract_details[nlc] = await self.api.async_get_contract_nlc(nlc)
                meter_list[nlc] = await self.api.async_get_meter_list(nlc)
                readings[nlc] = await self.api.async_get_readings(cc, nlc)
                convention[nlc] = await self.api.async_get_convention(nlc)

        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("[MyElectrica] Eroare la actualizare: %s", err)
            raise UpdateFailed(f"Eroare la actualizarea datelor: {err}") from err

        data: dict[str, Any] = {
            "hierarchy": hierarchy,
            "client_data": client_data,
            "invoices": invoices,
            "payments": payments,
            "contract_details": contract_details,
            "meter_list": meter_list,
            "readings": readings,
            "convention": convention,
            "nlc_to_client": nlc_to_client,
            "nlc_to_contract_account": nlc_to_contract_account,
        }

        _LOGGER.debug("[MyElectrica] Actualizare completă")
        return data
