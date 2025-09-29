## 📌 Funzione `dbops.fn_set_gucs_conn`

### 🎯 Scopo Principale

La funzione `dbops.fn_set_gucs_conn` serve a impostare in modo centralizzato le **GUC (Grand Unified Configuration)** custom di PostgreSQL per la **connessione corrente**.
Queste variabili sono usate da trigger, funzioni e policy RLS per conoscere l’utente applicativo e il contesto di esecuzione (es. sessione Django, gruppi, tenant).

> ✅ Tutti gli sviluppatori devono utilizzare questa funzione ogni volta che viene stabilita una connessione applicativa (es. tramite middleware Django), evitando di eseguire `SET` manuali.

---

### 🔑 Parametri

| Parametro       | Tipo    | Descrizione                                                         |
| --------------- | ------- | ------------------------------------------------------------------- |
| `p_user_id`     | `int`   | ID dell’utente Django (se autenticato).                             |
| `p_session_key` | `text`  | Chiave della sessione applicativa (es. cookie sessionid in Django). |
| `p_group_ids`   | `int[]` | Array con gli ID dei gruppi a cui appartiene l’utente.              |

---

### 📤 Output

* **Nessun valore di ritorno**.
* Imposta le GUC per la sessione DB corrente:

  * `app.user_id`
  * `app.session_key`
  * `app.group_ids`

---

### 🚀 Modalità d’Uso

### In SQL (debug/test)

```sql
SELECT dbops.fn_set_gucs_conn(42, 'abc123', ARRAY[1,2,3]);

SELECT current_setting('app.user_id', true);
-- 42
```

### In Django (middleware)

```python
from django.db import connection

def set_gucs(get_response):
    def middleware(request):
        if request.user.is_authenticated:
            with connection.cursor() as c:
                c.execute("SELECT dbops.fn_set_gucs_conn(%s, %s, %s)", [
                    request.user.id,
                    request.session.session_key,
                    list(request.user.groups.values_list("id", flat=True))
                ])
        return get_response(request)
    return middleware
```

---

### 📚 Collegamenti con altre componenti

* **`script.fn_get_parameter_full`**: utilizza le GUC `app.user_id` e `app.group_ids` per determinare l’override dei parametri.
* **Trigger di audit (`script.trgfn_upd_audit_data_user_generic`)**: può leggere `app.user_id` per valorizzare i campi `user_update`.
* **Row-Level Security (RLS)**: le policy possono basarsi su `current_setting('app.user_id', true)` per filtrare i dati per utente.

---

### ⚠️ Note Importanti

* La funzione va chiamata **a ogni nuova connessione DB**: se usi un connection pool (es. PgBouncer), assicurati che il middleware Django la riesegua al checkout della connessione.
* Le GUC impostate sono **per-connessione**, non persistono dopo il `DISCONNECT`.
* Non usare mai `SET app.*` manuali → centralizza sempre con questa funzione.
* In ambienti multi-tenant potrai estendere la funzione con un parametro `p_tenant_id`.
