{% include-markdown "it/dbzero/magazzino/manual/trgfn_documento_interno_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_documento_interno_guard_transizione`

```sql
CREATE FUNCTION trgfn_documento_interno_guard_transizione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION magazzino.trgfn_documento_interno_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- text e non %TYPE: la funzione e' PARAMETRICA su due tabelle (inventari,
    -- rettifiche), lo stato lo legge per nome da TG_ARGV.
    v_col_stato  text := TG_ARGV[0];
    v_guc        text := TG_ARGV[1];
    v_old        text;
    v_new        text;
    v_ammessa    boolean;
    v_guc_valore text;
BEGIN
    -- Scopo: la matrice degli stati dei documenti interni (D-L2-h), una per
    --   inventari e rettifiche (TG_ARGV: colonna di stato, nome della GUC):
    --   DRAFT -> CONFIRM | CANCEL; CONFIRM -> POSTED (solo se la GUC
    --   transazionale dell'operazione porta NEW.id) | CANCEL | DRAFT (riapri,
    --   C13); POSTED e CANCEL terminali. DELETE ammesso solo in DRAFT (C3): le
    --   righe cascano, e una POSTED lascerebbe orfani sul ledger.
    IF TG_OP = 'DELETE' THEN
        v_old := to_jsonb(OLD) ->> v_col_stato;
        IF v_old <> 'DRAFT' THEN
            PERFORM script.fn_log_and_raise_error(
                'magazzino', 'magazzino.trgfn_documento_interno_guard_transizione',
                'E_MAG_DOCUMENTO_NON_ELIMINABILE',
                jsonb_build_object('detail', 'DELETE di un documento interno non in DRAFT',
                                   'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                                   'documento_id', OLD.id, 'stato', v_old),
                OLD.tx_id,
                v_old);
        END IF;
        RETURN OLD;
    END IF;

    v_old := to_jsonb(OLD) ->> v_col_stato;
    v_new := to_jsonb(NEW) ->> v_col_stato;
    IF v_new IS NOT DISTINCT FROM v_old THEN
        RETURN NEW;
    END IF;

    -- La matrice, in una variabile: un solo punto di sollevamento.
    v_ammessa := CASE v_old
                     WHEN 'DRAFT'   THEN v_new IN ('CONFIRM', 'CANCEL')
                     WHEN 'CONFIRM' THEN v_new IN ('POSTED', 'CANCEL', 'DRAFT')
                     ELSE false                    -- POSTED, CANCEL: terminali
                 END;
    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.trgfn_documento_interno_guard_transizione',
            'E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA',
            jsonb_build_object('detail', 'transizione fuori dalla matrice',
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'documento_id', NEW.id, 'da', v_old, 'a', v_new),
            NEW.tx_id,
            v_old, v_new);
    END IF;

    -- La porta POSTED: solo l'operazione, che si firma con la GUC.
    IF v_new = 'POSTED' THEN
        v_guc_valore := current_setting(v_guc, true);
        IF v_guc_valore IS DISTINCT FROM NEW.id::text THEN
            PERFORM script.fn_log_and_raise_error(
                'magazzino', 'magazzino.trgfn_documento_interno_guard_transizione',
                'E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE',
                jsonb_build_object('detail', 'POSTED senza la GUC dell''operazione',
                                   'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                                   'documento_id', NEW.id, 'guc', v_guc,
                                   'guc_valore', v_guc_valore),
                NEW.tx_id,
                NEW.id::text);
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION magazzino.trgfn_documento_interno_guard_transizione()
IS 'Guard di famiglia dei documenti interni di magazzino (inventari, rettifiche; TG_ARGV = colonna di stato, nome della GUC), BEFORE UPDATE OF <stato> OR DELETE. La MATRICE (D-L2-h, la stessa per le due famiglie, COUNTING escluso): DRAFT -> CONFIRM | CANCEL; CONFIRM -> POSTED | CANCEL | DRAFT (riapri: il piano si legge in CONFIRM e le righe si correggono in DRAFT, C13); POSTED e CANCEL terminali (E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA). POSTED SOLO se current_setting(<GUC>, true) = NEW.id::text — la GUC transazionale che fn_posta_inventario / fn_posta_rettifica impostano e azzerano (E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE, TECNICO: un documento «registrato» senza movimenti dietro direbbe il falso). DELETE solo in DRAFT (C3, decisione del 2026-09-18): le righe cascano, una POSTED lascerebbe orfani (E_MAG_DOCUMENTO_NON_ELIMINABILE). Brief: brief-db-magazzino-lotto-2-motore, sezione 3 (D-L2-h), 6-ter C3/C13.';
```

---
{% include-markdown "signature-core.md" %}
