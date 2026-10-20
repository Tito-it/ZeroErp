{% include-markdown "it/dbzero/anagrafiche/manual/fn_lookup_utilities_per_ba.md" %}
# ⚙️ Funzione `fn_lookup_utilities_per_ba`

```sql
CREATE FUNCTION fn_lookup_utilities_per_ba(p_billing_account_id bigint, p_ruolo_codice_soggetto text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_lookup_utilities_per_ba(p_billing_account_id bigint, p_ruolo_codice_soggetto text)
 RETURNS TABLE(utility_id bigint, codice text, descrizione text, is_personalizzata_per_ef boolean, minimo_soglia_min numeric, minimo_soglia_max numeric, arrotondamento_importi_dec smallint, metodo_arrotondamento_importi text)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_emittente_pk        anagrafiche.emittenti_fiscali.id%TYPE;
    v_emittente_sr_id     anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_today               date := script.fn_data_operativa();
BEGIN
    -- rev 2026-10-21 (brief-db-modelli-documento-standard §10.3 K-7):
    --   i parametri d'importo sono quelli effettivi, dal BB
    --   anagrafiche.fn_parametri_importo_utility. Prima la riga
    --   dell'emittente in LEFT JOIN: senza riga NULL, e nessun valore di
    --   sistema da cui partire.
    -- rev 2026-06-29 (analisi-hardcoded-codice §3a #15 / §9.5):
    --   ruoli soggetto/EF risolti per codice_interno (immutabile).
    --   In tipi_ruoli codice_interno != codice -> col vecchio `codice`
    --   la funzione ritornava 0 righe.

    -- Guard input
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'fn_lookup_utilities_per_ba',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'detail', 'p_billing_account_id obbligatorio e > 0',
                'billing_account_id', p_billing_account_id
            ),
            NULL::uuid,
            'p_billing_account_id obbligatorio e > 0'
        );
    END IF;

    IF p_ruolo_codice_soggetto IS NULL
       OR length(btrim(p_ruolo_codice_soggetto)) = 0
    THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'fn_lookup_utilities_per_ba',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'detail', 'p_ruolo_codice_soggetto obbligatorio',
                'ruolo_codice_soggetto', p_ruolo_codice_soggetto
            ),
            NULL::uuid,
            'p_ruolo_codice_soggetto obbligatorio'
        );
    END IF;

    -- Risoluzione emittente del BA: catena specifico -> default globale.
    -- Riusa fn_get_emittente_fiscale_pk (solleva E_EMITTENTE_DEFAULT_MISSING
    -- se nessun emittente risolvibile, comportamento desiderato).
    v_emittente_pk := anagrafiche.fn_get_emittente_fiscale_pk(p_billing_account_id);

    -- Conversione PK -> soggetto_ruolo_id (la matrice utility usa SR_ID).
    SELECT ef.soggetto_ruolo_id
      INTO v_emittente_sr_id
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.id = v_emittente_pk;

    -- Query principale: intersezione (ruolo_soggetto AND ruolo EF) +
    -- LEFT JOIN override per i parametri personalizzati per emittente.
    RETURN QUERY
    SELECT
        u.id::bigint                                AS utility_id,
        u.codice::text                              AS codice,
        u.descrizione::text                         AS descrizione,
        par.personalizzata                          AS is_personalizzata_per_ef,
        par.minimo_soglia_min                       AS minimo_soglia_min,
        par.minimo_soglia_max                       AS minimo_soglia_max,
        par.arrotondamento_importi_dec              AS arrotondamento_importi_dec,
        par.metodo_arrotondamento_importi::text     AS metodo_arrotondamento_importi
    FROM config.utilities u
    -- ammessa per il ruolo del soggetto del BA
    JOIN config.utilities_tipi_ruolo utr_sogg
      ON utr_sogg.utility_id = u.id
     AND utr_sogg.attivo = true
     AND (utr_sogg.valido_dal IS NULL OR utr_sogg.valido_dal <= v_today)
     AND (utr_sogg.valido_al  IS NULL OR utr_sogg.valido_al  >= v_today)
    JOIN config.tipi_ruoli tr_sogg
      ON tr_sogg.id = utr_sogg.tipo_ruolo_id
     AND tr_sogg.codice_interno = p_ruolo_codice_soggetto
    -- ammessa per il ruolo EF (emittente fiscale)
    JOIN config.utilities_tipi_ruolo utr_ef
      ON utr_ef.utility_id = u.id
     AND utr_ef.attivo = true
     AND (utr_ef.valido_dal IS NULL OR utr_ef.valido_dal <= v_today)
     AND (utr_ef.valido_al  IS NULL OR utr_ef.valido_al  >= v_today)
    JOIN config.tipi_ruoli tr_ef
      ON tr_ef.id = utr_ef.tipo_ruolo_id
     AND tr_ef.codice_interno = 'EF'
    -- i parametri effettivi (K-7, 20261021-03): la riga dell'emittente
    -- se c'e', se no il valore di sistema dell'utility. Prima un LEFT
    -- JOIN sulla riga dell'emittente: senza riga uscivano NULL.
    CROSS JOIN LATERAL anagrafiche.fn_parametri_importo_utility(v_emittente_sr_id, u.id) par
    ORDER BY u.codice;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_lookup_utilities_per_ba(p_billing_account_id bigint, p_ruolo_codice_soggetto text)
IS 'Utility ammesse per un billing account, guidate da emittente: intersezione ruolo soggetto (p_ruolo_codice_soggetto, codice_interno: CL/FO/GE) AND ruolo EF (codice_interno EF), con override parametri per emittente (LEFT JOIN). rev 2026-06-29: ruoli risolti per codice_interno (analisi-hardcoded-codice §3a #15) - col vecchio codice ritornava 0 righe. rev 2026-10-21 (brief-db-modelli-documento-standard §10.3 K-7): i parametri d''importo sono quelli effettivi di anagrafiche.fn_parametri_importo_utility, la riga dell''emittente se c''e'' e altrimenti il valore di sistema dell''utility; is_personalizzata_per_ef dice se la riga c''e''.';
```

---
{% include-markdown "signature-core.md" %}
