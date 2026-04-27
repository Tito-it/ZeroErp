## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_guard_transizione_stato()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [dbops.fn_apply_chiusura_scadenze](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze)
>
Pattern correlato:
> [vendite.trgfn_listini_versioni_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_transizione_stato)
>
Linee guida:
> [Linee guida SQL §7c — Ciclo stato + finestra di validita'](/linee-guida-sql)

### 🎯 Scopo Principale

(latest review 26-04-2026)

La trigger function **`vendite.trgfn_contratti_guard_transizione_stato()`**
blocca le transizioni di stato non ammesse sul workflow contratti
(`DRAFT -> ATTIVO -> CESSATO`) e impone la **precondizione temporale**
sulla cessazione: `ATTIVO -> CESSATO` e' consentita **solo se**
`valido_al < CURRENT_DATE`.

E' applicata dal trigger
`trg_contratti_a10_guard_transizione_stato_upd` (fase `_a10_`,
`BEFORE UPDATE OF stato_doc_contratto_id`).

Il guard fa **lookup via `codice_interno`** su
`config.stati_doc_contratti` per stabilita' rispetto al relabelling
del codice business-visible (codice_interno e' immutabile per
`script.trgfn_lock_columns`).

---

### Matrice transizioni

| Da | A | Ammessa | Condizione |
| --- | --- | --- | --- |
| DRAFT | ATTIVO | si | — |
| ATTIVO | CESSATO | si | `NEW.valido_al IS NOT NULL AND NEW.valido_al < CURRENT_DATE` |
| (qualsiasi) | (stesso stato) | si | no-op (filtrato dal `WHEN` del trigger) |
| DRAFT | CESSATO | **no** | la bozza si cancella, non si chiude |
| ATTIVO | DRAFT | **no** | irreversibile |
| CESSATO | * | **no** | stato terminale |
| (qualsiasi) | SOSPESO | **non gestito** | fuori scope operativo attuale |
| SOSPESO | * | **non gestito** | fuori scope operativo attuale |

> Nota: lo stato `SOSPESO` esiste come `codice_interno` in
> `config.stati_doc_contratti` ma non e' attualmente parte del
> workflow operativo gestito dal guard. Una transizione che lo
> coinvolge cade nel ramo "non ammessa" → raise.

---

### Logica operativa

1. **Lookup combinato** di `codice_interno` per OLD e NEW in una
   sola query (pivot `MAX(CASE...)`) sul catalog
   `config.stati_doc_contratti`. Riduce 2 round-trip a 1.
2. **Dispatch** sul codice OLD/NEW:
   * `DRAFT -> ATTIVO`: ammessa.
   * `ATTIVO -> CESSATO`: ammessa solo se `NEW.valido_al < CURRENT_DATE`.
   * Tutte le altre combinazioni: ammessa = false.
3. Se non ammessa: `script.fn_log_and_raise_error` con codice
   `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` e contesto JSONB
   (`contratto_id`, `numero`, `stato_da`, `stato_a`, `valido_al`).

Il filtro `WHEN (OLD.stato_doc_contratto_id IS DISTINCT FROM NEW.stato_doc_contratto_id)`
nel trigger garantisce che la funzione non venga invocata su no-op:
non e' presente nel corpo della funzione.

---

### Compatibilita' con il framework di chiusura automatica

L'UPDATE eseguito da `dbops.fn_apply_chiusura_scadenze()` (job
notturno `chiusura_scadenze_daily`) **soddisfa per costruzione** la
condizione `valido_al < CURRENT_DATE` del guard (la query del
framework ha lo stesso WHERE). Quindi il job passa il guard senza
bypass, in modo del tutto naturale.

Semantica `valido_al`: ultimo giorno **incluso** (convenzione
`script.trgfn_set_validita`). Implica che:

* `valido_al = oggi` → cessazione manuale **vietata** (la condizione
  `< CURRENT_DATE` non e' soddisfatta); il job notturno dell'indomani
  chiudera' automaticamente.
* `valido_al = ieri` → cessazione manuale **ammessa** (oppure il job
  l'ha gia' fatto stanotte).

---

### Errori sollevati

| Codice | Contesto |
| --- | --- |
| `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` | `contratto_id`, `numero`, `stato_da`, `stato_a`, `valido_al`. Quattro placeholder `%s` nel template messaggio (`config.messaggi_errore` id 392). |

---

### Esempi

**1) Transizione ammessa (attivazione di una bozza):**

```sql
UPDATE vendite.contratti
   SET stato_doc_contratto_id = (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO')
 WHERE id = 123 AND stato_doc_contratto_id = (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT');
-- ok
```

**2) Cessazione manuale anticipata (bloccata):**

```sql
-- Contratto attivo con valido_al = 2026-12-31 (futuro):
UPDATE vendite.contratti SET stato_doc_contratto_id = 5 WHERE id = 123;
-- ERROR:  P0001 — Contratto 123: transizione stato ATTIVO -> CESSATO non ammessa (valido_al=2026-12-31).
```

**3) Cessazione manuale dopo scadenza (ammessa):**

```sql
-- Contratto attivo con valido_al = 2025-12-31 (gia' passato):
UPDATE vendite.contratti SET stato_doc_contratto_id = 5 WHERE id = 123;
-- ok (oppure il job notturno l'ha gia' fatto)
```

**4) Pattern raccomandato dal service backend (cessazione data-driven):**

```python
# apps/vendite/services/contratti_service.py
# 1. PATCH valido_al
contratto.valido_al = data_cessazione
contratto.save()
# 2. Se data_cessazione < oggi: lo stato passa a CESSATO subito (transazione)
# 3. Se data_cessazione >= oggi: stato resta ATTIVO; il job notturno
#    chiudera' automaticamente al primo run dopo data_cessazione+1
```

---

### Note operative

* Lookup `codice_interno` (immutabile, UNIQUE) e non `codice` (relabellabile).
* Il guard scatta solo su UPDATE OF `stato_doc_contratto_id` (NON su INSERT). L'INSERT diretto in qualunque stato e' permesso (seed/import).
* Il trigger e' in fase `_a10_` (guard pre-audit), priorita' lessicografica garantita.

---

{% include-markdown "signature-core.md" %}

---
