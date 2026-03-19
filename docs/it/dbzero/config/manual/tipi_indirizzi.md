## 📚 Tabella `config.tipi_indirizzi`

---
### 🎯 Scopo Principale
La tabella **`config.tipi_indirizzi`** centralizza i **tipi di indirizzo** utilizzabili in Zero ERP, come ad esempio Residenza, Domicilio Fiscale, Sede Legale, Sede Operativa, Corrispondenza Postale, Indirizzo di Fornitura, ecc. 

---

### Vincoli

* **PRIMARY KEY**: `pk_tipi_indirizzi` su `id`
* **UNIQUE**: `uq_tipi_indirizzi_codice_interno` su `codice_interno`
* **CHECK**: `chk_cod_int_tipo_indirizzo` per garantire che il codice interno non sia vuoto

---

### 🚨 Trigger

* **`trg_tipi_indirizzi_upd_lock_cod_interno`** (BEFORE UPDATE): blocca la modifica di `codice_interno` tramite `script.trgfn_lock_columns`.
* **`trg_upd_tipi_indirizzi_audit_data_user`** (BEFORE UPDATE): aggiorna `data_update` e `user_update` con `script.trgfn_upd_audit_data_user_generic()`.

---

### Esempi di Tipi Indirizzo

I codici interni attualmente definiti in `config.tipi_indirizzi` sono:

| Codice Interno | Descrizione            |
| -------------- | ---------------------- |
| `RES`          | Residenza              |
| `DOMFISC`      | Domicilio Fiscale      |
| `SEDELEG`      | Sede Legale            |
| `SEDEOP`       | Sede Operativa         |
| `POSTA`        | Corrispondenza Postale |
| `FORNITURA`    | Indirizzo Fornitura    |

> ℹ️ Il codice interno (`codice_interno`) è utilizzato in logica applicativa e non può essere modificato una volta inserito.

---

### Uso e Casi d’Oro

* **Assegnazione tipo indirizzo**: viene referenziato in tutte le tabelle che gestiscono indirizzi (es. `anagrafiche.indirizzi`) per identificare il contesto d’uso.
* **Filtri e reportistica**: consente di raggruppare gli indirizzi per tipo nelle interfacce utente e nei report.
* **Stradario & Anagrafiche**: si integra con la struttura `anagrafiche.indirizzi_dettaglio` e la master table `config.stradario`, collegando i tipi di indirizzi alla georeferenziazione completa (via, comune, provincia, regione) e ai soggetti in anagrafica, per avere una **vista centralizzata** di tutti gli indirizzi.
* **Estendibilità**: per aggiungere nuovi tipi, basta inserire una nuova riga in questa tabella con il codice interno e la descrizione desiderati.

---

> **“Centralizzare i tipi di indirizzo in `config.tipi_indirizzi` garantisce coerenza, facilità di estensione e chiarezza nell’assegnazione e gestione degli indirizzi in Zero ERP.”**