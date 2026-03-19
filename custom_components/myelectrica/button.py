"""
Platforma Button pentru MyElectrica România.

Creează un buton per NLC pentru trimiterea autocitiri (set-index).
Citește valoarea indexului din:
  - input_number.energy_meter_reading  (dacă produsul este Electricitate)
  - input_number.gas_meter_reading     (dacă produsul este Gaz)
"""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import MyElectricaCoordinator
from .helper import build_address, get_body_response
from .sensor import NlcContext

_LOGGER = logging.getLogger(__name__)

# Mapare produs → entity_id input_number
_INPUT_NUMBER_MAP = {
    "electricitate": "input_number.energy_meter_reading",
    "energie electrică": "input_number.energy_meter_reading",
    "energie electrica": "input_number.energy_meter_reading",
    "gaz": "input_number.gas_meter_reading",
    "gaze naturale": "input_number.gas_meter_reading",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurează butoanele de trimitere index pe baza ierarhiei."""
    coordinator: MyElectricaCoordinator = config_entry.runtime_data

    if not coordinator.data:
        _LOGGER.warning("[MyElectrica] Coordinator fără date la setup buttons")
        return

    hierarchy = coordinator.data.get("hierarchy", [])
    selected_nlcs = config_entry.data.get("selected_nlcs")
    buttons: list[ButtonEntity] = []

    for client in hierarchy:
        client_code = client.get("ClientCode", "")
        client_name = client.get("ClientName", "")

        for contract in client.get("to_ContContract", []):
            contract_account = contract.get("ContractAccount", "")

            for loc in contract.get("to_LocConsum", []):
                nlc = loc.get("IdLocConsum", "")
                if not nlc:
                    continue

                if selected_nlcs and nlc not in selected_nlcs:
                    continue

                address = build_address(loc)

                ctx = NlcContext(
                    nlc=nlc,
                    client_code=client_code,
                    client_name=client_name,
                    contract_account=contract_account,
                    address=address,
                )

                buttons.append(
                    TrimiteIndexButton(coordinator, config_entry, ctx)
                )

    _LOGGER.debug(
        "[MyElectrica] Se adaugă %s butoane (entry_id=%s)",
        len(buttons),
        config_entry.entry_id,
    )

    async_add_entities(buttons)


class TrimiteIndexButton(
    CoordinatorEntity[MyElectricaCoordinator], ButtonEntity
):
    """Buton pentru trimiterea autocitiri (set-index) per NLC."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:send"
    _attr_translation_key = "trimite_index"

    def __init__(
        self,
        coordinator: MyElectricaCoordinator,
        config_entry: ConfigEntry,
        ctx: NlcContext,
    ) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._ctx = ctx
        self._attr_name = "Trimite index"
        self._attr_unique_id = f"{DOMAIN}_{ctx.nlc}_trimite_index"
        self._custom_entity_id = f"button.{DOMAIN}_{ctx.nlc}_trimite_index"

    @property
    def entity_id(self) -> str | None:
        """Returnează ID-ul entității."""
        return self._custom_entity_id

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setează ID-ul entității."""
        self._custom_entity_id = value

    @property
    def device_info(self) -> DeviceInfo:
        """Asociază butonul la device-ul NLC-ului."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._ctx.nlc)},
            name=f"MyElectrica {self._ctx.nlc}",
            manufacturer="Ciprian Nicolae (cnecrea)",
            model="MyElectrica România",
            entry_type=DeviceEntryType.SERVICE,
        )

    def _get_meter_info(self) -> tuple[str, str, str]:
        """
        Extrage din meter_list: SerieContor, RegisterCode, ProductName.

        Returnează (serie_contor, register_code, product_name) sau
        ("", "", "") dacă datele lipsesc.
        """
        if not self.coordinator.data:
            return "", "", ""

        # Serie contor și register code din meter_list
        meter_bucket = self.coordinator.data.get("meter_list", {})
        meter_raw = meter_bucket.get(self._ctx.nlc)
        meter_resp = get_body_response(meter_raw)

        serie_contor = ""
        register_code = ""

        if meter_resp:
            contoare = meter_resp.get("to_Contor", [])
            if contoare:
                contor = contoare[0]
                serie_contor = contor.get("SerieContor", "")
                cadrane = contor.get("to_Cadran", [])
                if cadrane:
                    register_code = cadrane[0].get("RegisterCode", "")

        # Product name din contract_details
        contract_bucket = self.coordinator.data.get("contract_details", {})
        contract_raw = contract_bucket.get(self._ctx.nlc)
        contract_resp = get_body_response(contract_raw)

        product_name = ""
        if contract_resp:
            product_name = contract_resp.get("ProductName", "")

        # Fallback: dacă ProductName e gol, caută ServiceType din ierarhie
        if not product_name:
            hierarchy = self.coordinator.data.get("hierarchy", [])
            for client in hierarchy:
                for contract in client.get("to_ContContract", []):
                    for loc in contract.get("to_LocConsum", []):
                        if loc.get("IdLocConsum") == self._ctx.nlc:
                            product_name = loc.get("ServiceType", "")
                            break

        return serie_contor, register_code, product_name

    def _get_input_number_entity_id(self, product_name: str) -> str | None:
        """Determină entity_id-ul input_number pe baza tipului de produs."""
        key = product_name.strip().lower()
        return _INPUT_NUMBER_MAP.get(key)

    @property
    def extra_state_attributes(self):
        """Afișează informații utile despre contor și sursa indexului."""
        serie, register, product = self._get_meter_info()
        input_entity = self._get_input_number_entity_id(product) or "Neconfigurat"

        return {
            "NLC": self._ctx.nlc,
            "Serie contor": serie or "Necunoscut",
            "Cod registru": register or "Necunoscut",
            "Produs": product or "Necunoscut",
            "Sursă index": input_entity,
            "attribution": ATTRIBUTION,
        }

    async def async_press(self) -> None:
        """Trimite indexul citit din input_number către API."""
        serie_contor, register_code, product_name = self._get_meter_info()

        if not serie_contor or not register_code:
            _LOGGER.error(
                "[MyElectrica] Nu se pot determina datele contorului "
                "pentru NLC %s (serie=%s, register=%s)",
                self._ctx.nlc,
                serie_contor,
                register_code,
            )
            return

        # Determinăm entity_id-ul input_number
        input_entity_id = self._get_input_number_entity_id(product_name)
        if not input_entity_id:
            _LOGGER.error(
                "[MyElectrica] Nu se poate determina input_number pentru "
                "produsul '%s' (NLC: %s). Produse suportate: "
                "Electricitate → input_number.energy_meter_reading, "
                "Gaz → input_number.gas_meter_reading",
                product_name,
                self._ctx.nlc,
            )
            return

        # Citim valoarea din input_number
        state = self.hass.states.get(input_entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            _LOGGER.error(
                "[MyElectrica] Entitatea %s nu există sau nu are valoare "
                "(NLC: %s)",
                input_entity_id,
                self._ctx.nlc,
            )
            return

        try:
            index_value = str(int(float(state.state)))
        except (ValueError, TypeError):
            _LOGGER.error(
                "[MyElectrica] Valoare invalidă în %s: '%s' (NLC: %s)",
                input_entity_id,
                state.state,
                self._ctx.nlc,
            )
            return

        _LOGGER.info(
            "[MyElectrica] Trimitere index: NLC=%s, contor=%s, "
            "registru=%s, index=%s (sursă: %s)",
            self._ctx.nlc,
            serie_contor,
            register_code,
            index_value,
            input_entity_id,
        )

        # Apelăm API-ul
        result = await self.coordinator.api.async_set_index(
            nlc=self._ctx.nlc,
            serie_contor=serie_contor,
            register_code=register_code,
            index_value=index_value,
        )

        if result:
            # Verificăm dacă e eroare în răspuns
            body = result.get("body", {})
            response = body.get("response", {}) if isinstance(body, dict) else {}
            error_details = response.get("errorDetails") if isinstance(response, dict) else None
            errors = result.get("errors", [])

            if error_details:
                _LOGGER.error(
                    "[MyElectrica] Eroare la trimitere index NLC %s: %s",
                    self._ctx.nlc,
                    error_details,
                )
            elif errors:
                # Extragem mesajele de eroare pentru log clar
                err_msgs = [
                    e.get("errorMessage", str(e))
                    for e in errors
                    if isinstance(e, dict)
                ] or [str(errors)]
                _LOGGER.error(
                    "[MyElectrica] Eroare trimitere index NLC %s: %s",
                    self._ctx.nlc,
                    "; ".join(err_msgs),
                )
            else:
                _LOGGER.info(
                    "[MyElectrica] Index trimis cu succes pentru NLC %s "
                    "(index=%s)",
                    self._ctx.nlc,
                    index_value,
                )

                # Forțăm refresh date după trimitere
                await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "[MyElectrica] Trimitere index eșuată pentru NLC %s — "
                "API-ul nu a returnat date (posibil eroare de rețea sau "
                "timeout; verifică logurile anterioare)",
                self._ctx.nlc,
            )
