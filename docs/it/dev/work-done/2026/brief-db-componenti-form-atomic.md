# Brief DB — Form atomic CASO A: rollback opzione A relaxed + preview/overrides JSONB

**Data:** 2026-05-12
**Branch:** `dev/db-tid`
**Priorità:** alta — sostituisce opzione A relaxed (2026-05-12 mattina)
**Riferimento:** [refactor-componenti.md](refactor-componenti.md) §8 (decisioni di dominio
da aggiornare) + [brief-db-componenti-relaxed-override.md](brief-db-componenti-relaxed-override.md)
(da deprecare)

---

## Sintomo / motivazione

L'opzione A relaxed (commit 38fbd358) introduce `prezzo_unitario NULL` come
stato intermedio "pending valorizzazione manuale". Il NULL si propaga ovunque
nel modello: trigger `ricalcola_padre`, `ricalcola_riepilogo_iva` (bug
emerso oggi), `ricalcola_totali`, viste, report futuri.

**Decisione di dominio aggiornata 2026-05-12 pomeriggio**: il modello DB
non ammette più prezzo NULL su `*_righe_componenti`. Il caso "manca
listino" è gestito a livello UX nel **form atomic**: il drawer riga
mostra in anteprima i componenti con prezzi suggeriti (o vuoti),
l'operatore valorizza tutto PRIMA del save, il BE crea riga + componenti
in transazione atomica con prezzi sempre completi.

## Modifiche DB richieste

### 1. Rollback opzione A relaxed (cross-dominio 4 sorgenti)

Per ogni `<sorgente> ∈ {preventivi, ordini, contratti, ddt}`:

**1a. Ripristina NOT NULL su `prezzo_unitario`**:

```sql
ALTER TABLE vendite.<sorgente>_righe_componenti
    ALTER COLUMN prezzo_unitario SET NOT NULL;

-- Anche su riga padre (solo preventivi + ordini che erano stati modificati):
ALTER TABLE vendite.preventivi_righe
    ALTER COLUMN prezzo_unitario SET NOT NULL;
ALTER TABLE vendite.ordini_righe
    ALTER COLUMN prezzo_unitario SET NOT NULL;
```

**1b. Ripristina CHECK `<> 0` (no `IS NULL OR`)**:

```sql
ALTER TABLE vendite.<sorgente>_righe_componenti
    DROP CONSTRAINT chk_<sorgente>_righe_comp_prezzo_nonneg;
ALTER TABLE vendite.<sorgente>_righe_componenti
    ADD CONSTRAINT chk_<sorgente>_righe_comp_prezzo_nonneg
    CHECK (prezzo_unitario <> 0);
```

**1c. Rimuovi parametro `p_force_manuale` dalle 4 fn init**:

```sql
CREATE OR REPLACE FUNCTION vendite.fn_<sorgente>_riga_componenti_init(
    p_riga_id bigint,
    p_emittente_sr_id bigint,
    p_data_riferimento date,
    p_componenti_overrides jsonb DEFAULT NULL   -- NUOVO (al posto di p_force_manuale)
) RETURNS integer ...
```

Vedi §2 sotto per la nuova logica con overrides.

**1d. Trigger `script.trgfn_componenti_ricalcola_padre` torna a SUM standard**:

```sql
-- Rimuovi gestione NULL propagation introdotta in 20260512-12.
UPDATE vendite.<sorgente>_righe
   SET prezzo_unitario = COALESCE(
       (SELECT SUM(prezzo_unitario * coeff_qta_snapshot)
          FROM vendite.<sorgente>_righe_componenti
         WHERE riga_<sorgente>_id = v_riga_padre_id
           AND attivo IS TRUE),
       prezzo_unitario  -- mantiene il valore corrente se nessun componente
   )
 WHERE id = v_riga_padre_id;
```

**1e. Rimuovi guard `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`** dai 4
trigger `trgfn_<sorgente>_guard_transizione_*`: il caso "componenti pending"
non esiste più (atomic = mai prezzi NULL).

**1f. Rimuovi fix `fn_ricalcola_riepilogo_iva_preventivo` per NULL**
se è già stato applicato (probabilmente non ancora — bug appena trovato).

### 2. Nuove funzioni: preview + overrides

**2a. Fn preview componenti (4 sorgenti simmetriche)**:

```sql
CREATE OR REPLACE FUNCTION vendite.fn_<sorgente>_riga_componenti_preview(
    p_articolo_id     uuid,
    p_uom_id          bigint,
    p_quantita_padre  numeric,
    p_data_riferimento date,
    p_ba_id           bigint,
    p_utility_id      integer,
    p_emittente_sr_id bigint,
    p_classe_utenza_id integer DEFAULT NULL
) RETURNS TABLE (
    articolo_componente_id uuid,
    componente_id          uuid,
    componente_codice      varchar,
    componente_descrizione varchar,
    coeff_qta_snapshot     numeric,
    quantita_componente    numeric,   -- = coeff_qta * p_quantita_padre
    uom_id                 bigint,
    uom_codice             varchar,
    iva_id                 bigint,
    iva_codice             varchar,
    prezzo_suggerito       numeric,    -- NULL se resolver fail per questo componente
    origine_prezzo         varchar,    -- NULL se resolver fail
    resolver_error_reason  text        -- NULL se OK, dettaglio errore se fail
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_rec record;
    v_resolve record;
BEGIN
    -- Loop sui componenti BoM esposti del padre validi alla data
    FOR v_rec IN
        SELECT ac.id, ac.componente_id, ac.coeff_qta, a.codice, a.descrizione,
               a.uom_id AS componente_uom_id, a.iva_id AS componente_iva_id,
               um.codice AS uom_codice, iva.codice AS iva_codice
          FROM catalogo.articoli_componenti ac
          JOIN catalogo.articoli a ON a.id = ac.componente_id
          LEFT JOIN catalogo.unita_misura um ON um.id = a.uom_id
          LEFT JOIN config.iva iva ON iva.id = a.iva_id
         WHERE ac.prodotto_id = p_articolo_id
           AND ac.obbligatorio = TRUE
           AND ac.esposto_in_fattura = TRUE
           AND COALESCE(ac.attivo, TRUE) = TRUE
           AND ac.validita @> p_data_riferimento
    LOOP
        articolo_componente_id := v_rec.id;
        componente_id          := v_rec.componente_id;
        componente_codice      := v_rec.codice;
        componente_descrizione := v_rec.descrizione;
        coeff_qta_snapshot     := v_rec.coeff_qta;
        quantita_componente    := v_rec.coeff_qta * p_quantita_padre;
        uom_id                 := v_rec.componente_uom_id;
        uom_codice             := v_rec.uom_codice;
        iva_id                 := v_rec.componente_iva_id;
        iva_codice             := v_rec.iva_codice;

        BEGIN
            SELECT * INTO v_resolve
              FROM vendite.fn_resolve_prezzo_listino_v2(
                  v_rec.componente_id, v_rec.componente_uom_id,
                  p_data_riferimento, p_ba_id, p_utility_id,
                  p_emittente_sr_id, p_classe_utenza_id
              );
            prezzo_suggerito       := v_resolve.prezzo_finale;
            origine_prezzo         := v_resolve.origine;
            resolver_error_reason  := NULL;
        EXCEPTION WHEN SQLSTATE 'P0001' THEN
            GET STACKED DIAGNOSTICS resolver_error_reason = MESSAGE_TEXT;
            prezzo_suggerito := NULL;
            origine_prezzo   := NULL;
        END;

        RETURN NEXT;
    END LOOP;
END;
$$;

COMMENT ON FUNCTION vendite.fn_<sorgente>_riga_componenti_preview(...)
IS 'Preview componenti BoM CASO A per drawer riga (form atomic). Read-only, no side-effect. Per ogni componente esposto ritorna prezzo suggerito (NULL se resolver fail con motivazione in resolver_error_reason). Consumato dal FE per pre-popolare la sezione componenti del drawer riga, l''operatore valorizza eventuali NULL prima del save. Coerente con fn_resolve_prezzo_composito ma espone gli errori per singolo componente invece di sollevare.';
```

**2b. Fn init: nuovo parametro `p_componenti_overrides JSONB`**:

```sql
CREATE OR REPLACE FUNCTION vendite.fn_<sorgente>_riga_componenti_init(
    p_riga_id bigint,
    p_emittente_sr_id bigint,
    p_data_riferimento date,
    p_componenti_overrides jsonb DEFAULT NULL  -- mappa {componente_id_uuid: prezzo_numeric}
) RETURNS integer
```

Logica:
- Loop sui componenti BoM esposti (come oggi).
- Per ogni componente:
  - Se `p_componenti_overrides ? componente_id::text` → usa il prezzo
    dall'override, `origine_prezzo = 'MANUALE'`, `prezzo_resolver_context`
    include `{override: true, original_resolver_error: <reason>}`.
  - Altrimenti → resolver come oggi. Se P0001 → raise
    `E_DOC_COMPONENTE_LISTINO_MANCANTE` (path strict invariato — niente
    fallback prezzo=0, niente NULL).
- Validazione override:
  - Tutti i prezzi devono essere `<> 0` (CHECK invariante).
  - Solo i componenti esposti effettivi del padre alla data sono ammessi
    nell'override (altri sono ignorati con avviso log).

Esempio override:
```json
{
  "019d57c1-b2b2-7d3a-9ebb-421addc5f393": 75.00,
  "019d57c1-b2b2-7d3a-9ebb-aaaaaaaaaaaa": 12.50
}
```

### 3. Tabelle invariate (post-rollback)

Le tabelle `*_righe_componenti` restano come da migrations 20260511 (struttura
originale), con `prezzo_unitario NOT NULL` + `CHECK <> 0`.

## BE follow-up (a carico backend agent)

1. Repository: `preview_componenti_riga(articolo_id, uom_id, qty, ...)` chiama
   `fn_<sorgente>_riga_componenti_preview`. Ritorna lista di dict.
2. Repository: `init_componenti_riga(..., componenti_overrides=None)` passa
   JSONB alla fn DB.
3. Service `gestisci_riga`: accetta `componenti_overrides` nel payload riga
   (dict componente_id → prezzo). Passa a `init_componenti_riga`.
4. **Gating L1 sugli overrides** (defense-in-depth, identico al gating
   esistente per `prezzo_override_manuale` su prezzo riga padre):
   - Se `payload.componenti_overrides` non vuoto e l'operatore NON ha
     l'azione `prezzo_override_manuale` → raise
     `E_PRICING_OVERRIDE_NON_AUTORIZZATO` (esistente). Niente bypass via curl.
   - L'autorizzazione resta responsabilita' BE: la fn DB non conosce
     azioni di processo, accetta gli overrides senza ulteriori check.
5. Service: nuovo endpoint `preview_componenti_riga(preventivo_id, articolo_id, ...)`
   wrappa repo + restituisce shape FE-friendly.
6. API view: nuovo endpoint `POST /vendite/preventivi/{id}/righe/preview-componenti/`
   con payload `{articolo_id, uom_operativa_id, quantita}` → ritorna preview.
7. error_policies: rimuovere `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE` (non più sollevato).
8. Test BE: +preview, +override happy autorizzato, +override mancante →
   strict raise, +override fornito senza autorizzazione → 403.

## FE follow-up

1. Drawer riga in 2 step (visualizzati come accordion espandibile, no
   wizard rigido):
   - Step 1 (sempre): articolo + uom + qty + iva
   - Step 2 (solo se `articolo.is_composito` e BoM ha esposti): tabella
     componenti con prezzi precompilati dal preview, modificabili
2. **Gating L1 lato UI** (allineato BE):
   - Operatore con `prezzo_override_manuale` → input prezzo componente
     editabili (prezzo vuoto da inserire, o prezzo da listino sovrascrivibile)
   - Operatore senza override → input readonly. Se preview ritorna NULL
     su 1 o più componenti (resolver fail) → bottone Save disabled +
     banner "Listino mancante per [codice]: contatta il responsabile per
     configurarlo o richiedi l'autorizzazione `prezzo_override_manuale`"
3. `usePreventivoRigaComponenti` esteso o nuovo composable per preview
4. POST riga payload include `componenti_overrides` mappa (solo se
   operatore ha override e ha effettivamente modificato/inserito prezzi)
5. Rimuovi: i18n pending + badge "PENDING"/"in attesa" + banner pending +
   handler NULL nel panel

## Test pgtap consigliati

- `fn_<sorgente>_riga_componenti_preview` con resolver OK → tutti prezzi
  popolati + origine
- `fn_<sorgente>_riga_componenti_preview` con resolver fail su 1 componente
  → quella riga ha `prezzo_suggerito IS NULL` + `resolver_error_reason` popolato
- `fn_<sorgente>_riga_componenti_init` con override completo → tutti
  prezzi da override, origine MANUALE
- `fn_<sorgente>_riga_componenti_init` con override parziale + resolver
  OK su rimanenti → mix di MANUALE + resolver origini
- `fn_<sorgente>_riga_componenti_init` con override parziale + resolver
  fail su componente senza override → raise `E_DOC_COMPONENTE_LISTINO_MANCANTE`
- INSERT prezzo=0 → CHECK violato (regression)
- INSERT prezzo=NULL → NOT NULL violato (regression — rollback opzione A
  relaxed)

## Decisioni di dominio aggiornate (refactor-componenti.md §8)

Aggiornare §8.7 a:

> **Componente esposto DEVE avere prezzo non zero e non NULL** (CHECK <> 0
> + NOT NULL). Quando il pricing resolver non trova listino per un
> componente, il flusso UX e' atomic: il drawer riga mostra la preview con
> il prezzo vuoto/da inserire, l'operatore valorizza prima di salvare.
> Il BE accetta `componenti_overrides` nel payload `gestisci_riga`
> (mappa componente_id → prezzo) che la fn DB applica con
> `origine='MANUALE'`. Senza override per un componente con listino
> mancante: raise `E_DOC_COMPONENTE_LISTINO_MANCANTE` (path strict).

Rimuovere §8.8 (precedenza emittente preventivo > operatore resta
valida ma non riguarda direttamente il flusso atomic, va comunque
tenuta).

## Migrations attese (4 sorgenti × 6 step = 24 migrations? In bundle se possibile)

Pattern consigliato dal team DB:
- `20260512-NN..MM`: rollback opzione A relaxed (NOT NULL, CHECK, fn init senza
  p_force_manuale, guard senza pending, ricalcola_padre senza NULL propagation)
- `20260512-NN..MM`: nuove fn preview + fn init nuovo parametro overrides

Coordinarsi sul numerale incrementale.
