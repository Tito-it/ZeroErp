# ⚙️ Funzione `fn_annulla_contratto`

```sql
CREATE FUNCTION fn_annulla_contratto(p_contratto_id bigint, p_legami_confermati integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_contratto(p_contratto_id bigint, p_legami_confermati integer DEFAULT NULL::integer)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- =========================================================
-- Scopo: annullare un contratto. Con legami: conferma e ritiro
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
    IF p_contratto_id IS NULL OR p_contratto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_contratto',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_contratto_id', p_contratto_id),
            NULL::uuid, 'vendite.fn_annulla_contratto',
            'p_contratto_id (obbligatorio, maggiore di zero)');
    END IF;

    -- 2. La testata FOR UPDATE, nel perimetro (predicato della
    --    policy: DEFINER). Fuori perimetro come inesistente.
    SELECT true
      INTO v_trovato
      FROM vendite.contratti t
     WHERE t.id = p_contratto_id
       AND script.fn_scope_ef_whitelist_via_contratto(v_utente, t.id)
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_contratto',
            'E_CONTRATTO_NON_TROVATO', jsonb_build_object('id', p_contratto_id), NULL::uuid,
            p_contratto_id::text);
    END IF;

    -- 3. Conferma e ritiro: il BB apre la porta e la lascia aperta.
    v_legami := vendite.fn_documento_ritira_legami('CONTRATTO', p_contratto_id, p_legami_confermati);

    -- 4. Lo stato, dal verbo di stato (rev 2026-10-26, 20261026-09):
    --    lo stato d'annullo dal vocabolario, non dal letterale. I guard
    --    della tabella fanno il resto: matrice, freni (righe di
    --    commessa EMESSA, figli vivi), avviso. La prima riga del verbo
    --    dice lo stato che ha gia' (E_DOC_GIA_NELLO_STATO).
    PERFORM vendite.fn_cambia_stato_contratto(
        p_contratto_id,
        script.fn_doc_stato_codice('vendite.contratti'::regclass,
                                   script.fn_stato_abortito_id('vendite.contratti'::regclass)));

    -- 5. Porta chiusa.
    PERFORM set_config('zeroerp.doc_ritira_legami', '', true);

    RETURN v_legami;
END;
$function$

COMMENT ON FUNCTION vendite.fn_annulla_contratto(p_contratto_id bigint, p_legami_confermati integer)
IS 'VERBO (2026-10-11, brief-db-annullo-documento-con-legami D-1/D-4): annulla un contratto. Testata FOR UPDATE nel perimetro (script.fn_scope_ef_whitelist_via_contratto; fuori perimetro E_CONTRATTO_NON_TROVATO). Conferma e ritiro dal BB vendite.fn_documento_ritira_legami: chi conferma DICHIARA quanti legami ha visto (p_legami_confermati, le righe di vendite.fn_documento_legami(''CONTRATTO'', id): offerta d''origine, righe di commessa NON_EMESSA); se non corrisponde, E_DOC_ANNULLO_CON_LEGAMI. Poi lo stato passa ad ANNULLATO (i guard della tabella applicano matrice e freni) e la porta del ritiro si chiude. UNA transazione. Senza legami non c''e'' niente da confermare. Ritorna i legami confermati. SECURITY DEFINER con search_path bloccato: la porta del ritiro vuole il proprietario. EXECUTE solo all''app. ⭐ rev 2026-10-26 (20261026-09, brief-modello-documento-vendita §11): lo stato lo scrive il verbo di stato vendite.fn_cambia_stato_contratto (porta, prima riga comune), e lo stato d''annullo si legge dal vocabolario (script.fn_stato_abortito_id, script.fn_doc_stato_codice) invece del letterale ''ANNULLATO''.';
```

</div>

---
{% include-markdown "signature-core.md" %}
