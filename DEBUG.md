# Ghid de debugging — MyElectrica România

Acest ghid explică cum activezi logarea detaliată, ce mesaje să cauți, și cum interpretezi fiecare situație.

---

## 1. Activează debug logging

Editează `configuration.yaml` și adaugă:

```yaml
logger:
  default: warning
  logs:
    custom_components.myelectrica: debug
```

Restartează Home Assistant (**Settings** → **System** → **Restart**).

Pentru a reduce zgomotul din loguri, poți adăuga:

```yaml
logger:
  default: warning
  logs:
    custom_components.myelectrica: debug
    homeassistant.const: critical
    homeassistant.loader: critical
    homeassistant.helpers.frame: critical
```

**Important**: dezactivează debug logging după ce ai rezolvat problema (setează `custom_components.myelectrica: info` sau șterge blocul). Logarea debug generează mult text și poate conține date personale.

---

## 2. Unde găsești logurile

### Din UI

**Settings** → **System** → **Logs** → filtrează după `MyElectrica`

### Din fișier

```bash
# Calea implicită
cat config/home-assistant.log | grep -i myelectrica

# Doar erorile
grep -E "(ERROR|WARNING).*MyElectrica" config/home-assistant.log

# Ultimele 100 linii
grep -i myelectrica config/home-assistant.log | tail -100
```

### Din terminal (Docker/HAOS)

```bash
# Docker
docker logs homeassistant 2>&1 | grep -i myelectrica

# Home Assistant OS (SSH add-on)
ha core logs | grep -i myelectrica
```

---

## 3. Ciclul normal de actualizare

La fiecare ciclu (implicit la fiecare oră), ar trebui să vezi în loguri o secvență ca aceasta:

```
[MyElectrica] Începe actualizarea datelor
[MyElectrica] Descoperite 2 coduri client, 6 NLC-uri (selectate: 3)
[MyElectrica] GET OK: .../contract-nlc-details/7001250222 — Received data: {...}
[MyElectrica] GET OK: .../meter-list/7001250222 — Received data: {...}
[MyElectrica] GET OK: .../readings/9001218422/7001250222 — Received data: {...}
[MyElectrica] GET OK: .../consumtion-convention/7001250222 — Received data: {...}
[MyElectrica] Actualizare completă
```

Apoi se repetă pentru fiecare NLC selectat.

**Dacă vezi „Actualizare completă", totul funcționează corect.**

---

## 4. Mesajele de la pornire

La prima pornire a integrării (sau după restart), ar trebui să vezi:

```
[MyElectrica] Setup entry_id=01ABC...
[MyElectrica] Login OK — token obținut
[MyElectrica] Se adaugă 27 senzori (entry_id=01ABC...)
[MyElectrica] Se adaugă 3 butoane (entry_id=01ABC...)
[MyElectrica] Setup complet pentru entry_id=01ABC...
```

Numerele depind de câte NLC-uri ai selectat: 3 NLC × 9 senzori = 27 senzori, 3 butoane.

---

## 5. Situații normale (nu sunt erori)

### Token reînnoit automat

```
[MyElectrica] Token expirat (401) pentru .../contract-nlc-details/7001250222
[MyElectrica] Retry: re-autentificare pentru .../contract-nlc-details/7001250222
[MyElectrica] Login OK — token obținut
[MyElectrica] GET OK: .../contract-nlc-details/7001250222 — Received data: {...}
```

**Cauza**: token-ul API a expirat. Integrarea re-autentifică automat și reîncearcă request-ul. Comportament normal.

### Senzor „mâine" necunoscut pentru Citire permisă

Dacă senzorul „Citire permisă" afișează „Nu" în afara perioadei de autocitire — e corect. PACIndicator devine „1" doar în perioada activă.

---

## 6. Situații de eroare

### Autentificare eșuată

```
[MyElectrica] Login HTTP 401 — răspuns: ...
[MyElectrica] Login respins de API: {...}
```

**Cauza**: email sau parolă incorectă, sau cont blocat.

**Rezolvare**:
1. Verifică credențialele pe [myelectrica.ro](https://myelectrica.ro)
2. Dacă contul e blocat, așteaptă și reîncearcă
3. Reconfigurează integrarea cu credențiale corecte

### Eroare de rețea / timeout

```
[MyElectrica] Eroare conexiune: .../meter-list/7001250222 — ClientConnectorError(...)
[MyElectrica] Timeout: .../readings/9001218422/7001250222
```

**Cauza**: API-ul MyElectrica nu răspunde sau conexiunea HA la internet e întreruptă.

**Rezolvare**:
1. Verifică conexiunea la internet din HA
2. Verifică dacă `https://myelectrica.ro` e accesibil
3. Integrarea reîncearcă automat la următorul ciclu — de obicei se rezolvă singur
4. Dacă persistă, mărește intervalul de actualizare

### Ierarhie goală

```
[MyElectrica] Ierarhia contului este goală
```

**Cauza**: API-ul a răspuns cu succes dar nu a returnat date de ierarhie. Contul poate fi nou sau fără contracte active.

**Rezolvare**: verifică pe [myelectrica.ro](https://myelectrica.ro) dacă ai contracte vizibile.

### Coordinator fără date la setup

```
[MyElectrica] Coordinator fără date la setup
```

**Cauza**: prima actualizare a eșuat (eroare de rețea, credențiale invalide etc.). Senzorii nu se creează.

**Rezolvare**: verifică logurile anterioare pentru cauza erorilor. Restartează HA după rezolvare.

### Eroare la trimitere index

```
[MyElectrica] Nu se pot determina datele contorului pentru NLC 7001250222 (serie=, register=)
[MyElectrica] Entitatea input_number.energy_meter_reading nu există sau nu are valoare
[MyElectrica] Eroare la trimitere index NLC 7001250222: {...}
```

**Cauze posibile**:
1. Datele contorului nu sunt disponibile (meter_list gol)
2. `input_number` nu există sau are valoare `unknown`/`unavailable`
3. API-ul a respins cererea (index invalid, perioadă închisă)

---

## 7. Logare date API

La nivel debug, integrarea loghează răspunsurile API-ului complet:

```
[MyElectrica] Login response data: {"error": false, "app_token": "..."}
[MyElectrica] GET OK: .../client-code-invoices/9001218422/2024-03-03/2026-03-03/false — Received data: {...}
[MyElectrica] POST OK: .../set-index — Received data: {...}
```

**Atenție**: aceste loguri conțin date personale (nume, adrese, coduri client, token-uri). **Nu le posta public fără a le anonimiza.**

---

## 8. Cum raportezi un bug

1. Activează debug logging (secțiunea 1)
2. Reproduce problema
3. Deschide un [issue pe GitHub](https://github.com/cnecrea/myelectrica/issues) cu:
   - **Descrierea problemei** — ce ai așteptat vs. ce s-a întâmplat
   - **Logurile relevante** — filtrează după `MyElectrica` și include 20–50 linii relevante
   - **Versiunea HA** — din **Settings** → **About**
   - **Versiunea integrării** — din `manifest.json` sau **Settings** → **Devices & Services** → MyElectrica

### Cum postezi loguri pe GitHub

Folosește blocuri de cod delimitate de 3 backticks:

````
```
2026-03-03 10:15:12 DEBUG custom_components.myelectrica [MyElectrica] Începe actualizarea datelor
2026-03-03 10:15:13 DEBUG custom_components.myelectrica [MyElectrica] GET OK: .../contract-nlc-details/7001250222
2026-03-03 10:15:14 DEBUG custom_components.myelectrica [MyElectrica] Actualizare completă
```
````

Dacă logul e foarte lung (peste 50 linii), folosește secțiunea colapsabilă:

````
<details>
<summary>Log complet (click pentru a expanda)</summary>

```
... logul aici ...
```

</details>
````
