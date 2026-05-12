# Brief DB — Opzione A relaxed: ammetti componenti BoM CASO A senza prezzo se operatore ha `prezzo_override_manuale`

**Data:** 2026-05-12
**Branch:** `dev/db-tid`
**Priorità:** alta — sblocca path UX §3.4.B (operatore valorizza prezzo manualmente quando manca listino)
**Riferimento:** [refactor-componenti.md](refactor-componenti.md) §8.7 (decisione 2026-05-12 va aggiornata) +
[brief-db-fn-log-and-raise-error-signature.md](brief-db-fn-log-and-raise-error-signature.md) (precedente)

---

## Sintomo / motivazione

L'opzione A strict (atterrata 2026-05-12) blocca l'init componenti CASO A
quando manca listino su un componente: solleva
`E_DOC_COMPONENTE_LISTINO_MANCANTE` (HTTP 422). L'operatore deve PRIMA
configurare il listino in catalogo e POI tornare al preventivo.

UX confermato non praticabile per:
- Operatori autorizzati a override manuale (`prezzo_override_manuale`)
  che vogliono concordare prezzo straordinario col cliente senza creare
  listino "fittizio" in catalogo
- Test plan §3.4.B (`sviluppo-listini-v5-test-ui.md`) presuppone
  "componente con prezzo vuoto, operatore digita manuale al volo"

Decisione di dominio aggiornata 2026-05-12: ammetti componenti pending
**solo se operatore ha azione `prezzo_override_manuale`**, altrimenti resta
comportamento strict (raise).

## Modifiche DB richieste (4 sorgenti simmetriche)

Per ogni `<sorgente> ∈ {preventivi, ordini, contratti, ddt}`:

### 1. CHECK `chk_<sorgente>_righe_comp_prezzo_nonneg` ammette NULL

```sql
ALTER TABLE vendite.<sorgente>_righe_componenti
    DROP CONSTRAINT chk_<sorgente>_righe_comp_prezzo_nonneg;

ALTER TABLE vendite.<sorgente>_righe_componenti
    ADD CONSTRAINT chk_<sorgente>_righe_comp_prezzo_nonneg
    CHECK (prezzo_unitario IS NULL OR prezzo_unitario <> 0);
```

Razionale: NULL = "pending valorizzazione operatore", `<> 0` resta
invariante di dominio per i prezzi valorizzati.

### 2. Fn init: nuovo parametro `p_force_manuale BOOLEAN DEFAULT FALSE`

```sql
CREATE OR REPLACE FUNCTION vendite.fn_<sorgente>_riga_componenti_init(
    p_riga_id bigint,
    p_emittente_sr_id bigint,
    p_data_riferimento date,
    p_force_manuale boolean DEFAULT FALSE   -- NUOVO
) RETURNS integer ...
```

Logica:

- `p_force_manuale = FALSE` (default): comportamento attuale invariato
  (raise `E_DOC_COMPONENTE_LISTINO_MANCANTE` su listino mancante).
- `p_force_manuale = TRUE`: catch P0001 dal resolver come prima, MA
  invece di raise, esegui INSERT fallback con:
  ```sql
  prezzo_unitario     = NULL,
  origine_prezzo      = 'MANUALE',
  prezzo_resolver_context = jsonb_build_object(
      'error',            'resolver_failed',
      'reason',           v_err_msg,        -- messaggio originale
      'emittente_sr_id',  p_emittente_sr_id,
      'data_riferimento', p_data_riferimento,
      'ba_id',            v_ba_id,
      'utility_id',       v_utility_id,
      'force_manuale',    TRUE
  )
  ```
- Default backward-compat garantito (caller esistenti non si rompono).

### 3. Trigger `script.trgfn_componenti_ricalcola_padre`: gestione NULL

```sql
-- Pseudo-codice della logica nuova:
WITH componenti_attivi AS (
    SELECT prezzo_unitario, coeff_qta_snapshot
      FROM vendite.<sorgente>_righe_componenti
     WHERE riga_<sorgente>_id = v_riga_padre_id
       AND attivo IS TRUE
)
SELECT
    CASE
        WHEN COUNT(*) FILTER (WHERE prezzo_unitario IS NULL) > 0
            THEN NULL  -- almeno 1 pending → padre NULL
        ELSE SUM(prezzo_unitario * coeff_qta_snapshot)
    END
  INTO v_nuovo_prezzo
  FROM componenti_attivi;

UPDATE vendite.<sorgente>_righe SET prezzo_unitario = v_nuovo_prezzo ...;
```

Vincolo `vendite.<sorgente>_righe.prezzo_unitario` deve già ammettere
NULL? Verifica. Se non lo ammette, va modificato simmetricamente.

### 4. Trigger `trgfn_<sorgente>_guard_transizione_approvazione`

Estendi il check (già fatto su componenti PENDING in approvazione 2026-05-11)
con un NUOVO check: blocca transizione ad `ACCETTATO` se esiste anche
solo 1 componente attivo con `prezzo_unitario IS NULL`. Codice errore
nuovo:

```sql
-- Pseudo:
IF EXISTS (
    SELECT 1
      FROM vendite.<sorgente>_righe_componenti prc
     WHERE prc.riga_<sorgente>_id IN (SELECT id FROM vendite.<sorgente>_righe WHERE <sorgente>_id = NEW.id AND attivo)
       AND prc.attivo
       AND prc.prezzo_unitario IS NULL
) THEN
    PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE',
        jsonb_build_object('<sorgente>_id', NEW.id, 'hint', 'Valorizzare prezzo dei componenti pending prima di accettare.'),
        NULL::uuid,
        ARRAY[NEW.id::text]
    );
END IF;
```

## Verifica fn DB cross-dominio

Le 4 fn init (`fn_preventivo` / `fn_ordine` / `fn_contratto` / `fn_ddt`
`_riga_componenti_init`) sono simmetriche. Stesso pattern di modifica.

## BE / FE follow-up (a carico backend agent post-fix DB)

Lato BE:
1. `gestisci_riga` chiama `repo.init_componenti_riga(p_force_manuale=...)` dove
   `p_force_manuale = PermissionResolver.is_action_allowed(auth_user, 'prezzo_override_manuale')`
2. Repository: `init_componenti_riga` accetta nuovo kwarg `force_manuale`
3. `error_policies.py`: registrare `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE` (HTTP 409, `show_error_banner`)

Lato FE:
1. Sezione componenti drawer: render `prezzo IS NULL` come InputNumber con
   placeholder "Da valorizzare", badge warn "PENDING" accanto
2. Padre prezzo display: "Calcolato dai componenti (in attesa)" se ci sono NULL
3. i18n key nuova `preventivi.componenti_pending_valorizzazione`
4. Banner inline drawer: "N componenti senza prezzo: valorizzare prima di emettere"
5. Transizione ACCETTATO intercetta `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`

## Decisioni di dominio aggiornate

Aggiornare `refactor-componenti.md` §8.7 da:

> **Componente esposto DEVE avere prezzo non zero** (CHECK <> 0)

a:

> **Componente esposto DEVE avere prezzo non zero, MA può essere NULL se
> in attesa di valorizzazione manuale autorizzata.**
> CHECK: `(prezzo_unitario IS NULL OR prezzo_unitario <> 0)`.
> NULL ammesso solo via fn init con `p_force_manuale=TRUE`, attivato dal
> service BE quando l'operatore ha l'azione `prezzo_override_manuale`.
> Il preventivo non può transitare a ACCETTATO se ha componenti con
> prezzo NULL.

## Test pgtap consigliati

- `fn_<sorgente>_riga_componenti_init(force_manuale=FALSE, listino mancante)` → raise E_DOC_COMPONENTE_LISTINO_MANCANTE (regression)
- `fn_<sorgente>_riga_componenti_init(force_manuale=TRUE, listino mancante)` → INSERT con prezzo NULL + origine MANUALE
- `fn_<sorgente>_riga_componenti_init(force_manuale=TRUE, listino presente)` → resolver normale, prezzo da listino + origine resolver
- INSERT prezzo=0 → CHECK violato (regression)
- INSERT prezzo=NULL → OK (nuovo)
- UPDATE prezzo da NULL a valore valido → OK + trigger ricalcola padre
- Transizione ACCETTATO con 1 componente prezzo NULL → raise E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE
