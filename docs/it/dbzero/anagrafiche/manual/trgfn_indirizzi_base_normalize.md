## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_indirizzi_base_normalize()`

> 👀 **Vedi anche**
>
**Approfondimento Tabelle:**  
> 
[anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)      
> [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)      
>
**Approfondimento Funzioni:**   
> 
[script.fn_get_default_by_param](/dbzero/script/funzioni/fn_get_default_by_param)   
>
### 🎯 Scopo Principale
(latest review 28-12-25)
Normalizzare i campi base di `anagrafiche.indirizzi` in base alla presenza del collegamento a `indirizzi_dettaglio`.

Quando `indirizzo_dettaglio_id` e' valorizzato, la funzione ripulisce tutti i campi di fallback/indirizzo libero. Quando non e' valorizzato, applica un default minimo su `stato_id` se assente.

---

### Come Funziona

1. **Caso normalizzato** (`NEW.indirizzo_dettaglio_id IS NOT NULL`):
   * Azzeramento dei campi di fallback (`stato_id`, `indirizzo_libero`, `comune_id`, `codice_postale_id`, `administrative_area`, `locality`, `sublocality`, `postal_box`).
   * Azzeramento di `geoloc` per forzare la derivazione dal dettaglio civico.
2. **Caso libero/internazionale** (`indirizzo_dettaglio_id IS NULL`):
   * Se `stato_id` e' NULL, viene impostato con `script.fn_get_default_by_param('config','stati','codice_iso3','state_code_iso3', TG_NAME)`.

---

### Parametri del Trigger

* `NEW`: record in fase di INSERT o UPDATE di `anagrafiche.indirizzi`.
* `OLD`: record precedente (non usato).

---

### Valore di Ritorno

* **`NEW`**: record modificato e coerente con la modalita' di indirizzo scelta.

---

## Trigger Associato

```sql
CREATE TRIGGER trg_indirizzi_base_normalize
  BEFORE INSERT OR UPDATE
  ON anagrafiche.indirizzi
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_base_normalize();
```

---

### Note Operative

* Evita la coesistenza di dati normalizzati e liberi nello stesso record.
* Il ricalcolo di `geoloc` dal dettaglio civico richiede un trigger dedicato
  (es. `anagrafiche.trgfn_indirizzi_sync_geoloc` su `anagrafiche.indirizzi`).
  Su `anagrafiche.indirizzi_soggetti` e' disponibile il trigger
  `trg_indirizzi_soggetti_sync_geoloc_ins_upd`.
* Il default di `stato_id` e' guidato dai parametri di configurazione.

---

> **"Coerenza indirizzi: o normalizzato con dettaglio civico, o libero con default minimo."**
