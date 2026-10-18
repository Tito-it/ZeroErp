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
    v_voce      config.tabelle_gestibili%ROWTYPE;
    v_relid     oid;
    v_rls       boolean;
    v_scrivibili text[];
    v_estranea  text;
    v_riga      jsonb;
BEGIN
    -- 0. La tabella: nella lista, nel pannello, esistente, senza RLS.
    SELECT tg.*
      INTO v_voce
      FROM config.tabelle_gestibili tg
     WHERE tg.codice_interno = p_tabella
       AND tg.pannello;

    IF FOUND THEN
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

    -- Le colonne scrivibili hanno una sede sola, letta anche dal metadata
    -- del backend (20260927-21).
    v_scrivibili := config.fn_pannello_colonne_scrivibili(p_tabella);

    -- La regola «una chiave estranea si rifiuta» e' il BB
    -- script.fn_prima_chiave_estranea (rev 2026-10-17, regola del 2).
    v_estranea := script.fn_prima_chiave_estranea(p_dati, v_scrivibili);

    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_pannello_scrivi', 'E_PANNELLO_CAMPO_NON_AMMESSO',
            jsonb_build_object('tabella', p_tabella, 'id', p_id,
                               'campo',   v_estranea),
            NULL::uuid,
            v_estranea);
    END IF;

    -- 3. La scrittura. I valori li converte PostgreSQL, sul tipo di riga:
    --    il BB script.fn_scrivi_riga_da_jsonb (rev 2026-10-17, regola del 2).
    --    La tabella gli arriva per oid, quello trovato al passo 0.
    IF p_id IS NULL THEN
        v_riga := script.fn_scrivi_riga_da_jsonb(v_relid::regclass, p_dati);
    ELSE
        v_riga := script.fn_scrivi_riga_da_jsonb(
                      v_relid::regclass, p_dati, jsonb_build_object('id', p_id));

        IF v_riga IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'config', 'config.fn_pannello_scrivi', 'E_PANNELLO_RIGA_NON_TROVATA',
                jsonb_build_object('tabella', p_tabella, 'id', p_id),
                NULL::uuid,
                p_id::text);
        END IF;
    END IF;

    -- 4. La riga, con i campi del form: id e le colonne scrivibili.
    RETURN (SELECT jsonb_object_agg(e.key, e.value)
              FROM jsonb_each(v_riga) AS e
             WHERE e.key = 'id'
                OR e.key = ANY (v_scrivibili));
END;
$function$

COMMENT ON FUNCTION config.fn_pannello_scrivi(p_tabella text, p_id bigint, p_dati jsonb)
IS 'VERBO del pannello di configurazione (modello «una scrittura = un verbo», D-3 di brief-db-permesso-nel-verbo-di-scrittura). Scrive una riga di una tabella di config.tabelle_gestibili con pannello = true: p_id NULL = INSERT, altrimenti UPDATE per id. Passo 0: tabella in lista, esistente e SENZA RLS (il verbo non sa rimettere un perimetro, D-P2) -> altrimenti E_PANNELLO_TABELLA_NON_AMMESSA. Passo 1: script.fn_guard_livello(utente, app_label, model_name, TUTTO) sull''oggetto della riga di lista, non sull''area del pannello (E_PERMESSO_NEGATO). Passo 2: p_dati oggetto jsonb non vuoto (E_PANNELLO_DATI_VUOTI) con sole colonne scrivibili, che da'' config.fn_pannello_colonne_scrivibili (sede unica della regola, letta anche dal metadata del backend); una chiave estranea si RIFIUTA (E_PANNELLO_CAMPO_NON_AMMESSO con campo, D-P3). Passo 3: valori convertiti da jsonb_populate_record sul tipo di riga, scritte solo le colonne del payload; UPDATE su id assente -> E_PANNELLO_RIGA_NON_TROVATA. Ritorna la riga con id e le colonne scrivibili, cioe'' i campi del form. I trigger della tabella scattano come sempre. Nessun DELETE. SECURITY DEFINER del proprietario con search_path bloccato; il nome della tabella si compone dalla lista con format(%I.%I). Brief: brief-db-pannello-config-verbo-generico §3.3 e §6. Rev 2026-10-17: la scrittura del passo 3 la fa il BB script.fn_scrivi_riga_da_jsonb e la chiave estranea del passo 2 la trova script.fn_prima_chiave_estranea (regola del 2, brief-db-processi-accensione-per-ambiente 2b-1); comportamento, codici e firma invariati.';
```

---
{% include-markdown "signature-core.md" %}
