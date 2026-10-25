{% include-markdown "it/dbzero/script/manual/fn_doc_azione_passaggio.md" %}
# ⚙️ Funzione `fn_doc_azione_passaggio`

```sql
CREATE FUNCTION fn_doc_azione_passaggio(p_testata regclass, p_documento_id bigint, p_stato_a_codice text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_azione_passaggio(p_testata regclass, p_documento_id bigint, p_stato_a_codice text)
 RETURNS TABLE(stato_da_id bigint, stato_a_id bigint, emissione boolean, nella_matrice boolean, manuale boolean, azione_processo_codename character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- Testata, documento e stati di una qualunque testata della
    -- mappa: bigint in tutti, nessuna colonna comune a cui
    -- ancorarli. La colonna di stato e' un nome.
    v_col     text;
    v_da      bigint;
    v_a       bigint;
    v_manuale boolean;
    v_azione  config.azioni_processo.permission_codename%TYPE;
    v_trovata boolean;
BEGIN
    -- =========================================================
    -- Scopo: che cosa chiede il passaggio di questo documento
    --   verso lo stato chiesto. Una riga se il documento si
    --   vede, nessuna altrimenti.
    -- =========================================================
    SELECT m.colonna_stato
      INTO v_col
      FROM script.fn_doc_stato_modello(p_testata) m;

    IF v_col IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_doc_azione_passaggio', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text),
            NULL::uuid,
            'script.fn_doc_azione_passaggio',
            'p_testata: una testata della mappa del modello (script.fn_doc_stato_modello)');
    END IF;

    -- Lo stato corrente, sotto la RLS di chi chiama.
    EXECUTE format('SELECT t.%I FROM %s t WHERE t.id = $1', v_col, p_testata)
       INTO v_da
      USING p_documento_id;

    IF v_da IS NULL THEN
        RETURN;
    END IF;

    v_a := script.fn_doc_stato_id(p_testata, p_stato_a_codice);

    SELECT p.manuale, p.azione_processo_codename
      INTO v_manuale, v_azione
      FROM script.fn_doc_passaggio(p_testata, v_da, v_a) p;
    v_trovata := FOUND;

    RETURN QUERY
    SELECT v_da,
           v_a,
           COALESCE(v_a = script.fn_stato_emissione_id(p_testata), false),
           v_trovata,
           v_manuale,
           v_azione;
END;
$function$

COMMENT ON FUNCTION script.fn_doc_azione_passaggio(p_testata regclass, p_documento_id bigint, p_stato_a_codice text)
IS 'Lettore del modello del documento per il backend: per un documento (testata della mappa + id) e il codice_interno dello stato chiesto, che cosa chiede quel passaggio. Una riga se il documento esiste e chi chiama lo vede (SECURITY INVOKER: la RLS di chi chiama), nessuna altrimenti. Colonne: stato_da_id (corrente), stato_a_id (script.fn_doc_stato_id: NULL se il codice non e'' uno stato attivo), emissione (lo stato chiesto e'' quello di emissione, script.fn_stato_emissione_id: il cambio stato generico lo rifiuta, M-2), nella_matrice / manuale / azione_processo_codename (la riga del passaggio, script.fn_doc_passaggio; nella_matrice = false: il passaggio non e'' nella matrice e manuale e azione sono NULL). Non decide: il backend applica la regola del verbo (azione -> permesso dell''azione, nessuna azione -> livello sul documento) prima di aprire la transazione. Testata fuori mappa, o non ancora portata al modello (matrice senza azione_processo_codename): E_SCRIPT_CHIAMATA_NON_VALIDA. Brief: brief-modello-documento-vendita §8 (richiesta del team BE, Tid 2026-10-25).';
```

</div>

---
{% include-markdown "signature-core.md" %}
