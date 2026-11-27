{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_emittente_operatore.md" %}
# ⚙️ Funzione `fn_pgtap_crea_emittente_operatore`

```sql
CREATE FUNCTION fn_pgtap_crea_emittente_operatore(p_sigla character varying, p_processo_codice text, p_persona boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_emittente_operatore(p_sigla character varying DEFAULT NULL::character varying, p_processo_codice text DEFAULT 'chiusura_scadenze_daily'::text, p_persona boolean DEFAULT false)
 RETURNS TABLE(emittente_fiscale_id bigint, emittente_codice character varying, soggetto_ruolo_id bigint, auth_user_id integer, identita_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ef          record;
    v_auth_user   anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_identita_id anagrafiche.identita_digitali.id%TYPE;
BEGIN
    SELECT * INTO v_ef FROM dbops.fn_pgtap_crea_emittente(p_sigla);

    IF p_persona THEN
        -- Una persona: l'operatore umano dal percorso di
        -- produzione, poi l'azienda nel suo perimetro.
        SELECT ou.auth_user_id, ou.identita_id
          INTO v_auth_user, v_identita_id
          FROM dbops.fn_pgtap_crea_operatore_umano(
                   'pgTAP-' || v_ef.emittente_codice, false) ou;
        PERFORM dbops.fn_pgtap_sposta_scope_operatore(
                    v_auth_user, v_ef.emittente_fiscale_id);
        PERFORM config.fn_imposta_emittente_attivo(
                    v_auth_user, v_ef.emittente_fiscale_id);
    ELSE
        SET CONSTRAINTS ALL DEFERRED;

        v_auth_user := dbops.fn_pgtap_fixture_crea_utente_tecnico(
                           p_processo_codice  := p_processo_codice,
                           p_emittente_codice := v_ef.emittente_codice);

        SET CONSTRAINTS ALL IMMEDIATE;

        SELECT idg.id
          INTO v_identita_id
          FROM anagrafiche.identita_digitali idg
         WHERE idg.auth_user_id = v_auth_user
           AND idg.attivo;
    END IF;

    IF v_identita_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_emittente_operatore: nessuna identita'' attiva per auth_user_id=%',
            v_auth_user;
    END IF;

    RETURN QUERY
    SELECT v_ef.emittente_fiscale_id, v_ef.emittente_codice,
           v_ef.soggetto_ruolo_id, v_auth_user, v_identita_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_emittente_operatore(p_sigla character varying, p_processo_codice text, p_persona boolean)
IS 'Helper di fixture pgTAP: un''azienda su cui lavorare PIU'' l''operatore che la ha nel perimetro. Senza operatore il contesto di sessione resta vuoto e il dominio solleva «Nessun emittente fiscale attivo». Di default l''operatore e'' un utente TECNICO (dbops.fn_pgtap_fixture_crea_utente_tecnico, con le regole del verbo script.fn_crea_utente_tecnico, col processo p_processo_codice): per cio'' che i test attraversano e'' un operatore a tutti gli effetti (identita'' OPERATORE attiva, non super admin, un emittente nel perimetro). Con p_persona l''operatore e'' una PERSONA (dbops.fn_pgtap_crea_operatore_umano, non super admin), portata sull''azienda da dbops.fn_pgtap_sposta_scope_operatore (il verbo script.fn_change_user_emittenti_scope, con un SUPER_ADMIN di fixture) e con l''azienda come emittente attivo: serve dove il test fa dell''operatore un SUPER_ADMIN o gli lega un profilo, perche'' un''identita'' tecnica non ha mai il SUPER_ADMIN. Il chiamante deve poi puntarci il contesto: PERFORM script.fn_pgtap_set_contesto_operatore(auth_user_id). ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.';
```

</div>

---
{% include-markdown "signature-core.md" %}
