# ⚙️ Funzione `fn_titolo_iva_vigente_su_natura_esiste`

```sql
CREATE FUNCTION fn_titolo_iva_vigente_su_natura_esiste(p_tipo_titolo_iva_id bigint, p_tipo_soggetto_dettaglio_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_titolo_iva_vigente_su_natura_esiste(p_tipo_titolo_iva_id bigint, p_tipo_soggetto_dettaglio_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    -- ⚠️ DEFINER, come la gemella: risponde solo si'/no.
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.soggetti_titoli_iva t
          JOIN anagrafiche.soggetti s ON s.id = t.soggetto_id
         WHERE t.tipo_titolo_iva_id         = p_tipo_titolo_iva_id
           AND s.tipo_soggetto_dettaglio_id = p_tipo_soggetto_dettaglio_id
           AND anagrafiche.fn_titolo_iva_vigente(t.attivo, t.valido_al,
                                                 script.fn_giorno_operativo(now()))
    );
$function$

COMMENT ON FUNCTION anagrafiche.fn_titolo_iva_vigente_su_natura_esiste(p_tipo_titolo_iva_id bigint, p_tipo_soggetto_dettaglio_id bigint)
IS 'Esiste un titolo IVA VIGENTE del tipo dato su un soggetto della natura data? Lo chiama il guard del ritiro di una riga di config.tipi_titolo_iva_tipi_soggetto_dettaglio (D-6): una riga non si ritira finche'' ci sono titoli vigenti che la usano. SECURITY DEFINER per la RLS per emittente di soggetti_titoli_iva; risponde solo si''/no. Vigente: anagrafiche.fn_titolo_iva_vigente. Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parte D).';
```

</div>

---
{% include-markdown "signature-core.md" %}
