{% include-markdown "it/dbzero/dbops/manual/fn_genera_risolutori_emittente.md" %}
# ⚙️ Funzione `fn_genera_risolutori_emittente`

```sql
CREATE FUNCTION fn_genera_risolutori_emittente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_genera_risolutori_emittente()
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
  r          record;
  -- testi da confrontare e da eseguire: nessuna colonna da ancorare
  v_corpo    text;
  v_commento text;
  v_vivo     pg_catalog.pg_proc.prosrc%TYPE;
  v_vivo_com text;
  v_oid      pg_catalog.pg_proc.oid%TYPE;
  -- un conteggio
  n          integer := 0;
BEGIN
  -- Scopo: riscrivere i due risolutori dell'emittente dal registro,
  --   solo se sono cambiati. Restituisce quanti ne ha riscritti.
  FOR r IN
    SELECT * FROM (VALUES
      (false,
       'script.fn_resolve_emittente_fiscale_id(text,bigint)',
       $sig$script.fn_resolve_emittente_fiscale_id(
    p_modo   dbops.emittente_modi.modo%TYPE,
    -- polimorfo: l'id della riga che p_modo nomina, in tabelle diverse
    p_valore bigint)
 RETURNS anagrafiche.emittenti_fiscali.id%TYPE$sig$,
       'Dice DI CHI E'' una riga: l''id dell''emittente fiscale raggiunto da p_valore secondo p_modo, o NULL se il riferimento non porta a nessun emittente («nessun padrone»: il guard lascia passare). I modi e le loro strade sono le righe di dbops.emittente_modi, e il corpo lo genera dbops.fn_genera_risolutori_emittente: non si modifica a mano. Un modo sconosciuto solleva E_PARAMETRO_INVALIDO, non risponde NULL. SECURITY DEFINER del proprietario, perche'' le strade passano da tabelle sotto row security e un chiamante fuori perimetro non troverebbe l''emittente; search_path bloccato. Risponde solo alla domanda di fatto: il permesso e'' di script.fn_check_user_emittente_scope. La chiamano le policy ef_whitelist, gli adattatori script.fn_scope_ef_whitelist_via_* e il guard di scrittura script.trgfn_guard_emittente_scope.'),
      (true,
       'script.fn_resolve_emittente_sr_id(text,bigint)',
       $sig$script.fn_resolve_emittente_sr_id(
    p_modo   dbops.emittente_modi.modo%TYPE,
    -- polimorfo: l'id della riga che p_modo nomina, in tabelle diverse
    p_valore bigint)
 RETURNS anagrafiche.soggetti_ruoli.id%TYPE$sig$,
       'Il gemello in convenzione soggetto-ruolo di script.fn_resolve_emittente_fiscale_id: il soggetto_ruolo_id dell''emittente raggiunto da p_valore secondo p_modo, o NULL. Stessi modi e stesse strade (le righe di dbops.emittente_modi), con un''altra risposta in fondo: la colonna del soggetto-ruolo, o quella dell''emittente fiscale della radice. Il corpo lo genera dbops.fn_genera_risolutori_emittente: non si modifica a mano. Il doppio binario PK/SR e'' una scelta dichiarata del progetto. Un modo sconosciuto solleva E_PARAMETRO_INVALIDO. SECURITY DEFINER per la stessa ragione del gemello; search_path bloccato. La chiama il giornale degli eventi (vendite.trgfn_event_log_deriva_scope).')
    ) AS v(in_sr, firma, intestazione, commento)
  LOOP
    v_corpo := dbops.fn_risolutore_emittente_corpo(r.in_sr);
    v_commento := r.commento;
    v_oid := pg_catalog.to_regprocedure(r.firma);

    v_vivo := NULL;
    v_vivo_com := NULL;
    IF v_oid IS NOT NULL THEN
      SELECT p.prosrc INTO v_vivo FROM pg_catalog.pg_proc p WHERE p.oid = v_oid;
      v_vivo_com := pg_catalog.obj_description(v_oid, 'pg_proc');
    END IF;

    IF v_vivo IS DISTINCT FROM v_corpo OR v_vivo_com IS DISTINCT FROM v_commento THEN
      EXECUTE 'CREATE OR REPLACE FUNCTION ' || r.intestazione || E'\n'
           || E' LANGUAGE plpgsql\n STABLE SECURITY DEFINER\n'
           || E' SET search_path TO ''pg_catalog'', ''pg_temp''\n'
           || 'AS $corpo$' || v_corpo || '$corpo$';
      EXECUTE format('COMMENT ON FUNCTION %s IS %L', r.firma, v_commento);
      n := n + 1;
    END IF;
  END LOOP;

  RETURN n;
END
$function$

COMMENT ON FUNCTION dbops.fn_genera_risolutori_emittente()
IS 'Riscrive script.fn_resolve_emittente_fiscale_id e script.fn_resolve_emittente_sr_id dal registro dbops.emittente_modi (corpo da dbops.fn_risolutore_emittente_corpo), con la loro firma, SECURITY DEFINER e search_path bloccato, solo se il corpo o il COMMENT vivi sono diversi; restituisce quante funzioni ha riscritto (a regime zero). La chiama il changeSet di convergenza di 90_end a ogni migrate, dopo il seed del registro. Funziona solo dal proprietario delle due funzioni.';
```

</div>

---
{% include-markdown "signature-core.md" %}
