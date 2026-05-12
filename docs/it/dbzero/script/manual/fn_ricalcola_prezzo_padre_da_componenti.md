# fn_ricalcola_prezzo_padre_da_componenti

### Scopo

Funzione generica del pattern "righe componenti BoM CASO A": aggiorna `prezzo_unitario` della riga padre come `COALESCE(SUM(figli.prezzo_unitario × figli.coeff_qta_snapshot), 0)` sui figli attivi. Parametrizzata su schema/tabella/FK per essere riusata da tutte e 4 le sorgenti documentali (preventivi, ordini, contratti, DDT).

> **Vedi anche**
>
> - [script.trgfn_componenti_ricalcola_padre](/dbzero/script/funzioni/trgfn_componenti_ricalcola_padre) — trigger wrapper che chiama questa funzione
> - [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti) — prima delle 4 tabelle che la usano

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
- **Somma pesata**: `prezzo_unitario × coeff_qta_snapshot` per ogni componente attivo.
- **Nessun componente attivo → 0**: `COALESCE(..., 0)` gestisce la BoM vuota o con tutti i componenti inattivi.
- **SQL dinamico sicuro**: gli identificatori schema/tabella/colonna passano per `%I` di `format()` — nessun rischio SQL injection.

## Invariante componenti

Con il pattern form atomic (rev. 12-05-2026b), `prezzo_unitario` è sempre NOT NULL su tutte le tabelle `*_righe_componenti`. Il vincolo DB è:

```sql
prezzo_unitario NUMERIC NOT NULL CHECK (prezzo_unitario <> 0)
```

La somma dei componenti attivi è quindi sempre un valore numerico non nullo: `SUM` non produce mai NULL (i figli attivi hanno prezzo valorizzato), e `COALESCE` copre solo il caso di BoM vuota.

## Note operative

- Chiamata esclusivamente da `script.trgfn_componenti_ricalcola_padre` via `PERFORM`.
- Assume che `<tab_padre>` abbia colonna `prezzo_unitario NUMERIC NOT NULL` e `id BIGINT` (o compatibile con il tipo FK).
- Assume che `<tab_figli>` abbia colonne `prezzo_unitario NUMERIC NOT NULL`, `coeff_qta_snapshot NUMERIC` e `attivo BOOLEAN`.
- `LANGUAGE plpgsql` con SQL dinamico: non marcata `STABLE` perché esegue UPDATE.
