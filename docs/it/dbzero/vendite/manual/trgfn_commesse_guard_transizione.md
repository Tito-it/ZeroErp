## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_commesse_guard_transizione()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.commesse](/dbzero/vendite/tabelle/commesse)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)
> [vendite.transizioni_stati_commessa](/dbzero/vendite/tabelle/transizioni_stati_commessa)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [vendite.fn_cambia_stato_commessa](/dbzero/vendite/funzioni/fn_cambia_stato_commessa)
>
Pattern correlato (domini gemelli):
> [vendite.trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione)

### 🎯 Scopo Principale

(rev 2026-06-07)

La trigger function **`vendite.trgfn_commesse_guard_transizione()`** è l'**enforcement
DB-first del grafo transizioni** della commessa. È applicata dal trigger
`trg_commesse_a10_guard_transizione_upd` (fase `_a10_`, `BEFORE UPDATE OF stato_commessa_id`).

Come il guard gemello `trgfn_ordini_guard_transizione`, **legge la matrice**
`vendite.transizioni_stati_commessa` (grafo non hardcodato). Intercetta **ogni chiamante**
(`fn_cambia_stato_commessa`, handler applicativi, UPDATE diretto): nessun UPDATE può forzare
una transizione illegale.

---

### Regole applicate (`BEFORE UPDATE OF stato_commessa_id`)

1. **Transizione in matrice**: la coppia `(OLD.stato, NEW.stato)` deve esistere in
   `vendite.transizioni_stati_commessa` con `attivo = true`. Altrimenti
   `E_COMMESSA_STATO_TRANSIZIONE_INVALIDA`.
2. **Precondizione → `PRONTA_FATTURAZIONE`**: la commessa deve avere almeno una riga
   `commesse_attivita` con `stato_approvazione = 'APPROVATA'` e `stato_emissione = 'NON_EMESSA'`.
   Altrimenti `E_COMMESSA_NESSUNA_RIGA_APPROVATA`. Questa regola tiene allineati i due livelli
   (testata emittibile ⇔ esiste qualcosa da emettere) ed è analoga alla regola
   "DRAFT→CONFERMATO con almeno una riga" del guard ordini.

**No-op**: se `NEW.stato_commessa_id` non è distinto da `OLD.stato_commessa_id` (UPDATE su
altre colonne dello stesso set), il guard ritorna senza controlli.

**INSERT non vincolato**: per consentire seed/import con stati diretti, il guard è attivo
**solo** su `UPDATE OF stato_commessa_id`.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_COMMESSA_STATO_TRANSIZIONE_INVALIDA` (472) | Transizione assente o non attiva in matrice |
| `E_COMMESSA_NESSUNA_RIGA_APPROVATA` (473) | Verso `PRONTA_FATTURAZIONE` senza righe `APPROVATA`+`NON_EMESSA` |

Sollevati via `script.fn_log_and_raise_error` (nessun `E_GENERICO`).

---

### Note di design

* La regola di dominio (righe approvate) vive **nel trigger**, non nella matrice: è semantica
  di processo, non di grafo. La matrice resta puramente strutturale.
* Difesa in profondità: il trigger valida la matrice su qualunque UPDATE; l'entrypoint
  `fn_cambia_stato_commessa` aggiunge solo la risoluzione codice→id e il logging (non
  ri-valida la matrice → niente logica duplicata).

---

{% include-markdown "signature-core.md" %}
