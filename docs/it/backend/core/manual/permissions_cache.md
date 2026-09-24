# permissions_cache (Core Django)

## Scopo

Cache Redis L2 per i permessi utente. Integra la cache per-request (L1 dict) con Redis (L2)
per evitare query DB su ogni richiesta HTTP.

## Contesto

Modulo in `apps/core/services/permissions_cache.py`.
Utilizzato da `ZeroERPPermission` (e dalle permission class sorelle in
`apps/core/api/permissions.py`) per pre-popolare la cache per-request da Redis e
persistere i risultati della risoluzione, e da `JwtAuditMiddleware.process_view`
per il pre-caricamento.

Architettura a due livelli:

- **L1** — dict Python su `request._zeroerp_perms_cache`, vive per la singola richiesta HTTP
- **L2** — Redis via `django.core.cache`, condiviso tra richieste, TTL configurabile

## Input

Tutte le funzioni accettano `user_id: int` come identificativo utente.
`save_user_cache` richiede anche il dict dei permessi risolti.

## Output

| Funzione                | Ritorno                        |
|-------------------------|--------------------------------|
| `load_user_cache()`     | `dict | None` — dati cache L2  |
| `save_user_cache()`     | `None` — scrive su Redis       |
| `invalidate_user()`     | `None` — cancella chiave       |
| `invalidate_department()`| `None` — cancella chiavi reparto |
| `invalidate_all()`      | `None` — cancella tutte le chiavi permessi |

## Regole

- Chiave Redis: `perms:user:{user_id}` (con prefisso globale `zeroerp:` da settings)
- TTL: `settings.PERMISSIONS_CACHE_TTL` (default 300 secondi)
- Resilienza: tutte le operazioni sono wrappate in `try/except` — errori Redis non propagano eccezioni, il sistema degrada a DB-only
- `invalidate_department(uo_id)` cerca gli utenti del reparto sulla madre — `RisorseUmane` (l'UO) → `IdentitaDigitale` per `soggetto_ruolo_id` → `auth_user_id` — e invalida ciascuno, senza filtro su `attivo` o sulla veste
- `invalidate_all()` usa `cache.delete_pattern()` (supportato da `django-redis`) con il
  pattern `"{KEY_PREFIX}:perms:user:*"`. Oggi non ha chiamanti.
  > ⚠️ Difetto noto (S-3): `delete_pattern` aggiunge da se' prefisso e versione, quindi
  > il pattern effettivo non corrisponde a nessuna chiave e non viene cancellato nulla.
  > Vedi [analisi difetti](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md).

## Dipendenze DB

| Tabella                                | Uso                                      |
|----------------------------------------|------------------------------------------|
| `anagrafiche.risorse_umane` + `anagrafiche.identita_digitali` | Lookup utenti per invalidazione reparto (UO → `soggetto_ruolo_id` → `auth_user_id`) |

## Integrazione con ZeroERPPermission

1. `_get_cache()` — se L1 non esiste tenta `load_user_cache()` per pre-popolarla da Redis
2. Nel `finally` del controllo permessi — `_save_cache_to_redis()` salva L1 su Redis se
   l'utente e' autenticato e il dict non e' vuoto. La condizione sul flag
   `request._zeroerp_perms_cache_loaded_from_redis` non evita la scrittura (con dict non
   vuoto e' sempre vera): L1 viene riscritta a ogni controllo e il TTL si rinnova.
3. L1 contiene i risultati di `PermissionResolver` (ruolo applicativo, super admin,
   livelli area/oggetto, azioni, ...) sotto una chiave per `auth_user`.

> ⚠️ Difetto noto (M-1): la chiave e' per `auth_user`, ma diversi valori dipendono dalla
> veste del JWT e dall'emittente attivo (letti dai GUC); inoltre la riscrittura continua
> impedisce la scadenza per un utente attivo. Vedi [analisi difetti](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md).

## Configurazione

```python
# settings.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", "redis://127.0.0.1:6379/0"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "zeroerp",
    }
}
PERMISSIONS_CACHE_TTL = int(env("PERMISSIONS_CACHE_TTL", "300"))
```

## Test

`apps/core/tests/services/test_permissions_cache.py` — test unitari con mock Redis.
