{% include-markdown "it/dbzero/dbops/manual/fn_apply_chiusura_scadenze.md" %}
# ⚙️ Funzione `fn_apply_chiusura_scadenze`

```sql
CREATE FUNCTION fn_apply_chiusura_scadenze()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_apply_chiusura_scadenze()
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
          -- Scopo:
          --   Esegue la chiusura di stato per scadenza temporale su
          --   tutte le tabelle configurate in
          --   dbops.automazione_chiusura_scadenze (attivo=true).
          --   Ritorna JSONB con conteggio righe chiuse per tabella
          --   target + meta-info esecuzione.
          --
          -- Algoritmo:
          --   1. Pre-check struttura: schema/tabella/colonne esistono;
          --      per tipo_stato=FK anche tabella lookup e codici.
          --   2. UPDATE dinamico (VARCHAR diretto o FK con lookup id).
          --   3. Aggregazione conteggio in JSONB.
          --   4. Audit log dell'esito.
          --
          -- Classe: il registro ammette solo bersagli DOMINIO
          --   (chk_automazione_chiusura_scadenze_classe), che il chiamante
          --   lavora con l'identita' e la RLS di ogni azienda. Un bersaglio di
          --   un'altra classe chiede un esecutore che non c'e': il motore lo
          --   rifiuta (motivo classe_senza_esecutore).
          --
          -- Porta e verbo, valutati PRIMA del dispatch e per ogni tipo_stato:
          --   - un verbo di chiusura dichiarato si usa sempre: e' la porta del
          --     dominio, e lo stato lo scrive lui;
          --   - una testata sotto la porta (script.trgfn_doc_stato_solo_dal_verbo)
          --     senza verbo e' una configurazione non valida: l'UPDATE dinamico
          --     sarebbe rifiutato (E_DOC_STATO_SOLO_DAL_VERBO);
          --   - senza porta e senza verbo: UPDATE dinamico.
          --
          -- Sicurezza SQL dinamico:
          --   - format(%I) per identificatori (quote_ident implicito)
          --   - format(%L) per valori (quote_literal implicito)
          --   - I valori della config sono comunque controllati
          --     amministrativamente (Liquibase seed), ma applichiamo
          --     igiene comunque.
          DECLARE
              v_row              dbops.automazione_chiusura_scadenze%ROWTYPE;
              v_result           jsonb := '{}'::jsonb;
              v_total            bigint := 0;
              v_count            bigint;
              v_target_key       text;
              v_sql              text;
              v_id_chiuso        bigint;
              v_id_attivo        bigint;
              v_col_count        smallint;
              v_verbo            regprocedure;  -- il verbo di chiusura, risolto dal catalogo
              v_porta            boolean;       -- la testata e' sotto la porta degli stati
          BEGIN
              FOR v_row IN
                  SELECT *
                    FROM dbops.automazione_chiusura_scadenze
                   WHERE attivo = TRUE
                   ORDER BY id
              LOOP
                  v_target_key := v_row.schema_tabella || '.' || v_row.nome_tabella;

                  -- 0) Classe: solo DOMINIO ha un esecutore.
                  IF v_row.classe IS DISTINCT FROM 'DOMINIO' THEN
                      PERFORM script.fn_log_and_raise_error(
                          'database',
                          'fn_apply_chiusura_scadenze',
                          'E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA',
                          jsonb_build_object(
                              'config_id', v_row.id,
                              'target',    v_target_key,
                              'classe',    v_row.classe,
                              'motivo',    'classe_senza_esecutore'
                          ),
                          NULL::uuid,
                          v_target_key,
                          'il bersaglio non e'' di classe DOMINIO, e per le altre classi non c''e'' un esecutore'
                      );
                  END IF;

                  -- =====================================================
                  -- 1) Pre-check: tabella e colonne target
                  -- to_regclass restituisce NULL se la tabella non esiste
                  -- (idiomatico PG, una riga vs JOIN su pg_class/pg_namespace).
                  -- =====================================================
                  IF to_regclass(format('%I.%I', v_row.schema_tabella, v_row.nome_tabella)) IS NULL THEN
                      PERFORM script.fn_log_and_raise_error(
                          'database',
                          'fn_apply_chiusura_scadenze',
                          'E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA',
                          jsonb_build_object(
                              'config_id', v_row.id,
                              'target',    v_target_key,
                              'motivo',    'tabella_inesistente'
                          ),
                          NULL::uuid,
                          v_target_key,
                          'tabella inesistente'
                      );
                  END IF;

                  -- Verifica esistenza congiunta col_stato + col_valido_al.
                  SELECT count(*)::smallint INTO v_col_count
                    FROM pg_attribute a
                    JOIN pg_class    c ON c.oid = a.attrelid
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                   WHERE n.nspname = v_row.schema_tabella
                     AND c.relname = v_row.nome_tabella
                     AND a.attname IN (v_row.col_stato, v_row.col_valido_al)
                     AND a.attnum > 0
                     AND NOT a.attisdropped;

                  IF v_col_count < 2 THEN
                      PERFORM script.fn_log_and_raise_error(
                          'database',
                          'fn_apply_chiusura_scadenze',
                          'E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA',
                          jsonb_build_object(
                              'config_id',     v_row.id,
                              'target',        v_target_key,
                              'col_stato',     v_row.col_stato,
                              'col_valido_al', v_row.col_valido_al,
                              'motivo',        'colonna_mancante'
                          ),
                          NULL::uuid,
                          v_target_key,
                          format('colonne %s/%s non trovate',
                                 v_row.col_stato, v_row.col_valido_al)
                      );
                  END IF;

                  -- =====================================================
                  -- 1-bis) Porta e verbo, per ogni tipo_stato
                  -- =====================================================
                  v_porta := EXISTS (
                      SELECT 1 FROM pg_catalog.pg_trigger tg
                       WHERE tg.tgrelid = to_regclass(format('%I.%I', v_row.schema_tabella, v_row.nome_tabella))
                         AND tg.tgfoid  = 'script.trgfn_doc_stato_solo_dal_verbo()'::regprocedure
                         AND NOT tg.tgisinternal);

                  v_verbo := NULL;
                  IF v_row.verbo_chiusura IS NOT NULL THEN
                      -- Una funzione viva, senza argomenti: l'identificatore lo
                      -- da' il catalogo, non il testo del registro.
                      v_verbo := to_regprocedure(v_row.verbo_chiusura || '()');
                      IF v_verbo IS NULL THEN
                          PERFORM script.fn_log_and_raise_error(
                              'database',
                              'fn_apply_chiusura_scadenze',
                              'E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA',
                              jsonb_build_object(
                                  'config_id',      v_row.id,
                                  'target',         v_target_key,
                                  'verbo_chiusura', v_row.verbo_chiusura,
                                  'motivo',         'verbo_di_chiusura_inesistente'
                              ),
                              NULL::uuid,
                              v_target_key,
                              'il verbo di chiusura dichiarato non e'' una funzione senza argomenti'
                          );
                      END IF;
                  ELSIF v_porta THEN
                      PERFORM script.fn_log_and_raise_error(
                          'database',
                          'fn_apply_chiusura_scadenze',
                          'E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA',
                          jsonb_build_object(
                              'config_id', v_row.id,
                              'target',    v_target_key,
                              'motivo',    'porta_senza_verbo_di_chiusura'
                          ),
                          NULL::uuid,
                          v_target_key,
                          'lo stato si scrive solo da un verbo, e la testata non ha il verbo di chiusura'
                      );
                  END IF;

                  -- =====================================================
                  -- 2) Esecuzione: dispatch su tipo_stato
                  -- =====================================================
                  IF v_row.tipo_stato = 'VARCHAR' AND v_verbo IS NOT NULL THEN
                      EXECUTE format('SELECT %s()', v_verbo::regproc) INTO v_count;

                  ELSIF v_row.tipo_stato = 'VARCHAR' THEN
                      -- UPDATE diretto con valori varchar.
                      v_sql := format(
                          $f$
                          UPDATE %I.%I
                             SET %I = %L
                           WHERE %I = %L
                             AND %I IS NOT NULL
                             AND %I < (SELECT script.fn_data_operativa())
                          $f$,
                          v_row.schema_tabella, v_row.nome_tabella,
                          v_row.col_stato,      v_row.stato_chiuso_codice,
                          v_row.col_stato,      v_row.stato_attivo_codice,
                          v_row.col_valido_al,
                          v_row.col_valido_al
                      );

                      EXECUTE v_sql;
                      GET DIAGNOSTICS v_count = ROW_COUNT;

                  ELSIF v_row.tipo_stato = 'FK' THEN
                      -- Pre-check tabella lookup (to_regclass idiomatico).
                      IF to_regclass(format('%I.%I', v_row.fk_lookup_schema, v_row.fk_lookup_table)) IS NULL THEN
                          PERFORM script.fn_log_and_raise_error(
                              'database',
                              'fn_apply_chiusura_scadenze',
                              'E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA',
                              jsonb_build_object(
                                  'config_id',  v_row.id,
                                  'target',     v_target_key,
                                  'fk_lookup',  v_row.fk_lookup_schema || '.' || v_row.fk_lookup_table,
                                  'motivo',     'fk_lookup_inesistente'
                              ),
                              NULL::uuid,
                              v_target_key,
                              'fk_lookup inesistente'
                          );
                      END IF;

                      -- Lookup combinato id_attivo + id_chiuso in 1 round-trip.
                      -- MAX(CASE...) e' la classica idempotente "pivot": ritorna
                      -- l'unico id matching per ciascun codice, NULL se assente.
                      v_sql := format(
                          'SELECT max(CASE WHEN %I = %L THEN %I END),'
                          '       max(CASE WHEN %I = %L THEN %I END)'
                          '  FROM %I.%I'
                          ' WHERE %I IN (%L, %L)',
                          v_row.fk_lookup_codice_col, v_row.stato_attivo_codice, v_row.fk_lookup_id_col,
                          v_row.fk_lookup_codice_col, v_row.stato_chiuso_codice, v_row.fk_lookup_id_col,
                          v_row.fk_lookup_schema, v_row.fk_lookup_table,
                          v_row.fk_lookup_codice_col,
                          v_row.stato_attivo_codice, v_row.stato_chiuso_codice
                      );
                      EXECUTE v_sql INTO v_id_attivo, v_id_chiuso;

                      IF v_id_chiuso IS NULL THEN
                          PERFORM script.fn_log_and_raise_error(
                              'database',
                              'fn_apply_chiusura_scadenze',
                              'E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA',
                              jsonb_build_object(
                                  'config_id',           v_row.id,
                                  'target',              v_target_key,
                                  'stato_chiuso_codice', v_row.stato_chiuso_codice,
                                  'motivo',              'codice_chiuso_non_trovato'
                              ),
                              NULL::uuid,
                              v_target_key,
                              'codice chiuso non trovato'
                          );
                      END IF;

                      IF v_id_attivo IS NULL THEN
                          PERFORM script.fn_log_and_raise_error(
                              'database',
                              'fn_apply_chiusura_scadenze',
                              'E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA',
                              jsonb_build_object(
                                  'config_id',           v_row.id,
                                  'target',              v_target_key,
                                  'stato_attivo_codice', v_row.stato_attivo_codice,
                                  'motivo',              'codice_attivo_non_trovato'
                              ),
                              NULL::uuid,
                              v_target_key,
                              'codice attivo non trovato'
                          );
                      END IF;

                      IF v_verbo IS NOT NULL THEN
                          EXECUTE format('SELECT %s()', v_verbo::regproc) INTO v_count;
                      ELSE
                      -- UPDATE con id risolti.
                      v_sql := format(
                          $f$
                          UPDATE %I.%I
                             SET %I = %L
                           WHERE %I = %L
                             AND %I IS NOT NULL
                             AND %I < (SELECT script.fn_data_operativa())
                          $f$,
                          v_row.schema_tabella, v_row.nome_tabella,
                          v_row.col_stato,      v_id_chiuso::text,
                          v_row.col_stato,      v_id_attivo::text,
                          v_row.col_valido_al,
                          v_row.col_valido_al
                      );

                      EXECUTE v_sql;
                      GET DIAGNOSTICS v_count = ROW_COUNT;
                      END IF;
                  ELSE
                      -- Difesa in profondita': il CHECK constraint
                      -- esclude gia' tipi diversi, ma per chiarezza.
                      PERFORM script.fn_log_and_raise_error(
                          'database',
                          'fn_apply_chiusura_scadenze',
                          'E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA',
                          jsonb_build_object(
                              'config_id',  v_row.id,
                              'target',     v_target_key,
                              'tipo_stato', v_row.tipo_stato,
                              'motivo',     'tipo_stato_non_gestito'
                          ),
                          NULL::uuid,
                          v_target_key,
                          v_row.tipo_stato
                      );
                      v_count := 0;
                  END IF;

                  -- =====================================================
                  -- 3) Aggregazione risultato
                  -- =====================================================
                  v_result := v_result || jsonb_build_object(v_target_key, v_count);
                  v_total  := v_total + v_count;
              END LOOP;

              -- Meta-info.
              v_result := v_result
                          || jsonb_build_object('_total', v_total)
                          || jsonb_build_object('_executed_at', now());

              -- =====================================================
              -- 4) Audit log esecuzione (best-effort, non blocca)
              -- Pattern progetto: dbops.fn_audit_log_once con parametri named.
              -- WHEN OTHERS perche' un fallimento di audit non deve
              -- propagarsi: il caller (job pgAgent) deve comunque
              -- ricevere il JSONB con i conteggi.
              -- =====================================================
              BEGIN
                  PERFORM dbops.fn_audit_log_once(
                      p_function_name => 'dbops.fn_apply_chiusura_scadenze',
                      -- Un giro arrivato fin qui e' OK (INFO non e' nel
                      -- vocabolario di chk_audit_status).
                      p_status        => 'OK',
                      p_params        => v_result
                  );
              EXCEPTION WHEN OTHERS THEN
                  NULL;
              END;

              RETURN v_result;
          END;
          $function$

COMMENT ON FUNCTION dbops.fn_apply_chiusura_scadenze()
IS 'Framework di chiusura per scadenza: chiude lo stato gestionale sulle tabelle attive di dbops.automazione_chiusura_scadenze quando valido_al e'' passato (data operativa, script.fn_data_operativa). Lo chiama l''handler della coda dei lavori, una volta per azienda, con l''identita'' e la RLS di quell''azienda: per questo il registro ammette solo bersagli DOMINIO, e un bersaglio di un''altra classe e'' rifiutato. Per ogni bersaglio: pre-check di tabella, colonne e (tipo_stato FK) codici del vocabolario; poi porta e verbo, in tutti e due i rami: un verbo di chiusura dichiarato (verbo_chiusura, funzione viva senza argomenti) si usa sempre e il conteggio e'' il suo; una testata sotto la porta degli stati (script.trgfn_doc_stato_solo_dal_verbo) senza verbo e'' una configurazione non valida; senza porta e senza verbo, UPDATE dinamico. Ogni configurazione non valida solleva E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA col motivo nel contesto (classe_senza_esecutore, tabella_inesistente, colonna_mancante, fk_lookup_inesistente, codice_chiuso_non_trovato, codice_attivo_non_trovato, verbo_di_chiusura_inesistente, porta_senza_verbo_di_chiusura, tipo_stato_non_gestito). Ritorna un jsonb con il conteggio per bersaglio, _total ed _executed_at, e scrive l''esito in dbops.audit_log. INVOKER: vede e chiude cio'' che vede chi la chiama.';
```

</div>

---
{% include-markdown "signature-core.md" %}
