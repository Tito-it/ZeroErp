{% include-markdown "it/dbzero/dbops/manual/fn_populate_fk_index_policy.md" %}
# ⚙️ Funzione `fn_populate_fk_index_policy`

### 🎯 Scopo Principale
* **Coerenza iniziale**
  Garantire che ogni FK rilevata nella view senza indice abbia la propria entry di policy, evitando omissioni.
* **Popolamento “a freddo”**
  Tutti i nuovi record vengono creati con `consentito = false`, lasciando in carico all’operatore la decisione di abilitare o meno l’indice.
* **Automazione**
  Riduce il lavoro manuale di inserimento di policy per nuove FKs.

---

```sql
CREATE FUNCTION fn_populate_fk_index_policy()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_populate_fk_index_policy()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  rec RECORD;
BEGIN
  FOR rec IN
    SELECT schema_name, table_name, constraint_name, create_index_suggestion  
      FROM dbops.vw_fk_senza_indice
    WHERE (schema_name, table_name, constraint_name)
      NOT IN (
        SELECT schema_name, table_name, constraint_name
          FROM dbops.fk_index_policy
      )
  LOOP
    INSERT INTO dbops.fk_index_policy(
      schema_name,
      table_name,
      constraint_name,
      consentito,
      dll_command
    ) VALUES (
      rec.schema_name,
      rec.table_name,
      rec.constraint_name,
      false,
      rec.create_index_suggestion
    );
  END LOOP;
END;
$function$
```