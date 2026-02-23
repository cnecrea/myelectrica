"""Platforma Sensor pentru MyElectrica România."""

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, ATTRIBUTION, MONTHS_EN_RO, MONTHS_NUM_RO
from .coordinator import MyElectricaCoordinator

_LOGGER = logging.getLogger(__name__)


def format_ron(value: float) -> str:
    """Formatează o valoare numerică în format românesc (1.234,56)."""
    formatted = f"{value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------------------------------------------------------------
# Clasă de bază pentru toate entitățile MyElectrica România
# ------------------------------------------------------------------------
class MyElectricaEntity(CoordinatorEntity[MyElectricaCoordinator], SensorEntity):
    """Clasă de bază pentru entitățile MyElectrica România."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: MyElectricaCoordinator, config_entry: ConfigEntry):
        """Inițializare cu coordinator și config_entry."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._cod_incasare = config_entry.data["cod_incasare"]
        self._custom_entity_id: str | None = None

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
        """Returnează informațiile despre dispozitiv — comun tuturor entităților."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._cod_incasare)},
            name=f"MyElectrica România ({self._cod_incasare})",
            manufacturer="Ciprian Nicolae (cnecrea)",
            model="MyElectrica România",
            entry_type=DeviceEntryType.SERVICE,
        )

    def _get_response(self, key: str):
        """
        Extrage coordinator.data[key]["body"]["response"] în mod sigur.
        Returnează None dacă orice nivel lipsește.
        """
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(key)
        if not isinstance(raw, dict):
            return None
        body = raw.get("body")
        if not isinstance(body, dict):
            return None
        return body.get("response")


# ------------------------------------------------------------------------
# async_setup_entry
# ------------------------------------------------------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
):
    """Configurează senzorii pentru intrarea dată (config_entry)."""
    coordinator: MyElectricaCoordinator = config_entry.runtime_data
    cod_incasare = config_entry.data.get("cod_incasare", "")

    sensors: list[SensorEntity] = []

    _LOGGER.debug(
        "Inițializare platforma sensor pentru %s (entry_id=%s, contract=%s).",
        DOMAIN,
        config_entry.entry_id,
        cod_incasare,
    )

    # 1. Senzori de bază
    sensors.append(ContulMeuSensor(coordinator, config_entry))
    sensors.append(IndexCurentSensor(coordinator, config_entry))
    sensors.append(ConventieConsumSensor(coordinator, config_entry))
    sensors.append(FacturaRestantaSensor(coordinator, config_entry))
    sensors.append(IstoricPlatiSensor(coordinator, config_entry))

    _LOGGER.debug(
        "Se adaugă %s senzori pentru %s (entry_id=%s, contract=%s).",
        len(sensors),
        DOMAIN,
        config_entry.entry_id,
        cod_incasare,
    )

    # Înregistrăm senzorii
    async_add_entities(sensors)


# ------------------------------------------------------------------------
# ContulMeuSensor
# ------------------------------------------------------------------------
class ContulMeuSensor(MyElectricaEntity):
    """Senzor pentru afișarea informațiilor despre contul utilizatorului."""

    _attr_icon = "mdi:account-circle"
    _attr_translation_key = "contul_meu"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_name = "MyElectrica"
        self._attr_unique_id = f"{DOMAIN}_contul_meu_{config_entry.entry_id}"
        self._custom_entity_id = f"sensor.{DOMAIN}_{self._cod_incasare}_contul_meu"

    @property
    def native_value(self):
        """Returnează codul clientului ca valoare principală."""
        return self._config_entry.data.get("cod_client", "Necunoscut")

    @property
    def extra_state_attributes(self):
        """Atribute adiționale — detalii contract."""
        response = self._get_response("contulmeu")
        if not response:
            return {"attribution": ATTRIBUTION}

        attributes = {
            "Cod încasare": self._config_entry.data.get("cod_incasare", "Necunoscut"),
            "Cod loc de consum (NLC)": self._config_entry.data.get("cod_nlc", "Necunoscut"),
            "Cod client": self._config_entry.data.get("cod_client", "Necunoscut"),
            "Dată semnării contractului": response.get("ContractDate", "Necunoscut"),
            "Tip contract": response.get("ContractType", "Necunoscut").capitalize(),
        }

        attributes["attribution"] = ATTRIBUTION
        return attributes


# ------------------------------------------------------------------------
# IndexCurentSensor
# ------------------------------------------------------------------------
class IndexCurentSensor(MyElectricaEntity):
    """Senzor pentru afișarea informațiilor despre indexul curent al contorului."""

    _attr_icon = "mdi:counter"
    _attr_translation_key = "index_curent"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_name = "Index curent"
        self._attr_unique_id = f"{DOMAIN}_index_curent_{config_entry.entry_id}"
        self._custom_entity_id = f"sensor.{DOMAIN}_{self._cod_incasare}_index_curent"

    def _get_first_cadran(self) -> tuple[dict | None, dict | None]:
        """Returnează (contor, cadran) sau (None, None) dacă lipsesc."""
        response = self._get_response("indexcurent")
        if not response:
            return None, None

        contoare = response.get("to_Contor", [])
        if not contoare:
            return None, None

        contor = contoare[0]
        cadrane = contor.get("to_Cadran", [])
        if not cadrane:
            return contor, None

        return contor, cadrane[0]

    @property
    def native_value(self):
        """Returnează valoarea indexului curent."""
        _, cadran = self._get_first_cadran()
        if cadran is None:
            return None
        return cadran.get("Index")

    @property
    def extra_state_attributes(self):
        """Atribute adiționale — detalii contor și citire."""
        response = self._get_response("indexcurent")
        contor, cadran = self._get_first_cadran()
        if contor is None or cadran is None:
            return {"attribution": ATTRIBUTION}

        attributes = {
            "Numărul dispozitivului": contor.get("SerieContor", "Necunoscut"),
            "Data citirii": cadran.get("ReadingDate", "Necunoscut"),
            "Ultima citire validată": cadran.get("Index", "Necunoscut"),
            "Tipul citirii": cadran.get("MeterReadingType", "Necunoscut"),
            "Perioadă citire contor începere": response.get("StartDatePAC", "Necunoscut"),
            "Perioadă citire contor sfârșit": response.get("EndDatePAC", "Necunoscut"),
        }

        attributes["attribution"] = ATTRIBUTION
        return attributes


# ------------------------------------------------------------------------
# ConventieConsumSensor
# ------------------------------------------------------------------------
class ConventieConsumSensor(MyElectricaEntity):
    """Senzor pentru afișarea datelor de convenție de consum."""

    _attr_icon = "mdi:calendar-clock"
    _attr_translation_key = "conventie_consum"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_name = "Convenție consum"
        self._attr_unique_id = f"{DOMAIN}_conventie_consum_{config_entry.entry_id}"
        self._custom_entity_id = f"sensor.{DOMAIN}_{self._cod_incasare}_conventie_consum"

    @property
    def native_value(self):
        """Returnează numărul lunilor cu consum nenul."""
        response = self._get_response("conventie")
        if not response:
            return 0
        return len([item for item in response if item.get("Quantity") != "0"])

    @property
    def extra_state_attributes(self):
        """Atribute adiționale — detalii lunare consum."""
        response = self._get_response("conventie")
        if not response:
            return {"attribution": ATTRIBUTION}

        attributes = {}

        for item in response:
            month = item.get("Month", "Necunoscut")
            quantity = item.get("Quantity", "Necunoscut")
            month_name = MONTHS_NUM_RO.get(month.zfill(2), "Necunoscut")
            attributes[f"Luna {month_name}"] = f"{quantity} kWh"

        attributes["attribution"] = ATTRIBUTION
        return attributes


# ------------------------------------------------------------------------
# FacturaRestantaSensor
# ------------------------------------------------------------------------
class FacturaRestantaSensor(MyElectricaEntity):
    """Senzor pentru afișarea soldului restant al facturilor."""

    _attr_icon = "mdi:file-document-alert-outline"
    _attr_translation_key = "factura_restanta"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_name = "Factură restantă"
        self._attr_unique_id = f"{DOMAIN}_factura_restanta_{config_entry.entry_id}"
        self._custom_entity_id = f"sensor.{DOMAIN}_{self._cod_incasare}_factura_restanta"

    def _facturi_neachitate(self) -> list[dict]:
        """Filtrează și returnează lista facturilor neachitate."""
        response = self._get_response("factura_restanta")
        if not response:
            return []
        return [f for f in response if f.get("InvoiceStatus") == "neachitat"]

    @property
    def native_value(self):
        """Returnează starea principală (Da/Nu)."""
        return "Da" if self._facturi_neachitate() else "Nu"

    @property
    def extra_state_attributes(self):
        """Atribute adiționale — detalii facturi neachitate."""
        neachitate = self._facturi_neachitate()

        if not neachitate:
            return {
                "Total neachitat": "0,00 lei",
                "attribution": ATTRIBUTION,
            }

        attributes = {}
        total = 0.0
        today = dt_util.now().date()

        for idx, factura in enumerate(neachitate, start=1):
            unpaid = float(factura.get("UnpaidValue", 0))
            if unpaid <= 0:
                continue

            total += unpaid

            # Luna din IssueDate (YYYY-MM-DD)
            issue_raw = factura.get("IssueDate")
            month_name = "necunoscut"
            try:
                parsed_issue = datetime.strptime(issue_raw, "%Y-%m-%d")
                month_number = parsed_issue.strftime("%m")
                month_name = MONTHS_NUM_RO.get(month_number, "necunoscut")
            except (ValueError, TypeError):
                pass

            # Calcul scadență
            due_raw = factura.get("DueDate")
            try:
                parsed_due = datetime.strptime(due_raw, "%Y-%m-%d")
                days_until_due = (parsed_due.date() - today).days

                if days_until_due < 0:
                    unit = "zi" if abs(days_until_due) == 1 else "zile"
                    message = (
                        f"{format_ron(unpaid)} lei — termen depășit cu "
                        f"{abs(days_until_due)} {unit}"
                    )
                elif days_until_due == 0:
                    message = f"{format_ron(unpaid)} lei — scadentă astăzi"
                else:
                    unit = "zi" if days_until_due == 1 else "zile"
                    message = (
                        f"{format_ron(unpaid)} lei — scadentă în "
                        f"{days_until_due} {unit}"
                    )

            except (ValueError, TypeError):
                message = f"{format_ron(unpaid)} lei — scadență necunoscută"

            attributes[f"Restanță pe luna {month_name} (#{idx})"] = message

        attributes["Total neachitat"] = (
            format_ron(total) + " lei" if total > 0 else "0,00 lei"
        )
        attributes["attribution"] = ATTRIBUTION

        return attributes


# ------------------------------------------------------------------------
# IstoricPlatiSensor
# ------------------------------------------------------------------------
class IstoricPlatiSensor(MyElectricaEntity):
    """Senzor pentru afișarea istoricului de plăți din ultimele 12 luni."""

    _attr_icon = "mdi:cash-check"
    _attr_translation_key = "istoric_plati"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_name = "Istoric plăți"
        self._attr_unique_id = f"{DOMAIN}_istoric_plati_{config_entry.entry_id}"
        self._custom_entity_id = f"sensor.{DOMAIN}_{self._cod_incasare}_istoric_plati"

    def _facturi_achitate(self) -> list[dict]:
        """Returnează facturile achitate (maxim 12)."""
        response = self._get_response("facturi")
        if not response:
            return []
        achitate = [f for f in response if f.get("InvoiceStatus") == "achitat"]
        return achitate[:12]

    @property
    def native_value(self):
        """Returnează numărul facturilor achitate (max 12)."""
        return len(self._facturi_achitate())

    @property
    def extra_state_attributes(self):
        """Atribute adiționale — detalii facturi achitate."""
        achitate = self._facturi_achitate()
        if not achitate:
            return {
                "Total": "0,00 lei",
                "attribution": ATTRIBUTION,
            }

        attributes = {}
        total = 0.0

        for factura in achitate:
            issue_date = factura.get("IssueDate", "")
            amount = float(factura.get("TotalAmount", 0))
            total += amount

            friendly = _format_date_ro(issue_date)
            attributes[f"Emisă la {friendly}"] = f"{format_ron(amount)} lei"

        attributes["---------------"] = ""
        attributes["Total"] = f"{format_ron(total)} lei"
        attributes["attribution"] = ATTRIBUTION
        return attributes


# ------------------------------------------------------------------------
# Utilități
# ------------------------------------------------------------------------
def _parse_month_ro(date_str: str) -> str:
    """Extrage luna în română dintr-un string ISO (YYYY-MM-DD)."""
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        return MONTHS_EN_RO.get(parsed.strftime("%B"), "necunoscut")
    except (ValueError, TypeError):
        return "necunoscut"


def _format_date_ro(date_str: str) -> str:
    """Formatează o dată ISO ca '5 ianuarie 2025'."""
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        month = MONTHS_EN_RO.get(parsed.strftime("%B"), "necunoscut")
        return f"{parsed.day} {month} {parsed.year}"
    except (ValueError, TypeError):
        return "Necunoscut"
