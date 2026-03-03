"""
API Manager pentru integrarea MyElectrica România.

Se ocupă de autentificare (login + token) și de toate request-urile
către API-ul MyElectrica.  Include retry automat la 401 (token expirat).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    HEADERS_POST,
    URL_CLIENT_DATA,
    URL_CONTRACT_NLC,
    URL_CONVENTION,
    URL_HIERARCHY,
    URL_INVOICES,
    URL_LOGIN,
    URL_METER_LIST,
    URL_PAYMENTS,
    URL_READINGS,
    URL_SET_INDEX,
)

_LOGGER = logging.getLogger(__name__)

# Timeout global pentru orice request (secunde)
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


class MyElectricaAPI:
    """Manager API pentru integrarea MyElectrica."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
    ) -> None:
        self._hass = hass
        self._username = username
        self._password = password
        self._session = async_get_clientsession(self._hass)
        self._token: str | None = None

    # ── Autentificare ────────────────────────────

    async def async_login(self) -> bool:
        """Autentificare și obținere token.  Returnează True la succes."""
        payload = {
            "email": self._username,
            "parola": self._password,
        }
        try:
            async with self._session.post(
                URL_LOGIN,
                headers=HEADERS_POST,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status != 200:
                    _LOGGER.error(
                        "[MyElectrica] Login HTTP %s — răspuns: %s",
                        resp.status,
                        await resp.text(),
                    )
                    self._token = None
                    return False

                data = await resp.json()
                _LOGGER.debug("[MyElectrica] Login response data: %s", data)

                if data.get("error") is False:
                    self._token = data.get("app_token")
                    _LOGGER.debug("[MyElectrica] Login OK — token obținut")
                    return True

                _LOGGER.error("[MyElectrica] Login respins de API: %s", data)

        except aiohttp.ClientError as err:
            _LOGGER.error("[MyElectrica] Excepție la login: %s", err)
        except TimeoutError:
            _LOGGER.error("[MyElectrica] Timeout la login")

        self._token = None
        return False

    # ── Request generic (GET) cu retry pe 401 ───

    async def async_request(self, url: str) -> dict | list | None:
        """
        GET autorizat.  Dacă primim 401 (token expirat),
        re-autentificăm o dată și reîncercăm.
        """
        # Asigurăm token valid
        if not self._token:
            if not await self.async_login():
                _LOGGER.error("[MyElectrica] Nu s-a putut obține token-ul")
                return None

        data = await self._do_get(url)
        if data is not None:
            return data

        # Retry: re-login și a doua încercare
        _LOGGER.debug("[MyElectrica] Retry: re-autentificare pentru %s", url)
        if await self.async_login():
            return await self._do_get(url)

        return None

    async def _do_get(self, url: str) -> dict | list | None:
        """Execută un singur GET.  Returnează JSON sau None."""
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self._token}",
            "user-agent": HEADERS_POST["User-Agent"],
        }
        try:
            async with self._session.get(
                url, headers=headers, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _LOGGER.debug("[MyElectrica] GET OK: %s — Received data: %s", url, data)
                    return data

                if resp.status == 401:
                    _LOGGER.warning(
                        "[MyElectrica] Token expirat (401) pentru %s", url
                    )
                    self._token = None
                    return None

                _LOGGER.error(
                    "[MyElectrica] GET HTTP %s — URL: %s — răspuns: %s",
                    resp.status,
                    url,
                    await resp.text(),
                )
        except aiohttp.ClientError as err:
            _LOGGER.error("[MyElectrica] Eroare conexiune: %s — %s", url, err)
        except TimeoutError:
            _LOGGER.error("[MyElectrica] Timeout: %s", url)

        return None

    # ── Endpoint-uri specifice ───────────────────

    # 3.1 Ierarhie date cont
    async def async_get_hierarchy(self) -> dict | None:
        """Ierarhie completă: coduri client → contracte → NLC-uri."""
        return await self.async_request(URL_HIERARCHY)

    # 3.2 Date client detaliate
    async def async_get_client_data(self, client_code: str) -> dict | None:
        """Date detaliate ale unui client."""
        return await self.async_request(
            URL_CLIENT_DATA.format(client_code=client_code)
        )

    # 3.3 Detalii contract NLC
    async def async_get_contract_nlc(self, nlc: str) -> dict | None:
        """Detalii contract pentru un NLC."""
        return await self.async_request(
            URL_CONTRACT_NLC.format(nlc=nlc)
        )

    # 4.1 Facturi per cod client
    async def async_get_invoices(
        self,
        client_code: str,
        unpaid: bool = False,
    ) -> dict | None:
        """
        Facturi per cod client.

        start_date = acum − 2 ani (calculat dinamic).
        end_date   = azi.
        unpaid     = True → doar neachitate, False → toate.
        """
        now = datetime.now()
        start_date = (now - timedelta(days=730)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        return await self.async_request(
            URL_INVOICES.format(
                client_code=client_code,
                start_date=start_date,
                end_date=end_date,
                unpaid=str(unpaid).lower(),
            )
        )

    # 5.1 Istoric plăți
    async def async_get_payments(self, client_code: str) -> dict | None:
        """
        Istoric plăți per cod client.

        start_date = acum − 2 ani (calculat dinamic).
        end_date   = azi.
        """
        now = datetime.now()
        start_date = (now - timedelta(days=730)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        return await self.async_request(
            URL_PAYMENTS.format(
                client_code=client_code,
                start_date=start_date,
                end_date=end_date,
            )
        )

    # 6.1 Lista contoare
    async def async_get_meter_list(self, nlc: str) -> dict | None:
        """Lista contoare și cadrane pentru un NLC."""
        return await self.async_request(
            URL_METER_LIST.format(nlc=nlc)
        )

    # 7.1 Istoric citiri
    async def async_get_readings(
        self, client_code: str, nlc: str
    ) -> dict | None:
        """Istoric citiri contor pentru un client și NLC."""
        return await self.async_request(
            URL_READINGS.format(client_code=client_code, nlc=nlc)
        )

    # 8.1 Convenție consum
    async def async_get_convention(self, nlc: str) -> dict | None:
        """Convenție de consum pentru un NLC."""
        return await self.async_request(
            URL_CONVENTION.format(nlc=nlc)
        )

    # ── POST generic cu retry pe 401 ────────────

    async def async_post_request(
        self, url: str, payload: dict
    ) -> dict | None:
        """POST autorizat cu retry pe 401."""
        if not self._token:
            if not await self.async_login():
                _LOGGER.error("[MyElectrica] Nu s-a putut obține token-ul")
                return None

        data = await self._do_post(url, payload)
        if data is not None:
            return data

        _LOGGER.debug("[MyElectrica] Retry POST: re-autentificare pentru %s", url)
        if await self.async_login():
            return await self._do_post(url, payload)

        return None

    async def _do_post(self, url: str, payload: dict) -> dict | None:
        """Execută un singur POST autorizat.  Returnează JSON sau None."""
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self._token}",
            "user-agent": HEADERS_POST["User-Agent"],
        }
        try:
            async with self._session.post(
                url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _LOGGER.debug("[MyElectrica] POST OK: %s — Received data: %s", url, data)
                    return data

                if resp.status == 401:
                    _LOGGER.warning(
                        "[MyElectrica] Token expirat (401) POST %s", url
                    )
                    self._token = None
                    return None

                _LOGGER.error(
                    "[MyElectrica] POST HTTP %s — URL: %s — răspuns: %s",
                    resp.status,
                    url,
                    await resp.text(),
                )
        except aiohttp.ClientError as err:
            _LOGGER.error("[MyElectrica] Eroare conexiune POST: %s — %s", url, err)
        except TimeoutError:
            _LOGGER.error("[MyElectrica] Timeout POST: %s", url)

        return None

    # 6.2 Trimitere index (autocitire)
    async def async_set_index(
        self,
        nlc: str,
        serie_contor: str,
        register_code: str,
        index_value: str,
    ) -> dict | None:
        """
        Trimite autocitirea (index) pentru un NLC.

        Payload conform API 6.2:
        {
            "NLC": "...",
            "to_Contor": [{
                "SerieContor": "...",
                "to_Cadran": [{
                    "RegisterCode": "...",
                    "Index": "..."
                }]
            }]
        }
        """
        payload = {
            "NLC": nlc,
            "to_Contor": [
                {
                    "SerieContor": serie_contor,
                    "to_Cadran": [
                        {
                            "RegisterCode": register_code,
                            "Index": str(index_value),
                        }
                    ],
                }
            ],
        }
        return await self.async_post_request(URL_SET_INDEX, payload)
