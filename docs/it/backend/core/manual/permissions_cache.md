# permissions_cache (Core Django)

## Scopo

Cache Redis L2 per i permessi utente. Integra la cache per-request (L1 dict) con Redis (L2)
per evitare query DB su ogni richiesta HTTP.

## Contesto

Modulo in `apps/core/services/permissions_cache.py`.
Utilizzato da `ZeroERPPermission` per pre-popolare la cache per-request da Redis
e persistere i risultati della risoluzione dopo il primo calcolo.

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
- `invalidate_department(uo_id)` cerca gli utenti del reparto sulla madre — `RisorseUmane` (l'UO) → `IdentitaDigitale` per `soggetto_ruolo_id` → `auth_user_id` — e invalida ciascuno. ⚠️ Fino al 2026-09-12 passava dal model della vista col nome vecchio del ponte RU↔utente, ritirato (analisi-software-per-dati-morti §2.1)
- `invalidate_all()` usa `cache.delete_pattern()` (supportato da `django-redis`)

## Dipendenze DB

| Tabella                                | Uso                                      |
|----------------------------------------|------------------------------------------|
| `anagrafiche.risorse_umane` + `anagrafiche.identita_digitali` | Lookup utenti per invalidazione reparto (UO → `soggetto_ruolo_id` → `auth_user_id`) |

## Integrazione con ZeroERPPermission

1. `_get_cache()` — tenta `load_user_cache()` per pre-popolare L1 da Redis
2. Dopo la risoluzione permessi — `_save_cache_to_redis()` persiste L1 su Redis se ci sono stati cambiamenti
3. Flag `request._zeroerp_perms_cache_loaded_from_redis` evita scritture inutili quando L2 era gia` popolato

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

`apps/core/tests/services/test_permissions_cache.py` — 7 test unitari con mock Redis.
