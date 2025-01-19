"""
Definirea senzorilor pentru integrarea MyElectrica România.
"""

import logging
from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MONTHS_RO

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """
    Configurează entitățile de tip senzor pentru o intrare specifică din config_entries.
    """
    _LOGGER.debug("Configurarea senzorilor pentru entry_id=%s", entry.entry_id)

    # Obținem coordinatorul din hass.data
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Creăm entitățile senzor
    async_add_entities([
        ContulMeuSensor(coordinator, entry.entry_id),
        IndexCurentSensor(coordinator, entry.entry_id),
        ConventieSensor(coordinator, entry.entry_id),
        FacturaRestantaSensor(coordinator, entry.entry_id),
        IstoricPlatiSensor(coordinator, entry.entry_id),
    ])

    _LOGGER.debug("Senzorii au fost adăugați pentru entry_id=%s", entry.entry_id)


class ContulMeuSensor(CoordinatorEntity, SensorEntity):
    """Senzor pentru afișarea informațiilor despre contul utilizatorului."""

    def __init__(self, coordinator, entry_id):
        """Inițializează senzorul ContulMeu."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_contulmeu"
        self._attr_name = "MyElectrica"
        self._entity_id = f"sensor.myelectrica_contul_meu_{entry_id}"
        self._icon = "mdi:account-circle"

    @property
    def state(self):
        """Returnează starea senzorului (statusul contractului)."""
        return self.native_value

    @property
    def native_value(self):
        """
        Returnează valoarea principală a senzorului.
        În acest caz, afișăm codul clientului din configurarea intrării.
        """
        return self.coordinator.config_entry.data.get("cod_client", "Necunoscut")

    @property
    def extra_state_attributes(self):
        """
        Returnează atributele adiționale ale senzorului.
        Acestea includ informații suplimentare despre contractul utilizatorului.
        """
        data = self.coordinator.data.get("contulmeu", {})
        if data and "body" in data and "response" in data["body"]:
            contract_data = data["body"]["response"]
            return {
                "Cod încasare": self.coordinator.config_entry.data.get("cod_incasare", "Necunoscut"),
                "Cod loc de consum (NLC)": self.coordinator.config_entry.data.get("cod_nlc", "Necunoscut"),
                "Cod client": self.coordinator.config_entry.data.get("cod_client", "Necunoscut"),
                "Dată semnării contractului": contract_data.get("ContractDate", "Necunoscut"),
                "Tip contract": contract_data.get("ContractType", "Necunoscut").capitalize(),
            }
        return {}

    @property
    def unique_id(self):
        """Returnează ID-ul unic al senzorului."""
        return self._attr_unique_id

    @property
    def entity_id(self):
        """Returnează ID-ul entității."""
        return self._entity_id

    @entity_id.setter
    def entity_id(self, value):
        """Setează ID-ul entității."""
        self._entity_id = value

    @property
    def icon(self):
        """Returnează iconița asociată senzorului."""
        return self._icon

    @property
    def device_info(self):
        """Informații despre dispozitiv pentru integrare."""
        return {
            "identifiers": {(DOMAIN, "myelectrica")},
            "name": "myElectrica România",
            "manufacturer": "Ciprian Nicolae (cnecrea)",
            "model": "MyElectrica România",
            "entry_type": DeviceEntryType.SERVICE,
        }


class IndexCurentSensor(CoordinatorEntity, SensorEntity):
    """Senzor pentru afișarea informațiilor despre indexul curent al contorului."""

    def __init__(self, coordinator, entry_id):
        """Inițializează senzorul IndexCurent."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_index_curent"
        self._attr_name = "Index curent"
        self._entity_id = f"sensor.myelectrica_index_curent_{entry_id}"
        self._icon = "mdi:counter"

    @property
    def state(self):
        """Returnează starea senzorului (Index-ul curent)."""
        data = self.coordinator.data.get("indexcurent", {})
        if not data or "body" not in data or "response" not in data["body"]:
            return None

        to_contor = data["body"]["response"].get("to_Contor", [])
        if to_contor:
            return to_contor[0]["to_Cadran"][0]["Index"]
        return None

    @property
    def extra_state_attributes(self):
        """
        Returnează atributele adiționale ale senzorului.
        Acestea includ informații suplimentare despre contor.
        """
        data = self.coordinator.data.get("indexcurent", {})
        if not data or "body" not in data or "response" not in data["body"]:
            return {}

        attributes = {}
        to_contor = data["body"]["response"].get("to_Contor", [])
        if to_contor:
            contor = to_contor[0]
            cadran = contor.get("to_Cadran", [])[0]
            attributes["Numărul dispozitivului"] = contor.get("SerieContor", "Necunoscut")
            attributes["Data citirii"] = cadran.get("ReadingDate", "Necunoscut")
            attributes["Ultima citire validată"] = cadran.get("Index", "Necunoscut")
            attributes["Tipul citirii"] = cadran.get("MeterReadingType", "Necunoscut")
            attributes["Perioadă citire contor începere"] = data["body"]["response"].get("StartDatePAC", "Necunoscut")
            attributes["Perioadă citire contor sfârșit"] = data["body"]["response"].get("EndDatePAC", "Necunoscut")

        return attributes

    @property
    def unique_id(self):
        """Returnează ID-ul unic al senzorului."""
        return self._attr_unique_id

    @property
    def entity_id(self):
        """Returnează ID-ul entității."""
        return self._entity_id

    @entity_id.setter
    def entity_id(self, value):
        """Setează ID-ul entității."""
        self._entity_id = value

    @property
    def icon(self):
        """Returnează iconița asociată senzorului."""
        return self._icon

    @property
    def device_info(self):
        """Informații despre dispozitiv pentru integrare."""
        return {
            "identifiers": {(DOMAIN, "myelectrica")},
            "name": "myElectrica România",
            "manufacturer": "Ciprian Nicolae (cnecrea)",
            "model": "MyElectrica România",
            "entry_type": DeviceEntryType.SERVICE,
        }


class ConventieSensor(CoordinatorEntity, SensorEntity):
    """Senzor pentru afișarea informațiilor despre convenția de consum."""

    def __init__(self, coordinator, entry_id):
        """Inițializează senzorul ConventieSensor."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_conventie"
        self._attr_name = "Conventie consum"
        self._entity_id = f"sensor.myelectrica_conventie_{entry_id}"
        self._icon = "mdi:calendar-clock"

    @property
    def state(self):
        """Returnează starea senzorului (numărul de luni cu date nenule de consum)."""
        data = self.coordinator.data.get("conventie", {})
        if data and "body" in data and "response" in data["body"]:
            conventie_data = data["body"]["response"]
            # Filtrăm lunile care au valoare nenulă pentru "Quantity"
            valid_months = [item for item in conventie_data if item.get("Quantity") != "0"]
            return len(valid_months)
        return 0

    @property
    def extra_state_attributes(self):
        """
        Returnează atributele adiționale ale senzorului.
        Acestea includ datele lunare despre convenția de consum, inclusiv lunile cu "Quantity".
        """
        data = self.coordinator.data.get("conventie", {})
        if data and "body" in data and "response" in data["body"]:
            conventie_data = data["body"]["response"]
            attributes = {}

            for item in conventie_data:
                month = item.get("Month", "Necunoscut")
                quantity = item.get("Quantity", "Necunoscut")
                # Folosim denumirea lunii în limba română
                month_name_ro = MONTHS_RO.get(month.zfill(2), "Necunoscut")
                attributes[f"Luna {month_name_ro}"] = f"{quantity} kWh"

            return attributes
        return {}

    @property
    def unique_id(self):
        """Returnează ID-ul unic al senzorului."""
        return self._attr_unique_id

    @property
    def entity_id(self):
        """Returnează ID-ul entității."""
        return self._entity_id

    @entity_id.setter
    def entity_id(self, value):
        """Setează ID-ul entității."""
        self._entity_id = value

    @property
    def icon(self):
        """Returnează iconița asociată senzorului."""
        return self._icon

    @property
    def device_info(self):
        """Informații despre dispozitiv pentru integrare."""
        return {
            "identifiers": {(DOMAIN, "myelectrica")},
            "name": "myElectrica România",
            "manufacturer": "Ciprian Nicolae (cnecrea)",
            "model": "MyElectrica România",
            "entry_type": DeviceEntryType.SERVICE,
        }


class FacturaRestantaSensor(CoordinatorEntity, SensorEntity):
    """Senzor pentru afișarea informațiilor despre facturile restante."""

    def __init__(self, coordinator, entry_id):
        """Inițializează senzorul FacturaRestantaSensor."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_factura_restanta"
        self._attr_name = "Factură restantă"
        self._entity_id = f"sensor.myelectrica_factura_restanta_{entry_id}"
        self._icon = "mdi:file-document-alert-outline"

    @property
    def state(self):
        """Returnează starea principală a senzorului."""
        data = self.coordinator.data.get("factura_restanta", {})
        if not data or "body" not in data or "response" not in data["body"]:
            return "Nu"

        # Verificăm dacă există cel puțin o factură neachitată
        for factura in data["body"]["response"]:
            if factura.get("InvoiceStatus") == "neachitat":
                return "Da"
        return "Nu"

    @property
    def extra_state_attributes(self):
        """
        Returnează atributele adiționale ale senzorului.
        Acestea includ detalii despre facturile neachitate, formate conform preferințelor de design.
        """
        data = self.coordinator.data.get("factura_restanta", {})
        if not data or "body" not in data or "response" not in data["body"]:
            return {}

        attributes = {}
        total_unpaid = 0.0

        # Procesăm facturile neachitate
        for idx, factura in enumerate(data["body"]["response"], start=1):
            if factura.get("InvoiceStatus") == "neachitat":
                unpaid_value = float(factura.get("UnpaidValue", 0))
                total_unpaid += unpaid_value

                issue_date = factura.get("IssueDate", "Necunoscut")
                try:
                    parsed_date = datetime.strptime(issue_date, "%Y-%m-%d")
                    month_name_en = parsed_date.strftime("%B")
                    month_name_ro = MONTHS_RO.get(month_name_en, "necunoscut")
                except ValueError:
                    month_name_ro = "necunoscut"

                attributes[f"Restanță pe luna {month_name_ro} (#{idx})"] = f"{unpaid_value:.2f} lei"
                attributes[f"Factură #{idx} - Scadență"] = factura.get("DueDate", "Necunoscut")

        attributes["---------------"] = ""
        attributes["Total neachitat"] = f"{total_unpaid:.2f} lei" if total_unpaid > 0 else "0.00 lei"
        return attributes

    @property
    def unique_id(self):
        """Returnează ID-ul unic al senzorului."""
        return self._attr_unique_id

    @property
    def entity_id(self):
        """Returnează ID-ul entității."""
        return self._entity_id

    @entity_id.setter
    def entity_id(self, value):
        """Setează ID-ul entității."""
        self._entity_id = value

    @property
    def icon(self):
        """Returnează iconița asociată senzorului."""
        return self._icon

    @property
    def device_info(self):
        """Informații despre dispozitiv pentru integrare."""
        return {
            "identifiers": {(DOMAIN, "myelectrica")},
            "name": "myElectrica România",
            "manufacturer": "Ciprian Nicolae (cnecrea)",
            "model": "MyElectrica România",
            "entry_type": DeviceEntryType.SERVICE,
        }


class IstoricPlatiSensor(CoordinatorEntity, SensorEntity):
    """Senzor pentru afișarea istoricului de plăți din ultimele 12 luni."""

    def __init__(self, coordinator, entry_id):
        """Inițializează senzorul IstoricPlati."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_istoric_plati"
        self._attr_name = "Istoric plăți"
        self._entity_id = f"sensor.myelectrica_istoric_plati_{entry_id}"
        self._icon = "mdi:cash-check"

    @property
    def state(self):
        """Returnează starea senzorului (numărul total al facturilor plătite)."""
        data = self.coordinator.data.get("facturi", {})
        if data and "body" in data and "response" in data["body"]:
            facturi_platite = [
                factura for factura in data["body"]["response"]
                if factura.get("InvoiceStatus") == "achitat"
            ]
            return len(facturi_platite[:12])  # Numărăm ultimele 12 facturi
        return 0

    @property
    def extra_state_attributes(self):
        """
        Returnează atributele adiționale ale senzorului.
        Acestea includ detalii despre ultimele 12 facturi achitate.
        """
        data = self.coordinator.data.get("facturi", {})
        if not data or "body" not in data or "response" not in data["body"]:
            return {}

        attributes = {}
        total_amount = 0.0

        for factura in data["body"]["response"]:
            if factura.get("InvoiceStatus") == "achitat":
                issue_date = factura.get("IssueDate", "Necunoscut")
                try:
                    parsed_date = datetime.strptime(issue_date, "%Y-%m-%d")
                    day = parsed_date.day
                    year = parsed_date.year
                    month_name_en = parsed_date.strftime("%B")
                    month_name_ro = MONTHS_RO.get(month_name_en, "necunoscut")
                    friendly_date = f"Emisă la {day} {month_name_ro} {year}"
                except ValueError:
                    friendly_date = "Necunoscut"

                amount = float(factura.get("TotalAmount", 0))
                total_amount += amount

                # Adăugăm data emisiei ca cheie și valoarea facturii ca valoare
                attributes[f"{friendly_date}"] = f"{amount:.2f} lei"

        # Separator și total
        attributes["---------------"] = ""
        attributes["Total"] = f"{total_amount:.2f} lei"
        return attributes

    @property
    def unique_id(self):
        """Returnează ID-ul unic al senzorului."""
        return self._attr_unique_id

    @property
    def entity_id(self):
        """Returnează ID-ul entității."""
        return self._entity_id

    @entity_id.setter
    def entity_id(self, value):
        """Setează ID-ul entității."""
        self._entity_id = value

    @property
    def icon(self):
        """Returnează iconița asociată senzorului."""
        return self._icon

    @property
    def device_info(self):
        """Informații despre dispozitiv pentru integrare."""
        return {
            "identifiers": {(DOMAIN, "myelectrica")},
            "name": "myElectrica România",
            "manufacturer": "Ciprian Nicolae (cnecrea)",
            "model": "MyElectrica România",
            "entry_type": DeviceEntryType.SERVICE,
        }
