# ⚙️ Funzione `fn_annulla_ddt`

```sql
CREATE FUNCTION fn_annulla_ddt(p_ddt_id bigint, p_righe_legate_confermate integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_ddt(p_ddt_id bigint, p_righe_legate_confermate integer DEFAULT NULL::integer)
 RETURNS TABLE(movimento_id bigint, prelievo_id bigint, qta numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
#variable_conflict use_column
-- =========================================================
-- Scopo: annullare una bolla (D-8 di brief-db-ddt-righe-evase-
--   dall-ordine). Con legami: la conferma dichiara quante righe
--   legate si sono viste, i legami si ritirano, poi lo stato passa
--   dal verbo di stato. p_righe_legate_confermate e' un CONTEGGIO:
--   tipo nudo. Vedi l'intestazione del changeSet.
-- Ritorna: i movimenti di storno del verbo di stato (nessuno se la
--   bolla non muove merce).
-- =========================================================
DECLARE
    v_utente       config.user_override_azioni.auth_user_id%TYPE;
    v_numero       vendite.ddt.numero%TYPE;
    -- CONTEGGIO delle righe legate: nessuna colonna da ancorare.
    v_righe_legate integer;
    v_riga_id      vendite.ddt_righe.id%TYPE;
BEGIN
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametri.
    IF p_ddt_id IS NULL OR p_ddt_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_ddt',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_ddt_id', p_ddt_id),
            NULL::uuid, 'vendite.fn_annulla_ddt',
            'p_ddt_id (obbligatorio, maggiore di zero)');
    END IF;

    -- 2. La testata FOR UPDATE, nel perimetro (predicato della policy:
    --    DEFINER). Fuori perimetro come inesistente.
    SELECT d.numero
      INTO v_numero
      FROM vendite.ddt d
     WHERE d.id = p_ddt_id
       AND script.fn_scope_ef_whitelist_via_ddt(v_utente, d.id)
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_ddt',
            'E_DDT_NOT_FOUND', jsonb_build_object('ddt_id', p_ddt_id), NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 3. La conferma: dichiara quante righe legate si sono viste.
    SELECT count(DISTINCT l.ddt_riga_id)::integer
      INTO v_righe_legate
      FROM vendite.fn_ddt_legami(p_ddt_id) AS l;

    IF v_righe_legate > 0
       AND p_righe_legate_confermate IS DISTINCT FROM v_righe_legate THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_ddt',
            'E_DDT_ANNULLO_CON_LEGAMI',
            jsonb_build_object('ddt_id',       p_ddt_id,
                               'numero',       v_numero,
                               'righe_legate', v_righe_legate,
                               'confermate',   p_righe_legate_confermate),
            NULL::uuid,
            'DDT ' || COALESCE(v_numero, '#' || p_ddt_id::text),
            v_righe_legate::text);
    END IF;

    -- 4. Il ritiro, riga per riga, con la porta dell'annullo aperta
    --    per QUESTA bolla.
    IF v_righe_legate > 0 THEN
        PERFORM set_config('zeroerp.ddt_annullo', p_ddt_id::text, true);
        FOR v_riga_id IN
            SELECT DISTINCT l.ddt_riga_id
              FROM vendite.fn_ddt_legami(p_ddt_id) AS l
             ORDER BY l.ddt_riga_id
        LOOP
            PERFORM vendite.fn_ddt_riga_ritira_legami(v_riga_id);
        END LOOP;
        PERFORM set_config('zeroerp.ddt_annullo', '', true);
    END IF;

    -- 5. Lo stato, dal verbo di stato: matrice, permesso, storno.
    RETURN QUERY
        SELECT c.movimento_id, c.prelievo_id, c.qta
          FROM vendite.fn_cambia_stato_ddt(p_ddt_id, 'ANNULLATO') AS c;
END;
$function$

COMMENT ON FUNCTION vendite.fn_annulla_ddt(p_ddt_id bigint, p_righe_legate_confermate integer)
IS 'VERBO (2026-10-11, brief-db-ddt-righe-evase-dall-ordine D-8): annulla una bolla. Se porta legami con ordini o resi (vendite.fn_ddt_legami), chi conferma DICHIARA quante righe legate ha visto (p_righe_legate_confermate): se non corrisponde, E_DDT_ANNULLO_CON_LEGAMI, lo stesso avviso del guard di transizione (stampo di E_CREDENZIALE_DA_CONFERMARE). Poi, con la porta dell''annullo aperta (GUC transazionale zeroerp.ddt_annullo = id della bolla; il guard del legame vuole anche il proprietario), ritira i legami riga per riga (vendite.fn_ddt_riga_ritira_legami: gli ordini si riproiettano, i resi tornano da ri-consegnare) e infine passa lo stato a ANNULLATO da vendite.fn_cambia_stato_ddt, che applica matrice, permesso emetti_ddt sull''annullo di una emessa e storno del magazzino, e ne restituisce i movimenti. UNA transazione. Una bolla senza legami non ha niente da confermare. Testata FOR UPDATE nel perimetro (script.fn_scope_ef_whitelist_via_ddt; fuori perimetro E_DDT_NOT_FOUND). SECURITY DEFINER con search_path bloccato; EXECUTE solo all''app.';
```

---
{% include-markdown "signature-core.md" %}
