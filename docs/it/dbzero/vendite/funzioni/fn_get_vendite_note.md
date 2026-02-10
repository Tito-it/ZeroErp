{% include-markdown "it/dbzero/vendite/manual/fn_get_vendite_note.md" %}
# ⚙️ Funzione `fn_get_vendite_note`

```sql
CREATE FUNCTION fn_get_vendite_note(
  _target_tipo text,
  _target_id bigint,
  _target_riga_id bigint,
  _include_doc boolean,
  _include_righe boolean,
  _only_visible boolean
)
```
