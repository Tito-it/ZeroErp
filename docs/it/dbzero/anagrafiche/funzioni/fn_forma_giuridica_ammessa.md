# ⚙️ Funzione `fn_forma_giuridica_ammessa`

```sql
CREATE FUNCTION fn_forma_giuridica_ammessa(p_forma_giuridica_id bigint, p_tipo_soggetto_dettaglio_id bigint, p_oggi date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_forma_giuridica_ammessa(p_forma_giuridica_id bigint, p_tipo_soggetto_dettaglio_id bigint, p_oggi date)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Riga attiva e valida oggi = ammessa; nessuna riga = no; NULL = no.
    SELECT EXISTS (
        SELECT 1
          FROM config.forme_giuridiche_tipi_soggetto_dettaglio m
         WHERE m.forma_giuridica_id         = p_forma_giuridica_id
           AND m.tipo_soggetto_dettaglio_id = p_tipo_soggetto_dettaglio_id
           AND m.attivo
           AND (m.valido_dal IS NULL OR m.valido_dal <= p_oggi)
           AND (m.valido_al  IS NULL OR m.valido_al  >= p_oggi)
    );
$function$

COMMENT ON FUNCTION anagrafiche.fn_forma_giuridica_ammessa(p_forma_giuridica_id bigint, p_tipo_soggetto_dettaglio_id bigint, p_oggi date)
IS 'La forma giuridica e'' ammessa dalla natura di dettaglio: true se esiste una riga ATTIVA e valida oggi (valido_dal/valido_al) di config.forme_giuridiche_tipi_soggetto_dettaglio per la coppia. Nessuna riga = false; forma o natura NULL = false. Oggi lo passa chi chiama (script.fn_giorno_operativo(now())). Sede unica della domanda: la chiamano il guard della forma su anagrafiche.dati_societari e il guard al COMMIT sul cambio di natura del soggetto. STABLE, LANGUAGE sql, non STRICT. Brief: brief-db-dati-fiscali-e-societari-del-soggetto (C-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
