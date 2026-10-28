# ⚙️ Funzione `fn_pgtap_crea_cliente`

```sql
CREATE FUNCTION fn_pgtap_crea_cliente(p_etichetta text, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_stato_codice_interno character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_cliente(p_etichetta text DEFAULT 'pgTAP'::text, p_utility_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_stato_codice_interno character varying DEFAULT 'AT'::character varying)
 RETURNS TABLE(cliente_id bigint, billing_account_id bigint, istanza_utility_id bigint, soggetto_ruolo_id bigint, soggetto_id uuid, utility_id integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un cliente COMPLETO, fino alla
--   riga di anagrafiche.clienti, con uno stato ammesso e le date
--   che quello stato pretende.
-- Uso:
--   CREATE TEMP TABLE tmp_cli AS
--   SELECT * FROM dbops.fn_pgtap_crea_cliente('RICERCA');
-- ⭐ Rev 20261018-38: la riga la scrive la madre
--   anagrafiche.fn_crea_cliente, sul BA della catena (regola del 2).
DECLARE
    v_ba_id       anagrafiche.billing_account.id%TYPE;
    v_ist_id      anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_sr_id       anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_soggetto_id anagrafiche.soggetti.id%TYPE;
    v_utility_id  anagrafiche.billing_account.utility_id%TYPE;
    v_stato_id    config.stati_cliente.id%TYPE;
    v_cliente_id  anagrafiche.clienti.id%TYPE;
    v_oggi        anagrafiche.clienti.data_attivazione%TYPE;
BEGIN
    SELECT sc.id
      INTO v_stato_id
      FROM config.stati_cliente sc
     WHERE sc.codice_interno = p_stato_codice_interno;

    IF v_stato_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_cliente: stato cliente % non a catalogo', p_stato_codice_interno;
    END IF;

    SELECT c.billing_account_id, c.istanza_utility_id, c.soggetto_ruolo_id,
           c.soggetto_id, c.utility_id
      INTO v_ba_id, v_ist_id, v_sr_id, v_soggetto_id, v_utility_id
      FROM dbops.fn_pgtap_crea_cliente_ba(
               p_etichetta,
               COALESCE(p_utility_id,
                        (SELECT u.id FROM config.utilities u
                          WHERE NOT u.richiede_pdp
                          ORDER BY u.id LIMIT 1)),
               p_emittente_soggetto_ruolo_id) c;

    v_oggi := script.fn_data_operativa();

    -- Le date come le pretende anagrafiche.trgfn_clienti_guard_stato_date
    -- (rev 2026-10-14): attivazione per attivi, sospesi e chiusi;
    -- sospensione per SF/SC; chiusura per i chiusi. PR, AN, AG
    -- senza date. Per codice_interno, non per l'etichetta `codice`.
    -- Ruolo e istanza li prende la madre dal BA.
    SELECT c.cliente_id
      INTO v_cliente_id
      FROM anagrafiche.fn_crea_cliente(
               p_soggetto_id        := v_soggetto_id,
               p_campi              := jsonb_build_object(
                   'stato_cliente_id', v_stato_id,
                   'data_attivazione',
                       CASE WHEN p_stato_codice_interno IN ('AT', 'RS', 'SF', 'SC', 'CH', 'CM', 'CW', 'CF')
                            THEN v_oggi END,
                   'data_sospensione',
                       CASE WHEN p_stato_codice_interno IN ('SF', 'SC') THEN v_oggi END,
                   'data_chiusura',
                       CASE WHEN p_stato_codice_interno IN ('CH', 'CM', 'CW', 'CF') THEN v_oggi END),
               p_billing_account_id := v_ba_id,
               p_istanza_utility_id := v_ist_id) c;

    RETURN QUERY
    SELECT v_cliente_id, v_ba_id, v_ist_id, v_sr_id, v_soggetto_id, v_utility_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_cliente(p_etichetta text, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_stato_codice_interno character varying)
IS 'Fixture pgTAP: un cliente COMPLETO, cioe'' dbops.fn_pgtap_crea_cliente_ba (soggetto, ruolo CL, istanza, billing account; stessi primi tre parametri) piu'' la riga di anagrafiche.clienti sul BA appena nato. Rev 20261018-38: la riga la scrive la madre anagrafiche.fn_crea_cliente (regola del 2, brief-db-processi-accensione-per-ambiente 2b-1 lotto 5), che la rilegge a istruzione finita. Stato dal quarto parametro (codice_interno, default AT) e le date che quello stato pretende (trgfn_clienti_guard_stato_date), decise qui: attivazione = data operativa per attivi, sospesi e chiusi; sospensione per SF/SC; chiusura per i chiusi. Utility di default: la prima che non richiede il PDP. Rende cliente_id e le colonne di fn_pgtap_crea_cliente_ba. Usabile come zeroerp_app con un operatore dell''emittente del BA in sessione; altrimenti la rilettura risponde E_SCRIPT_CHIAMATA_NON_VALIDA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
