{% include-markdown "it/dbzero/magazzino/manual/trgfn_documento_interno_righe_guard_testata.md" %}
# ⚙️ Funzione `trgfn_documento_interno_righe_guard_testata`

```sql
CREATE FUNCTION trgfn_documento_interno_righe_guard_testata()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.trgfn_documento_interno_righe_guard_testata()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_testata     text := TG_ARGV[0];   -- es. 'inventari'
    v_col_fk      text := TG_ARGV[1];   -- es. 'inventario_id'
    v_col_stato   text := TG_ARGV[2];   -- es. 'stato_mag_inventario'
    v_guc         text := TG_ARGV[3];   -- es. 'zeroerp.magazzino_posting_inventario'
    -- bigint/text e non %TYPE: parametrica su due famiglie (vedi sopra).
    v_ids         bigint[];
    v_id          bigint;
    v_stato       text;
    v_bloccata    boolean;
    v_tx_id       uuid;
BEGIN
    -- Scopo: le righe di un documento interno si scrivono con la testata in
    --   DRAFT; in CONFIRM scrive solo l'operazione (la GUC che fissa
    --   qta_sistema, e solo dentro un verbo: chi esegue e' il proprietario,
    --   D-V1); POSTED e CANCEL sono congelate (D-L2-h). Un UPDATE che
    --   sposta la riga su un'altra testata le controlla entrambe. «Testata
    --   assente» = cascata gia' decisa a monte (DELETE solo in DRAFT): passa.
    IF TG_OP = 'DELETE' THEN
        v_ids   := ARRAY[(to_jsonb(OLD) ->> v_col_fk)::bigint];
        v_tx_id := OLD.tx_id;
    ELSIF TG_OP = 'INSERT' THEN
        v_ids   := ARRAY[(to_jsonb(NEW) ->> v_col_fk)::bigint];
        v_tx_id := NEW.tx_id;
    ELSE
        v_ids   := ARRAY[(to_jsonb(NEW) ->> v_col_fk)::bigint];
        IF (to_jsonb(OLD) ->> v_col_fk)::bigint IS DISTINCT FROM v_ids[1] THEN
            v_ids := v_ids || (to_jsonb(OLD) ->> v_col_fk)::bigint;
        END IF;
        v_tx_id := NEW.tx_id;
    END IF;

    FOREACH v_id IN ARRAY v_ids LOOP
        CONTINUE WHEN v_id IS NULL;
        -- Nomi da TG_ARGV (scritti nel CREATE TRIGGER), quotati: mai da un input.
        EXECUTE format('SELECT %I FROM magazzino.%I WHERE id = $1', v_col_stato, v_testata)
           INTO v_stato USING v_id;
        CONTINUE WHEN v_stato IS NULL;       -- cascata in corso, o fuori perimetro

        -- Un solo punto di sollevamento: la condizione in una variabile.
        -- CONFIRM: la GUC dell'operazione per QUESTO documento E dentro un verbo
        -- (la GUC l'app puo' accenderla da se', il proprietario non lo e').
        v_bloccata := CASE v_stato
                          WHEN 'DRAFT'   THEN false
                          WHEN 'CONFIRM' THEN current_setting(v_guc, true) IS DISTINCT FROM v_id::text
                                              OR NOT script.fn_is_proprietario_tabella(TG_RELID)
                          ELSE true                 -- POSTED, CANCEL
                      END;
        IF v_bloccata THEN
            PERFORM script.fn_log_and_raise_error(
                'magazzino', 'magazzino.trgfn_documento_interno_righe_guard_testata',
                'E_MAG_DOCUMENTO_RIGHE_CONGELATE',
                jsonb_build_object('detail', 'scrittura di una riga con testata non in DRAFT',
                                   'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                                   'testata', v_testata, 'documento_id', v_id,
                                   'stato', v_stato, 'operazione', TG_OP,
                                   'db_user', current_user),
                v_tx_id,
                v_stato);
        END IF;
    END LOOP;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION magazzino.trgfn_documento_interno_righe_guard_testata()
IS 'Guard delle righe dei documenti interni di magazzino (inventari_righe, rettifiche_righe; TG_ARGV = tabella testata, colonna FK, colonna di stato, nome della GUC), BEFORE INSERT OR UPDATE OR DELETE: righe scrivibili solo con la testata in DRAFT; in CONFIRM scrive solo l''operazione — la stessa GUC transazionale della porta POSTED, e'' lei a fissare qta_sistema — e dal 2026-09-25 solo dentro un verbo: chi esegue deve essere il proprietario della tabella, script.fn_is_proprietario_tabella(TG_RELID) (D-V1: la GUC l''app puo'' accenderla da se''); POSTED e CANCEL congelate (E_MAG_DOCUMENTO_RIGHE_CONGELATE, CONFLITTO_STATO). Un UPDATE che sposta la riga controlla entrambe le testate. Testata assente = cascata gia'' ammessa a monte (DELETE solo in DRAFT) o fuori perimetro: passa. Brief: brief-db-magazzino-lotto-2-motore, sezione 3 (D-L2-h); brief-db-magazzino-verbi-con-permesso D-V1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
