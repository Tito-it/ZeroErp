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
   SET prezzo_unitario = CASE
       -- Almeno un componente attivo con prezzo NULL → padre = NULL
       WHEN EXISTS (
           SELECT 1 FROM <schema>.<tab_figli> c
            WHERE c.<col_fk_padre> = <id>
              AND c.attivo = TRUE
              AND c.prezzo_unitario IS NULL
       ) THEN NULL
       -- Nessun componente attivo → 0 (BoM vuota o tutti inattivi)
       WHEN NOT EXISTS (
           SELECT 1 FROM <schema>.<tab_figli> c
            WHERE c.<col_fk_padre> = <id>
              AND c.attivo = TRUE
       ) THEN 0
       -- Caso normale: somma pesata dei componenti attivi
       ELSE (
           SELECT SUM(c.prezzo_unitario * c.coeff_qta_snapshot)
             FROM <schema>.<tab_figli> c
            WHERE c.<col_fk_padre> = <id>
              AND c.attivo = TRUE
       )
   END
 WHERE id = <id>
```

- **Figli inattivi esclusi**: `attivo = TRUE` — i componenti disattivati non concorrono al prezzo padre.
- **Componente attivo con prezzo NULL → padre NULL**: se almeno un componente attivo ha `prezzo_unitario IS NULL` (valorizzazione manuale pendente autorizzata), il padre riflette lo stato di incompletezza. Il `CASE` esplicito è necessario perché PostgreSQL `SUM` ignora i NULL e restituirebbe comunque un valore parziale, mascherando la pendenza.
- **Nessun componente attivo → 0**: se la BoM è vuota o tutti i componenti sono inattivi, il prezzo padre viene impostato a `0`.
- **Caso normale → SUM pesata**: somma dei prodotti `prezzo_unitario × coeff_qta_snapshot` sui componenti attivi con prezzo valorizzato.
- **SQL dinamico sicuro**: gli identificatori schema/tabella/colonna passano per `%I` di `format()`, che li quota correttamente — nessun rischio SQL injection.

## Invariante componenti

Il vincolo DB su tutte le tabelle `*_righe_componenti` è:

```sql
CHECK (prezzo_unitario IS NULL OR prezzo_unitario <> 0)
```

NULL è ammesso solo via `fn_*_riga_componenti_init` con `p_force_manuale = TRUE` (attivato dal service BE quando l'operatore ha l'azione `prezzo_override_manuale`). Il valore `0` è sempre vietato.

## Note operative

- Chiamata esclusivamente da `script.trgfn_componenti_ricalcola_padre` via `PERFORM`.
- Assume che `<tab_padre>` abbia colonna `prezzo_unitario NUMERIC` (nullable) e `id BIGINT/identico al tipo FK`.
- Assume che `<tab_figli>` abbia colonne `prezzo_unitario NUMERIC` (nullable), `coeff_qta_snapshot NUMERIC` e `attivo BOOLEAN`.
- Il padre eredita `NULL` se anche un solo figlio attivo è pending: questa propagazione è intenzionale e consente ai guard di transizione di bloccare la finalizzazione del documento.
- `LANGUAGE plpgsql` con SQL dinamico: non marcata `STABLE` perché esegue UPDATE.
