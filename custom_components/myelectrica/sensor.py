"""
Platforma Sensor pentru MyElectrica România.

Creează câte un device per NLC (loc de consum) descoperit în ierarhie,
fiecare cu 9 senzori:
  1. Date contract      (3.3)
  2. Date client        (3.2)
  3. Index curent       (6.1)
  4. Istoric citiri     (7.1)
  5. Citire permisă     (6.1 PAC)
  6. Convenție consum   (8.1)
  7. Arhivă facturi     (4.1)
  8. Factură restantă   (4.1 filtrat)
  9. Arhivă plăți       (5.1)
"""

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTRIBUTION, DOMAIN, MONTHS_NUM_RO
from .coordinator import MyElectricaCoordinator
from .helper import (
    build_address,
    build_address_consum,
    format_date_ro,
    format_ron,
    get_body_response,
    get_judet,
    safe_float,
    client_type_friendly,
)

_LOGGER = logging.getLogger(__name__)


# ── async_setup_entry ────────────────────────────


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurează senzorii pe baza ierarhiei descoperite."""
    coordinator: MyElectricaCoordinator = config_entry.runtime_data

    if not coordinator.data:
        _LOGGER.warning("[MyElectrica] Coordinator fără date la setup")
        return

    hierarchy = coordinator.data.get("hierarchy", [])
    sensors: list[SensorEntity] = []

    # NLC-urile selectate de utilizator (dacă există)
    selected_nlcs = config_entry.data.get("selected_nlcs")

    # Iterăm ierarhia: client → contract → NLC
    for client in hierarchy:
        client_code = client.get("ClientCode", "")
        client_name = client.get("ClientName", "")

        for contract in client.get("to_ContContract", []):
            contract_account = contract.get("ContractAccount", "")

            for loc in contract.get("to_LocConsum", []):
                nlc = loc.get("IdLocConsum", "")
                if not nlc:
                    continue

                # Filtrare: doar NLC-urile selectate
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

                sensors.extend([
                    ContractNlcSensor(coordinator, config_entry, ctx),
                    ClientDataSensor(coordinator, config_entry, ctx),
                    IndexCurentSensor(coordinator, config_entry, ctx),
                    IstoricCitiriSensor(coordinator, config_entry, ctx),
                    CitirePermisaSensor(coordinator, config_entry, ctx),
                    ConventieConsumSensor(coordinator, config_entry, ctx),
                    ArhivaFacturiSensor(coordinator, config_entry, ctx),
                    FacturaRestantaSensor(coordinator, config_entry, ctx),
                    ArhivaPlatiSensor(coordinator, config_entry, ctx),
                ])

    _LOGGER.debug(
        "[MyElectrica] Se adaugă %s senzori (entry_id=%s)",
        len(sensors),
        config_entry.entry_id,
    )

    async_add_entities(sensors)


# ── Context NLC (date partajate între senzori) ───


class NlcContext:
    """Date contextuale pentru un NLC — partajate între senzori."""

    __slots__ = (
        "nlc",
        "client_code",
        "client_name",
        "contract_account",
        "address",
    )

    def __init__(
        self,
        nlc: str,
        client_code: str,
        client_name: str,
        contract_account: str,
        address: str,
    ) -> None:
        self.nlc = nlc
        self.client_code = client_code
        self.client_name = client_name
        self.contract_account = contract_account
        self.address = address


# ── Clasă de bază ────────────────────────────────

class MyElectricaEntity(
    CoordinatorEntity[MyElectricaCoordinator], SensorEntity
):
    """Clasă de bază pentru entitățile MyElectrica România."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: MyElectricaCoordinator,
        config_entry: ConfigEntry,
        ctx: NlcContext,
    ) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._ctx = ctx

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
        """Fiecare NLC = un device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._ctx.nlc)},
            name=f"MyElectrica {self._ctx.nlc}",
            manufacturer="Ciprian Nicolae (cnecrea)",
            model="MyElectrica România",
            entry_type=DeviceEntryType.SERVICE,
        )

    def _get_nlc_response(self, data_key: str):
        """Extrage body.response pentru NLC-ul curent din coordinator.data[key][nlc]."""
        if not self.coordinator.data:
            return None
        bucket = self.coordinator.data.get(data_key)
        if not isinstance(bucket, dict):
            return None
        raw = bucket.get(self._ctx.nlc)
        return get_body_response(raw)

    def _get_client_response(self, data_key: str):
        """Extrage body.response pentru client_code-ul curent."""
        if not self.coordinator.data:
            return None
        bucket = self.coordinator.data.get(data_key)
        if not isinstance(bucket, dict):
            return None
        raw = bucket.get(self._ctx.client_code)
        return get_body_response(raw)

    def _get_loc_consum(self) -> dict | None:
        """Caută LocConsum-ul curent (după NLC) în ierarhie."""
        if not self.coordinator.data:
            return None
        hierarchy = self.coordinator.data.get("hierarchy", [])
        for client in hierarchy:
            for contract in client.get("to_ContContract", []):
                for loc in contract.get("to_LocConsum", []):
                    if loc.get("IdLocConsum") == self._ctx.nlc:
                        return loc
        return None


# ── 1. ContractNlcSensor (3.3) ──────────────────

class ContractNlcSensor(MyElectricaEntity):
    """Detalii contract pentru NLC (3.3)."""

    _attr_icon = "mdi:file-document-outline"
    _attr_translation_key = "date_contract"

    def __init__(self, coordinator, config_entry, ctx: NlcContext) -> None:
        super().__init__(coordinator, config_entry, ctx)
        self._attr_name = "Date contract"
        self._attr_unique_id = f"{DOMAIN}_{ctx.nlc}_date_contract"
        self._custom_entity_id = f"sensor.{DOMAIN}_{ctx.nlc}_date_contract"

    @property
    def native_value(self):
        response = self._get_nlc_response("contract_details")
        if not response:
            return None
        # Ia valoarea și pune prima literă mare
        return response.get("ContractStatus", "Necunoscut").capitalize()

    @property
    def extra_state_attributes(self):
        response = self._get_nlc_response("contract_details")
        if not response:
            return {"attribution": ATTRIBUTION}

        product = response.get("ProductName", "")
        if product == "Electricitate":
            product = "Energie electrică"
        elif product == "Gaz":
            product = "Gaze naturale"

        # Date adresă din ierarhie (to_LocConsum)
        loc = self._get_loc_consum()

        attrs = {
            "NLC": self._ctx.nlc,
            "Cod client": self._ctx.client_code,
            "Cont contract": self._ctx.contract_account,
            "Tip contract": response.get("ContractType", "Necunoscut").lower(),
            "Produs": product or "Necunoscut",
            "Dată contract": format_date_ro(
                response.get("ContractDate", "")
            ),
            "Status": response.get("ContractStatus", "Necunoscut").lower(),
            "Metodă estimare": response.get("EstimationMethod", "Necunoscut").lower(),
            "Autocitire disponibilă": (
                "Da"
                if response.get("PACIndicator") == "true"
                else "Nu"
            ),
            "Periodicitate citiri": response.get(
                "PeriodicitateCitiri", "Necunoscut"
            ).lower(),
            "Grupă regională": response.get("RegionGroup", "Necunoscut").lower(),
        }

        if loc:
            attrs["Adresă consum"] = build_address_consum(loc)
            service = loc.get("ServiceType", "")
            if service:
                attrs["Tip serviciu"] = service

        attrs["attribution"] = ATTRIBUTION
        return attrs

# ── 2. ClientDataSensor (3.2) ───────────────────

class ClientDataSensor(MyElectricaEntity):
    """Date client detaliate (3.2)."""

    _attr_icon = "mdi:account-circle"
    _attr_translation_key = "date_client"

    def __init__(self, coordinator, config_entry, ctx: NlcContext) -> None:
        super().__init__(coordinator, config_entry, ctx)
        self._attr_name = "Date client"
        self._attr_unique_id = f"{DOMAIN}_{ctx.nlc}_date_client"
        self._custom_entity_id = f"sensor.{DOMAIN}_{ctx.nlc}_date_client"

    @property
    def native_value(self):
        response = self._get_client_response("client_data")
        if not response:
            return (self._ctx.client_name or "Necunoscut").title()
        return (response.get("ClientName", self._ctx.client_name or "Necunoscut")).title()

    @property
    def extra_state_attributes(self):
        response = self._get_client_response("client_data")
        if not response:
            return {"attribution": ATTRIBUTION}

        address = build_address_consum(response)
        client_type_code = response.get("ClientType", "")
        client_type = client_type_friendly(client_type_code)

        return {
            "Cod client": self._ctx.client_code,
            "Tip client": client_type,
            "Adresă": address,
            "Județ": get_judet(response.get("Region", "")),
            "Telefon": response.get("Telephone", "Necunoscut"),
            "attribution": ATTRIBUTION,
        }


# ── 3. IndexCurentSensor (6.1) ──────────────────

class IndexCurentSensor(MyElectricaEntity):
    """Index curent contor (6.1 — meter-list)."""

    _attr_icon = "mdi:counter"
    _attr_translation_key = "index_curent"

    def __init__(self, coordinator, config_entry, ctx: NlcContext) -> None:
        super().__init__(coordinator, config_entry, ctx)
        self._attr_name = "Index curent"
        self._attr_unique_id = f"{DOMAIN}_{ctx.nlc}_index_curent"
        self._custom_entity_id = f"sensor.{DOMAIN}_{ctx.nlc}_index_curent"

    def _get_meter_data(self) -> tuple[dict | None, dict | None, dict | None]:
        """Returnează (response, contor, cadran) sau (None, None, None)."""
        response = self._get_nlc_response("meter_list")
        if not response:
            return None, None, None

        contoare = response.get("to_Contor", [])
        if not contoare:
            return response, None, None

        contor = contoare[0]
        cadrane = contor.get("to_Cadran", [])
        if not cadrane:
            return response, contor, None

        return response, contor, cadrane[0]

    @property
    def native_value(self):
        _, _, cadran = self._get_meter_data()
        if cadran is None:
            return None
        return cadran.get("Index")

    @property
    def extra_state_attributes(self):
        response, contor, cadran = self._get_meter_data()
        if contor is None or cadran is None:
            return {"attribution": ATTRIBUTION}

        attrs = {
            "Serie contor": contor.get("SerieContor", "Necunoscut"),
            "Data citirii": format_date_ro(
                cadran.get("ReadingDate", "")
            ),
            "Index validat": cadran.get("Index", "Necunoscut"),
            "Tip citire": cadran.get("MeterReadingType", "Necunoscut"),
            "Cod registru": cadran.get("RegisterCode", "Necunoscut"),
            "Descriere registru": cadran.get(
                "RegisterDescription", "Necunoscut"
            ),
        }

        # Date PAC (autocitire)
        index_pac = cadran.get("IndexPAC")
        if index_pac:
            attrs["Index PAC"] = index_pac
            attrs["Data citire PAC"] = format_date_ro(
                cadran.get("ReadingDatePAC", "")
            )

        if response:
            pac = response.get("PACIndicator")
            if pac == "true":
                attrs["Perioadă autocitire început"] = format_date_ro(
                    response.get("StartDatePAC", "")
                )
                attrs["Perioadă autocitire sfârșit"] = format_date_ro(
                    response.get("EndDatePAC", "")
                )

        # Cadrane adiționale (dacă sunt mai multe)
        all_contoare = (response or {}).get("to_Contor", [])
        for c_idx, cnt in enumerate(all_contoare):
            cadrane = cnt.get("to_Cadran", [])
            for d_idx, cdr in enumerate(cadrane):
                if c_idx == 0 and d_idx == 0:
                    continue  # deja afișat mai sus
                prefix = f"Contor {c_idx + 1} cadran {d_idx + 1}"
                attrs[f"{prefix} index"] = cdr.get("Index", "Necunoscut")
                attrs[f"{prefix} tip"] = cdr.get(
                    "MeterReadingType", "Necunoscut"
                )
                attrs[f"{prefix} dată"] = format_date_ro(
                    cdr.get("ReadingDate", "")
                )

        attrs["attribution"] = ATTRIBUTION
        return attrs


# ── 4. IstoricCitiriSensor (7.1) ────────────────

class IstoricCitiriSensor(MyElectricaEntity):
    """Istoric citiri contor (7.1 — readings)."""

    _attr_icon = "mdi:history"
    _attr_translation_key = "istoric_citiri"

    def __init__(self, coordinator, config_entry, ctx: NlcContext) -> None:
        super().__init__(coordinator, config_entry, ctx)
        self._attr_name = "Istoric citiri"
        self._attr_unique_id = f"{DOMAIN}_{ctx.nlc}_istoric_citiri"
        self._custom_entity_id = f"sensor.{DOMAIN}_{ctx.nlc}_istoric_citiri"

    def _get_readings(self) -> list[dict]:
        response = self._get_nlc_response("readings")
        if isinstance(response, list):
            return response
        return []

    def _get_recent_readings(self) -> list[dict]:
        """Cele mai recente 12 citiri (ordine cronologică inversă)."""
        return list(reversed(self._get_readings()))[:12]

    @property
    def native_value(self):
        return len(self._get_recent_readings())

    @property
    def extra_state_attributes(self):
        recent = self._get_recent_readings()
        if not recent:
            return {"attribution": ATTRIBUTION}

        attrs = {}
        for reading in recent:
            date = format_date_ro(reading.get("ReadingDate", ""))
            index_val = reading.get("Index", "Necunoscut")
            read_type_raw = reading.get("MeterReadingType", "")

            # Traducere tip citire
            if "client" in read_type_raw.lower():
                tip = "autocitit"
            elif "comp" in read_type_raw.lower():
                tip = "citit distribuitor"
            else:
                tip = read_type_raw.lower() if read_type_raw else "necunoscut"

            label = f"Index ({tip}) {date}"
            attrs[label] = index_val

        # Date contor din prima citire disponibilă
        if recent:
            serie = recent[0].get("SerieContor", "Necunoscut")
            install_date = recent[0].get("InstallationDate", "")
            attrs["Serie contor"] = serie
            attrs["Data instalării"] = format_date_ro(install_date)

        attrs["Total citiri"] = str(len(recent))
        attrs["attribution"] = ATTRIBUTION
        return attrs


# ── 5. CitirePermisaSensor (6.1 — meter-list PAC) ─

class CitirePermisaSensor(MyElectricaEntity):
    """Citire permisă — indică dacă autocitirea este activă (PAC din meter-list)."""

    _attr_translation_key = "citire_permisa"

    def __init__(self, coordinator, config_entry, ctx: NlcContext) -> None:
        super().__init__(coordinator, config_entry, ctx)
        self._attr_name = "Citire permisă"
        self._attr_unique_id = f"{DOMAIN}_{ctx.nlc}_citire_permisa"
        self._custom_entity_id = f"sensor.{DOMAIN}_{ctx.nlc}_citire_permisa"

    def _get_pac_data(self) -> dict | None:
        """Extrage datele PAC din meter-list (nivelul rădăcină al response-ului)."""
        return self._get_nlc_response("meter_list")

    @property
    def icon(self):
        """Returnează iconița în funcție de starea senzorului."""
        value = self.native_value
        if value == "Da":
            return "mdi:clock-check-outline"
        if value == "Nu":
            return "mdi:clock-alert-outline"
        return "mdi:cog-stop-outline"

    @property
    def native_value(self):
        response = self._get_pac_data()
        if not response:
            return "Nu"
        return "Da" if response.get("PACIndicator") == "1" else "Nu"

    @property
    def extra_state_attributes(self):
        response = self._get_pac_data()
        if not response:
            return {"attribution": ATTRIBUTION}

        start_pac = response.get("StartDatePAC", "")
        end_pac = response.get("EndDatePAC", "")

        attrs = {}
        if start_pac:
            attrs["Început perioadă"] = format_date_ro(start_pac)
        if end_pac:
            attrs["Sfârșit perioadă"] = format_date_ro(end_pac)

        attrs["attribution"] = ATTRIBUTION
        return attrs


# ── 6. ConventieConsumSensor (8.1) ──────────────

class ConventieConsumSensor(MyElectricaEntity):
    """Convenție consum (8.1)."""

    _attr_icon = "mdi:calendar-clock"
    _attr_translation_key = "conventie_consum"

    def __init__(self, coordinator, config_entry, ctx: NlcContext) -> None:
        super().__init__(coordinator, config_entry, ctx)
        self._attr_name = "Convenție consum"
        self._attr_unique_id = f"{DOMAIN}_{ctx.nlc}_conventie_consum"
        self._custom_entity_id = f"sensor.{DOMAIN}_{ctx.nlc}_conventie_consum"

    def _get_convention(self) -> list[dict]:
        response = self._get_nlc_response("convention")
        if isinstance(response, list):
            return response
        return []

    @property
    def native_value(self):
        """Total kWh convenție (suma lunilor nenule)."""
        items = self._get_convention()
        if not items:
            return 0
        total = sum(safe_float(item.get("Quantity")) for item in items)
        return int(total) if total == int(total) else total

    @property
    def extra_state_attributes(self):
        items = self._get_convention()
        if not items:
            return {"attribution": ATTRIBUTION}

        attrs = {}
        for item in items:
            month_raw = item.get("Month", "")
            quantity = item.get("Quantity", "0")

            # Lunar poate fi numeric (01-12) sau text (Ianuarie)
            if month_raw.isdigit():
                month_name = MONTHS_NUM_RO.get(
                    month_raw.zfill(2), month_raw
                )
            else:
                month_name = month_raw.lower()

            attrs[f"Luna {month_name}"] = f"{quantity} kWh"

        attrs["attribution"] = ATTRIBUTION
        return attrs


# ── 6. ArhivaFacturiSensor (4.1) ──────────────────────

class ArhivaFacturiSensor(MyElectricaEntity):
    """Arhivă facturi per cod client (4.1), filtrate pe ContractAccount al NLC-ului."""

    _attr_icon = "mdi:file-document-multiple-outline"
    _attr_translation_key = "arhivafacturi"

    def __init__(self, coordinator, config_entry, ctx: NlcContext) -> None:
        super().__init__(coordinator, config_entry, ctx)
        self._attr_name = "Arhivă facturi"
        self._attr_unique_id = f"{DOMAIN}_{ctx.nlc}_arhivafacturi"
        self._custom_entity_id = f"sensor.{DOMAIN}_{ctx.nlc}_arhivafacturi"

    def _get_invoices(self) -> list[dict]:
        """Facturi filtrate pe ContractAccount al acestui NLC."""
        response = self._get_client_response("invoices")
        if not isinstance(response, list):
            return []
        ca = self._ctx.contract_account
        if not ca:
            return response
        return [f for f in response if f.get("ContractAccount") == ca]

    def _get_recent_invoices(self) -> list[dict]:
        """Cele mai recente 12 facturi (ordine cronologică inversă)."""
        return list(reversed(self._get_invoices()))[:12]

    @property
    def native_value(self):
        return len(self._get_recent_invoices())

    @property
    def extra_state_attributes(self):
        recent = self._get_recent_invoices()
        if not recent:
            return {"attribution": ATTRIBUTION}

        attrs = {}
        total = 0.0

        for idx, inv in enumerate(recent, start=1):
            date = format_date_ro(inv.get("IssueDate", ""))
            amount = safe_float(inv.get("TotalAmount"))
            total += amount

            label = f"Emisă pe {date}"
            value = f"{format_ron(amount)} lei"

            attrs[label] = value

        attrs["Total facturi"] = str(len(recent))
        attrs["Total facturat"] = f"{format_ron(total)} lei"
        attrs["attribution"] = ATTRIBUTION
        return attrs


# ── 7. FacturaRestantaSensor (4.1 filtrat) ──────

class FacturaRestantaSensor(MyElectricaEntity):
    """Facturi restante (din 4.1, filtrate pe neachitate)."""

    _attr_icon = "mdi:file-document-alert-outline"
    _attr_translation_key = "factura_restanta"

    def __init__(self, coordinator, config_entry, ctx: NlcContext) -> None:
        super().__init__(coordinator, config_entry, ctx)
        self._attr_name = "Factură restantă"
        self._attr_unique_id = f"{DOMAIN}_{ctx.nlc}_factura_restanta"
        self._custom_entity_id = f"sensor.{DOMAIN}_{ctx.nlc}_factura_restanta"

    def _facturi_neachitate(self) -> list[dict]:
        """Facturi neachitate pentru ContractAccount-ul acestui NLC."""
        response = self._get_client_response("invoices")
        if not isinstance(response, list):
            return []
        ca = self._ctx.contract_account
        result = []
        for f in response:
            if ca and f.get("ContractAccount") != ca:
                continue
            status = (f.get("InvoiceStatus") or "").lower()
            if status in ("neachitat", "neachitata", "neplătit"):
                unpaid = safe_float(f.get("UnpaidValue"))
                if unpaid > 0:
                    result.append(f)
        return result

    @property
    def native_value(self):
        """Există factură restantă? Da/Nu."""
        neachitate = self._facturi_neachitate()
        return "Da" if neachitate else "Nu"

    @property
    def extra_state_attributes(self):
        """Detalii facturi neachitate și total."""
        neachitate = self._facturi_neachitate()
        today = dt_util.now().date()
        attrs = {}

        total = sum(safe_float(f.get("UnpaidValue")) for f in neachitate)

        if not neachitate:
            attrs["Total neachitat"] = "0,00 lei"
        else:
            for idx, factura in enumerate(neachitate, start=1):
                unpaid = safe_float(factura.get("UnpaidValue"))

                # Luna din IssueDate
                issue_raw = factura.get("IssueDate", "")
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
                    days_until = (parsed_due.date() - today).days

                    if days_until < 0:
                        unit = "zi" if abs(days_until) == 1 else "zile"
                        msg = (
                            f"{format_ron(unpaid)} lei — termen depășit cu "
                            f"{abs(days_until)} {unit}"
                        )
                    elif days_until == 0:
                        msg = f"{format_ron(unpaid)} lei — scadentă astăzi"
                    else:
                        unit = "zi" if days_until == 1 else "zile"
                        msg = (
                            f"{format_ron(unpaid)} lei — scadentă în "
                            f"{days_until} {unit}"
                        )
                except (ValueError, TypeError):
                    msg = f"{format_ron(unpaid)} lei — scadență necunoscută"

                attrs[f"Restanță luna {month_name} (#{idx})"] = msg

            attrs["Total neachitat"] = f"{format_ron(total)} lei"

        attrs["attribution"] = ATTRIBUTION
        return attrs


# ── 8. ArhivaPlatiSensor (5.1) ────────────────────────

class ArhivaPlatiSensor(MyElectricaEntity):
    """
    Arhivă plăți (5.1 — client-code-payments), filtrate per NLC.

    API-ul returnează plățile per cod client.  Filtrăm per NLC
    corelând FiscalNumber / InvoiceID din plăți cu cele din facturile
    care aparțin ContractAccount-ului acestui NLC.
    """

    _attr_icon = "mdi:cash-check"
    _attr_translation_key = "arhiva_plati"

    def __init__(self, coordinator, config_entry, ctx: NlcContext) -> None:
        super().__init__(coordinator, config_entry, ctx)
        self._attr_name = "Arhivă plăți"
        self._attr_unique_id = f"{DOMAIN}_{ctx.nlc}_arhivaplati"
        self._custom_entity_id = f"sensor.{DOMAIN}_{ctx.nlc}_arhivaplati"

    def _get_nlc_invoice_keys(self) -> set[str]:
        """
        Colectează FiscalNumber + InvoiceID din facturile
        care aparțin ContractAccount-ului acestui NLC.
        Le folosim pentru a filtra plățile.
        """
        keys: set[str] = set()
        response = self._get_client_response("invoices")
        if not isinstance(response, list):
            return keys

        ca = self._ctx.contract_account
        for inv in response:
            if ca and inv.get("ContractAccount") != ca:
                continue
            fiscal = inv.get("FiscalNumber", "")
            inv_id = inv.get("InvoiceID", "")
            if fiscal:
                keys.add(fiscal)
            if inv_id:
                keys.add(inv_id)

        return keys

    def _get_payments(self) -> list[dict]:
        """Plăți filtrate per NLC (prin FiscalNumber/InvoiceID din facturi)."""
        response = self._get_client_response("payments")
        if not isinstance(response, list):
            return []

        invoice_keys = self._get_nlc_invoice_keys()
        if not invoice_keys:
            # Dacă nu avem facturi pentru acest NLC, nu returnăm plăți
            return []

        filtered = []
        for pay in response:
            fiscal = pay.get("FiscalNumber", "")
            inv_id = pay.get("InvoiceID", "")
            if fiscal in invoice_keys or inv_id in invoice_keys:
                filtered.append(pay)

        return filtered

    def _get_recent_payments(self) -> list[dict]:
        """Cele mai recente 12 plăți (ordine cronologică inversă)."""
        return list(reversed(self._get_payments()))[:12]

    @property
    def native_value(self):
        return len(self._get_recent_payments())

    @property
    def extra_state_attributes(self):
        recent = self._get_recent_payments()
        if not recent:
            return {
                "Total plătit": "0,00 lei",
                "attribution": ATTRIBUTION,
            }

        attrs = {}
        total = 0.0

        for idx, pay in enumerate(recent, start=1):
            date = format_date_ro(pay.get("PaymentDate", ""))
            amount = safe_float(pay.get("PaidValue"))
            total += amount

            label = f"Plătită pe {date}"
            value = f"{format_ron(amount)} lei"

            attrs[label] = value

        attrs["Total plăți"] = str(len(recent))
        attrs["Total plătit"] = f"{format_ron(total)} lei"
        attrs["attribution"] = ATTRIBUTION
        return attrs
