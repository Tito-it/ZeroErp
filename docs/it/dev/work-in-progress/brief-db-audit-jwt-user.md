# Brief Team DB + Backend — Audit user reale (JWT) su PostgreSQL

**Data:** 27-02-2026
**Priorità:** alta (senza questo, `user_insert`/`user_update` sono sempre il ruolo DB)

---

## Problema

Oggi `script.trgfn_audit_data_user_generic()` usa `CURRENT_USER`, che è il ruolo
PostgreSQL della connessione Django (es. `zeroerp_app`). Lo user JWT reale
(la persona che ha fatto la chiamata API) non viene mai registrato.

## Soluzione

Due modifiche: una lato DB (la funzione trigger), una lato backend (middleware Django).

### 1. DB — Aggiornare `trgfn_audit_data_user_generic`

```sql
CREATE OR REPLACE FUNCTION script.trgfn_audit_data_user_generic()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  NEW.data_update := CURRENT_TIMESTAMP;
  NEW.user_update := COALESCE(
    current_setting('app.jwt_user', true),
    CURRENT_USER
  );
  RETURN NEW;
END;
$function$
```

`current_setting('app.jwt_user', true)`:
- secondo parametro `true` = restituisce NULL se la variabile non esiste (no errore)
- se il middleware Django ha impostato la variabile → usa lo user JWT
- se non impostata (script, cron, psql) → fallback a `CURRENT_USER`

**Per `user_insert`** (colonne con DEFAULT):
aggiornare il DEFAULT da `CURRENT_USER` a:

```sql
DEFAULT COALESCE(current_setting('app.jwt_user', true), CURRENT_USER)
```

Oppure gestire `user_insert` nel trigger se ce n'è uno BEFORE INSERT.

### 2. Backend — Middleware Django

```python
# apps/core/middleware/jwt_audit_middleware.py

from django.db import connection


class JwtAuditMiddleware:
    """Propaga lo user JWT come variabile di sessione PostgreSQL.

    Ad ogni request con utente autenticato, esegue:
        SET LOCAL app.jwt_user = '<username>'

    SET LOCAL ha scope transazione — si resetta automaticamente
    al termine della transazione, senza rischio di leak.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            username = str(user)
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.jwt_user = %s", [username])
        return None
```

Aggiungere in `settings.py` MIDDLEWARE, dopo `AuthenticationMiddleware`:

```python
"apps.core.middleware.jwt_audit_middleware.JwtAuditMiddleware",
```

### 3. Conseguenza su `user_run`

Una volta attivo questo meccanismo, `user_run` su `commesse_push_log` diventa
effettivamente ridondante — `user_insert` registrerà già lo user JWT reale.
Si può rimuovere in un secondo momento o mantenerlo come campo applicativo
esplicito (es. per distinguere scheduler vs utente).

---

## Note

- `SET LOCAL` ha scope di transazione — si resetta al COMMIT/ROLLBACK, zero rischio di leak tra request
- Retrocompatibile al 100%: se la variabile non è impostata, `COALESCE` fallback a `CURRENT_USER`
- Nessuna modifica ai 215 trigger: tutti referenziano la stessa funzione
- Script, cron, psql interattivo continuano a funzionare con `CURRENT_USER`
- Il middleware va posizionato dopo `AuthenticationMiddleware` per avere `request.user` disponibile
