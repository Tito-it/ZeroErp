## Documentazione Concettuale – Funzione `script.fn_current_identita_context`

> **Ultimo aggiornamento**: 24 ottobre 2026
>
> **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Parametri personalizzati (GUC)](/postgresql/parametri-personalizzati-(GUC)) — con l'[elenco dei GUC](/postgresql/parametri-personalizzati-(GUC)#elenco-dei-guc)
> [Contratto GUC `app.*`](/guide/contratto-guc-app)
>
**Tabelle correlate:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>
**Funzioni correlate:**
>
[script.fn_scope_ba_ownership](/dbzero/script/funzioni/fn_scope_ba_ownership)
> [script.fn_scope_ef_whitelist](/dbzero/script/funzioni/fn_scope_ef_whitelist)
> [script.fn_scope_fornitore_ownership](/dbzero/script/funzioni/fn_scope_fornitore_ownership)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

La funzione **`script.fn_current_identita_context()`** è un **helper di
convenienza** che legge in un unico SELECT i tre GUC di sessione del
contesto identità popolati dal middleware `JwtAuditAuthentication` e li
restituisce come record tipato.

Introdotta in §4.7.2 WIP multi-face-auth per centralizzare il pattern di
lettura dei GUC (con missing_ok=true + NULLIF + cast) usato dalle policy
RLS, dalle funzioni `fn_scope_*` e da ogni futura logica DB che necessita
di sapere "chi sta operando in questa sessione" al di là del semplice
`auth_user.id`.

---

### Output

`TABLE` a singola riga con tre colonne:

| Colonna | Tipo | Sorgente GUC | Descrizione |
|---------|------|--------------|-------------|
| `current_identita_id` | `bigint` | `app.current_identita_id` | `anagrafiche.identita_digitali.id` della veste attiva per la richiesta corrente. |
| `ruolo_applicativo` | `config.ruolo_applicativo` | `app.ruolo_applicativo` | Ruolo applicativo dell'identità (`OPERATORE`, `CLIENTE_PORTALE`, …). |
| `soggetto_ruolo_id` | `bigint` | `app.soggetto_ruolo_id` | `anagrafiche.soggetti_ruoli.id` del soggetto proprietario dell'identità. Usato dalle policy di ownership. |

Fail-soft: se uno o più GUC non sono settati (o sono stringhe vuote), la
colonna corrispondente ritorna `NULL`. Nessun errore sollevato.

---

### Pattern di lettura applicato

Per ciascun GUC:

```sql
NULLIF(current_setting('app.<nome>', true), '')::<tipo>
```

* `current_setting(..., true)` con `missing_ok = true`: restituisce
  stringa vuota se il GUC non è stato mai impostato (niente exception).
* `NULLIF('', '')` → `NULL`: coerenza semantica tra "non settato" e
  "settato a vuoto".
* Cast al tipo target (bigint / enum): tipizzazione sicura, validazione
  automatica se il valore non è parseable.

---

### Invariante "tutto o niente"

Il middleware `JwtAuditAuthentication` **deve popolare tutti e tre i GUC
contemporaneamente** (oppure nessuno, per i percorsi non autenticati).

* Dati parziali producono stati incoerenti nelle policy RLS.
* Se una delle tre colonne ritorna `NULL` in una chiamata autenticata, è
  un **bug del middleware** — le policy `fn_scope_*` devono trattarlo come
  **fail-closed**.

---

### Regole implementative

* `LANGUAGE sql`, `STABLE`: inlineable dal planner, nessun side effect,
  cacheable nella stessa statement.
* Nessun parametro di input: usa solo stato di sessione via
  `current_setting`.
* Ritorno come `TABLE` (set di record): permette sia la forma
  `SELECT * FROM script.fn_current_identita_context()` sia
  `SELECT (script.fn_current_identita_context()).current_identita_id`.

---

### Esempi d'uso

**Diagnostica** (chi sono, in quale veste?):

```sql
SELECT * FROM script.fn_current_identita_context();
--  current_identita_id | ruolo_applicativo | soggetto_ruolo_id
-- ---------------------+-------------------+-------------------
--                   42 | OPERATORE         |               123
```

**Dentro una policy RLS** (§4.9 WIP):

```sql
CREATE POLICY rls_fatture_ba_ownership ON vendite.fatture
    FOR SELECT
    USING (
        script.fn_scope_ba_ownership(
            (SELECT current_identita_id FROM script.fn_current_identita_context()),
            billing_account_id
        )
    );
```

**Dentro una funzione scope** (recupera solo il campo necessario):

```sql
DECLARE
    v_identita_id bigint;
BEGIN
    SELECT current_identita_id
      INTO v_identita_id
      FROM script.fn_current_identita_context();

    IF v_identita_id IS NULL THEN
        RETURN false;  -- fail-closed: sessione senza identita
    END IF;

    -- ... logica di scope ...
END;
```

**Debug via `SET` locale** (test pgTAP / psql):

```sql
SET LOCAL app.current_identita_id = '42';
SET LOCAL app.ruolo_applicativo   = 'OPERATORE';
SET LOCAL app.soggetto_ruolo_id   = '123';

SELECT * FROM script.fn_current_identita_context();
```

---

### Quando NON usarla

* Non chiamarla in hot loop riga-per-riga su grandi result set: usa un
  CTE o una variabile PL/pgSQL per cache del risultato.
* Non è un "validator": se il GUC è settato a un valore non parseable
  (es. `'foo'::bigint`), la chiamata fallisce con un cast error. Il
  middleware è responsabile di passare valori validi.

---

{% include-markdown "signature-core.md" %}
