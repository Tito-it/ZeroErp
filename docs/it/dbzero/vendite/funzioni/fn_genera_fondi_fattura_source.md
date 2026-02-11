{% include-markdown "it/dbzero/vendite/manual/fn_genera_fondi_fattura_source.md" %}
# ⚙️ Funzione `fn_genera_fondi_fattura_source`

```sql
CREATE FUNCTION fn_genera_fondi_fattura_source(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_tipo_fondo_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_genera_fondi_fattura_source(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_tipo_fondo_fattura_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_inserted integer := 0;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Genera righe in fatture_fondi_fattura_source per fatture
  --   con minimo=true non ancora presenti, non pagate.
  -- =========================================================

  IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_genera_fondi_fattura_source', 'E_GENERICO',
      jsonb_build_object('detail','billing_account_id obbligatorio'),
      NULL::uuid,
      'billing_account_id non valido'
    );
  END IF;

  IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_genera_fondi_fattura_source', 'E_GENERICO',
      jsonb_build_object('detail','utility_id obbligatorio'),
      NULL::uuid,
      'utility_id non valido'
    );
  END IF;

  IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_genera_fondi_fattura_source', 'E_GENERICO',
      jsonb_build_object('detail','tipo_doc_fiscale_id obbligatorio'),
      NULL::uuid,
      'tipo_doc_fiscale_id non valido'
    );
  END IF;

  IF p_emittente_soggetto_ruolo_id IS NULL OR p_emittente_soggetto_ruolo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_genera_fondi_fattura_source', 'E_GENERICO',
      jsonb_build_object('detail','emittente_soggetto_ruolo_id obbligatorio'),
      NULL::uuid,
      'emittente_soggetto_ruolo_id non valido'
    );
  END IF;

  IF p_valuta_id IS NULL OR p_valuta_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_genera_fondi_fattura_source', 'E_GENERICO',
      jsonb_build_object('detail','valuta_id obbligatorio'),
      NULL::uuid,
      'valuta_id non valido'
    );
  END IF;

  IF p_tipo_fondo_fattura_id IS NULL OR p_tipo_fondo_fattura_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_genera_fondi_fattura_source', 'E_GENERICO',
      jsonb_build_object('detail','tipo_fondo_fattura_id obbligatorio'),
      NULL::uuid,
      'tipo_fondo_fattura_id non valido'
    );
  END IF;

  INSERT INTO vendite.fatture_fondi_fattura_source (
    fattura_sorgente_id,
    tipo_fondo_fattura_id,
    importo,
    stato,
    fattura_figlia_id,
    data_assegnazione,
    user_assegnazione,
    billing_account_id,
    utility_id,
    tipo_doc_fiscale_id,
    emittente_soggetto_ruolo_id,
    valuta_id,
    meta,
    attivo,
    data_insert,
    user_insert,
    data_update,
    user_update
  )
  SELECT
    f.id,
    p_tipo_fondo_fattura_id,
    coalesce(f.totale_a_pagare, 0), 
    'DISPONIBILE',
    NULL,
    NULL,
    NULL,
    f.billing_account_id,
    p_utility_id,
    f.tipo_doc_fiscale_id,
    f.emittente_soggetto_ruolo_id,
    f.valuta_id,
    '{}'::jsonb,
    TRUE,
    now(),
    current_user,
    now(),
    current_user
  FROM vendite.fatture f
  CROSS JOIN LATERAL pagamenti.fn_get_saldo_fattura(f.id) sf
  WHERE f.minimo IS TRUE 
    AND f.billing_account_id = p_billing_account_id
    AND f.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
    AND f.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
    AND f.valuta_id = p_valuta_id
    AND NOT EXISTS (
      SELECT 1
      FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id = f.id
    )
    AND sf.saldo <>  f.totale_a_pagare;

  GET DIAGNOSTICS v_inserted = ROW_COUNT;

  RETURN v_inserted;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
