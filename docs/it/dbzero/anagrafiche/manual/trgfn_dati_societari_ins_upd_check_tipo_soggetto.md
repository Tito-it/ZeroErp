## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_dati_societari_ins_upd_check_tipo_soggetto()`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:
>
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari)   
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)    
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio)  
>
> Approfondimento funzioni:
>   
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)

---

### 🎯 Scopo Principale

Verificare che il soggetto associato ai dati societari (
`new.soggetto_id` in `anagrafiche.dati_societari`
) abbia un `cod_int_tipo_soggetto` ammesso (solo **`SC`** o **`SP`**). In caso contrario, viene lanciato un errore tramite `script.fn_log_and_raise_error`.

---

### 🔗 Collegamenti

* **`anagrafiche.dati_societari`** – tabella su cui viene applicato il trigger `BEFORE INSERT OR UPDATE` che richiama questa funzione.
* **`anagrafiche.soggetti`** – da cui si legge il campo `tipo_soggetto_dettaglio_id`.
* **`config.tipi_soggetto_dettaglio`** – contiene `cod_int_tipo_soggetto` per validazione.

---

### 💡 Note Operative

* Utilizza `script.fn_log_and_raise_error` per loggare dettagli e abortire la DML in caso di tipo non ammesso (codice errore `E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`).
* Facile da estendere aggiungendo codici consentiti alla condizione.
* Si accompagna al trigger definito come:

```sql
CREATE TRIGGER trg_dati_societari_ins_upd_check_tipo_soggetto
  BEFORE INSERT OR UPDATE ON anagrafiche.dati_societari
  FOR EACH ROW EXECUTE FUNCTION anagrafiche.trgfn_dati_societari_ins_upd_check_tipo_soggetto();
```

* Assicurarsi che la funzione sia caricata prima del trigger e aggiornata in caso di modifiche future.

---

> 🧠 **“Blocca in anticipo l’inserimento di dati societari per soggetti non conformi: integrità di business garantita.”**
