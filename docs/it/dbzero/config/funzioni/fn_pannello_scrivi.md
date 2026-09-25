{% include-markdown "it/dbzero/config/manual/fn_pannello_scrivi.md" %}
# ⚙️ Funzione `fn_pannello_scrivi`

```sql
CREATE FUNCTION fn_pannello_scrivi(p_tabella text, p_id bigint, p_dati jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.fn_pannello_scrivi(p_tabella text, p_id bigint, p_dati jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: scrivere (INSERT o UPDATE per id) una riga di una tabella gestita
--   dal pannello di configurazione, applicando il livello TUTTO sull'oggetto
--   a cui la tabella appartiene. Ritorna la riga scritta.
DECLARE
    -- Le colonne che il pannello non scrive: le stesse escluse dal backend
    -- (config_metadata_repository._EXCLUDED_COLUMNS) piu' la chiave.
    c_escluse   CONSTANT text[] := ARRAY['id', 'data_insert', 'user_insert',
                                         'data_update', 'user_update', 'tx_id',
                                         'storicizza', 'uid'];
    v_voce      config.tabelle_gestibili%ROWTYPE;
    v_nome      text;      -- schema.tabella quotato, composto dalla lista
    v_relid     oid;
    v_rls       boolean;
    v_scrivibili text[];
    v_chiavi    text[];
    v_estranea  text;
    v_colonne   text;      -- colonne del payload, quotate
    v_riga      jsonb;
BEGIN
    -- 0. La tabella: nella lista, nel pannello, esistente, senza RLS.
    SELECT tg.*
      INTO v_voce
      FROM config.tabelle_gestibili tg
     WHERE tg.codice_interno = p_tabella
       AND tg.pannello;

    IF FOUND THEN
        v_nome := format('%I.%I', v_voce.schema_tabella, v_voce.nome_tabella);
        SELECT c.oid, c.relrowsecurity
          INTO v_relid, v_rls
          FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = v_voce.schema_tabella
           AND c.relname = v_voce.nome_tabella
           AND c.relkind IN ('r', 'p');
    END IF;

    IF v_relid IS NULL OR v_rls THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_pannello_scrivi', 'E_PANNELLO_TABELLA_NON_AMMESSA',
            jsonb_build_object('tabella',  p_tabella,
                               'in_lista', v_voce.id IS NOT NULL,
                               'esiste',   v_relid IS NOT NULL,
                               'rls',      v_rls),
            NULL::uuid,
            COALESCE(p_tabella, '(nessuna)'));
    END IF;

    -- 1. Il permesso: TUTTO sull'oggetto della riga di lista (D-5).
    PERFORM script.fn_guard_livello(
        NULLIF(current_setting('app.current_user_id', true), '')::integer,
        v_voce.app_label, v_voce.model_name, 'TUTTO');

    -- 2. Il payload: un oggetto non vuoto, solo colonne scrivibili.
    IF p_dati IS NULL OR jsonb_typeof(p_dati) <> 'object' OR p_dati = '{}'::jsonb THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_pannello_scrivi', 'E_PANNELLO_DATI_VUOTI',
            jsonb_build_object('tabella', p_tabella, 'id', p_id,
                               'tipo', jsonb_typeof(p_dati)),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    SELECT array_agg(a.attname::text ORDER BY a.attnum)
      INTO v_scrivibili
      FROM pg_catalog.pg_attribute a
     WHERE a.attrelid = v_relid
       AND a.attnum > 0
       AND NOT a.attisdropped
       AND a.attgenerated = ''
       AND a.attidentity <> 'a'
       AND a.attname::text <> ALL (c_escluse);

    SELECT array_agg(k ORDER BY k)
      INTO v_chiavi
      FROM jsonb_object_keys(p_dati) AS k;

    SELECT k
      INTO v_estranea
      FROM unnest(v_chiavi) AS k
     WHERE k <> ALL (COALESCE(v_scrivibili, ARRAY[]::text[]))
     ORDER BY k
     LIMIT 1;

    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_pannello_scrivi', 'E_PANNELLO_CAMPO_NON_AMMESSO',
            jsonb_build_object('tabella', p_tabella, 'id', p_id,
                               'campo',   v_estranea),
            NULL::uuid,
            v_estranea);
    END IF;

    SELECT string_agg(quote_ident(k), ', ' ORDER BY k)
      INTO v_colonne
      FROM unnest(v_chiavi) AS k;

    -- 3. La scrittura. I valori li converte PostgreSQL, sul tipo di riga.
    IF p_id IS NULL THEN
        EXECUTE format(
            'INSERT INTO %s AS t (%s) SELECT %s FROM jsonb_populate_record(NULL::%s, $1) '
            'RETURNING to_jsonb(t.*)',
            v_nome, v_colonne, v_colonne, v_nome)
           INTO v_riga
          USING p_dati;
    ELSE
        EXECUTE format(
            'UPDATE %s AS t SET (%s) = (SELECT %s FROM jsonb_populate_record(NULL::%s, $1)) '
            'WHERE t.id = $2 RETURNING to_jsonb(t.*)',
            v_nome, v_colonne, v_colonne, v_nome)
           INTO v_riga
          USING p_dati, p_id;

        IF v_riga IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'config', 'config.fn_pannello_scrivi', 'E_PANNELLO_RIGA_NON_TROVATA',
                jsonb_build_object('tabella', p_tabella, 'id', p_id),
                NULL::uuid,
                p_id::text);
        END IF;
    END IF;

    -- 4. La riga, nella forma che il backend restituiva: senza le escluse, con id.
    RETURN v_riga - array_remove(c_escluse, 'id');
END;
$function$

COMMENT ON FUNCTION config.fn_pannello_scrivi(p_tabella text, p_id bigint, p_dati jsonb)
IS 'VERBO del pannello di configurazione (modello «una scrittura = un verbo», D-3 di brief-db-permesso-nel-verbo-di-scrittura). Scrive una riga di una tabella di config.tabelle_gestibili con pannello = true: p_id NULL = INSERT, altrimenti UPDATE per id. Passo 0: tabella in lista, esistente e SENZA RLS (il verbo non sa rimettere un perimetro, D-P2) -> altrimenti E_PANNELLO_TABELLA_NON_AMMESSA. Passo 1: script.fn_guard_livello(utente, app_label, model_name, TUTTO) sull''oggetto della riga di lista, non sull''area del pannello (E_PERMESSO_NEGATO). Passo 2: p_dati oggetto jsonb non vuoto (E_PANNELLO_DATI_VUOTI) con sole colonne scrivibili — escluse id, audit, tx_id, storicizza, uid, generate e identity ALWAYS — e una chiave estranea si RIFIUTA (E_PANNELLO_CAMPO_NON_AMMESSO con campo, D-P3). Passo 3: valori convertiti da jsonb_populate_record sul tipo di riga, scritte solo le colonne del payload; UPDATE su id assente -> E_PANNELLO_RIGA_NON_TROVATA. Ritorna la riga senza le colonne escluse tranne id. I trigger della tabella scattano come sempre. Nessun DELETE. SECURITY DEFINER del proprietario con search_path bloccato; il nome della tabella si compone dalla lista con format(%I.%I). Brief: brief-db-pannello-config-verbo-generico §3.3.';
```

---
{% include-markdown "signature-core.md" %}
