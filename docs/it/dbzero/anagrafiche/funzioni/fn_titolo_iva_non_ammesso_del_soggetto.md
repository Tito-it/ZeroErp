# ⚙️ Funzione `fn_titolo_iva_non_ammesso_del_soggetto`

```sql
CREATE FUNCTION fn_titolo_iva_non_ammesso_del_soggetto(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_titolo_iva_non_ammesso_del_soggetto(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint)
 RETURNS bigint
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    -- ⚠️ DEFINER: la RLS per emittente nasconderebbe i titoli presentati
    --   agli altri emittenti. Esce solo l'id del tipo (catalogo).
    SELECT t.tipo_titolo_iva_id
      FROM anagrafiche.soggetti_titoli_iva t
      JOIN config.tipi_titolo_iva tt ON tt.id = t.tipo_titolo_iva_id
     WHERE t.soggetto_id = p_soggetto_id
       AND anagrafiche.fn_titolo_iva_vigente(t.attivo, t.valido_al,
                                             script.fn_giorno_operativo(now()))
       AND NOT anagrafiche.fn_titolo_iva_ammesso(t.tipo_titolo_iva_id,
                                                 p_tipo_soggetto_dettaglio_id)
     ORDER BY tt.ordine, tt.id
     LIMIT 1;
$function$

COMMENT ON FUNCTION anagrafiche.fn_titolo_iva_non_ammesso_del_soggetto(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint)
IS 'Il primo tipo di titolo IVA VIGENTE del soggetto che la natura di dettaglio passata NON ammette, o NULL. La natura si passa perche'' il chiamante (il guard del cambio di natura, BEFORE UPDATE) ha ancora quella vecchia sulla riga; natura NULL = ogni titolo vigente e'' non ammesso. SECURITY DEFINER: soggetti_titoli_iva ha la RLS per emittente, e da INVOKER un titolo presentato a un altro emittente sarebbe invisibile. Esce solo l''id del tipo, mai protocollo, plafond o emittente. Vigente e ammesso: anagrafiche.fn_titolo_iva_vigente e fn_titolo_iva_ammesso. Ordine stabile (ordine del tipo, id). Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parte D).';
```

</div>

---
{% include-markdown "signature-core.md" %}
