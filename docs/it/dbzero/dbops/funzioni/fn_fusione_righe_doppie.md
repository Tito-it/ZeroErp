{% include-markdown "it/dbzero/dbops/manual/fn_fusione_righe_doppie.md" %}
# ⚙️ Funzione `fn_fusione_righe_doppie`

```sql
CREATE FUNCTION fn_fusione_righe_doppie(p_padre regclass, p_id_orig bigint, p_id_target bigint, p_porta text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_fusione_righe_doppie(p_padre regclass, p_id_orig bigint, p_id_target bigint, p_porta text DEFAULT NULL::text)
 RETURNS TABLE(tabella regclass, indice regclass, riga_origine jsonb, riga_destinazione jsonb)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_chi     dbops.error_log.function_name%TYPE := COALESCE(p_porta, 'dbops.fn_fusione_righe_doppie');
    r_fk      record;
    r_ix      record;
    v_nuova   text;   -- la riga dell'origine con la FK gia' sulla destinazione
    v_fk      text;   -- le colonne della FK nella figlia
    v_rif     text;   -- le colonne riferite nel padre
    v_riga_c  text;   -- come si nomina una riga, alias c
    v_riga_r  text;   -- come si nomina una riga, alias r0
    v_on      text;
BEGIN
    IF p_id_orig IS NULL OR p_id_target IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', CASE WHEN p_id_orig IS NULL THEN 'p_id_orig' ELSE 'p_id_target' END),
            NULL::uuid,
            v_chi, 'origine e destinazione sono obbligatorie');
    END IF;

    FOR r_fk IN
        SELECT f.figlia, f.colonne_fk, f.colonne_rif, f.chiave_padre
          FROM dbops.fn_fusione_figlie(p_padre, v_chi) f
    LOOP
        SELECT string_agg(format('c.%I', x.c), ', ' ORDER BY x.o),
               string_agg(format('p.%I', x.r), ', ' ORDER BY x.o)
          INTO v_fk, v_rif
          FROM unnest(r_fk.colonne_fk, r_fk.colonne_rif) WITH ORDINALITY AS x(c, r, o);

        -- La riga com'e' dopo la fusione: ogni colonna della FK dalla
        -- destinazione, le altre uguali.
        SELECT string_agg(
                   CASE WHEN x.r IS NOT NULL
                        THEN format('(SELECT p.%I FROM %s p WHERE p.%I = $2) AS %I',
                                    x.r, dbops.fn_nome_qualificato(p_padre), r_fk.chiave_padre, a.attname)
                        ELSE format('c.%I', a.attname)
                   END, ', ' ORDER BY a.attnum)
          INTO v_nuova
          FROM pg_catalog.pg_attribute a
          LEFT JOIN unnest(r_fk.colonne_fk, r_fk.colonne_rif) AS x(c, r)
            ON x.c = a.attname
         WHERE a.attrelid = r_fk.figlia
           AND a.attnum > 0
           AND NOT a.attisdropped;

        -- Il nome di una riga: la chiave primaria, o il ctid.
        SELECT COALESCE(
                   'jsonb_build_object(' || string_agg(format('%L, %%1$s.%I', a.attname, a.attname), ', '
                                                       ORDER BY k.o) || ')',
                   'jsonb_build_object(''ctid'', %1$s.ctid::text)')
          INTO v_riga_c
          FROM pg_catalog.pg_constraint pk
         CROSS JOIN LATERAL unnest(pk.conkey) WITH ORDINALITY AS k(col, o)
          JOIN pg_catalog.pg_attribute a
            ON a.attrelid = pk.conrelid AND a.attnum = k.col
         WHERE pk.conrelid = r_fk.figlia
           AND pk.contype = 'p';
        v_riga_r := format(v_riga_c, 'r0');
        v_riga_c := format(v_riga_c, 'c');

        FOR r_ix IN
            SELECT i.indexrelid::regclass AS indice,
                   i.indnullsnotdistinct,
                   COALESCE(pg_get_expr(i.indpred, i.indrelid), 'true') AS predicato,
                   array_agg(a.attname ORDER BY k.o) AS chiave
              FROM pg_catalog.pg_index i
             CROSS JOIN LATERAL unnest((i.indkey::int2[])[0:i.indnkeyatts - 1]) WITH ORDINALITY AS k(col, o)
              JOIN pg_catalog.pg_attribute a
                ON a.attrelid = i.indrelid AND a.attnum = k.col
             WHERE i.indrelid = r_fk.figlia
               AND i.indisunique
               AND i.indexprs IS NULL
             GROUP BY i.indexrelid, i.indnullsnotdistinct, i.indpred, i.indrelid
            HAVING array_agg(a.attname) && r_fk.colonne_fk
             ORDER BY dbops.fn_nome_qualificato(i.indexrelid::regclass)
        LOOP
            SELECT string_agg(format('n.%1$I %2$s r.%1$I', x.c,
                                     CASE WHEN r_ix.indnullsnotdistinct
                                          THEN 'IS NOT DISTINCT FROM' ELSE '=' END),
                              ' AND ')
              INTO v_on
              FROM unnest(r_ix.chiave) AS x(c);

            RETURN QUERY EXECUTE format(
                $q$
                SELECT %1$s::oid::regclass, %2$s::oid::regclass, n.__riga, r.__riga
                  FROM (SELECT *
                          FROM (SELECT %3$s, %4$s AS __riga
                                  FROM %5$s c
                                 WHERE (%6$s) = (SELECT %7$s FROM %8$s p WHERE p.%9$I = $1)) n0
                         WHERE %10$s) n
                  JOIN (SELECT r0.*, %11$s AS __riga
                          FROM %5$s r0
                         WHERE %10$s) r
                    ON %12$s
                $q$,
                r_fk.figlia::oid, r_ix.indice::oid, v_nuova, v_riga_c, dbops.fn_nome_qualificato(r_fk.figlia),
                v_fk, v_rif, dbops.fn_nome_qualificato(p_padre), r_fk.chiave_padre, r_ix.predicato,
                v_riga_r, v_on)
            USING p_id_orig, p_id_target;
        END LOOP;
    END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_fusione_righe_doppie(p_padre regclass, p_id_orig bigint, p_id_target bigint, p_porta text)
IS 'Le righe che la fusione di p_id_orig in p_id_target, due righe di p_padre, renderebbe doppie: per ogni tabella figlia (dbops.fn_fusione_figlie) e per ogni suo indice unico che contiene una colonna della chiave esterna, la riga dell''origine come diventerebbe e la riga che c''e'' gia'' e che avrebbe la stessa chiave. Ogni riga si nomina con la sua chiave primaria in jsonb (o col ctid). Rispetta NULLS NOT DISTINCT e il predicato di un indice parziale; le colonne INCLUDE non contano. Non legge gli indici su espressioni: quelli li intercetta dbops.fn_fusione_ripunta_figlie al momento della scrittura. Sola lettura: nessuna riga vuol dire che la fusione non trova doppi. p_porta e'' il nome della fusione che chiama, e compare nei messaggi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
