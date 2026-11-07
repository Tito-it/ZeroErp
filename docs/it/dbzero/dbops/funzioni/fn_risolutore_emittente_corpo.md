{% include-markdown "it/dbzero/dbops/manual/fn_risolutore_emittente_corpo.md" %}
# ⚙️ Funzione `fn_risolutore_emittente_corpo`

```sql
CREATE FUNCTION fn_risolutore_emittente_corpo(p_in_soggetto_ruolo boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_risolutore_emittente_corpo(p_in_soggetto_ruolo boolean)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  r            dbops.emittente_modi%ROWTYPE;
  v_cur        dbops.emittente_modi%ROWTYPE;
  v_padre      dbops.emittente_modi%ROWTYPE;
  v_rel        regclass;
  -- i problemi del registro, detti tutti insieme: nessuna colonna da ancorare
  v_problemi   text[] := ARRAY[]::text[];
  -- i pezzi del testo generato: nessuna colonna da ancorare
  v_from       text;
  v_risposta   text;
  v_rami       text := '';
  v_modi       text;
  v_funzione   text;
  v_tipo       text;
  -- quanti salti dalla riga alla radice: un conteggio
  v_passi      integer;
BEGIN
  -- Scopo: il testo del corpo di un risolutore dell'emittente,
  --   dal registro dbops.emittente_modi.
  IF p_in_soggetto_ruolo IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
        'database', 'dbops.fn_risolutore_emittente_corpo', 'E_DBOPS_CHIAMATA_NON_VALIDA',
        jsonb_build_object('campo', 'p_in_soggetto_ruolo'),
        NULL::uuid,
        'dbops.fn_risolutore_emittente_corpo',
        'p_in_soggetto_ruolo e'' obbligatorio: false per il risolutore fiscale, true per il soggetto-ruolo');
  END IF;

  -- 1) Il registro si controlla tutto, prima di scrivere una riga.
  FOR r IN SELECT * FROM dbops.emittente_modi m ORDER BY m.modo LOOP
    v_rel := pg_catalog.to_regclass(format('%I.%I', r.schema_tabella, r.nome_tabella));
    IF v_rel IS NULL THEN
      v_problemi := array_append(v_problemi,
          format('%s: la tabella %s.%s non esiste', r.modo, r.schema_tabella, r.nome_tabella));
    ELSE
      IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                      WHERE a.attrelid = v_rel AND a.attname = r.colonna_chiave
                        AND a.attnum > 0 AND NOT a.attisdropped) THEN
        v_problemi := array_append(v_problemi,
            format('%s: %s.%s non ha la colonna chiave %s', r.modo, r.schema_tabella, r.nome_tabella, r.colonna_chiave));
      END IF;
      IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                      WHERE a.attrelid = v_rel AND a.attname = r.colonna
                        AND a.attnum > 0 AND NOT a.attisdropped) THEN
        v_problemi := array_append(v_problemi,
            format('%s: %s.%s non ha la colonna %s', r.modo, r.schema_tabella, r.nome_tabella, r.colonna));
      END IF;
    END IF;

    -- la catena dei salti arriva a una radice, senza giri
    v_cur := r;
    v_passi := 0;
    WHILE v_cur.forma = 'SALTO' AND v_passi <= 10 LOOP
      SELECT * INTO v_cur FROM dbops.emittente_modi m WHERE m.modo = v_cur.modo_padre;
      v_passi := v_passi + 1;
    END LOOP;
    IF v_cur.forma = 'SALTO' THEN
      v_problemi := array_append(v_problemi,
          format('%s: la catena dei salti non arriva a una radice in 10 passi (un giro?)', r.modo));
    END IF;
  END LOOP;

  IF NOT EXISTS (SELECT 1 FROM dbops.emittente_modi) THEN
    v_problemi := array_append(v_problemi, 'il registro e'' vuoto');
  END IF;

  IF cardinality(v_problemi) > 0 THEN
    PERFORM script.fn_log_and_raise_error(
        'database', 'dbops.fn_risolutore_emittente_corpo', 'E_EMITTENTE_MODI_INVALIDO',
        jsonb_build_object('problemi', to_jsonb(v_problemi)),
        NULL::uuid,
        array_to_string(v_problemi, '; '));
  END IF;

  -- 2) Un ramo per modo: la riga (t0), i salti (t1, t2, …), la radice.
  FOR r IN SELECT * FROM dbops.emittente_modi m ORDER BY m.modo LOOP
    v_from := format('%I.%I t0', r.schema_tabella, r.nome_tabella);
    v_cur := r;
    v_passi := 0;
    WHILE v_cur.forma = 'SALTO' LOOP
      SELECT * INTO v_padre FROM dbops.emittente_modi m WHERE m.modo = v_cur.modo_padre;
      v_passi := v_passi + 1;
      v_from := v_from || format(E'\n          JOIN %I.%I t%s ON t%s.%I = t%s.%I',
                                 v_padre.schema_tabella, v_padre.nome_tabella, v_passi,
                                 v_passi, v_padre.colonna_chiave, v_passi - 1, v_cur.colonna);
      v_cur := v_padre;
    END LOOP;

    IF NOT p_in_soggetto_ruolo AND v_cur.forma = 'PK' THEN
      v_risposta := format('t%s.%I', v_passi, v_cur.colonna);
    ELSIF NOT p_in_soggetto_ruolo THEN
      v_from := v_from || format(E'\n          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = t%s.%I',
                                 v_passi, v_cur.colonna);
      v_risposta := 'ef.id';
    ELSIF v_cur.forma = 'SR' THEN
      v_risposta := format('t%s.%I', v_passi, v_cur.colonna);
    ELSE
      v_from := v_from || format(E'\n          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t%s.%I',
                                 v_passi, v_cur.colonna);
      v_risposta := 'ef.soggetto_ruolo_id';
    END IF;

    v_rami := v_rami || format(
        E'    %s p_modo = %L THEN\n        SELECT %s\n          INTO v_risultato\n          FROM %s\n         WHERE t0.%I = p_valore;\n',
        CASE WHEN v_rami = '' THEN 'IF' ELSE 'ELSIF' END,
        r.modo, v_risposta, v_from, r.colonna_chiave);
  END LOOP;

  SELECT string_agg(m.modo, ', ' ORDER BY m.modo) INTO v_modi FROM dbops.emittente_modi m;

  IF p_in_soggetto_ruolo THEN
    v_funzione := 'script.fn_resolve_emittente_sr_id';
    v_tipo     := 'anagrafiche.soggetti_ruoli.id%TYPE';
  ELSE
    v_funzione := 'script.fn_resolve_emittente_fiscale_id';
    v_tipo     := 'anagrafiche.emittenti_fiscali.id%TYPE';
  END IF;

  RETURN
       E'\nDECLARE\n    v_risultato ' || v_tipo || E';\nBEGIN\n'
    || E'    -- =========================================================\n'
    || E'    -- GENERATO da dbops.fn_genera_risolutori_emittente dal registro\n'
    || E'    -- dbops.emittente_modi: non si modifica a mano, il migrate\n'
    || E'    -- successivo lo riscriverebbe. Un modo nuovo e'' una riga del\n'
    || E'    -- seed 80_data/sql/dbops/emittente_modi.csv.\n'
    || E'    --\n'
    || CASE WHEN p_in_soggetto_ruolo
         THEN E'    -- Scopo: il soggetto-ruolo dell''emittente di una riga, o NULL\n'
           || E'    --   se il riferimento non porta a nessun emittente.\n'
         ELSE E'    -- Scopo: l''id dell''emittente fiscale di una riga, o NULL se il\n'
           || E'    --   riferimento non porta a nessun emittente.\n'
       END
    || E'    --\n'
    || E'    -- SECURITY DEFINER: le strade passano da tabelle con la ROW\n'
    || E'    --   SECURITY accesa, e per chi e'' fuori perimetro la riga non\n'
    || E'    --   c''e'': «non la vedo» non e'' «non esiste». Dipende dalla RLS\n'
    || E'    --   abilitata e non forzata (il proprietario la salta).\n'
    || E'    -- =========================================================\n'
    || E'    IF p_valore IS NULL THEN\n        RETURN NULL;\n    END IF;\n\n'
    || v_rami
    || E'    ELSE\n'
    || E'        -- Un modo sconosciuto solleva: NULL vorrebbe dire «nessun\n'
    || E'        -- padrone», e un refuso in un montaggio spegnerebbe il guard.\n'
    || E'        PERFORM script.fn_log_and_raise_error(\n'
    || E'            ''database'',\n'
    || E'            ' || quote_literal(v_funzione) || E',\n'
    || E'            ''E_PARAMETRO_INVALIDO'',\n'
    || E'            jsonb_build_object(\n'
    || E'                ''detail'', ''Modo di risoluzione sconosciuto'',\n'
    || E'                ''modo'',   p_modo,\n'
    || E'                ''valore'', p_valore\n'
    || E'            ),\n'
    || E'            NULL::uuid,\n'
    || E'            format(\n'
    || E'                ''il modo di risoluzione dell''''emittente «%s» non esiste: sono ammessi %s'',\n'
    || E'                p_modo,\n'
    || E'                ' || quote_literal(v_modi) || E'\n'
    || E'            )\n'
    || E'        );\n'
    || E'    END IF;\n\n'
    || E'    RETURN v_risultato;\n'
    || E'END\n';
END
$function$

COMMENT ON FUNCTION dbops.fn_risolutore_emittente_corpo(p_in_soggetto_ruolo boolean)
IS 'Il corpo (prosrc) di un risolutore dell''emittente, scritto dal registro dbops.emittente_modi: false per script.fn_resolve_emittente_fiscale_id, true per script.fn_resolve_emittente_sr_id. Un ramo per modo, in ordine di modo, con SQL statico: la riga per colonna_chiave, un JOIN per ogni salto verso la testata, la radice che da'' l''emittente fiscale (PK) o il soggetto-ruolo (SR), con un JOIN su anagrafiche.emittenti_fiscali quando la radice e'' nell''altra convenzione. Il ramo ELSE solleva E_PARAMETRO_INVALIDO con l''elenco dei modi del registro. Prima di scrivere controlla il registro (tabella, colonna chiave, colonna, catena dei salti senza giri) e dice tutti i problemi insieme con E_EMITTENTE_MODI_INVALIDO. Lo usano dbops.fn_genera_risolutori_emittente e il pgTAP che confronta il corpo vivo col registro.';
```

</div>

---
{% include-markdown "signature-core.md" %}
