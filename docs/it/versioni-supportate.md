# 📄 Versioni supportate e Licenze dei componenti utilizzati

Zero ERP utilizza esclusivamente componenti **open‑source** o **gratuiti**, coperti da licenze permissive o copyleft compatibili con la distribuzione del progetto. L’obiettivo è garantire:

* massima trasparenza tecnologica,
* assenza di vincoli commerciali,
* piena verificabilità del codice,
* facilità di manutenzione da parte della comunità.

Tutti i componenti adottati provengono da ecosistemi maturi, ampiamente supportati e con una storia consolidata di stabilità e sicurezza.

---

## 📦 Stack software principale

| Componente      | Versione  | Licenza principale |
| --------------- | --------- | ------------------ |
| **Python**      | 3.x       | PSF License        |
| **Django**      | 5.x       | BSD 3‑Clause       |
| **PostgreSQL**  | 18+       | PostgreSQL License |
| **Liquibase**   | 5.x (OSS) | Apache License 2.0 |
| **Vue 3**       | 3.x       | MIT License        |
| **PrimeVue**    | 4.x       | MIT License        |
| **Node / Vite** | 24+/7.x   | MIT License        |
| **Zensical**    | latest    | MIT License        |
| **Docker CE**   | latest    | Apache 2.0 / MIT   |

Tutti i componenti sono impiegati in conformità con le rispettive licenze.

---

## 🔍 Dettaglio: Liquibase 5 OSS

A partire dalla versione **5.x**, Liquibase introduce un modello di distribuzione basato su tre edizioni: **OSS**, **Pro** ed **Enterprise**.

Zero ERP utilizza esclusivamente la **Liquibase OSS Edition**, distribuita sotto licenza **Apache License 2.0**, completamente open‑source e liberamente utilizzabile anche in contesti commerciali.

Caratteristiche dell’edizione OSS:

* tutte le funzionalità core per la gestione delle migrazioni database,
* compatibilità completa con PostgreSQL,
* supporto al nuovo **Liquibase Package Manager (LPM)** per la gestione dei driver JDBC,
* parsing più robusto e modello tecnico aggiornato.

Non sono inclusi componenti proprietari delle edizioni Pro/Enterprise (es. reportistica avanzata, controlli aggiuntivi, changeType commerciali).

---
{% include-markdown "signature-core.md" %}
