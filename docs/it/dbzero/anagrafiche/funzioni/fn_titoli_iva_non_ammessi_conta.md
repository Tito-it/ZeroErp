# ⚙️ Funzione `fn_titoli_iva_non_ammessi_conta`

```sql
CREATE FUNCTION fn_titoli_iva_non_ammessi_conta(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_titoli_iva_non_ammessi_conta(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint)
 RETURNS integer
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
BEGIN ATOMIC
 SELECT (count(*))::integer AS count
    FROM anagrafiche.fn_titoli_iva_non_ammessi(fn_titoli_iva_non_ammessi_conta.p_soggetto_id, fn_titoli_iva_non_ammessi_conta.p_tipo_soggetto_dettaglio_id) fn_titoli_iva_non_ammessi(titolo_iva_id, tipo_titolo_iva_id, ordine);
END

COMMENT ON FUNCTION anagrafiche.fn_titoli_iva_non_ammessi_conta(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint)
IS 'Quanti sono, in tutto, i titoli IVA vigenti del soggetto che la natura passata non ammette: anagrafiche.fn_titoli_iva_non_ammessi letta da SECURITY DEFINER, sopra la RLS per emittente di anagrafiche.soggetti_titoli_iva. Risponde solo il numero, mai id, protocollo, plafond o emittente: confrontato con quanti ne vede chi agisce dice se ce ne sono di altri emittenti. La legge anagrafiche.fn_check_cambio_natura_soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
