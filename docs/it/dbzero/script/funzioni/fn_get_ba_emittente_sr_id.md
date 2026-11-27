{% include-markdown "it/dbzero/script/manual/fn_get_ba_emittente_sr_id.md" %}
# ⚙️ Funzione `fn_get_ba_emittente_sr_id`

```sql
CREATE FUNCTION fn_get_ba_emittente_sr_id(p_billing_account_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_ba_emittente_sr_id(p_billing_account_id bigint)
 RETURNS bigint
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: «quale emittente fattura questo billing account?» —
    --   il soggetto_ruolo dell'emittente, o NULL se non risolvibile.
    --   Regola a TRE livelli dal 20260913-01 (D13): mapping
    --   specifico; altrimenti, IN SESSIONE, l'emittente di chi
    --   sta agendo; altrimenti il default dell'installazione.
    -- ⚠️ Il CASE esterno non e' ridondante. Senza, un BA NULL
    --   cadrebbe nei rami 2 e 3 e si vedrebbe rispondere un
    --   emittente — cioe' «nessun billing account» verrebbe
    --   letto come «billing account non ancora collegato», che e'
    --   una cosa diversa e apre invece di chiudere.
    SELECT CASE
             WHEN p_billing_account_id IS NULL THEN NULL
             ELSE COALESCE(
                    -- 1) Mapping specifico del BA. Al massimo una
                    --    riga: uq_emittenti_fiscali_ba. Vince sempre:
                    --    il COALESCE non valuta i rami dopo.
                    (SELECT efba.emittente_soggetto_ruolo_id
                       FROM anagrafiche.emittenti_fiscali_billing_account efba
                      WHERE efba.billing_account_id = p_billing_account_id),
                    -- 2) Riserva IN SESSIONE: un BA non ancora
                    --    collegato appartiene a chi lo sta creando.
                    --    E' l'istante fra l'INSERT e il trigger AFTER
                    --    z90_link_ef, cioe' il RETURNING: la riserva
                    --    dice cio' che il trigger sta per scrivere,
                    --    con la STESSA funzione che usa lui.
                    -- ⛔ Il CASE e' il guard: fn_resolve_emittente_for_user
                    --    SOLLEVA (e logga) su NULL o <= 0, e senza
                    --    sessione non va chiamata. Un WHERE sulla
                    --    stessa riga non garantirebbe l'ordine.
                    (SELECT ef.soggetto_ruolo_id
                       FROM anagrafiche.emittenti_fiscali ef
                      WHERE ef.id = (SELECT CASE
                                              WHEN s.auth_user_id > 0
                                              THEN script.fn_resolve_emittente_for_user(s.auth_user_id)
                                            END
                                       FROM (SELECT script.fn_utente_di_sessione('script.fn_get_ba_emittente_sr_id')
                                                    AS auth_user_id) s)),
                    -- 3) Riserva SENZA sessione: l'emittente di
                    --    default dell'installazione (batch,
                    --    manutenzione, admin globale senza
                    --    emittente attivo). Al massimo uno:
                    --    uq_emittenti_fiscali_ba_default.
                    (SELECT efba_d.emittente_soggetto_ruolo_id
                       FROM anagrafiche.emittenti_fiscali_billing_account efba_d
                      WHERE efba_d.is_default)
                  )
           END;
$function$

COMMENT ON FUNCTION script.fn_get_ba_emittente_sr_id(p_billing_account_id bigint)
IS 'L''azienda (soggetto_ruolo_id dell''emittente) che fattura un billing account, per chi agisce; NULL se non e'' risolvibile. Tre livelli: 1) il collegamento del billing account in anagrafiche.emittenti_fiscali_billing_account (al massimo uno, uq_emittenti_fiscali_ba), che vince sempre; 2) in sessione, l''azienda di chi agisce, script.fn_resolve_emittente_for_user, la stessa con cui anagrafiche.trgfn_billing_account_link_ef scrive il collegamento; 3) senza sessione, l''azienda predefinita (is_default, al massimo una). Ogni billing account nasce collegato e il collegamento non si toglie: i livelli 2 e 3 rispondono nell''istante della nascita, fra l''INSERT e il trigger AFTER che scrive il collegamento (il RETURNING, che la policy del billing account giudica con questa funzione), e a un id che non e'' un billing account. Non solleva, perche'' la chiamano le policy ef_whitelist del billing account: un id sbagliato lo rifiutano gli involucri per chi scrive, anagrafiche.fn_get_emittente_fiscale_id e anagrafiche.fn_get_emittente_fiscale_pk (E_BILLING_ACCOUNT_NOT_FOUND). Input NULL: NULL, perche'' «nessun billing account» non e'' un billing account da collegare. Non risale l''albero dei billing account: l''omogeneita'' di padre e figli la tiene anagrafiche.fn_guard_albero_ba_emittente. Non applica il perimetro: dice chi fattura, non chi puo'' vedere. La risposta che non guarda chi agisce e'' script.fn_get_ba_emittente_sr_id_installazione. STABLE e non PARALLEL SAFE, perche'' la delegata del livello 2 non lo e''; COST 5000, perche'' legge tabelle ed e'' nominata dalle policy.';
```

</div>

---
{% include-markdown "signature-core.md" %}
