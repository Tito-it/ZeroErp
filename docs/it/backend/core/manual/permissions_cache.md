# permissions_cache (Core Django)

## Scopo

Cache Redis L2 per i permessi utente. Integra la cache per-request (L1 dict) con Redis (L2)
per evitare query DB su ogni richiesta HTTP.

## Contesto

Modulo in `apps/core/services/permissions_cache.py`.
Utilizzato da `ZeroERPPermission` (e dalle permission class sorelle in
`apps/core/api/permissions.py`) per pre-popolare la cache per-request da Redis e
persistere i risultati della risoluzione. E' l'unica sede che carica la L2:
`JwtAuditMiddleware` non la precarica piu' (dal 2026-09-24), perche' gira prima
che il contesto di sessione esista.

Architettura a due livelli:

- **L1** — dict Python su `request._zeroerp_perms_cache`, vive per la singola richiesta HTTP
- **L2** — Redis via `django.core.cache`, condiviso tra richieste, TTL configurabile

## Input

- `contesto_sessione(identita_id, emittente_effettivo_id)` costruisce il **contesto**
  (`i<identita>:e<emittente>`, `e-` se l'emittente e' assente): lo chiama
  `set_jwt_gucs` e lo segna su `request._zeroerp_perms_contesto`.
- `load_user_cache(user_id, contesto)` e `save_user_cache(user_id, contesto, valori, generazioni)`
  lavorano sulla coppia (utente, contesto).
- `invalidate_user(user_id)`, `invalidate_department(uo_id)`, `invalidate_all()`.

## Output

| Funzione                | Ritorno                        |
|-------------------------|--------------------------------|
| `contesto_sessione()`   | `str` — il contesto di sessione |
| `load_user_cache()`     | `(dict | None, generazioni | None)` — valori L2 validi e generazioni correnti; generazioni `None` = Redis irraggiungibile, o generazione che la cache non conserva |
| `save_user_cache()`     | `None` — scrive su Redis con le generazioni lette al caricamento |
| `invalidate_user()`     | `None` — nuova generazione dell'utente (tutti i suoi contesti) |
| `invalidate_department()`| `None` — nuova generazione per ogni utente del reparto |
| `invalidate_all()`      | `None` — nuova generazione globale |

## Regole

- ⛔ **La chiave e' (utente, contesto di sessione)**: `perms:user:{user_id}:{contesto}`
  (con prefisso globale `zeroerp:` da settings). I valori li calcolano funzioni SQL che
  leggono le GUC `app.ruolo_applicativo` (dalla veste, cioe' dall'identita') e
  `app.current_emittente_id`: lo stesso utente ha risposte diverse in due vesti o in due
  emittenti. Il contesto usa l'emittente **effettivo** — il valore che la GUC porta, non
  il claim: un claim su un emittente disattivato lascia la GUC vuota.
- **Senza contesto la L2 non si usa**: una richiesta che non e' passata da
  `set_jwt_gucs` lavora sulla sola L1.
- **Invalidazione per generazione**: ogni voce porta le generazioni (utente, globale)
  lette **prima** di calcolarla; invalidare vuol dire cambiare generazione
  (`perms:gen:user:{user_id}`, `perms:gen:all`), e le voci vecchie non tornano valide.
  Cosi' `invalidate_user` scade tutti i contesti dell'utente senza cercarli per pattern,
  e funziona su qualunque backend di cache (anche la LocMem dei test).
  Una generazione assente non vale «nessuna»: si ricrea, e le voci scritte prima non
  tornano valide.
- TTL: `settings.PERMISSIONS_CACHE_TTL` (default 300 secondi). Le generazioni non scadono.
- Resilienza: tutte le operazioni sono wrappate in `try/except` — errori Redis non propagano eccezioni, il sistema degrada a DB-only
- `invalidate_department(uo_id)` cerca gli utenti del reparto sulla madre — `RisorseUmane` (l'UO) → `IdentitaDigitale` per `soggetto_ruolo_id` → `auth_user_id` — e invalida ciascuno, senza filtro su `attivo` o sulla veste
- `invalidate_all()` cambia la generazione globale. Oggi non ha chiamanti.
  ⚠️ Fino al 2026-09-24 usava `cache.delete_pattern()` con un pattern costruito a mano
  col prefisso, che `django-redis` aggiunge da se': non cancellava niente (S-3 della
  [analisi difetti](../../../dev/work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md)).

## Dipendenze DB

| Tabella                                | Uso                                      |
|----------------------------------------|------------------------------------------|
| `anagrafiche.risorse_umane` + `anagrafiche.identita_digitali` | Lookup utenti per invalidazione reparto (UO → `soggetto_ruolo_id` → `auth_user_id`) |

## Integrazione con ZeroERPPermission

1. `_get_cache()` — se L1 non esiste e la richiesta ha il contesto
   (`request._zeroerp_perms_contesto`), tenta `load_user_cache()` per pre-popolarla da Redis
   e ricorda il contesto, le generazioni lette e il numero di voci caricate. Si salva
   sempre nel contesto del caricamento, anche se a meta' richiesta le GUC si riaprono in un altro.
2. Nel `finally` del controllo permessi — `_save_cache_to_redis()` salva L1 su Redis
   **solo se la richiesta ha aggiunto voci**. Riscrivere una voce letta e invariata
   rinnoverebbe il TTL a ogni richiesta: fino al 2026-09-24 succedeva, e per un utente
   attivo la voce non scadeva mai.
3. L1 contiene i risultati di `PermissionResolver` (ruolo applicativo, super admin,
   livelli area/oggetto, azioni, scope emittente, ...).

⚠️ Fino al 2026-09-24 la chiave era `perms:user:{user_id}`: un utente con due vesti, o che
cambiava emittente attivo, riceveva livelli e perimetro dell'altro contesto (M-1 della
[analisi difetti](../../../dev/work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md)).

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

- `apps/core/tests/services/test_permissions_cache.py` — contratto su una cache vera
  (LocMem): contesti separati, invalidazione per utente/reparto/globale, invalidazione a
  meta' richiesta, generazione sfrattata.
- `apps/core/tests/api/test_permissions_cache_richiesta.py` — percorso della richiesta:
  niente L2 senza contesto, niente riscrittura di una voce invariata.
- `apps/core/tests/api/test_jwt_audit_authentication.py` (test 13) — il contesto nasce
  dall'emittente effettivo della GUC.
