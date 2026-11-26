{% include-markdown "it/dbzero/anagrafiche/manual/fn_tipi_indirizzo_proponibili_natura.md" %}
# ⚙️ Funzione `fn_tipi_indirizzo_proponibili_natura`

```sql
CREATE FUNCTION fn_tipi_indirizzo_proponibili_natura(p_tipo_soggetto_dettaglio_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_tipi_indirizzo_proponibili_natura(p_tipo_soggetto_dettaglio_id bigint)
 RETURNS TABLE(tipo_indirizzo_id integer, obbligatorio boolean, ammesso boolean, motivo_codice text, reason text, reason_key text, reason_valori jsonb, motivi jsonb)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT ti.id,
     anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura(fn_tipi_indirizzo_proponibili_natura.p_tipo_soggetto_dettaglio_id, ti.id, script.fn_data_operativa()) AS fn_tipo_indirizzo_obbligatorio_per_natura,
     (jsonb_array_length(c.motivi) = 0),
     ((c.motivi -> 0) ->> 'codice'::text),
     ((c.motivi -> 0) ->> 'reason'::text),
     ((c.motivi -> 0) ->> 'reason_key'::text),
     COALESCE(((c.motivi -> 0) -> 'valori'::text), '[]'::jsonb) AS "coalesce",
     c.motivi
    FROM (config.tipi_indirizzi ti
      CROSS JOIN LATERAL ( SELECT anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(fn_tipi_indirizzo_proponibili_natura.p_tipo_soggetto_dettaglio_id, '{}'::integer[], ti.id, script.fn_data_operativa(), NULL::uuid) AS motivi) c)
   WHERE ((fn_tipi_indirizzo_proponibili_natura.p_tipo_soggetto_dettaglio_id IS NULL) OR (EXISTS ( SELECT 1
            FROM config.tipi_soggetto_dettaglio tsd
           WHERE (tsd.id = fn_tipi_indirizzo_proponibili_natura.p_tipo_soggetto_dettaglio_id))))
   ORDER BY (jsonb_array_length(c.motivi) = 0) DESC, ti.codice_interno;
END

COMMENT ON FUNCTION anagrafiche.fn_tipi_indirizzo_proponibili_natura(p_tipo_soggetto_dettaglio_id bigint)
IS 'Il picker dei tipi di indirizzo per un soggetto che non esiste ancora, sulla natura di dettaglio scelta nel form: una riga per tipo di config.tipi_indirizzi, con obbligatorio (anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura, oggi), ammesso, il primo motivo (motivo_codice, reason, reason_key, reason_valori) e tutti i motivi. Legge la stessa check della madre singolare, anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto, senza tipi presenti: l''unico motivo possibile e'' il tipo che la natura non ammette (E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO). Natura NULL (nessuna natura scelta) o senza matrice: tutti ammessi, come per il guard. Natura che non esiste in config.tipi_soggetto_dettaglio: nessuna riga, come anagrafiche.fn_tipi_indirizzo_proponibili_soggetto per un soggetto che non c''e''. Prima gli ammessi, poi gli altri, per codice interno. Giorno: script.fn_data_operativa().';
```

</div>

---
{% include-markdown "signature-core.md" %}
