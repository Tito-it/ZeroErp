# EmittenteFiscaleScopeMixin (Core Django)

## Scopo

Mixin per ViewSet e GenericAPIView che filtra automaticamente il queryset in base
agli emittenti fiscali autorizzati per l'utente corrente.

## Contesto

Classe in `apps/core/mixins.py`.
Si inserisce nella catena MRO prima della view base, sovrascrivendo `get_queryset()`.

Se l'utente non ha righe in `config.user_emittenti_fiscali`, vede tutto (nessuna restrizione).
Se ha almeno una riga, vede solo i record relativi agli emittenti autorizzati.

## Uso

```python
from apps.core.mixins import EmittenteFiscaleScopeMixin

class FattureViewSet(EmittenteFiscaleScopeMixin, ModelViewSet):
    queryset = Fattura.objects.all()
    emittente_field = "emittente_fiscale_id"
```

Per relazioni indirette (es. fattura via billing account):

```python
class AttivitaViewSet(EmittenteFiscaleScopeMixin, ModelViewSet):
    queryset = Attivita.objects.all()
    emittente_field = "billing_account__emittente_fiscale_id"
```

## Attributi

| Attributo        | Tipo         | Default | Note                                          |
|------------------|--------------|---------|-----------------------------------------------|
| `emittente_field`| string\|None | `None`  | Path al campo emittente per il filtro `__in`  |

## Logica di filtro

```text
1. Superuser?               → nessun filtro
2. emittente_field = None?   → nessun filtro
3. ruolo_sistema = ADMIN?    → nessun filtro
4. emittenti_ids = None?     → nessun filtro (whitelist vuota = tutto)
5. emittenti_ids = [1,3,5]?  → qs.filter(emittente_field__in=[1,3,5])
```

## Note

- **Non applicabile alle APIView con SQL diretto**: le view vendite attuali usano funzioni DB
  e non hanno queryset ORM. Per queste, usare `PermissionResolver.get_emittenti_sr_ids()` (ritorna
  `soggetto_ruolo_id`) nei service/repository quando il SQL filtra su `emittente_soggetto_ruolo_id`.
  Usare `get_emittenti_pk_ids()` per i filtri su `emittenti_fiscali.id` (PK).
- Il mixin utilizza la cache per-request da `request._zeroerp_perms_cache` quando disponibile.

## Dipendenze

- `PermissionResolver.is_super_admin()` — bypass SUPER_ADMIN (⚠️ fino al 2026-09-12 qui c'era `get_ruolo_sistema()`, caduta con `ruolo_sistema` in Fase 7)
- `PermissionResolver.get_emittenti_pk_ids()` — per lista PK `emittenti_fiscali.id` (l'alias `get_emittenti_ids` e' stato tolto il 2026-09-12)
- `PermissionResolver.get_emittenti_sr_ids()` — per lista `soggetto_ruolo_id` (filtri su efba)

## Test

`apps/core/tests/mixins/test_emittente_fiscale_scope.py` — 7 test unitari.
