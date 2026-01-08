## Funzione `anagrafiche.trgfn_indirizzi_sync_geoloc()`

> 
👀 **Vedi anche**
> 
> Approfondimento Tabelle:   
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)  
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)     


> Sincronizza il campo `geoloc` di `anagrafiche.indirizzi` e `anagrafiche.indirizzi_soggetti`
> con la geolocalizzazione memorizzata in `anagrafiche.indirizzi_dettaglio`.

---

### 🎯 Scopo Principale

Ogni volta che viene inserito o aggiornato un record in `anagrafiche.indirizzi` o
`anagrafiche.indirizzi_soggetti`, se è impostato `indirizzo_dettaglio_id`, la funzione recupera
dal dettaglio civico la coordinata geografica (`civic_geoloc`) e la copia in `NEW.geoloc`.
In questo modo il dato di geolocalizzazione rimane sempre allineato con la fonte di verità civica.

---


### Parametri del Trigger

* `NEW`: record di riga in inserimento o aggiornamento delle tabelle `anagrafiche.indirizzi`
  o `anagrafiche.indirizzi_soggetti`.
* `OLD`: non utilizzato in questa funzione.

### Valore di Ritorno

* **`NEW`** (record modificato), con `geoloc` aggiornato quando applicabile.

---

### 🔗 Trigger Associato

```sql
CREATE TRIGGER trg_indirizzi_sync_geoloc_ins_upd
  BEFORE INSERT OR UPDATE
  ON anagrafiche.indirizzi
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_sync_geoloc();

CREATE TRIGGER trg_indirizzi_soggetti_sync_geoloc_ins_upd
  BEFORE INSERT OR UPDATE
  ON anagrafiche.indirizzi_soggetti
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_sync_geoloc();
```

---

### 💡 Note Operative

* Garantisce coerenza tra i dati geografici civici (`indirizzi_dettaglio`) e la tabella principale degli indirizzi.
* Evita geolocalizzazioni obsolete: ad ogni modifica o inserimento si riallinea il campo `geoloc`.
* Se `indirizzo_dettaglio_id` è `NULL`, non interviene e lascia invariato il valore esistente di `geoloc`.

---

> 🧠 **“Allinea sempre la posizione geografica degli indirizzi con il dettaglio civico: precisione e consistenza garantite.”**
