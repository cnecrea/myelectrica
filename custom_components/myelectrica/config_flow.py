"""
ConfigFlow și OptionsFlow pentru integrarea MyElectrica România.

Utilizatorul introduce email + parolă, apoi selectează NLC-urile dorite.
Ierarhia contului se descoperă automat prin account-data-hierarchy.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import MyElectricaAPI
from .const import DEFAULT_UPDATE, DOMAIN
from .helper import normalize_title

_LOGGER = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _build_nlc_options(hierarchy: list[dict]) -> list[SelectOptionDict]:
    """Construiește lista de opțiuni pentru selectorul de NLC-uri."""
    options: list[SelectOptionDict] = []

    for client in hierarchy:
        for contract in client.get("to_ContContract", []):
            for loc in contract.get("to_LocConsum", []):
                nlc = loc.get("IdLocConsum", "")
                if not nlc:
                    continue

                # Construim adresa normalizată: Stradă Nr, detalii, Oraș
                parts: list[str] = []

                street = normalize_title(loc.get("Street", ""))
                nr = loc.get("HouseNumber", "").strip()
                if street and nr:
                    parts.append(f"{street} {nr}")
                elif street:
                    parts.append(street)

                building = loc.get("Building", "").strip()
                if building:
                    parts.append(f"bl. {building}")

                entrance = loc.get("Entrance", "").strip()
                if entrance:
                    parts.append(f"sc. {entrance}")

                floor = loc.get("Floor", "").strip()
                if floor:
                    parts.append(f"et. {floor}")

                room = loc.get("RoomNumber", "").strip()
                if room:
                    parts.append(f"ap. {room}")

                city = normalize_title(loc.get("City", ""))
                if city:
                    parts.append(city)

                address = ", ".join(parts) if parts else "Fără adresă"
                service = loc.get("ServiceType", "")

                # Format final dorit:
                # Moților 90A, ap. 17, Alba Iulia —> NLC: 7003050900 (Electricitate)
                label = f"{address} ➜ NLC: {nlc}"

                if service:
                    label += f" ({service})"

                options.append(
                    SelectOptionDict(value=nlc, label=label)
                )

    return options


def _extract_all_nlcs(hierarchy: list[dict]) -> list[str]:
    """Extrage toate NLC-urile unice din ierarhie."""
    nlcs: list[str] = []

    for client in hierarchy:
        for contract in client.get("to_ContContract", []):
            for loc in contract.get("to_LocConsum", []):
                nlc = loc.get("IdLocConsum", "")
                if nlc and nlc not in nlcs:
                    nlcs.append(nlc)

    return nlcs


def _resolve_selected_nlcs(
    select_all: bool,
    selected: list[str],
    hierarchy: list[dict],
) -> list[str]:
    """Returnează lista finală de NLC-uri."""
    if select_all:
        return _extract_all_nlcs(hierarchy)

    return selected


# ------------------------------------------------------------------
# ConfigFlow
# ------------------------------------------------------------------


class MyElectricaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ConfigFlow — autentificare + selecție NLC-uri."""

    VERSION = 3

    def __init__(self) -> None:
        self._username: str = ""
        self._password: str = ""
        self._update_interval: int = DEFAULT_UPDATE
        self._hierarchy: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input["username"]
            self._password = user_input["password"]
            self._update_interval = user_input.get(
                "update_interval", DEFAULT_UPDATE
            )

            await self.async_set_unique_id(self._username.lower())
            self._abort_if_unique_id_configured()

            api = MyElectricaAPI(
                self.hass,
                username=self._username,
                password=self._password,
            )

            if await api.async_login():
                hierarchy_raw = await api.async_get_hierarchy()

                if hierarchy_raw and hierarchy_raw.get("details"):
                    self._hierarchy = hierarchy_raw["details"]
                    return await self.async_step_select_nlc()

                errors["base"] = "no_data"
            else:
                errors["base"] = "auth_failed"

        schema = vol.Schema(
            {
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Optional(
                    "update_interval", default=DEFAULT_UPDATE
                ): int,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_select_nlc(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            select_all = user_input.get("select_all", False)
            selected = user_input.get("selected_nlcs", [])

            if not select_all and not selected:
                errors["base"] = "no_nlc_selected"
            else:
                final_selection = _resolve_selected_nlcs(
                    select_all, selected, self._hierarchy
                )

                return self.async_create_entry(
                    title=f"MyElectrica ({self._username})",
                    data={
                        "username": self._username,
                        "password": self._password,
                        "update_interval": self._update_interval,
                        "select_all": select_all,
                        "selected_nlcs": final_selection,
                    },
                )

        nlc_options = _build_nlc_options(self._hierarchy)

        schema = vol.Schema(
            {
                vol.Optional("select_all", default=False): bool,
                vol.Required("selected_nlcs", default=[]): SelectSelector(
                    SelectSelectorConfig(
                        options=nlc_options,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="select_nlc",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MyElectricaOptionsFlow:
        return MyElectricaOptionsFlow()


# ------------------------------------------------------------------
# OptionsFlow
# ------------------------------------------------------------------


class MyElectricaOptionsFlow(config_entries.OptionsFlow):
    """OptionsFlow — modificare setări + selecție NLC."""

    def __init__(self) -> None:
        self._username: str = ""
        self._password: str = ""
        self._update_interval: int = DEFAULT_UPDATE
        self._hierarchy: list[dict] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input["username"]
            password = user_input["password"]
            update_interval = user_input.get(
                "update_interval", DEFAULT_UPDATE
            )

            api = MyElectricaAPI(
                self.hass, username=username, password=password
            )

            if await api.async_login():
                hierarchy_raw = await api.async_get_hierarchy()

                if hierarchy_raw and hierarchy_raw.get("details"):
                    self._hierarchy = hierarchy_raw["details"]
                    self._username = username
                    self._password = password
                    self._update_interval = update_interval
                    return await self.async_step_select_nlc()

                errors["base"] = "no_data"
            else:
                errors["base"] = "auth_failed"

        current = self.config_entry.data

        schema = vol.Schema(
            {
                vol.Required(
                    "username", default=current.get("username", "")
                ): str,
                vol.Required(
                    "password", default=current.get("password", "")
                ): str,
                vol.Required(
                    "update_interval",
                    default=current.get(
                        "update_interval", DEFAULT_UPDATE
                    ),
                ): int,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )

    async def async_step_select_nlc(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            select_all = user_input.get("select_all", False)
            selected = user_input.get("selected_nlcs", [])

            if not select_all and not selected:
                errors["base"] = "no_nlc_selected"
            else:
                final_selection = _resolve_selected_nlcs(
                    select_all, selected, self._hierarchy
                )

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        "username": self._username,
                        "password": self._password,
                        "update_interval": self._update_interval,
                        "select_all": select_all,
                        "selected_nlcs": final_selection,
                    },
                )

                await self.hass.config_entries.async_reload(
                    self.config_entry.entry_id
                )

                return self.async_create_entry(data={})

        current = self.config_entry.data

        schema = vol.Schema(
            {
                vol.Optional(
                    "select_all",
                    default=current.get("select_all", False),
                ): bool,
                vol.Required(
                    "selected_nlcs",
                    default=current.get("selected_nlcs", []),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=_build_nlc_options(self._hierarchy),
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="select_nlc",
            data_schema=schema,
            errors=errors,
        )
