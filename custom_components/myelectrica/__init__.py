"""
Inițializarea integrării MyElectrica România.

Folosește pattern-ul modern `entry.runtime_data` pentru stocarea
coordinator-ului (disponibil din HA 2024.x).
"""

from __future__ import annotations

import asyncio
import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components import persistent_notification
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN, LICENSE_DATA_KEY, LICENSE_PURCHASE_URL
from .coordinator import MyElectricaCoordinator
from .license import LicenseManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

type MyElectricaConfigEntry = ConfigEntry[MyElectricaCoordinator]

# Stările în care o intrare încă folosește managerul de licențe
_STARI_ACTIVE = (
    ConfigEntryState.LOADED,
    ConfigEntryState.SETUP_IN_PROGRESS,
    ConfigEntryState.SETUP_RETRY,
    ConfigEntryState.UNLOAD_IN_PROGRESS,
)


def _update_license_notifications(hass: HomeAssistant, mgr: LicenseManager) -> None:
    """Creează sau șterge notificările de expirare licență/trial."""
    if mgr.is_valid:
        ir.async_delete_issue(hass, DOMAIN, "trial_expired")
        ir.async_delete_issue(hass, DOMAIN, "license_expired")
        persistent_notification.async_dismiss(hass, "myelectrica_license_expired")
        return

    if mgr.has_license:
        issue_id = "license_expired"
        notif_title = "MyElectrica România — Licența a expirat"
        notif_message = (
            "Licența pentru integrarea **MyElectrica România** a expirat.\n\n"
            "Senzorii sunt dezactivați până la reînnoirea licenței.\n\n"
            f"[Reînnoiește licența]({LICENSE_PURCHASE_URL})"
        )
    else:
        issue_id = "trial_expired"
        notif_title = "MyElectrica România — Licența de probă a expirat"
        notif_message = (
            "Perioada de evaluare gratuită pentru integrarea **MyElectrica România** s-a încheiat.\n\n"
            "Senzorii sunt dezactivați până la obținerea unei licențe.\n\n"
            f"[Obține o licență acum]({LICENSE_PURCHASE_URL})"
        )

    other_id = "license_expired" if issue_id == "trial_expired" else "trial_expired"
    ir.async_delete_issue(hass, DOMAIN, other_id)

    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=True,
        learn_more_url=LICENSE_PURCHASE_URL,
        severity=ir.IssueSeverity.WARNING,
        translation_key=issue_id,
        translation_placeholders={"learn_more_url": LICENSE_PURCHASE_URL},
    )

    persistent_notification.async_create(
        hass,
        notif_message,
        title=notif_title,
        notification_id="myelectrica_license_expired",
    )

    _LOGGER.debug("[MyElectrica] Notificare expirare creată: %s", issue_id)


def _cleanup_domain(hass: HomeAssistant) -> None:
    """Oprește verificarea licenței și eliberează datele domeniului."""
    domain_data = hass.data.pop(DOMAIN, None) or {}
    cancel_check = domain_data.pop("_cancel_license_check", None)
    if cancel_check:
        cancel_check()


def _schedule_license_check(hass: HomeAssistant, mgr: LicenseManager) -> None:
    """Programează următoarea verificare a licenței (un singur timer, reprogramat mereu).

    Momentul vine de la server: imediat după `valid_until`, sau cu backoff
    (60s → 1h) cât timp serverul nu răspunde. La fiecare verificare: /check
    (+ /validate pentru licențe); dacă validitatea s-a schimbat → notificări
    actualizate + reload.
    """
    if hass.is_stopping:
        return  # la oprire sesiunea HTTP se închide — nu mai verificăm
    domain_data = hass.data.get(DOMAIN)
    if domain_data is None or domain_data.get(LICENSE_DATA_KEY) is not mgr:
        return
    cancel_prev = domain_data.pop("_cancel_license_check", None)
    if cancel_prev:
        cancel_prev()

    delay = mgr.check_interval_seconds + (2 if not mgr.needs_heartbeat else 0)

    async def _async_check() -> None:
        try:
            was_valid = mgr.is_valid
            if mgr.needs_heartbeat:
                await mgr.async_heartbeat()
            now_valid = mgr.is_valid
            if hass.data.get(DOMAIN, {}).get(LICENSE_DATA_KEY) is not mgr:
                return  # integrarea a fost descărcată în timpul verificării
            if was_valid != now_valid:
                if now_valid:
                    _LOGGER.info("[MyElectrica] Licența a redevenit validă — reîncarc")
                else:
                    _LOGGER.warning("[MyElectrica] Licența a devenit invalidă — reîncarc")
                _update_license_notifications(hass, mgr)
                await mgr._async_reload_entries()
        except Exception:  # noqa: BLE001 — timer-ul nu trebuie să se oprească
            _LOGGER.exception("[MyElectrica] Eroare la verificarea periodică a licenței")
        finally:
            _schedule_license_check(hass, mgr)

    @callback
    def _on_timer(_now) -> None:
        domain_now = hass.data.get(DOMAIN, {})
        domain_now.pop("_cancel_license_check", None)
        if hass.is_stopping or domain_now.get(LICENSE_DATA_KEY) is not mgr:
            return
        if not any(
            e.state in _STARI_ACTIVE for e in hass.config_entries.async_entries(DOMAIN)
        ):
            # Ex: intrare dezactivată cât era în „setup retry" (HA nu apelează unload)
            _cleanup_domain(hass)
            return
        # Task de fundal: pornirea/oprirea Home Assistant nu așteaptă
        # niciodată serverul de licențe (issue #329).
        hass.async_create_background_task(
            _async_check(), f"{DOMAIN}_license_check"
        )

    domain_data["_cancel_license_check"] = async_call_later(hass, delay, _on_timer)


async def _async_wait_license_loaded(hass: HomeAssistant) -> None:
    """Așteaptă încărcarea managerului de licențe pornită de altă intrare.

    La pornirea HA intrările aceluiași domeniu se configurează în paralel. Fără
    această așteptare, a doua intrare găsea managerul încă neîncărcat (licență
    „invalidă") → fără date, doar „Licență necesară" și senzorii reali scoși din
    registry, până la un reload manual (issue reteleelectrice#15).
    """
    load = hass.data.get(DOMAIN, {}).get("_license_load")
    if load is not None and not load.done():
        try:
            await asyncio.shield(load)
        except Exception as err:
            raise ConfigEntryNotReady("Managerul de licențe nu s-a putut încărca") from err
    if LICENSE_DATA_KEY not in hass.data.get(DOMAIN, {}):
        raise ConfigEntryNotReady("Managerul de licențe nu s-a putut încărca")


async def async_setup_entry(hass: HomeAssistant, entry: MyElectricaConfigEntry) -> bool:
    """Configurare intrare: creează coordinator, face primul refresh, setează platformele."""
    _LOGGER.debug("[MyElectrica] Setup entry_id=%s", entry.entry_id)

    hass.data.setdefault(DOMAIN, {})

    # ── Inițializare License Manager (o singură instanță per domeniu) ──
    if LICENSE_DATA_KEY not in hass.data[DOMAIN]:
        license_mgr = LicenseManager(hass)
        # Referința se setează ÎNAINTE de async_load(): async_load() poate face
        # await HTTP, iar intrările configurate în paralel nu trebuie să creeze
        # manageri duplicați.
        hass.data[DOMAIN][LICENSE_DATA_KEY] = license_mgr
        # Încărcarea e un task comun: intrările configurate în paralel o așteaptă
        # (vezi _async_wait_license_loaded) în loc să folosească managerul neîncărcat.
        load = hass.async_create_task(license_mgr.async_load(), f"{DOMAIN} license load")
        hass.data[DOMAIN]["_license_load"] = load
        try:
            await load
        except Exception:
            hass.data[DOMAIN].pop(LICENSE_DATA_KEY, None)
            hass.data[DOMAIN].pop("_license_load", None)
            raise
        _LOGGER.debug(
            "[MyElectrica] LicenseManager: status=%s, valid=%s, fingerprint=%s...",
            license_mgr.status,
            license_mgr.is_valid,
            license_mgr.fingerprint[:16],
        )
        _schedule_license_check(hass, license_mgr)

        # ── Notificare re-enable (dacă a fost dezactivată anterior) ──
        if hass.data.pop(f"{DOMAIN}_was_disabled", False):
            await license_mgr.async_notify_event("integration_enabled")

        if not license_mgr.is_valid:
            _LOGGER.warning(
                "[MyElectrica] Integrarea nu are licență validă. "
                "Senzorii vor afișa 'Licență necesară'."
            )
        elif license_mgr.is_trial_valid:
            _LOGGER.info(
                "[MyElectrica] Perioadă de evaluare — %d zile rămase",
                license_mgr.trial_days_remaining,
            )
        else:
            _LOGGER.info(
                "[MyElectrica] Licență activă — tip: %s",
                license_mgr.license_type,
            )
    else:
        await _async_wait_license_loaded(hass)

    license_mgr = hass.data[DOMAIN][LICENSE_DATA_KEY]
    # La FIECARE setup — după activare, reload-ul intrărilor șterge notificările
    # chiar dacă managerul de licențe rămâne același (mai multe conturi).
    _update_license_notifications(hass, license_mgr)

    coordinator = MyElectricaCoordinator(hass, entry)
    # Dacă MyElectrica nu răspunde → ConfigEntryNotReady → HA reîncearcă automat
    await coordinator.async_config_entry_first_refresh()

    # Stocăm coordinator-ul direct pe entry (pattern modern)
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("[MyElectrica] Setup complet pentru entry_id=%s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MyElectricaConfigEntry) -> bool:
    """Descarcă platformele la eliminarea intrării."""
    _LOGGER.info(
        "[MyElectrica] ── async_unload_entry ── entry_id=%s",
        entry.entry_id,
    )

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    _LOGGER.debug("[MyElectrica] Unload platforme: %s", "OK" if unload_ok else "EȘUAT")

    if unload_ok:
        # Doar intrările ACTIVE contează (cele dezactivate / descărcate nu folosesc
        # managerul de licențe — altfel acesta și timer-ul nu s-ar opri niciodată).
        entry_ids_ramase = {
            e.entry_id
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id and e.state in _STARI_ACTIVE
        }

        _LOGGER.debug(
            "[MyElectrica] Entry-uri active rămase după unload: %d (%s)",
            len(entry_ids_ramase),
            entry_ids_ramase or "niciuna",
        )

        if not entry_ids_ramase:
            _LOGGER.info("[MyElectrica] Ultima entry descărcată — curăț domeniul complet")

            # ── Notificare lifecycle (înainte de cleanup!) ──
            mgr = hass.data.get(DOMAIN, {}).get(LICENSE_DATA_KEY)
            if mgr and not hass.is_stopping:
                if entry.disabled_by:
                    await mgr.async_notify_event("integration_disabled")
                    # Flag pentru async_setup_entry: la re-enable, trimitem "enabled"
                    hass.data[f"{DOMAIN}_was_disabled"] = True
                else:
                    # Salvăm fingerprint-ul pentru async_remove_entry
                    hass.data.setdefault(f"{DOMAIN}_notify", {}).update({
                        "fingerprint": mgr.fingerprint,
                        "license_key": mgr._data.get("license_key", ""),
                    })

            _cleanup_domain(hass)
            _LOGGER.info("[MyElectrica] Cleanup complet — domeniul %s descărcat", DOMAIN)
    else:
        _LOGGER.error("[MyElectrica] Unload EȘUAT pentru entry_id=%s", entry.entry_id)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Notifică serverul când integrarea e complet eliminată (ștearsă)."""
    _LOGGER.debug(
        "[MyElectrica] ── async_remove_entry ── entry_id=%s",
        entry.entry_id,
    )

    # Verifică dacă mai sunt entry-uri rămase
    remaining = hass.config_entries.async_entries(DOMAIN)
    if not remaining:
        # O intrare ștearsă cât era în „setup retry" nu trece prin async_unload_entry
        if DOMAIN in hass.data:
            mgr = hass.data[DOMAIN].get(LICENSE_DATA_KEY)
            if mgr is not None and f"{DOMAIN}_notify" not in hass.data:
                hass.data[f"{DOMAIN}_notify"] = {
                    "fingerprint": mgr.fingerprint,
                    "license_key": mgr._data.get("license_key", ""),
                }
            _cleanup_domain(hass)
        notify_data = hass.data.pop(f"{DOMAIN}_notify", None)
        if notify_data and notify_data.get("fingerprint"):
            await _send_lifecycle_event(
                hass,
                notify_data["fingerprint"],
                notify_data.get("license_key", ""),
                "integration_removed",
            )


async def _send_lifecycle_event(
    hass: HomeAssistant, fingerprint: str, license_key: str, action: str
) -> None:
    """Trimite un eveniment lifecycle direct (fără LicenseManager).

    Folosit în async_remove_entry când LicenseManager nu mai există.
    """
    import hashlib
    import hmac as hmac_lib
    import json
    import time

    from .license import INTEGRATION, LICENSE_API_URL, USER_AGENT

    timestamp = int(time.time())
    payload = {
        "fingerprint": fingerprint,
        "timestamp": timestamp,
        "action": action,
        "license_key": license_key,
        "integration": INTEGRATION,
    }
    data = {k: v for k, v in payload.items() if k != "hmac"}
    msg = json.dumps(data, sort_keys=True).encode()
    payload["hmac"] = hmac_lib.new(
        fingerprint.encode(), msg, hashlib.sha256
    ).hexdigest()

    try:
        session = async_get_clientsession(hass)
        async with session.post(
            f"{LICENSE_API_URL}/notify",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10),
            headers={
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                if not result.get("success"):
                    _LOGGER.warning(
                        "[MyElectrica] Server a refuzat '%s': %s",
                        action, result.get("error"),
                    )
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("[MyElectrica] Nu s-a putut raporta '%s': %s", action, err)
