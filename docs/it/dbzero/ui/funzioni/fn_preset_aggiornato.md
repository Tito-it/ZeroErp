{% include-markdown "it/dbzero/ui/manual/fn_preset_aggiornato.md" %}
# ⚙️ Funzione `fn_preset_aggiornato`

```sql
CREATE FUNCTION fn_preset_aggiornato(p_snapshot jsonb, p_contenuto jsonb, p_chiavi text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_preset_aggiornato(p_snapshot jsonb, p_contenuto jsonb, p_chiavi text[])
 RETURNS text[]
 LANGUAGE sql
 STABLE PARALLEL SAFE
BEGIN ATOMIC
 SELECT COALESCE(array_agg(k.chiave ORDER BY k.chiave), ARRAY[]::text[]) AS "coalesce"
    FROM unnest(fn_preset_aggiornato.p_chiavi) k(chiave)
   WHERE (((fn_preset_aggiornato.p_contenuto ->> k.chiave))::timestamp with time zone > ((fn_preset_aggiornato.p_snapshot ->> k.chiave))::timestamp with time zone);
END

COMMENT ON FUNCTION ui.fn_preset_aggiornato(p_snapshot jsonb, p_contenuto jsonb, p_chiavi text[])
IS 'Il banner del preset aggiornato, per liste e dashboard: le chiavi di p_chiavi per cui il contenuto del preset di base (p_contenuto, contenuto_aggiornato_il del preset) e'' piu'' recente dello snapshot salvato con la preferenza (p_snapshot, preset_base_contenuto_aggiornato_il). Il chiamante passa le chiavi che la preferenza imposta: una chiave che segue gia'' il preset non entra. Elenco ordinato, vuoto e mai NULL; vuoto se manca lo snapshot, il contenuto o la chiave in uno dei due. Chiudere il banner e'' riallineare lo snapshot (ui.trgfn_preferenza_preset_base_snapshot). Il chiamante lo chiede solo quando la base salvata e'' la base di oggi: una base diversa e'' un altro esito (preset_base_cambiato). La leggono ui.fn_resolve_lista_config e ui.fn_resolve_dashboard_config. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
