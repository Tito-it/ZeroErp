{% include-markdown "it/dbzero/ui/manual/fn_preset_impronta.md" %}
# ⚙️ Funzione `fn_preset_impronta`

```sql
CREATE FUNCTION fn_preset_impronta(p_famiglia text, p_preset_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_preset_impronta(p_famiglia text, p_preset_id integer)
 RETURNS text
 LANGUAGE sql
 STABLE PARALLEL SAFE
BEGIN ATOMIC
 SELECT
         CASE p_famiglia
             WHEN 'lista'::text THEN ( SELECT md5((COALESCE(jsonb_agg(jsonb_build_array(pc.colonna_id, pc.ordine, pc.larghezza, pc.visibile, pc.fissata) ORDER BY pc.colonna_id), '[]'::jsonb))::text) AS md5
                FROM ui.lista_preset_colonna pc
               WHERE (pc.preset_id = fn_preset_impronta.p_preset_id))
             WHEN 'dashboard'::text THEN ( SELECT md5((COALESCE(jsonb_agg(jsonb_build_array(pw.widget_id, pw.ordine, pw.visibile) ORDER BY pw.widget_id), '[]'::jsonb))::text) AS md5
                FROM ui.dashboard_preset_widget pw
               WHERE (pw.preset_id = fn_preset_impronta.p_preset_id))
             ELSE NULL::text
         END AS "case";
END

COMMENT ON FUNCTION ui.fn_preset_impronta(p_famiglia text, p_preset_id integer)
IS 'L''impronta della composizione di un preset: l''md5 delle sue righe, ordinate per colonna (p_famiglia = ''lista'': colonna_id, ordine, larghezza, visibile, fissata di ui.lista_preset_colonna) o per widget (''dashboard'': widget_id, ordine, visibile di ui.dashboard_preset_widget). Due composizioni con le stesse righe hanno la stessa impronta, in qualunque ordine e con qualunque numero di riscritture siano nate; un preset senza righe ha l''impronta dell''insieme vuoto. Famiglia fuori dalle due: NULL. Una colonna nuova di contenuto della composizione entra qui. La scrive in ui.lista_preset.composizione_impronta e ui.dashboard_preset.composizione_impronta il trigger differito ui.trgfn_preset_riga_tocca_preset; la confronta con OLD ui.trgfn_preset_contenuto_aggiornato. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
