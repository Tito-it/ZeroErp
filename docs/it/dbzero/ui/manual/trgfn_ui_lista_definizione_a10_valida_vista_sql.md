# trgfn_ui_lista_definizione_a10_valida_vista_sql

### 🎯 Scopo Principale

Guard BEFORE INSERT/UPDATE su `ui.lista_definizione`: verifica che `vista_sql` esista come relazione (view, materialized view o tabella) in `pg_catalog.pg_class` prima di permettere il salvataggio. Previene typo nel nome della view che causerebbero errori runtime alla prima apertura della lista.

## Schema

`ui`

## Firma

```sql
ui.trgfn_ui_lista_definizione_a10_valida_vista_sql() RETURNS trigger
```

## Trigger associato

```sql
TRIGGER trg_ui_lista_definizione_a10_valida_vista_sql_ins_upd
  BEFORE INSERT OR UPDATE OF vista_sql, attivo
  ON ui.lista_definizione
  FOR EACH ROW
```

## Logica

| Condizione | Azione |
|------------|--------|
| `NEW.vista_sql IS NULL` | Skip (la lista può non avere una view) |
| `NEW.attivo = FALSE` | Skip (lista disattivata, non validare) |
| View non trovata in `pg_catalog.pg_class` | Errore `E_UI_VISTA_SQL_NON_TROVATA` |
| View trovata (`relkind IN ('v','m','r')`) | `RETURN NEW` |

## Errori sollevati

| Codice | Quando |
|--------|--------|
| `E_UI_VISTA_SQL_NON_TROVATA` | `vista_sql` non trovata in `pg_catalog.pg_class` |

## Note

- Il trigger si attiva solo su `UPDATE OF vista_sql, attivo` (non su ogni UPDATE): minimizza l'overhead.
- Accetta `relkind IN ('v','m','r')`: view, materialized view e tabelle sono tutti validi come sorgente dati.
- Il nome della view deve essere il nome grezzo (senza schema) come appare in `pg_class.relname`.
