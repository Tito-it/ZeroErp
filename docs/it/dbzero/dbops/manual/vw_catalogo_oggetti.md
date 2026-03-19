## 📘 Documentazione Concettuale – View `dbops.vw_catalogo_oggetti`

> 👀 **Vedi anche**
>
Sistema di catalogazione cataloghi di sistema (`pg_class`, `pg_namespace`)
> Schema `dbops` e schema `script`

La view **`dbops.vw_catalogo_oggetti`** fornisce un elenco centralizzato degli oggetti presenti negli schemi **`dbops`** e **`script`**, includendo tabelle, viste, indici, sequenze, materialized views e funzioni, con informazioni sul tipo, sul proprietario e sulla descrizione.

---
### 🎯 Scopo Principale
* Offrire una vista unificata degli oggetti PostgreSQL definiti nei due schemi principali di amministrazione.
* Agevolare operazioni di discovery e auditing, bypassando query dirette sulle catalog tables.

---

### Definizione (DDL)

```sql
CREATE OR REPLACE VIEW dbops.vw_catalogo_oggetti AS
SELECT
  n.nspname            AS schema,
  c.relkind            AS tipo_oggetto,
  c.relname            AS nome_oggetto,
  CASE c.relkind
    WHEN 'r' THEN 't'  -- table
    WHEN 'v' THEN 'v'  -- view
    WHEN 'm' THEN 'm'  -- materialized view
    WHEN 'i' THEN 'i'  -- index
    WHEN 'S' THEN 's'  -- sequence
    WHEN 'f' THEN 'f'  -- function
    ELSE c.relkind
  END                   AS tipo_descrizione,
  pg_roles.rolname      AS proprietario,
  obj_description(c.oid, 'pg_class') AS descrizione
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_roles ON pg_roles.oid = c.relowner
WHERE n.nspname = ANY (ARRAY['dbops', 'script']);
```

**Owner**: `postgres`

**Commento**: "Vista degli oggetti presenti negli schemi dbops,script (tabelle, viste, sequenze, indici ecc.)"

---

### Colonne e Significato

| Colonna            | Descrizione                                                                  |
| ------------------ | ---------------------------------------------------------------------------- |
| `schema`           | Nome dello schema in cui risiede l’oggetto (`dbops` o `script`).             |
| `tipo_oggetto`     | Codice interno (`relkind`) che indica il tipo: `r`, `v`, `m`, `i`, `S`, `f`. |
| `nome_oggetto`     | Nome dell’oggetto nel catalogo (`relname`).                                  |
| `tipo_descrizione` | Versione sintetica del tipo (stessa lettera) per filtro più leggibile.       |
| `proprietario`     | Utente/role che possiede l’oggetto (`rolname`).                              |
| `descrizione`      | Commento associato all’oggetto, se presente (da `obj_description`).          |

---

### Esempi di Utilizzo

1. **Elencare tutte le tabelle** dei due schemi:

   ```sql
   SELECT nome_oggetto, descrizione
     FROM dbops.vw_catalogo_oggetti
    WHERE tipo_oggetto = 'r';
   ```

2. **Filtrare le view** (oggetti di tipo `v`) e mostrarne il proprietario:

   ```sql
   SELECT schema, nome_oggetto, proprietario
     FROM dbops.vw_catalogo_oggetti
    WHERE tipo_oggetto = 'v'
      AND schema = 'dbops';
   ```

3. **Trovare oggetti senza descrizione** (per manutenzione commenti):

   ```sql
   SELECT schema, nome_oggetto
     FROM dbops.vw_catalogo_oggetti
    WHERE descrizione IS NULL;
   ```

---

### Vantaggi Operativi

* **Rapidità di analisi**: evita join viewsi su `pg_class`, `pg_namespace` e `pg_roles`.
* **Auditing e documentazione**: consente di scoprire oggetti orfani o privi di commento.
* **Scripting**: facilita la generazione di report ad-hoc sul catalogo di sistema.

---

> **“Una view di catalogo centralizzato semplifica il discovery e il governo degli oggetti di database, favorendo manutenzione e compliance.”**
