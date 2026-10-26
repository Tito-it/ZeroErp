{% include-markdown "it/dbzero/vendite/manual/fn_genera_fondi_fattura_source.md" %}
# ⚙️ Funzione `fn_genera_fondi_fattura_source`

```sql
CREATE FUNCTION fn_genera_fondi_fattura_source(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_tipo_fondo_fattura_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_genera_fondi_fattura_source(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_tipo_fondo_fattura_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_inserted INTEGER := 0;
BEGIN
    -- Guard: tutti i parametri obbligatori e > 0
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_genera_fondi_fattura_source', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_billing_account_id', 'valore', p_billing_account_id), NULL::uuid, 'p_billing_account_id obbligatorio e > 0');
    END IF;
    IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_genera_fondi_fattura_source', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_utility_id', 'valore', p_utility_id), NULL::uuid, 'p_utility_id obbligatorio e > 0');
    END IF;
    IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_genera_fondi_fattura_source', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_doc_fiscale_id', 'valore', p_tipo_doc_fiscale_id), NULL::uuid, 'p_tipo_doc_fiscale_id obbligatorio e > 0');
    END IF;
    IF p_emittente_soggetto_ruolo_id IS NULL OR p_emittente_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_genera_fondi_fattura_source', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_soggetto_ruolo_id', 'valore', p_emittente_soggetto_ruolo_id), NULL::uuid, 'p_emittente_soggetto_ruolo_id obbligatorio e > 0');
    END IF;
    IF p_valuta_id IS NULL OR p_valuta_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_genera_fondi_fattura_source', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_valuta_id', 'valore', p_valuta_id), NULL::uuid, 'p_valuta_id obbligatorio e > 0');
    END IF;
    IF p_tipo_fondo_fattura_id IS NULL OR p_tipo_fondo_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_genera_fondi_fattura_source', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_fondo_fattura_id', 'valore', p_tipo_fondo_fattura_id), NULL::uuid, 'p_tipo_fondo_fattura_id obbligatorio e > 0');
    END IF;

    -- =========================================================
    -- CREAZIONE, e SOLO creazione.
    --
    -- Il fondo di una fattura DEFINITIVA e' un atto: si scrive
    -- una volta con l'importo letto in quel momento e non si
    -- ricalcola. Non c'e' un ramo di aggiornamento.
    --
    -- ⭐ E l'inviluppo NON e' scritto qui: lo dice
    -- fn_fondo_fattura_proponibile, che e' anche cio' che
    -- l'elenco «da decidere» mostra all'operatore. Una sola
    -- definizione, due lettori — altrimenti l'elenco e il giro
    -- notturno finirebbero per raccontare due cose diverse.
    --
    -- Restano qui i CINQUE FILTRI DI SCOPE: dicono quali
    -- fatture guarda questa chiamata, non se una fattura
    -- meriti un fondo.
    -- =========================================================
    WITH base AS (
        SELECT f.id AS fattura_sorgente_id,
               p.importo_proposto
          FROM vendite.fatture f
          CROSS JOIN LATERAL (
              SELECT vendite.fn_fondo_fattura_proponibile(f.id, p_tipo_fondo_fattura_id)
                     AS importo_proposto
          ) p
         WHERE f.billing_account_id = p_billing_account_id
           -- ⭐ utility nel FILTRO, non solo in scrittura: senza,
           --    su un BA con due utility la stessa riga veniva
           --    rimarcata a ogni giro e l'attribuzione del fondo
           --    dipendeva dall'ordine. `=` e non IS NOT DISTINCT
           --    FROM: una fattura senza utility e' un dato
           --    incompleto (BASE e' una utility vera), e
           --    un'attribuzione non si indovina. Quel caso lo
           --    mostra vw_fondi_fattura_da_decidere.
           AND f.utility_id                  = p_utility_id
           AND f.tipo_doc_fiscale_id         = p_tipo_doc_fiscale_id
           AND f.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
           AND f.valuta_id                   = p_valuta_id
           -- NULL = l'automatismo non farebbe niente su questa
           -- fattura. Il perche' sta tutto nella funzione.
           AND p.importo_proposto IS NOT NULL
    ), ins AS (
        INSERT INTO vendite.fatture_fondi_fattura_source (
            fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato, origine,
            fattura_figlia_id, data_assegnazione, user_assegnazione,
            billing_account_id, utility_id, tipo_doc_fiscale_id,
            emittente_soggetto_ruolo_id, valuta_id, meta, attivo,
            data_insert, user_insert, data_update, user_update
        )
        SELECT b.fattura_sorgente_id, p_tipo_fondo_fattura_id, b.importo_proposto,
               'DISPONIBILE', 'AUTOMATICA', NULL, NULL, NULL,
               p_billing_account_id, p_utility_id, p_tipo_doc_fiscale_id,
               p_emittente_soggetto_ruolo_id, p_valuta_id, '{}'::jsonb, TRUE,
               now(), current_user, now(), current_user
          FROM base b
        RETURNING id
    )
    SELECT COUNT(*)::INTEGER INTO v_inserted FROM ins;

    RETURN COALESCE(v_inserted, 0);
END;
$function$

COMMENT ON FUNCTION vendite.fn_genera_fondi_fattura_source(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_tipo_fondo_fattura_id bigint)
IS 'Crea le source dei fondi fattura per le fatture del perimetro indicato. E'' CREATE-ONLY dal 2026-08-15: il ramo UPDATE (che riallineava importo e stato a ogni giro) e'' stato rimosso, perche'' il fondo di una fattura DEFINITIVA e'' un atto e non si ricalcola — «una volta che la fattura e'' effettiva il fondo rimane lo stesso». ⭐ Dal 2026-08-15 (sera) l''INVILUPPO non e'' piu'' scritto qui: DEFINITIVA, di minimo, utility attribuita, atto unico, importo non nullo e CORRISPONDENZA col documento sono tutti dentro vendite.fn_fondo_fattura_proponibile, che questa funzione chiama in LATERAL e di cui inserisce il risultato. La ragione e'' che lo stesso inviluppo serve all''elenco vw_fondi_fattura_da_decidere: due copie della regola darebbero prima o poi due risposte diverse, e il divario si vedrebbe come un elenco che propone cio'' che il giro notturno non crea. Restano qui i CINQUE FILTRI DI SCOPE (billing account, utility, tipo doc fiscale, emittente, valuta), che dicono quali fatture guardare e non se una fattura meriti un fondo. ⚠️ Nessun pre-filtro su minimo: sarebbe un pezzo di regola in un secondo posto, e lo scope riduce gia'' i candidati a una manciata. Firma invariata di proposito: la chiave piena a nove elementi e la madre DB per lotto richiedono il backend, e sono scritte come richiesta nel brief. D-1 + D-4 + coda D-9 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
