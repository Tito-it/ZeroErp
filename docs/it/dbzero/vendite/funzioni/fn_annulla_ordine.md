# ⚙️ Funzione `fn_annulla_ordine`

```sql
CREATE FUNCTION fn_annulla_ordine(p_ordine_id bigint, p_legami_confermati integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_ordine(p_ordine_id bigint, p_legami_confermati integer DEFAULT NULL::integer)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$

-- =========================================================
-- Scopo: annullare un ordine. Con legami: conferma e ritiro
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
    IF p_ordine_id IS NULL OR p_ordine_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_ordine',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_ordine_id', p_ordine_id),
            NULL::uuid, 'vendite.fn_annulla_ordine',
            'p_ordine_id (obbligatorio, maggiore di zero)');
    END IF;

    -- 2. La testata FOR UPDATE, nel perimetro (predicato della
    --    policy: DEFINER). Fuori perimetro come inesistente.
    SELECT true
      INTO v_trovato
      FROM vendite.ordini t
     WHERE t.id = p_ordine_id
       AND script.fn_scope_ef_whitelist_via_ordine(v_utente, t.id)
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_ordine',
            'E_ORD_NOT_FOUND', jsonb_build_object('id', p_ordine_id), NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 3. Conferma e ritiro: il BB apre la porta e la lascia aperta.
    v_legami := vendite.fn_documento_ritira_legami('ORDINE_VENDITA', p_ordine_id, p_legami_confermati);

    -- 4. Lo stato, dal verbo di stato (rev 2026-10-25, 20261025-76):
    --    lo stato d'annullo dal vocabolario, non dal letterale. I guard
    --    della tabella fanno il resto: matrice, freni (righe di
    --    commessa EMESSA, figli vivi), avviso. L'azione del passaggio
    --    (emetti_ordine sull'annullo del confermato) la chiede la sua
    --    prima riga.
    PERFORM vendite.fn_cambia_stato_ordine(
        p_ordine_id,
        script.fn_doc_stato_codice('vendite.ordini'::regclass,
                                   script.fn_stato_abortito_id('vendite.ordini'::regclass)));

    -- 5. Porta chiusa.
    PERFORM set_config('zeroerp.doc_ritira_legami', '', true);

    RETURN v_legami;
END;
$function$

COMMENT ON FUNCTION vendite.fn_annulla_ordine(p_ordine_id bigint, p_legami_confermati integer)
IS 'VERBO (2026-10-11, brief-db-annullo-documento-con-legami D-1/D-4): annulla un ordine. Testata FOR UPDATE nel perimetro (script.fn_scope_ef_whitelist_via_ordine; fuori perimetro E_ORD_NOT_FOUND). Conferma e ritiro dal BB vendite.fn_documento_ritira_legami: chi conferma DICHIARA quanti legami ha visto (p_legami_confermati, le righe di vendite.fn_documento_legami(''ORDINE'', id): righe di preventivo, offerta d''origine, righe di commessa NON_EMESSA); se non corrisponde, E_DOC_ANNULLO_CON_LEGAMI. Poi lo stato passa ad ANNULLATO (i guard della tabella applicano matrice e freni) e la porta del ritiro si chiude. UNA transazione. Senza legami non c''e'' niente da confermare. Ritorna i legami confermati. SECURITY DEFINER con search_path bloccato: la porta del ritiro vuole il proprietario. EXECUTE solo all''app. ⭐ rev 2026-10-19 (20261019-61, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. ⭐ rev 2026-10-25 (20261025-76, brief-modello-documento-vendita §9): lo stato lo scrive il verbo di stato vendite.fn_cambia_stato_ordine (porta, permesso del passaggio: emetti_ordine sull''annullo del confermato), e lo stato d''annullo si legge dal vocabolario (script.fn_stato_abortito_id, script.fn_doc_stato_codice) invece del letterale ''ANNULLATO''.';
```

</div>

---
{% include-markdown "signature-core.md" %}
