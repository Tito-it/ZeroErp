# ⚙️ Funzione `trgfn_guard_sorgente`

```sql
CREATE FUNCTION trgfn_guard_sorgente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_guard_sorgente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_riga_json   jsonb;
    v_tipo        config.sorgenti.id%TYPE;
    v_id          bigint;
    v_uid_testo   text;
    v_uid         uuid;
    v_riga        bigint;
    v_dettaglio   bigint;

    v_livello     text;
    v_azione      text;
    v_valido      boolean;

    v_codice      config.sorgenti.codice_interno%TYPE;
    v_attivo      config.sorgenti.attivo%TYPE;
    v_selector    config.sorgenti.key_selector%TYPE;
    v_doc_tabella pg_catalog.pg_class.relname%TYPE;
    v_r_schema    pg_catalog.pg_namespace.nspname%TYPE;
    v_r_tabella   pg_catalog.pg_class.relname%TYPE;
    v_r_fk        config.sorgenti.righe_fk_column%TYPE;
    v_d_schema    pg_catalog.pg_namespace.nspname%TYPE;
    v_d_tabella   pg_catalog.pg_class.relname%TYPE;
    v_d_fk        config.sorgenti.dettaglio_fk_column%TYPE;

    v_doc_id      bigint;
    v_chiave      text;
    v_trovato     boolean;
BEGIN
    -- =========================================================
    -- Scopo: la provenienza scritta sulla riga e' un documento che
    --   esiste, citato con la chiave del suo tipo, e la riga e il
    --   dettaglio indicati gli appartengono.
    -- Argomenti: livello minimo, azione in cancellazione
    --   (script.fn_sorgente_guard_argomenti).
    -- =========================================================
    SELECT a.livello_minimo, a.azione_cancellazione, a.valido
      INTO v_livello, v_azione, v_valido
      FROM script.fn_sorgente_guard_argomenti(
               CASE WHEN TG_NARGS = 0 THEN ARRAY[]::text[] ELSE TG_ARGV END) a;

    IF NOT v_valido THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.trgfn_guard_sorgente', 'E_SORG_CONF',
            jsonb_build_object('detail', 'argomenti del guard non validi',
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'argomenti', to_jsonb(TG_ARGV)),
            NULL::uuid,
            concat(TG_TABLE_SCHEMA, '.', TG_TABLE_NAME, ': argomenti del guard non validi'));
    END IF;

    v_riga_json := to_jsonb(NEW);
    v_tipo := (v_riga_json ->> 'sorgente_tipo_id')::bigint;

    -- Nessuna provenienza: niente da verificare (la forma e' del CHECK).
    IF v_tipo IS NULL THEN
        RETURN NEW;
    END IF;

    v_id        := (v_riga_json ->> 'sorgente_id')::bigint;
    v_uid_testo := v_riga_json ->> 'sorgente_uid';
    v_uid       := script.fn_sorgente_chiave_uuid(v_uid_testo);
    v_riga      := (v_riga_json ->> 'sorgente_riga')::bigint;
    v_dettaglio := (v_riga_json ->> 'sorgente_dettaglio')::bigint;

    -- 1. il tipo
    SELECT l.codice_interno, l.attivo, l.key_selector, l.documento_tabella,
           l.righe_schema, l.righe_tabella, l.righe_fk_column,
           l.dettaglio_schema, l.dettaglio_tabella, l.dettaglio_fk_column
      INTO v_codice, v_attivo, v_selector, v_doc_tabella,
           v_r_schema, v_r_tabella, v_r_fk,
           v_d_schema, v_d_tabella, v_d_fk
      FROM config.fn_sorgente_livelli(v_tipo) l;

    IF v_codice IS NULL OR v_attivo IS NOT TRUE OR v_doc_tabella IS NULL
       OR v_selector IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.trgfn_guard_sorgente', 'E_SORG_CONF',
            jsonb_build_object('detail', 'tipo di sorgente assente, spento o senza tabella',
                               'sorgente_tipo_id', v_tipo,
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
            NULL::uuid, COALESCE(v_codice, v_tipo::text));
    END IF;

    -- Un uid che non e' un uuid in forma canonica.
    IF v_uid_testo IS NOT NULL AND v_uid IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.trgfn_guard_sorgente', 'E_SORG_FORMATO',
            jsonb_build_object('sorgente_tipo_id', v_tipo,
                               'sorgente_uid', v_uid_testo,
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
            NULL::uuid, concat(v_codice, ': sorgente_uid non e'' un uuid, «', v_uid_testo, '»'));
    END IF;

    -- 2. una sola chiave, quella del tipo
    IF (v_selector = 'id'  AND (v_id  IS NULL OR v_uid_testo IS NOT NULL))
    OR (v_selector = 'uid' AND (v_uid IS NULL OR v_id IS NOT NULL)) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.trgfn_guard_sorgente', 'E_SORG_CHIAVE_NON_CONFORME',
            jsonb_build_object('sorgente_tipo_id', v_tipo,
                               'key_selector', v_selector,
                               'sorgente_id', v_id,
                               'sorgente_uid', v_uid_testo,
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
            NULL::uuid, v_codice,
            CASE WHEN v_selector = 'id' THEN 'sorgente_id' ELSE 'sorgente_uid' END);
    END IF;

    v_chiave := COALESCE(v_id::text, v_uid::text);

    -- 3. i livelli indicati sono livelli del tipo; il dettaglio con la sua riga
    IF v_dettaglio IS NOT NULL AND v_riga IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.trgfn_guard_sorgente', 'E_SORG_LIVELLO_NON_PREVISTO',
            jsonb_build_object('sorgente_tipo_id', v_tipo,
                               'sorgente_dettaglio', v_dettaglio,
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
            NULL::uuid, v_codice, 'un dettaglio senza la sua riga');
    END IF;

    IF v_riga IS NOT NULL THEN
        IF v_r_tabella IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.trgfn_guard_sorgente', 'E_SORG_LIVELLO_NON_PREVISTO',
                jsonb_build_object('sorgente_tipo_id', v_tipo,
                                   'sorgente_riga', v_riga,
                                   'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
                NULL::uuid, v_codice, 'una riga');
        END IF;
    END IF;

    IF v_dettaglio IS NOT NULL THEN
        IF v_d_tabella IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.trgfn_guard_sorgente', 'E_SORG_LIVELLO_NON_PREVISTO',
                jsonb_build_object('sorgente_tipo_id', v_tipo,
                                   'sorgente_dettaglio', v_dettaglio,
                                   'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
                NULL::uuid, v_codice, 'un dettaglio');
        END IF;
    END IF;

    -- 4. il livello minimo, limitato ai livelli che il tipo ha
    IF v_livello IN ('RIGA', 'DETTAGLIO') AND v_r_tabella IS NOT NULL AND v_riga IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.trgfn_guard_sorgente', 'E_SORG_LIVELLO_MANCANTE',
            jsonb_build_object('sorgente_tipo_id', v_tipo,
                               'livello_minimo', v_livello,
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
            NULL::uuid, v_codice, 'riga');
    END IF;

    IF v_livello = 'DETTAGLIO' AND v_d_tabella IS NOT NULL AND v_dettaglio IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.trgfn_guard_sorgente', 'E_SORG_LIVELLO_MANCANTE',
            jsonb_build_object('sorgente_tipo_id', v_tipo,
                               'livello_minimo', v_livello,
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
            NULL::uuid, v_codice, 'dettaglio');
    END IF;

    -- 5. il documento esiste ed e' visibile, col BB che risolve
    SELECT d.documento_id INTO v_doc_id
      FROM script.fn_sorgente_documento(v_tipo, v_id, v_uid) d;

    IF v_doc_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.trgfn_guard_sorgente', 'E_SORG_NOT_FOUND',
            jsonb_build_object('sorgente_tipo_id', v_tipo,
                               'sorgente_id', v_id,
                               'sorgente_uid', v_uid,
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
            NULL::uuid, concat(v_codice, ' ', v_chiave));
    END IF;

    -- 6. la riga e' del documento
    IF v_riga IS NOT NULL THEN
        EXECUTE format('SELECT true FROM %I.%I r WHERE r.id = $1 AND r.%I = $2',
                       v_r_schema, v_r_tabella, v_r_fk)
          INTO v_trovato
          USING v_riga, v_doc_id;

        IF v_trovato IS NOT TRUE THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.trgfn_guard_sorgente', 'E_SORG_RIGA_NON_DEL_DOCUMENTO',
                jsonb_build_object('sorgente_tipo_id', v_tipo,
                                   'documento_id', v_doc_id,
                                   'sorgente_riga', v_riga,
                                   'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
                NULL::uuid, v_riga::text, v_codice, v_chiave);
        END IF;
    END IF;

    -- 7. il dettaglio e' della riga
    IF v_dettaglio IS NOT NULL THEN
        v_trovato := NULL;
        EXECUTE format('SELECT true FROM %I.%I d WHERE d.id = $1 AND d.%I = $2',
                       v_d_schema, v_d_tabella, v_d_fk)
          INTO v_trovato
          USING v_dettaglio, v_riga;

        IF v_trovato IS NOT TRUE THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.trgfn_guard_sorgente', 'E_SORG_DETTAGLIO_NON_DELLA_RIGA',
                jsonb_build_object('sorgente_tipo_id', v_tipo,
                                   'documento_id', v_doc_id,
                                   'sorgente_riga', v_riga,
                                   'sorgente_dettaglio', v_dettaglio,
                                   'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
                NULL::uuid, v_dettaglio::text, v_riga::text, v_codice);
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_guard_sorgente()
IS 'Il guard unico della provenienza (sorgente_tipo_id + sorgente_id | sorgente_uid + sorgente_riga + sorgente_dettaglio). Su una riga con il tipo valorizzato verifica, prima la forma e poi l''esistenza: il tipo esiste, e'' attivo e dichiara la tabella del documento (E_SORG_CONF); c''e'' una sola chiave, quella del key_selector del tipo (E_SORG_CHIAVE_NON_CONFORME; E_SORG_FORMATO per un uid che non e'' un uuid); i livelli indicati esistono per il tipo e il dettaglio sta con la sua riga (E_SORG_LIVELLO_NON_PREVISTO); la riga arriva al livello minimo che la tabella chiede, se il tipo ce l''ha (E_SORG_LIVELLO_MANCANTE); il documento esiste ed e'' visibile a chi scrive, letto con script.fn_sorgente_documento (E_SORG_NOT_FOUND); la riga e'' del documento e il dettaglio della riga, nelle tabelle che config.sorgenti dichiara (E_SORG_RIGA_NON_DEL_DOCUMENTO, E_SORG_DETTAGLIO_NON_DELLA_RIGA). Argomenti del trigger, letti da script.fn_sorgente_guard_argomenti: livello minimo (DOCUMENTO, RIGA, DETTAGLIO) e azione quando l''origine si cancella (BLOCCA, CANCELLA). Le colonne si leggono da to_jsonb(NEW): quella che la tabella non ha vale NULL. Una riga senza tipo passa: la forma la tiene il CHECK della tabella. INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
