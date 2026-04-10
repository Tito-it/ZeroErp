# fn_get_user_object_permissions_map

## Scopo

Restituisce la mappa completa degli override oggetto attivi per un utente.
La chiave JSONB e' `app_label.model_name`, il valore e' il livello di accesso
configurato su `config.user_override_oggetti`.

## Schema

`script`

## Firma

```sql
script.fn_get_user_object_permissions_map(
    p_auth_user_id  anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:------------:|-------------|
| `p_auth_user_id` | `risorse_umane_auth_user.auth_user_id%TYPE` | Si | ID utente Django (`auth_user.id`) |

## Caratteristiche

- **STABLE**: solo lettura
- **SECURITY INVOKER**: esegue con i permessi del chiamante
- Guard: `p_auth_user_id` obbligatorio e `> 0`

## Output

JSONB nel formato:

```json
{
  "anagrafiche.conto_bancario": "BLOCCATO",
  "vendite.fattura": "LETTURA"
}
```

Se non esistono override attivi, ritorna:

```json
{}
```

## Logica

1. Valida `p_auth_user_id`
2. Legge `config.user_override_oggetti`
3. Filtra solo gli override attivi alla `CURRENT_DATE`
4. Aggrega con `jsonb_object_agg(app_label || '.' || model_name, livello::text)`
5. Se il risultato e' nullo, ritorna `'{}'::jsonb`

## Filtro validita' temporale

Sono inclusi solo gli override che rispettano entrambe le condizioni:

```sql
(valido_dal IS NULL OR valido_dal <= CURRENT_DATE)
AND (valido_al IS NULL OR valido_al >= CURRENT_DATE)
```

Override futuri o scaduti vengono ignorati.

## Dipendenze

- `config.user_override_oggetti`

## Integrazione con fn_get_user_profile

La funzione viene chiamata da `fn_get_user_profile` per popolare
la chiave `permessi_oggetto` del profilo utente.

## Note

- La funzione restituisce solo gli **override espliciti attivi**
- Non calcola il livello effettivo finale per tutti i model del sistema
- Per il livello effettivo di un singolo model resta il resolver
  `script.fn_resolve_livello_oggetto(...)`

## Esempi

```sql
-- Mappa completa override oggetto
SELECT script.fn_get_user_object_permissions_map(1);

-- Lettura di una chiave specifica
SELECT (script.fn_get_user_object_permissions_map(1))->>'vendite.fattura';

-- Uso indiretto nel profilo
SELECT script.fn_get_user_profile(1);
```
