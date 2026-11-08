# trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts

### 🎯 Scopo Principale

Mantiene la coerenza tra `preset_base_id` e i due campi derivati (`preset_base_contenuto_aggiornato_il`, `preset_aggiornato_ignored_at`) nella tabella `ui.dashboard_preferenza_utente`. Quando `preset_base_id` cambia verso qualsiasi valore diverso (NULL o un altro preset), azzera entrambi i campi. Mirror del trigger omologo di [ui.lista_preferenza_utente](/dbzero/ui/funzioni/trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts).

## Schema

`ui`

## Firma

```sql
ui.trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts() RETURNS trigger
```

## Trigger associato

```sql
TRIGGER trg_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts_upd
  BEFORE UPDATE OF preset_base_id
  ON ui.dashboard_preferenza_utente
  FOR EACH ROW
```

## Logica

| Condizione | Azione |
|------------|--------|
| `NEW.preset_base_id IS DISTINCT FROM OLD.preset_base_id` | `NEW.preset_base_contenuto_aggiornato_il := NULL` **e** `NEW.preset_aggiornato_ignored_at := NULL` |
| Qualsiasi altra condizione | `RETURN NEW` senza modifiche |

`IS DISTINCT FROM` copre tutte le transizioni significative: `NULL → valore`, `valore → NULL`, `valore → valore diverso`.

## Perché è necessario

`preset_base_contenuto_aggiornato_il` è uno snapshot di `dashboard_preset.contenuto_aggiornato_il` al salvataggio della preferenza; `preset_aggiornato_ignored_at` è il tombstone dell'avviso "preset aggiornato" ignorato dall'utente. Entrambi sono relativi al **preset di base referenziato**: quando `preset_base_id` cambia (per `ON DELETE SET NULL` dalla FK o per UPDATE diretto verso un altro preset), quei valori perdono significato.

Azzerarli chiude il contratto col frontend: con `preset_base_id IS NULL` o cambiato, il badge "preset aggiornato" non si basa più su uno snapshot orfano.

## Note

- Si attiva su `UPDATE OF preset_base_id`: copertura sia per `ON DELETE SET NULL` (che genera un `UPDATE` interno di PostgreSQL) che per UPDATE diretti.
- Fase `_z90_`: non è un guard (non solleva errori), è un'azione finale di normalizzazione.
- Differenza rispetto al trigger liste: usa `IS DISTINCT FROM` (non solo `→ NULL`) e azzera **due** campi (include il tombstone `preset_aggiornato_ignored_at`).
