## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_promo_articoli_guard_data_driven()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.promo_articoli](/dbzero/vendite/tabelle/promo_articoli)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> `script.trgfn_guard_date_validita` — il guard comune dell'ordine delle date (automazione `DATE_VALIDITA`)
> [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)
>
Pattern correlato:
> [vendite.trgfn_listini_versioni_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_transizione_stato)
> [vendite.trgfn_contratti_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_contratti_guard_transizione_stato)
>
Linee guida:
> [Linee guida SQL §7c — Ciclo stato + finestra di validita'](/linee-guida-sql)

### 🎯 Scopo Principale

(latest review 27-04-2026)

La trigger function **`vendite.trgfn_promo_articoli_guard_data_driven()`**
applica le regole **data-driven** di immutabilita' alle promo articoli
(STADIO 0 del resolver pricing v5):

* **No retroattivita'** alla creazione: una promo non puo' nascere con
  validita' iniziale che cade nel passato o nello stesso giorno.
* **Whitelist ristretta** sugli UPDATE quando la promo e' gia' iniziata:
  solo descrizione, `valido_al` (>= oggi) e `meta` sono mutabili.
* **Immutabilita' terminale** sugli UPDATE quando la promo e' scaduta:
  nessun campo dominio puo' essere modificato.

E' applicata dal trigger
`trg_promo_articoli_a10_guard_data_driven_ins_upd`
(fase `_a10_`, `BEFORE INSERT OR UPDATE` `FOR EACH ROW`). Single trigger
per INSERT + UPDATE perche' la regola "no retroattivita'" e' la stessa
predicato (INSERT e' un caso degenere di UPDATE su promo FUTURA con OLD
assente).

A differenza dei guard gemelli `listini_versioni` e `contratti`, qui
**non esiste una colonna `stato`**: lo stato della promo
(FUTURA / INIZIATA / SCADUTA) e' **derivato dalle date**
`valido_dal` / `valido_al` e mai persistito. Il guard ricalcola lo
stato a runtime da `OLD.valido_dal`/`OLD.valido_al` al momento
dell'UPDATE.

---

### Stati derivati dalle date

| Stato | Predicato | Significato |
| --- | --- | --- |
| FUTURA   | `CURRENT_DATE < OLD.valido_dal` | Programmata, non ancora applicata. |
| INIZIATA | `OLD.valido_dal <= CURRENT_DATE <= OLD.valido_al` | In corso oggi: applicata dal resolver per le righe nuove. |
| SCADUTA  | `OLD.valido_al < CURRENT_DATE` | Terminata: non piu' applicata, ma referenziata da snapshot pricing v5 storici (`commesse_attivita.promo_id`). |

Nota: il resolver pricing
[`vendite.fn_resolve_prezzo_listino_v2`](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)
filtra le promo applicabili tramite `validita @> data_riferimento`,
**indipendentemente** da qualunque flag di stato. La logica operativa e'
quindi gia' fail-safe sulle date; il guard fornisce **defense-in-depth**
applicativa contro UPDATE diretti SQL che porterebbero la promo in stato
incoerente con lo snapshot pricing gia' chiuso.

---

### Matrice regole

| Operazione | Stato (derivato OLD) | Vincolo | Errore |
| --- | --- | --- | --- |
| INSERT | — | `NEW.valido_dal > CURRENT_DATE` | `E_PROMO_RETROATTIVA` |
| UPDATE | FUTURA  | tutti i campi mutabili; date solo verso il futuro (`NEW.valido_dal > today`, `NEW.valido_al >= today`) | `E_PROMO_RETROATTIVA` |
| UPDATE | INIZIATA | solo `descrizione`, `valido_al` (>= oggi), `meta` mutabili | `E_PROMO_INIZIATA_CAMPI_RISTRETTI` |
| UPDATE | INIZIATA | nuovo `valido_al < CURRENT_DATE` (tentativo di pre-datare la chiusura) | `E_PROMO_RETROATTIVA` |
| UPDATE | SCADUTA  | nessun campo dominio mutabile (immutabile terminale) | `E_PROMO_SCADUTA_IMMUTABILE` |
| UPDATE | SCADUTA  | nessun campo dominio cambia (audit-only refresh: `data_update`/`user_update`/`tx_id`) | ammesso |

> Nota INIZIATA: l'unica via per "anticipare la chiusura" di una promo
> in corso e' impostare `valido_al = oggi`. Il giorno dopo la promo
> entra in SCADUTA per costruzione (semantica `valido_al` = ultimo
> giorno **incluso**).

---

### Logica operativa

1. **Dispatch su `TG_OP`**:
   * `INSERT`: verifica `NEW.valido_dal > CURRENT_DATE`. Il vincolo
     `valido_al >= valido_dal` lo verifica il guard comune delle date
     (`script.trgfn_guard_date_validita`, automazione `DATE_VALIDITA`),
     e sotto di lui la colonna generata `validita`; non serve ripeterlo
     nel guard.
   * `UPDATE`: stato derivato da `OLD.valido_dal`/`OLD.valido_al`,
     poi dispatch sui tre rami.

2. **SCADUTA**: confronto a tupla `IS DISTINCT FROM` su 10 colonne
   dominio (`codice`, `descrizione`, `articolo_id`, `uom_id`,
   `tipo_variazione`, `valore_variazione`, `valido_dal`, `valido_al`,
   `attivo`, `meta`). Le colonne audit (`data_update`, `user_update`,
   `tx_id`) **non** rientrano nel confronto: i loro trigger di sistema
   non costituiscono UPDATE applicativo e non devono essere bloccati.

3. **INIZIATA**: whitelist diretta. Si rifiuta la mutazione di
   `codice`, `articolo_id`, `uom_id`, `tipo_variazione`,
   `valore_variazione`, `valido_dal`, `attivo`. Si ammette mutazione di
   `descrizione`, `meta`, `valido_al` (con vincolo `>= CURRENT_DATE`).

4. **FUTURA**: tutti i campi mutabili. Le sole regole sono
   `NEW.valido_dal > CURRENT_DATE` (se cambia) e
   `NEW.valido_al >= CURRENT_DATE` (se cambia). Confronti `IS DISTINCT
   FROM` evitano falsi positivi su no-op.

5. Su violazione: `script.fn_log_and_raise_error` con codice + contesto
   JSONB (`promo_id`, `codice`, `valido_dal`/`valido_al`, `oggi`) e tre
   placeholder `%s` per il template messaggio (vedi
   [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore) id
   394/395/396).

Il trigger e' **senza clausola `WHEN`**: scatta su ogni INSERT/UPDATE.
La protezione contro falsi positivi su no-op e' interna alla funzione
(confronti `IS DISTINCT FROM`), permettendo cosi' di lasciar passare
gli UPDATE applicativi che toccano solo le colonne audit.

---

### Errori sollevati

| Codice | Contesto | Quando |
| --- | --- | --- |
| `E_PROMO_RETROATTIVA` | `op`, `campo`, `valore`, `oggi`. Tre `%s` nel template (`config.messaggi_errore` id 394). | INSERT con `valido_dal <= today`; UPDATE FUTURA/INIZIATA con date verso il passato. |
| `E_PROMO_INIZIATA_CAMPI_RISTRETTI` | `promo_id`, `codice`, `valido_dal`, `oggi`. Tre `%s` nel template (id 395). | UPDATE su INIZIATA che tocca campi fuori whitelist. |
| `E_PROMO_SCADUTA_IMMUTABILE` | `promo_id`, `codice`, `valido_al`, `oggi`. Tre `%s` nel template (id 396). | UPDATE su SCADUTA con almeno una colonna dominio modificata. |

Tutti e tre i codici sono mappati lato backend in
`apps.core.services.error_policies`:

* `E_PROMO_RETROATTIVA` -> HTTP 400 + `highlight_form_fields`
* `E_PROMO_INIZIATA_CAMPI_RISTRETTI` -> HTTP 409 + `show_toast_error`
* `E_PROMO_SCADUTA_IMMUTABILE` -> HTTP 409 + `show_toast_error`

---

### Esempi

**1) Creazione promo programmata (ammessa):**

```sql
INSERT INTO vendite.promo_articoli(
    codice, descrizione, articolo_id, uom_id,
    tipo_variazione, valore_variazione, valido_dal, valido_al)
VALUES ('PROMO_2026Q3', 'Sconto estate', '...', 1,
        'PERCENTUALE', 15, CURRENT_DATE + 30, CURRENT_DATE + 90);
-- ok
```

**2) Tentativo di INSERT retroattivo (bloccato):**

```sql
INSERT INTO vendite.promo_articoli(
    codice, descrizione, articolo_id, uom_id,
    tipo_variazione, valore_variazione, valido_dal, valido_al)
VALUES ('PROMO_BACKDATE', 'Promo retroattiva', '...', 1,
        'PERCENTUALE', 10, CURRENT_DATE - 1, CURRENT_DATE + 30);
-- ERROR:  P0001 — Promo articolo: il campo valido_dal ha valore <data> antecedente o uguale a oggi (<oggi>).
```

**3) UPDATE descrizione su promo INIZIATA (ammesso):**

```sql
UPDATE vendite.promo_articoli
   SET descrizione = 'Descrizione corretta'
 WHERE id = 42;  -- promo con valido_dal=oggi-5, valido_al=oggi+10
-- ok
```

**4) UPDATE prezzo su promo INIZIATA (bloccato):**

```sql
UPDATE vendite.promo_articoli
   SET valore_variazione = 25
 WHERE id = 42;  -- promo INIZIATA
-- ERROR:  P0001 — Promo articolo 42 gia' iniziata (valido_dal=<...> <= oggi=<...>): solo descrizione, valido_al e meta sono modificabili.
```

**5) Chiusura anticipata di promo INIZIATA (pattern data-driven):**

```sql
-- Imposto valido_al = oggi: la promo e' gia' applicata oggi
-- (semantica "ultimo giorno incluso") e domani entra in SCADUTA.
UPDATE vendite.promo_articoli
   SET valido_al = CURRENT_DATE
 WHERE id = 42;
-- ok (rimane in INIZIATA fino a fine giornata; passa in SCADUTA dal giorno successivo)
```

**6) UPDATE su promo SCADUTA (bloccato):**

```sql
UPDATE vendite.promo_articoli
   SET valido_al = CURRENT_DATE + 30
 WHERE id = 42;  -- promo con valido_al < oggi
-- ERROR:  P0001 — Promo articolo 42 scaduta (valido_al=<...> < oggi=<...>): non modificabile.
```

**7) UPDATE no-op su SCADUTA (ammesso):**

```sql
-- Nessun campo dominio cambia, solo audit refresh: il guard lo lascia
-- passare (es. tx_id manager dei trigger di sistema).
UPDATE vendite.promo_articoli
   SET descrizione = descrizione
 WHERE id = 42;  -- promo SCADUTA
-- ok
```

---

### Coerenza con lo snapshot pricing v5

Una promo gia' applicata su righe `commesse_attivita` lascia traccia
permanente nello **snapshot pricing v5** tramite la FK
`commesse_attivita.promo_id` + le colonne `prezzo_base_snapshot`,
`origine_prezzo`, etc. Il guard tutela questa traccia:

* **INIZIATA**: cambiare `tipo_variazione`/`valore_variazione`/`articolo`
  altererebbe la formula gia' applicata sulle righe attive del giorno.
* **SCADUTA**: cambiare qualunque campo dominio retroagirebbe sulla
  storia delle righe gia' chiuse che riferiscono la promo via FK.

Lo snapshot pricing in se' resta **frozen** (i valori puntuali non
vengono riletti dalla promo a posteriori), ma la coerenza fra
"promo sorgente" e "snapshot derivato" e' parte del contratto
applicativo del modello v5.

---

### Note operative

* **Single trigger per INSERT + UPDATE**: dispatch via `TG_OP`. Pattern
  diverso dai gemelli listini-versioni/contratti che usano
  `BEFORE UPDATE OF stato` perche' qui non c'e' colonna stato e la
  regola e' la stessa per le due operazioni.
* **Defense-in-depth**: il backend `apps.vendite.services.promo_articoli_service.PromoArticoliService` applica le stesse regole a livello applicativo. Il guard DB garantisce uniformita' anche per UPDATE diretti SQL e script di manutenzione.
* **Audit-safe**: il confronto su SCADUTA esclude `data_update`/`user_update`/`tx_id`. Gli UPDATE che toccano solo audit (es. dovuti al trigger `dbops.trgfn_tx_id_managed`) non vengono bloccati.
* **Nessuna clausola `WHEN`** sul trigger: la protezione contro falsi positivi e' interna alla fn (`IS DISTINCT FROM` per ogni colonna confrontata).
* **Pattern data-driven puro**: e' la variante "senza colonna stato" del pattern documentato in [linee-guida-sql §7c](/linee-guida-sql). I gemelli VARCHAR/FK trattano stato esplicito + finestra; qui la finestra **e'** lo stato.

---

{% include-markdown "signature-core.md" %}

---
