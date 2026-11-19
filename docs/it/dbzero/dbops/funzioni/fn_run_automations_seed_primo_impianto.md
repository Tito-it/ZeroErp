{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_seed_primo_impianto.md" %}
# ⚙️ Funzione `fn_run_automations_seed_primo_impianto`

```sql
CREATE FUNCTION fn_run_automations_seed_primo_impianto(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_seed_primo_impianto(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
/*
  Scopo
  Porta i trigger del seed di primo impianto (script.trgfn_seed_primo_impianto)
  delle tabelle in scope allo stato che dichiara
  dbops.automazione_seed_primo_impianto. Il confronto fra atteso e vivo lo fa
  dbops.fn_seed_primo_impianto_divergenze: qui si esegue l'azione.

  Azioni
  CREA      il trigger atteso, poi l'iscrizione delle righe di seed gia' presenti
  RIGENERA  toglie tutti i trigger vivi della funzione sulla tabella, qualunque
            nome abbiano, e crea quello atteso
  TOGLIE    toglie tutti i trigger vivi (la riga e' spenta); il registro
            dbops.seed_righe resta, e torna buono se la riga si riaccende
  NON_CLASSIFICATA, SENZA_ID
            nessuna DDL: WARN nell'audit, il trigger di prima resta

  Trigger fuori dal registro
  Un trigger della funzione su una tabella che il registro non nomina
  (SCONOSCIUTO) ferma il giro con E_SEED_PRIMO_IMPIANTO, prima di qualunque
  DDL. Si aggiunge la riga (enabled = false se il trigger va tolto).

  Righe su tabelle che non esistono: WARN TABLE_NOT_FOUND.

  DRY RUN
  p_dry_run = true: nessuna DDL, l'azione nell'audit (dbops.fn_audit_log_once).
*/
DECLARE
  -- Il contesto dell'errore, costruito una volta e usato dalle due
  -- chiamate del gestore (registro e involucro).
  v_ctx_errore dbops.error_log.context%TYPE;
  -- text[]: %TYPE non fa array
  v_schemas text[];
  rconf record;
  r record;
  -- text nudi: un nome di trigger letto da pg_trigger (tipo name) e
  -- l'elenco dei trigger sconosciuti per il messaggio
  v_trg text;
  v_sconosciuti text;
  -- integer: un conteggio
  v_segnate integer;
BEGIN
  v_schemas := dbops.fn_resolve_scope(p_schemas);

  -- Le righe che puntano a una tabella che non c'e': un salto dichiarato.
  FOR rconf IN
    SELECT d.*
      FROM dbops.automazione_seed_primo_impianto d
     WHERE d.enabled
       AND d.schema_name = ANY(v_schemas)
       AND to_regclass(format('%I.%I', d.schema_name, d.table_name)) IS NULL
     ORDER BY d.id
  LOOP
    PERFORM dbops.fn_audit_log_once(
      p_function_name => 'dbops.fn_run_automations_seed_primo_impianto',
      p_status        => 'WARN',
      p_rule_type     => 'SEED_PRIMO_IMPIANTO',
      p_exec_mode     => p_exec_mode,
      p_parts         => ARRAY['SEED_PRIMO_IMPIANTO'],
      p_dry_run       => p_dry_run,
      p_params        => jsonb_build_object(
                          'action','SKIP',
                          'reason','TABLE_NOT_FOUND',
                          'table', rconf.schema_name||'.'||rconf.table_name
                        ),
      p_message       => 'Skip: table not found'
    );
  END LOOP;

  IF NOT p_dry_run THEN
    SELECT string_agg(d.schema_name||'.'||d.table_name||' ('||array_to_string(d.trigger_vivi, ', ')||')',
                      '; ' ORDER BY d.schema_name, d.table_name)
      INTO v_sconosciuti
      FROM dbops.fn_seed_primo_impianto_divergenze(p_schemas) AS d
     WHERE d.azione = 'SCONOSCIUTO';

    IF v_sconosciuti IS NOT NULL THEN
      PERFORM script.fn_log_and_raise_error(
          'database',
          'dbops.fn_run_automations_seed_primo_impianto',
          'E_SEED_PRIMO_IMPIANTO',
          jsonb_build_object('where', 'SEED_PRIMO_IMPIANTO_FUORI_REGISTRO', 'tabelle', v_sconosciuti),
          NULL::uuid,
          format('trigger del seed di primo impianto su tabelle che dbops.automazione_seed_primo_impianto non nomina: %s. '
                 'Aggiungere la riga (enabled = false se il trigger va tolto) prima di convergere',
                 v_sconosciuti));
    END IF;
  END IF;

  FOR r IN
    SELECT d.*
      FROM dbops.fn_seed_primo_impianto_divergenze(p_schemas) AS d
     ORDER BY d.schema_name, d.table_name
  LOOP
    IF r.azione IN ('NON_CLASSIFICATA', 'SENZA_ID') THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_run_automations_seed_primo_impianto',
        p_status        => 'WARN',
        p_rule_type     => 'SEED_PRIMO_IMPIANTO',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['SEED_PRIMO_IMPIANTO'],
        p_dry_run       => p_dry_run,
        p_params        => jsonb_build_object(
                            'action',                   'SKIP',
                            'reason',                   r.azione,
                            'table',                    r.schema_name||'.'||r.table_name,
                            'trigger_vivi',             r.trigger_vivi,
                            'colonne_non_classificate', r.colonne_non_classificate,
                            'colonne_assenti',          r.colonne_assenti
                          ),
        p_message       => 'Seed primo impianto: '||r.azione||', trigger lasciato com''e'''
      );
      CONTINUE;
    END IF;

    IF p_dry_run THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_run_automations_seed_primo_impianto',
        p_status        => 'DRYRUN',
        p_rule_type     => 'SEED_PRIMO_IMPIANTO',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['SEED_PRIMO_IMPIANTO'],
        p_dry_run       => true,
        p_params        => jsonb_build_object(
                            'table',        r.schema_name||'.'||r.table_name,
                            'trigger',      r.trigger_atteso,
                            'argomenti',    r.argomenti_attesi,
                            'trigger_vivi', r.trigger_vivi,
                            'action',       'DRYRUN_'||r.azione
                          ),
        p_message       => 'Seed primo impianto: '||r.azione
      );
      CONTINUE;
    END IF;

    v_segnate := NULL;

    BEGIN
      FOREACH v_trg IN ARRAY r.trigger_vivi LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I', v_trg, r.schema_name, r.table_name);
      END LOOP;

      IF r.azione IN ('CREA', 'RIGENERA') THEN
        EXECUTE format(
          'CREATE TRIGGER %I BEFORE INSERT OR UPDATE OR DELETE ON %I.%I '
          'FOR EACH ROW EXECUTE FUNCTION script.trgfn_seed_primo_impianto(%s)',
          r.trigger_atteso, r.schema_name, r.table_name,
          (SELECT string_agg(quote_literal(x), ', ' ORDER BY o)
             FROM unnest(r.argomenti_attesi) WITH ORDINALITY AS u(x, o)));
      END IF;

      -- L'iscrizione: solo alla nascita del trigger. Le righe di seed che
      -- ci sono gia' entrano nel registro; le altre restano
      -- dell'installazione.
      IF r.azione = 'CREA' THEN
        IF NOT EXISTS (
             SELECT 1 FROM pg_catalog.pg_attribute a
              WHERE a.attrelid = format('%I.%I', r.schema_name, r.table_name)::regclass
                AND a.attname = 'user_insert' AND a.attnum > 0 AND NOT a.attisdropped) THEN
          PERFORM script.fn_log_and_raise_error(
              'database',
              'dbops.fn_run_automations_seed_primo_impianto',
              'E_SEED_PRIMO_IMPIANTO',
              jsonb_build_object('where', 'SEED_PRIMO_IMPIANTO_SENZA_USER_INSERT',
                                 'table', r.schema_name||'.'||r.table_name),
              NULL::uuid,
              format('%s.%s non ha la colonna user_insert: le righe di seed che ci sono gia'' '
                     'non si riconoscono', r.schema_name, r.table_name));
        END IF;

        EXECUTE format(
          'INSERT INTO dbops.seed_righe (schema_name, table_name, riga_id, segnata_da) '
          'SELECT %L, %L, t.id::text, ''ISCRIZIONE'' '
          '  FROM %I.%I t '
          ' WHERE t.user_insert = ''SEED'' OR dbops.fn_ruolo_del_migratore(t.user_insert) '
          'ON CONFLICT ON CONSTRAINT uq_seed_righe_tabella_riga DO NOTHING',
          r.schema_name, r.table_name, r.schema_name, r.table_name);
        GET DIAGNOSTICS v_segnate = ROW_COUNT;
      END IF;
    EXCEPTION WHEN others THEN
      -- ⭐ Un guasto dell'AMBIENTE (script.fn_sqlstate_di_ambiente) si
      --   rilancia COM'E', col suo SQLSTATE, dopo averlo scritto nel registro
      --   errori; gli altri escono con E_SEED_PRIMO_IMPIANTO.
      v_ctx_errore := jsonb_build_object(
          'where','SEED_PRIMO_IMPIANTO',
          'table', r.schema_name||'.'||r.table_name,
          'azione', r.azione,
          'error', SQLERRM
        );
      IF script.fn_sqlstate_di_ambiente(SQLSTATE) THEN
        PERFORM script.fn_log_error_only(
            'dbops', 'run_automations', 'E_SEED_PRIMO_IMPIANTO',
            v_ctx_errore, NULL::uuid, SQLERRM);
        RAISE;
      END IF;
      PERFORM script.fn_log_and_raise_error(
          'dbops', 'run_automations', 'E_SEED_PRIMO_IMPIANTO',
          v_ctx_errore, NULL::uuid, SQLERRM);
    END;

    -- ⭐ Il giro vero lascia traccia: qui l'azione e' fatta.
    PERFORM dbops.fn_audit_log_once(
      p_function_name => 'dbops.fn_run_automations_seed_primo_impianto',
      p_status        => 'OK',
      p_rule_type     => 'SEED_PRIMO_IMPIANTO',
      p_exec_mode     => p_exec_mode,
      p_parts         => ARRAY['SEED_PRIMO_IMPIANTO'],
      p_dry_run       => false,
      p_params        => jsonb_build_object(
                          'table',          r.schema_name||'.'||r.table_name,
                          'trigger',        r.trigger_atteso,
                          'argomenti',      r.argomenti_attesi,
                          'trigger_vivi',   r.trigger_vivi,
                          'action',         r.azione,
                          'righe_segnate',  v_segnate
                        ),
      p_message       => 'Seed primo impianto: '||r.azione
    );
  END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_run_automations_seed_primo_impianto(p_exec_mode text, p_schemas text[], p_dry_run boolean)
IS 'Runner della regola SEED_PRIMO_IMPIANTO: porta i trigger su script.trgfn_seed_primo_impianto delle tabelle in scope allo stato che dichiara dbops.automazione_seed_primo_impianto, con il confronto di dbops.fn_seed_primo_impianto_divergenze. CREA monta il trigger (BEFORE INSERT OR UPDATE OR DELETE FOR EACH ROW, fase a00) e iscrive le righe di seed gia'' presenti in dbops.seed_righe: user_insert = ''SEED'' o un ruolo del migratore (dbops.fn_ruolo_del_migratore), segnata_da ISCRIZIONE; RIGENERA toglie i trigger vivi della funzione e rimonta l''atteso, senza ripassare dall''iscrizione; TOGLIE li toglie (riga spenta), il registro resta. NON_CLASSIFICATA e SENZA_ID non fanno DDL: WARN nell''audit, il trigger di prima resta. Un trigger della funzione su una tabella che il registro non nomina ferma il giro (E_SEED_PRIMO_IMPIANTO), come una tabella iscritta senza user_insert. Un guasto dell''ambiente esce col suo SQLSTATE. p_dry_run = true: nessuna DDL, l''azione nell''audit. Lo chiamano maintenance.proc_automations_lock_columns_job (convergenza del rilascio e giro notturno) e la rete di 90_end a ogni migrate.';
```

</div>

---
{% include-markdown "signature-core.md" %}
