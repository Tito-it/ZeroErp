# Brief DB — Fix operatore JSONB `??` → `?` nelle 4 fn `*_init` componenti

> **Data**: 2026-05-13
> **Branch target**: `dev/db-tid`
> **Urgenza**: BLOCCA il path overrides — riproducibile su CREATE riga
> composito con `componenti_overrides` valorizzato (cioe' ogni volta che
> l'operatore inserisce prezzi manuali per i componenti BoM).

## 1. Sintesi

Le 4 fn DB del modello unificato componenti BoM (init per preventivi,
ordini, contratti, ddt — migration 20260513-09/10/11/12) usano l'operatore
JSONB **`??`** che PostgreSQL non riconosce:

```sql
IF p_componenti_overrides IS NOT NULL
   AND p_componenti_overrides ?? v_comp.componente_id::text THEN
```

Errore runtime ottenuto durante smoke utente:

```
l'operatore non esiste: jsonb ?? text
LINE 2: AND p_componenti_overrides ?? v_comp.componente_i...
CONTEXT: funzione PL/pgSQL vendite.fn_preventivo_riga_componenti_init(...)
```

**Root cause probabile**: `??` scritto come escape Liquibase JDBC (Liquibase
usa `?` come placeholder, alcuni convertono `??` → `?` letterale). Con
`splitStatements: false` + SQL inline non c'e' escape, e il `??` arriva
letteralmente al DB.

**Operatore corretto**: `?` singolo — "JSONB has key" (vedi
[docs/postgres jsonb operators](https://www.postgresql.org/docs/18/functions-json.html)).
Alternativa equivalente: `jsonb_exists(jsonb, text)`.

## 2. Caller impattati

| Migration | Fn | Riga `??` |
|---|---|---|
| `20260513-09` | `vendite.fn_preventivo_riga_componenti_init` | 131 |
| `20260513-10` | `vendite.fn_ordine_riga_componenti_init` | 133 |
| `20260513-11` | `vendite.fn_ddt_riga_componenti_init` | 133 |
| `20260513-12` | `vendite.fn_contratto_riga_componenti_init` | 141 |

Tutte e 4 ricalcano lo stesso pattern (loop sui componenti BoM con check
override per chiave). Il bug e' identico in tutti i caller.

## 3. Cosa fare

**Non modificare i changelog 20260513-09..12** (gia' mergiati,
`runOnChange: true` ma policy progetto richiede nuova numerazione per
re-deploy).

**Creare 4 nuovi changelog** con numerazione successiva (es.
`20260513-25..28-update-fn-<sorgente>-riga-componenti-init-fix-jsonb-exists-mctit.yaml`),
ognuno con `runOnChange: true` e `validCheckSums: [ANY]`, che fanno
`CREATE OR REPLACE FUNCTION` identica all'originale **eccetto la riga
incriminata**:

```sql
-- PRIMA (rotto):
AND p_componenti_overrides ?? v_comp.componente_id::text THEN

-- DOPO (PostgreSQL standard):
AND p_componenti_overrides ? v_comp.componente_id::text THEN
```

Il modo piu' veloce: copiare integralmente lo `CREATE OR REPLACE FUNCTION
...` di ciascuna migration 09..12 nei nuovi file, sostituendo solo `??`
con `?`. Nessuna altra modifica logica.

## 4. Test post-fix

**Smoke manuale** (path che ha rivelato il bug):

1. Aprire un preventivo BOZZA
2. Aggiungere riga con articolo composito
3. Nel `ComponentiDialog` FE: modificare il prezzo di almeno un
   componente (genera `componenti_overrides` non vuoto nel payload)
4. Conferma Dialog + Save riga → deve passare senza `E_DATABASE`

**Diretto in psql** per confermare l'operatore:

```sql
-- Deve ritornare TRUE:
SELECT '{"foo": 1}'::jsonb ? 'foo';

-- Deve ritornare FALSE:
SELECT '{"foo": 1}'::jsonb ? 'bar';
```

**pgTAP**: aggiungere un test al suite `db/pgtap/vendite/` che valida
il path overrides con jsonb non vuoto su almeno 1 delle 4 fn init.

## 5. Verifica catena BE

Una volta applicato il fix DB, il backend non richiede modifiche: il
service `gestisci_riga` passa gia' `p_componenti_overrides` come JSONB
correttamente. La firma e il contratto delle fn restano invariati.

## 6. Riferimenti

- Modello: [`manual/modello-componenti-bom.md`](../manual/modello-componenti-bom.md)
- Brief DB originario: [`brief-db-componenti-modello-unificato.md`](brief-db-componenti-modello-unificato.md)
- Doc fn JSONB operators PostgreSQL 18:
  https://www.postgresql.org/docs/18/functions-json.html
