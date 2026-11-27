{% include-markdown "it/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_id.md" %}
# ⚙️ Funzione `fn_get_emittente_fiscale_id`

```sql
CREATE FUNCTION fn_get_emittente_fiscale_id(p_billing_account_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: «quale emittente fattura questo billing account»,
--   per lo SCRITTORE. Restituisce il soggetto_ruolo_id
--   dell'emittente e SOLLEVA se non e' risolvibile.
-- La regola «quale emittente» vive in
--   script.fn_get_ba_emittente_sr_id: qui restano il rifiuto
--   dell'id sbagliato e il punto in cui un NULL diventa un
--   errore di dominio, perche' questa e' la funzione che
--   vendite.fn_build_fattura_key usa per scegliere il REGISTRO
--   su cui numerare, e li' un NULL vorrebbe dire «numera dove
--   capita».
DECLARE
  v_emittente_id anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE;
BEGIN
  -- ⛔ UN ID CHE NON E' UN BILLING ACCOUNT SI RIFIUTA.
  --   Ogni billing account ha il suo collegamento: i livelli di
  --   riserva del lettore (l'azienda di chi agisce, la
  --   predefinita) risponderebbero solo a un id sbagliato del
  --   chiamante, e ne farebbero un'azienda. Il controllo e'
  --   SECURITY DEFINER: un BA fuori dal perimetro di chi chiama
  --   esiste, e risponde la sua azienda.
  --   NULL non e' un id sbagliato: e' «nessun billing account»,
  --   e scende al ripiego qui sotto.
  IF p_billing_account_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'anagrafiche',
      'fn_get_emittente_fiscale_id',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object(
        'detail', 'p_billing_account_id deve essere > 0',
        'billing_account_id', p_billing_account_id
      ),
      NULL::uuid,
      'p_billing_account_id deve essere > 0'
    );
  END IF;

  IF NOT anagrafiche.fn_check_billing_account_esiste(p_billing_account_id) THEN
    PERFORM script.fn_log_and_raise_error(
      'anagrafiche',
      'fn_get_emittente_fiscale_id',
      'E_BILLING_ACCOUNT_NOT_FOUND',
      jsonb_build_object(
        'detail', 'p_billing_account_id non e'' un billing account',
        'billing_account_id', p_billing_account_id
      ),
      NULL::uuid,
      p_billing_account_id::text
    );
  END IF;

  v_emittente_id := script.fn_get_ba_emittente_sr_id(p_billing_account_id);

  -- ⚠️ IL RIPIEGO SENZA BILLING ACCOUNT, e perche' sta qui.
  --   La delegata corto-circuita sull'input NULL
  --   (`WHEN p_billing_account_id IS NULL THEN NULL`) e non
  --   arriva mai al default.
  --   ⭐ Il ripiego e' PORTANTE: vendite.fn_get_or_create_lotto,
  --   attraverso vendite.fn_resolve_lotto_utility_emittente,
  --   chiama senza billing account — un lotto non ne ha uno,
  --   raccoglie fatture di BA diversi — e senza questo ripiego
  --   prende E_EMITTENTE_DEFAULT_MISSING su un giro legittimo.
  --   Con un billing account il ramo non scatta: il lettore
  --   risponde col suo collegamento.
  --   ⛔ NON si toglie il corto-circuito alla delegata: i suoi
  --   lettori (le policy del billing account) si aspettano NULL
  --   da un input nullo.
  IF v_emittente_id IS NULL THEN
    SELECT m.emittente_soggetto_ruolo_id
      INTO v_emittente_id
      FROM anagrafiche.emittenti_fiscali_billing_account m
     WHERE m.is_default IS TRUE;
  END IF;

  IF v_emittente_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'anagrafiche',
      'fn_get_emittente_fiscale_id',
      'E_EMITTENTE_DEFAULT_MISSING',
      jsonb_build_object(
        'detail', 'Emittente fiscale di default mancante',
        'billing_account_id', p_billing_account_id
      ),
      NULL::uuid,
      concat('Emittente fiscale di default mancante ',
        'billing_account_id ', p_billing_account_id::text)
    );
  END IF;

  RETURN v_emittente_id;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id bigint)
IS 'L''azienda che fattura un billing account, per chi SCRIVE: restituisce il soggetto_ruolo_id dell''emittente e solleva se non e'' risolvibile. La regola «quale emittente» e'' di script.fn_get_ba_emittente_sr_id, il collegamento del billing account in anagrafiche.emittenti_fiscali_billing_account; qui un''azienda non risolta diventa un errore di dominio, perche'' vendite.fn_build_fattura_key la usa per scegliere il registro su cui numerare. Rifiuta un id <= 0 (E_PARAMETRO_INVALIDO) e un id che non e'' un billing account (E_BILLING_ACCOUNT_NOT_FOUND, con anagrafiche.fn_check_billing_account_esiste, che vede anche i billing account fuori dal perimetro di chi chiama). Senza billing account (NULL) risponde l''azienda predefinita: e'' il giro del lotto, che non ha un billing account (vendite.fn_get_or_create_lotto, attraverso vendite.fn_resolve_lotto_utility_emittente), e il lettore su NULL risponde NULL. Senza un''azienda predefinita solleva E_EMITTENTE_DEFAULT_MISSING. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
