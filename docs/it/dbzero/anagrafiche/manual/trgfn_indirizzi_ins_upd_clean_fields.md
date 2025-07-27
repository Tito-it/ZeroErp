## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_indirizzi_ins_upd_clean_fields()`

>
> Approfondimento Tabelle:  
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)      
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)      


> Pulisce i campi di fallback di `anagrafiche.indirizzi` quando è presente un `indirizzo_dettaglio_id`.

---

### 🎯 Scopo Principale

Assicura che, in modalità **indirizzo normalizzato**, tutti i campi alternativi utilizzati per gli **indirizzi liberi** siano resettati a `NULL`. In questo modo si evita la coesistenza di dati incongruenti tra indirizzo normalizzato e indirizzo libero.

---


### Parametri del Trigger

* `NEW`: record in fase di INSERT o UPDATE di `anagrafiche.indirizzi`.
* `OLD`: record precedente alla modifica (non utilizzato).

### Valore di Ritorno

* **`NEW`**: record modificato, con i campi di fallback (`stato_id`, `indirizzo_libero`, `comune_id`, `codice_postale_id`, `administrative_area`, `locality`, `sublocality`, `postal_box`, `geoloc`) azzerati se `indirizzo_dettaglio_id` è valorizzato.

---

## 🔗 Trigger Associato

```sql
CREATE TRIGGER trg_indirizzi_ins_upd_clean_fields
  BEFORE INSERT OR UPDATE
  ON anagrafiche.indirizzi
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_ins_upd_clean_fields();
```

---

## 💡 Note Operative

* Garantisce la **mutua esclusione** tra modalità normalizzata e libera.
* Previene l’inserimento di dati superflui o incongruenti quando si usa il dettaglio civico.
* La pulizia è estesa per azzerare anche `geoloc`, si preferisce derivare sempre da `indirizzi_dettaglio`.

---

> 🧠 **“Mantieni coerenza tra indirizzo normalizzato e campi di fallback: pulizia automatica e sicura.”**
