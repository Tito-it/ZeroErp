# ⚙️ Funzione `trgfn_gestori_guard`

```sql
CREATE FUNCTION trgfn_gestori_guard()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_gestori_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_soggetto_id   uuid;
    v_partita_iva   text;
    v_existing_id   integer;
BEGIN

-- =========================================================
-- anagrafiche.trgfn_gestori_guard_ins_upd()
-- Guard di dominio per anagrafiche.gestori
--
-- Regole:
--  1) Singleton: massimo 1 record in anagrafiche.gestori
--  2) Il soggetto collegato DEVE avere partita_iva valorizzata
-- =========================================================


    ----------------------------------------------------------------
    -- 0) Verifica che il soggetto_ruolo esista e risali al soggetto
    ----------------------------------------------------------------
    SELECT s.id, s.partita_iva
    INTO v_soggetto_id, v_partita_iva
    FROM anagrafiche.soggetti_ruoli sr
    JOIN anagrafiche.soggetti s
    ON s.id = sr.soggetto_id
    WHERE sr.id = NEW.soggetto_ruolo_id;

    IF v_soggetto_id IS NULL THEN
        PERFORM dbops.fn_log_and_raise_error(
            p_codice_errore := 'E_GESTORE_SOGGETTO_RUOLO_MANCANTE',
            p_messaggio     := 'Il gestore deve riferirsi a un soggetto_ruolo esistente.',
            p_context       := jsonb_build_object(
                                'table', TG_TABLE_NAME,
                                'soggetto_ruolo_id', NEW.soggetto_ruolo_id
                            ),
        NEW.tx_id,
        coalesce(NEW.soggetto_ruolo_id::text, 'NULL')
        );
    END IF;

    ----------------------------------------------------------------
    -- 1) Regola: il soggetto del gestore deve avere PARTITA IVA
    ----------------------------------------------------------------
    IF v_partita_iva IS NULL OR btrim(v_partita_iva) = '' THEN
        PERFORM dbops.fn_log_and_raise_error(
            p_codice_errore := 'E_RUOLO_RICHIEDE_PIVA',
            p_messaggio     := 'Il gestore deve essere associato a un soggetto con partita_iva valorizzata.',
            p_context       := jsonb_build_object(
                                'table', TG_TABLE_NAME,
                                'soggetto_id', v_soggetto_id,
                                'soggetto_ruolo_id', NEW.soggetto_ruolo_id
                            ),
        NEW.tx_id,
        'gestore',
        v_soggetto_id::text,
        coalesce(NEW.soggetto_ruolo_id::text, 'NULL')
        
        );
    END IF;

    ----------------------------------------------------------------
    -- 2) Regola singleton: massimo 1 record in anagrafiche.gestori
    --
    -- NB: id <> NEW.id per permettere UPDATE sulla stessa riga.
    ----------------------------------------------------------------
    SELECT g.id
    INTO v_existing_id
    FROM anagrafiche.gestori g
    WHERE g.id <> COALESCE(NEW.id, -1)
    LIMIT 1;

    IF FOUND THEN
        PERFORM dbops.fn_log_and_raise_error(
            p_codice_errore := 'E_GESTORE_SINGLETON_VIOLATO',
            p_messaggio     := 'Esiste già un record di gestore. Non è possibile crearne un secondo.',
            p_context       := jsonb_build_object(
                                'table', TG_TABLE_NAME,
                                'existing_gestore_id', v_existing_id,
                                'new_soggetto_ruolo_id', NEW.soggetto_ruolo_id
                            ),
        NEW.tx_id,
        coalesce(NEW.soggetto_ruolo_id::text, 'NULL')
        );
    END IF;

    RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
