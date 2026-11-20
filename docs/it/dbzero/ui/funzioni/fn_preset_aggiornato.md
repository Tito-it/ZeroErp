{% include-markdown "it/dbzero/ui/manual/fn_preset_aggiornato.md" %}
# ⚙️ Funzione `fn_preset_aggiornato`

```sql
CREATE FUNCTION fn_preset_aggiornato(p_snapshot timestamp with time zone, p_contenuto timestamp with time zone, p_ignorato timestamp with time zone)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_preset_aggiornato(p_snapshot timestamp with time zone, p_contenuto timestamp with time zone, p_ignorato timestamp with time zone)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
BEGIN ATOMIC
 SELECT ((p_snapshot IS NOT NULL) AND (p_contenuto IS NOT NULL) AND (p_contenuto > p_snapshot) AND ((p_ignorato IS NULL) OR (p_ignorato < p_contenuto)));
END

COMMENT ON FUNCTION ui.fn_preset_aggiornato(p_snapshot timestamp with time zone, p_contenuto timestamp with time zone, p_ignorato timestamp with time zone)
IS 'Il flag del banner del preset aggiornato, per liste e dashboard: vero se il contenuto del preset di base (p_contenuto) e'' piu'' recente di quello salvato con la preferenza (p_snapshot) e l''utente non ha chiuso il banner dopo quel cambio (p_ignorato NULL o precedente). Falso, mai NULL, se manca lo snapshot o il contenuto. Il chiamante lo chiede solo quando la base salvata e'' la base di oggi: una base diversa e'' un altro esito (preset_base_cambiato). La leggono ui.fn_resolve_lista_config e ui.fn_resolve_dashboard_config. IMMUTABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
