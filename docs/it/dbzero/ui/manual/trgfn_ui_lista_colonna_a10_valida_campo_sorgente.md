# trgfn_ui_lista_colonna_a10_valida_campo_sorgente

### 🎯 Scopo Principale

Guard BEFORE INSERT/UPDATE su `ui.lista_colonna`: verifica che `campo_sorgente` esista come attributo della view indicata da `lista_definizione.vista_sql` in `pg_catalog.pg_attribute`. Previene typo nel nome della colonna che causerebbero errori runtime alla prima apertura della lista.

## Schema

`ui`

## Firma

```sql
ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente() RETURNS trigger
```

## Trigger associato

```sql
TRIGGER trg_ui_lista_colonna_a10_valida_campo_sorgente_ins_upd
  BEFORE INSERT OR UPDATE OF campo_sorgente, tipo_colonna, lista_id
  ON ui.lista_colonna
  FOR EACH ROW
```

## Logica (cascata di skip)

| Condizione | Azione |
|------------|--------|
| `NEW.tipo_colonna = 'azione'` | Skip — le colonne azione non hanno `campo_sorgente` |
| `NEW.campo_sorgente IS NULL` | Skip |
| `lista_definizione.vista_sql IS NULL` | Skip — la lista non ha view, validazione impossibile |
| Colonna non trovata in `pg_catalog.pg_attribute` | Errore `E_UI_CAMPO_SORGENTE_NON_TROVATO` |
| Colonna trovata | `RETURN NEW` |

## Errori sollevati

| Codice | Quando |
|--------|--------|
| `E_UI_CAMPO_SORGENTE_NON_TROVATO` | `campo_sorgente` non trovato come attributo nella view |

## Note

- Esegue un lookup su `pg_catalog` (schema, relazione, attributo) ad ogni INSERT/UPDATE delle colonne indicate. Overhead trascurabile dato che avviene solo in fase di seed/configurazione, non a runtime.
- La verifica usa `attnum > 0 AND NOT attisdropped` per escludere colonne di sistema e colonne eliminate fisicamente ma ancora in catalogo.
- Il trigger si attiva su `UPDATE OF campo_sorgente, tipo_colonna, lista_id` perché tutti e tre i campi influenzano la validazione.
