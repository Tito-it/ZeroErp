{% include-markdown "it/dbzero/ui/manual/trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts.md" %}
# ⚙️ Funzione `trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts`

```sql
CREATE FUNCTION trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: mantiene la coerenza tra preset_base_id e i campi derivati
-- (snapshot contenuto_aggiornato_il + tombstone ignore). Quando preset_base_id cambia
-- verso qualsiasi valore diverso (NULL o altro preset), entrambi i campi
-- perdono significato: si riferivano al vecchio preset.
-- IS DISTINCT FROM copre: NULL->valore, valore->NULL, valore->valore diverso.
BEGIN
  IF NEW.preset_base_id IS DISTINCT FROM OLD.preset_base_id THEN
    NEW.preset_base_contenuto_aggiornato_il      := NULL;
    NEW.preset_aggiornato_ignored_at := NULL;
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts()
IS 'Azzera preset_base_contenuto_aggiornato_il e preset_aggiornato_ignored_at quando preset_base_id cambia (IS DISTINCT FROM). Previene badge FE "preset aggiornato" non coerente dopo cambio o eliminazione del preset di base. Mirror del trigger ui.lista_preferenza_utente. rev 2026-11-08 (brief-db-revisione-dbops, giro 7-bis blocco c): la data del contenuto del preset sta in contenuto_aggiornato_il, lo snapshot in preset_base_contenuto_aggiornato_il; data_update e'' l''audit.';
```

</div>

---
{% include-markdown "signature-core.md" %}
