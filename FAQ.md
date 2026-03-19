# Întrebări frecvente (FAQ) — MyElectrica România

---

## Generale

### Ce este MyElectrica?

MyElectrica este portalul online al Electrica Furnizare, unde clienții pot vedea datele contractuale, facturile, plățile, indexul contorului și pot trimite autocitiri. Această integrare importă aceste date în Home Assistant prin API-ul MyElectrica.

### De ce aș folosi această integrare?

Dacă vrei să monitorizezi din Home Assistant: starea contractului, facturile restante, istoricul plăților, indexul contorului, sau să trimiți autocitirea fără a intra pe site. Poți crea automatizări care te notifică la facturi restante sau când se deschide perioada de autocitire.

### E gratuită?

Da. Integrarea este open-source, iar datele vin din contul tău MyElectrica (nu necesită abonament suplimentar).

### Funcționează și pentru gaz?

Integrarea suportă orice tip de serviciu returnat de API (Electricitate, Gaz). Butonul de trimitere index detectează automat tipul de produs și citește din `input_number.energy_meter_reading` (electricitate) sau `input_number.gas_meter_reading` (gaz).

---

## Configurare

### Ce date trebuie să introduc?

Trei câmpuri:

| Câmp | Descriere | Implicit |
|------|-----------|----------|
| Email | Adresa de email a contului MyElectrica | — |
| Parolă | Parola contului MyElectrica | — |
| Interval actualizare | Secunde între interogările API | 3600 (1 oră) |

### Ce sunt NLC-urile?

NLC (Număr Loc de Consum) este identificatorul unic al fiecărei locații de consum asociate contului tău. Fiecare NLC corespunde unui contor/adresă. Un cont poate avea mai multe NLC-uri (mai multe locuințe, mai multe contoare).

### Pot selecta doar anumite NLC-uri?

Da. După autentificare, vezi lista completă cu adrese normalizate:

```
Furcilor 90A, ap. 17, Alba Iulia → NLC: 7001250422 (Electricitate)
Ștefan cel Mare 20, Timișoara → NLC: 7003271722 (Electricitate)
```

Selectezi individual sau bifezi „Monitorizează toate locurile de consum".

### Pot schimba setările fără a reinstala?

Da. **Settings** → **Devices & Services** → **MyElectrica** → **Configure** → modifică → **Submit**. Integrarea se reîncarcă automat. Detalii în [SETUP.md](SETUP.md).

### Ce interval de actualizare recomandați?

Implicit: **3600 secunde** (1 oră). Datele MyElectrica nu se schimbă frecvent (facturile se emit lunar, indexul se actualizează la citire). Nu se recomandă valori sub 600 secunde pentru a evita blocarea contului de către API.

---

## Senzori

### Câți senzori se creează?

**9 senzori + 1 buton** per NLC selectat. Cu 3 NLC-uri = 30 entități total.

| Nr | Senzor | Valoare principală |
|----|--------|-------------------|
| 1 | Date contract | Status contract |
| 2 | Date client | Nume client |
| 3 | Index curent | Ultimul index validat |
| 4 | Istoric citiri | Număr citiri (max 12) |
| 5 | Citire permisă | Da / Nu |
| 6 | Convenție consum | Total kWh |
| 7 | Arhivă facturi | Număr facturi (max 12) |
| 8 | Factură restantă | Da / Nu |
| 9 | Arhivă plăți | Număr plăți (max 12) |
| — | Trimite index (buton) | — |

### De ce văd doar 12 facturi/plăți/citiri?

Senzorii afișează cele mai recente 12 înregistrări, în ordine cronologică inversă. Totalurile (native_value, Total facturi/plăți, sume) reflectă exclusiv cele 12 afișate, nu toate datele din API.

### De ce nu văd facturile din anul curent?

Integrarea solicită facturi din ultimii 2 ani (730 zile) și le afișează în ordine cronologică inversă. Dacă facturile din anul curent nu apar:

1. Verifică în log dacă API-ul le returnează (activează debug — vezi [DEBUG.md](DEBUG.md))
2. Contul poate avea facturile asociate unui alt ContractAccount decât NLC-ul selectat

### Ce înseamnă „autocitit" și „citit distribuitor"?

În senzorul Istoric citiri, tipul de citire este tradus automat:

| API (MeterReadingType) | Afișat |
|------------------------|--------|
| „Citire contor de către client - SAP" | autocitit |
| „Citire contor de comp.utilități - SAP" | citit distribuitor |

### De ce iconița senzorului „Citire permisă" se schimbă?

Senzorul are iconiță dinamică:

| Stare | Iconiță |
|-------|---------|
| Da (autocitire activă) | `mdi:clock-check-outline` |
| Nu (autocitire inactivă) | `mdi:clock-alert-outline` |
| Nedeterminat | `mdi:cog-stop-outline` |

### Cum funcționează senzorul „Factură restantă"?

Filtrează facturile neachitate pe ContractAccount-ul NLC-ului curent. Pentru fiecare factură restantă, calculează automat zilele până la/de la scadență:

- `termen depășit cu 15 zile` — scadența a trecut cu 15 zile
- `scadentă astăzi` — azi e ultima zi
- `scadentă în 3 zile` — mai ai 3 zile

---

## Butonul Trimite index

### Cum funcționează?

Butonul citește valoarea din `input_number`, detectează automat seria contorului și codul registru din datele existente (meter_list), și trimite indexul către API-ul MyElectrica.

### Ce `input_number` trebuie să creez?

Definește manual în `configuration.yaml`:

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

Integrarea detectează automat ce `input_number` să folosească pe baza tipului de produs (Electricitate → `energy_meter_reading`, Gaz → `gas_meter_reading`).

### De ce nu funcționează butonul?

Cauze posibile:

1. **`input_number` nu există** — trebuie creat manual (vezi mai sus)
2. **`input_number` are valoare invalidă** — valoarea trebuie să fie un număr valid
3. **Perioada de autocitire nu e activă** — verifică senzorul „Citire permisă"
4. **Eroare API** — verifică logurile pentru mesaje `[MyElectrica] Eroare la trimitere index`

---

## Adrese și județe

### De ce adresele apar cu majuscule corecte?

API-ul MyElectrica returnează adresele în ALL CAPS (`STEFAN CEL MARE`, `ALBA IULIA`). Integrarea aplică `normalize_title()` care transformă textul în Title Case (`Stefan Cel Mare`, `Alba Iulia`).

**Limitare**: funcția nu adaugă diacritice lipsă. Dacă API-ul returnează `STEFAN CEL MARE` (fără diacritice), rezultatul va fi `Stefan Cel Mare`, nu `Ștefan cel Mare`.

### De ce apare „Alba" în loc de „AB" la județ?

Integrarea conține un mapping complet al celor 41 de județe + București. Codurile scurte sunt convertite automat:

| Cod | Județ |
|-----|-------|
| AB | Alba |
| BV | Brașov |
| CJ | Cluj |
| B | București |
| ... | (toate 42 în `helper.py`) |

### De ce apare „Persoană fizică" în loc de „PF"?

Similar, tipurile de client sunt mapate automat: PF → Persoană fizică, PJ → Persoană juridică, SRL → Societate cu răspundere limitată etc.

---

## Troubleshooting

### Senzorii afișează „Necunoscut"

Cauze posibile:

1. **API-ul nu returnează date** — activează debug logging (vezi [DEBUG.md](DEBUG.md)) și verifică răspunsurile API
2. **NLC dezactivat** — contractul poate fi inactiv sau NLC-ul nu mai are date
3. **Eroare de rețea** — verifică conexiunea HA la internet
4. **Prima actualizare** — la prima pornire, datele pot lipsi până la primul ciclu complet

### Autentificare eșuată

1. Verifică email-ul și parola pe [myelectrica.ro](https://myelectrica.ro)
2. Contul poate fi blocat temporar după mai multe încercări eșuate
3. Verifică logurile: `[MyElectrica] Login HTTP 4xx` sau `Login respins de API`

### Prețurile/sumele arată incorect

Integrarea formatează în format românesc: `1.234,56 lei` (punct = mii, virgulă = zecimale). Dacă vezi numere neformatate, verifică versiunea integrării.

### Cum activez debug logging?

Adaugă în `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.myelectrica: debug
```

Restartează HA. Vezi [DEBUG.md](DEBUG.md) pentru detalii complete.

---

## Actualizări

### Cum actualizez integrarea?

**HACS**: HACS te notifică automat când e o versiune nouă. Click **Update**.

**Manual**: descarcă noua versiune, suprascrie fișierele din `custom_components/myelectrica/`, restartează HA.

### Se pierd setările la actualizare?

Nu. Setările sunt stocate în baza de date HA, nu în fișiere. Actualizarea suprascrie doar codul.

### Trebuie să șterg și readaug integrarea?

De regulă nu. Dacă o versiune nouă necesită asta (ex: schimbare majoră de arhitectură), va fi menționat explicit în release notes.
