## 📘 Documentazione Concettuale – Funzione `catalogo.fn_duplica_componente_versione()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti)
> [catalogo.vw_articoli_componenti_dettaglio](/dbzero/catalogo/views/vw_articoli_componenti_dettaglio)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni / trigger:
> [catalogo.trgfn_articoli_componenti_block_modifica_struttura](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_block_modifica_struttura)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

### 🎯 Scopo Principale

(latest review 28-04-2026)

`catalogo.fn_duplica_componente_versione(p_articolo_id, p_componente_row_id, p_chiudi_al)`
e' un **endpoint atomico DB** per **duplicare la versione corrente** di un
componente di una distinta base (BoM). In una singola transazione:

1. **chiude** la riga sorgente impostando `valido_al = p_chiudi_al`
   (default: `CURRENT_DATE`),
2. **inserisce una nuova riga** con `valido_dal = p_chiudi_al + 1`,
   copiando `componente_id` + i campi di struttura + `meta` + `note_*`,
   forzando `attivo = true`.

Restituisce l'`id` (uuid) della nuova riga.

E' il pattern operativo "chiudi + apri nuova" della BoM versionata
(coerente con `trgfn_articoli_componenti_block_modifica_struttura()`):
permette al FE di proporre la chiusura della versione corrente e l'apertura
contestuale di una versione successiva con i parametri ereditati ed
eventualmente modificabili dopo.

---

### Firma

| Parametro | Tipo (`%TYPE`) | Default | Significato |
|---|---|---|---|
| `p_articolo_id` | `articoli_componenti.prodotto_id%TYPE` (uuid) | — | Articolo prodotto target. Guard di sicurezza: la riga sorgente deve appartenere a questo prodotto. |
| `p_componente_row_id` | `articoli_componenti.id%TYPE` (uuid) | — | PK della riga sorgente da duplicare. |
| `p_chiudi_al` | `articoli_componenti.valido_al%TYPE` (date) | `NULL` (= `CURRENT_DATE`) | Data di chiusura della sorgente. La nuova riga apre il giorno successivo. |
| **Ritorno** | `uuid` | — | `id` della nuova riga inserita. |

---

### Regole applicate

| Operazione | Pre-condizione | Esito |
|---|---|---|
| Parametri `NULL` | `p_articolo_id IS NULL OR p_componente_row_id IS NULL` | **Raise** `E_BOM_RIGA_NOT_FOUND` |
| Riga sorgente non trovata | `id` non esiste in `articoli_componenti` | **Raise** `E_BOM_RIGA_NOT_FOUND` |
| Mismatch articolo | `row.prodotto_id != p_articolo_id` | **Raise** `E_BOM_PRODOTTO_MISMATCH` |
| Sorgente gia' chiusa | `row.valido_al IS NOT NULL` | **Raise** `E_BOM_SORGENTE_GIA_CHIUSA` |
| `p_chiudi_al < row.valido_dal` | UPDATE valido_al violerebbe coerenza temporale | **Raise** `E_BOM_VALIDO_AL_INVALIDO` (propagato dal trigger `block_modifica_struttura`) |
| Overlap su nuova versione | esiste gia' una riga su `(prodotto_id, componente_id)` con range che intercetta `[p_chiudi_al + 1, ∞)` | **Raise** `E_BOM_VERSIONE_OVERLAP` |
| Path felice | tutto OK | UPDATE sorgente + INSERT nuova; ritorna `id` nuova |

---

### Logica operativa

1. **Default `p_chiudi_al`** → `COALESCE(p_chiudi_al, CURRENT_DATE)`.
2. **Guard parametri NULL** → fail-fast con `E_BOM_RIGA_NOT_FOUND`.
3. **Lock advisory** transazionale per `prodotto_id`:
   `pg_advisory_xact_lock(hashtext('catalogo.articoli_componenti.duplica:' || p_articolo_id::text))`.
   Serializza duplicazioni concorrenti sullo **stesso articolo**.
   Granularita' giusta perche' l'EXCLUDE GIST e' su `(prodotto_id, componente_id, validita)`:
   non serve scendere a `(prodotto, componente)`.
4. **`SELECT ... FOR UPDATE`** la riga sorgente per `id = p_componente_row_id`.
5. **Guard ordinati**:
   `NOT_FOUND` → `PRODOTTO_MISMATCH` → `SORGENTE_GIA_CHIUSA`.
6. **UPDATE** `valido_al = v_chiudi_al` sulla sorgente. Eventuali violazioni
   temporali (`v_chiudi_al < OLD.valido_dal`) vengono **intercettate dal trigger
   esistente** `trgfn_articoli_componenti_block_modifica_struttura` con codice
   `E_BOM_VALIDO_AL_INVALIDO` (388, gia' UI-friendly): la fn non duplica la guard.
7. **INSERT** nuova riga con:
   - `prodotto_id`, `componente_id` ereditati dalla sorgente,
   - struttura (`coeff_qta`, `partecipa_qta`, `obbligatorio`, `determina_qta_padre`,
     `esposto_in_fattura`) ereditata,
   - `meta`, `note_target_tipo`, `note_id` ereditati (la nota descrive il
     componente, condivisa fra versioni — non clonata),
   - `valido_dal = v_chiudi_al + 1` (gap obbligato dal canonicalize daterange:
     la sorgente chiusa ha `validita = [v_dal, v_chiudi_al + 1)`, la nuova
     deve partire dal giorno successivo per non urtare l'EXCLUDE),
   - `valido_al = NULL` (riga aperta),
   - `attivo = true` **forzato** (anche se sorgente era `attivo = false`):
     "duplica versione" implica nuova versione attiva.
8. **`EXCEPTION WHEN exclusion_violation`** sull'INSERT →
   `E_BOM_VERSIONE_OVERLAP`: scatta se sullo stesso couple esiste una riga
   futura nel range `[v_chiudi_al + 1, ∞)` (es. una versione gia' programmata).
9. **`RETURN v_new_id`**.

I trigger di sistema (`audit_data_user_generic`, `tx_id_managed`,
`set_validita`, `block_modifica_struttura`) gestiscono autonomamente audit,
tx_id, canonicalize daterange, immutabilita' della struttura. La fn non
duplica nessuna di queste responsabilita'.

---

### Errori sollevati

| Codice | id | Quando |
|---|---|---|
| `E_BOM_RIGA_NOT_FOUND` | 402 | parametri NULL oppure `p_componente_row_id` non esiste in `articoli_componenti` |
| `E_BOM_PRODOTTO_MISMATCH` | 403 | la riga esiste ma appartiene a un prodotto diverso da `p_articolo_id` (FE stale o errore chiamante) |
| `E_BOM_SORGENTE_GIA_CHIUSA` | 401 | `row.valido_al IS NOT NULL`: una riga storica non puo' essere duplicata, va selezionata la versione corrente |
| `E_BOM_VALIDO_AL_INVALIDO` | 388 | propagato dal trigger esistente `block_modifica_struttura` se `p_chiudi_al < row.valido_dal` |
| `E_BOM_VERSIONE_OVERLAP` | 400 | la nuova versione collide con una riga futura sullo stesso couple `(prodotto, componente)` |

Tutti i raise passano da `script.fn_log_and_raise_error('database', v_fn_name, ...)`
con contesto JSONB diagnostico (`riga_id`, `prodotto_id`, `componente_id`,
`valido_al`, `nuova_valido_dal`, ...). SQLSTATE `P0001`.

---

### Concorrenza

- **Lock advisory** transazionale (`pg_advisory_xact_lock`) per `prodotto_id`:
  due chiamate concorrenti sullo stesso articolo si serializzano automaticamente.
  Il lock viene rilasciato a fine TX (commit o rollback), mai sospeso.
- **`SELECT FOR UPDATE`** sulla riga sorgente: row-level lock pessimistico,
  sufficiente a difendere da UPDATE concorrenti su `valido_al` da altri
  callsite (anche fuori da questa fn) durante la TX.
- **EXCLUDE GIST** `ex_articoli_componenti_no_overlap`: ultima linea di
  difesa contro overlap, gestito via `EXCEPTION WHEN exclusion_violation`.

---

### Esempi

**1) Duplica oggi la versione corrente di un componente:**

```sql
-- BoM esistente: prodotto 'aaa...101', componente 'aaa...102',
-- valido_dal=2026-03-01, valido_al=NULL
SELECT catalogo.fn_duplica_componente_versione(
    'aaa...101'::uuid,         -- p_articolo_id
    'aaa...555'::uuid,         -- p_componente_row_id (PK riga)
    NULL                       -- p_chiudi_al = oggi (default)
);
-- Esito:
--   sorgente: valido_al = 2026-04-28 (oggi)
--   nuova:    valido_dal = 2026-04-29, valido_al=NULL, attivo=true
-- Ritorno: uuid della nuova riga.
```

**2) Chiusura programmata futura (nuova versione attiva da fra una settimana):**

```sql
SELECT catalogo.fn_duplica_componente_versione(
    'aaa...101'::uuid,
    'aaa...555'::uuid,
    (CURRENT_DATE + INTERVAL '7 days')::date
);
-- Esito:
--   sorgente: valido_al = oggi+7
--   nuova:    valido_dal = oggi+8, valido_al=NULL
```

**3) Riga sorgente gia' chiusa (errore chiamante):**

```sql
SELECT catalogo.fn_duplica_componente_versione(
    'aaa...101'::uuid,
    'aaa...777'::uuid,         -- riga con valido_al = 2026-02-15
    NULL
);
-- ERROR: P0001 — La riga sorgente della BoM e' gia' chiusa
-- (valido_al=2026-02-15): impossibile duplicarla.
```

**4) Overlap con versione futura programmata:**

```sql
-- Esiste gia': prodotto 'aaa...101', componente 'aaa...102',
-- valido_dal=2026-05-15, valido_al=NULL (versione futura).
-- Sorgente corrente: valido_dal=2026-03-01, valido_al=NULL.
SELECT catalogo.fn_duplica_componente_versione(
    'aaa...101'::uuid,
    'aaa...555'::uuid,
    (CURRENT_DATE + INTERVAL '30 days')::date  -- chiusura oltre 2026-05-15
);
-- ERROR: P0001 — La nuova versione del componente con
-- valido_dal=2026-05-29 si sovrappone a una versione esistente per
-- lo stesso prodotto/componente.
```

---

### Note operative

* **Atomicita' garantita**: l'intera operazione (UPDATE sorgente + INSERT
  nuova) e' in singola TX. In caso di errore qualunque step fallisce, la TX
  fa rollback completo: la sorgente NON resta chiusa "a meta'".
* **Pattern non implementato in CTE**: una `WITH ... INSERT` non sarebbe
  semanticamente sicura -- PostgreSQL non garantisce ordine di esecuzione
  fra sub-statement modificanti, l'INSERT potrebbe partire prima
  dell'UPDATE e urtare l'EXCLUDE.
* **Nessuna duplica delle note**: `note_target_tipo` e `note_id` puntano allo
  stesso record di `dbops.note` della sorgente -- la nota descrive il
  componente, non la versione specifica. Se il dominio richiedesse note
  per-versione, andrebbe rivisto a livello di modello (NON via guard fn).
* **`attivo = true` forzato**: la nuova riga non eredita lo stato `attivo`
  della sorgente. Decisione di dominio: "duplica versione" implica nuova
  versione attiva.
* **`p_chiudi_al = NULL` e' default operativo**: il flow tipico FE manda
  `NULL` (chiudi oggi). Il parametro esiste per chiusure programmate.
* **Race condition cross-session**: il lock advisory protegge da chiamate
  concorrenti di questa fn sullo stesso articolo. Una corsa fra `fn_duplica_*`
  e un INSERT diretto su `articoli_componenti` da un altro callsite e'
  comunque coperta dall'EXCLUDE GIST (defense-in-depth) -- la fn raise
  `E_BOM_VERSIONE_OVERLAP` invece di un IntegrityError generico.

---

### Verifica e test

- pgTAP: `db/pgtap/catalogo/test-fn-duplica-componente-versione-v1.sql`
  copre 4 scenari (happy x6 + sorgente_chiusa + non_esistente + prodotto_mismatch),
  per un totale di `plan(9)`.
- Lo scenario `E_BOM_VERSIONE_OVERLAP` non e' riproducibile in pgTAP single-session
  (l'EXCLUDE GIST blocca la pre-creazione della riga futura sullo stesso couple
  mentre la sorgente e' aperta): testato via code-review della clausola
  `EXCEPTION WHEN exclusion_violation` nella fn.

---

{% include-markdown "signature-core.md" %}

---
