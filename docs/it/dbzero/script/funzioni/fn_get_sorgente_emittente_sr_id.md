{% include-markdown "it/dbzero/script/manual/fn_get_sorgente_emittente_sr_id.md" %}
# ⚙️ Funzione `fn_get_sorgente_emittente_sr_id`

```sql
CREATE FUNCTION fn_get_sorgente_emittente_sr_id(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_sorgente_emittente_sr_id(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_codice    config.sorgenti.codice_interno%TYPE;
    v_attivo    config.sorgenti.attivo%TYPE;
    v_selector  config.sorgenti.key_selector%TYPE;
    v_relid     pg_catalog.pg_class.oid%TYPE;
    v_schema    pg_catalog.pg_namespace.nspname%TYPE;
    v_tabella   pg_catalog.pg_class.relname%TYPE;
    v_colonna   pg_catalog.pg_attribute.attname%TYPE;
    v_chiave    text;      -- la chiave ricevuta resa a testo, per i messaggi
    v_doc_id    bigint;    -- id del documento: polimorfo, la tabella la dice il tipo
    v_valore    bigint;    -- la colonna letta: SR, emittente o BA, secondo la strada
    v_sr_id     anagrafiche.soggetti_ruoli.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dato (tipo sorgente, chiave del documento) dire CHI EMETTE
    --   quel documento, in convenzione soggetto_ruolo.
    --   La chiave e' quella delle colonne del modello: sorgente_id o
    --   sorgente_uid. Il documento lo risolve il BB
    --   script.fn_sorgente_documento (brief-db-sorgente-documento-e-riga
    --   §7.2 giro 0.3): qui si legge solo l'emittente, per id.
    --
    -- ⛔ NON si passa dal billing account se il documento ha un
    --   emittente: su ordini, preventivi, ddt e resi il BA e' NULLABLE,
    --   uno stato LEGALE; emittente_fiscale_id e' NOT NULL.
    --
    -- ⚠️ SECURITY DEFINER: le tabelle documento hanno la RLS. Da
    --   INVOKER la sorgente di un altro emittente sarebbe invisibile e
    --   il chiamante concluderebbe «non esiste» invece di «e' di un
    --   altro». Il BB che risolve e' INVOKER: chiamato da qui legge
    --   come il proprietario.
    --
    -- ⛔ Fail-closed ovunque: mai un NULL silenzioso.
    -- =========================================================
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_CONF',
            jsonb_build_object('detail', 'Tipo sorgente non valorizzato',
                               'sorgente_tipo_id', p_sorgente_tipo_id),
            NULL::uuid, COALESCE(p_sorgente_tipo_id::text, '<nessuno>'));
    END IF;

    SELECT l.codice_interno, l.attivo, l.key_selector,
           l.documento_relid, l.documento_schema, l.documento_tabella
      INTO v_codice, v_attivo, v_selector, v_relid, v_schema, v_tabella
      FROM config.fn_sorgente_livelli(p_sorgente_tipo_id) l;

    IF v_attivo IS NOT TRUE OR v_tabella IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_CONF',
            jsonb_build_object('detail', 'Sorgente non attiva o senza target_table',
                               'sorgente_tipo_id', p_sorgente_tipo_id,
                               'target_table', COALESCE(v_schema || '.' || v_tabella, '<NULL>')),
            NULL::uuid, p_sorgente_tipo_id::text);
    END IF;

    v_chiave := COALESCE(p_sorgente_id::text, p_sorgente_uid::text);
    IF v_chiave IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_KEY_MISSING',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                               'key_selector', v_selector),
            NULL::uuid, p_sorgente_tipo_id::text, v_selector);
    END IF;

    -- La strada, dal catalogo: prima la colonna SR (commesse, fatture,
    -- lotti: e' gia' la risposta), poi l'emittente del documento (i sei
    -- documenti, NOT NULL), poi il billing account (attivita_consumi,
    -- attivita_fatturabili). Nessuna delle tre: la sorgente non e'
    -- interrogabile, a prescindere dal documento.
    SELECT a.attname INTO v_colonna
      FROM pg_catalog.pg_attribute a
     WHERE a.attrelid = v_relid
       AND a.attname IN ('emittente_soggetto_ruolo_id', 'emittente_fiscale_id', 'billing_account_id')
       AND a.attnum > 0 AND NOT a.attisdropped
     ORDER BY array_position(ARRAY['emittente_soggetto_ruolo_id', 'emittente_fiscale_id',
                                   'billing_account_id']::name[], a.attname)
     LIMIT 1;

    IF v_colonna IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_CONF',
            jsonb_build_object('detail', 'target_table senza colonna emittente ne'' billing account',
                               'sorgente_tipo_id', p_sorgente_tipo_id,
                               'target_table', v_schema || '.' || v_tabella),
            NULL::uuid, p_sorgente_tipo_id::text);
    END IF;

    -- Il documento, dal BB che risolve: legge la chiave che riceve.
    SELECT d.documento_id INTO v_doc_id
      FROM script.fn_sorgente_documento(p_sorgente_tipo_id, p_sorgente_id, p_sorgente_uid) d;

    IF v_doc_id IS NOT NULL THEN
        EXECUTE format('SELECT t.%I::bigint FROM %I.%I t WHERE t.id = $1',
                       v_colonna, v_schema, v_tabella)
           INTO v_valore
          USING v_doc_id;

        IF v_colonna = 'emittente_soggetto_ruolo_id' THEN
            v_sr_id := v_valore;
        ELSIF v_colonna = 'emittente_fiscale_id' THEN
            SELECT ef.soggetto_ruolo_id INTO v_sr_id
              FROM anagrafiche.emittenti_fiscali ef
             WHERE ef.id = v_valore;
        ELSIF v_valore IS NOT NULL THEN
            v_sr_id := anagrafiche.fn_get_emittente_fiscale_id(v_valore);
        END IF;
    END IF;

    -- ⛔ Documento inesistente, oppure esistente ma senza un emittente
    --    risolvibile: per il chiamante sono la stessa cosa, e un NULL
    --    qui disarmerebbe il guard a valle.
    IF v_sr_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_EMITTENTE_NON_RISOLTO',
            jsonb_build_object('detail', 'documento inesistente o senza emittente risolvibile',
                               'sorgente_tipo_id', p_sorgente_tipo_id,
                               'sorgente_id', p_sorgente_id,
                               'sorgente_uid', p_sorgente_uid,
                               'target_table', v_schema || '.' || v_tabella),
            NULL::uuid, COALESCE(v_codice, p_sorgente_tipo_id::text), v_chiave);
    END IF;

    RETURN v_sr_id;
END;
$function$

COMMENT ON FUNCTION script.fn_get_sorgente_emittente_sr_id(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
IS '«Chi emette questo documento», per la sorgente polimorfa, sulle colonne del modello: dato il tipo (config.sorgenti) e la chiave del documento (sorgente_id o sorgente_uid) restituisce il soggetto_ruolo dell''emittente. Il documento lo risolve script.fn_sorgente_documento, con la chiave che riceve; qui si legge solo l''emittente, per id, per tre strade in ordine di direttezza: (1) emittente_soggetto_ruolo_id se la tabella ce l''ha (commesse, fatture, lotti); (2) emittente_fiscale_id tradotto in soggetto_ruolo (i documenti: e'' NOT NULL, mentre il billing account e'' facoltativo su ordini, preventivi, bolle e resi); (3) billing_account_id con anagrafiche.fn_get_emittente_fiscale_id (attivita_consumi, attivita_fatturabili). La strada la sceglie il catalogo prima del documento. Fail-closed, mai un NULL silenzioso: tipo assente o spento -> E_SORG_CONF; nessuna chiave -> E_SORG_KEY_MISSING; tabella senza nessuna delle tre colonne -> E_SORG_CONF; documento inesistente o senza emittente -> E_SORG_EMITTENTE_NON_RISOLTO. SECURITY DEFINER: da INVOKER la sorgente di un altro emittente sarebbe invisibile sotto RLS, e il chiamante concluderebbe «non esiste» invece di «e'' di un altro». La porta testuale (tipo, chiave text) controlla la forma e passa qui.';
```

</div>

---
{% include-markdown "signature-core.md" %}
