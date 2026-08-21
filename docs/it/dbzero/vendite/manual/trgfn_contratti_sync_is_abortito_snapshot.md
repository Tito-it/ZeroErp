## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_sync_is_abortito_snapshot()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> • [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — funzione rev 2026-06-02)

Copia sul contratto **due proprietà dello stato** che gli servono come colonne proprie:

| Colonna su `vendite.contratti` | Sorgente in `config.stati_doc_contratti` |
|---|---|
| `is_abortito_snapshot` | `is_abortito` |
| `is_draft_snapshot` | `is_bozza` |

Il motivo non è la comodità di lettura. È che da quelle due colonne PostgreSQL calcola la
colonna **`GENERATED`** `partecipa_overlap_snapshot` (`NOT abortito AND NOT draft`), e su
quella colonna poggia l'indice di esclusione che impedisce due contratti sovrapposti:

```sql
ex_contratti_no_overlap
  USING gist (billing_account_id, istanza_utility_id, utility_id, ambito, validita)
  WHERE partecipa_overlap_snapshot
```

Un contratto abortito o ancora in bozza **non deve** occupare il perimetro: se lo facesse,
nessuno potrebbe più stipularne uno valido sullo stesso billing account. Questo trigger è
ciò che tiene vera quella distinzione.

---

### Aggancio

Trigger `trg_contratti_z90_sync_is_abortito_snapshot_ins_upd` —
`BEFORE INSERT OR UPDATE OF stato_doc_contratto_id` su `vendite.contratti`, `FOR EACH ROW`.

---

### ⚠️ `z90` ma `BEFORE`: la fase è la parte che conta

Il nome porta la fase `_z90_`, riservata a ciò che deve girare **per ultimo** — e insieme il
trigger è `BEFORE`, non `AFTER`. Non è una contraddizione, è il requisito:

* deve essere **`BEFORE`**, perché una colonna `GENERATED` viene calcolata sul `NEW` finale,
  cioè dopo che tutti i `BEFORE` hanno scritto. Un `AFTER` arriverebbe a calcolo già fatto e
  gli snapshot resterebbero indietro di un'operazione;
* deve essere **`z90`**, cioè l'ultimo dei `BEFORE`, perché qualunque altro trigger che
  cambiasse `stato_doc_contratto_id` dopo di lui lascerebbe gli snapshot disallineati.

⚠️ Chi rinomina questo trigger, o ne aggiunge uno alfabeticamente successivo che tocca lo
stato, rompe l'anti-overlap **senza nessun errore**: la colonna generata continua a esistere,
solo con il valore sbagliato.

---

### ⚠️ Il nome della funzione ne dichiara metà

Si chiama `sync_is_abortito_snapshot`, ma sincronizza **due** colonne. `is_draft_snapshot` è
stato aggiunto dopo e il nome non è stato aggiornato.

Chi cerca «chi valorizza `is_draft_snapshot`» partendo dal nome non trova nulla — e la
risposta è qui.

---

### Regole applicate

1. Legge `is_abortito` e `is_bozza` dalla riga di `config.stati_doc_contratti` puntata da
   `NEW.stato_doc_contratto_id`.
2. Scrive i due snapshot, con `COALESCE(..., false)`.

---

### ⚠️ Il `COALESCE` decide anche il caso «stato non trovato»

Se il `SELECT` non trova righe, le variabili restano `NULL` e il `COALESCE` le porta
entrambe a `false` — cioè a **«né abortito né bozza»**, che significa
`partecipa_overlap_snapshot = true`: il contratto entra nel perimetro dell'anti-overlap.

Nella pratica non accade, perché la FK verso `config.stati_doc_contratti` non ammette uno
stato inesistente. Ma è utile sapere da che parte cade il default se un giorno quella FK
venisse allentata: dalla parte del *più restrittivo*, non del silenzio.

---

### Codici errore

Nessuno: la funzione non solleva. Gli errori possibili sono violazioni dell'EXCLUDE
`ex_contratti_no_overlap` che questa funzione contribuisce ad alimentare.

---

{% include-markdown "signature-core.md" %}
