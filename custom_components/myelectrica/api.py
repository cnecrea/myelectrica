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
    URL_CONTULMEU,
    URL_CONVENTIE,
    URL_FACTURI,
    URL_INDEXCONTOR,
    URL_LOGIN,
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
        cod_incasare: str,
        cod_nlc: str,
    ) -> None:
        self._hass = hass
        self._username = username
        self._password = password
        self._cod_incasare = cod_incasare
        self._cod_nlc = cod_nlc
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

    async def async_request(self, url: str) -> dict | None:
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

    async def _do_get(self, url: str) -> dict | None:
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
                    _LOGGER.debug("[MyElectrica] GET OK: %s", url)
                    return data

                if resp.status == 401:
                    _LOGGER.warning("[MyElectrica] Token expirat (401) pentru %s", url)
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

    async def async_get_contul_meu(self) -> dict | None:
        """Date contract (contul meu)."""
        return await self.async_request(
            URL_CONTULMEU.format(cod_nlc=self._cod_nlc)
        )

    async def async_get_index_curent(self) -> dict | None:
        """Index curent contor."""
        return await self.async_request(
            URL_INDEXCONTOR.format(cod_nlc=self._cod_nlc)
        )

    async def async_get_conventie(self) -> dict | None:
        """Convenție de consum."""
        return await self.async_request(
            URL_CONVENTIE.format(cod_nlc=self._cod_nlc)
        )

    async def async_get_facturi(self) -> dict | None:
        """
        Facturi (achitate + neachitate).

        start_date = acum − 2 ani (calculat dinamic, nu hardcodat).
        end_date   = azi.
        """
        now = datetime.now()
        start_date = (now - timedelta(days=730)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        return await self.async_request(
            URL_FACTURI.format(
                cod_incasare=self._cod_incasare,
                start_date=start_date,
                end_date=end_date,
            )
        )
