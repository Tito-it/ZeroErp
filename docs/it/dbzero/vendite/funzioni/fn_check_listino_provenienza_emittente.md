# ⚙️ Funzione `fn_check_listino_provenienza_emittente`

```sql
CREATE FUNCTION fn_check_listino_provenienza_emittente(p_emittente_soggetto_ruolo_id bigint, p_articolo_id uuid, p_uom_id bigint, p_listino_versione_id bigint, p_listino_riga_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_check_listino_provenienza_emittente(p_emittente_soggetto_ruolo_id bigint, p_articolo_id uuid, p_uom_id bigint, p_listino_versione_id bigint, p_listino_riga_id bigint)
 RETURNS text
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_riga_articolo     vendite.listini_righe.articolo_id%TYPE;
    v_riga_uom          vendite.listini_righe.uom_id%TYPE;
    v_riga_versione     vendite.listini_righe.listino_versione_id%TYPE;
    v_versione          vendite.listini_versioni.id%TYPE := p_listino_versione_id;
    v_stato             config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_emittente_listino vendite.listini.emittente_soggetto_ruolo_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   il codice del primo motivo per cui la riga e la versione
    --   di listino citate per un prezzo non sono ammesse per
    --   l'emittente dato; NULL = ammesse.
    --   1. riga di listino incoerente con articolo, UoM, versione
    --   2. listino di un altro emittente
    --   3. versione in BOZZA
    -- =========================================================

    -- 1. La riga di listino: articolo, unita' di misura, versione.
    IF p_listino_riga_id IS NOT NULL THEN
        SELECT lr.articolo_id, lr.uom_id, lr.listino_versione_id
          INTO v_riga_articolo, v_riga_uom, v_riga_versione
          FROM vendite.listini_righe lr
         WHERE lr.id = p_listino_riga_id;

        IF NOT FOUND
           OR v_riga_articolo IS DISTINCT FROM p_articolo_id
           OR v_riga_uom      IS DISTINCT FROM p_uom_id
           OR (v_versione IS NOT NULL AND v_riga_versione <> v_versione) THEN
            RETURN 'E_ATTIVITA_LISTINO_RIGA_INCOERENTE';
        END IF;

        v_versione := v_riga_versione;
    END IF;

    -- Ne' riga ne' versione: niente da giudicare.
    IF v_versione IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT s.codice_interno, l.emittente_soggetto_ruolo_id
      INTO v_stato, v_emittente_listino
      FROM vendite.listini_versioni lv
      JOIN vendite.listini l ON l.id = lv.listino_id
      JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
     WHERE lv.id = v_versione;

    -- 2. Il listino e' dell'emittente dato.
    IF v_emittente_listino IS DISTINCT FROM p_emittente_soggetto_ruolo_id THEN
        RETURN 'E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO';
    END IF;

    -- 3. Mai un prezzo da una versione in bozza.
    IF v_stato = 'BOZZA' THEN
        RETURN 'E_ATTIVITA_LISTINO_VERSIONE_BOZZA';
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.fn_check_listino_provenienza_emittente(p_emittente_soggetto_ruolo_id bigint, p_articolo_id uuid, p_uom_id bigint, p_listino_versione_id bigint, p_listino_riga_id bigint)
IS 'Check: il codice del primo motivo per cui la riga e la versione di listino citate come provenienza di un prezzo non sono ammesse per l''emittente dato (soggetto_ruolo dell''azienda che emette il documento o la commessa); NULL = ammesse. Motivi in ordine: 1) E_ATTIVITA_LISTINO_RIGA_INCOERENTE: la riga di listino non c''e'', o non e'' dell''articolo e dell''unita'' di misura dati, o (se la versione e'' data) non e'' di quella versione; 2) E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO: il listino della versione (data, o quella della riga) e'' di un altro emittente, o l''emittente non e'' dato; 3) E_ATTIVITA_LISTINO_VERSIONE_BOZZA: quella versione e'' in BOZZA. Ne'' riga ne'' versione: NULL. SECURITY DEFINER: listini e versioni hanno la RLS per emittente, e letti con la RLS di chi scrive un listino di un''altra azienda tornerebbero a vuoto. Ritorna solo un codice e non solleva: lo fanno vendite.trgfn_attivita_guard_listino_riga (righe di commessa e attivita'' fatturabili, attraverso vendite.fn_check_listino_provenienza) e vendite.trgfn_riga_documento_guard_listino_provenienza (righe e componenti dei documenti).';
```

</div>

---
{% include-markdown "signature-core.md" %}
