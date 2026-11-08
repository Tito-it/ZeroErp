{% include-markdown "it/dbzero/dbops/manual/fn_fusione_ripunta_figlie.md" %}
# ⚙️ Funzione `fn_fusione_ripunta_figlie`

```sql
CREATE FUNCTION fn_fusione_ripunta_figlie(p_padre regclass, p_id_orig bigint, p_id_target bigint, p_porta text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_fusione_ripunta_figlie(p_padre regclass, p_id_orig bigint, p_id_target bigint, p_porta text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi       dbops.error_log.function_name%TYPE := COALESCE(p_porta, 'dbops.fn_fusione_ripunta_figlie');
    v_n_doppi   bigint;
    v_doppi     jsonb;
    v_tabelle   text;
    r_fk        record;
    v_set       text;
    v_rif       text;
    v_n         bigint;
    v_esito     jsonb := '{}'::jsonb;
    v_vincolo   pg_catalog.pg_constraint.conname%TYPE;
    v_dettaglio text;
BEGIN
    -- 1. I doppi, prima di scrivere.
    WITH d AS (
        SELECT d.tabella, d.indice, d.riga_origine, d.riga_destinazione
          FROM dbops.fn_fusione_righe_doppie(p_padre, p_id_orig, p_id_target, v_chi) d
    )
    SELECT (SELECT count(*) FROM d),
           (SELECT jsonb_agg(jsonb_build_object(
                       'tabella', dbops.fn_nome_qualificato(e.tabella),
                       'indice', dbops.fn_nome_qualificato(e.indice),
                       'riga_origine', e.riga_origine,
                       'riga_destinazione', e.riga_destinazione))
              FROM (SELECT * FROM d
                     ORDER BY dbops.fn_nome_qualificato(d.tabella), dbops.fn_nome_qualificato(d.indice), d.riga_origine::text
                     LIMIT 100) e),
           (SELECT string_agg(DISTINCT dbops.fn_nome_qualificato(d.tabella), ', ') FROM d)
      INTO v_n_doppi, v_doppi, v_tabelle;

    IF v_n_doppi > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_MERGE_RIGHE_DOPPIE',
            jsonb_build_object('padre', dbops.fn_nome_qualificato(p_padre),
                               'id_origine', p_id_orig,
                               'id_destinazione', p_id_target,
                               'n_doppi', v_n_doppi,
                               'doppi', v_doppi),
            NULL::uuid,
            p_id_orig::text, p_id_target::text, v_tabelle);
    END IF;

    -- 2. Una UPDATE per figlia.
    FOR r_fk IN
        SELECT f.figlia, f.colonne_fk, f.colonne_rif, f.chiave_padre
          FROM dbops.fn_fusione_figlie(p_padre, v_chi) f
    LOOP
        SELECT string_agg(format('%I', x.c), ', ' ORDER BY x.o),
               string_agg(format('p.%I', x.r), ', ' ORDER BY x.o)
          INTO v_set, v_rif
          FROM unnest(r_fk.colonne_fk, r_fk.colonne_rif) WITH ORDINALITY AS x(c, r, o);

        BEGIN
            EXECUTE format(
                'UPDATE %1$s c SET (%2$s) = (SELECT %3$s FROM %4$s p WHERE p.%5$I = $2)
                  WHERE (%6$s) = (SELECT %3$s FROM %4$s p WHERE p.%5$I = $1)',
                dbops.fn_nome_qualificato(r_fk.figlia), v_set, v_rif, dbops.fn_nome_qualificato(p_padre), r_fk.chiave_padre,
                (SELECT string_agg(format('c.%I', x.c), ', ' ORDER BY x.o)
                   FROM unnest(r_fk.colonne_fk) WITH ORDINALITY AS x(c, o)))
            USING p_id_orig, p_id_target;
            GET DIAGNOSTICS v_n = ROW_COUNT;
        EXCEPTION WHEN unique_violation OR exclusion_violation THEN
            GET STACKED DIAGNOSTICS v_vincolo   = CONSTRAINT_NAME,
                                    v_dettaglio = PG_EXCEPTION_DETAIL;
            PERFORM script.fn_log_and_raise_error(
                'database', v_chi, 'E_MERGE_RIGHE_DOPPIE',
                jsonb_build_object('padre', dbops.fn_nome_qualificato(p_padre),
                                   'id_origine', p_id_orig,
                                   'id_destinazione', p_id_target,
                                   'tabella', dbops.fn_nome_qualificato(r_fk.figlia),
                                   'vincolo', v_vincolo,
                                   'dettaglio', v_dettaglio),
                NULL::uuid,
                p_id_orig::text, p_id_target::text, dbops.fn_nome_qualificato(r_fk.figlia));
        END;

        v_esito := v_esito || jsonb_build_object(dbops.fn_nome_qualificato(r_fk.figlia), v_n);
    END LOOP;

    RETURN v_esito;
END;
$function$

COMMENT ON FUNCTION dbops.fn_fusione_ripunta_figlie(p_padre regclass, p_id_orig bigint, p_id_target bigint, p_porta text)
IS 'Sposta su p_id_target tutto cio'' che riferiva p_id_orig, due righe di p_padre: una UPDATE per ogni tabella figlia (dbops.fn_fusione_figlie), che porta le colonne della chiave esterna ai valori della destinazione. Prima di scrivere cerca i doppi (dbops.fn_fusione_righe_doppie) e, se ce n''e'' anche uno, si ferma con E_MERGE_RIGHE_DOPPIE e l''elenco nel contesto (le prime cento coppie e il conteggio). Un doppio che quel controllo non sa leggere (un indice su espressioni) risponde allo stesso modo, col vincolo e il dettaglio di PostgreSQL. Ogni altro rifiuto di una figlia risale com''e''. Non apre le porte delle figlie: se una figlia protegge la sua chiave esterna con un guard, la fusione che chiama la apre attorno a questa chiamata. Restituisce le righe ripuntate per figlia, { "schema.tabella": n }. p_porta e'' il nome della fusione che chiama, e compare nei messaggi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
