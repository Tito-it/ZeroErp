# ⚙️ Funzione `fn_annulla_preventivo`

```sql
CREATE FUNCTION fn_annulla_preventivo(p_preventivo_id bigint, p_legami_confermati integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_preventivo(p_preventivo_id bigint, p_legami_confermati integer DEFAULT NULL::integer)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- =========================================================
-- Scopo: annullare un preventivo. Con legami: conferma e ritiro
--   dal BB vendite.fn_documento_ritira_legami, poi lo stato.
--   p_legami_confermati e' un CONTEGGIO: tipo nudo. Vedi
--   l'intestazione del changeSet.
-- Ritorna: i legami confermati (0 se non ce n'erano).
-- =========================================================
DECLARE
    v_utente  config.user_override_azioni.auth_user_id%TYPE;
    v_trovato boolean;
    -- CONTEGGIO dei legami confermati.
    v_legami  integer;
BEGIN
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametri.
    IF p_preventivo_id IS NULL OR p_preventivo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_preventivo',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_preventivo_id', p_preventivo_id),
            NULL::uuid, 'vendite.fn_annulla_preventivo',
            'p_preventivo_id (obbligatorio, maggiore di zero)');
    END IF;

    -- 2. La testata FOR UPDATE, nel perimetro (predicato della
    --    policy: DEFINER). Fuori perimetro come inesistente.
    SELECT true
      INTO v_trovato
      FROM vendite.preventivi t
     WHERE t.id = p_preventivo_id
       AND script.fn_scope_ef_whitelist_via_preventivo(v_utente, t.id)
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_preventivo',
            'E_PREV_NOT_FOUND', jsonb_build_object('id', p_preventivo_id), NULL::uuid,
            p_preventivo_id::text);
    END IF;

    -- 3. Conferma e ritiro: il BB apre la porta e la lascia aperta.
    v_legami := vendite.fn_documento_ritira_legami('PREVENTIVO', p_preventivo_id, p_legami_confermati);

    -- 4. Lo stato, dal verbo di stato (rev 2026-10-25, 20261025-43:
    --    firma senza p_user). I guard della tabella fanno il resto:
    --    matrice, freni (righe di commessa EMESSA, figli vivi), avviso.
    --    L'azione del passaggio (emetti_preventivo sull'annullo
    --    dell'emesso e dell'accettato) la chiede la sua prima riga.
    --    rev 2026-10-25 (20261025-77): lo stato d'annullo dal
    --    vocabolario, non dal letterale.
    PERFORM vendite.fn_cambia_stato_preventivo(
        p_preventivo_id,
        script.fn_doc_stato_codice('vendite.preventivi'::regclass,
                                   script.fn_stato_abortito_id('vendite.preventivi'::regclass)));

    -- 5. Porta chiusa.
    PERFORM set_config('zeroerp.doc_ritira_legami', '', true);

    RETURN v_legami;
END;
$function$

COMMENT ON FUNCTION vendite.fn_annulla_preventivo(p_preventivo_id bigint, p_legami_confermati integer)
IS 'VERBO (2026-10-11, brief-db-annullo-documento-con-legami D-1/D-4): annulla un preventivo. Testata FOR UPDATE nel perimetro (script.fn_scope_ef_whitelist_via_preventivo; fuori perimetro E_PREV_NOT_FOUND). Conferma e ritiro dal BB vendite.fn_documento_ritira_legami: chi conferma DICHIARA quanti legami ha visto (p_legami_confermati, le righe di vendite.fn_documento_legami(''PREVENTIVO'', id): righe di commessa NON_EMESSA); se non corrisponde, E_DOC_ANNULLO_CON_LEGAMI. Poi lo stato passa ad ANNULLATO dal verbo di stato vendite.fn_cambia_stato_preventivo (la riga del passaggio chiede emetti_preventivo sull''annullo dell''emesso e dell''accettato; i guard della tabella applicano matrice e freni) e la porta del ritiro si chiude. UNA transazione. Senza legami non c''e'' niente da confermare. Ritorna i legami confermati. SECURITY DEFINER con search_path bloccato: la porta del ritiro vuole il proprietario. EXECUTE solo all''app. rev 2026-10-25 (20261025-43, brief-modello-documento-vendita §8): il verbo di stato con la firma (id, stato). rev 2026-10-25 (20261025-77, brief-modello-documento-vendita §9, Z-3): lo stato d''annullo dal vocabolario (script.fn_stato_abortito_id, script.fn_doc_stato_codice), non dal letterale ''ANNULLATO''.';
```

</div>

---
{% include-markdown "signature-core.md" %}
