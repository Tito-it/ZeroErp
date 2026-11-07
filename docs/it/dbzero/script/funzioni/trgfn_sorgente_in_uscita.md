# ⚙️ Funzione `trgfn_sorgente_in_uscita`

```sql
CREATE FUNCTION trgfn_sorgente_in_uscita()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_sorgente_in_uscita()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_tipo        config.sorgenti.id%TYPE;
    v_codice      config.sorgenti.codice_interno%TYPE;
    v_selector    config.sorgenti.key_selector%TYPE;
    v_livello     text;
    v_schema      pg_catalog.pg_namespace.nspname%TYPE;
    v_tabella     pg_catalog.pg_class.relname%TYPE;
    v_azione      text;
    v_ha_riga     boolean;
    v_ha_dett     boolean;
    v_col_figlio  text;
    v_col_origine text;
    v_n           bigint;
    v_bloccanti   bigint := 0;
    v_passo       integer;
BEGIN
    -- =========================================================
    -- Scopo: la regola padre-figli della provenienza polimorfa,
    --   dal lato dell'origine. Due passi: prima si contano i figli
    --   che bloccano (e se ce n'e' anche uno si solleva), poi si
    --   cancellano quelli che seguono l'origine.
    -- =========================================================
    FOR v_passo IN 1 .. 2 LOOP
        FOR v_tipo, v_codice, v_selector, v_livello IN
            SELECT s.id, s.codice_interno, s.key_selector, x.livello
              FROM config.sorgenti s
              CROSS JOIN LATERAL (VALUES ('DOCUMENTO', s.target_table),
                                         ('RIGA',      s.righe_table),
                                         ('DETTAGLIO', s.dettaglio_table)) x(livello, tabella)
             WHERE x.tabella = TG_RELID
             ORDER BY s.id, x.livello
        LOOP
            FOR v_schema, v_tabella, v_azione, v_ha_riga, v_ha_dett IN
                SELECT m.schema_tabella, m.nome_tabella, m.azione_cancellazione,
                       m.ha_sorgente_riga, m.ha_sorgente_dettaglio
                  FROM script.fn_sorgente_guard_montaggi() m
                 WHERE m.argomenti_validi
                 ORDER BY m.schema_tabella, m.nome_tabella
            LOOP
                CONTINUE WHEN (v_passo = 1 AND v_azione <> 'BLOCCA')
                           OR (v_passo = 2 AND v_azione <> 'CANCELLA');

                IF v_livello = 'DOCUMENTO' THEN
                    v_col_figlio  := CASE WHEN v_selector = 'uid' THEN 'sorgente_uid' ELSE 'sorgente_id' END;
                    v_col_origine := CASE WHEN v_selector = 'uid' THEN 'uid' ELSE 'id' END;
                ELSIF v_livello = 'RIGA' THEN
                    CONTINUE WHEN NOT v_ha_riga;
                    v_col_figlio  := 'sorgente_riga';
                    v_col_origine := 'id';
                ELSE
                    CONTINUE WHEN NOT v_ha_dett;
                    v_col_figlio  := 'sorgente_dettaglio';
                    v_col_origine := 'id';
                END IF;

                IF v_passo = 1 THEN
                    EXECUTE format(
                        'SELECT count(*) FROM %I.%I f '
                        'WHERE f.sorgente_tipo_id = $1 '
                        '  AND f.%I IN (SELECT o.%I FROM vecchie o)',
                        v_schema, v_tabella, v_col_figlio, v_col_origine)
                      INTO v_n
                      USING v_tipo;
                    v_bloccanti := v_bloccanti + v_n;
                ELSE
                    EXECUTE format(
                        'DELETE FROM %I.%I f '
                        'WHERE f.sorgente_tipo_id = $1 '
                        '  AND f.%I IN (SELECT o.%I FROM vecchie o)',
                        v_schema, v_tabella, v_col_figlio, v_col_origine)
                      USING v_tipo;
                END IF;
            END LOOP;
        END LOOP;

        IF v_passo = 1 AND v_bloccanti > 0 THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.trgfn_sorgente_in_uscita', 'E_SORG_ORIGINE_REFERENZIATA',
                jsonb_build_object('tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                                   'record_che_ne_nascono', v_bloccanti),
                NULL::uuid, v_bloccanti::text);
        END IF;
    END LOOP;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION script.trgfn_sorgente_in_uscita()
IS 'Il lato «in uscita» della provenienza polimorfa, la FK che il legame non ha. Montata AFTER DELETE FOR EACH STATEMENT (tabella di transizione «vecchie») su ogni tabella che config.sorgenti dichiara come documento, righe o dettaglio di un tipo. Quando se ne cancellano righe guarda i record che ne dichiarano la provenienza nelle tabelle che montano il guard unico (script.fn_sorgente_guard_montaggi): sorgente_id o sorgente_uid per il documento, secondo il key_selector, sorgente_riga per la riga, sorgente_dettaglio per il dettaglio. Che cosa fare lo dichiara il figlio nel secondo argomento del suo guard, come un ON DELETE: BLOCCA ferma la cancellazione con E_SORG_ORIGINE_REFERENZIATA, CANCELLA porta via i figli con l''origine. Prima conta tutti i figli che bloccano, poi cancella: se uno blocca, non si cancella niente. SECURITY DEFINER, come una FK: vede anche i figli che la RLS nasconde a chi cancella. La monta dbops.fn_sorgente_converge_uscita.';
```

</div>

---
{% include-markdown "signature-core.md" %}
