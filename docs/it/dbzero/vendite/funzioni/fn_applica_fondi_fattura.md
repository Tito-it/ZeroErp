{% include-markdown "it/dbzero/vendite/manual/fn_applica_fondi_fattura.md" %}
# ⚙️ Funzione `fn_applica_fondi_fattura`

```sql
CREATE FUNCTION fn_applica_fondi_fattura(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_fattura_figlia_id bigint, p_tipo_fondo_fattura_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_applica_fondi_fattura(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_fattura_figlia_id bigint, p_tipo_fondo_fattura_id bigint DEFAULT NULL::bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_inserted INTEGER := 0;
BEGIN
    -- Guard: parametri obbligatori
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_billing_account_id', 'valore', p_billing_account_id),
            NULL::uuid, 'p_billing_account_id obbligatorio e > 0');
    END IF;

    IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_utility_id', 'valore', p_utility_id),
            NULL::uuid, 'p_utility_id obbligatorio e > 0');
    END IF;

    IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_doc_fiscale_id', 'valore', p_tipo_doc_fiscale_id),
            NULL::uuid, 'p_tipo_doc_fiscale_id obbligatorio e > 0');
    END IF;

    IF p_emittente_soggetto_ruolo_id IS NULL OR p_emittente_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_soggetto_ruolo_id', 'valore', p_emittente_soggetto_ruolo_id),
            NULL::uuid, 'p_emittente_soggetto_ruolo_id obbligatorio e > 0');
    END IF;

    IF p_valuta_id IS NULL OR p_valuta_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_valuta_id', 'valore', p_valuta_id),
            NULL::uuid, 'p_valuta_id obbligatorio e > 0');
    END IF;

    IF p_fattura_figlia_id IS NULL OR p_fattura_figlia_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_figlia_id', 'valore', p_fattura_figlia_id),
            NULL::uuid, 'p_fattura_figlia_id obbligatorio e > 0');
    END IF;

    IF p_tipo_fondo_fattura_id IS NOT NULL AND p_tipo_fondo_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_fondo_fattura_id', 'valore', p_tipo_fondo_fattura_id),
            NULL::uuid, 'p_tipo_fondo_fattura_id se fornito deve essere > 0');
    END IF;

    -- =========================================================
    -- Applica i fondi: lock delle sole source, update, insert righe.
    -- =========================================================
    WITH src AS (
        SELECT s.*
          FROM vendite.fatture_fondi_fattura_source s
          JOIN vendite.fatture fs ON fs.id = s.fattura_sorgente_id
          JOIN vendite.fatture g  ON g.id  = p_fattura_figlia_id
          -- CAPIENZA, letta UNA volta sola. Prima erano due
          -- chiamate alla stessa funzione VOLATILE sulla stessa
          -- riga (una per il segno, una per il valore assoluto):
          -- due giri su `pagamenti`, e in teoria due numeri
          -- diversi che avrebbero potuto accettare meta'
          -- condizione e rifiutare l'altra.
          CROSS JOIN LATERAL (
              SELECT vendite.fn_saldo_sorgente_fondo(s.fattura_sorgente_id, s.id) AS capienza
          ) cap
         WHERE s.stato = 'DISPONIBILE'
           AND s.fattura_figlia_id IS NULL
           AND s.attivo IS TRUE
           AND (p_tipo_fondo_fattura_id IS NULL OR s.tipo_fondo_fattura_id = p_tipo_fondo_fattura_id)

           -- Sanity check del chiamante: i cinque parametri di
           -- scope descrivono la FIGLIA, e qui si verifica che
           -- sia cosi'. ⚠️ Applicati alla source (com'era prima)
           -- erano ridondanti e potevano far saltare in silenzio
           -- un fondo la cui colonna denormalizzata fosse
           -- rimasta indietro.
           AND g.billing_account_id = p_billing_account_id
           AND g.utility_id IS NOT DISTINCT FROM p_utility_id
           AND g.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
           AND g.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
           AND g.valuta_id = p_valuta_id

           -- LA CHIAVE DI GENERAZIONE, tutti e nove gli elementi.
           -- Forma copiata da fn_get_or_create_fattura_header per
           -- non creare una seconda definizione della stessa
           -- chiave: `=` sui cinque non nullable, IS NOT DISTINCT
           -- FROM sui quattro nullable.
           AND fs.id <> g.id
           AND fs.billing_account_id          = g.billing_account_id
           AND fs.tipo_doc_fiscale_id         = g.tipo_doc_fiscale_id
           AND fs.valuta_id                   = g.valuta_id
           AND fs.emittente_soggetto_ruolo_id = g.emittente_soggetto_ruolo_id
           AND fs.registro_id                 = g.registro_id
           AND fs.reseller_soggetto_ruolo_id  IS NOT DISTINCT FROM g.reseller_soggetto_ruolo_id
           AND fs.utility_id                  IS NOT DISTINCT FROM g.utility_id
           AND fs.termine_pagamento_id        IS NOT DISTINCT FROM g.termine_pagamento_id
           AND fs.modalita_pagamento_id       IS NOT DISTINCT FROM g.modalita_pagamento_id

           -- CAPIENZA. Non e' un ricalcolo del fondo (vietato):
           -- e' il controllo che la sorgente non sia stata pagata
           -- nel frattempo. Se non regge, il fondo NON si applica
           -- e resta dov'e' — e vw_fondi_fattura_da_decidere lo
           -- mostra come NON_PIU_CAPIENTE, con la STESSA regola.
           AND vendite.fn_check_fondo_fattura_capiente(cap.capienza, s.importo)
           FOR UPDATE OF s SKIP LOCKED
    ), upd AS (
        UPDATE vendite.fatture_fondi_fattura_source s
           SET fattura_figlia_id = p_fattura_figlia_id,
               data_assegnazione = now(),
               user_assegnazione = current_user,
               stato = 'ASSEGNATO',
               data_update = now(),
               user_update = current_user
          FROM src
         WHERE s.id = src.id
        RETURNING s.*
    )
    INSERT INTO vendite.fatture_fondi_fattura (
        fattura_id, tipo_fondo_fattura_id, importo,
        riferimento_fattura_id, meta, attivo,
        data_insert, user_insert, data_update, user_update
    )
    SELECT
        p_fattura_figlia_id, u.tipo_fondo_fattura_id, u.importo,
        u.fattura_sorgente_id, u.meta, TRUE,
        now(), current_user, now(), current_user
      FROM upd u;

    GET DIAGNOSTICS v_inserted = ROW_COUNT;

    RETURN v_inserted;
END;
$function$

COMMENT ON FUNCTION vendite.fn_applica_fondi_fattura(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_fattura_figlia_id bigint, p_tipo_fondo_fattura_id bigint)
IS 'Applica i fondi DISPONIBILE alla fattura figlia, crea le righe fondi e marca le source come ASSEGNATO. E'' l''unico punto in cui il fondo MUOVE DENARO, e dal 2026-08-15 porta i due presidi che ne discendono. (1) CHIAVE: sorgente e figlia si confrontano sui NOVE elementi di vendite.fn_build_fattura_key (ne confrontava cinque, sulle colonne denormalizzate della source: mancavano reseller, registro, TERMINE e MODALITA'' di pagamento, quindi un fondo nato da una fattura a 30 giorni poteva finire su una figlia a 60 — due documenti che la chiave tiene separati apposta). Forma copiata da fn_get_or_create_fattura_header per non duplicare la definizione della chiave. I cinque parametri di scope restano ma cambiano mestiere: da filtro sulla source a sanity check sulla FIGLIA, perche'' sulla source potevano far saltare in silenzio un fondo con la colonna denormalizzata rimasta indietro. (2) CAPIENZA: prima di assegnare si RILEGGE il residuo della sorgente al netto del contributo del fondo stesso (fn_saldo_sorgente_fondo) e si verifica con vendite.fn_check_fondo_fattura_capiente che regga ancora l''importo — segno e valore assoluto, non `>=`, perche'' su una sorgente a credito il residuo e'' negativo. E'' la contropartita dell''ANNULLATO automatico rimosso da fn_genera_fondi_fattura_source: non un altro automatismo che scrive, ma una lettura nell''istante in cui il denaro si muove. ⭐ Rev 2026-08-15 (sera): la regola di capienza non e'' piu'' scritta qui ma nel predicato condiviso con vw_fondi_fattura_da_decidere, cosi'' l''elenco non puo'' dichiarare inapplicabile un fondo che il giro applica; e la capienza si calcola UNA volta in LATERAL invece di due volte nel WHERE — erano due giri su `pagamenti` per ogni source, con due valutazioni indipendenti di una funzione VOLATILE che in teoria potevano rispondere in modo diverso al segno e al valore assoluto. D-3(b) + D-4 + coda D-10 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
