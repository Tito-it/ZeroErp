{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_commessa.md" %}
# ⚙️ Funzione `fn_pgtap_crea_commessa`

```sql
CREATE FUNCTION fn_pgtap_crea_commessa(p_etichetta text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_commessa(p_etichetta text DEFAULT 'pgTAP'::text)
 RETURNS TABLE(commessa_id bigint, commessa_codice character varying, emittente_fiscale_id bigint, emittente_soggetto_ruolo_id bigint, auth_user_id integer, billing_account_id bigint, istanza_utility_id bigint, cliente_soggetto_ruolo_id bigint, utility_id integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP una COMMESSA del mondo in una
--   chiamata: azienda, operatore, cliente e commessa aperta
--   dalla madre del dominio.
-- Uso:
--   CREATE TEMP TABLE tmp_c AS
--   SELECT * FROM dbops.fn_pgtap_crea_commessa('rls commesse');
-- ⛔ Le attivita' NON le scrive: sono il caso del test
--   (dbops.fn_pgtap_crea_commessa_attivita ne da' una).
-- ⚠️ Senza contesto aperto, il mondo lo apre sull'operatore che
--   costruisce. Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_ef_id     anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_sr_id  anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_user_id   anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_ba_id     anagrafiche.billing_account.id%TYPE;
    v_ist_id    anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_cli_sr_id anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_utility   anagrafiche.billing_account.utility_id%TYPE;
    v_commessa  vendite.commesse.id%TYPE;
    v_codice    vendite.commesse.codice%TYPE;
BEGIN
    SELECT m.emittente_fiscale_id, m.emittente_soggetto_ruolo_id,
           m.auth_user_id, m.billing_account_id, m.istanza_utility_id,
           m.cliente_soggetto_ruolo_id, m.utility_id
      INTO v_ef_id, v_ef_sr_id, v_user_id, v_ba_id, v_ist_id,
           v_cli_sr_id, v_utility
      FROM dbops.fn_pgtap_crea_mondo_cliente(p_etichetta) m;

    -- La madre: codice, emittente e stato li decide lei.
    v_commessa := vendite.fn_get_or_create_commessa(
        p_billing_account_id => v_ba_id,
        p_utility_id         => v_utility,
        p_competenza_dal     => date_trunc('month', (SELECT script.fn_data_operativa()))::date,
        p_competenza_al      => (date_trunc('month', (SELECT script.fn_data_operativa()))
                                 + interval '1 month - 1 day')::date,
        p_meta               => jsonb_build_object('test_scope', 'pgtap_' || p_etichetta),
        p_force_new          => true);

    SELECT c.codice INTO v_codice
      FROM vendite.commesse c
     WHERE c.id = v_commessa;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT v_commessa, v_codice, v_ef_id, v_ef_sr_id, v_user_id,
           v_ba_id, v_ist_id, v_cli_sr_id, v_utility;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_commessa(p_etichetta text)
IS 'Fixture pgTAP: una COMMESSA del mondo in una chiamata: azienda, operatore e cliente (dbops.fn_pgtap_crea_mondo_cliente) e la commessa aperta dalla madre vendite.fn_get_or_create_commessa (p_force_new), con competenza nel mese corrente. Codice, emittente e stato iniziale li decide la madre, come in produzione. ⛔ NON scrive attivita'': sono il caso del test (dbops.fn_pgtap_crea_commessa_attivita ne da'' una). ⛔ Non cambia stato: vendite.commesse ha un guard di transizione. ⚠️ Senza contesto aperto lo apre sull''operatore che costruisce; esce con i vincoli IMMEDIATE. Brief: brief-db-fixture-rls-documenti-costruiti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
