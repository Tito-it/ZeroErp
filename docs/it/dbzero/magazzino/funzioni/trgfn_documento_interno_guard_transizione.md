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
    -- Scopo: far rispettare la matrice degli stati dei documenti interni
    --   (D-L2-h), una per inventari e rettifiche (TG_ARGV: colonna di stato,
    --   nome della GUC). La matrice NON sta piu' qui: la dice
    --   magazzino.fn_documento_interno_transizioni, che la capability del
    --   drawer legge per disegnare i pulsanti (R-1 del Lotto 2-bis). Qui
    --   restano il DELETE ammesso solo in DRAFT (C3) e la porta POSTED, che
    --   si apre solo per l'operazione firmata con la GUC transazionale.
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

    -- La matrice, da UNA sede: qui si fa rispettare, li' si legge anche per
    -- accendere i pulsanti. Uno stato terminale (o sconosciuto) torna {},
    -- quindi nessuna destinazione e' ammessa.
    v_ammessa := v_new = ANY (magazzino.fn_documento_interno_transizioni(v_old));
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
IS 'Guard di famiglia dei documenti interni di magazzino (inventari, rettifiche): fa rispettare la matrice degli stati, che dal 2026-09-22 LEGGE da magazzino.fn_documento_interno_transizioni invece di contenerla — la stessa sede da cui la capability del drawer disegna i pulsanti (R-1 del Lotto 2-bis, linee-guida-sql §12.2 punto 1). Monta su BEFORE UPDATE OF <colonna stato> e BEFORE DELETE con TG_ARGV = (colonna di stato, nome della GUC di posting). Tre rifiuti: E_MAG_DOCUMENTO_NON_ELIMINABILE (DELETE fuori da DRAFT, C3), E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA (fuori matrice), E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE (POSTED senza la GUC transazionale che l''operazione scrive: la porta del ledger passa di li''). Brief: brief-db-magazzino-lotto-2-motore sezione 3 (D-L2-h), 6-ter C3/C13; brief-db-magazzino-lotto-2-bis-be-fe R-1.';
```

---
{% include-markdown "signature-core.md" %}
