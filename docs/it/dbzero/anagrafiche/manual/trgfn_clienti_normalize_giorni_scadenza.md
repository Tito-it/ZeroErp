## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_clienti_normalize_giorni_scadenza()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
Pattern correlato (gemella fornitori):
> [anagrafiche.trgfn_fornitori_guard_normalize](/dbzero/anagrafiche/funzioni/trgfn_fornitori_guard_normalize)

### 🎯 Scopo Principale

(latest review 27-04-2026)

La trigger function **`anagrafiche.trgfn_clienti_normalize_giorni_scadenza()`**
applica le regole **dominio scadenza fattura** del cliente prima della
scrittura. Il dominio combina due colonne:

* `tipo_gg_scadenza_ft CHAR(1)` — modalita' di calcolo della data scadenza
  fattura (`G` giorni, `F` fine mese, `M` manuale, `N` nessuna).
* `nr_giorni_scadenza INTEGER` — numero giorni associati al calcolo, **solo**
  per le modalita' che richiedono un'offset (`G`, `F`).

E' applicata dal trigger
`trg_clienti_normalize_giorni_scadenza_ins_upd`
(`BEFORE INSERT OR UPDATE OF tipo_gg_scadenza_ft, nr_giorni_scadenza`,
no fase `_a10_` perche' fa anche normalize, non solo guard).

Pattern allineato alla gemella
[`anagrafiche.trgfn_fornitori_guard_normalize`](/dbzero/anagrafiche/funzioni/trgfn_fornitori_guard_normalize)
sulla coppia `ritenuta_acconto`/`ritenuta_aliquota`: stessa logica
asimmetrica normalize-vs-guard.

---

### Regole applicate

| Operazione | `tipo_gg_scadenza_ft` (NEW) | `nr_giorni_scadenza` (NEW) | Esito |
| --- | --- | --- | --- |
| INSERT/UPDATE | `'G'` o `'F'` | `> 0` | OK |
| INSERT/UPDATE | `'M'` o `'N'` | qualunque | **Normalize**: `nr_giorni_scadenza := NULL` |
| INSERT/UPDATE | `'G'` o `'F'` | `NULL` o `<= 0` | **Raise** `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI` |
| INSERT/UPDATE | fuori dominio (es. `'X'`) | qualunque | **CHECK** `chk_clienti_tipo_gg_scadenza_ft` rifiuta (SQLSTATE 23514) |

### Asimmetria normalize / guard

Stessa filosofia della gemella fornitori:

* **Normalize silenzioso** quando il payload e' palesemente "spazzatura"
  (es. l'utente ha cambiato la modalita' a `N` ma il FE/import ha lasciato
  un residuo `nr_giorni = 5`): il dato sporco non e' bloccante, viene
  ripulito senza interrompere il flusso utente.
* **Raise fail-fast** quando il payload e' ambiguo (es. modalita' `G` con
  `nr_giorni` mancante): qui l'omissione e' probabilmente un bug del
  caller, conviene esporlo subito invece di salvare un record monco che
  fara' poi calcoli scadenza errati.

---

### Logica operativa

1. **Branch 1 — normalize**: se `NEW.tipo_gg_scadenza_ft NOT IN ('G','F')`,
   forza `NEW.nr_giorni_scadenza := NULL` e ritorna NEW. La modifica e'
   silenziosa e idempotente.
2. **Branch 2 — guard**: se `NEW.tipo_gg_scadenza_ft IN ('G','F')` e
   `NEW.nr_giorni_scadenza IS NULL OR <= 0`, solleva
   `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI` via
   `script.fn_log_and_raise_error` con contesto JSONB
   (`cliente_id`, `tipo_gg_scadenza_ft`, `nr_giorni_scadenza`) e due
   placeholder `%s` nel template messaggio
   ([`config.messaggi_errore`](/dbzero/config/tabelle/messaggi_errore) id
   397).
3. **CHECK constraint** `chk_clienti_tipo_gg_scadenza_ft IN ('G','M','F','N')`
   filtra i valori fuori dominio (es. `'X'`) e scatta dopo i BEFORE
   trigger: il trigger normalize fa branch 1 (forza `nr_giorni = NULL`),
   poi il CHECK rifiuta con SQLSTATE 23514.

Il trigger ha clausola `OF tipo_gg_scadenza_ft, nr_giorni_scadenza`: scatta
solo quando una di queste due colonne cambia. Su INSERT la clausola e'
ignorata da PostgreSQL e il trigger scatta sempre (corretto: i nuovi
record vanno validati a prescindere).

---

### Errori sollevati

| Codice | Contesto | Quando |
| --- | --- | --- |
| `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI` | `cliente_id`, `tipo_gg_scadenza_ft`, `nr_giorni_scadenza`. Due `%s` nel template ([`config.messaggi_errore`](/dbzero/config/tabelle/messaggi_errore) id 397). | Branch 2 — modalita' `G`/`F` ma `nr_giorni` NULL/<=0. SQLSTATE P0001. |
| `chk_clienti_tipo_gg_scadenza_ft` | CHECK constraint, non un raise applicativo. | `tipo_gg_scadenza_ft` fuori dominio `('G','M','F','N')`. SQLSTATE 23514. |

---

### Esempi

**1) Combinazione valida (giorni dalla data fattura):**

```sql
UPDATE anagrafiche.clienti
   SET tipo_gg_scadenza_ft = 'G',
       nr_giorni_scadenza  = 30
 WHERE id = 42;
-- ok
```

**2) Combinazione valida (fine mese + N giorni):**

```sql
UPDATE anagrafiche.clienti
   SET tipo_gg_scadenza_ft = 'F',
       nr_giorni_scadenza  = 60
 WHERE id = 42;
-- ok
```

**3) Normalize silenzioso (residuo dopo cambio modalita'):**

```sql
UPDATE anagrafiche.clienti
   SET tipo_gg_scadenza_ft = 'N',
       nr_giorni_scadenza  = 5
 WHERE id = 42;
-- ok
SELECT nr_giorni_scadenza FROM anagrafiche.clienti WHERE id = 42;
-- NULL  (forzato dal trigger, payload sporco ripulito)
```

**4) Guard fail-fast (modalita' G senza giorni):**

```sql
UPDATE anagrafiche.clienti
   SET tipo_gg_scadenza_ft = 'G',
       nr_giorni_scadenza  = NULL
 WHERE id = 42;
-- ERROR:  P0001 — Cliente: tipo_gg_scadenza_ft=G richiede nr_giorni_scadenza > 0 (ricevuto NULL).
```

**5) Guard fail-fast (modalita' G con 0 giorni):**

```sql
UPDATE anagrafiche.clienti
   SET tipo_gg_scadenza_ft = 'G',
       nr_giorni_scadenza  = 0
 WHERE id = 42;
-- ERROR:  P0001 — Cliente: tipo_gg_scadenza_ft=G richiede nr_giorni_scadenza > 0 (ricevuto 0).
```

**6) Tipo fuori dominio (CHECK):**

```sql
UPDATE anagrafiche.clienti
   SET tipo_gg_scadenza_ft = 'X',
       nr_giorni_scadenza  = 5
 WHERE id = 42;
-- ERROR:  23514 — new row for relation "clienti" violates check constraint "chk_clienti_tipo_gg_scadenza_ft"
```

---

### Pre-requisiti schema (migration package 20260427-03)

Il trigger lavora insieme a tre componenti applicati nella stessa
migration di pacchetto:

* **Backfill**: UPDATE one-shot sui record incoerenti
  (`tipo NOT IN ('G','F') AND nr_giorni IS NOT NULL` -> NULL). ZeroErp non
  e' in produzione, quindi non serve compat.
* **DROP DEFAULT** su `nr_giorni_scadenza`: il default `0` diventerebbe
  misleading sotto la nuova regola (per `G`/`F` non valido, per `M`/`N`
  privo di significato). Default implicito NULL.
* **CHECK constraint** `chk_clienti_tipo_gg_scadenza_ft IN ('G','M','F','N')`:
  vincola il dominio del tipo. Coerente con la baseline dichiarata dal
  brief BE 27-04-2026.

---

### Note operative

* **Niente fase `_a10_`** sul trigger: la fase e' riservata a guard puri
  fail-fast. Qui c'e' anche normalize che modifica `NEW`. Pattern coerente
  con i normalize esistenti su `clienti`
  (`trg_clienti_set_periodo_ins_upd`, `trg_clienti_sync_pdp_ins_upd`,
  `trg_clienti_sync_utility_from_ba_ins_upd`) e con la gemella
  `trg_fornitori_guard_normalize_ins_upd`.
* **Defense-in-depth**: il backend
  `apps.vendite.services` (o equivalente lato anagrafiche) applica le
  stesse regole a livello service. Il trigger DB garantisce uniformita'
  anche per UPDATE diretti SQL e script di manutenzione.
* **Audit-safe**: il trigger ha clausola `OF tipo_gg_scadenza_ft,
  nr_giorni_scadenza`, quindi non scatta su UPDATE che toccano solo
  colonne audit (`data_update`/`user_update`/`tx_id`).
* **Codice errore seedato** in
  [`config.messaggi_errore`](/dbzero/config/tabelle/messaggi_errore) id
  397: opzionalmente fallback a `MESSAGGIO_NON_DEFINITO` (id 14) se non
  presente, ma il seed e' parte della stessa migration pacchetto.

---

{% include-markdown "signature-core.md" %}

---
