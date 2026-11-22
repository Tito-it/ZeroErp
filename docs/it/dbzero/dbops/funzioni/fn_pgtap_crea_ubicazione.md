# ⚙️ Funzione `fn_pgtap_crea_ubicazione`

```sql
CREATE FUNCTION fn_pgtap_crea_ubicazione(p_magazzino_id bigint, p_codice character varying, p_campi jsonb, p_tipo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_ubicazione(p_magazzino_id bigint, p_codice character varying, p_campi jsonb DEFAULT '{}'::jsonb, p_tipo_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un'ubicazione del magazzino
--   p_magazzino_id, dal verbo magazzino.fn_aggiungi_ubicazione. Senza
--   p_tipo_id: il primo tipo attivo del catalogo. p_campi: i facoltativi
--   del verbo (parent_id, area, corsia, ...).
-- Uso: v_ubi := dbops.fn_pgtap_crea_ubicazione(v_mag, 'PGT-U1');
DECLARE
    v_tipo magazzino.ubicazioni.tipo_id%TYPE;
    v_ov   jsonb;  -- il ricordo di fn_pgtap_apri_area_per_nascita
    v_id   magazzino.ubicazioni.id%TYPE;
BEGIN
    v_tipo := COALESCE(p_tipo_id,
                       (SELECT t.id FROM config.tipi_ubicazione t
                         WHERE t.attivo ORDER BY t.id LIMIT 1));

    v_ov := dbops.fn_pgtap_apri_area_per_nascita('magazzino', 'ubicazioni');
    v_id := magazzino.fn_aggiungi_ubicazione(
                p_magazzino_id, p_codice, v_tipo, COALESCE(p_campi, '{}'::jsonb));
    PERFORM dbops.fn_pgtap_richiudi_area(v_ov);
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_ubicazione(p_magazzino_id bigint, p_codice character varying, p_campi jsonb, p_tipo_id bigint)
IS 'Fixture pgTAP: un''ubicazione del magazzino dato, dal verbo magazzino.fn_aggiungi_ubicazione, con l''area aperta per il tempo della nascita. Senza tipo: il primo tipo attivo di config.tipi_ubicazione. p_campi porta i facoltativi (parent_id, area, corsia, ...).';
```

</div>

---
{% include-markdown "signature-core.md" %}
