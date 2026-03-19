# fn_get_user_permissions_map

### Scopo Principale

Restituisce la mappa completa dei livelli di accesso per tutte le aree
funzionali attive, in un solo roundtrip DB. Evita N chiamate separate
da Python a `fn_resolve_livello_area`.

## Schema

`script` (funzione cross-dominio)

## Firma

```sql
script.fn_get_user_permissions_map(
    p_auth_user_id  integer
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `p_auth_user_id` | integer | - | ID utente Django (auth_user.id), obbligatorio |

## Caratteristiche

- **STABLE**: solo lettura
- **SECURITY INVOKER**: esegue con i permessi del chiamante
- Guard: `p_auth_user_id` obbligatorio e > 0

## Ritorno

JSONB con una chiave per ogni area funzionale attiva. Valore = livello accesso risolto.

```json
{
  "anagrafiche": "TUTTO",
  "vendite": "LETTURA",
  "acquisti": "BLOCCATO",
  "contabilita": "SCRITTURA",
  "magazzino": "LETTURA",
  "config": "TUTTO"
}
```

Valori possibili per ogni area (enum `config.livello_accesso`):
- `TUTTO` — accesso completo
- `SCRITTURA` — lettura + scrittura
- `LETTURA` — solo lettura
- `BLOCCATO` — nessun accesso

## Logica

1. Guard: `p_auth_user_id` non NULL e > 0
2. Loop su `config.aree_funzionali` WHERE `attiva = TRUE`, ordinato per `ordinamento`, `schema_db`
3. Per ogni area: chiama `script.fn_resolve_livello_area(p_auth_user_id, schema_db)`
4. Accumula risultato in JSONB
5. Ritorna la mappa completa

## Catena di risoluzione (delegata a fn_resolve_livello_area)

```
Per ogni area:
  1. ruolo_sistema → ADMIN = TUTTO, DISABILITATO = BLOCCATO
  2. Override utente area (config.user_override_aree) se presente e valido temporalmente
  3. Profilo reparto (config.profili_reparto_aree) ereditato dalla UO
  4. Default → BLOCCATO
```

## Dipendenze

- `config.aree_funzionali` — elenco aree attive
- `script.fn_resolve_livello_area` — risoluzione livello per singola area

## Performance

- ~10 aree attive = ~10 chiamate leggere a `fn_resolve_livello_area`
- Risultato cacheable lato Redis (`permissions_cache.py`)
- 1 roundtrip DB vs 10 chiamate separate da Python

## Integrazione con fn_get_user_profile

Questa funzione viene chiamata da `fn_get_user_profile` per popolare
la chiave `permessi_area` nel JSONB di risposta dell'endpoint `/api/v1/core/me/`.

## Esempi

```sql
-- Mappa permessi per utente con id=1
SELECT script.fn_get_user_permissions_map(1);

-- Accesso a una singola area dal risultato
SELECT (script.fn_get_user_permissions_map(1))->>'vendite';

-- Uso nel profilo utente (chiamata interna)
-- fn_get_user_profile chiama internamente fn_get_user_permissions_map
SELECT script.fn_get_user_profile(1);
-- → { ..., "permessi_area": {"anagrafiche": "TUTTO", ...} }
```
