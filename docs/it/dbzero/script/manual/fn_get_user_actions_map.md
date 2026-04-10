# fn_get_user_actions_map

## Scopo

Restituisce la mappa completa delle azioni di processo abilitate o negate
per un utente, in un solo roundtrip DB.
E' la gemella di `fn_get_user_permissions_map`, ma opera sul catalogo
`config.azioni_processo`.

## Schema

`script`

## Firma

```sql
script.fn_get_user_actions_map(
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
  "genera_fatture_lotti": true,
  "reset_lotto_draft": false,
  "run_commesse_push": true
}
```

## Logica

1. Valida `p_auth_user_id`
2. Legge una sola volta il contesto utente:
   `ruolo_sistema` + `unita_organizzativa_id`
3. Esegue una query set-based su `config.azioni_processo`
4. Applica la catena di risoluzione con `LEFT JOIN` su:
   `config.user_override_azioni` e `config.profili_reparto_azioni`
5. Compone il risultato con `jsonb_object_agg`

## Catena di risoluzione

```text
1. ruolo_sistema:
   - NULL / DISABILITATO -> false
   - ADMIN -> true
2. Override utente azione (se presente e valido)
3. Profilo reparto azione (ereditato dalla UO)
4. Default -> false
```

## Ottimizzazione introdotta

La versione iniziale iterava `config.azioni_processo` e chiamava
`fn_check_azione_processo` per ogni riga.

La versione corrente:

- legge `ruolo_sistema` una sola volta
- legge `unita_organizzativa_id` una sola volta
- evita il loop PL/pgSQL
- costruisce la mappa completa in forma set-based

Questo riduce il costo soprattutto quando la funzione viene richiamata
nel payload di `fn_get_user_profile`.

## Dipendenze

- `config.azioni_processo`
- `config.user_override_azioni`
- `config.profili_reparto_azioni`
- `anagrafiche.risorse_umane_auth_user`
- `anagrafiche.risorse_umane`

## Integrazione con fn_get_user_profile

La funzione popola la chiave `azioni_abilitate` nel JSONB del profilo utente:

```sql
v_result := jsonb_build_object(
    ...,
    'permessi_area',     script.fn_get_user_permissions_map(p_auth_user_id),
    'azioni_abilitate',  script.fn_get_user_actions_map(p_auth_user_id)
);
```

## Esempi

```sql
-- Mappa completa azioni
SELECT script.fn_get_user_actions_map(1);

-- Verifica singola chiave del JSONB
SELECT (script.fn_get_user_actions_map(1))->'genera_fatture_lotti';

-- Uso indiretto nel profilo
SELECT script.fn_get_user_profile(1);
```
