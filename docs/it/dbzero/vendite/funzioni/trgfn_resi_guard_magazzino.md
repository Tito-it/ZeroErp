# ⚙️ Funzione `trgfn_resi_guard_magazzino`

```sql
CREATE FUNCTION trgfn_resi_guard_magazzino()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_guard_magazzino()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: le regole del magazzino di rientro che un CHECK non vede (D-3b-a):
--   immutabile fuori bozza, e dell'emittente del reso.
DECLARE
    v_stato_old config.stati_doc_reso.codice_interno%TYPE;
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.magazzino_id IS NOT DISTINCT FROM OLD.magazzino_id
       AND NEW.emittente_fiscale_id IS NOT DISTINCT FROM OLD.emittente_fiscale_id THEN
        RETURN NEW;
    END IF;

    -- 1. Immutabile fuori bozza: lo stato VECCHIO decide (l'UPDATE che
    --    conferma e sceglie il magazzino insieme resta lecito).
    IF TG_OP = 'UPDATE' AND NEW.magazzino_id IS DISTINCT FROM OLD.magazzino_id THEN
        SELECT s.codice_interno INTO v_stato_old
          FROM config.stati_doc_reso s
         WHERE s.id = OLD.stato_doc_reso_id;
        IF v_stato_old IS DISTINCT FROM 'DRAFT' THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'vendite.trgfn_resi_guard_magazzino',
                'E_RESO_MAGAZZINO_IMMUTABILE',
                jsonb_build_object('reso_id', NEW.id, 'stato', v_stato_old,
                                   'magazzino_da', OLD.magazzino_id, 'magazzino_a', NEW.magazzino_id),
                NEW.tx_id,
                COALESCE(v_stato_old, 'NULL'));
        END IF;
    END IF;

    -- 2. Dell'emittente del reso (M-6), dal BB: letto sotto RLS, un
    --    magazzino di un altro emittente non si vede, e la frase e' la stessa.
    IF NEW.magazzino_id IS NOT NULL
       AND NOT script.fn_magazzino_dell_emittente(NEW.magazzino_id, NEW.emittente_fiscale_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.trgfn_resi_guard_magazzino',
            'E_RESO_MAGAZZINO_INCOERENTE',
            jsonb_build_object('reso_id', NEW.id, 'magazzino_id', NEW.magazzino_id,
                               'emittente_reso', NEW.emittente_fiscale_id),
            NEW.tx_id,
            VARIADIC ARRAY[]::text[]);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_guard_magazzino()
IS 'Guard BEFORE INSERT OR UPDATE su vendite.resi (D-3b-a), che esce subito se magazzino ed emittente non cambiano. E_RESO_MAGAZZINO_IMMUTABILE: il magazzino cambia su un reso che non era in bozza (stato VECCHIO). E_RESO_MAGAZZINO_INCOERENTE: il magazzino non e'' dell''emittente del reso, dal BB script.fn_magazzino_dell_emittente (letto sotto RLS: invisibile e inesistente rispondono uguale). Fascia z10: dopo trgfn_resi_normalize, che all''INSERT eredita l''emittente dalla bolla. Il magazzino mancante NON e'' qui: e'' un motivo della conferma (script.fn_check_reso_merce). Brief: brief-db-magazzino-lotto-3-bis-carico-da-reso.';
```

---
{% include-markdown "signature-core.md" %}
