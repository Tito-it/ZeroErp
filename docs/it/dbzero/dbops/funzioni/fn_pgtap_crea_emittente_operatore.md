{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_emittente_operatore.md" %}
# ⚙️ Funzione `fn_pgtap_crea_emittente_operatore`

```sql
CREATE FUNCTION fn_pgtap_crea_emittente_operatore(p_sigla character varying, p_processo_codice text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_emittente_operatore(p_sigla character varying DEFAULT NULL::character varying, p_processo_codice text DEFAULT 'chiusura_scadenze_daily'::text)
 RETURNS TABLE(emittente_fiscale_id bigint, emittente_codice character varying, soggetto_ruolo_id bigint, auth_user_id integer, identita_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un'azienda su cui lavorare E
--   l'operatore che la ha nel perimetro, perche' senza operatore
--   il contesto resta vuoto e il dominio solleva «Nessun
--   emittente fiscale attivo».
-- Uso, in testa al file, al posto della sola riga di contesto:
--   DO $ctx$
--   DECLARE v_u integer;
--   BEGIN
--       SELECT auth_user_id INTO v_u
--         FROM dbops.fn_pgtap_crea_emittente_operatore();
--       PERFORM script.fn_pgtap_set_contesto_operatore(v_u);
--   END $ctx$;
DECLARE
    v_ef          record;
    v_auth_user   anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_identita_id anagrafiche.identita_digitali.id%TYPE;
BEGIN
    SELECT * INTO v_ef FROM dbops.fn_pgtap_crea_emittente(p_sigla);

    -- ⛔ DENTRO UNA FINESTRA DIFFERITA, o non parte.
    --   `fn_crea_utente_tecnico` e' una SAGA: scrive il soggetto
    --   del processo e SOLO DOPO il suo contatto. Il guard
    --   `trgfn_soggetti_guard_soggetto_contatti` e' DEFERRABLE
    --   INITIALLY DEFERRED apposta, ma qui i vincoli sono
    --   IMMEDIATE — li mette il preambolo obbligatorio dei pgTAP e
    --   li richiude `fn_pgtap_crea_soggetto_pg` in uscita.
    --   Senza queste due righe si muore su «Il soggetto non ha
    --   contatti validi» al primo INSERT. In produzione non
    --   succede: li' nessuno ha mai messo i vincoli IMMEDIATE.
    SET CONSTRAINTS ALL DEFERRED;

    v_auth_user := script.fn_crea_utente_tecnico(
                       p_processo_codice  := p_processo_codice,
                       p_emittente_codice := v_ef.emittente_codice);

    -- Saga completa: i guard differiti scattano QUI, su un mondo
    -- finito. ⚠️ La richiusura non e' facoltativa: senza, il
    -- ROLLBACK del test se li porterebbe via NON verificati.
    SET CONSTRAINTS ALL IMMEDIATE;

    SELECT idg.id
      INTO v_identita_id
      FROM anagrafiche.identita_digitali idg
     WHERE idg.auth_user_id = v_auth_user
       AND idg.attivo;

    -- ⚠️ Guard sul RISULTATO, non sul parametro: senza identita'
    --   l'operatore non e' selezionabile dal contesto, e
    --   restituire una tupla con un NULL dentro manderebbe il
    --   chiamante a cercare il difetto tre passi piu' in la'.
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

COMMENT ON FUNCTION dbops.fn_pgtap_crea_emittente_operatore(p_sigla character varying, p_processo_codice text)
IS 'Helper di fixture pgTAP: un''azienda su cui lavorare PIU'' l''operatore che la ha nel perimetro. Senza operatore il contesto di sessione resta vuoto e il dominio solleva «Nessun emittente fiscale attivo». ⚠️ L''operatore e'' un utente TECNICO, perche'' script.fn_crea_utente_tecnico e'' l''unico percorso di produzione che lega un utente a un emittente; per cio'' che i test attraversano e'' un operatore a tutti gli effetti (identita'' OPERATORE attiva, non super admin, un emittente nel perimetro). ⛔ Non usarlo dove il soggetto del test e'' l''operatore UMANO (flag tecnica, profili di accesso): li'' il caso va costruito, con dbops.fn_pgtap_crea_operatore_umano. Il chiamante deve poi puntarci il contesto: PERFORM script.fn_pgtap_set_contesto_operatore(auth_user_id). ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.';
```

</div>

---
{% include-markdown "signature-core.md" %}
