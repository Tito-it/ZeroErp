## 📘 Documentazione Concettuale – Funzione `documenti.fn_pubblica_template_documento_versione()`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
> [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
> Approfondimento funzioni / trigger:
> [documenti.trgfn_template_documenti_versioni_protect_pubblicata](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_protect_pubblicata)
> [documenti.trgfn_template_documenti_versioni_block_delete](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_block_delete)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

### 🎯 Scopo Principale

(latest review 06-05-2026)

`documenti.fn_pubblica_template_documento_versione(p_versione_id, p_valido_dal, p_valido_al)`
è un **endpoint atomico DB** per **pubblicare una versione BOZZA** di un template documento.
In una singola transazione:

1. **valida** i parametri di input e lo stato della versione target,
2. **chiude e rende OBSOLETE** le versioni PUBBLICATE dello stesso template che si
   sovrappongono temporalmente al nuovo intervallo (`valido_dal` / `valido_al`),
3. **pubblica** la versione target portandola da `BOZZA` a `PUBBLICATA`.

Restituisce una riga con `versione_id`, `template_documento_id` e `versioni_obsolete`
(conteggio delle versioni PUBBLICATE precedenti che sono state chiuse).

---

### Firma

| Parametro | Tipo | Default | Significato |
|---|---|---|---|
| `p_versione_id` | `bigint` | — | PK della versione da pubblicare. Deve essere > 0. |
| `p_valido_dal` | `date` | — | Data inizio validità della versione pubblicata. Obbligatoria. |
| `p_valido_al` | `date` | `NULL` | Data fine validità (inclusa). `NULL` = versione aperta (nessuna scadenza). Se valorizzato non può precedere `p_valido_dal`. |
| **Ritorno** | `RETURNS TABLE` | — | `versione_id bigint`, `template_documento_id bigint`, `versioni_obsolete integer` |

---

### Regole applicate

| Operazione | Pre-condizione | Esito |
|---|---|---|
| `p_versione_id NULL o <= 0` | — | **Raise** `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` |
| `p_valido_dal NULL` | — | **Raise** `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` |
| `p_valido_al < p_valido_dal` | `p_valido_al IS NOT NULL` | **Raise** `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` |
| Versione non trovata | `p_versione_id` non esiste in `template_documenti_versioni` | **Raise** `E_DOCUMENTI_VERSIONE_NOT_FOUND` |
| Stato non BOZZA | `stato IN ('PUBBLICATA', 'OBSOLETA')` | **Raise** `E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO` |
| Overlap con versioni PUBBLICATE precedenti | esistono versioni `PUBBLICATA` + `attivo IS TRUE` con `valido_dal < p_valido_dal` e range sovrapposto | Chiusura atomica (doppio UPDATE: stato → OBSOLETA, poi `valido_al = p_valido_dal - 1`) |
| Path felice | tutto OK | `stato = 'PUBBLICATA'`, `valido_dal / valido_al` aggiornati; ritorna riga risultato |
| Race condition finale | la versione target non è più BOZZA alla fase finale (bypass lock improbabile) | **Raise** `E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO` |

---

### Logica operativa

1. **Guard parametri di input**: `versione_id > 0`, `valido_dal IS NOT NULL`,
   `valido_al >= valido_dal` (se valorizzato). Fail-fast con `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO`.
2. **`SELECT ... FOR UPDATE`** sulla versione target: lock pessimistico + lettura
   `template_documento_id` e `stato`. Se non trovata → `E_DOCUMENTI_VERSIONE_NOT_FOUND`.
3. **Guard stato BOZZA**: se `stato != 'BOZZA'` → `E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO`.
4. **Lock ordinato su tutte le versioni del template** (`ORDER BY v.id FOR UPDATE`):
   serializza pubblicazioni concorrenti sullo stesso template, evitando deadlock.
5. **Ricerca versioni da chiudere** (sub-query con `FOR UPDATE`):
   versioni `PUBBLICATA + attivo IS TRUE` con `valido_dal < p_valido_dal`
   il cui `validita` si sovrappone a `daterange(p_valido_dal, COALESCE(p_valido_al, 'infinity'), '[]')`.
6. **Conteggio versioni da chiudere**: `v_closed_count = COALESCE(array_length(v_closed_ids, 1), 0)`,
   calcolato immediatamente sull'array (non via `GET DIAGNOSTICS`).
7. **Chiusura versioni sovrapposte** (se `v_closed_count > 0`) — doppio UPDATE obbligato:
   - **Step 1** `SET stato = 'OBSOLETA'` → la colonna `stato` **non** è nell'`UPDATE OF` del trigger
     `trgfn_template_documenti_versioni_protect_pubblicata` (guard A1), quindi non viene bloccato.
   - **Step 2** `SET valido_al = p_valido_dal - 1` → ora `OLD.stato = 'OBSOLETA'`, il trigger
     guard A1 non scatta (controlla `OLD.stato = 'PUBBLICATA'`).
   `validita` si ricalcola da sola ad ogni UPDATE: e' una colonna generata.
8. **Pubblicazione versione target**: `SET stato = 'PUBBLICATA', valido_dal = p_valido_dal, valido_al = p_valido_al`.
   La condizione `AND stato = 'BOZZA'` nell'UPDATE è una difesa ulteriore contro race concorrenti.
9. **`IF NOT FOUND`** dopo la pubblicazione: safety net per scenari eccezionali di bypass lock.
10. **`RETURN NEXT`** con `versione_id`, `template_documento_id`, `versioni_obsolete`.

I trigger di sistema (`audit_data_user_generic`, `tx_id_managed`, `storico_generic`) e la colonna
generata `validita` gestiscono autonomamente audit, tx_id, daterange e storicizzazione.
La funzione non duplica nessuna di queste responsabilità.

---

### Errori sollevati

| Codice | id | Quando |
|---|---|---|
| `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` | 430 | `versione_id` NULL/<=0, `valido_dal` NULL, oppure `valido_al < valido_dal` |
| `E_DOCUMENTI_VERSIONE_NOT_FOUND` | 431 | `p_versione_id` non esiste in `documenti.template_documenti_versioni` |
| `E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO` | 432 | la versione non è in stato BOZZA (già PUBBLICATA o OBSOLETA), oppure race condition finale |

Tutti i raise passano da `script.fn_log_and_raise_error('documenti', 'fn_pubblica_template_documento_versione', ...)`
con contesto JSONB diagnostico. SQLSTATE `P0001`.

---

### Concorrenza

- **Primo `SELECT FOR UPDATE`** sulla versione target: blocca la riga specifica fin dall'inizio,
  rendendo sicure le validazioni successive di stato.
- **Lock ordinato** su tutte le versioni del template (`ORDER BY v.id FOR UPDATE`):
  serializza due pubblicazioni concorrenti sullo stesso template. L'ordinamento per `id`
  garantisce acquisizione dei lock nello stesso ordine, prevenendo deadlock.
- **Sub-query con `FOR UPDATE`** sulle versioni da chiudere: blocca le righe PUBBLICATE
  candidate alla chiusura per l'intera durata della TX.
- **Vincolo `EXCLUDE USING gist`** (`ex_template_documenti_versioni_no_overlap_pubblicata`):
  guardrail finale contro overlap residui o race non coperti dal lock applicativo.
  Si attiva solo per versioni `attivo IS TRUE AND stato = 'PUBBLICATA'`.

---

### Esempi

**1) Pubblicazione senza scadenza (versione aperta):**

```sql
SELECT * FROM documenti.fn_pubblica_template_documento_versione(
    42,                          -- p_versione_id (BOZZA)
    '2026-05-01'::date,          -- p_valido_dal
    NULL                         -- p_valido_al = aperta
);
-- versione_id | template_documento_id | versioni_obsolete
--          42 |                    10 |                 0
```

**2) Pubblicazione che chiude automaticamente una versione precedente sovrapposta:**

```sql
-- Esiste: versione 38, PUBBLICATA, valido_dal=2026-01-01, valido_al=NULL
SELECT * FROM documenti.fn_pubblica_template_documento_versione(
    42,
    '2026-05-01'::date,
    NULL
);
-- versione_id | template_documento_id | versioni_obsolete
--          42 |                    10 |                 1
-- La versione 38 diventa OBSOLETA con valido_al = 2026-04-30.
```

**3) Versione già pubblicata (errore):**

```sql
SELECT * FROM documenti.fn_pubblica_template_documento_versione(38, '2026-06-01', NULL);
-- ERROR: P0001 — La versione template 38 non puo' essere pubblicata:
-- stato attuale 'PUBBLICATA', atteso BOZZA.
```

**4) Data fine precedente a data inizio (errore):**

```sql
SELECT * FROM documenti.fn_pubblica_template_documento_versione(
    42, '2026-05-01'::date, '2026-04-30'::date
);
-- ERROR: P0001 — Parametro non valido per la pubblicazione della versione template:
-- valido_al non puo' precedere valido_dal.
```

---

### Note operative

- **Atomicità garantita**: la chiusura delle versioni precedenti e la pubblicazione della nuova
  avvengono nella stessa transazione. In caso di errore su qualsiasi step la TX fa rollback completo.
- **Doppio UPDATE necessario**: il trigger guard A1
  (`trgfn_template_documenti_versioni_protect_pubblicata`) blocca `UPDATE OF valido_al`
  quando `OLD.stato = 'PUBBLICATA'`. La sequenza *stato → OBSOLETA* poi *valido_al = p_valido_dal - 1*
  è l'unico percorso per chiudere una versione pubblicata senza bypassare il guard.
- **Filtro `attivo IS TRUE` sulle versioni da chiudere**: allineato al vincolo EXCLUDE GIST
  che opera solo su `attivo IS TRUE AND stato = 'PUBBLICATA'`. Versioni disattivate
  non rientrano nel vincolo e non devono essere chiuse da questa funzione.
- **`versioni_obsolete` nel risultato**: utile per il backend/log per tracciare quante versioni
  precedenti sono state chiuse implicitamente, senza richiedere una query separata.
- **Nessuna auto-incremento versione**: questa funzione aggiorna solo stato e date di validità.
  Il numero di versione (`versione`) è immutabile una volta assegnato (protetto dal trigger guard A1).

---

### Verifica e test

- Nessun test pgTAP ancora creato. I casi da coprire sono:
  - Happy path senza versioni sovrapposte (`versioni_obsolete = 0`).
  - Happy path con una o più versioni PUBBLICATE che vengono chiuse.
  - Errore `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` (versione_id <= 0, valido_dal NULL, valido_al < valido_dal).
  - Errore `E_DOCUMENTI_VERSIONE_NOT_FOUND` (id inesistente).
  - Errore `E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO` (versione già PUBBLICATA o OBSOLETA).

---

{% include-markdown "signature-core.md" %}

---
