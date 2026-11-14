# ⚙️ Funzione `fn_titoli_iva_non_ammessi`

```sql
CREATE FUNCTION fn_titoli_iva_non_ammessi(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_titoli_iva_non_ammessi(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint)
 RETURNS TABLE(titolo_iva_id bigint, tipo_titolo_iva_id bigint, ordine smallint)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT t.id,
     t.tipo_titolo_iva_id,
     tt.ordine
    FROM (anagrafiche.soggetti_titoli_iva t
      JOIN config.tipi_titolo_iva tt ON ((tt.id = t.tipo_titolo_iva_id)))
   WHERE ((t.soggetto_id = fn_titoli_iva_non_ammessi.p_soggetto_id) AND anagrafiche.fn_titolo_iva_vigente(t.attivo, t.valido_al, script.fn_giorno_operativo(now())) AND (NOT anagrafiche.fn_titolo_iva_ammesso(t.tipo_titolo_iva_id, fn_titoli_iva_non_ammessi.p_tipo_soggetto_dettaglio_id)))
   ORDER BY tt.ordine, tt.id, t.id;
END

COMMENT ON FUNCTION anagrafiche.fn_titoli_iva_non_ammessi(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint)
IS 'I titoli IVA VIGENTI del soggetto che la natura di dettaglio passata NON ammette, in ordine stabile (ordine del tipo, poi id). Vigente e ammesso sono anagrafiche.fn_titolo_iva_vigente (oggi = script.fn_giorno_operativo(now())) e anagrafiche.fn_titolo_iva_ammesso; natura NULL = ogni titolo vigente e'' non ammesso. SECURITY INVOKER: vede i titoli che la RLS di chi chiama gli mostra; chiamata da anagrafiche.fn_titoli_iva_non_ammessi_conta, che e'' DEFINER, li vede tutti. E'' la sede unica del predicato: la legge anagrafiche.fn_check_cambio_natura_soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
