{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_righe_comp_guard_immutabilita_v5.md" %}
# ⚙️ Funzione `trgfn_listini_righe_comp_guard_immutabilita_v5`

```sql
CREATE FUNCTION trgfn_listini_righe_comp_guard_immutabilita_v5()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_righe_comp_guard_immutabilita_v5()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: BEFORE INS/UPD/DEL su listini_righe_componenti — immutabilita' v5.
--   Pattern listini: INSERT solo in versione BOZZA, UPDATE campi core
--   bloccato in versione non-BOZZA, DELETE sempre bloccato.
--   Il check periodo usa valido_dal/valido_al: validita e' STORED generated,
--   non disponibile nei BEFORE trigger (D-OPEN-1).
DECLARE
    v_stato   vendite.listini_versioni.stato%TYPE;
    v_riga_id vendite.listini_righe_componenti.id%TYPE;
BEGIN
    v_riga_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;

    -- DELETE bloccato: usare attivo=FALSE
    IF TG_OP = 'DELETE' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME, 'E_RIGA_LISTINO_VERSIONE_CHIUSA',
            jsonb_build_object(
                'operazione', 'DELETE',
                'hint',       'Usare attivo=FALSE per disattivare la riga.',
                'riga_id',    v_riga_id
            ),
            NULL::uuid,
            'DELETE', v_riga_id::text, 'PROTETTA'
        );
    END IF;

    -- Legge stato versione
    SELECT lv.stato INTO v_stato
      FROM vendite.listini_versioni lv
     WHERE lv.id = NEW.listino_versione_id;

    -- INSERT: solo in versione BOZZA
    IF TG_OP = 'INSERT' AND COALESCE(v_stato, 'BOZZA') <> 'BOZZA' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME, 'E_RIGA_LISTINO_VERSIONE_CHIUSA',
            jsonb_build_object(
                'operazione',         'INSERT',
                'stato_versione',     v_stato,
                'listino_versione_id', NEW.listino_versione_id
            ),
            NULL::uuid,
            'INSERT', v_riga_id::text, v_stato
        );
    END IF;

    -- UPDATE campi core: bloccato se versione non BOZZA.
    -- Il periodo e' identificato da valido_dal/valido_al (non da validita,
    -- che e' STORED generated e non e' visibile nei BEFORE trigger).
    IF TG_OP = 'UPDATE' AND COALESCE(v_stato, 'BOZZA') <> 'BOZZA' THEN
        IF NEW.prezzo    IS DISTINCT FROM OLD.prezzo
           OR NEW.iva_id    IS DISTINCT FROM OLD.iva_id
           OR NEW.valido_dal IS DISTINCT FROM OLD.valido_dal
           OR NEW.valido_al  IS DISTINCT FROM OLD.valido_al
        THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', TG_NAME, 'E_RIGA_LISTINO_VERSIONE_CHIUSA',
                jsonb_build_object(
                    'operazione',         'UPDATE_CAMPI_CORE',
                    'stato_versione',     v_stato,
                    'listino_versione_id', NEW.listino_versione_id,
                    'riga_id',            NEW.id
                ),
                NULL::uuid,
                'UPDATE', NEW.id::text, v_stato
            );
        END IF;
    END IF;

    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_righe_comp_guard_immutabilita_v5()
IS 'Trigger BEFORE INS/UPD/DEL su listini_righe_componenti: immutabilita'' v5. DELETE sempre bloccato (usare attivo=FALSE). INSERT solo in BOZZA. UPDATE prezzo/iva_id/valido_dal/valido_al bloccato in non-BOZZA. Raise E_RIGA_LISTINO_VERSIONE_CHIUSA (362). rev 2026-05-14.';
```

</div>

---
{% include-markdown "signature-core.md" %}
