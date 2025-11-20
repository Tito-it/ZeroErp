{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_dati_societari_guard_tipo_soggetto.md" %}
# ⚙️ Funzione `trgfn_dati_societari_guard_tipo_soggetto`

```sql
CREATE FUNCTION trgfn_dati_societari_guard_tipo_soggetto()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_dati_societari_guard_tipo_soggetto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
   DECLARE
     v_cod_int_tipo text;
   BEGIN
   -- Controlla che il soggetto associato abbia un tipo valido
   -- solo SC e SP. In futuro si potrà estendere per altri tipi

     SELECT tsd.codice_interno
       INTO v_cod_int_tipo
       FROM anagrafiche.soggetti s
         JOIN config.tipi_soggetto_dettaglio tsd 
           ON s.tipo_soggetto_dettaglio_id = tsd.id
     WHERE s.id = NEW.soggetto_id;

     IF v_cod_int_tipo NOT IN ('SC','SP') THEN
       PERFORM script.fn_log_and_raise_error(
         'database',
         'anagrafiche.trgfn_check_tipo_soggetto_for_dati_societari',
         'E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO',
         jsonb_build_object(
           'soggetto_id', NEW.soggetto_id,
           'codice_interno', v_cod_int_tipo
         ),
         NULL::uuid,
         NEW.soggetto_id::text, v_cod_int_tipo
       );
     END IF;

     RETURN NEW;
   END;
   $function$
```

---
{% include-markdown "signature-core.md" %}
