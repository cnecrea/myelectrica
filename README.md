# MyElectrica România — Integrare Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/cnecrea/myelectrica)](https://github.com/cnecrea/myelectrica/releases)
![Total descărcări pentru toate versiunile](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/cnecrea/myelectrica/main/statistici/shields/descarcari.json)
![Descărcări pentru ultima versiune](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/cnecrea/myelectrica/main/statistici/shields/ultima_release.json)


Integrare custom pentru [Home Assistant](https://www.home-assistant.io/) care monitorizează datele contractuale, consumul și facturile prin API-ul [MyElectrica România](https://myelectrica.ro/).

Oferă senzori dedicați per loc de consum (NLC) pentru contract, index curent, facturi, plăți, istoric citiri, convenție consum, autocitire permisă, și un buton de trimitere autocitire.

---

## Ce face integrarea

- **Descoperire automată** a ierarhiei de conturi: Cont → Coduri client → Contracte → NLC-uri (locuri de consum)
- **Selectare granulară** a NLC-urilor pe care vrei să le monitorizezi
- **9 senzori + 1 buton** per NLC selectat — fiecare NLC devine un device dedicat
- **Facturi și plăți** — ultimele 12, în ordine cronologică inversă, cu sume în format românesc
- **Istoric citiri** — ultimele 12 citiri cu tip (autocitit / citit distribuitor)
- **Factură restantă** — detectare automată cu calcul zile scadență
- **Autocitire** — senzor care indică dacă perioada de autocitire e activă + buton de trimitere index
- **Adrese normalizate** — formatare corectă din ALL CAPS (API) în format românesc (`Furcilor 90A, ap. 17, 510128 Alba Iulia, Alba`)
- **Mapping județe** — coduri scurte (AB, BV, CJ) convertite automat în denumiri complete (Alba, Brașov, Cluj)
- **Reconfigurare fără reinstalare** — OptionsFlow pentru modificarea credențialelor și selecției NLC

---

## Sursa datelor

Datele vin prin API-ul MyElectrica România (`api.myelectrica.ro`), care expune endpoint-uri REST pentru:

| Endpoint | Descriere |
|----------|-----------|
| 3.1 | Ierarhie date cont (coduri client → contracte → NLC) |
| 3.2 | Date client detaliate |
| 3.3 | Detalii contract per NLC |
| 4.1 | Facturi per cod client (ultimii 2 ani) |
| 5.1 | Istoric plăți per cod client (ultimii 2 ani) |
| 6.1 | Lista contoare + cadrane per NLC |
| 6.2 | Trimitere autocitire (set-index) |
| 7.1 | Istoric citiri per NLC |
| 8.1 | Convenție consum per NLC |

Autentificarea se face cu email + parolă. Token-ul expirat (401) este reînnoit automat.

---

## Instalare

### HACS (recomandat)

1. Deschide HACS în Home Assistant
2. Click pe cele 3 puncte (⋮) din colțul dreapta sus → **Custom repositories**
3. Adaugă URL-ul: `https://github.com/cnecrea/myelectrica`
4. Categorie: **Integration**
5. Click **Add** → găsește „MyElectrica România" → **Install**
6. Restartează Home Assistant

### Manual

1. Copiază folderul `custom_components/myelectrica/` în directorul `config/custom_components/` din Home Assistant
2. Restartează Home Assistant

---

## Configurare

### Pasul 1 — Adaugă integrarea

1. **Settings** → **Devices & Services** → **Add Integration**
2. Caută „**MyElectrica**" sau „**MyElectrica România**"
3. Completează formularul:

| Câmp | Descriere | Implicit |
|------|-----------|----------|
| **Email** | Adresa de email a contului MyElectrica | — |
| **Parolă** | Parola contului MyElectrica | — |
| **Interval actualizare** | Secunde între interogările API | `3600` (1 oră) |

### Pasul 2 — Selectează NLC-urile

După autentificare, ierarhia contului este descoperită automat. Fiecare NLC apare cu adresa completă normalizată:

```
Furcilor 90A, ap. 17, Alba Iulia → NLC: 7002020110 (Electricitate)
Ștefan cel Mare 20, Timișoara → NLC: 7001236723 (Electricitate)
```

Selectezi individual sau bifezi „Monitorizează toate locurile de consum".

### Pasul 3 — Reconfigurare (opțional)

Toate setările pot fi modificate după instalare, fără a șterge integrarea:

1. **Settings** → **Devices & Services** → click pe integrarea **MyElectrica**
2. Click pe **Configure** (⚙️)
3. Modifică setările dorite → **Submit**
4. Integrarea se reîncarcă automat cu noile setări

Detalii complete în [SETUP.md](SETUP.md).

---

## Entități create

Integrarea creează un **device** per NLC selectat. Sub fiecare device se creează **9 senzori + 1 buton**.

Cu 3 NLC-uri selectate = 3 device-uri × 10 entități = **30 entități** total.

### Senzori

| Entitate | Descriere | Valoare principală |
|----------|-----------|-------------------|
| `Date contract` | Detalii contract (3.3) | Status contract |
| `Date client` | Date client (3.2) | Nume client |
| `Index curent` | Index contor (6.1) | Ultimul index validat |
| `Istoric citiri` | Ultimele 12 citiri (7.1) | Număr citiri |
| `Citire permisă` | Autocitire activă? (6.1 PAC) | Da / Nu |
| `Convenție consum` | Consum lunar convenit (8.1) | Total kWh |
| `Arhivă facturi` | Ultimele 12 facturi (4.1) | Număr facturi |
| `Factură restantă` | Facturi neachitate (4.1 filtrat) | Da / Nu |
| `Arhivă plăți` | Ultimele 12 plăți (5.1) | Număr plăți |

### Buton

| Entitate | Descriere |
|----------|-----------|
| `Trimite index` | Trimite autocitirea contorului către API (6.2) |

---

### Senzor: Date contract

**Valoare principală**: status contract (activ/inactiv)

**Atribute**:
```yaml
NLC: "7002020110"
Cod client: "9004018471"
Cont contract: "..."
Tip contract: "nedeterminat"
Produs: "Energie electrică"
Dată contract: "5 ianuarie 2020"
Status: "activ"
Metodă estimare: "..."
Autocitire disponibilă: "Da"
Periodicitate citiri: "lunar"
Grupă regională: "..."
Adresă consum: "Furcilor 90A, ap. 17, 510128 Alba Iulia, Alba"
Tip serviciu: "Electricitate"
```

### Senzor: Date client

**Valoare principală**: numele clientului

**Atribute**:
```yaml
Cod client: "9004018471"
Tip client: "Persoană fizică"
Adresă: "Furcilor 90A, ap. 17, 510128 Alba Iulia, Alba"
Județ: "Alba"
Telefon: "07..."
```

### Senzor: Index curent

**Valoare principală**: ultimul index validat

**Atribute**:
```yaml
Serie contor: "ABC123456"
Data citirii: "20 februarie 2026"
Index validat: "4993"
Tip citire: "Citire contor de către client - SAP"
Cod registru: "001"
Descriere registru: "..."
```

Dacă există date PAC (perioadă autocitire), se adaugă: Index PAC, Data citire PAC, Perioadă autocitire început/sfârșit.

### Senzor: Istoric citiri

**Valoare principală**: numărul de citiri afișate (max 12)

Fiecare citire apare ca atribut cu formatul:

```yaml
Index (autocitit) 20 februarie 2026: "4993"
Index (citit distribuitor) 15 ianuarie 2026: "4850"
Serie contor: "ABC123456"
Data instalării: "10 martie 2019"
Total citiri: "12"
```

Tipurile de citire sunt traduse automat: „Citire contor de către client" → `autocitit`, „Citire contor de comp.utilități" → `citit distribuitor`.

### Senzor: Citire permisă

**Valoare principală**: Da / Nu

**Iconiță dinamică**: `clock-check-outline` (Da), `clock-alert-outline` (Nu), `cog-stop-outline` (nedeterminat)

**Atribute**: Început perioadă, Sfârșit perioadă (dacă sunt disponibile).

### Senzor: Convenție consum

**Valoare principală**: total kWh convenție (suma lunilor nenule)

**Atribute**: consum per lună (`Luna ianuarie: 150 kWh`, `Luna februarie: 120 kWh` etc.).

### Senzor: Arhivă facturi

**Valoare principală**: numărul de facturi afișate (max 12)

Fiecare factură apare ca atribut:

```yaml
Emisă pe 8 martie 2024: "125,50 lei"
Emisă pe 5 februarie 2024: "98,20 lei"
Total facturi: "12"
Total facturat: "1.450,30 lei"
```

Facturile sunt filtrate pe ContractAccount-ul NLC-ului curent. Se afișează cele mai recente 12, în ordine cronologică inversă. Totalurile reflectă exclusiv cele 12 afișate.

### Senzor: Factură restantă

**Valoare principală**: Da / Nu

**Atribute** (când există restanțe):

```yaml
Restanță luna martie (#1): "125,50 lei — termen depășit cu 15 zile"
Restanță luna februarie (#2): "98,20 lei — scadentă în 3 zile"
Total neachitat: "223,70 lei"
```

Calcul automat: termen depășit cu X zile / scadentă astăzi / scadentă în X zile.

### Senzor: Arhivă plăți

**Valoare principală**: numărul de plăți afișate (max 12)

Fiecare plată apare ca atribut:

```yaml
Plătită pe 8 martie 2024: "125,50 lei"
Plătită pe 5 februarie 2024: "98,20 lei"
Total plăți: "12"
Total plătit: "1.450,30 lei"
```

Plățile sunt corelate cu facturile NLC-ului curent prin FiscalNumber/InvoiceID.

### Buton: Trimite index

Trimite autocitirea contorului către API-ul MyElectrica (endpoint 6.2).

**Cerințe**:
- `input_number.energy_meter_reading` (electricitate) sau `input_number.gas_meter_reading` (gaz) — definit de utilizator
- Perioada de autocitire activă (senzorul „Citire permisă" = Da)

**Atribute**: NLC, Serie contor, Cod registru, Produs, Sursă index.

---

## Exemple de automatizări

### Notificare factură restantă

```yaml
automation:
  - alias: "Notificare factură restantă"
    trigger:
      - platform: state
        entity_id: sensor.myelectrica_7002020110_factura_restanta
        to: "Da"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Factură restantă MyElectrica"
          message: >
            Ai {{ state_attr('sensor.myelectrica_7002020110_factura_restanta', 'Total neachitat') }}
            de plătit.
```

### Notificare perioadă autocitire

```yaml
automation:
  - alias: "Perioadă autocitire deschisă"
    trigger:
      - platform: state
        entity_id: sensor.myelectrica_7002020110_citire_permisa
        to: "Da"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Autocitire disponibilă"
          message: "Poți trimite indexul contorului pentru NLC 7002020110."
```

### Card pentru Dashboard

```yaml
type: entities
title: MyElectrica — Furcilor 90A
entities:
  - entity: sensor.myelectrica_7002020110_date_contract
    name: Contract
  - entity: sensor.myelectrica_7002020110_index_curent
    name: Index curent
  - entity: sensor.myelectrica_7002020110_citire_permisa
    name: Citire permisă
  - entity: sensor.myelectrica_7002020110_factura_restanta
    name: Factură restantă
  - entity: sensor.myelectrica_7002020110_conventie_consum
    name: Convenție consum
```

---

## Structura fișierelor

```
custom_components/myelectrica/
├── __init__.py          # Setup/unload integrare (runtime_data pattern)
├── api.py               # Manager API — login, GET/POST cu retry pe 401
├── button.py            # Buton trimitere autocitire per NLC
├── config_flow.py       # ConfigFlow + OptionsFlow (autentificare, selecție NLC)
├── const.py             # Constante, URL-uri API, mapping luni
├── coordinator.py       # DataUpdateCoordinator — fetch centralizat per NLC
├── helper.py            # Funcții utilitare, mapping județe, formatare adrese
├── manifest.json        # Metadata integrare
├── sensor.py            # 9 clase senzor cu clasă de bază comună
├── strings.json         # Traduceri implicite
└── translations/
    └── ro.json          # Traduceri române
```

---

## Cerințe

- **Home Assistant** 2024.x sau mai nou (pattern `entry.runtime_data`)
- **HACS** (opțional, pentru instalare ușoară)
- **Cont MyElectrica România** activ cu email + parolă

Nu necesită dependențe externe (nu instalează pachete pip/npm).

---

## Limitări cunoscute

1. **O singură instanță per cont** — dacă încerci să adaugi același email de două ori, vei primi eroare „already configured".

2. **Ultimele 12 înregistrări** — senzorii Arhivă facturi, Arhivă plăți și Istoric citiri afișează cele mai recente 12 intrări. Totalurile reflectă exclusiv cele 12 afișate, nu toate datele din API.

3. **Facturi pe ultimii 2 ani** — API-ul este interogat cu interval de 730 zile. Facturile mai vechi nu sunt incluse.

4. **Trimitere index** — butonul necesită `input_number` definit manual de utilizator. Nu se creează automat.

5. **Normalizare adrese** — funcția `normalize_title` transformă ALL CAPS în Title Case prin `.lower().title()`. Nu adaugă diacritice lipsă dacă API-ul nu le furnizează.

---

## ☕ Susține dezvoltatorul

Dacă ți-a plăcut această integrare și vrei să sprijini munca depusă, **invită-mă la o cafea**! 🫶  
Nu costă nimic, iar contribuția ta ajută la dezvoltarea viitoare a proiectului. 🙌  

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Susține%20dezvoltatorul-orange?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/cnecrea)

Mulțumesc pentru sprijin și apreciez fiecare gest de susținere! 🤗

--- 

## 🧑‍💻 Contribuții

Contribuțiile sunt binevenite! Simte-te liber să trimiți un pull request sau să raportezi probleme [aici](https://github.com/cnecrea/myelectrica/issues).

---

## 🌟 Suport
Dacă îți place această integrare, oferă-i un ⭐ pe [GitHub](https://github.com/cnecrea/myelectrica/)! 😊


## Licență

[MIT](LICENSE)
