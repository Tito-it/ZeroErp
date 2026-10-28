{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_versioni_guard_transizione_stato.md" %}
# ⚙️ Funzione `trgfn_listini_versioni_guard_transizione_stato`

```sql
CREATE FUNCTION trgfn_listini_versioni_guard_transizione_stato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_versioni_guard_transizione_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: bloccare transizioni di stato non ammesse sul
-- workflow versione listino (BOZZA -> ATTIVA -> CHIUSA).
-- Regola chiave: ATTIVA -> CHIUSA richiede valido_al scaduto
-- (valido_al IS NOT NULL AND valido_al < CURRENT_DATE).
-- La precondizione temporale rende impossibile per costruzione
-- lo stato incoerente CHIUSA con valido_al NULL e forza il
-- pattern "PATCH valido_al" -> chiusura automatica (job).
-- Lo stesso trigger e' attraversato dal job notturno di
-- close: quando l'UPDATE parte da stato=ATTIVA e valido_al
-- e' gia' scaduto, il guard lo lascia passare naturalmente.
DECLARE
    v_old vendite.listini_versioni.stato%TYPE := OLD.stato;
    v_new vendite.listini_versioni.stato%TYPE := NEW.stato;
    v_ammessa boolean := false;
BEGIN
    -- Nessun cambio stato: niente da validare.
    IF v_old IS NOT DISTINCT FROM v_new THEN
        RETURN NEW;
    END IF;

    -- Dispatch transizioni ammesse (workflow piatto, 3 stati).
    IF v_old = 'BOZZA' AND v_new = 'ATTIVA' THEN
        v_ammessa := true;
    ELSIF v_old = 'ATTIVA' AND v_new = 'CHIUSA' THEN
        -- Chiusura consentita solo a finestra gia' scaduta.
        -- Evita incoerenza CHIUSA + valido_al NULL e uniforma
        -- il path utente (PATCH valido_al) con il job notturno.
        v_ammessa := (NEW.valido_al IS NOT NULL
                      AND NEW.valido_al < (SELECT script.fn_data_operativa()));
    END IF;
    -- Tutte le altre transizioni sono vietate:
    --   BOZZA  -> CHIUSA : bozza si cancella
    --   ATTIVA -> BOZZA  : immutabile all'indietro
    --   CHIUSA -> *      : stato terminale
    --   *      -> BOZZA  : vietato salvo no-op

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_VERSIONE_STATO_TRANSIZIONE_INVALIDA',
            jsonb_build_object(
                'versione_id', NEW.id,
                'listino_id',  NEW.listino_id,
                'stato_da',    v_old,
                'stato_a',     v_new,
                'valido_al',   NEW.valido_al
            ),
            NEW.tx_id,
            NEW.id::text,
            v_old::text,
            v_new::text,
            COALESCE(NEW.valido_al::text, 'NULL')
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_versioni_guard_transizione_stato()
IS 'Guard transizione stato versione listino: ammette BOZZA->ATTIVA e ATTIVA->CHIUSA solo con valido_al<CURRENT_DATE. Raise E_VERSIONE_STATO_TRANSIZIONE_INVALIDA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
