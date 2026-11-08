# trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts

### 🎯 Scopo Principale

Mantiene la coerenza tra `preset_base_id` e `preset_base_contenuto_aggiornato_il` nella tabella `ui.lista_preferenza_utente`. Quando `preset_base_id` diventa NULL (per `ON DELETE SET NULL` dalla FK o per UPDATE diretto), azzera automaticamente anche `preset_base_contenuto_aggiornato_il`.

## Schema

`ui`

## Firma

```sql
ui.trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts() RETURNS trigger
```

## Trigger associato

```sql
TRIGGER trg_ui_lista_preferenza_utente_z90_clear_preset_base_ts_upd
  BEFORE UPDATE OF preset_base_id
  ON ui.lista_preferenza_utente
  FOR EACH ROW
```

## Logica

| Condizione | Azione |
|------------|--------|
| `NEW.preset_base_id IS NULL AND OLD.preset_base_id IS NOT NULL` | `NEW.preset_base_contenuto_aggiornato_il := NULL` |
| Qualsiasi altra condizione | `RETURN NEW` senza modifiche |

## Perché è necessario

`preset_base_contenuto_aggiornato_il` è uno snapshot di `lista_preset.contenuto_aggiornato_il` al momento del salvataggio della preferenza. Il frontend confronta questo valore con `lista_preset.contenuto_aggiornato_il` corrente per mostrare il badge "preset aggiornato — vuoi vedere le novità?".

Se il preset viene eliminato, la FK `ON DELETE SET NULL` azzera `preset_base_id` ma lascerebbe `preset_base_contenuto_aggiornato_il` con un timestamp relativo a un preset inesistente. Il trigger garantisce che il frontend non mostri mai il badge "preset aggiornato" per un preset eliminato: con `preset_base_id IS NULL`, il confronto non avviene.

## Note

- Si attiva su `UPDATE OF preset_base_id`: copertura sia per `ON DELETE SET NULL` (che genera un `UPDATE` interno di PostgreSQL) che per UPDATE diretti.
- Fase `_z90_`: non è un guard (non solleva errori), è un'azione finale di normalizzazione.
