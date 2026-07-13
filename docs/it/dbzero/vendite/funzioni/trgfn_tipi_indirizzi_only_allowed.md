{% include-markdown "it/dbzero/vendite/manual/trgfn_tipi_indirizzi_only_allowed.md" %}
# ⚙️ Funzione `trgfn_tipi_indirizzi_only_allowed`

```sql
CREATE FUNCTION trgfn_tipi_indirizzi_only_allowed()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
 DECLARE
   v_ambito         text := COALESCE(TG_ARGV[0], 'FATTURE'); -- 'FATTURE'|'DDT'|'ORDINI'|'PREVENTIVI'|'OFFERTE'|'CONTRATTI'|'ACQUISTI_DDT'
   v_codice         text;
   v_allowed_ids    integer[];
   v_allowed_codes  text[];
   v_tabella        text := TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME;
 BEGIN
   -- Codice interno del tipo richiesto (per log).
   SELECT t.codice_interno INTO v_codice
   FROM config.tipi_indirizzi t
   WHERE t.id = NEW.tipo_indirizzo_id;

   -- Whitelist dei tipi ammessi per l'ambito: UNICA fonte = config.
   -- Nessun fallback hardcoded (fail-closed se ambito non configurato).
   SELECT array_agg(a.tipo_indirizzo_id),
          array_agg(t.codice_interno)
     INTO v_allowed_ids, v_allowed_codes
   FROM config.tipi_indirizzi_allowed a
   JOIN config.tipi_indirizzi t ON t.id = a.tipo_indirizzo_id
   WHERE a.ambito = v_ambito
     AND a.attivo = true;

   -- Validazione: tipo esistente E incluso nella whitelist dell'ambito.
   IF v_codice IS NULL
      OR v_allowed_ids IS NULL
      OR NOT (NEW.tipo_indirizzo_id = ANY(v_allowed_ids)) THEN
     PERFORM script.fn_log_and_raise_error(
       'database', TG_NAME, 'E_TIPO_INDIRIZZO',
       jsonb_build_object(
         'table', v_tabella,
         'ambito', v_ambito,
         'new_row', (to_jsonb(NEW) - 'snapshot'),
         'tipo_indirizzo_id', NEW.tipo_indirizzo_id,
         'codice_interno', v_codice,
         'allowed_codes', v_allowed_codes
       ),
       NULL::uuid,
       NEW.tipo_indirizzo_id::text,
       v_codice,
       v_ambito,
       array_to_string(COALESCE(v_allowed_codes, ARRAY[]::text[]), ', ')
     );
   END IF;

   RETURN NEW;
 END
 $function$
```

---
{% include-markdown "signature-core.md" %}
