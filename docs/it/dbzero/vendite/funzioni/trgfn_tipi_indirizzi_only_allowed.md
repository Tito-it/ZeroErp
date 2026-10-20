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
-- rev 2026-10-20 (20261020-52, brief-db-grammatica-unica-documenti, 2d G-6):
--   l'ambito degli indirizzi e' il codice della sorgente del
--   documento; il ripiego senza argomento e' FATTURA.
 DECLARE
   -- rev 2026-10-20 (G-6): il codice della sorgente del documento (FATTURA, DDT_VENDITA,
  --   ORDINE_VENDITA, PREVENTIVO, OFFERTA_COMMERCIALE, CONTRATTO, DDT_ACQUISTO)
  v_ambito         config.tipi_indirizzi_allowed.ambito%TYPE := COALESCE(TG_ARGV[0], 'FATTURA');
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

COMMENT ON FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed()
IS 'Rev 2026-10-20 (20261020-52, brief-db-grammatica-unica-documenti 2d, G-6): l''ambito degli indirizzi e'' il codice della sorgente del documento (l''argomento del montaggio); ripiego FATTURA.';
```

---
{% include-markdown "signature-core.md" %}
