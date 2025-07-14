{% include-markdown "it/dbzero/script/manual/fn_validate_cf_piva_it.md" %}
# ⚙️ Funzione `fn_validate_cf_piva_it`

```sql
CREATE FUNCTION fn_validate_cf_piva_it(p_tipo_det_id bigint, p_partita_iva text, p_piva_gruppo text, p_codice_fiscale text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_validate_cf_piva_it(p_tipo_det_id bigint, p_partita_iva text, p_piva_gruppo text, p_codice_fiscale text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
     DECLARE
       l_tipo_det RECORD;
       l_error_ctx JSONB;
     BEGIN

     -- 0) Recupero il tipo di dettaglio del soggetto
     
       SELECT formato_cf, formato_piva
         INTO STRICT l_tipo_det
         FROM config.tipi_soggetto_dettaglio
       WHERE id = p_tipo_det_id;

     -- 2) Validazione Partita IVA principale (se formattato e valorizzato)
     IF l_tipo_det.formato_piva IS NOT NULL
       AND p_partita_iva IS NOT NULL
       AND NOT script.fn_valida_partita_iva(p_partita_iva)
     THEN
       l_error_ctx := jsonb_build_object(
         'tipo_det', p_tipo_det_id,
         'partita_iva', p_partita_iva
       );
       PERFORM script.fn_log_and_raise_error(
         'database',                           -- categoria
         'fn_validate_cf_piva_it',             -- nome della function
         'PIVA_NON_VALIDA',                    -- codice messaggio
         l_error_ctx,                          -- metadata
         NULL::uuid,
         p_partita_iva::text
       );
     END IF;

     -- 3) Validazione Partita IVA Gruppo Acquisto (stesso pattern)
     IF l_tipo_det.formato_piva IS NOT NULL
       AND p_piva_gruppo IS NOT NULL
       AND NOT script.fn_valida_partita_iva(p_piva_gruppo)
     THEN
       l_error_ctx := jsonb_build_object(
         'tipo_det', p_tipo_det_id,
         'piva_gruppo_acquisto', p_piva_gruppo
       );
       PERFORM script.fn_log_and_raise_error(
         'database',
         'fn_validate_cf_piva_it',
         'PIVA_NON_VALIDA',
         l_error_ctx, 
         NULL::uuid,
          p_piva_gruppo::text 
       );
     END IF;

     -- 4) Validazione Codice Fiscale (se formattato e valorizzato)
     IF l_tipo_det.formato_cf IS NOT NULL
       AND p_codice_fiscale IS NOT NULL
       AND NOT script.fn_valida_codice_fiscale(p_codice_fiscale)
     THEN
       l_error_ctx := jsonb_build_object(
         'tipo_det', p_tipo_det_id,
         'codice_fiscale', p_codice_fiscale
       );
       PERFORM script.fn_log_and_raise_error(
         'database',
         'fn_validate_cf_piva_it',
         'CF_NON_VALIDO',
         l_error_ctx,
         NULL::uuid,
         p_codice_fiscale::text 
       );
     END IF;

     RETURN;
   END;
   $function$
```