{% include-markdown "it/dbzero/config/manual/trgfn_tipi_ruoli_guard_entita_ref.md" %}
# ⚙️ Funzione `trgfn_tipi_ruoli_guard_entita_ref`

```sql
CREATE FUNCTION trgfn_tipi_ruoli_guard_entita_ref()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_tipi_ruoli_guard_entita_ref()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_colonna_codice config.tipi_ruoli.entita_colonna_codice%TYPE;
    -- OID di catalogo della relazione: nessuna colonna di cui sia il riflesso.
    v_rel_oid        oid;
    -- relkind di pg_class: tipo di catalogo, nessuna colonna applicativa.
    v_relkind        "char";
BEGIN
    -- Regola 1: coerenza NULL
    IF NEW.entita_tabella IS NULL THEN
        IF NEW.entita_colonna_codice IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'config.trgfn_tipi_ruoli_guard_entita_ref',
                'E_PARAMETRO_INVALIDO',
                jsonb_build_object(
                    'detail', 'entita_colonna_codice deve essere NULL se entita_tabella e'' NULL',
                    'codice_interno', NEW.codice_interno,
                    'entita_colonna_codice', NEW.entita_colonna_codice
                ),
                NULL::uuid,
                'entita_colonna_codice non NULL senza entita_tabella'
            );
        END IF;
    ELSE
        -- Regola 2: entita_tabella deve essere un regclass valido
        v_rel_oid := to_regclass(NEW.entita_tabella);

        IF v_rel_oid IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'config.trgfn_tipi_ruoli_guard_entita_ref',
                'E_TIPI_RUOLI_ENTITA_INVALIDA',
                jsonb_build_object(
                    'codice_interno', NEW.codice_interno,
                    'entita_tabella', NEW.entita_tabella
                ),
                NULL::uuid,
                NEW.codice_interno,
                concat('tabella/vista ', NEW.entita_tabella, ' non trovata')
            );
        END IF;

        -- Regola 3: la tabella deve avere soggetto_ruolo_id
        IF NOT EXISTS (
            SELECT 1
              FROM pg_catalog.pg_attribute a
             WHERE a.attrelid = v_rel_oid
               AND a.attname  = 'soggetto_ruolo_id'
               AND a.attnum   > 0
               AND NOT a.attisdropped
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'config.trgfn_tipi_ruoli_guard_entita_ref',
                'E_TIPI_RUOLI_ENTITA_INVALIDA',
                jsonb_build_object(
                    'codice_interno', NEW.codice_interno,
                    'entita_tabella', NEW.entita_tabella
                ),
                NULL::uuid,
                NEW.codice_interno,
                concat(NEW.entita_tabella, ' manca colonna soggetto_ruolo_id')
            );
        END IF;

        -- Regola 4: colonna codice deve esistere
        v_colonna_codice := COALESCE(NEW.entita_colonna_codice, 'codice');

        IF NOT EXISTS (
            SELECT 1
              FROM pg_catalog.pg_attribute a
             WHERE a.attrelid = v_rel_oid
               AND a.attname  = v_colonna_codice
               AND a.attnum   > 0
               AND NOT a.attisdropped
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'config.trgfn_tipi_ruoli_guard_entita_ref',
                'E_TIPI_RUOLI_ENTITA_INVALIDA',
                jsonb_build_object(
                    'codice_interno', NEW.codice_interno,
                    'entita_tabella', NEW.entita_tabella,
                    'colonna_cercata', v_colonna_codice
                ),
                NULL::uuid,
                NEW.codice_interno,
                concat(NEW.entita_tabella, '.', v_colonna_codice, ' non trovata')
            );
        END IF;
    END IF;

    -- Regola 5 (rev 2026-10-10, R-6): entita_esistenza e' una
    --   TABELLA esistente con soggetto_ruolo_id. Mai una vista:
    --   il perimetro lo fa la RLS della tabella, e una vista
    --   senza security_invoker la spegnerebbe in silenzio.
    IF NEW.entita_esistenza IS NOT NULL THEN
        SELECT c.oid, c.relkind
          INTO v_rel_oid, v_relkind
          FROM pg_catalog.pg_class c
         WHERE c.oid = to_regclass(NEW.entita_esistenza);

        IF v_rel_oid IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'config.trgfn_tipi_ruoli_guard_entita_ref',
                'E_TIPI_RUOLI_ENTITA_INVALIDA',
                jsonb_build_object(
                    'codice_interno', NEW.codice_interno,
                    'entita_esistenza', NEW.entita_esistenza
                ),
                NULL::uuid,
                NEW.codice_interno,
                concat('entita_esistenza: tabella ', NEW.entita_esistenza, ' non trovata')
            );
        END IF;

        IF v_relkind NOT IN ('r', 'p') THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'config.trgfn_tipi_ruoli_guard_entita_ref',
                'E_TIPI_RUOLI_ENTITA_INVALIDA',
                jsonb_build_object(
                    'codice_interno', NEW.codice_interno,
                    'entita_esistenza', NEW.entita_esistenza,
                    'relkind', v_relkind
                ),
                NULL::uuid,
                NEW.codice_interno,
                concat('entita_esistenza: ', NEW.entita_esistenza,
                       ' non e'' una tabella (le viste non sono ammesse: il perimetro lo fa la RLS della tabella)')
            );
        END IF;

        IF NOT EXISTS (
            SELECT 1
              FROM pg_catalog.pg_attribute a
             WHERE a.attrelid = v_rel_oid
               AND a.attname  = 'soggetto_ruolo_id'
               AND a.attnum   > 0
               AND NOT a.attisdropped
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'config.trgfn_tipi_ruoli_guard_entita_ref',
                'E_TIPI_RUOLI_ENTITA_INVALIDA',
                jsonb_build_object(
                    'codice_interno', NEW.codice_interno,
                    'entita_esistenza', NEW.entita_esistenza
                ),
                NULL::uuid,
                NEW.codice_interno,
                concat('entita_esistenza: ', NEW.entita_esistenza, ' manca colonna soggetto_ruolo_id')
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_tipi_ruoli_guard_entita_ref()
IS 'Guard INSERT/UPDATE su config.tipi_ruoli. entita_tabella (ricerca del codice): regclass valido, tabella o vista, con soggetto_ruolo_id e la colonna codice (entita_colonna_codice, default codice); se NULL, entita_colonna_codice deve essere NULL. entita_esistenza (rev 2026-10-10, brief-db-codici-non-trovato-email-e-permessi R-6): se valorizzata, una TABELLA esistente (relkind r o p, mai una vista: il perimetro lo fa la RLS della tabella) con soggetto_ruolo_id. Errore: E_TIPI_RUOLI_ENTITA_INVALIDA, E_PARAMETRO_INVALIDO per la coerenza dei NULL. ⚠️ Vale in scrittura: una tabella cancellata dopo la presidia il pgTAP script/test-search-regola-unica-visibile-v1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
