{% include-markdown "it/dbzero/maintenance/manual/fn_analyze_statistiche.md" %}
# ⚙️ Funzione `fn_analyze_statistiche`

```sql
CREATE FUNCTION fn_analyze_statistiche(p_tabelle regclass[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION maintenance.fn_analyze_statistiche(p_tabelle regclass[] DEFAULT NULL::regclass[])
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tabella  regclass;
    v_mancanti integer;
    v_elenco   text;
    v_tabelle  jsonb;
BEGIN
    -- Scopo: dare al planner statistiche vere. ANALYZE del database
    --   (p_tabelle NULL) o delle tabelle indicate, poi la prova di
    --   esserci riuscito: ANALYZE salta con un WARNING cio' che non
    --   puo' analizzare, e senza questa prova il giornale direbbe
    --   «done». Ritorna quante tabelle del perimetro restano senza
    --   statistiche: sempre 0, perche' altrimenti solleva.
    IF p_tabelle IS NULL THEN
        ANALYZE;
    ELSE
        FOREACH v_tabella IN ARRAY p_tabelle LOOP
            EXECUTE format('ANALYZE %s', v_tabella);
        END LOOP;
    END IF;

    -- ⭐ L'autoverifica: nella stessa transazione, quindi vede
    --   reltuples appena scritto da ANALYZE.
    SELECT count(*)::integer,
           string_agg(m.relid::text || ' (' || m.motivo || ')', ', '
                      ORDER BY m.relid::text)
               FILTER (WHERE m.ordinale <= 10),
           jsonb_agg(jsonb_build_object('tabella', m.relid::text,
                                        'motivo',  m.motivo)
                     ORDER BY m.relid::text)
      INTO v_mancanti, v_elenco, v_tabelle
      FROM (SELECT s.relid, s.motivo,
                   row_number() OVER (ORDER BY s.relid::text) AS ordinale
              FROM maintenance.vw_statistiche_mancanti s
             WHERE p_tabelle IS NULL
                OR s.relid = ANY (p_tabelle)) m;

    IF v_mancanti > 0 THEN
        -- TECNICO: nessun operatore ha un gesto da fare; il
        --   rimedio e' un diritto al ruolo del job (provisioning)
        --   o una tabella da guardare.
        PERFORM script.fn_log_and_raise_error(
            'maintenance',
            'fn_analyze_statistiche',
            'E_STATISTICHE_MANCANTI',
            jsonb_build_object(
                'tabelle', v_tabelle,
                'ruolo',   current_user),
            NULL::uuid,
            v_mancanti::text,
            v_elenco);
    END IF;

    RETURN v_mancanti;
END;
$function$

COMMENT ON FUNCTION maintenance.fn_analyze_statistiche(p_tabelle regclass[])
IS 'ANALYZE del database (p_tabelle NULL, il job notturno analyze_statistiche e la convergenza in CI) o delle tabelle indicate, poi l''AUTOVERIFICA nella stessa transazione: se maintenance.vw_statistiche_mancanti ha ancora una tabella (nel perimetro, o fra quelle indicate) solleva E_STATISTICHE_MANCANTI con le tabelle nel contesto. ⛔ Senza, un ANALYZE che salta meta'' delle tabelle (lo fa con un WARNING, senza fallire) lascerebbe «done» nel giornale. ⭐ La verifica sta qui e non in una vista guardata dal digest: subito dopo ANALYZE una tabella senza statistiche e'' un errore, in un''ora qualunque potrebbe essere solo nata da poco. Una transazione sola (la CI la chiama dentro un changeSet): SHARE UPDATE EXCLUSIVE su ogni tabella fino alla fine, che blocca DDL e autovacuum ma non letture e scritture. Il catalogo di sistema e'' analizzato se il ruolo e'' proprietario del database o superuser, e resta fuori dall''autoverifica (D-1). Brief: brief-db-statistiche-tabelle-job-notturno (D15).';
```

</div>

---
{% include-markdown "signature-core.md" %}
