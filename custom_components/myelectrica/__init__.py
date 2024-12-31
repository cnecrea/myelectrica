"""Inițializarea integrării MyElectrica România."""
import logging
from datetime import timedelta, datetime
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, DEFAULT_UPDATE, URL_LOGIN, URL_CONTULMEU, URL_INDEXCONTOR, URL_CONVENTIE, URL_FACTURI

_LOGGER = logging.getLogger(__name__)

# Configurare globală
async def async_setup(hass: HomeAssistant, config: dict):
    """Configurează integrarea globală."""
    _LOGGER.debug("Inițializarea globală a integrării %s", DOMAIN)
    return True

async def _fetch_login(hass, username: str, password: str):
    """Realizează autentificarea utilizatorului prin API."""
    url = "https://api.myelectrica.ro/api/login-web"
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'ro',
        'content-type': 'application/json',
        'origin': 'https://myelectrica.ro',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    }
    payload = {
        'email': username,
        'parola': password,
    }

    session = async_get_clientsession(hass)
    try:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("error") is False:
                    _LOGGER.debug("Autentificare reușită: %s", data)
                    return data.get("app_token")
                else:
                    _LOGGER.error("Eroare la autentificare: %s", data)
            else:
                _LOGGER.error("Eroare HTTP la autentificare: Status=%s", response.status)
    except Exception as e:
        _LOGGER.error("Excepție în timpul autentificării: %s", e)
    return None

# Configurare pentru fiecare intrare adăugată
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Configurare specifică pentru o intrare de config_entries."""
    _LOGGER.debug("Configurare pentru entry_id=%s", entry.entry_id)

    update_interval = timedelta(seconds=entry.data.get("update_interval", DEFAULT_UPDATE))
    session = async_get_clientsession(hass)

    # Creăm coordinatorii pentru senzori
    contulmeu_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_contulmeu_coordinator",
        update_method=lambda: _fetch_data(hass, session, entry, URL_CONTULMEU.format(cod_nlc=entry.data["cod_nlc"])),
        update_interval=update_interval,
    )

    indexcurent_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_indexcurent_coordinator",
        update_method=lambda: _fetch_data(hass, session, entry, URL_INDEXCONTOR.format(cod_nlc=entry.data["cod_nlc"])),
        update_interval=update_interval,
    )

    conventie_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_conventie_coordinator",
        update_method=lambda: _fetch_data(hass, session, entry, URL_CONVENTIE.format(cod_nlc=entry.data["cod_nlc"])),
        update_interval=update_interval,
    )

    factura_restanta_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_factura_restanta_coordinator",
        update_method=lambda: _fetch_data(hass, session, entry, URL_FACTURI.format(
            cod_incasare=entry.data["cod_incasare"],
            start_date="2023-01-01",
            end_date=datetime.now().strftime('%Y-%m-%d'),
        )),
        update_interval=update_interval,
    )

    facturi_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_facturi_coordinator",
        update_method=lambda: _fetch_data(
            hass,
            session,
            entry,
            URL_FACTURI.format(
                cod_incasare=entry.data["cod_incasare"],
                start_date="2023-01-01",
                end_date=datetime.now().strftime('%Y-%m-%d'),
            ),
        ),
        update_interval=update_interval,
    )

    # Asigurăm inițializarea `hass.data[DOMAIN]`
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "contulmeu": contulmeu_coordinator,
        "indexcurent": indexcurent_coordinator,
        "conventie": conventie_coordinator,
        "factura_restanta": factura_restanta_coordinator,
        "facturi": facturi_coordinator,
    }

    # Actualizăm datele coordonatorilor
    await contulmeu_coordinator.async_config_entry_first_refresh()
    await indexcurent_coordinator.async_config_entry_first_refresh()
    await conventie_coordinator.async_config_entry_first_refresh()
    await factura_restanta_coordinator.async_config_entry_first_refresh()
    await facturi_coordinator.async_config_entry_first_refresh()

    # Configurăm entitățile de tip senzor
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    _LOGGER.debug("Setup complet pentru entry_id=%s", entry.entry_id)
    return True

# Descărcarea unei intrări
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Elimină o intrare din config_entries."""
    _LOGGER.debug("Descărcare pentru entry_id=%s", entry.entry_id)

    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("Entry descărcat cu succes pentru entry_id=%s", entry.entry_id)
    else:
        _LOGGER.error("Eșec la descărcarea entry-ului pentru entry_id=%s", entry.entry_id)

    return unload_ok

# Reîncarcă o intrare
async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reîncarcă o intrare din config_entries după reconfigurare."""
    _LOGGER.debug("Reîncărcare pentru entry_id=%s", entry.entry_id)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

# Funcție generică pentru a obține date de la API cu autentificare
async def _fetch_data(hass, session, entry, url: str):
    """Obține datele de la un endpoint specific, cu autentificare."""
    _LOGGER.debug("Obținere date de la URL: %s", url)

    token = await _fetch_login(hass, entry.data["username"], entry.data["password"])
    if not token:
        _LOGGER.error("Eroare: Nu s-a putut obține un token.")
        return None

    headers = {
        'accept': 'application/json',
        'authorization': f'Bearer {token}',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    }

    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                _LOGGER.debug("Date primite de la URL=%s: %s", url, data)
                return data
            else:
                _LOGGER.error("Eroare API: Status=%s, URL=%s, Răspuns=%s",
                              response.status, url, await response.text())
    except Exception as e:
        _LOGGER.error("Eroare conexiune API la URL=%s: %s", url, e)
    return None