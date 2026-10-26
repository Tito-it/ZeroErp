# ⚙️ Funzione `fn_titolo_iva_ammesso`

```sql
CREATE FUNCTION fn_titolo_iva_ammesso(p_tipo_titolo_iva_id bigint, p_tipo_soggetto_dettaglio_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_titolo_iva_ammesso(p_tipo_titolo_iva_id bigint, p_tipo_soggetto_dettaglio_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Nessuna riga attiva = non ammesso (D-1); natura NULL = non ammesso.
    SELECT EXISTS (
        SELECT 1
          FROM config.tipi_titolo_iva_tipi_soggetto_dettaglio m
         WHERE m.tipo_titolo_iva_id         = p_tipo_titolo_iva_id
           AND m.tipo_soggetto_dettaglio_id = p_tipo_soggetto_dettaglio_id
           AND m.attivo
    );
$function$

COMMENT ON FUNCTION anagrafiche.fn_titolo_iva_ammesso(p_tipo_titolo_iva_id bigint, p_tipo_soggetto_dettaglio_id bigint)
IS 'La natura di dettaglio ammette il tipo di titolo IVA: true se esiste una riga ATTIVA di config.tipi_titolo_iva_tipi_soggetto_dettaglio per la coppia. Nessuna riga = false (un dettaglio senza righe non e'' libero, D-1); natura NULL = false. Sede unica della domanda: la chiamano il guard sui titoli e i due lettori DEFINER del cambio di natura e del ritiro di matrice. STABLE, LANGUAGE sql, non STRICT. Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parte D).';
```

</div>

---
{% include-markdown "signature-core.md" %}
