{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_azienda_di_chi_agisce.md" %}
# ⚙️ Funzione `fn_pgtap_azienda_di_chi_agisce`

```sql
CREATE FUNCTION fn_pgtap_azienda_di_chi_agisce(p_chiamante text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_azienda_di_chi_agisce(p_chiamante text DEFAULT 'dbops.fn_pgtap_azienda_di_chi_agisce'::text)
 RETURNS TABLE(emittente_fiscale_id bigint, emittente_codice character varying, emittente_soggetto_ruolo_id bigint, auth_user_id integer, identita_id bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: l'azienda su cui una fixture scrive quando un contesto
--   e' gia' aperto: quella di CHI AGISCE, con la regola di
--   produzione. Estratta dal «ramo B» di
--   dbops.fn_pgtap_crea_mondo_cliente (rev 20261024-37).
DECLARE
    v_user_id   anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_identita  anagrafiche.identita_digitali.id%TYPE;
    v_ef_id     anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_codice anagrafiche.emittenti_fiscali.codice%TYPE;
    v_ef_sr_id  anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
BEGIN
    -- La domanda e' «c'e' un contesto?», alla GUC che le policy
    -- leggono davvero.
    v_user_id := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION
            '%: nessun contesto aperto (app.current_user_id): l''azienda di chi agisce non c''e''. Si costruisce prima il mondo (dbops.fn_pgtap_crea_mondo_cliente) o si apre il contesto (script.fn_pgtap_set_contesto_operatore)',
            p_chiamante;
    END IF;

    -- ⭐ L'azienda di chi agisce con la regola di produzione: l'emittente
    --   scelto in alto (app.current_emittente_id) se l'utente lo puo'
    --   usare, altrimenti la sua riga in config.user_emittenti_fiscali.
    --   E' la stessa domanda che fa il trigger z90 quando lega il BA.
    SELECT ef.id, ef.codice, ef.soggetto_ruolo_id
      INTO v_ef_id, v_ef_codice, v_ef_sr_id
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.id = script.fn_resolve_emittente_for_user(v_user_id);
    -- ⚠️ Guard sul RISULTATO: un operatore senza riga in
    --   user_emittenti_fiscali e' fail-closed dal 2026-08-18 (P-2a);
    --   un super admin non ha azienda finche' non ne sceglie una.
    IF v_ef_id IS NULL THEN
        RAISE EXCEPTION
            '%: l''utente di contesto (auth_user_id = %) non ha un''azienda su cui scrivere: ne'' una riga in config.user_emittenti_fiscali ne'' un emittente scelto (app.current_emittente_id, per il super admin). Aprire il contesto senza argomento (script.fn_pgtap_set_contesto_operatore()), scegliere l''emittente, o costruire il mondo PRIMA del contesto',
            p_chiamante, v_user_id;
    END IF;

    -- Una sola riga per costruzione: uq_identita_digitali_auth_user_ruolo_attivo
    -- e' UNIQUE su (auth_user_id, ruolo_applicativo) WHERE attivo.
    SELECT idg.id
      INTO v_identita
      FROM anagrafiche.identita_digitali idg
     WHERE idg.auth_user_id = v_user_id
       AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
       AND idg.attivo;
    IF v_identita IS NULL THEN
        RAISE EXCEPTION
            '%: nessuna identita'' OPERATORE attiva per auth_user_id = %: il contesto e'' aperto su un utente che l''applicazione non farebbe entrare',
            p_chiamante, v_user_id;
    END IF;

    RETURN QUERY
    SELECT v_ef_id, v_ef_codice, v_ef_sr_id, v_user_id, v_identita;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_azienda_di_chi_agisce(p_chiamante text)
IS 'Fixture pgTAP (building block): l''azienda del contesto aperto — emittente (id, codice, soggetto_ruolo) e operatore (auth_user_id, identita) — risolta con la regola di produzione script.fn_resolve_emittente_for_user, la stessa del trigger z90 che lega il billing account. Estratta dal «ramo B» di dbops.fn_pgtap_crea_mondo_cliente; la usano il mondo e dbops.fn_pgtap_cliente_del_builder. Solleva, nominando il chiamante (p_chiamante), senza contesto, senza azienda o senza identita'' OPERATORE attiva. STABLE: non scrive. Brief: brief-modello-documento-vendita (§4-octies), 2026-10-24.';
```

</div>

---
{% include-markdown "signature-core.md" %}
