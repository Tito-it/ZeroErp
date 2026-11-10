{% include-markdown "it/dbzero/dbops/manual/fn_check_funzioni_riferimenti_morti.md" %}
# ⚙️ Funzione `fn_check_funzioni_riferimenti_morti`

```sql
CREATE FUNCTION fn_check_funzioni_riferimenti_morti()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_check_funzioni_riferimenti_morti()
 RETURNS TABLE(classe text, schema_nome text, funzione text, argomenti text, esito text)
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
  r          record;
  rel        record;
  m          text;
  v_relazioni int;
  v_tipi     text[];
  v_chiamata text;
  v_e_variadic boolean;
BEGIN
  CREATE TEMP TABLE IF NOT EXISTS tmp_raw(
    nsp text, pro text, args text, relid oid, msg text
  ) ON COMMIT DROP;
  DELETE FROM tmp_raw;

  FOR r IN
    SELECT p.oid                                     AS oid,
           n.nspname::text                           AS nsp,
           p.proname::text                           AS pro,
           pg_get_function_identity_arguments(p.oid) AS args,
           (p.prorettype = 'trigger'::regtype)       AS is_trg
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
      JOIN pg_language  l ON l.oid = p.prolang
     WHERE l.lanname = 'plpgsql'
       AND n.nspname NOT IN ('pg_catalog', 'information_schema')
       AND n.nspname NOT LIKE 'pg\_%'
       -- fuori tutto cio' che appartiene a un'estensione: non e' codice
       -- che manteniamo noi (PostGIS, topology, pgagent).
       AND NOT EXISTS (SELECT 1 FROM pg_depend d
                        WHERE d.objid = p.oid AND d.deptype = 'e')
     ORDER BY n.nspname, p.proname
  LOOP
    IF r.is_trg THEN
      -- Trigger function: si valida contro OGNI tabella su cui e'
      -- agganciata. Zero tabelle = orfana, e non e' validabile.
      v_relazioni := 0;
      FOR rel IN
        SELECT DISTINCT tg.tgrelid
          FROM pg_trigger tg
         WHERE tg.tgfoid = r.oid AND NOT tg.tgisinternal
      LOOP
        v_relazioni := v_relazioni + 1;
        BEGIN
          -- ⛔ `public.` NON e' decorazione: togliendolo il presidio MENTE.
          --   Questa funzione gira anche DENTRO `dbops.fn_conta_presidio`, che
          --   e' SECURITY DEFINER con `search_path = pg_catalog, pg_temp`. Li'
          --   un nome non qualificato non si risolve — 42883, l'estensione sta
          --   in `public` — l'EXCEPTION qui sotto lo scrive come
          --   `error:CHECK-KO:` e OGNI funzione del database esce
          --   NON_MISURATO. Misurato il 2026-09-12: il digest riferiva 784
          --   «riferimenti morti» che erano 784 «non ho potuto guardare», e la
          --   lettura diretta della stessa vista rispondeva 0.
          --   Brief: brief-db-un-destinatario-per-i-presidi §13.2.
          FOR m IN SELECT c FROM public.plpgsql_check_function(
                     r.oid::regprocedure, relid => rel.tgrelid::regclass,
                     fatal_errors => false) AS c
          LOOP
            IF m LIKE 'error:%' THEN
              INSERT INTO tmp_raw VALUES (r.nsp, r.pro, r.args, rel.tgrelid, m);
            END IF;
          END LOOP;
        EXCEPTION WHEN OTHERS THEN
          INSERT INTO tmp_raw VALUES (r.nsp, r.pro, r.args, rel.tgrelid,
                                      'error:CHECK-KO:' || SQLERRM);
        END;
      END LOOP;

      IF v_relazioni = 0 THEN
        classe := 'ORFANA'; schema_nome := r.nsp; funzione := r.pro;
        argomenti := r.args;
        esito := 'trigger function senza alcun trigger agganciato: non validabile, e gia'' di per se'' un residuo';
        RETURN NEXT;
      END IF;

    ELSE
      BEGIN
        -- ⛔ Qualificato come il gemello qui sopra e per la stessa ragione: i
        --   due rami sono la stessa chiamata su due forme di funzione, quindi
        --   sanarne uno solo lascerebbe cieca meta' della scansione.
        FOR m IN SELECT c FROM public.plpgsql_check_function(
                   r.oid::regprocedure, fatal_errors => false) AS c
        LOOP
          IF m LIKE 'error:%' THEN
            INSERT INTO tmp_raw VALUES (r.nsp, r.pro, r.args, NULL, m);
          END IF;
        END LOOP;
      EXCEPTION WHEN OTHERS THEN
        INSERT INTO tmp_raw VALUES (r.nsp, r.pro, r.args, NULL,
                                    'error:CHECK-KO:' || SQLERRM);
      END;
    END IF;
  END LOOP;

  -- ── Classificazione ──────────────────────────────────────────────
  FOR r IN
    SELECT t.nsp, t.pro, t.args, t.msg,
           count(*)                                   AS visto_su,
           (SELECT count(DISTINCT tg.tgrelid)
              FROM pg_trigger tg
              JOIN pg_proc p2 ON p2.oid = tg.tgfoid
              JOIN pg_namespace n2 ON n2.oid = p2.pronamespace
             WHERE n2.nspname = t.nsp AND p2.proname = t.pro
               AND NOT tg.tgisinternal)                AS tabelle_totali
      FROM tmp_raw t
     GROUP BY t.nsp, t.pro, t.args, t.msg
     ORDER BY t.nsp, t.pro, t.msg
  LOOP
    schema_nome := r.nsp; funzione := r.pro; argomenti := r.args; esito := r.msg;

    -- (1) Errore visto solo su ALCUNE delle tabelle del trigger: e' il
    --     ramo dedicato a un'altra tabella, non un difetto.
    IF r.tabelle_totali > 1 AND r.visto_su < r.tabelle_totali THEN
      classe := 'FP_RAMO_ALTRA_TABELLA';

    -- (1-bis) «relazione X non esiste» dove X e' una TRANSITION TABLE
    --     dichiarata nel CREATE TRIGGER (`REFERENCING NEW TABLE AS ...`).
    --     Esiste solo durante lo scatto del trigger, plpgsql_check non la
    --     vede. Il nome non si indovina: si legge da pg_trigger, che lo
    --     conserva in tgnewtable/tgoldtable.
    ELSIF r.msg ~ '^error:42P01:' AND EXISTS (
            SELECT 1
              FROM pg_trigger tg
              JOIN pg_proc p3      ON p3.oid = tg.tgfoid
              JOIN pg_namespace n3 ON n3.oid = p3.pronamespace
             WHERE n3.nspname = r.nsp AND p3.proname = r.pro
               AND NOT tg.tgisinternal
               AND substring(r.msg from '"([^"]+)"')
                   IN (tg.tgnewtable::text, tg.tgoldtable::text))
    THEN
      classe := 'FP_TRANSITION_TABLE';

    -- (1-ter) Errore di SINTASSI dentro un EXECUTE: e' SQL costruito a
    --     runtime, con dentro segnaposto che non sono SQL valido finche'
    --     non vengono sostituiti. plpgsql_check prova a interpretarlo
    --     comunque.
    ELSIF r.msg ~ '^error:42601:' AND r.msg LIKE '%:EXECUTE:%' THEN
      classe := 'FP_SQL_DINAMICO';

    -- (1-quater) «permesso negato» (SQLSTATE 42501) dentro una funzione
    --     SECURITY DEFINER, misurata da chi NON e' il suo proprietario (ne'
    --     membro del suo ruolo). Il corpo di una DEFINER gira con i privilegi
    --     del PROPRIETARIO: «il chiamante puo' risolvere il riferimento?» e'
    --     la domanda sbagliata, e la risposta non dice niente della funzione.
    --     La domanda giusta — «puo' risolverlo il proprietario?» — la fanno
    --     gli altri occhi del presidio: fn_conta_presidio (DEFINER, conta per
    --     il digest) e il guardrail in CI (superuser). Chi e' proprietario, o
    --     ne ha i privilegi, e prende lo stesso un 42501, cade nell'ELSE:
    --     quello e' REALE.
    --
    -- ⭐ rev 2026-09-14 — Il caso: dbops.fn_get_pgagent_job_stato (DEFINER di
    --     titodb) legge pgagent.pga_job, che zeroerp_app non vede: come app
    --     usciva REALE 42501 e stava a registro (esenzione 7, «due facce»); come
    --     proprietario NON usciva affatto, e il primo digest settimanale
    --     (14-09 07:30) ha dato la riga 7 «rientrata». Tre occhi, due
    --     risposte, una sola verita': quel 42501 non era un difetto della
    --     funzione, era il ruolo che la misurava. Lo stesso tipo di falso
    --     positivo era gia' stato sanato per maintenance.* dando USAGE all'app
    --     (provision_db_roles.sql): un rimedio per-schema, questo e' la regola.
    --     ⚠️ In CI non cambia niente: il guardrail misura da superuser, dove
    --     un 42501 non esiste; il difetto pgAgent-assente la' resta 42P01 e
    --     resta REALE, com'e' giusto.
    ELSIF r.msg ~ '^error:42501:' AND EXISTS (
            SELECT 1
              FROM pg_proc p6
              JOIN pg_namespace n6 ON n6.oid = p6.pronamespace
             WHERE n6.nspname = r.nsp
               AND p6.proname = r.pro
               AND pg_get_function_identity_arguments(p6.oid) = r.args
               AND p6.prosecdef
               AND NOT pg_has_role(current_user, p6.proowner, 'MEMBER'))
    THEN
      classe := 'FP_DEFINER_PRIVILEGIO';

    -- (2) «funzione non esiste» (SQLSTATE 42883): falso positivo SOLO se
    --     tutti i tipi passati sono testo-compatibili — allora e' la
    --     variadic che plpgsql_check non sa risolvere. Se c'e' un tipo
    --     non testuale, il cast non esiste e la chiamata fallisce davvero.
    --
    -- 🔴 v4 (2026-08-05) — LA PREMESSA DI v1 ERA FALSA. Solo
    --     `VARIADIC "any"` (quello di `format()`) ammette ZERO argomenti
    --     variadici; un `VARIADIC <tipo>[]` no. Verificato in SQL e in
    --     plpgsql: la chiamata a 5 argomenti NON si risolve davvero.
    --     Le due strette precedenti (v2 sui TIPI, v3 su provariadic <> 0)
    --     hanno ridotto il danno senza mai toccare l'assunto che lo
    --     causava. Segnalato dal team BE il 2026-08-05.
    --     ⚠️ Da noi nessuna funzione e' `VARIADIC "any"`: la classe resta
    --     strutturalmente vuota, ed e' il risultato giusto.
    --
    -- ⚠️ v3 (2026-08-04) — la regola era TROPPO LARGA e ha scusato un
    --     difetto vero. La chiamata
    --       dbops.fn_audit_log_once('…','SKIP_EXISTS','STORICO', jsonb, '…')
    --     ha il 3o e 4o argomento INVERTITI rispetto alla firma
    --     (p_params jsonb, p_message text). Ma `jsonb` e' nella lista dei
    --     testo-compatibili, quindi uno scambio fra un text e un jsonb
    --     produce esattamente la stessa firma di un variadico omesso, e
    --     usciva etichettato FP_VARIADIC.
    --     Rimedio: l'esenzione vale solo se la funzione chiamata **ha
    --     davvero** un parametro VARIADIC. Se non ce l'ha, il variadico
    --     non c'entra e l'errore e' reale.
    --     Delle 17 righe FP_VARIADIC del primo giro, questa era l'unica a
    --     non chiamare fn_log_and_raise_error / fn_log_error_only — ed era
    --     l'unica sbagliata.
    ELSIF r.msg ~ '^error:42883:' AND r.msg LIKE '%(%)%' THEN
      v_tipi := string_to_array(
                  btrim(substring(r.msg from '\(([^)]*)\)')), ', ');
      -- Nome della funzione chiamata, come compare nel messaggio:
      -- «la funzione <schema>.<nome>(tipi) non esiste».
      v_chiamata := substring(r.msg from '([A-Za-z_][A-Za-z0-9_$]*\.[A-Za-z_][A-Za-z0-9_$]*)\s*\(');
      v_e_variadic := EXISTS (
        SELECT 1
          FROM pg_proc p4
          JOIN pg_namespace n4 ON n4.oid = p4.pronamespace
         WHERE n4.nspname || '.' || p4.proname = v_chiamata
           AND p4.provariadic = '"any"'::regtype   -- virgolette: `any` e' riservata
      );
      IF v_e_variadic AND NOT EXISTS (
           SELECT 1 FROM unnest(v_tipi) AS x(t)
            WHERE btrim(x.t) NOT IN ('unknown','text','name','jsonb','uuid',
                                     'character varying','"unknown"'))
      THEN
        classe := 'FP_VARIADIC';
      ELSE
        classe := 'REALE';
      END IF;

    -- (5) 🔴 LO STRUMENTO NON HA MISURATO, e non e' un difetto del codice.
    --     `error:CHECK-KO:` lo scrive il gestore EXCEPTION qui sopra quando
    --     `plpgsql_check_function` SOLLEVA invece di rispondere. Fino al
    --     2026-09-10 quella forma non aveva un ramo e cadeva nell'ELSE, cioe'
    --     usciva come REALE: una funzione che non si e' potuta controllare
    --     veniva riferita come «riferimento morto».
    --
    -- ⛔ NON e' un caso di bordo: il 2026-09-10 su dbdev plpgsql_check ha
    --     fallito su quasi ogni funzione e la vista di lavoro ha esposto 779
    --     righe su 780 funzioni plpgsql, mentre il registro del debito ne ha
    --     DUE e lo stesso controllo passava in CI. Un presidio che, quando il
    --     suo strumento si rompe, riferisce 779 difetti invece di dire «non ho
    --     misurato» e' peggio di un presidio assente: manda a cercare 779 cose
    --     che non ci sono, e nasconde l'unica che c'e'.
    --
    -- ⭐ La regola era gia' scritta, e in casa: `guardrail_riferimenti_morti.sql`
    --     tratta cosi' l'estensione ASSENTE — «NON si passa in silenzio: un
    --     guardrail che non misura e non lo dice e' peggio di uno assente».
    --     Qui l'estensione c'e' e si rompe: stesso principio, e fino a oggi due
    --     esiti opposti.
    --
    -- ⚠️ E NON si nasconde: chi consuma questa classe deve trattarla come un
    --     ROSSO, non come un'assenza di difetti. La vista di lavoro la include
    --     e il guardrail solleva con un messaggio suo.
    ELSIF r.msg LIKE 'error:CHECK-KO:%' THEN
      classe := 'NON_MISURATO';

    ELSE
      classe := 'REALE';
    END IF;

    RETURN NEXT;
  END LOOP;
END
$function$

COMMENT ON FUNCTION dbops.fn_check_funzioni_riferimenti_morti()
IS 'Compila con plpgsql_check ogni funzione plpgsql non di estensione e classifica i difetti in otto classi: REALE, ORFANA, NON_MISURATO, FP_DEFINER_PRIVILEGIO, FP_RAMO_ALTRA_TABELLA, FP_SQL_DINAMICO, FP_TRANSITION_TABLE, FP_VARIADIC. Fonte unica: la leggono scripts/sql/check_funzioni_riferimenti_morti.sql, il pgTAP db/pgtap/dbops/test-riferimenti-morti-v1.sql e i presidi dbops.vw_riferimenti_morti_da_sanare e dbops.vw_riferimenti_morti_rientrati. Richiede l''estensione plpgsql_check. NON_MISURATO e'' la classe di chi non si e'' potuto controllare: plpgsql_check ha sollevato invece di rispondere e il gestore EXCEPTION ha scritto error:CHECK-KO:. Chi consuma la tratta come un ROSSO, mai come assenza di difetti, come l''estensione assente. FP_DEFINER_PRIVILEGIO: un 42501 (permesso negato) dentro una funzione SECURITY DEFINER misurata da chi non ne e'' il proprietario ne'' membro del suo ruolo non e'' un riferimento morto, perche'' il corpo di una DEFINER gira coi privilegi del proprietario; la domanda giusta la fanno gli altri occhi del presidio (il conteggio come proprietario, il guardrail in CI come superuser). Chi e'' proprietario e prende un 42501 resta REALE. Il search_path e'' fissato nella definizione (pg_catalog, public, pg_temp) e la chiamata a plpgsql_check_function e'' qualificata con public.: servono entrambi. La funzione e'' SECURITY INVOKER e gira anche dentro dbops.fn_conta_presidio_per_variante, che e'' SECURITY DEFINER con search_path = pg_catalog, pg_temp: senza il pin ne erediterebbe il path, plpgsql_check_function non si risolverebbe (42883, l''estensione sta in public) e ogni funzione uscirebbe NON_MISURATO. Il search_path governa anche la risoluzione dei riferimenti DENTRO le funzioni che si compilano: senza public resterebbero falsi REALE le funzioni che nominano un''estensione senza schema (unaccent, dblink, il tipo geometry), come e'' normale in esercizio. public nel pin e'' nel path reale dell''applicazione, quindi la misura compila nel contesto in cui quelle funzioni girano. ⚠️ Un CREATE OR REPLACE che perde la clausola SET non fallisce: riporta il presidio a mentire.';
```

</div>

---
{% include-markdown "signature-core.md" %}
