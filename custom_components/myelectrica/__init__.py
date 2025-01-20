"""
Inițializarea integrării MyElectrica România.
"""

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import MyElectricaCoordinator

_LOGGER = logging.getLogger(__name__)

# Dacă ai mai multe platforme, le enumeri în această listă
PLATFORMS = ["sensor"]

# Adăugarea unei scheme implicite pentru configurările globale (dacă este cazul)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict):
    """
    Setup global (rareori folosit) – doar dacă integrarea e definită și în configuration.yaml.
    """
    _LOGGER.debug("Inițializarea globală a integrării %s", DOMAIN)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Configurează integrarea pentru o intrare de config_entries.
    Creează coordinator, face primul refresh și configurează platformele (ex. sensor).
    """
    _LOGGER.debug("Configurare pentru entry_id=%s", entry.entry_id)

    coordinator = MyElectricaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    # Inițializăm stocarea datelor pe hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # Înregistrăm platformele (în loc de async_setup_platforms)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("Setup complet pentru entry_id=%s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Elimină o intrare din config_entries.
    Descărcăm platformele și ștergem datele din hass.data.
    """
    _LOGGER.debug("Descărcare pentru entry_id=%s", entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Reîncarcă o intrare din config_entries după reconfigurare.
    """
    _LOGGER.debug("Reîncărcare pentru entry_id=%s", entry.entry_id)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
