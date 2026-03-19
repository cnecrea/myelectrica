# Ghid de instalare și configurare — MyElectrica România

Acest ghid acoperă fiecare pas al instalării și configurării integrării MyElectrica România pentru Home Assistant. Dacă ceva nu e clar, deschide un [issue pe GitHub](https://github.com/cnecrea/myelectrica/issues).

---

## Cerințe preliminare

Înainte de a începe, asigură-te că ai:

- **Home Assistant** versiunea 2024.x sau mai nouă (necesită pattern `entry.runtime_data`)
- **Cont MyElectrica România** activ — cu email și parolă funcționale pe [myelectrica.ro](https://myelectrica.ro)
- **HACS** instalat (opțional, dar recomandat) — [instrucțiuni HACS](https://hacs.xyz/docs/setup/download)

---

## Metoda 1: Instalare prin HACS (recomandat)

### Pasul 1 — Adaugă repository-ul custom

1. Deschide Home Assistant → sidebar → **HACS**
2. Click pe cele 3 puncte (⋮) din colțul dreapta sus
3. Selectează **Custom repositories**
4. În câmpul „Repository" scrie: `https://github.com/cnecrea/myelectrica`
5. În câmpul „Category" selectează: **Integration**
6. Click **Add**

### Pasul 2 — Instalează integrarea

1. În HACS, caută „**MyElectrica**" sau „**MyElectrica România**"
2. Click pe rezultat → **Download** (sau **Install**)
3. Confirmă instalarea

### Pasul 3 — Restartează Home Assistant

1. **Settings** → **System** → **Restart**
2. Sau din terminal: `ha core restart`

**Așteptare**: restartul durează 1–3 minute. Nu continua până nu se încarcă complet dashboard-ul.

---

## Metoda 2: Instalare manuală

### Pasul 1 — Descarcă fișierele

1. Mergi la [Releases](https://github.com/cnecrea/myelectrica/releases) pe GitHub
2. Descarcă ultima versiune (zip sau tar.gz)
3. Dezarhivează

### Pasul 2 — Copiază folderul

Copiază întregul folder `custom_components/myelectrica/` în directorul de configurare al Home Assistant:

```
config/
└── custom_components/
    └── myelectrica/
        ├── __init__.py
        ├── api.py
        ├── button.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── helper.py
        ├── manifest.json
        ├── sensor.py
        ├── strings.json
        └── translations/
            └── ro.json
```

**Atenție**: folderul trebuie să fie exact `myelectrica` (litere mici, fără spații).

Dacă folderul `custom_components` nu există, creează-l.

### Pasul 3 — Restartează Home Assistant

La fel ca la Metoda 1.

---

## Configurare inițială

### Pasul 1 — Adaugă integrarea

1. **Settings** → **Devices & Services**
2. Click **+ Add Integration** (butonul albastru, dreapta jos)
3. Caută „**MyElectrica**" — va apărea „MyElectrica România"
4. Click pe ea

### Pasul 2 — Completează formularul de autentificare

Vei vedea un formular cu 3 câmpuri:

#### Câmp 1: Email

- **Ce face**: adresa de email a contului MyElectrica
- **Format**: email valid (ex: `user@example.com`)
- **Observație**: este și identificatorul unic al integrării — nu poți adăuga același email de două ori

#### Câmp 2: Parolă

- **Ce face**: parola contului MyElectrica
- **Observație**: stocată criptat în baza de date HA

#### Câmp 3: Interval actualizare (secunde)

- **Ce face**: la câte secunde se reîmprospătează datele de la API
- **Implicit**: `3600` (1 oră)
- **Recomandare**: lasă pe 3600. Datele MyElectrica nu se schimbă frecvent. Nu se recomandă valori sub 600 secunde.

### Pasul 3 — Selectează locurile de consum (NLC)

După autentificare reușită, ierarhia contului este descoperită automat. Vei vedea lista tuturor NLC-urilor asociate contului, cu adrese complete normalizate:

```
Furcilor 90A, ap. 17, Alba Iulia → NLC: 7002020110 (Electricitate)
Ștefan cel Mare 20, Timișoara → NLC: 7001236723 (Electricitate)
Henri Coandă 26, Alba Iulia → NLC: 7001224189 (Electricitate)
```

Ai două opțiuni:
- **Selectare individuală** — bifezi doar NLC-urile dorite
- **Monitorizează toate** — bifezi „Monitorizează toate locurile de consum"

**Observație**: dacă nu selectezi niciun NLC și nu bifezi „toate", vei primi eroare: „Trebuie să selectezi cel puțin un loc de consum sau să activezi opțiunea pentru toate."

### Pasul 4 — Confirmă

Click **Submit**. Integrarea se instalează și creează:
- 1 device per NLC selectat
- 9 senzori + 1 buton per device

Prima actualizare durează câteva secunde (interogare API pentru toate endpoint-urile).

---

## Reconfigurare (fără reinstalare)

Toate setările pot fi modificate din UI, fără a șterge și readăuga integrarea.

1. **Settings** → **Devices & Services**
2. Găsește **MyElectrica** → click pe **Configure** (⚙️)
3. Completează din nou email, parolă, interval
4. La pasul următor, poți modifica selecția NLC-urilor
5. Click **Submit**
6. Integrarea se reîncarcă automat (nu e nevoie de restart)

**Observație**: la reconfigurare, ierarhia contului este redescoperită. Dacă au apărut NLC-uri noi (nouă locuință, nou contor), le vei vedea în listă.

---

## Pregătire pentru butonul Trimite index

Butonul de trimitere autocitire necesită un `input_number` definit manual. Adaugă în `configuration.yaml`:

```yaml
input_number:
  energy_meter_reading:
    name: Index contor electricitate
    min: 0
    max: 999999
    step: 1
    mode: box

  gas_meter_reading:
    name: Index contor gaz
    min: 0
    max: 999999
    step: 1
    mode: box
```

Restartează HA după adăugare. Integrarea detectează automat ce `input_number` să folosească pe baza tipului de produs al contractului:

| Produs | input_number |
|--------|-------------|
| Electricitate / Energie electrică | `input_number.energy_meter_reading` |
| Gaz / Gaze naturale | `input_number.gas_meter_reading` |

---

## Verificare după instalare

### Verifică că device-urile există

1. **Settings** → **Devices & Services** → click pe **MyElectrica**
2. Ar trebui să vezi un device per NLC selectat (ex: „MyElectrica 7002020110")

### Verifică senzorii

1. **Developer Tools** → **States**
2. Filtrează după `myelectrica`
3. Ar trebui să vezi entitățile cu valori (ex: `activ`, `Da`, `4993`, `12`)

### Verifică logurile (dacă ceva nu merge)

1. **Settings** → **System** → **Logs**
2. Caută mesaje cu `[MyElectrica]`
3. Pentru detalii, activează debug logging — vezi [DEBUG.md](DEBUG.md)

---

## Dezinstalare

### Prin HACS

1. HACS → găsește „MyElectrica România" → **Remove**
2. Restartează Home Assistant

### Manual

1. **Settings** → **Devices & Services** → MyElectrica → **Delete**
2. Șterge folderul `config/custom_components/myelectrica/`
3. Restartează Home Assistant
