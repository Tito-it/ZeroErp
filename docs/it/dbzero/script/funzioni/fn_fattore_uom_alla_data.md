{% include-markdown "it/dbzero/script/manual/fn_fattore_uom_alla_data.md" %}
# ⚙️ Funzione `fn_fattore_uom_alla_data`

```sql
CREATE FUNCTION fn_fattore_uom_alla_data(p_articolo_id uuid, p_uom_id bigint, p_data date, p_porta text, p_campo text, p_tabella text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_fattore_uom_alla_data(p_articolo_id uuid, p_uom_id bigint, p_data date, p_porta text, p_campo text, p_tabella text)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- numeric nudo DICHIARATO: l'inversa di una conversione non sta in
    -- numeric(18,6). p_porta, p_campo, p_tabella: nomi, nessuna colonna dietro.
    v_factor      numeric;
    v_art_codice  catalogo.articoli.codice%TYPE;
    v_base_codice catalogo.unita_misura.codice%TYPE;
    v_uom_codice  catalogo.unita_misura.codice%TYPE;
BEGIN
    v_factor := catalogo.fn_get_uom_factor(p_articolo_id, p_uom_id, p_data);
    IF v_factor IS NOT NULL THEN
        RETURN v_factor;
    END IF;

    SELECT a.codice, ub.codice INTO v_art_codice, v_base_codice
      FROM catalogo.articoli a
      LEFT JOIN catalogo.unita_misura ub ON ub.id = a.uom_id
     WHERE a.id = p_articolo_id;
    SELECT u.codice INTO v_uom_codice
      FROM catalogo.unita_misura u
     WHERE u.id = p_uom_id;

    PERFORM script.fn_log_and_raise_error(
        split_part(p_porta, '.', 1), p_porta,
        'E_UOM_MISSING',
        jsonb_build_object(
            'campo', p_campo,
            'articolo_id', p_articolo_id,
            p_campo, p_uom_id,
            'data_documento', p_data,
            'tabella', p_tabella),
        NULL::uuid,
        COALESCE(v_uom_codice, '—'), COALESCE(v_base_codice, '—'),
        COALESCE(v_art_codice, '—'), COALESCE(to_char(p_data, 'DD/MM/YYYY'), '—'));
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION script.fn_fattore_uom_alla_data(p_articolo_id uuid, p_uom_id bigint, p_data date, p_porta text, p_campo text, p_tabella text)
IS 'Il fattore dell''unita'' p_uom_id per l''articolo p_articolo_id alla data p_data (catalogo.fn_get_uom_factor), o il rifiuto: senza fattore -> E_UOM_MISSING, perche'' una quantita'' base inventata e'' peggio di nessuna. Il rifiuto nomina la porta che chiama (p_porta, schema.funzione: lo schema e'' l''area del log), il campo dell''unita'' (p_campo) e la tabella (p_tabella); valori: unita'', unita'' base, articolo, data. E'' la regola «senza fattore scritto, il fattore alla data» delle righe che portano un fattore: la chiamano script.trgfn_qta_from_operativa (righe dei documenti di vendita) e vendite.trgfn_attivita_fattore_alla_data (attivita'' di commessa).';
```

</div>

---
{% include-markdown "signature-core.md" %}
