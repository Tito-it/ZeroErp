# ⚙️ Funzione `fn_sorgente_provenienza`

```sql
CREATE FUNCTION fn_sorgente_provenienza(p_codice_interno character varying, p_chiave text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_sorgente_provenienza(p_codice_interno character varying, p_chiave text)
 RETURNS TABLE(sorgente_tipo_id bigint, sorgente_id bigint, sorgente_uid uuid)
 LANGUAGE plpgsql
 STABLE ROWS 1
AS $function$
DECLARE
    v_tipo config.sorgenti.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: la provenienza da scrivere su una riga nata da un
    --   documento, citato col codice del suo tipo e con una sua
    --   chiave qualsiasi: il tipo e la chiave giusta per il
    --   key_selector, da script.fn_sorgente_chiave.
    -- Ritorna: una riga.
    -- ⛔ Solleva su un codice che non e' un tipo (E_SORG_CONF) e,
    --   tramite script.fn_sorgente_chiave, su tutto cio' che non e'
    --   un documento esistente e visibile.
    -- =========================================================
    SELECT s.id INTO v_tipo
      FROM config.sorgenti s
     WHERE s.codice_interno = p_codice_interno;

    IF v_tipo IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_sorgente_provenienza', 'E_SORG_CONF',
            jsonb_build_object('codice_interno', p_codice_interno),
            NULL::uuid, COALESCE(p_codice_interno, '<nessuno>'));
    END IF;

    RETURN QUERY
    SELECT v_tipo, k.sorgente_id, k.sorgente_uid
      FROM script.fn_sorgente_chiave(v_tipo, p_chiave) k;
END;
$function$

COMMENT ON FUNCTION script.fn_sorgente_provenienza(p_codice_interno character varying, p_chiave text)
IS 'La provenienza da scrivere su una riga nata da un documento, citato col codice del suo tipo (config.sorgenti.codice_interno) e con una sua chiave qualsiasi, id o uid in forma canonica: una riga (sorgente_tipo_id, sorgente_id, sorgente_uid), con la sola chiave del key_selector del tipo. La chiave e la verifica del documento sono di script.fn_sorgente_chiave. La chiamano i verbi che generano righe da un documento, una volta per documento; sorgente_riga la mette il verbo, riga per riga. Solleva E_SORG_CONF su un codice che non e'' un tipo, e gli errori di script.fn_sorgente_chiave (tipo spento, chiave mancante o malformata, documento assente o non visibile). STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
