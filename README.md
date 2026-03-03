
![logo-my-electrica](https://github.com/user-attachments/assets/4f8abcd2-b470-4521-918e-036fc8e7354c)

# MyElectrica România - Integrare pentru Home Assistant 🏠🇷🇴
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/cnecrea/myelectrica)](https://github.com/cnecrea/myelectrica/releases)
![Total descărcări pentru toate versiunile](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/cnecrea/myelectrica/main/statistici/shields/descarcari.json)
![Descărcări pentru ultima versiune](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/cnecrea/myelectrica/main/statistici/shields/ultima_release.json)


Această integrare pentru Home Assistant oferă **monitorizare completă** a datelor contractuale și a consumului pentru utilizatorii MyElectrica România. Integrarea este configurabilă prin interfața UI și permite afișarea datelor despre contract, indexuri curente, facturi restante și istoricul plăților. 🚀

## 🌟 Caracteristici

### Senzor `Contul Meu`:
  - **🔍 Monitorizare Generală**:
      - Afișează informații detaliate despre contractul de furnizare energie.
  - **📊 Atribute disponibile**:
      - **Tip contract**: Tipul contractului (determinat/nedeterminat).
      - **Produs**: Denumirea produsului de energie.
      - **Data contractului**: Data semnării contractului.
      - **Status contract**: Statusul curent al contractului.
      - **Periodicitate citiri**: Intervalul în care se fac citirile.
      - **Grup regiune**: Regiunea corespunzătoare locației de consum.

### Senzor `Conventie Consum`:
  - **🔍 Monitorizare Date Convenție**:
      - Afișează consumul lunar convenit pentru fiecare lună.
  - **📊 Atribute disponibile**:
      - **Consum pe luna [nume lună]**: Cantitatea de consum convenită (în kWh).

### Senzor `Factura Restantă`:
- **📄 Detalii Sold**:
  - Afișează dacă există facturi restante și detalii pe luni.
- **📊 Atribute disponibile**:
  - **Restanțe pe luna [nume lună]**: Soldul restant pentru luna respectivă.
  - **Total neachitat**: Suma totală restantă, afișată în lei.

### Senzor `Istoric Plăți`:
- **📚 Date Istorice**:
  - Afișează istoricul plăților pentru facturile anterioare.
- **📊 Atribute disponibile**:
  - **Lună plată**: Suma achitată pentru luna respectivă.
  - **Total achitat**: Suma totală achitată.

---

## ⚙️ Configurare

### 🛠️ Interfața UI:
1. Adaugă integrarea din meniul **Setări > Dispozitive și Servicii > Adaugă Integrare**.
2. Introdu datele contului MyElectrica:
   - **Nume utilizator**: username-ul contului tău MyElectrica.
   - **Parolă**: parola asociată contului tău.
   - **Cod încasare**: Cod unic asociat contractului tău.
     - Dacă codul este format din 10 cifre (ex. `5004697022`), integrarea adaugă automat două zerouri, astfel încât să devină `005004697022`.
   - **Cod client** și **Cod NLC**: Codurile asociate locației tale de consum.
   - **Interval de actualizare**: Timpul în secunde între actualizări (implicit: 3600 secunde).
3. Salvează configurația și bucură-te de monitorizarea datelor în Home Assistant.

---

## 🚀 Instalare

### 💡 Instalare prin HACS:
1. Adaugă [depozitul personalizat](https://github.com/cnecrea/myelectrica) în HACS. 🛠️
2. Caută integrarea **MyElectrica România** și instaleaz-o. ✅
3. Repornește Home Assistant și configurează integrarea. 🔄

### ✋ Instalare manuală:
1. Clonează sau descarcă [depozitul GitHub](https://github.com/cnecrea/myelectrica). 📂
2. Copiază folderul `custom_components/myelectrica` în directorul `custom_components` al Home Assistant. 🗂️
3. Repornește Home Assistant și configurează integrarea. 🔧

---

## ✨ Exemple de utilizare

### 🔔 Automatizare pentru Index:
Creează o automatizare pentru a primi notificări când indexul curent depășește o valoare specificată.

```yaml
alias: Notificare Index Ridicat
description: Notificare dacă indexul depășește 1000
trigger:
  - platform: numeric_state
    entity_id: sensor.index_curent
    above: 1000
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "Index Ridicat Detectat! ⚡"
      message: "Indexul curent este {{ states('sensor.index_curent') }}."
mode: single
```

### 🔍 Card pentru Dashboard:
Afișează datele despre contract, indexuri și arhivă pe interfața Home Assistant.

```yaml
type: entities
title: Monitorizare MyElectrica
entities:
  - entity: sensor.contul_meu
    name: Contul Meu
  - entity: sensor.conventie_consum
    name: Convenție Consum
  - entity: sensor.factura_restanta
    name: Factură Restantă
  - entity: sensor.istoric_plati
    name: Istoric Plăți
```

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

