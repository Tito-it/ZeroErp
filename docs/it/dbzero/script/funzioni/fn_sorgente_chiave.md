# ⚙️ Funzione `fn_sorgente_chiave`

```sql
CREATE FUNCTION fn_sorgente_chiave(p_sorgente_tipo_id bigint, p_chiave text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_sorgente_chiave(p_sorgente_tipo_id bigint, p_chiave text)
 RETURNS TABLE(sorgente_id bigint, sorgente_uid uuid)
 LANGUAGE plpgsql
 STABLE ROWS 1
AS $function$
DECLARE
    v_codice    config.sorgenti.codice_interno%TYPE;
    v_attivo    config.sorgenti.attivo%TYPE;
    v_selector  config.sorgenti.key_selector%TYPE;
    v_tabella   pg_catalog.pg_class.relname%TYPE;
    v_ha_uid    boolean;
    v_chiave_id  bigint;
    v_chiave_uid uuid;
    v_doc_id    bigint;
    v_doc_uid   uuid;
BEGIN
    -- =========================================================
    -- Scopo: la chiave da scrivere nelle colonne della
    --   provenienza, per il key_selector del tipo, da una chiave
    --   qualsiasi del documento (id o uid, in testo).
    -- Ritorna: una riga, (sorgente_id, NULL) o (NULL, sorgente_uid).
    -- ⛔ Solleva su tutto cio' che non e' un documento esistente
    --   e visibile.
    -- =========================================================
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_sorgente_chiave', 'E_SORG_CONF',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id),
            NULL::uuid, COALESCE(p_sorgente_tipo_id::text, '<nessuno>'));
    END IF;

    SELECT l.codice_interno, l.attivo, l.key_selector, l.documento_tabella, l.documento_ha_uid
      INTO v_codice, v_attivo, v_selector, v_tabella, v_ha_uid
      FROM config.fn_sorgente_livelli(p_sorgente_tipo_id) l;

    IF v_codice IS NULL OR v_attivo IS NOT TRUE OR v_tabella IS NULL
       OR v_selector IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_sorgente_chiave', 'E_SORG_CONF',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                               'codice_interno', v_codice,
                               'attivo', v_attivo,
                               'key_selector', v_selector),
            NULL::uuid, COALESCE(v_codice, p_sorgente_tipo_id::text));
    END IF;

    IF p_chiave IS NULL OR btrim(p_chiave) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_sorgente_chiave', 'E_SORG_KEY_MISSING',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                               'key_selector', v_selector),
            NULL::uuid, v_codice, v_selector);
    END IF;

    -- La forma CANONICA, con la stessa regola di chi la cerca.
    v_chiave_id  := script.fn_sorgente_chiave_id(p_chiave);
    v_chiave_uid := script.fn_sorgente_chiave_uuid(p_chiave);

    IF v_chiave_id IS NULL AND v_chiave_uid IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_sorgente_chiave', 'E_SORG_FORMATO',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                               'chiave', p_chiave,
                               'key_selector', v_selector),
            NULL::uuid,
            concat(v_codice, ': atteso un id o un uuid in forma canonica, ricevuto «',
                   p_chiave, '»'));
    END IF;

    -- Un uuid per un tipo a chiave id: si traduce, se la tabella ha l'uid.
    IF v_chiave_uid IS NOT NULL AND v_selector = 'id' AND NOT v_ha_uid THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_sorgente_chiave', 'E_SORG_NORM_NON_RISOLTA',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                               'chiave', p_chiave,
                               'detail', 'la tabella del documento non ha la colonna uid'),
            NULL::uuid, concat(v_codice, ' non si cita per uid; uid ', p_chiave));
    END IF;

    -- La traduzione e la verifica d'esistenza: il BB che risolve.
    SELECT d.documento_id, d.documento_uid
      INTO v_doc_id, v_doc_uid
      FROM script.fn_sorgente_documento(p_sorgente_tipo_id, v_chiave_id, v_chiave_uid) d;

    IF v_doc_id IS NULL THEN
        IF v_chiave_uid IS NOT NULL AND v_selector = 'id' THEN
            PERFORM script.fn_log_and_raise_error(
                'script', 'fn_sorgente_chiave', 'E_SORG_NORM_NON_RISOLTA',
                jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                                   'chiave', p_chiave,
                                   'detail', 'nessun documento con questo uid'),
                NULL::uuid, concat(v_codice, ' con uid ', p_chiave, ' non trovato'));
        END IF;
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_sorgente_chiave', 'E_SORG_NOT_FOUND',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                               'chiave', p_chiave,
                               'key_selector', v_selector),
            NULL::uuid, concat(v_codice, ' ', p_chiave));
    END IF;

    IF v_selector = 'id' THEN
        sorgente_id  := v_doc_id;
        sorgente_uid := NULL;
    ELSE
        sorgente_id  := NULL;
        sorgente_uid := v_doc_uid;
    END IF;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION script.fn_sorgente_chiave(p_sorgente_tipo_id bigint, p_chiave text)
IS 'Il BB che scrive la provenienza: da tipo (config.sorgenti) e una chiave qualsiasi del documento in testo, l''id o l''uid in forma canonica, la coppia da scrivere nelle colonne: (sorgente_id, NULL) se il tipo ha key_selector id, (NULL, sorgente_uid) se uid. Una chiave dell''altra specie si traduce leggendo il documento con script.fn_sorgente_documento. Solleva: E_SORG_CONF (tipo assente, spento o senza tabella), E_SORG_KEY_MISSING (chiave vuota), E_SORG_FORMATO (ne'' id ne'' uuid in forma canonica), E_SORG_NORM_NON_RISOLTA (uuid per un tipo a chiave id che non si traduce), E_SORG_NOT_FOUND (documento che non esiste o non e'' visibile a chi scrive: INVOKER). La riga e il dettaglio non passano di qui: li verifica il guard script.trgfn_guard_sorgente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
