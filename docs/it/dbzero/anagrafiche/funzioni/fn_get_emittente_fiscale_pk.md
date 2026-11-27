{% include-markdown "it/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_pk.md" %}
# ⚙️ Funzione `fn_get_emittente_fiscale_pk`

```sql
CREATE FUNCTION fn_get_emittente_fiscale_pk(p_billing_account_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_emittente_fiscale_pk(p_billing_account_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la PK reale (anagrafiche.emittenti_fiscali.id) dell'emittente
--   che fattura un billing account, per chi SCRIVE: solleva se non
--   e' risolvibile. E' l'involucro PK del lettore
--   script.fn_get_ba_emittente_sr_id, come
--   anagrafiche.fn_get_emittente_fiscale_id ne e' l'involucro SR.
-- ⛔ La regola «quale emittente» NON e' scritta qui: una copia
--   accanto al lettore risponderebbe cose diverse sullo stesso
--   billing account alla prima modifica di uno dei due.
DECLARE
    v_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    -- Guard sul parametro: invariato (codice, frase, contesto).
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'fn_get_emittente_fiscale_pk',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'detail', 'p_billing_account_id obbligatorio e > 0',
                'billing_account_id', p_billing_account_id
            ),
            NULL::uuid,
            'p_billing_account_id obbligatorio e > 0'
        );
    END IF;

    -- ⛔ UN ID CHE NON E' UN BILLING ACCOUNT SI RIFIUTA.
    --   Ogni billing account ha il suo collegamento: i livelli di
    --   riserva del lettore (l'azienda di chi agisce, la
    --   predefinita) risponderebbero solo a un id sbagliato del
    --   chiamante. Il controllo e' SECURITY DEFINER: un BA fuori
    --   dal perimetro di chi chiama esiste, e risponde la sua
    --   azienda.
    IF NOT anagrafiche.fn_check_billing_account_esiste(p_billing_account_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'fn_get_emittente_fiscale_pk',
            'E_BILLING_ACCOUNT_NOT_FOUND',
            jsonb_build_object(
                'detail', 'p_billing_account_id non e'' un billing account',
                'billing_account_id', p_billing_account_id
            ),
            NULL::uuid,
            p_billing_account_id::text
        );
    END IF;

    -- Traduzione soggetto_ruolo -> PK reale. Il filtro ef.attivo
    -- c'era gia' e resta come DIFESA: sul modello un emittente con
    -- una riga di mapping non si puo' disattivare
    -- (trgfn_prevent_deactivate_if_children), quindi il ramo non e'
    -- raggiungibile — se lo fosse, «non risolto» e' la risposta
    -- giusta, non un ripiego silenzioso su un'altra azienda.
    SELECT ef.id
      INTO v_emittente_fiscale_id
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.soggetto_ruolo_id
               = script.fn_get_ba_emittente_sr_id(p_billing_account_id)
       AND ef.attivo = true;

    -- Nessuna azienda: e' l'installazione che manca di un
    -- emittente, non il chiamante. Invariato.
    IF v_emittente_fiscale_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'fn_get_emittente_fiscale_pk',
            'E_EMITTENTE_DEFAULT_MISSING',
            jsonb_build_object(
                'detail', 'Emittente fiscale di default mancante o disattivato',
                'billing_account_id', p_billing_account_id
            ),
            NULL::uuid,
            concat('Emittente fiscale di default mancante per billing_account_id ',
                   p_billing_account_id::text)
        );
    END IF;

    RETURN v_emittente_fiscale_id;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_get_emittente_fiscale_pk(p_billing_account_id bigint)
IS 'La PK reale (anagrafiche.emittenti_fiscali.id) dell''azienda che fattura un billing account, per chi SCRIVE: solleva se non e'' risolvibile. E'' l''involucro PK di script.fn_get_ba_emittente_sr_id, come anagrafiche.fn_get_emittente_fiscale_id ne e'' l''involucro SR: la regola «quale emittente» e'' del lettore, il collegamento del billing account, e qui non si riscrive. Rifiuta NULL e un id <= 0 (E_PARAMETRO_INVALIDO) e un id che non e'' un billing account (E_BILLING_ACCOUNT_NOT_FOUND, con anagrafiche.fn_check_billing_account_esiste, che vede anche i billing account fuori dal perimetro di chi chiama). Traduce il ruolo dell''azienda nella PK con il filtro ef.attivo, una difesa: un''azienda collegata a un billing account non si spegne. Senza azienda solleva E_EMITTENTE_DEFAULT_MISSING. Consumatori: script.trgfn_doc_guard_emittente_ba (i documenti di vendita), vendite.trgfn_ddt_normalize, vendite.trgfn_resi_normalize, anagrafiche.fn_lookup_utilities_per_ba, vendite.fn_genera_pratica_da_preventivo, il backend. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
