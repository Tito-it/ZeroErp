{% include-markdown "it/dbzero/dbops/manual/fn_sorgenti_orfane.md" %}
# ⚙️ Funzione `fn_sorgenti_orfane`

```sql
CREATE FUNCTION fn_sorgenti_orfane()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_sorgenti_orfane()
 RETURNS TABLE(tabella regclass, riga_id bigint, grammatica text, livello text, sorgente_tipo_id bigint, sorgente_codice_interno character varying, sorgente_id bigint, sorgente_uid text, sorgente_riga bigint, sorgente_dettaglio bigint, target_table regclass)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_relid      oid;
    v_schema     pg_catalog.pg_namespace.nspname%TYPE;
    v_tabella    pg_catalog.pg_class.relname%TYPE;
    v_grammatica text;
    v_ha_id      boolean;
    v_ha_uid     boolean;
    v_ha_riga    boolean;
    v_ha_dett    boolean;

    v_tipo       config.sorgenti.id%TYPE;
    v_codice     config.sorgenti.codice_interno%TYPE;
    v_selector   config.sorgenti.key_selector%TYPE;
    v_d_relid    oid;
    v_d_schema   pg_catalog.pg_namespace.nspname%TYPE;
    v_d_tabella  pg_catalog.pg_class.relname%TYPE;
    v_d_ha_uid   boolean;
    v_r_relid    oid;
    v_r_schema   pg_catalog.pg_namespace.nspname%TYPE;
    v_r_tabella  pg_catalog.pg_class.relname%TYPE;
    v_r_fk       config.sorgenti.righe_fk_column%TYPE;
    v_t_relid    oid;
    v_t_schema   pg_catalog.pg_namespace.nspname%TYPE;
    v_t_tabella  pg_catalog.pg_class.relname%TYPE;
    v_t_fk       config.sorgenti.dettaglio_fk_column%TYPE;

    -- La testa comune della riga restituita, e le espressioni delle
    -- colonne che la tabella puo' non avere.
    v_testa      text;
    v_e_id       text;
    v_e_uid      text;
    v_e_riga     text;
    v_e_dett     text;
    v_chiave_x   text;
    v_chiave_d   text;
BEGIN
    -- =========================================================
    -- Scopo: le righe la cui provenienza punta a un documento, una
    --   riga o un dettaglio che non c'e' piu'. Per tabella del
    --   perimetro e per tipo presente, un anti-join dinamico nella
    --   grammatica della tabella.
    -- =========================================================
    FOR v_relid, v_schema, v_tabella, v_grammatica, v_ha_id, v_ha_uid, v_ha_riga, v_ha_dett IN
        SELECT p.tabella::oid, p.schema_tabella, p.nome_tabella, p.grammatica,
               p.ha_sorgente_id, p.ha_sorgente_uid, p.ha_sorgente_riga, p.ha_sorgente_dettaglio
          FROM dbops.fn_sorgenti_orfane_perimetro() p
         WHERE p.orfani_esclusi_perche IS NULL
    LOOP
        v_e_id   := CASE WHEN v_ha_id   THEN 'x.sorgente_id::bigint'      ELSE 'NULL::bigint' END;
        v_e_uid  := CASE WHEN v_ha_uid  THEN 'x.sorgente_uid::text'       ELSE 'NULL::text'   END;
        v_e_riga := CASE WHEN v_ha_riga THEN 'x.sorgente_riga::bigint'    ELSE 'NULL::bigint' END;
        v_e_dett := CASE WHEN v_ha_dett THEN 'x.sorgente_dettaglio::bigint' ELSE 'NULL::bigint' END;

        FOR v_tipo IN
            EXECUTE format('SELECT DISTINCT x.sorgente_tipo_id::bigint FROM %I.%I x '
                           'WHERE x.sorgente_tipo_id IS NOT NULL', v_schema, v_tabella)
        LOOP
            SELECT l.codice_interno, l.key_selector,
                   l.documento_relid, l.documento_schema, l.documento_tabella, l.documento_ha_uid,
                   l.righe_relid, l.righe_schema, l.righe_tabella, l.righe_fk_column,
                   l.dettaglio_relid, l.dettaglio_schema, l.dettaglio_tabella, l.dettaglio_fk_column
              INTO v_codice, v_selector,
                   v_d_relid, v_d_schema, v_d_tabella, v_d_ha_uid,
                   v_r_relid, v_r_schema, v_r_tabella, v_r_fk,
                   v_t_relid, v_t_schema, v_t_tabella, v_t_fk
              FROM config.fn_sorgente_livelli(v_tipo) l;

            CONTINUE WHEN v_d_tabella IS NULL;

            v_testa := format(
                'SELECT %s::oid::regclass, x.id::bigint, %L::text, %%L::text, '
                'x.sorgente_tipo_id::bigint, %L::varchar, %s, %s, %s, %s, %%s::oid::regclass '
                'FROM %I.%I x ',
                v_relid, v_grammatica, v_codice, v_e_id, v_e_uid, v_e_riga, v_e_dett,
                v_schema, v_tabella);

            IF v_grammatica = 'UNICO' THEN
                -- La chiave del documento secondo il key_selector.
                IF v_selector = 'uid' THEN
                    CONTINUE WHEN NOT v_ha_uid;
                    v_chiave_x := 'x.sorgente_uid';
                    v_chiave_d := 'd.uid';
                ELSE
                    CONTINUE WHEN NOT v_ha_id;
                    v_chiave_x := 'x.sorgente_id';
                    v_chiave_d := 'd.id';
                END IF;

                -- documento
                RETURN QUERY EXECUTE format(v_testa, 'DOCUMENTO', v_d_relid)
                    || format('WHERE x.sorgente_tipo_id = $1 AND %s IS NOT NULL '
                              'AND NOT EXISTS (SELECT 1 FROM %I.%I d WHERE %s = %s)',
                              v_chiave_x, v_d_schema, v_d_tabella, v_chiave_d, v_chiave_x)
                    USING v_tipo;

                -- riga
                IF v_ha_riga AND v_r_tabella IS NOT NULL THEN
                    RETURN QUERY EXECUTE format(v_testa, 'RIGA', v_r_relid)
                        || format('JOIN %I.%I d ON %s = %s '
                                  'WHERE x.sorgente_tipo_id = $1 AND x.sorgente_riga IS NOT NULL '
                                  'AND NOT EXISTS (SELECT 1 FROM %I.%I r '
                                  'WHERE r.id = x.sorgente_riga AND r.%I = d.id)',
                                  v_d_schema, v_d_tabella, v_chiave_d, v_chiave_x,
                                  v_r_schema, v_r_tabella, v_r_fk)
                        USING v_tipo;
                END IF;

                -- dettaglio
                IF v_ha_dett AND v_t_tabella IS NOT NULL THEN
                    RETURN QUERY EXECUTE format(v_testa, 'DETTAGLIO', v_t_relid)
                        || format('JOIN %I.%I r ON r.id = x.sorgente_riga '
                                  'WHERE x.sorgente_tipo_id = $1 AND x.sorgente_dettaglio IS NOT NULL '
                                  'AND NOT EXISTS (SELECT 1 FROM %I.%I t '
                                  'WHERE t.id = x.sorgente_dettaglio AND t.%I = x.sorgente_riga)',
                                  v_r_schema, v_r_tabella, v_t_schema, v_t_tabella, v_t_fk)
                        USING v_tipo;
                END IF;

            ELSIF v_grammatica = 'MODELLO_A' THEN
                -- La chiave dell'oggetto del tipo: sorgente_riga per 'id', sorgente_uid per 'uid'.
                IF v_selector = 'uid' THEN
                    CONTINUE WHEN NOT v_ha_uid;
                    v_chiave_x := 'x.sorgente_uid';
                    v_chiave_d := 'd.uid';
                ELSE
                    CONTINUE WHEN NOT v_ha_riga;
                    v_chiave_x := 'x.sorgente_riga';
                    v_chiave_d := 'd.id';
                END IF;

                RETURN QUERY EXECUTE format(v_testa, 'DOCUMENTO', v_d_relid)
                    || format('WHERE x.sorgente_tipo_id = $1 AND %s IS NOT NULL '
                              'AND NOT EXISTS (SELECT 1 FROM %I.%I d WHERE %s = %s)',
                              v_chiave_x, v_d_schema, v_d_tabella, v_chiave_d, v_chiave_x)
                    USING v_tipo;

            ELSE
                -- TESTUALE: la chiave in sorgente_uid, come id o come uid, nella
                -- forma canonica dei BB della chiave (la regola del ponte).
                CONTINUE WHEN NOT v_ha_uid;
                RETURN QUERY EXECUTE format(v_testa, 'DOCUMENTO', v_d_relid)
                    || format('WHERE x.sorgente_tipo_id = $1 AND x.sorgente_uid IS NOT NULL '
                              'AND NOT EXISTS (SELECT 1 FROM %I.%I d '
                              'WHERE d.id = script.fn_sorgente_chiave_id(x.sorgente_uid::text)%s)',
                              v_d_schema, v_d_tabella,
                              CASE WHEN v_d_ha_uid
                                   THEN ' OR d.uid = script.fn_sorgente_chiave_uuid(x.sorgente_uid::text)'
                                   ELSE '' END)
                    USING v_tipo;
            END IF;
        END LOOP;
    END LOOP;
    RETURN;
END;
$function$

COMMENT ON FUNCTION dbops.fn_sorgenti_orfane()
IS 'Le righe la cui provenienza punta a un record che non esiste piu'': un documento (livello DOCUMENTO), una riga che non c''e'' o non e'' di quel documento (RIGA), un dettaglio che non c''e'' o non e'' di quella riga (DETTAGLIO). Una riga per orfano, con la tabella, l''id, la grammatica, il tipo, le colonne della provenienza e target_table, la tabella dove manca il record. Perimetro: dbops.fn_sorgenti_orfane_perimetro, tranne le tabelle con orfani_esclusi_perche. Per tabella e per tipo un anti-join dinamico nella grammatica della tabella: UNICO a tre livelli; MODELLO_A con la chiave in sorgente_riga o sorgente_uid; TESTUALE con la chiave in sorgente_uid, riconosciuta in forma canonica (script.fn_sorgente_chiave_id / _uuid). Il guard impedisce di scrivere un orfano; qui si trovano quelli nati dopo, cancellando l''origine senza il lato «in uscita». SECURITY DEFINER del proprietario (attraversa la RLS), STABLE. Letta da dbops.vw_sorgenti_orfane, che deve restare vuota.';
```

</div>

---
{% include-markdown "signature-core.md" %}
