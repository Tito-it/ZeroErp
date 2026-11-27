{% include-markdown "it/dbzero/anagrafiche/manual/fn_lookup_utilities_per_ba.md" %}
# ⚙️ Funzione `fn_lookup_utilities_per_ba`

```sql
CREATE FUNCTION fn_lookup_utilities_per_ba(p_billing_account_id bigint, p_ruolo_codice_soggetto text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_lookup_utilities_per_ba(p_billing_account_id bigint, p_ruolo_codice_soggetto text)
 RETURNS TABLE(utility_id bigint, codice text, descrizione text, is_personalizzata_per_ef boolean, minimo_soglia_min numeric, minimo_soglia_max numeric, arrotondamento_importi_dec smallint, metodo_arrotondamento_importi text)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_emittente_pk        anagrafiche.emittenti_fiscali.id%TYPE;
    v_emittente_sr_id     anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_ruolo_ba            config.tipi_ruoli.codice_interno%TYPE;
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

    -- Il BA esiste (ed e' nel perimetro di chi chiama: la funzione e'
    -- INVOKER), e il ruolo chiesto e' il suo. Un id che non e' un BA
    -- ricadeva sulla predefinita e rispondeva; un ruolo diverso dava le
    -- utility di un altro ruolo.
    SELECT tr.codice_interno
      INTO v_ruolo_ba
      FROM anagrafiche.billing_account ba
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
      JOIN config.tipi_ruoli tr          ON tr.id = sr.tipo_ruolo_id
     WHERE ba.id = p_billing_account_id;

    -- Un id ben formato senza billing account: la cosa indicata non
    -- esiste (NON_TROVATO), non e' un parametro malformato.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'fn_lookup_utilities_per_ba',
            'E_BILLING_ACCOUNT_NOT_FOUND',
            jsonb_build_object(
                'detail', 'p_billing_account_id non e'' un billing account',
                'billing_account_id', p_billing_account_id
            ),
            NULL::uuid,
            p_billing_account_id::text
        );
    END IF;

    IF v_ruolo_ba IS DISTINCT FROM p_ruolo_codice_soggetto THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'fn_lookup_utilities_per_ba',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'detail', 'p_ruolo_codice_soggetto non e'' il ruolo del billing account',
                'billing_account_id', p_billing_account_id,
                'ruolo_codice_soggetto', p_ruolo_codice_soggetto,
                'ruolo_del_billing_account', v_ruolo_ba
            ),
            NULL::uuid,
            'p_ruolo_codice_soggetto non e'' il ruolo del billing account'
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

    -- Le utility che l'azienda del BA gestisce, ammesse per il ruolo
    -- del soggetto: la regola sta nel building block
    -- anagrafiche.fn_utilities_emittente (D-U-2: un'utility che
    -- l'azienda non gestisce non si propone).
    RETURN QUERY
    SELECT
        a.utility_id::bigint                        AS utility_id,
        a.codice::text                              AS codice,
        a.descrizione::text                         AS descrizione,
        a.personalizzata                            AS is_personalizzata_per_ef,
        a.minimo_soglia_min                         AS minimo_soglia_min,
        a.minimo_soglia_max                         AS minimo_soglia_max,
        a.arrotondamento_importi_dec                AS arrotondamento_importi_dec,
        a.metodo_arrotondamento_importi::text       AS metodo_arrotondamento_importi
      FROM anagrafiche.fn_utilities_emittente(v_emittente_sr_id, p_ruolo_codice_soggetto) a
     WHERE a.gestita
     ORDER BY a.codice;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_lookup_utilities_per_ba(p_billing_account_id bigint, p_ruolo_codice_soggetto text)
IS 'Le utility proponibili per un billing account: quelle che l''azienda del billing account gestisce, ammesse per il ruolo del soggetto (p_ruolo_codice_soggetto, per codice_interno: CL, FO, GE), coi parametri d''importo effettivi dell''azienda. La regola e'' di anagrafiche.fn_utilities_emittente (le righe gestite). Il billing account deve esistere ed essere nel perimetro di chi chiama, altrimenti E_BILLING_ACCOUNT_NOT_FOUND; il ruolo deve essere il suo, altrimenti E_PARAMETRO_INVALIDO, come per un parametro mancante. Ruoli e validita'' si leggono al giorno operativo. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
