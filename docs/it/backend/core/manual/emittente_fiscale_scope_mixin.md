# EmittenteFiscaleScopeMixin (Core Django)

## Scopo

Mixin per ViewSet e GenericAPIView che filtra automaticamente il queryset in base
agli emittenti fiscali autorizzati per l'utente corrente.

## Contesto

Classe in `apps/core/mixins.py`.
Si inserisce nella catena MRO prima della view base, sovrascrivendo `get_queryset()`.

Il perimetro e' quello di `PermissionResolver.get_emittenti_pk_ids()`
(`script.fn_get_emittenti_scope_pk_ids`): un operatore vede solo i record degli
emittenti delle sue righe in `config.user_emittenti_fiscali`, intersecati con
l'emittente attivo se presente; **senza righe non vede nulla** (`[]`), come chi
non ha un'identita `OPERATORE` attiva. Il super admin non viene filtrato.

Oggi nessuna view usa il mixin: e' un building block disponibile, non adottato.

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
1. Superuser?                     → nessun filtro
2. emittente_field = None?         → nessun filtro
3. is_super_admin()?               → nessun filtro (esce prima di leggere lo scope)
4. get_emittenti_pk_ids() = None?  → nessun filtro
5. get_emittenti_pk_ids() = [1,3]? → qs.filter(emittente_field__in=[1,3])
   get_emittenti_pk_ids() = []?    → qs.filter(emittente_field__in=[]) = nessun record
```

## Note

- **Non applicabile alle APIView con SQL diretto**: le view vendite attuali usano funzioni DB
  e non hanno queryset ORM. Per queste, usare `PermissionResolver.get_emittenti_sr_ids()` (ritorna
  `soggetto_ruolo_id`) nei service/repository quando il SQL filtra su `emittente_soggetto_ruolo_id`.
  Usare `get_emittenti_pk_ids()` per i filtri su `emittenti_fiscali.id` (PK).
- Il mixin utilizza la cache per-request da `request._zeroerp_perms_cache` quando disponibile.
- Al passo 3 il super admin esce senza filtro: l'intersezione con l'emittente
  attivo, che `fn_get_emittenti_scope_pk_ids` applica anche al super admin, qui
  non avviene.

## Dipendenze

- `PermissionResolver.is_super_admin()` — bypass SUPER_ADMIN
- `PermissionResolver.get_emittenti_pk_ids()` — per lista PK `emittenti_fiscali.id`

## Test

`apps/core/tests/mixins/test_emittente_fiscale_scope.py` — test unitari.
