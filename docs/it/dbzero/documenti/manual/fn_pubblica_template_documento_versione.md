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
> [documenti.fn_guard_versione_contesto](/dbzero/documenti/funzioni/fn_guard_versione_contesto)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

### 🎯 Scopo Principale

(latest review 14-11-2026 — che cosa stampa dopo la pubblicazione: lo decide la validità)

`documenti.fn_pubblica_template_documento_versione(p_versione_id, p_valido_dal, p_versione_contesto, p_valido_al)`
è un **endpoint atomico DB** per **pubblicare una versione BOZZA** di un template documento.
In una singola transazione:

1. **valida** i parametri di input e lo stato della versione target,
   e che la versione legga la **forma dei dati** che il builder produce (rev 2026-09-30),
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
| `p_versione_contesto` | `integer` | — | La **forma dei dati** che il builder del backend produce per quel tipo di documento (la stessa costante da cui esce `_meta.context_version`). Obbligatoria, senza default: la versione si pubblica solo se `versione_contesto` coincide. |
| `p_valido_al` | `date` | `NULL` | Data fine validità (inclusa). `NULL` = versione aperta (nessuna scadenza). Che non preceda `p_valido_dal` lo verifica il guard comune delle date sull'UPDATE della versione (sotto). |
| **Ritorno** | `RETURNS TABLE` | — | `versione_id bigint`, `template_documento_id bigint`, `versioni_obsolete integer` |

---

### Regole applicate

| Operazione | Pre-condizione | Esito |
|---|---|---|
| `p_versione_id NULL o <= 0` | — | **Raise** `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` |
| `p_valido_dal NULL` | — | **Raise** `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` |
| `p_valido_al < p_valido_dal` | `p_valido_al IS NOT NULL` | **Raise** `E_DATA_AL_MINORE_DAL` (campo `valido_al`) dal guard comune `script.trgfn_guard_date_validita`, sull'UPDATE della versione target; le chiusure già fatte si annullano con la transazione |
| Versione non trovata | `p_versione_id` non esiste in `template_documenti_versioni` | **Raise** `E_DOCUMENTI_VERSIONE_NOT_FOUND` |
| Stato non BOZZA | `stato IN ('PUBBLICATA', 'OBSOLETA')` | **Raise** `E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO` |
| Forma dei dati diversa | `versione_contesto` della versione ≠ `p_versione_contesto` | **Raise** `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA` da `documenti.fn_guard_versione_contesto`, prima di chiudere qualunque altra versione |
| Forma dei dati non passata | `p_versione_contesto IS NULL` | **Raise** `E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE` (TECNICO) |
| Overlap con versioni PUBBLICATE precedenti | esistono versioni `PUBBLICATA` + `attivo IS TRUE` con `valido_dal < p_valido_dal` e range sovrapposto | Chiusura atomica (una scrittura sotto la porta: stato → OBSOLETA e `valido_al = p_valido_dal - 1`) |
| Path felice | tutto OK | `stato = 'PUBBLICATA'`, `valido_dal / valido_al` aggiornati; ritorna riga risultato |
| Race condition finale | la versione target non è più BOZZA alla fase finale (bypass lock improbabile) | **Raise** `E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO` |

---

### Logica operativa

1. **Guard parametri di input**: `versione_id > 0`, `valido_dal IS NOT NULL`.
   Fail-fast con `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO`. L'ordine delle due date
   **non** si giudica qui: ha una sede sola, il guard comune
   `script.trgfn_guard_date_validita`, che scatta sull'UPDATE del passo 8.
2. **`SELECT ... FOR UPDATE`** sulla versione target: lock pessimistico + lettura
   `template_documento_id` e `stato`. Se non trovata → `E_DOCUMENTI_VERSIONE_NOT_FOUND`.
3. **Guard stato BOZZA**: se `stato != 'BOZZA'` → `E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO`.
3-bis. **Il patto versione/forma dei dati** (rev 2026-09-30): `documenti.fn_guard_versione_contesto(p_versione_id, p_versione_contesto)`.
   Sta prima di ogni scrittura, quindi un rifiuto non lascia niente a metà. La riga è già sotto
   `FOR UPDATE`: la forma letta non cambia fino al commit. Una BOZZA può dichiarare una forma che il
   builder non produce ancora (è così che si prepara la versione successiva): il controllo è qui.
4. **Lock ordinato su tutte le versioni del template** (`ORDER BY v.id FOR UPDATE`):
   serializza pubblicazioni concorrenti sullo stesso template, evitando deadlock.
5. **Ricerca versioni da chiudere** (sub-query con `FOR UPDATE`):
   versioni `PUBBLICATA + attivo IS TRUE` con `valido_dal < p_valido_dal`
   il cui `validita` si sovrappone a `[p_valido_dal, oltre)`. Poiché queste versioni partono
   **prima** di `p_valido_dal`, si sovrappongono alla nuova se e solo se sono ancora aperte a
   `p_valido_dal`: `p_valido_al` non entra nel giudizio. ⚠️ Per questo la ricerca non costruisce
   un intervallo dai due parametri: con le date invertite quel costruttore solleverebbe un
   errore tecnico (`22000`) prima che l'UPDATE arrivi al guard comune.
6. **Conteggio versioni da chiudere**: `v_closed_count = COALESCE(array_length(v_closed_ids, 1), 0)`,
   calcolato immediatamente sull'array (non via `GET DIAGNOSTICS`).
7. **Chiusura versioni sovrapposte** (se `v_closed_count > 0`) — una scrittura sola, sotto la
   porta (dal 14-11-2026):
   - apre `zeroerp.allow_template_versione_chiusura_override` (`set_config(…, 'on', true)`);
   - `SET stato = 'OBSOLETA', valido_al = p_valido_dal - 1` sulle versioni scelte: il guard A1
     (`trgfn_template_documenti_versioni_protect_pubblicata`) protegge `PUBBLICATA` e `OBSOLETA`, e
     a porta aperta ammette solo questa forma (da `PUBBLICATA` a `OBSOLETA`, validità accorciata,
     nient'altro cambiato);
   - richiude la porta (`'off'`).
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
| `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` | 430 | `versione_id` NULL/<=0, oppure `valido_dal` NULL |
| `E_DATA_AL_MINORE_DAL` | — | `valido_al < valido_dal`: lo solleva il guard comune `script.trgfn_guard_date_validita` sull'UPDATE della versione, non la funzione |
| `E_DOCUMENTI_VERSIONE_NOT_FOUND` | 431 | `p_versione_id` non esiste in `documenti.template_documenti_versioni` |
| `E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO` | 432 | la versione non è in stato BOZZA (già PUBBLICATA o OBSOLETA), oppure race condition finale |
| `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA` | 1169 | la versione dichiara di leggere una forma dei dati diversa da `p_versione_contesto` (dal guard) |
| `E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE` | 1170 | `p_versione_contesto` NULL (dal guard, TECNICO) |

Tutti i raise della funzione passano da `script.fn_log_and_raise_error('documenti', 'fn_pubblica_template_documento_versione', ...)`
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
  Si attiva per le versioni `attivo IS TRUE` fuori bozza, `PUBBLICATA` o `OBSOLETA` (dal
  14-11-2026): una versione resa `OBSOLETA` qui continua a stampare fino al suo `valido_al`, quindi
  conta anche lei per «una sola versione stampabile per data».

### Che cosa stampa dopo la pubblicazione

(dal 14-11-2026)

La funzione rende `OBSOLETA` la versione precedente nel momento in cui pubblica, anche quando la
nuova parte da una data futura. Che cosa stampa lo decide la validità, non lo stato
([vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili)): la
precedente, chiusa a `p_valido_dal - 1`, stampa fino alla vigilia, e la nuova dal giorno di
partenza. È la decisione del 29-04-2026 (`work-done/sviluppo-documenti.md`, punto 51): la vecchia
resta in uso fino alla partenza della nuova.

---

### Esempi

**1) Pubblicazione senza scadenza (versione aperta):**

```sql
SELECT * FROM documenti.fn_pubblica_template_documento_versione(
    42,                          -- p_versione_id (BOZZA)
    '2026-05-01'::date,          -- p_valido_dal
    2,                           -- p_versione_contesto: la forma del builder
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
    2,
    NULL
);
-- versione_id | template_documento_id | versioni_obsolete
--          42 |                    10 |                 1
-- La versione 38 diventa OBSOLETA con valido_al = 2026-04-30.
```

**3) Versione già pubblicata (errore):**

```sql
SELECT * FROM documenti.fn_pubblica_template_documento_versione(38, '2026-06-01', 2, NULL);
-- ERROR: P0001 — La versione template 38 non puo' essere pubblicata:
-- stato attuale 'PUBBLICATA', atteso BOZZA.
```

**4) Data fine precedente a data inizio (errore):**

```sql
SELECT * FROM documenti.fn_pubblica_template_documento_versione(
    42, '2026-05-01'::date, 2, '2026-04-30'::date
);
-- ERROR: P0001 — E_DATA_AL_MINORE_DAL, dal guard comune delle date (campo valido_al).
-- Nessuna versione precedente resta chiusa: tutto si annulla.
```

**5) La versione legge una forma che il builder non produce (errore):**

```sql
-- La versione 42 dichiara versione_contesto = 2, il builder del documento e' alla forma 1
SELECT * FROM documenti.fn_pubblica_template_documento_versione(42, '2026-05-01'::date, 1, NULL);
-- ERROR: P0001 — E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA: «La versione … legge i dati nella
-- forma 2, ma il sistema li prepara nella forma 1 …». Nessuna versione e' stata toccata.
```

---

### Note operative

- **Atomicità garantita**: la chiusura delle versioni precedenti e la pubblicazione della nuova
  avvengono nella stessa transazione. In caso di errore su qualsiasi step la TX fa rollback completo.
- **La chiusura passa dalla porta**: il guard A1 rifiuta ogni modifica di una versione
  `PUBBLICATA` o `OBSOLETA`, stato compreso. L'unico percorso per chiudere una versione pubblicata
  è questa funzione, che apre `zeroerp.allow_template_versione_chiusura_override` per la sola
  scrittura di chiusura e la richiude subito. Fino al 14-11-2026 la chiusura erano due `UPDATE`
  (lo stato, poi la data quando lo stato `OBSOLETA` non era più protetto): con le `OBSOLETA`
  protette il secondo morirebbe.
- **Filtro `attivo IS TRUE` sulle versioni da chiudere**: allineato al vincolo EXCLUDE GIST
  che opera solo su `attivo IS TRUE` (stato `PUBBLICATA` o `OBSOLETA`). Versioni disattivate
  non rientrano nel vincolo e non devono essere chiuse da questa funzione.
- **`versioni_obsolete` nel risultato**: utile per il backend/log per tracciare quante versioni
  precedenti sono state chiuse implicitamente, senza richiedere una query separata.
- **Nessuna auto-incremento versione**: questa funzione aggiorna solo stato e date di validità.
  Il numero di versione (`versione`) è immutabile una volta assegnato (protetto dal trigger guard A1).

---

### Verifica e test

- `db/pgtap/documenti/test-fn-pubblica-template-documento-versione-v1.sql` copre:
  - date invertite → guard comune (`E_DATA_AL_MINORE_DAL`, campo `valido_al`), rifiuto atomico;
  - chiusura di una versione aperta anche quando la nuova ha una fine (`versioni_obsolete = 1`);
  - nessuna chiusura per una versione già finita prima dell'inizio della nuova (`versioni_obsolete = 0`);
  - forma dei dati diversa → `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA`, rifiuto atomico; forma NULL →
    `E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE`; una bozza preparata per la forma 2 si pubblica
    quando il builder la produce (test 8-11, rev 2026-09-30);
  - il vincolo e il registro coprono `PUBBLICATA` e `OBSOLETA`; con la nuova che parte domani oggi
    stampa la precedente, con la nuova che parte oggi stampa la nuova; una `OBSOLETA` allargata sopra
    la versione che la segue viola il vincolo (test 12-17, 2026-11-14).
- Casi ancora da coprire:
  - Errore `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` (versione_id <= 0, valido_dal NULL).
  - Errore `E_DOCUMENTI_VERSIONE_NOT_FOUND` (id inesistente).
  - Errore `E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO` (versione già PUBBLICATA o OBSOLETA).

---

{% include-markdown "signature-core.md" %}

---
