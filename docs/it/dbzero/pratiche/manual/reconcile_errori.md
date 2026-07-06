## 📘 Documentazione Concettuale – Tabella `pratiche.reconcile_errori`

> 👀 **Vedi anche**
>
Approfondimento oggetti collegati:
>
> [pratiche.fn_reconcile_sorgente](/dbzero/pratiche/funzioni/fn_reconcile_sorgente)
> [pratiche.trgfn_documento_reconcile_proiezione](/dbzero/pratiche/funzioni/trgfn_documento_reconcile_proiezione)

---
### 🎯 Scopo Principale
(review 06-07-2026 — GUIDA D4, brief-db-guida-avanza-esito-proiettato)

Log **append-only** dei fallimenti e degli skip della riconciliazione su esito proiettato.
È la **superficie di osservabilità** del meccanismo GUIDA (`G5`, decisione D-B7).

Il trigger generico `pratiche.trgfn_documento_reconcile_proiezione` è **best-effort**: il
documento è **sovrano**, quindi un errore lato pratiche viene **inghiottito** (blocco
`EXCEPTION`) e **non** fa rollback del cambio-stato del documento. Senza questa tabella un
avanzamento milestone mancato resterebbe **silenzioso** (anche in caso di bug). Qui invece
è **diagnosticabile**.

---

### Ruolo nel processo

* La scrive **il trigger** nel proprio handler `EXCEPTION` (l'`INSERT` gira nella transazione
  esterna del cambio-stato documento, **fuori** dal savepoint rollbackato) e
  **`fn_reconcile_sorgente`** per gli **skip deliberati** (es. tie-break ambiguo,
  `errcode = 'E_RECONCILE_AMBIGUO'`).
* **Nessuna FK** verso `pratiche`/`flussi`: è un log **resiliente** per definizione, deve
  sopravvivere anche se la causa del fallimento è proprio un dato inconsistente sulla pratica.

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `sorgente_tipo_id` | BIGINT. Tipo sorgente (`config.sorgenti`) del documento che ha innescato il reconcile. |
| `sorgente_uid` | TEXT. UID del documento (chiave nativa castata a text). |
| `pratica_id` | BIGINT nullable. Pratica coinvolta, se risolta (no FK). |
| `flusso_id` | BIGINT nullable. Milestone coinvolto, se identificato (no FK). |
| `errcode` | TEXT. `SQLSTATE` del fallimento, oppure codice dello skip deliberato (es. `E_RECONCILE_AMBIGUO`). |
| `messaggio` | TEXT. `SQLERRM` / descrizione dello skip. |
| `tx_id` | UUID. Transaction-id di sessione per correlazione col giornale/log. |

---

### Esempio d'uso

```sql
-- Avanzamenti mancati recenti (fallimenti + skip), più recenti in cima.
SELECT data_insert, sorgente_tipo_id, sorgente_uid, errcode, messaggio
FROM pratiche.reconcile_errori
ORDER BY data_insert DESC
LIMIT 50;

-- Solo i tie-break ambigui (2+ milestone candidati senza flusso_id esplicito).
SELECT * FROM pratiche.reconcile_errori WHERE errcode = 'E_RECONCILE_AMBIGUO';
```

---

{% include-markdown "signature-core.md" %}
