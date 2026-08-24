## 📘 Documentazione Concettuale – Funzione `pratiche.trgfn_flussi_guard_esito_completato()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> • [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche)
> • [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche)
>
Approfondimento funzioni:
> • [config.trgfn_stati_doc_guard_esito_verdetto](/dbzero/config/funzioni/trgfn_stati_doc_guard_esito_verdetto)
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Nessuna fase si chiude senza verdetto.** Se un flusso di pratica passa allo stato
`COMPLETATO`, la colonna `esito` deve essere valorizzata.

È la regola che tiene insieme il modello: lo stato dice *dove si è arrivati*, l'esito dice
*com'è andata*. Un flusso `COMPLETATO` con esito nullo sarebbe una fase chiusa di cui nessuno
sa il risultato — e a valle non ci sarebbe modo di ricostruirlo, perché il verdetto non è
derivabile dallo stato.

---

### Aggancio

Trigger `trg_flussi_a10_guard_esito_completato_ins_upd` — fase `_a10_`,
`BEFORE INSERT OR UPDATE OF stato_id` su `pratiche.flussi`, `FOR EACH ROW`.

---

### Regole applicate

Blocca quando **entrambe** le condizioni valgono:

1. `NEW.esito IS NULL`;
2. `NEW.stato_id` corrisponde alla riga di `config.stati_flussi_pratiche` con
   `codice_interno = 'COMPLETATO'`.

Lo stato terminale è riconosciuto **per codice interno**, non per id: la matrice degli stati
resta dato di configurazione e il guard non ne fotografa nessuna chiave tecnica.

---

### ⚠️ Il guard scatta sullo stato, non sull'esito

Il trigger è `UPDATE OF stato_id`. Conseguenza pratica: **svuotare l'esito di un flusso già
`COMPLETATO` non fa scattare nulla.**

```sql
UPDATE pratiche.flussi SET esito = NULL WHERE id = :flusso_completato;  -- passa
```

La regola è quindi presidiata **al momento della chiusura**, non in permanenza. Se serve
anche l'immutabilità a valle, va aggiunta con un lock di colonna: questo guard non la copre,
e nessun `UPDATE OF esito` è oggi agganciato.

---

### Rapporto con il guard gemello di `config`

`config.trgfn_stati_doc_guard_esito_verdetto` presidia un asse **diverso**: che l'esito
usato come proiezione di uno stato documento sia un vero verdetto. Qui invece si presidia
la *presenza* dell'esito alla chiusura del flusso. I due si completano:

* **qui**: chiudere ⇒ deve esserci un esito;
* **là**: l'esito usato come proiezione ⇒ deve essere un verdetto.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_FLUSSI_ESITO_OBBLIGATORIO` | Stato portato a `COMPLETATO` con `esito` nullo |

Sollevato via `script.fn_log_and_raise_error` con `area = 'pratiche'`; il `tx_id` propagato
è `NEW.tx_id`, quindi l'errore è correlabile alla transazione applicativa che l'ha causato.

---

{% include-markdown "signature-core.md" %}
