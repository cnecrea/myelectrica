"""
ConfigFlow și OptionsFlow pentru integrarea MyElectrica România.

Utilizatorul introduce email + parolă, apoi selectează NLC-urile dorite.
Ierarhia contului se descoperă automat prin account-data-hierarchy.

OptionsFlow:
  - Meniu principal cu: Setări cont / Licență
  - Setări: modificare credențiale + interval + selecție NLC-uri
  - Licență: activare / vizualizare licență (1:1 cu eonromania)
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import MyElectricaAPI
from .const import (
    CONF_LICENSE_KEY,
    DEFAULT_UPDATE,
    DOMAIN,
    LICENSE_DATA_KEY,
    LICENSE_PURCHASE_URL,
    MAX_UPDATE,
    MIN_UPDATE,
)
from .helper import normalize_title

_LOGGER = logging.getLogger(__name__)

# Interval de actualizare valid (înainte: orice număr, inclusiv 0 sau negativ)
_INTERVAL = vol.All(vol.Coerce(int), vol.Range(min=MIN_UPDATE, max=MAX_UPDATE))


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
                ): _INTERVAL,
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


# ── Textele licenței: aceleași în toate integrările hubinteligent (standardizate pe 12.11.2026) ──

_TIP_LICENTA = {
    # Tipurile emise de WebAPI (LICENSE_DURATION)
    "perpetual": ("permanentă", "permanent"),
    "annual": ("anuală", "annual"),
    "semi_annual": ("semestrială", "semi-annual"),
    "monthly": ("lunară", "monthly"),
}


def _tip_licenta(tip: str | None, is_ro: bool) -> str:
    """Eticheta tipului de licență primit de la server."""
    if not tip:
        return "necunoscut" if is_ro else "unknown"
    ro, en = _TIP_LICENTA.get(tip, (tip, tip))
    return ro if is_ro else en


def _zile_ramase(zile: int, is_ro: bool) -> str:
    """„o zi rămasă”, „5 zile rămase”, „20 de zile rămase” — „1 day left”, „5 days left”."""
    if zile <= 0:
        return "ultima zi" if is_ro else "last day"
    if not is_ro:
        return "1 day left" if zile == 1 else f"{zile} days left"
    if zile == 1:
        return "o zi rămasă"
    return f"{zile} {'de ' if zile % 100 >= 20 or zile % 100 == 0 else ''}zile rămase"


def _status_licenta(mgr, is_ro: bool) -> str:
    """Starea licenței, afișată la pasul „Licență”, deasupra câmpului „Cheie de licență”."""
    from homeassistant.util import dt as dt_util

    def data(moment: float) -> str:
        return dt_util.as_local(dt_util.utc_from_timestamp(moment)).strftime("%d.%m.%Y")

    obtine = f"🛒 {'Obține o licență' if is_ro else 'Get a license'}: {LICENSE_PURCHASE_URL}"
    if mgr.status == "licensed":
        linii = [f"✅ {'Licență activă' if is_ro else 'Active license'} ({_tip_licenta(mgr.license_type, is_ro)})"]
        if mgr.license_key_masked:
            linii[0] += f" — {mgr.license_key_masked}"
        if mgr.activated_at:
            linii.append(f"{'Activată la' if is_ro else 'Activated on'}: {data(mgr.activated_at)}")
        if mgr.license_expires_at:
            linii.append(f"📅 {'Expiră la' if is_ro else 'Expires on'}: {data(mgr.license_expires_at)}")
        else:
            linii.append("Valabilitate: nelimitată" if is_ro else "Validity: unlimited")
        return "\n".join(linii)
    if mgr.status == "trial":
        perioada = "Perioadă de test" if is_ro else "Free trial"
        return "\n".join([f"⏳ {perioada}: {_zile_ramase(mgr.trial_days_remaining, is_ro)}", "", obtine])
    if mgr.status == "expired" and mgr.has_license:
        linii = ["❌ Licență expirată" if is_ro else "❌ License expired"]
        if mgr.license_expires_at:
            linii.append(f"{'Expirată la' if is_ro else 'Expired on'}: {data(mgr.license_expires_at)}")
        return "\n".join([*linii, "", obtine])
    if mgr.status == "expired":
        return "\n".join(["❌ Perioada de test s-a încheiat" if is_ro else "❌ The free trial has ended", "", obtine])
    stare = "❌ Fără licență: senzorii nu se actualizează." if is_ro else "❌ No license: sensors do not update."
    return "\n".join([stare, "", obtine])


class MyElectricaOptionsFlow(config_entries.OptionsFlow):
    """OptionsFlow — meniu cu setări cont și licențiere."""

    def __init__(self) -> None:
        self._username: str = ""
        self._password: str = ""
        self._update_interval: int = DEFAULT_UPDATE
        self._hierarchy: list[dict] = []

    # ─────────────────────────────────────────
    # Meniu principal
    # ─────────────────────────────────────────
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Afișează meniul principal cu opțiunile disponibile."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "settings",
                "licenta",
            ],
        )

    # ─────────────────────────────────────────
    # Setări cont (credențiale + interval + NLC-uri)
    # ─────────────────────────────────────────
    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Modificare credențiale și interval de actualizare."""
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

            conflict = any(
                e.entry_id != self.config_entry.entry_id
                and e.unique_id == username.lower()
                for e in self.hass.config_entries.async_entries(DOMAIN)
            )
            if conflict:
                # Contul e deja configurat într-o altă intrare
                errors["base"] = "already_configured"
            elif await api.async_login():
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
                ): _INTERVAL,
            }
        )

        return self.async_show_form(
            step_id="settings", data_schema=schema, errors=errors
        )

    async def async_step_select_nlc(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Modificare selecție NLC-uri."""
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
                    title=f"MyElectrica ({self._username})",
                    unique_id=self._username.lower(),
                )

                await self.hass.config_entries.async_reload(
                    self.config_entry.entry_id
                )

                return self.async_create_entry(data=dict(self.config_entry.options))

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

    # ─────────────────────────────────────────
    # Licențiere
    # ─────────────────────────────────────────
    async def async_step_licenta(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Formular pentru activarea / vizualizarea licenței MyElectrica."""
        from .license import LicenseManager

        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}

        is_ro = self.hass.config.language == "ro"

        # Obține LicenseManager
        mgr: LicenseManager | None = self.hass.data.get(DOMAIN, {}).get(
            LICENSE_DATA_KEY
        )
        if mgr is None:
            mgr = LicenseManager(self.hass)
            await mgr.async_load()

        description_placeholders["license_status"] = _status_licenta(mgr, is_ro)

        if user_input is not None:
            cheie = user_input.get(CONF_LICENSE_KEY, "").strip()

            if not cheie:
                errors["base"] = "license_key_empty"
            elif len(cheie) < 10:
                errors["base"] = "license_key_invalid"
            else:
                # Activare prin API
                result = await mgr.async_activate(cheie)

                if result.get("success"):
                    # Notificare de succes
                    from homeassistant.components import (
                        persistent_notification,
                    )

                    persistent_notification.async_create(
                        self.hass,
                        f"Licența MyElectrica este activă ({_tip_licenta(mgr.license_type, True)}).",
                        title="Licență activată",
                        notification_id="myelectrica_license_activated",
                    )
                    return self.async_create_entry(
                        data=self.config_entry.options
                    )

                # Mapare erori API (codurile WebAPI /activate + erorile locale)
                api_error = result.get("error", "unknown_error")
                error_map = {
                    "invalid_key": "license_key_invalid",
                    "already_used": "license_already_used",
                    "expired_key": "license_key_expired",
                    "fingerprint_mismatch": "license_fingerprint_mismatch",
                    "network_error": "license_network_error",
                    "http_502": "license_network_error",
                    "http_503": "license_network_error",  # server temporar ocupat
                    "http_504": "license_network_error",
                }
                errors["base"] = error_map.get(api_error, "license_server_error")

        schema = vol.Schema(
            {
                vol.Optional(CONF_LICENSE_KEY): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                        suffix="MELC-XXXX-XXXX-XXXX-XXXX",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="licenta",
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )
