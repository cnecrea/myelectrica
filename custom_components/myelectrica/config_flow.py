"""
ConfigFlow și OptionsFlow pentru integrarea MyElectrica România.
"""

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .api import MyElectricaAPI
from .const import DOMAIN, DEFAULT_UPDATE

_LOGGER = logging.getLogger(__name__)

class MyElectricaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestionarea ConfigFlow pentru integrarea MyElectrica."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Pasul inițial pentru configurare."""
        errors = {}

        if user_input is not None:
            username = user_input["username"]
            password = user_input["password"]
            cod_incasare = user_input["cod_incasare"]
            cod_client = user_input["cod_client"]
            cod_nlc = user_input["cod_nlc"]

            # Completează automat cod_incasare la 12 caractere
            if len(cod_incasare) < 12:
                cod_incasare = cod_incasare.zfill(12)
                _LOGGER.debug("Codul de încasare completat automat: %s", cod_incasare)

            # Validăm autentificarea prin API (simplu)
            api = MyElectricaAPI(
                self.hass,
                username=username,
                password=password,
                cod_incasare=cod_incasare,
                cod_nlc=cod_nlc
            )
            if await api.async_login():
                # OK -> Creăm intrarea
                return self.async_create_entry(
                    title=f"MyElectrica ({cod_incasare})",
                    data={
                        "username": username,
                        "password": password,
                        "cod_incasare": cod_incasare,
                        "cod_client": cod_client,
                        "cod_nlc": cod_nlc,
                        "update_interval": user_input.get("update_interval", DEFAULT_UPDATE),
                    },
                )
            else:
                errors["base"] = "auth_failed"
                _LOGGER.error("Autentificare eșuată pentru utilizatorul %s", username)

        # Schema formularului
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
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Returnează fluxul de opțiuni."""
        return MyElectricaOptionsFlow(config_entry)


class MyElectricaOptionsFlow(config_entries.OptionsFlow):
    """Gestionarea OptionsFlow pentru integrarea MyElectrica România."""

    def __init__(self, config_entry):
        """Inițializează OptionsFlow cu intrarea existentă."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Pasul inițial pentru modificarea opțiunilor."""
        errors = {}

        if user_input is not None:
            cod_incasare = user_input["cod_incasare"]
            if len(cod_incasare) < 12:
                cod_incasare = cod_incasare.zfill(12)

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={
                    "update_interval": user_input["update_interval"],
                },
                data={
                    "username": user_input["username"],
                    "password": user_input["password"],
                    "cod_incasare": cod_incasare,
                    "cod_client": user_input["cod_client"],
                    "cod_nlc": user_input["cod_nlc"],
                },
            )
            return self.async_create_entry(title="", data={})

        # Construim schema de opțiuni
        options_schema = vol.Schema(
            {
                vol.Optional("username", default=self.config_entry.data.get("username", "")): str,
                vol.Optional("password", default=self.config_entry.data.get("password", "")): str,
                vol.Optional("cod_incasare", default=self.config_entry.data.get("cod_incasare", "")): str,
                vol.Optional("cod_client", default=self.config_entry.data.get("cod_client", "")): str,
                vol.Optional("cod_nlc", default=self.config_entry.data.get("cod_nlc", "")): str,
                vol.Optional("update_interval", default=self.config_entry.data.get("update_interval", DEFAULT_UPDATE)): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema, errors=errors)
