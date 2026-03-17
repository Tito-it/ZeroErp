## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_indirizzi_dettaglio_normalize()`

> 👀 **Vedi anche**   
>
**Approfondimento tabelle:**    
>
[anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)   
>
**Approfondimento view:**    
>
[script.vw_indirizzo_completo](/dbzero/script/views/vw_indirizzo_completo)    
>
🎯 Scopo Principale

(latest review 28-12-25)
Normalizzare i campi dell'indirizzo dettaglio per garantire coerenza su via, civico e indirizzo completo prima di INSERT/UPDATE.

---

### Come Funziona

1. **Normalizzazione via**
   * Ricava `tipo_toponimo` e `nome_strada` da `script.vw_indirizzo_completo` e valorizza `NEW.via_norm` in maiuscolo con `TRIM`.
2. **Normalizzazione civico**
   * Se `NEW.civico` e' valorizzato e diverso da 0, costruisce `NEW.civico_norm`.
   * Se esiste `estensione_civico`, assicura il prefisso `/` e concatena (es. `12/A`).
   * Se il civico non e' valorizzato, imposta `NEW.civico_norm := 'SNC'`.
3. **Indirizzo completo normalizzato**
   * Costruisce `NEW.indirizzo_normalizzato` concatenando `via_norm`, `civico_norm` e, se presenti, `palazzina`, `scala`, `piano`, `interno`.

---

### Parametri del Trigger

* `NEW`: record in fase di INSERT o UPDATE su `anagrafiche.indirizzi_dettaglio`.
* `OLD`: record precedente (non usato).

---

### Valore di Ritorno

* **`NEW`**: record con `via_norm`, `civico_norm`, `indirizzo_normalizzato` aggiornati.

---

## Trigger Associato

```sql
CREATE TRIGGER trg_indirizzi_dettaglio_normalize
  BEFORE INSERT OR UPDATE
  ON anagrafiche.indirizzi_dettaglio
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_normalize();
```

---

### Note Operative

* La query su `script.vw_indirizzo_completo` e' eseguita in `INTO STRICT`: la riga deve esistere.
* `SNC` viene usato come fallback per civico mancante.
* La normalizzazione migliora la qualita' dei dati e le ricerche testuali.

---

> **"Indirizzi coerenti e confrontabili: normalizzazione centralizzata a livello DB."**

