{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_guard_transizione_stato.md" %}
# ⚙️ Funzione `trgfn_contratti_guard_transizione_stato`

```sql
CREATE FUNCTION trgfn_contratti_guard_transizione_stato()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_guard_transizione_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: bloccare transizioni stato non ammesse sul workflow
-- contratti (DRAFT -> ATTIVO -> CESSATO).
-- Regola chiave: ATTIVO -> CESSATO ammessa solo se
-- valido_al < CURRENT_DATE. Coerente col job pgAgent
-- chiusura_scadenze_daily che soddisfa la condizione per
-- costruzione.
-- Lookup codice_interno per stabilita' a relabelling.
-- Il filtro WHEN del trigger garantisce che si entra solo
-- se OLD.stato e' DISTINCT da NEW.stato; non serve double-check.
DECLARE
    v_codice_da config.stati_doc_contratti.codice_interno%TYPE;
    v_codice_a  config.stati_doc_contratti.codice_interno%TYPE;
    v_ammessa   boolean := false;
BEGIN
    -- Risolve codice_interno OLD e NEW in una sola query (pivot
    -- via MAX(CASE...)). Riduce 2 round-trip a 1 sul catalog.
    SELECT
        max(CASE WHEN id = OLD.stato_doc_contratto_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_contratto_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_contratti
     WHERE id IN (OLD.stato_doc_contratto_id, NEW.stato_doc_contratto_id);

    -- Dispatch transizioni ammesse.
    IF v_codice_da = 'DRAFT' AND v_codice_a = 'ATTIVO' THEN
        v_ammessa := true;
    ELSIF v_codice_da = 'ATTIVO' AND v_codice_a = 'CESSATO' THEN
        -- Cessazione consentita solo a finestra gia' scaduta.
        -- Coerente col principio "le date comandano": evita
        -- stato CESSATO con validita' ancora aperta.
        v_ammessa := (NEW.valido_al IS NOT NULL
                      AND NEW.valido_al < CURRENT_DATE);
    END IF;
    -- Tutte le altre transizioni vietate:
    --   DRAFT -> CESSATO  : la bozza si cancella
    --   ATTIVO -> DRAFT   : irreversibile
    --   CESSATO -> *      : terminale
    --   * -> SOSPESO / SOSPESO -> *: non in scope ora

    IF NOT v_ammessa THEN
        -- NEW.tx_id disponibile dal 20260426-09 (ALTER ADD).
        -- Popolato automaticamente dal trigger
        -- dbops.trgfn_tx_id_managed registrato via automation.
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA',
            jsonb_build_object(
                'contratto_id', NEW.id,
                'numero',       NEW.numero,
                'stato_da',     v_codice_da,
                'stato_a',      v_codice_a,
                'valido_al',    NEW.valido_al
            ),
            NEW.tx_id,
            NEW.id::text,
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL'),
            coalesce(NEW.valido_al::text, 'NULL')
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_guard_transizione_stato()
IS 'Guard transizione stato contratto (FK con lookup codice_interno). Ammette DRAFT->ATTIVO e ATTIVO->CESSATO solo con valido_al<CURRENT_DATE. Raise E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA.';
```

---
{% include-markdown "signature-core.md" %}
