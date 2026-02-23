"""
Inițializarea integrării MyElectrica România.

Folosește pattern-ul modern `entry.runtime_data` pentru stocarea
coordinator-ului (disponibil din HA 2024.x).
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import MyElectricaCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type MyElectricaConfigEntry = ConfigEntry[MyElectricaCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MyElectricaConfigEntry) -> bool:
    """Configurare intrare: creează coordinator, face primul refresh, setează platformele."""
    _LOGGER.debug("[MyElectrica] Setup entry_id=%s", entry.entry_id)

    coordinator = MyElectricaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    # Stocăm coordinator-ul direct pe entry (pattern modern)
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("[MyElectrica] Setup complet pentru entry_id=%s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MyElectricaConfigEntry) -> bool:
    """Descarcă platformele la eliminarea intrării."""
    _LOGGER.debug("[MyElectrica] Unload entry_id=%s", entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
