{% include-markdown "it/dbzero/vendite/manual/fn_annulla_commessa.md" %}
# ⚙️ Funzione `fn_annulla_commessa`

```sql
CREATE FUNCTION fn_annulla_commessa(p_commessa_id bigint, p_legami_confermati integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_commessa(p_commessa_id bigint, p_legami_confermati integer DEFAULT NULL::integer)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- =========================================================
-- Scopo: annullare una commessa. Con legami: prima cio' che
--   vieta, poi conferma e ritiro dal BB
--   vendite.fn_documento_ritira_legami, poi lo stato.
--   p_legami_confermati e' un CONTEGGIO: tipo nudo. Vedi
--   l'intestazione del changeSet.
-- Ritorna: i legami confermati (0 se non ce n'erano).
-- =========================================================
DECLARE
    v_utente  config.user_override_azioni.auth_user_id%TYPE;
    -- Esito della presa della testata (SELECT true): un flag, nessuna
    -- colonna di cui sia il riflesso.
    v_trovato boolean;
    -- CONTEGGIO dei legami confermati.
    v_legami  integer;
BEGIN
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametri.
    IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_commessa',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_commessa_id', p_commessa_id),
            NULL::uuid, 'vendite.fn_annulla_commessa',
            'p_commessa_id (obbligatorio, maggiore di zero)');
    END IF;

    -- 2. La testata FOR UPDATE, nel perimetro (predicato della
    --    policy: DEFINER). Fuori perimetro come inesistente.
    SELECT true
      INTO v_trovato
      FROM vendite.commesse t
     WHERE t.id = p_commessa_id
       AND script.fn_scope_ef_whitelist_via_commessa(v_utente, t.id)
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_commessa',
            'E_COMMESSA_NON_TROVATA',
            jsonb_build_object('p_commessa_id', p_commessa_id), NULL::uuid,
            p_commessa_id::text);
    END IF;

    -- 3. Prima cio' che vieta (righe EMESSA), poi conferma e ritiro:
    --    il BB apre la porta e la lascia aperta.
    v_legami := vendite.fn_documento_ritira_legami('COMMESSA', p_commessa_id, p_legami_confermati);

    -- 4. Lo stato, dal verbo di stato (rev 2026-10-26, 20261026-33,
    --    brief-modello-documento-vendita §14): firma senza p_user (C-4),
    --    lo stato d'annullo dal vocabolario, non dal letterale. La prima
    --    riga del verbo chiede l'azione del passaggio (cambia_stato_commessa
    --    sull'annullo di una commessa non in bozza, C-1); i guard della
    --    tabella fanno il resto: matrice, motivi, avviso (che con le righe
    --    ritirate non ha piu' niente da dire).
    PERFORM vendite.fn_cambia_stato_commessa(
        p_commessa_id,
        script.fn_doc_stato_codice('vendite.commesse'::regclass,
                                   script.fn_stato_abortito_id('vendite.commesse'::regclass)));

    -- 5. Porta chiusa.
    PERFORM set_config('zeroerp.doc_ritira_legami', '', true);

    RETURN v_legami;
END;
$function$

COMMENT ON FUNCTION vendite.fn_annulla_commessa(p_commessa_id bigint, p_legami_confermati integer)
IS 'VERBO (2026-10-12, brief-db-annullo-a-valle-riapre-a-monte D-1/D-2/D-3/D-7 di Tid): annulla una commessa. Testata FOR UPDATE nel perimetro (script.fn_scope_ef_whitelist_via_commessa; fuori perimetro E_COMMESSA_NON_TROVATA). Dal BB vendite.fn_documento_ritira_legami: prima i motivi che vietano (script.fn_check_commessa_annullabile, righe EMESSA: E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE), poi la conferma — chi conferma DICHIARA quanti legami ha visto (p_legami_confermati, le righe di vendite.fn_documento_legami(''COMMESSA'', id): le righe NON_EMESSA); se non corrisponde, E_DOC_ANNULLO_CON_LEGAMI — poi il ritiro: righe con sorgente ANNULLATA col registro (il documento o il consumo torna da mandare, il preventivo EVASO torna ACCETTATO dal trigger delle righe), accrediti annullati (il reso torna da accreditare), oneri annullati. Poi lo stato passa ad ANNULLATA (vendite.fn_cambia_stato_commessa: matrice e guard) e la porta del ritiro si chiude. L''ordine non cambia stato (D-6): torna solo da mandare. UNA transazione. Senza legami non c''e'' niente da confermare. Ritorna i legami confermati. SECURITY DEFINER con search_path bloccato. EXECUTE solo all''app. ⭐ rev 2026-10-26 (20261026-33, brief-modello-documento-vendita §14): lo stato dal verbo di stato vendite.fn_cambia_stato_commessa nella firma nuova (senza p_user, C-4), che chiede l''azione del passaggio (cambia_stato_commessa sull''annullo di una commessa non in bozza, C-1); lo stato d''annullo dal vocabolario (script.fn_stato_abortito_id, script.fn_doc_stato_codice) invece del letterale ''ANNULLATA''.';
```

</div>

---
{% include-markdown "signature-core.md" %}
