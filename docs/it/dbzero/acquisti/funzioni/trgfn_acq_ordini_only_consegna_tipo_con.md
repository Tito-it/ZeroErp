{% include-markdown "it/dbzero/acquisti/manual/trgfn_acq_ordini_only_consegna_tipo_con.md" %}
# ⚙️ Funzione `trgfn_acq_ordini_only_consegna_tipo_con`

```sql
CREATE FUNCTION trgfn_acq_ordini_only_consegna_tipo_con()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION acquisti.trgfn_acq_ordini_only_consegna_tipo_con()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
           DECLARE
             v_codice text;
           BEGIN
             
             SELECT ti.codice_interno
               INTO v_codice
               FROM anagrafiche.indirizzi i
               JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id
             WHERE i.id = NEW.indirizzo_consegna_id;

             IF v_codice IS DISTINCT FROM 'CON' THEN

                 PERFORM script.fn_log_and_raise_error(
                   'database', TG_NAME, 'E_TIPO_INDIRIZZO',
                   jsonb_build_object('table', 'acquisti.ordini',
                   'ordine_id', NEW.id,
                   'indirizzo_consegna_id', NEW.indirizzo_consegna_id,
                   'codice_interno', v_codice),
                   NULL::uuid,  NEW.id::text, v_codice, 'ordini' , 'CON'
                 );
             END IF;

             RETURN NEW;
 
           END;
 $function$
```

</div>

---
{% include-markdown "signature-core.md" %}
