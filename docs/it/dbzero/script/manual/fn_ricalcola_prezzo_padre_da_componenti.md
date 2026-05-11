# fn_ricalcola_prezzo_padre_da_componenti

### Scopo

Funzione pura generica del pattern "righe componenti BoM CASO A": aggiorna `prezzo_unitario` della riga padre come `SUM(figli.prezzo_unitario × figli.coeff_qta_snapshot)` sui figli attivi. Parametrizzata su schema/tabella/FK per essere riusata da tutte e 5 le sorgenti documentali (preventivi, ordini, contratti, DDT, consumi).

> **Vedi anche**
>
> - [script.trgfn_componenti_ricalcola_padre](/dbzero/script/funzioni/trgfn_componenti_ricalcola_padre) — trigger wrapper che chiama questa funzione
> - [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti) — prima delle 5 tabelle che la usano

## Schema

`script`

## Firma

```sql
script.fn_ricalcola_prezzo_padre_da_componenti(
    p_schema        text,
    p_tab_padre     text,
    p_tab_figli     text,
    p_col_fk_padre  text,
    p_riga_padre_id BIGINT
) RETURNS VOID
```

## Parametri

| Parametro | Tipo | Descrizione |
|---|---|---|
| `p_schema` | `text` | Schema delle tabelle padre e figli (es. `'vendite'`) |
| `p_tab_padre` | `text` | Nome tabella padre (es. `'preventivi_righe'`) |
| `p_tab_figli` | `text` | Nome tabella figli (es. `'preventivi_righe_componenti'`) |
| `p_col_fk_padre` | `text` | Nome colonna FK sulla tabella figli (es. `'riga_preventivo_id'`) |
| `p_riga_padre_id` | `bigint` | PK della riga padre da aggiornare |

## Algoritmo

Esegue via SQL dinamico (`format` con `%I` per identifier quoting):

```sql
UPDATE <schema>.<tab_padre>
   SET prezzo_unitario = COALESCE((
       SELECT SUM(c.prezzo_unitario * c.coeff_qta_snapshot)
         FROM <schema>.<tab_figli> c
        WHERE c.<col_fk_padre> = <id>
          AND c.attivo = TRUE
   ), 0)
 WHERE id = <id>
```

- **Figli inattivi esclusi**: `attivo = TRUE` — i componenti disattivati non concorrono al prezzo padre.
- **COALESCE 0**: se tutti i figli sono inattivi o non esistono figli, il prezzo padre viene impostato a `0` (mai NULL).
- **SQL dinamico sicuro**: gli identificatori schema/tabella/colonna passano per `%I` di `format()`, che li quota correttamente — nessun rischio SQL injection.

## Note operative

- Chiamata esclusivamente da `script.trgfn_componenti_ricalcola_padre` via `PERFORM`.
- Assume che `<tab_padre>` abbia colonna `prezzo_unitario NUMERIC` e `id BIGINT/identico al tipo FK`.
- Assume che `<tab_figli>` abbia colonne `prezzo_unitario NUMERIC`, `coeff_qta_snapshot NUMERIC` e `attivo BOOLEAN`.
- `LANGUAGE plpgsql` con SQL dinamico: non marcata `STABLE` perché esegue UPDATE.
