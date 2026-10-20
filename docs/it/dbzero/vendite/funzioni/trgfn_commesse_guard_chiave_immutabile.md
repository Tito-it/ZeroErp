{% include-markdown "it/dbzero/vendite/manual/trgfn_commesse_guard_chiave_immutabile.md" %}
# ⚙️ Funzione `trgfn_commesse_guard_chiave_immutabile`

```sql
CREATE FUNCTION trgfn_commesse_guard_chiave_immutabile()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_commesse_guard_chiave_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo:
--   Le condizioni di pagamento sono elemento della chiave di
--   raggruppamento della commessa (D-R): una volta che alla
--   commessa e' stato attaccato del lavoro, cambiarle lascerebbe
--   quelle attivita' sotto una chiave che non le descrive.
-- Regole:
--   - blocca UPDATE di termine/modalita' se esiste almeno una
--     riga in commesse_attivita per questa commessa;
--   - commessa ancora vuota: modifica ammessa (non ha raggruppato
--     nulla, non c'e' promessa da tradire);
--   - riscrivere lo STESSO valore non e' un cambio di chiave e
--     passa (IS DISTINCT FROM);
--   - bypass tecnico via GUC zeroerp.maintenance_reset_lotto_draft,
--     coerente con gli altri guard di dominio.
-- =========================================================
DECLARE
    v_bypass    text;
    v_attivita  bigint;
    v_campo     text;
BEGIN
    v_bypass := current_setting('zeroerp.maintenance_reset_lotto_draft', true);
    IF v_bypass IS NOT NULL AND lower(v_bypass) IN ('1','true','on','yes') THEN
        RETURN NEW;
    END IF;

    IF NEW.termine_pagamento_id IS NOT DISTINCT FROM OLD.termine_pagamento_id
       AND NEW.modalita_pagamento_id IS NOT DISTINCT FROM OLD.modalita_pagamento_id THEN
        RETURN NEW;
    END IF;

    SELECT count(*) INTO v_attivita
      FROM vendite.commesse_attivita ca
     WHERE ca.commessa_id = OLD.id;

    IF v_attivita = 0 THEN
        RETURN NEW;
    END IF;

    -- Quale delle due si sta muovendo: finisce nel messaggio, cosi'
    -- chi lo legge sa dove guardare senza aprire il payload.
    v_campo := CASE
        WHEN NEW.termine_pagamento_id IS DISTINCT FROM OLD.termine_pagamento_id
         AND NEW.modalita_pagamento_id IS DISTINCT FROM OLD.modalita_pagamento_id
            THEN 'termine e modalita'' di pagamento'
        WHEN NEW.termine_pagamento_id IS DISTINCT FROM OLD.termine_pagamento_id
            THEN 'termine di pagamento'
        ELSE 'modalita'' di pagamento'
    END;

    PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_COMMESSA_CHIAVE_IMMUTABILE',
        jsonb_build_object(
            'commessa_id', OLD.id,
            'codice', OLD.codice,
            'attivita_collegate', v_attivita,
            'termine_old', OLD.termine_pagamento_id,
            'termine_new', NEW.termine_pagamento_id,
            'modalita_old', OLD.modalita_pagamento_id,
            'modalita_new', NEW.modalita_pagamento_id),
        NULL::uuid, OLD.codice, v_campo, v_attivita::text
    );

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_commesse_guard_chiave_immutabile()
IS 'Guard D-R: termine/modalita'' di pagamento sono elemento della chiave di raggruppamento della commessa, quindi non si cambiano una volta che ci sono attivita'' collegate (si apre una commessa nuova). Commessa vuota: ammesso. Riscrittura dello stesso valore: ammessa. Bypass via GUC zeroerp.maintenance_reset_lotto_draft. Errore E_COMMESSA_CHIAVE_IMMUTABILE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
