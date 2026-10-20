{% include-markdown "it/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_id.md" %}
# ⚙️ Funzione `fn_get_emittente_fiscale_id`

```sql
CREATE FUNCTION fn_get_emittente_fiscale_id(p_billing_account_id bigint)
```

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
-- La regola «mapping specifico, poi is_default» vive in
--   script.fn_get_ba_emittente_sr_id dal 2026-08-19 (P-6/5b):
--   qui resta il punto in cui un NULL diventa un errore di
--   dominio, perche' questa e' la funzione che
--   vendite.fn_build_fattura_key usa per scegliere il REGISTRO
--   su cui numerare, e li' un NULL vorrebbe dire «numera dove
--   capita».
DECLARE
  v_emittente_id anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE;
BEGIN
  v_emittente_id := script.fn_get_ba_emittente_sr_id(p_billing_account_id);

  -- ⚠️ IL RIPIEGO SENZA BILLING ACCOUNT, e perche' sta qui.
  --   La delegata corto-circuita sull'input NULL
  --   (`WHEN p_billing_account_id IS NULL THEN NULL`) e non
  --   arriva mai al default. La versione storica di questa
  --   funzione invece ci arrivava, e non per disegno: il suo
  --   `WHERE billing_account_id = NULL` non trovava nulla e la
  --   SELECT sul default rispondeva lo stesso.
  --   ⭐ Comportamento nato per caso, ma PORTANTE:
  --   vendite.fn_get_or_create_lotto chiama senza billing
  --   account — un lotto non ne ha uno, raccoglie fatture di BA
  --   diversi — e senza questo ripiego prende
  --   E_EMITTENTE_DEFAULT_MISSING su un giro legittimo.
  --   (Regressione del 20260819-03, vista il 2026-08-19.)
  --   ⚠️ Il ramo NON scatta quando il BA c'e' ed e' solo non
  --   mappato: li' la delegata ha gia' fatto COALESCE con il
  --   default. Costa una query in piu' SOLO senza BA.
  --   ⛔ NON si toglie il corto-circuito alla delegata: e' una
  --   scelta esplicita di un altro cantiere e i suoi lettori si
  --   aspettano NULL da un input nullo. Toglierlo sarebbe una
  --   decisione di dominio, non la riparazione di un difetto.
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
IS 'Risolve «quale emittente fattura questo billing account» PER LO SCRITTORE: restituisce il soggetto_ruolo_id dell''emittente e SOLLEVA E_EMITTENTE_DEFAULT_MISSING se non e'' risolvibile. La regola «mapping specifico, poi is_default» vive in script.fn_get_ba_emittente_sr_id dal 2026-08-19 (P-6/5b); qui resta il punto in cui un NULL diventa un errore di dominio, perche'' e'' questa la funzione che vendite.fn_build_fattura_key usa per scegliere il REGISTRO su cui numerare — e li'' un NULL significherebbe «numera dove capita». ⚠️ CONSERVA UN RIPIEGO PROPRIO sul default per il caso SENZA billing account: la delegata corto-circuita sull''input NULL e non ci arriva, mentre la versione storica ci arrivava — non per disegno, ma perche'' il suo WHERE su NULL non trovava nulla e la SELECT sul default rispondeva lo stesso. E'' un comportamento nato per caso e diventato portante: vendite.fn_get_or_create_lotto chiama senza BA (un lotto non ne ha uno) e senza il ripiego prende E_EMITTENTE_DEFAULT_MISSING su un giro legittimo — regressione introdotta dal 20260819-03 e riparata qui. ⛔ Non si e'' tolto il corto-circuito alla delegata: e'' una scelta esplicita del cantiere perimetro emittente (§11.11) e i suoi lettori si aspettano NULL da un input nullo; cambiarlo e'' una decisione di dominio da prendere a parte. Il ramo non scatta per un BA esistente ma non mappato, dove la delegata ha gia'' fatto COALESCE. SECURITY INVOKER. rev 2026-08-19.';
```

</div>

---
{% include-markdown "signature-core.md" %}
