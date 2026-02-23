"""
ConfigFlow și OptionsFlow pentru integrarea MyElectrica România.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback

from .api import MyElectricaAPI
from .const import DEFAULT_UPDATE, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MyElectricaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ConfigFlow — pasul inițial de configurare."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pasul de configurare interactivă (utilizatorul completează formularul)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input["username"]
            password = user_input["password"]
            cod_incasare = user_input["cod_incasare"]
            cod_client = user_input["cod_client"]
            cod_nlc = user_input["cod_nlc"]
            update_interval = user_input.get("update_interval", DEFAULT_UPDATE)

            # Completare automată cod încasare la 12 caractere
            if len(cod_incasare) < 12:
                cod_incasare = cod_incasare.zfill(12)
                _LOGGER.debug(
                    "[MyElectrica] Cod încasare completat automat: %s", cod_incasare
                )

            # Evităm duplicate pentru același NLC
            await self.async_set_unique_id(cod_nlc)
            self._abort_if_unique_id_configured()

            # Validare autentificare
            api = MyElectricaAPI(
                self.hass,
                username=username,
                password=password,
                cod_incasare=cod_incasare,
                cod_nlc=cod_nlc,
            )

            if await api.async_login():
                return self.async_create_entry(
                    title=f"MyElectrica ({cod_incasare})",
                    data={
                        "username": username,
                        "password": password,
                        "cod_incasare": cod_incasare,
                        "cod_client": cod_client,
                        "cod_nlc": cod_nlc,
                        "update_interval": update_interval,
                    },
                )

            errors["base"] = "auth_failed"
            _LOGGER.error(
                "[MyElectrica] Autentificare eșuată pentru %s", username
            )

        data_schema = vol.Schema(
            {
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Required("cod_incasare"): str,
                vol.Required("cod_client"): str,
                vol.Required("cod_nlc"): str,
                vol.Optional("update_interval", default=DEFAULT_UPDATE): int,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MyElectricaOptionsFlow:
        """Returnează fluxul de opțiuni."""
        return MyElectricaOptionsFlow()


class MyElectricaOptionsFlow(config_entries.OptionsFlow):
    """OptionsFlow — permite modificarea setărilor după configurare."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pasul de modificare opțiuni."""
        errors: dict[str, str] = {}

        if user_input is not None:
            cod_incasare = user_input["cod_incasare"]
            if len(cod_incasare) < 12:
                cod_incasare = cod_incasare.zfill(12)

            # Actualizăm `data` (credențiale) și `options` (interval)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    "username": user_input["username"],
                    "password": user_input["password"],
                    "cod_incasare": cod_incasare,
                    "cod_client": user_input["cod_client"],
                    "cod_nlc": user_input["cod_nlc"],
                    "update_interval": user_input["update_interval"],
                },
            )

            # Forțăm reload ca noul interval / credențiale să fie active
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(data={})

        # Pre-completăm cu valorile curente
        current = self.config_entry.data
        options_schema = vol.Schema(
            {
                vol.Required("username", default=current.get("username", "")): str,
                vol.Required("password", default=current.get("password", "")): str,
                vol.Required(
                    "cod_incasare", default=current.get("cod_incasare", "")
                ): str,
                vol.Required(
                    "cod_client", default=current.get("cod_client", "")
                ): str,
                vol.Required("cod_nlc", default=current.get("cod_nlc", "")): str,
                vol.Required(
                    "update_interval",
                    default=current.get("update_interval", DEFAULT_UPDATE),
                ): int,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
