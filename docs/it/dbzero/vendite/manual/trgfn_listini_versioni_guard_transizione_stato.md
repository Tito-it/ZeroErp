## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_listini_versioni_guard_transizione_stato()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [dbops.fn_apply_chiusura_scadenze](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze)
>
Pattern correlato:
> [vendite.trgfn_contratti_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_contratti_guard_transizione_stato)
>
Linee guida:
> [Linee guida SQL §7c — Ciclo stato + finestra di validita'](/linee-guida-sql)

### 🎯 Scopo Principale

(latest review 26-04-2026)

La trigger function **`vendite.trgfn_listini_versioni_guard_transizione_stato()`**
blocca le transizioni di stato non ammesse sul workflow versioni
listino (`BOZZA -> ATTIVA -> CHIUSA`) e impone la **precondizione
temporale** sulla chiusura: `ATTIVA -> CHIUSA` e' consentita **solo
se** `valido_al < CURRENT_DATE`.

E' applicata dal trigger
`trg_listini_versioni_a10_guard_transizione_stato_upd` (fase `_a10_`,
`BEFORE UPDATE OF stato`).

A differenza del gemello su contratti, lo stato qui e' una colonna
**varchar diretta** (CHECK constraint
`chk_listini_versioni_stato IN ('BOZZA','ATTIVA','CHIUSA')`), quindi
nessun lookup serve: i confronti avvengono direttamente sui valori
stringa.

---

### Matrice transizioni

| Da | A | Ammessa | Condizione |
| --- | --- | --- | --- |
| BOZZA | ATTIVA | si | — |
| ATTIVA | CHIUSA | si | `NEW.valido_al IS NOT NULL AND NEW.valido_al < CURRENT_DATE` |
| (qualsiasi) | (stesso stato) | si | no-op (filtrato dal `WHEN` del trigger) |
| BOZZA | CHIUSA | **no** | la bozza si cancella, non si chiude |
| ATTIVA | BOZZA | **no** | irreversibile |
| CHIUSA | * | **no** | stato terminale |

---

### Logica operativa

1. Confronto diretto tra `OLD.stato` e `NEW.stato` (varchar).
2. **Dispatch** sulle combinazioni:
   * `BOZZA -> ATTIVA`: ammessa.
   * `ATTIVA -> CHIUSA`: ammessa solo se `NEW.valido_al < CURRENT_DATE`.
   * Tutte le altre: ammessa = false.
3. Se non ammessa: `script.fn_log_and_raise_error` con codice
   `E_VERSIONE_STATO_TRANSIZIONE_INVALIDA` e contesto JSONB
   (`versione_id`, `listino_id`, `stato_da`, `stato_a`, `valido_al`).

Il filtro `WHEN (OLD.stato IS DISTINCT FROM NEW.stato)` nel trigger
garantisce che la funzione non venga invocata su no-op.

---

### Compatibilita' con il framework di chiusura automatica

L'UPDATE eseguito da `dbops.fn_apply_chiusura_scadenze()` (job
notturno `chiusura_scadenze_daily`) **soddisfa per costruzione** la
condizione `valido_al < CURRENT_DATE` del guard. La query del
framework ha lo stesso WHERE: il job passa il guard senza bypass.

Semantica `valido_al`: ultimo giorno **incluso** (convenzione
`script.trgfn_set_validita`). Implica che:

* `valido_al = oggi` → chiusura manuale **vietata**; il job
  dell'indomani chiudera' automaticamente.
* `valido_al = ieri` → chiusura manuale **ammessa** (oppure il job
  l'ha gia' fatto stanotte).

---

### Errori sollevati

| Codice | Contesto |
| --- | --- |
| `E_VERSIONE_STATO_TRANSIZIONE_INVALIDA` | `versione_id`, `listino_id`, `stato_da`, `stato_a`, `valido_al`. Quattro placeholder `%s` nel template messaggio (`config.messaggi_errore` id 391). |

---

### Esempi

**1) Transizione ammessa (attivazione di una bozza):**

```sql
UPDATE vendite.listini_versioni
   SET stato = 'ATTIVA'
 WHERE id = 42 AND stato = 'BOZZA';
-- ok
```

**2) Chiusura manuale anticipata (bloccata):**

```sql
-- Versione attiva con valido_al = 2026-12-31 (futuro):
UPDATE vendite.listini_versioni SET stato = 'CHIUSA' WHERE id = 42;
-- ERROR:  P0001 — Versione listino 42: transizione stato ATTIVA -> CHIUSA non ammessa (valido_al=2026-12-31).
```

**3) Chiusura dopo scadenza (ammessa):**

```sql
-- Versione attiva con valido_al = 2025-12-31 (gia' passato):
UPDATE vendite.listini_versioni SET stato = 'CHIUSA' WHERE id = 42;
-- ok (oppure il job notturno l'ha gia' fatto)
```

**4) Pattern raccomandato dal service backend (chiusura data-driven):**

```python
# apps/vendite/services/listini_service.py
# 1. PATCH valido_al
versione.valido_al = data_chiusura
versione.save()
# 2. Stato resta ATTIVA fino al run notturno successivo (00:05);
#    se data_chiusura < oggi puo' anche essere chiuso subito in transazione.
```

---

### Note operative

* Stato come colonna **varchar diretta** + CHECK constraint, niente lookup runtime (a differenza di contratti).
* Il guard scatta solo su `UPDATE OF stato` (NON su INSERT). L'INSERT diretto in qualunque stato e' permesso (seed/import).
* Il trigger e' in fase `_a10_` (guard pre-audit), priorita' lessicografica garantita.
* Pattern documentato in [linee-guida-sql §7c](/linee-guida-sql) come variante "stato VARCHAR".

---

{% include-markdown "signature-core.md" %}

---
