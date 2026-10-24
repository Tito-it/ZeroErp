{% include-markdown "it/dbzero/vendite/manual/trgfn_promo_articoli_guard_data_driven.md" %}
# ⚙️ Funzione `trgfn_promo_articoli_guard_data_driven`

```sql
CREATE FUNCTION trgfn_promo_articoli_guard_data_driven()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_promo_articoli_guard_data_driven()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcer data-driven sulle promo_articoli.
-- Lo stato della promo (FUTURA/INIZIATA/SCADUTA) e' derivato
-- dalle date e mai persistito. Il guard:
--   INSERT  -> valido_dal > CURRENT_DATE (no retroattiva).
--   UPDATE  -> dispatch su stato derivato OLD:
--              FUTURA   tutti mutabili, date solo nel futuro
--              INIZIATA solo descrizione/valido_al(>=today)/meta
--              SCADUTA  nessun campo dominio mutabile
-- Applicato in BEFORE INSERT OR UPDATE; le colonne audit
-- (data_update/user_update/tx_id) sono escluse dal confronto
-- SCADUTA per non bloccare i trigger di sistema.
DECLARE
    v_today CONSTANT date := script.fn_data_operativa();
    v_old_dal vendite.promo_articoli.valido_dal%TYPE;
    v_old_al  vendite.promo_articoli.valido_al%TYPE;
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- valido_al >= valido_dal lo verifica il guard comune delle
        -- date, script.trgfn_guard_date_validita (automazione
        -- DATE_VALIDITA), e sotto di lui la colonna generata `validita`.
        -- rev 20260923-48: qui si citavano chk_promo_articoli_date e il
        -- trigger set_validita, che non esistono (piu').
        IF NEW.valido_dal <= v_today THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_PROMO_RETROATTIVA',
                jsonb_build_object(
                    'op',     'INSERT',
                    'campo',  'valido_dal',
                    'valore', NEW.valido_dal,
                    'oggi',   v_today
                ),
                NEW.tx_id,
                'valido_dal',
                NEW.valido_dal::text,
                v_today::text
            );
        END IF;
        RETURN NEW;
    END IF;

    -- UPDATE: stato derivato dalle date OLD.
    v_old_dal := OLD.valido_dal;
    v_old_al  := OLD.valido_al;

    IF v_old_al < v_today THEN
        -- SCADUTA: ogni cambio dei campi dominio rifiutato.
        IF (NEW.codice, NEW.descrizione, NEW.articolo_id,
            NEW.uom_id, NEW.tipo_variazione,
            NEW.valore_variazione, NEW.valido_dal,
            NEW.valido_al, NEW.attivo, NEW.meta)
           IS DISTINCT FROM
           (OLD.codice, OLD.descrizione, OLD.articolo_id,
            OLD.uom_id, OLD.tipo_variazione,
            OLD.valore_variazione, OLD.valido_dal,
            OLD.valido_al, OLD.attivo, OLD.meta) THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_PROMO_SCADUTA_IMMUTABILE',
                jsonb_build_object(
                    'promo_id',  OLD.id,
                    'codice',    OLD.codice,
                    'valido_al', v_old_al,
                    'oggi',      v_today
                ),
                NEW.tx_id,
                OLD.id::text,
                v_old_al::text,
                v_today::text
            );
        END IF;
        RETURN NEW;
    END IF;

    IF v_old_dal <= v_today AND v_today <= v_old_al THEN
        -- INIZIATA: solo descrizione, valido_al (>= today),
        -- meta sono mutabili.
        IF NEW.codice            IS DISTINCT FROM OLD.codice
           OR NEW.articolo_id    IS DISTINCT FROM OLD.articolo_id
           OR NEW.uom_id         IS DISTINCT FROM OLD.uom_id
           OR NEW.tipo_variazione    IS DISTINCT FROM OLD.tipo_variazione
           OR NEW.valore_variazione  IS DISTINCT FROM OLD.valore_variazione
           OR NEW.valido_dal     IS DISTINCT FROM OLD.valido_dal
           OR NEW.attivo         IS DISTINCT FROM OLD.attivo THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_PROMO_INIZIATA_CAMPI_RISTRETTI',
                jsonb_build_object(
                    'promo_id',   OLD.id,
                    'codice',     OLD.codice,
                    'valido_dal', v_old_dal,
                    'oggi',       v_today
                ),
                NEW.tx_id,
                OLD.id::text,
                v_old_dal::text,
                v_today::text
            );
        END IF;
        -- valido_al non puo' tornare al passato in iniziata.
        IF NEW.valido_al IS DISTINCT FROM OLD.valido_al
           AND NEW.valido_al < v_today THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_PROMO_RETROATTIVA',
                jsonb_build_object(
                    'op',     'UPDATE/INIZIATA',
                    'campo',  'valido_al',
                    'valore', NEW.valido_al,
                    'oggi',   v_today
                ),
                NEW.tx_id,
                'valido_al',
                NEW.valido_al::text,
                v_today::text
            );
        END IF;
        RETURN NEW;
    END IF;

    -- FUTURA (v_today < v_old_dal): tutti i campi mutabili,
    -- nuove date solo verso il futuro.
    IF NEW.valido_dal IS DISTINCT FROM OLD.valido_dal
       AND NEW.valido_dal <= v_today THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_PROMO_RETROATTIVA',
            jsonb_build_object(
                'op',     'UPDATE/FUTURA',
                'campo',  'valido_dal',
                'valore', NEW.valido_dal,
                'oggi',   v_today
            ),
            NEW.tx_id,
            'valido_dal',
            NEW.valido_dal::text,
            v_today::text
        );
    END IF;
    IF NEW.valido_al IS DISTINCT FROM OLD.valido_al
       AND NEW.valido_al < v_today THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_PROMO_RETROATTIVA',
            jsonb_build_object(
                'op',     'UPDATE/FUTURA',
                'campo',  'valido_al',
                'valore', NEW.valido_al,
                'oggi',   v_today
            ),
            NEW.tx_id,
            'valido_al',
            NEW.valido_al::text,
            v_today::text
        );
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_promo_articoli_guard_data_driven()
IS 'Guard data-driven promo_articoli: no retroattivita'' su INSERT, whitelist ristretta su UPDATE INIZIATA, immutabilita'' su SCADUTA. Raise E_PROMO_RETROATTIVA / E_PROMO_INIZIATA_CAMPI_RISTRETTI / E_PROMO_SCADUTA_IMMUTABILE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
