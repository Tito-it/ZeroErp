{% include-markdown "it/dbzero/pratiche/manual/fn_pratica_flussi_aperti.md" %}
# ⚙️ Funzione `fn_pratica_flussi_aperti`

```sql
CREATE FUNCTION fn_pratica_flussi_aperti(p_pratica_id bigint, p_escludi_flusso_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_pratica_flussi_aperti(p_pratica_id bigint, p_escludi_flusso_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(flusso_id bigint, template_flusso_id integer, codice character varying, stato_codice_interno character varying)
 LANGUAGE sql
 STABLE
AS $function$
-- Scopo: fn_check_* puro (no raise). Flussi ISTANZIATI della pratica in
--   stato NON TERMINALE = lavoro pendente. Terminale = stato senza
--   transizione di stato in uscita attiva (config.transizioni_stati_flussi_
--   pratiche), auto-mantenuto come il guard pratica-terminale.
--   p_escludi_flusso_id: ignora un'istanza (es. il flusso che sta
--   completando, ancora non-terminale nel guard BEFORE).
    SELECT f.id, f.template_flusso_id, tf.codice, sfp.codice_interno
      FROM pratiche.flussi f
      JOIN config.stati_flussi_pratiche sfp ON sfp.id = f.stato_id
      LEFT JOIN pratiche.template_flussi tf ON tf.id = f.template_flusso_id
     WHERE f.pratica_id = p_pratica_id
       AND (p_escludi_flusso_id IS NULL OR f.id <> p_escludi_flusso_id)
       AND EXISTS (
             SELECT 1
               FROM config.transizioni_stati_flussi_pratiche t
              WHERE t.stato_da_id = f.stato_id
                AND t.attivo
       );
$function$

COMMENT ON FUNCTION pratiche.fn_pratica_flussi_aperti(p_pratica_id bigint, p_escludi_flusso_id bigint)
IS 'Pure check (D1): flussi istanziati in stato NON terminale (lavoro pendente) della pratica. Terminale = stato senza transizione di stato in uscita attiva (config.transizioni_stati_flussi_pratiche), auto-mantenuto. p_escludi_flusso_id ignora un''istanza (il flusso che sta completando). Consumata da fn_check_pratica_chiudibile e dal guard di chiusura pratica.';
```

</div>

---
{% include-markdown "signature-core.md" %}
