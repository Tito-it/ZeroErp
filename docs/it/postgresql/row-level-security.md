## Row Level Security (RLS) in PostgreSQL

>
> **Ultimo aggiornamento**: 24 ottobre 2026
>
> **Vedi anche**
>
> * [Linee guida SQL — sezione 10 Row Level Security](/linee-guida-sql#10-row-level-security-rls) — convenzioni ZeroErp (naming, funzioni `fn_scope_*`, bypass ruoli, checklist migrazione)
> * [Parametri personalizzati (GUC)](/postgresql/parametri-personalizzati-(GUC)) — le famiglie di GUC e l'[elenco](/postgresql/parametri-personalizzati-(GUC)#elenco-dei-guc)
> * [Contratto GUC `app.*`](/guide/contratto-guc-app) — i GUC d'identità che le policy leggono

Questa scheda descrive **sintassi e comportamento** di Row Level Security in PostgreSQL 18.
Le scelte architetturali di ZeroErp (quando abilitarla, come nominare le policy, come
strutturare le funzioni di scope) sono nella sezione dedicata delle linee guida SQL.

---

### Scopo Principale

Row Level Security consente di definire **policy a livello di riga** che filtrano
automaticamente cosa un utente vede, modifica, inserisce o elimina, senza richiedere
clausole WHERE esplicite nelle query.

Il filtro avviene nel planner: la policy diventa parte della query ottimizzata. Un
utente che tenta di aggirarla con `SELECT *` vede solo le righe ammesse dalla policy,
non l'intera tabella.

---

### Sintassi Essenziale

#### Abilitare RLS su una tabella

```sql
-- Abilita il meccanismo RLS (default: nessuna policy = nega tutto ai non-owner)
ALTER TABLE vendite.fatture ENABLE ROW LEVEL SECURITY;

-- Estende RLS anche al proprietario della tabella (altrimenti esentato)
ALTER TABLE vendite.fatture FORCE ROW LEVEL SECURITY;
```

**Attenzione**: senza `FORCE`, il ruolo proprietario della tabella ignora le policy.

In ZeroErp il backend si connette come `zeroerp_app`, che e' **non-owner** e
**`NOBYPASSRLS`** (le tabelle sono di `zeroerp_owner`, il proprietario, che fa
migrazioni e manutenzione). Per un ruolo non-owner il solo `ENABLE` e' gia'
sufficiente: la RLS si applica senza bisogno di `FORCE`. Di conseguenza, sulle
tabelle del ciclo attivo ZeroErp **non** usa `FORCE`: l'unico percorso DML
applicativo passa da `zeroerp_app` (gia' soggetto), mentre il proprietario **deve**
restarne fuori per le migrazioni e i lavori di manutenzione.

`FORCE` serve solo quando e' l'**owner** stesso a fare DML applicativo: non e' il
caso qui. (Nota: nei test pgTAP `FORCE` viene usato *localmente alla transazione*
per assoggettare il proprietario senza cambiare utente — vedi `db/pgtap/rls/`.)

#### Creare una policy

```sql
CREATE POLICY nome_policy ON schema.tabella
    [ AS { PERMISSIVE | RESTRICTIVE } ]
    [ FOR { ALL | SELECT | INSERT | UPDATE | DELETE } ]
    [ TO { role_name | PUBLIC | CURRENT_USER | SESSION_USER } [, ...] ]
    [ USING ( using_expression ) ]
    [ WITH CHECK ( check_expression ) ];
```

Esempio minimale:

```sql
CREATE POLICY rls_fatture_ba_ownership ON vendite.fatture
    FOR SELECT
    USING (
        script.fn_scope_ba_ownership(
            NULLIF(current_setting('app.current_identita_id', true), '')::bigint,
            billing_account_id
        )
    );
```

#### Rimuovere una policy

```sql
DROP POLICY IF EXISTS rls_fatture_ba_ownership ON vendite.fatture;
```

---

### `USING` vs `WITH CHECK`

La distinzione tra le due clausole e' **l'aspetto piu' frainteso** di RLS:

| Clausola | Si applica a | Semantica |
| --- | --- | --- |
| `USING` | `SELECT`, `UPDATE`, `DELETE` (righe **esistenti**) | Le righe che non soddisfano sono **invisibili** al comando |
| `WITH CHECK` | `INSERT`, `UPDATE` (righe **nuove / dopo modifica**) | Le righe che non soddisfano fanno **fallire** il comando con `ERROR: new row violates row-level security policy` |

Regole pratiche:

| Evento | Serve `USING` | Serve `WITH CHECK` |
| --- | :---: | :---: |
| `FOR SELECT` | Si' | No |
| `FOR INSERT` | No | Si' |
| `FOR UPDATE` | Si' | **Si'** |
| `FOR DELETE` | Si' | No |
| `FOR ALL` | Si' | Si' (se applicabile) |

**Comportamento silenzioso da conoscere**: se su `FOR UPDATE` ometti `WITH CHECK`,
PostgreSQL usa automaticamente l'espressione di `USING` anche per la verifica post-update.
In molti casi questo e' sbagliato: un utente potrebbe "spostare" una riga fuori dal proprio
scope (es. riassegnare `billing_account_id` a un altro cliente) senza errore. **Sempre
esplicitare** `WITH CHECK`, anche se uguale a `USING`.

---

### `PERMISSIVE` vs `RESTRICTIVE`

Le policy di default sono `PERMISSIVE`: se piu' policy si applicano allo stesso evento,
vengono combinate in **OR** (l'utente vede la riga se **almeno una** policy la ammette).

Le policy `RESTRICTIVE` vengono combinate in **AND** con tutte le altre: filtrano
ulteriormente anche cio' che le permissive avrebbero ammesso.

```sql
CREATE POLICY rls_fatture_non_annullate ON vendite.fatture
    AS RESTRICTIVE
    FOR SELECT
    USING (stato <> 'ANNULLATA');
```

Usare `RESTRICTIVE` con parsimonia: riduce la componibilita' e va documentato con
chiarezza, perche' non si combina "naturalmente" con le altre.

---

### Interazione con i GUC `app.*`

Le policy ZeroErp leggono l'identita' applicativa dai GUC `app.*` popolati da
`JwtAuditAuthentication` (backend Django). Riferimento completo:
[parametri-personalizzati-(GUC)](/postgresql/parametri-personalizzati-(GUC)).

Pattern raccomandato di lettura sicura del GUC:

```sql
-- Ritorna NULL se il GUC non e' settato, invece di errore
NULLIF(current_setting('app.current_identita_id', true), '')::bigint
```

Il secondo parametro `true` di `current_setting` attiva la modalita' "missing_ok":
invece di sollevare `unrecognized configuration parameter`, la funzione ritorna stringa
vuota. `NULLIF(..., '')::bigint` la converte in `NULL`.

**Regola**: le funzioni `script.fn_scope_*` **non leggono mai i GUC direttamente** —
ricevono i valori come parametri. Questo le rende pure, testabili con pgTAP, e
riutilizzabili anche fuori dalle policy.

**Helper `script.fn_current_identita_context`**: per funzioni PL/pgSQL che hanno bisogno
di piu' di un GUC insieme (es. policy RLS composta, audit), esiste il wrapper
[`script.fn_current_identita_context`](/dbzero/script/funzioni/fn_current_identita_context)
che restituisce `current_identita_id` + `ruolo_applicativo` + `soggetto_ruolo_id` in
un unico SELECT tipato, gestendo internamente il pattern `NULLIF(current_setting(...), '')::tipo`.
Dentro una policy RLS "mono-scope" e' preferibile leggere solo il GUC direttamente
(meno overhead del chiamare una funzione).

---

### Ruoli DB: `BYPASSRLS` e `FORCE ROW LEVEL SECURITY`

Tre regole di visibilita' concorrenti:

| Ruolo | Caso default | Con `FORCE` sulla tabella |
| --- | --- | --- |
| **Superuser** | Bypassa sempre RLS | Bypassa sempre RLS |
| **Owner della tabella** | Bypassa RLS | **Soggetto** a RLS |
| **Ruolo con `BYPASSRLS`** | Bypassa RLS | Bypassa RLS |
| **Altri ruoli** | Soggetti a RLS | Soggetti a RLS |

Configurazione ZeroErp:

```sql
-- Il proprietario delle tabelle (migrazioni, lavori di manutenzione) e' fuori
-- dalla RLS perche' e' il proprietario, non per un attributo: NOBYPASSRLS.
-- Ruoli e regole: provisioning-db-roles.

-- Ruolo applicativo del backend (DB_USER): NON owner, NON bypassa.
-- E' il ruolo con cui Django si connette -> soggetto a RLS col solo ENABLE.
ALTER ROLE zeroerp_app        NOBYPASSRLS;

-- Sulle tabelle del ciclo attivo basta ENABLE (zeroerp_app e' non-owner):
ALTER TABLE vendite.fatture   ENABLE ROW LEVEL SECURITY;
-- FORCE NON necessario: nessun owner fa DML applicativo a runtime.
```

**Processi automatici: nessun ruolo `BYPASSRLS`.** I processi senza utente
umano (management command, cron, lavori di coda) che toccano i dati di un'azienda
girano come `zeroerp_app`, con l'**utente tecnico** di quell'azienda nelle GUC: la
RLS li filtra come un operatore. Un processo che deve lavorare su più aziende ne
tratta una alla volta, ognuna con il suo utente. Il controllo
`dbops.vw_processi_che_bypassano` deve restare vuoto. Modello:
[I lavori automatici](/guide/processi-automatici-classe-e-identita); ruoli:
[Provisioning ruoli DB](/dev/backend/provisioning-db-roles).

Il parametro di sessione `row_security` (default `on`) permette a superuser o owner
di forzare il comportamento: `SET row_security = off` causa errore se una query
incontra una policy (utile per debug, **mai** in produzione).

---

### Troubleshooting

#### Policy "silent" che nasconde righe senza errore

Il rischio principale di RLS: **una query ritorna 0 righe invece di un errore**.
Senza conoscere la policy, il bug sembra un problema di dati.

Strategie di debug:

1. **Verifica lo stato RLS**:

   ```sql
   SELECT schemaname, tablename, rowsecurity, forcerowsecurity
     FROM pg_tables
    WHERE schemaname = 'vendite' AND tablename = 'fatture';
   ```

2. **Elenca le policy installate**:

   ```sql
   SELECT polname, polcmd, polroles, polqual, polwithcheck
     FROM pg_policy p
     JOIN pg_class c ON c.oid = p.polrelid
    WHERE c.relname = 'fatture';
   ```

3. **Simula un ruolo** in una sessione di test:

   ```sql
   SET ROLE zeroerp_app;
   SET app.current_identita_id = '42';
   SELECT COUNT(*) FROM vendite.fatture;
   RESET ROLE;
   ```

4. **Debug con `EXPLAIN`**: le policy appaiono come filtri nel piano:

   ```sql
   EXPLAIN (ANALYZE, VERBOSE)
   SELECT * FROM vendite.fatture;
   ```

   Cercare nel piano righe come `Filter: script.fn_scope_ba_ownership(...)`.

5. **Temporaneo per superuser** (solo debug, mai in produzione):

   ```sql
   SET row_security = off;  -- da superuser: errore se incontra policy
   ```

#### Policy troppo restrittiva (falso negativo)

Se una policy ritorna sempre false per un utente che dovrebbe vedere la riga:

* Controllare che il GUC sia popolato (`SHOW app.current_identita_id;`)
* Verificare con `SELECT` diretta della funzione di scope, passando i parametri attesi
* Ricordare che `current_setting(..., true)` ritorna stringa vuota, non `NULL`,
  quando il GUC manca — se la funzione di scope non gestisce il caso, fallisce silente

#### `ERROR: new row violates row-level security policy`

Errore tipico di `WITH CHECK`: l'utente tenta di inserire o aggiornare una riga in uno
stato fuori dal proprio scope. Diagnosi: stampare i valori della riga e confrontarli
con il GUC dell'utente corrente.

---

### Performance

Le policy RLS diventano parte della query e vengono ottimizzate insieme al resto del piano.
Non c'e' overhead "magico" — ma ci sono alcune insidie:

#### Funzioni in policy: sempre `STABLE` o `IMMUTABLE`

Una funzione `VOLATILE` **non puo'** essere inlineata dal planner. Le funzioni
`script.fn_scope_*` devono essere:

* `STABLE`: se leggono tabelle ma non modificano nulla (tipico)
* `IMMUTABLE`: se calcolano solo dai parametri (raro nello scope)

```sql
CREATE FUNCTION script.fn_scope_ba_ownership(...)
RETURNS BOOLEAN
LANGUAGE sql
STABLE             -- <-- obbligatorio per performance
AS $$ ... $$;
```

Una funzione `STABLE` scritta in `LANGUAGE sql` (non plpgsql) e con una singola query
e' candidata all'**inlining**: il planner la sostituisce in-place con il suo corpo,
ottenendo lo stesso piano di una WHERE scritta a mano.

#### Indici funzionali sulle colonne scope

Se la policy filtra su una colonna con funzione (es. `lower(email)`), serve un indice
funzionale corrispondente. Per colonne scope tipiche (`billing_account_id`,
`emittente_soggetto_ruolo_id`) basta un indice B-tree standard, gia' coperto dalla policy
FK automatica ZeroErp (`dbops.fk_index_policy`).

#### Misurare l'effetto di una policy

Una policy si paga a ogni riga letta, e cambia le strade che il planner può usare:
sotto RLS entrano nell'indice solo le condizioni leakproof. Si misura **come
applicazione**, mai da owner, e la cura si scrive sulla forma della query, non su
una soglia di tempo. Regole: [linee-guida-sql §8.5-bis e §13](/linee-guida-sql#13-prestazioni-la-forma-di-funzioni-e-query);
metodo: [Un database che resta veloce](/guide/database-che-resta-veloce).

---

### Convivenza con Viste e `SECURITY DEFINER`

#### Viste

Una vista eredita le policy RLS delle tabelle sottostanti **solo se** creata da un
utente non-owner oppure se la vista e' `security_invoker = true` (PostgreSQL 15+).

```sql
CREATE VIEW vendite.vw_fatture_cliente
WITH (security_invoker = true)
AS SELECT * FROM vendite.fatture;
```

Senza `security_invoker`, la vista gira con i permessi del creatore e bypassa le policy
di chi la interroga. In ZeroErp: **tutte** le viste che coprono tabelle con RLS devono
avere `security_invoker = true`. Quelle senza vanno considerate un bug.

#### Funzioni `SECURITY DEFINER`

Una funzione `SECURITY DEFINER` gira con i privilegi del **definitore**, non del chiamante.
Questo significa che **bypassa le policy RLS del chiamante** e applica invece quelle del
definitore (o nessuna, se il definitore e' owner).

Usarla con cautela in contesti scope-sensitive:

* Preferire `SECURITY INVOKER` (default) nelle funzioni di dominio.
* Se serve `SECURITY DEFINER` (es. per audit cross-schema), documentare **esplicitamente**
  perche' si sta bypassando RLS e proteggere la funzione con controlli equivalenti dentro
  al suo corpo.

#### CTE (`WITH ...`)

Le CTE non aggirano RLS: la policy si applica alla tabella base, non alla CTE.

---

### Comandi Utili

```sql
-- Elenco tabelle con RLS abilitato
SELECT schemaname, tablename, rowsecurity, forcerowsecurity
  FROM pg_tables
 WHERE rowsecurity = true
 ORDER BY schemaname, tablename;

-- Elenco policy installate
SELECT n.nspname AS schema,
       c.relname AS table,
       p.polname AS policy,
       p.polcmd  AS command,
       pg_get_expr(p.polqual, p.polrelid) AS using_expr,
       pg_get_expr(p.polwithcheck, p.polrelid) AS with_check_expr
  FROM pg_policy p
  JOIN pg_class c ON c.oid = p.polrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 ORDER BY schema, table, policy;

-- Ruoli con BYPASSRLS
SELECT rolname, rolbypassrls
  FROM pg_roles
 WHERE rolbypassrls = true
 ORDER BY rolname;
```

---

### Best Practices ZeroErp (sintesi)

1. Attivare RLS solo su tabelle con scope multi-soggetto evidente.
2. Una policy per scope, nominata `rls_<tabella>_<scope>`.
3. Logica **sempre** in funzione `script.fn_scope_*`, mai inline.
4. Funzioni `STABLE` in `LANGUAGE sql` per favorire inlining.
5. Parametri dai GUC `app.*`, letti dalla policy e passati alla funzione.
6. Per il ruolo applicativo (`zeroerp_app`, non-owner `NOBYPASSRLS`) basta `ENABLE`; `FORCE` solo se e' l'owner a fare DML (non e' il caso ZeroErp a runtime).
7. Nessun `BYPASSRLS`: fuori dalla RLS resta solo il proprietario delle tabelle (`zeroerp_owner`: migrazioni e manutenzione), perché ne è il proprietario. I processi automatici sono filtrati come l'applicazione.
8. `WITH CHECK` **esplicito**: una policy che copre la scrittura va `FOR ALL` (o `FOR INSERT`/`FOR UPDATE`) con `WITH CHECK`. Una sola `FOR SELECT` su tabella `ENABLE`d **blocca ogni INSERT/UPDATE** ("new row violates row-level security policy").
9. Viste con `security_invoker = true`.
10. Test pgTAP obbligatori: visibile / non visibile / senza GUC / bypass / check bloccante.

Riferimento operativo completo: [Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).

---

---
{% include-markdown "signature-core.md" %}
