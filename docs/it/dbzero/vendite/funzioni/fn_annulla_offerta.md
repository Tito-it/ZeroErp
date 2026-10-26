{% include-markdown "it/dbzero/vendite/manual/fn_annulla_offerta.md" %}
# ⚙️ Funzione `fn_annulla_offerta`

```sql
CREATE FUNCTION fn_annulla_offerta(p_offerta_id bigint, p_motivazione text, p_legami_confermati integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_offerta(p_offerta_id bigint, p_motivazione text, p_legami_confermati integer DEFAULT NULL::integer)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- =========================================================
-- Scopo: annullare un'offerta. Con legami (la revisione
--   precedente che torna emessa): conferma dal BB
--   vendite.fn_documento_ritira_legami, poi lo stato col verbo
--   di stato, che chiede la motivazione.
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
    IF p_offerta_id IS NULL OR p_offerta_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_offerta',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_offerta_id', p_offerta_id),
            NULL::uuid, 'vendite.fn_annulla_offerta',
            'p_offerta_id (obbligatorio, maggiore di zero)');
    END IF;

    -- 2. La testata FOR UPDATE, nel perimetro (predicato della
    --    policy: DEFINER). Fuori perimetro come inesistente.
    SELECT true
      INTO v_trovato
      FROM vendite.offerte_commerciali t
     WHERE t.id = p_offerta_id
       AND script.fn_scope_ef_whitelist_via_offerta(v_utente, t.id)
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_offerta',
            'E_OFFERTA_NON_TROVATA', jsonb_build_object('id', p_offerta_id), NULL::uuid,
            p_offerta_id::text);
    END IF;

    -- 3. Prima cio' che vieta, poi la conferma: il BB apre la
    --    porta e la lascia aperta.
    v_legami := vendite.fn_documento_ritira_legami('OFFERTA_COMMERCIALE', p_offerta_id,
                                                   p_legami_confermati);

    -- 4. Lo stato, dal verbo di stato, con la motivazione (O-3):
    --    lo stato d'annullo dal vocabolario. La prima riga del
    --    verbo dice lo stato che ha gia' e l'azione (emetti_offerta
    --    sull'annullo dell'accettata); i guard della tabella fanno
    --    il resto: matrice, documenti vivi, avviso.
    PERFORM vendite.fn_cambia_stato_offerta(
        p_offerta_id,
        script.fn_doc_stato_codice('vendite.offerte_commerciali'::regclass,
                                   script.fn_stato_abortito_id('vendite.offerte_commerciali'::regclass)),
        p_motivazione);

    -- 5. Porta chiusa.
    PERFORM set_config('zeroerp.doc_ritira_legami', '', true);

    RETURN v_legami;
END;
$function$

COMMENT ON FUNCTION vendite.fn_annulla_offerta(p_offerta_id bigint, p_motivazione text, p_legami_confermati integer)
IS 'VERBO d''annullo dell''offerta (brief-modello-documento-vendita §13, O-3 e O-4 di Tid, 2026-10-26). Testata FOR UPDATE nel perimetro (script.fn_scope_ef_whitelist_via_offerta; fuori perimetro E_OFFERTA_NON_TROVATA). Dal BB vendite.fn_documento_ritira_legami: prima cio'' che vieta (script.fn_check_offerta_annullabile: un contratto o un ordine vivo nato dall''offerta, E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI), poi la conferma: chi annulla DICHIARA quanti legami ha visto (p_legami_confermati, le righe di vendite.fn_documento_legami(''OFFERTA_COMMERCIALE'', id): la revisione precedente, superata, che torna emessa); se non corrisponde, E_DOC_ANNULLO_CON_LEGAMI. Poi lo stato d''annullo (dal vocabolario) col verbo di stato vendite.fn_cambia_stato_offerta, con la motivazione (obbligatoria: E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA) e l''azione del passaggio (emetti_offerta sull''annullo dell''accettata); la revisione precedente torna emessa dalla proiezione vendite.fn_offerta_proietta_stato_revisione. Poi la porta del ritiro si chiude. UNA transazione. Ritorna i legami confermati. SECURITY DEFINER con search_path bloccato; EXECUTE solo all''app.';
```

</div>

---
{% include-markdown "signature-core.md" %}
