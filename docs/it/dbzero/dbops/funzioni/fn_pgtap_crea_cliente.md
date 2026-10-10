# ⚙️ Funzione `fn_pgtap_crea_cliente`

```sql
CREATE FUNCTION fn_pgtap_crea_cliente(p_etichetta text, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_stato_codice_interno character varying)
```

**Definizione completa:**

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
DECLARE
    v_ba_id       anagrafiche.billing_account.id%TYPE;
    v_ist_id      anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_sr_id       anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_soggetto_id anagrafiche.soggetti.id%TYPE;
    v_utility_id  anagrafiche.billing_account.utility_id%TYPE;
    v_stato_id    config.stati_cliente.id%TYPE;
    v_macro       config.stati_cliente.codice%TYPE;
    v_cliente_id  anagrafiche.clienti.id%TYPE;
    v_oggi        anagrafiche.clienti.data_attivazione%TYPE;
BEGIN
    SELECT sc.id, sc.codice
      INTO v_stato_id, v_macro
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

    -- Le date come le pretende trgfn_clienti_set_periodo: AT vuole
    -- l'attivazione, gli stati CH la chiusura (>= attivazione).
    -- Pre-contratto (IS) e annullato (AN) non hanno attivazione.
    -- ⚠️ Ruolo e istanza dal BA: sono le sue copie (FK composte),
    --   la utility la mette il trigger dal BA.
    INSERT INTO anagrafiche.clienti
        (billing_account_id, istanza_utility_id, soggetto_ruolo_id,
         stato_cliente_id, data_attivazione, data_chiusura)
    VALUES
        (v_ba_id, v_ist_id, v_sr_id, v_stato_id,
         CASE WHEN v_macro IN ('IS', 'AN') THEN NULL ELSE v_oggi END,
         CASE WHEN v_macro = 'CH' THEN v_oggi END);

    -- Senza RETURNING: sotto la RLS si rilegge a istruzione finita.
    SELECT c.id INTO v_cliente_id
      FROM anagrafiche.clienti c
     WHERE c.billing_account_id = v_ba_id;

    IF v_cliente_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_cliente: il cliente del billing account % e'' stato scritto ma non si legge: sotto la RLS serve un operatore dell''emittente del BA in sessione',
            v_ba_id;
    END IF;

    RETURN QUERY
    SELECT v_cliente_id, v_ba_id, v_ist_id, v_sr_id, v_soggetto_id, v_utility_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_cliente(p_etichetta text, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_stato_codice_interno character varying)
IS 'Fixture pgTAP: un cliente COMPLETO, cioe'' dbops.fn_pgtap_crea_cliente_ba (soggetto, ruolo CL, istanza, billing account; stessi primi tre parametri) piu'' la riga di anagrafiche.clienti sul BA appena nato, con ruolo e istanza del BA (la utility la copia il trigger). Stato dal quarto parametro (codice_interno, default AT); le date le pretende trgfn_clienti_set_periodo: attivazione = data operativa salvo pre-contratto e annullato (macro IS, AN), chiusura = data operativa per gli stati di macro CH. Utility di default: la prima che non richiede il PDP. Rende cliente_id e le colonne di fn_pgtap_crea_cliente_ba. Senza RETURNING (rilettura dal BA, uq_clienti_billing_account): usabile come zeroerp_app con un operatore in sessione, stesse regole d''ordine di fn_pgtap_crea_cliente_ba. Nasce il 2026-10-10 (brief-db-codici-non-trovato-email-e-permessi R-9): regola del 2 sulle copie a mano della riga clienti nelle fixture.';
```

---
{% include-markdown "signature-core.md" %}
