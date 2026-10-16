{% include-markdown "it/dbzero/dbops/manual/fn_ensure_storico_table.md" %}
# ⚙️ Funzione `fn_ensure_storico_table`

```sql
CREATE FUNCTION fn_ensure_storico_table(p_schema_base text, p_table_base text, p_fk_col text, p_create_gin_index boolean, p_dry_run boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_ensure_storico_table(p_schema_base text, p_table_base text, p_fk_col text, p_create_gin_index boolean, p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- ⭐ Rev 2026-10-16: il contesto dell'errore, costruito una volta e usato
  --   dalle due chiamate del gestore (registro e involucro).
  v_ctx_errore dbops.error_log.context%TYPE;
  v_exists      boolean;
  v_sql         text;

  -- nome tabella storico = stesso nome della base, schema 'storico'
  v_tbl_sto     text := format('%I', p_table_base);
  v_full_base   text := format('%I.%I', p_schema_base, p_table_base);
  v_full_sto    text := format('storico.%I', v_tbl_sto);

  -- PK padre (monocolonna) e tipo per allineare la FK
  v_parent_reg  regclass := (quote_ident(p_schema_base)||'.'||quote_ident(p_table_base))::regclass;
  v_parent_pk   text;
  v_parent_pk_n int;
  v_fk_type     text;

  -- nomi vincoli/indici
  v_pk_name     text := format('pk_%s_%s', 'storico', p_table_base);
  v_fk_name     text := format('fk_%s', p_table_base);
  v_ix_fk_name  text := format('ix_%s_%s_fk', p_table_base, p_fk_col);
  v_ix_gin_name text := format('ix_%s_snapshot_gin', p_table_base);
  -- rev 2026-09-11 (D-a): la shadow appartiene a chi possiede la madre
  v_owner_madre text := (SELECT pg_get_userbyid(c.relowner) FROM pg_catalog.pg_class c WHERE c.oid = v_parent_reg);
BEGIN

      /*
      Scopo
      -----
      Provisioning "on demand" della tabella di storico (schema: storico) associata a una tabella base.
      Crea la tabella storico SOLO se non esiste, con struttura standard (id seriale, fk logica, snapshot jsonb,
      metadati di audit e finestre di validità).

      Convenzioni
      ----------
      - Tabella storico: schema fisso 'storico', nome = stesso nome della tabella base.
      - PK storico: BIGSERIAL 'id' (indipendente dalla PK del padre).
      - Collegamento al padre: colonna p_fk_col (tipizzata come PK del padre, se determinabile).
      - FK fisica verso la tabella base: NON creata volutamente (evita blocchi su delete/cleanup e vincoli operativi).

      Input / Parametri
      -----------------
      - p_schema_base: schema della tabella base (es. 'anagrafiche').
      - p_table_base : nome tabella base.
      - p_fk_col     : nome della colonna nella tabella storico che conterrà l'id logico del record padre.
      - p_create_gin_index: se true crea indice GIN su snapshot.
      - p_dry_run    : se true non esegue DDL, ma registra audit "would be created".

      Note operative
      --------------
      - La tipizzazione della colonna fk logica tenta di leggere la PK monocampo del padre; fallback su 'id'.
      - In caso di errore DDL viene loggato e rilanciato tramite script.fn_log_and_raise_error.
    */



  -- esiste già la tabella storico?<— esci
  SELECT EXISTS (
    SELECT 1
    FROM pg_class c
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='storico' AND c.relname=p_table_base AND c.relkind='r'
  ) INTO v_exists;
  IF v_exists THEN
    RETURN;
  END IF;

  -- PK e tipo dal padre (assume PK monocampo; fallback su 'id')
  SELECT a.attname, array_length(i.indkey,1)
    INTO v_parent_pk, v_parent_pk_n
  FROM pg_index i
  JOIN pg_attribute a
    ON a.attrelid=i.indrelid AND a.attnum = i.indkey[0]
  WHERE i.indrelid = v_parent_reg
    AND i.indisprimary
    AND array_length(i.indkey,1)=1
  LIMIT 1;

  IF v_parent_pk IS NOT NULL THEN
    SELECT format_type(att.atttypid, att.atttypmod)
      INTO v_fk_type
    FROM pg_attribute att
    WHERE att.attrelid = v_parent_reg
      AND att.attname  = v_parent_pk
      AND NOT att.attisdropped;
  END IF;

  IF v_fk_type IS NULL THEN
    v_parent_pk := 'id';
    SELECT format_type(att.atttypid, att.atttypmod)
      INTO v_fk_type
    FROM pg_attribute att
    WHERE att.attrelid = v_parent_reg
      AND att.attname  = 'id'
      AND NOT att.attisdropped;

    IF v_fk_type IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'dbops',
        'fn_run_automations_storico_provision',
        'E_STORICO_PARENT_PK_NOT_FOUND',
        jsonb_build_object('schema',p_schema_base,'table',p_table_base),
        NULL::uuid,
        p_schema_base, p_table_base
      );
      RETURN;
    END IF;
  END IF;

  -- DDL: tabella, commenti, FK, indici (no indice su ts; non esiste più)
  v_sql := format($ddl$
    CREATE SCHEMA IF NOT EXISTS storico;
    CREATE TABLE IF NOT EXISTS %s (
      id              BIGSERIAL,
      %I              %s NOT NULL,
      change_type     char(1) DEFAULT 'A',
      tipo_operazione smallint,
      snapshot        jsonb,
      user_insert     text DEFAULT CURRENT_USER,
      data_insert     timestamptz DEFAULT now(),
      tx_id           uuid,
      valid_from      timestamptz DEFAULT now(),
      valid_to        timestamptz,
      CONSTRAINT %I PRIMARY KEY (id)
    );
    COMMENT ON COLUMN %s.change_type
      IS 'Tipo di cambiamento: A=Active, S=Suppressed, F=Fused, D=Divided';
    COMMENT ON COLUMN %s.tipo_operazione
      IS 'Tipo operazione (1=insert, 2=update, 3=delete)';

  -- non si genera più la fk perchè bloccerebbe la cancellazione delle righe della tabella e non è corretto
  -- si crea solo l'indice.
  -- ALTER TABLE %s
  --   ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES %s(%I);

    CREATE INDEX IF NOT EXISTS %I ON %s (%I);
  $ddl$,
    v_full_sto,
    p_fk_col, v_fk_type,
    v_pk_name,
    v_full_sto,
    v_full_sto,
    v_full_sto,
    v_fk_name, p_fk_col, v_full_base, v_parent_pk,
    v_ix_fk_name, v_full_sto, p_fk_col
  );

  IF p_create_gin_index THEN
    v_sql := v_sql || format(E'\nCREATE INDEX IF NOT EXISTS %I ON %s USING GIN (snapshot);\n',
                            v_ix_gin_name, v_full_sto);
  END IF;

  IF p_dry_run THEN
    PERFORM dbops.fn_audit_log_once(
      p_function_name => 'fn_run_automations_storico_provision',
      p_status        => 'DRYRUN',
      p_rule_type     => 'STORICO_PROVISION',
      p_dry_run       => true,
      p_params        => jsonb_build_object('table', v_full_sto, 'action','CREATE_STORICO_TABLE'),
      p_message       => 'Storico table would be created'
    );
    RETURN;
  END IF;

  BEGIN
    EXECUTE v_sql;
    PERFORM dbops.fn_audit_log_once(
      p_function_name => 'fn_run_automations_storico_provision',
      p_status        => 'OK',
      p_rule_type     => 'STORICO_PROVISION',
      p_params        => jsonb_build_object('table', v_full_sto, 'action','CREATE_STORICO_TABLE'),
      p_message       => 'Storico table created'
    );
    -- rev 2026-09-11 (brief-db-rls-storico-scope-congelato §4b): la shadow nasce
    -- già nella forma dello scope congelato. La primitiva aggiunge le colonne
    -- origine_schema (NOT NULL: la shadow è vuota) e scope_emittente_fiscale_id
    -- con indice e, se dbops.storico_scope_policy dice che la madre è protetta,
    -- accende la RLS con le sue policy. È la STESSA primitiva che il 90_end
    -- runAlways applica alle shadow esistenti: una sede sola per DDL e commenti.
    -- Se fallisce, fallisce qui dentro e il blocco EXCEPTION lo riporta come
    -- E_STORICO_PROVISION: una shadow senza scope non deve nascere zitta.
    PERFORM dbops.fn_storico_arma_scope(p_schema_base, p_table_base, false);
    -- rev 2026-09-11 (decisione a, brief §4d): L'ARCHIVIO DI UNA TABELLA E' DI
    -- CHI POSSIEDE LA TABELLA. Il job pgAgent crea le shadow come `postgres`, e
    -- da quel momento la convergenza da Liquibase (fn_storico_arma_scope_tutte,
    -- fn_grant_storico_shadows) le salterebbe per sempre. Si cede la proprieta'
    -- al proprietario della madre — DOPO l'armatura, perche' arma solo chi e'
    -- proprietario, cioe' chi ha appena creato. Solo se chi crea puo' farlo
    -- (superuser, o membro del ruolo): altrimenti WARN e la shadow resta di chi
    -- l'ha creata, come prima — mai un errore che fermi la storicizzazione.
    IF v_owner_madre IS NOT NULL
       AND v_owner_madre <> (SELECT pg_get_userbyid(c.relowner) FROM pg_catalog.pg_class c
                              WHERE c.oid = v_full_sto::regclass) THEN
      IF (SELECT r.rolsuper FROM pg_catalog.pg_roles r WHERE r.rolname = current_user)
         OR pg_has_role(current_user, v_owner_madre, 'MEMBER') THEN
        EXECUTE format('ALTER TABLE %s OWNER TO %I', v_full_sto, v_owner_madre);
        PERFORM dbops.fn_audit_log_once(
          p_function_name => 'fn_run_automations_storico_provision',
          p_status        => 'OK',
          p_rule_type     => 'STORICO_PROVISION',
          p_params        => jsonb_build_object('table', v_full_sto, 'action','OWNER_TO_MADRE', 'owner', v_owner_madre),
          p_message       => 'Shadow ceduta al proprietario della madre'
        );
      ELSE
        PERFORM dbops.fn_audit_log_once(
          p_function_name => 'fn_run_automations_storico_provision',
          p_status        => 'WARN',
          p_rule_type     => 'STORICO_PROVISION',
          p_params        => jsonb_build_object('table', v_full_sto, 'action','OWNER_TO_MADRE',
                                                'owner_madre', v_owner_madre, 'current_user', current_user),
          p_message       => 'Shadow NON ceduta: chi la ha creata non puo'' assegnarla al proprietario della madre'
        );
      END IF;
    END IF;
  EXCEPTION WHEN OTHERS THEN
    -- ⭐ Rev 2026-10-16 (brief-db-presidio-job-run-a-chi-tocca D8, D10, D11):
    --   un guasto dell'AMBIENTE (script.fn_sqlstate_di_ambiente: connessione,
    --   risorse, arresto, sistema, privilegio, lock) si rilancia COM'E', col suo
    --   SQLSTATE: l'involucro lo faceva diventare P0001, e il presidio dei job lo
    --   mandava allo sviluppo. Prima si scrive nel registro errori, col contesto.
    v_ctx_errore := jsonb_build_object(
        'action','CREATE_STORICO_TABLE',
        'schema', p_schema_base,
        'table',  p_table_base,
        'target', v_full_sto,
        'fk',     p_fk_col
      );
    IF script.fn_sqlstate_di_ambiente(SQLSTATE) THEN
      PERFORM script.fn_log_error_only(
          'dbops', 'fn_run_automations_storico_provision', 'E_STORICO_PROVISION',
          v_ctx_errore, NULL::uuid, SQLERRM);
      RAISE;
    END IF;
    PERFORM script.fn_log_and_raise_error(
        'dbops', 'fn_run_automations_storico_provision', 'E_STORICO_PROVISION',
        v_ctx_errore, NULL::uuid, SQLERRM);
  END;
END;
$function$

COMMENT ON FUNCTION dbops.fn_ensure_storico_table(p_schema_base text, p_table_base text, p_fk_col text, p_create_gin_index boolean, p_dry_run boolean)
IS 'Provisioning idempotente della tabella di storico (schema storico) per una tabella base.
Crea storico.<table_base> se mancante, con struttura standard (snapshot jsonb, audit cols, finestre valid_from/to)
e indice BTree su fk logica. La FK fisica verso la tabella base NON viene creata per scelta progettuale. Supporta dry-run con audit. Rev 2026-09-11: dopo la creazione chiama dbops.fn_storico_arma_scope, che aggiunge origine_schema e scope_emittente_fiscale_id (con indice) e, se dbops.storico_scope_policy dice che la madre è protetta, accende la RLS con le policy dello scope congelato. Rev 2026-09-11 (decisione a): creata e armata, la shadow viene CEDUTA al proprietario della madre — l''archivio di una tabella è di chi possiede la tabella — così la convergenza da Liquibase non la salta anche quando a crearla è il job pgAgent come postgres. Solo se chi crea può cederla (superuser o membro), altrimenti WARN. Brief: brief-db-rls-storico-scope-congelato §4b, §4d. ⭐ Rev 2026-10-16: nel gestore WHEN others, un guasto dell''AMBIENTE (script.fn_sqlstate_di_ambiente: 08, 53, 57, 58, 42501, 55P03) si rilancia COM''E'', col suo SQLSTATE, dopo averlo scritto nel registro errori con lo stesso codice e contesto (fn_log_error_only). Prima diventava P0001 col codice dell''involucro, e il presidio dei job (maintenance.vw_job_run_da_guardare) lo mandava allo sviluppo. I difetti di struttura escono come prima. Brief: brief-db-presidio-job-run-a-chi-tocca D8, D11.';
```

---
{% include-markdown "signature-core.md" %}
