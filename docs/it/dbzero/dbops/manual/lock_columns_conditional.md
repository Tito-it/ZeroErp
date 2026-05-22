# lock_columns_conditional

> **Vedi anche**
>
> - [dbops.fn_non_editable_fields](/dbzero/dbops/manual/fn_non_editable_fields) — funzione che unisce lock statici e condizionali per una riga specifica
> - [dbops.vw_non_editable_fields](/dbzero/dbops/manual/vw_non_editable_fields) — lock statici (incondizionati)
> - [dbops.automation_lock_columns](/dbzero/dbops/manual/automation_lock_columns) — tabella sorgente dei lock statici
> - [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/manual/trgfn_articoli_guard_flags_struttura_bom_attiva) — prima applicazione: guard trigger simmetrico

## Scopo

(latest review 2026-05-22)

`dbops.lock_columns_conditional` e' il registro dei **lock condizionali** sulle
colonne di entita' applicative: colonne che diventano non editabili solo quando
una condizione legata allo stato della riga specifica e' vera.

Complementare a `dbops.automation_lock_columns` (lock statici, sempre attivi):

| Tipo lock | Registro | Quando si attiva |
| --- | --- | --- |
| **Statico** | `automation_lock_columns` → `vw_non_editable_fields` | Sempre, per qualsiasi riga |
| **Condizionale** | `lock_columns_conditional` → `fn_non_editable_fields` | Solo se `condition_expr` e' TRUE per la riga specifica |

---

## Schema DB

`dbops`

## Struttura tabella

| Colonna | Tipo | Descrizione |
| --- | --- | --- |
| `id` | `INTEGER IDENTITY` | PK surrogata |
| `schema_name` | `text NOT NULL` | Schema della tabella target (es. `catalogo`) |
| `table_name` | `text NOT NULL` | Tabella target (es. `articoli`) |
| `column_name` | `text NOT NULL` | Colonna che diventa non editabile se la condizione e' vera |
| `condition_expr` | `text NOT NULL` | Snippet SQL booleano. `$1` = id riga come `text` |
| `descrizione` | `text` | Spiegazione in linguaggio naturale (per audit e revisione) |
| `enabled` | `boolean NOT NULL DEFAULT true` | Abilita/disabilita senza eliminare la riga |
| Audit | `data_insert`, `user_insert`, `data_update`, `user_update` | Tracciabilita' standard |

**UNIQUE**: `(schema_name, table_name, column_name, condition_expr)` — previene duplicati
testuali della stessa regola. Per duplicati semantici (whitespace) il code review e'
sufficiente data la policy "solo-migration".

---

## condition_expr — sintassi e vincoli

`condition_expr` e' un frammento SQL che:

1. Deve restituire un **boolean** (TRUE/FALSE/NULL). NULL viene trattato come FALSE.
2. Usa `$1` come placeholder parametrico per l'id della riga target (`text`).
   Il cast al tipo della colonna FK e' a carico dell'espressione.
3. E' concatenato direttamente nel corpo della query dinamica:
   ```sql
   EXECUTE 'SELECT (' || condition_expr || ')' USING p_record_id INTO v_match
   ```
4. Non deve contenere DDL, side effects, o transazioni nidificate.

**Regola di accesso**: la tabella e' scrivibile **solo via migration Liquibase**.
Nessuna API espone questa tabella. Il code review e' la protezione principale.
Non e' previsto un trigger di validazione sintattica (aggiungerebbe complessita' per
una sicurezza marginale su un dato accessibile solo a migration author).

**Esempio condition_expr per articolo padre di BoM attiva:**

```sql
EXISTS (
    SELECT 1 FROM catalogo.articoli_componenti
     WHERE prodotto_id = $1::uuid
       AND attivo IS TRUE
       AND validita @> CURRENT_DATE
)
```

`$1::uuid`: l'id di `catalogo.articoli` e' UUID; il cast e' necessario perche'
`fn_non_editable_fields` passa `p_record_id` come `text`.

---

## Come aggiungere una nuova regola

1. Identificare la colonna, la tabella, e la condizione SQL che attiva il lock.
2. Verificare che la stessa logica sia enforced a DB da un guard trigger
   (defense-in-depth: il lock condizionale segnala al FE, il trigger rifiuta al save).
3. Creare una migration in `80_data/` con INSERT in `lock_columns_conditional`.
4. Aggiornare la doc manuale della tabella target (sezione `non_editable_fields`).

```sql
INSERT INTO dbops.lock_columns_conditional
    (schema_name, table_name, column_name, condition_expr, descrizione)
VALUES
    (
        'schema',
        'tabella',
        'colonna',
        'EXISTS (SELECT 1 FROM ... WHERE fk = $1::tipo AND attivo IS TRUE)',
        'Spiegazione human-readable del perche'' la colonna e'' bloccata'
    )
ON CONFLICT ON CONSTRAINT uq_lock_columns_conditional DO UPDATE
    SET descrizione = EXCLUDED.descrizione,
        data_update = now(),
        user_update = CURRENT_USER;
```

---

## Casi registrati (al 2026-05-22)

| Schema | Tabella | Colonna | Condizione (sintesi) | Guard trigger simmetrico |
| --- | --- | --- | --- | --- |
| `catalogo` | `articoli` | `is_composito` | Articolo padre di BoM attiva (`prodotto_id = $1::uuid`) | `trg_articoli_a10_guard_flags_struttura_bom_attiva_upd` |
| `catalogo` | `articoli` | `requires_serial` | Articolo padre di BoM attiva (`prodotto_id = $1::uuid`) | `trg_articoli_a10_guard_flags_struttura_bom_attiva_upd` |
| `catalogo` | `articoli` | `is_solo_componente` | Articolo figlio in BoM attiva (`componente_id = $1::uuid`) | `trg_articoli_a10_guard_flags_struttura_bom_attiva_upd` |

---

## Dipendenze

| Oggetto | Tipo | Motivo |
| --- | --- | --- |
| `dbops.fn_non_editable_fields` | Funzione | Consumer principale: valuta `condition_expr` e unisce i risultati con i lock statici |
| `dbops.vw_non_editable_fields` | Vista | Complementare: lock statici che `fn_non_editable_fields` include nel risultato |

---

## Note operative

- **SECURITY INVOKER**: `fn_non_editable_fields` esegue `condition_expr` con i permessi
  del chiamante. Le tabelle referenziate in `condition_expr` devono avere `SELECT` concesso
  al ruolo applicativo (`zeroerp_app`). Se RLS e' attiva, filtra le righe visibili —
  comportamento corretto per il principio di minimo privilegio.
- **Guard trigger disaccoppiato**: il trigger DB che rifiuta la modifica e' self-contained
  (hardcoded). Se una riga viene rimossa da `lock_columns_conditional`, il trigger continua
  a rifiutare il save — la colonna smette solo di apparire come non editabile nel segnale API.
  Questo e' il comportamento voluto (defense-in-depth nella direzione corretta).
- **enabled = false**: disabilita temporaneamente una regola senza cancellarla. Utile
  durante patch di dati autorizzati. Reimpostare `enabled = true` a fine intervento.
- Migration di riferimento: `20260522-02` (tabella), `20260522-03` (funzione), `20260522-04` (seed articoli).
