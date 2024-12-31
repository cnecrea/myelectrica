"""ConfigFlow și OptionsFlow pentru integrarea MyElectrica România."""

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .__init__ import _fetch_login
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

            # Completați automat cod_incasare cu 00 dacă este mai scurt de 12 caractere
            if len(cod_incasare) < 12:
                cod_incasare = cod_incasare.zfill(12)
                _LOGGER.debug("Codul de încasare completat automat: %s", cod_incasare)

            _LOGGER.debug("Date introduse: username=%s, cod_incasare=%s, cod_client=%s, cod_nlc=%s",
                          username, cod_incasare, cod_client, cod_nlc)

            # Validăm autentificarea
            auth_response = await _fetch_login(self.hass, username, password)

            if auth_response:
                _LOGGER.debug("Autentificare reușită!")
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

        # Schema formularului de configurare
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

            # Completați automat cod_incasare cu 00 dacă este mai scurt de 12 caractere
            if len(cod_incasare) < 12:
                cod_incasare = cod_incasare.zfill(12)
                _LOGGER.debug("Codul de încasare completat automat: %s", cod_incasare)

            # Salvăm noile date în config_entry
            _LOGGER.debug("Modificare date: %s", user_input)
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

        # Schema pentru modificarea opțiunilor
        options_schema = vol.Schema(
            {
                vol.Optional("username", default=self.config_entry.data.get("username", "")): str,
                vol.Optional("password", default=self.config_entry.data.get("password", "")): str,
                vol.Optional("cod_incasare", default=self.config_entry.data.get("cod_incasare", "")): str,
                vol.Optional("cod_client", default=self.config_entry.data.get("cod_client", "")): str,
                vol.Optional("cod_nlc", default=self.config_entry.data.get("cod_nlc", "")): str,
                vol.Optional("update_interval", default=self.config_entry.options.get("update_interval", DEFAULT_UPDATE)): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema, errors=errors)