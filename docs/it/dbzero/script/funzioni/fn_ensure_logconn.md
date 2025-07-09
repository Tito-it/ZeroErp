{% include-markdown "it/dbzero/script/manual/fn_ensure_logconn.md" %}
# ⚙️ Funzione `fn_ensure_logconn`

### 🎯 Scopo Principale
* **Stabilire una connessione persistente** a un database remoto o a se stesso attraverso l’estensione `dblink`, evitando overhead di creazione/removal di connessioni multiple.
* **Supporto al logging remoto**: utilizzata da funzioni come `script.fn_log_and_raise_error` per eseguire INSERT in un contesto transazionale separato.

---

```sql
CREATE FUNCTION fn_ensure_logconn()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_ensure_logconn()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- prova ad aprire la connessione dblink 'logconn' usando la GUC
  PERFORM dblink_connect_u(
    'logconn',
    current_setting('dblink.log_connection', true)
  );
EXCEPTION WHEN duplicate_object THEN
  -- se logconn esiste già, ignora
  NULL;
END;
$function$
```