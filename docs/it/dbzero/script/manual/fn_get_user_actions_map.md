# fn_get_user_actions_map

## Scopo

Ritorna la mappa completa delle azioni di processo abilitate/disabilitate
per un utente, in un singolo roundtrip DB.
Gemella di `fn_get_user_permissions_map` (che mappa le aree funzionali).

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

## Logica

1. Guard: `p_auth_user_id` obbligatorio e > 0
2. Loop su `config.azioni_processo` dove `attivo = TRUE`
3. Per ogni azione, chiama `script.fn_check_azione_processo(p_auth_user_id, permission_codename)`
4. Compone JSONB `{codename: true/false, ...}`

## Catena di risoluzione (delegata a fn_check_azione_processo)

1. `ruolo_sistema`: DISABILITATO → false, ADMIN → true
2. Override utente azione (se presente e valido)
3. Profilo reparto azione (ereditato dall'UO)
4. Default → false (negata)

## Esempio di output

```json
{
  "genera_fatture_lotti": true,
  "reset_lotto_draft": false,
  "approva_rimessa": true,
  "annulla_fattura": false
}
```

## Dipendenze

- `config.azioni_processo` — tabella azioni registrate
- `script.fn_check_azione_processo` — risoluzione singola azione

## Integrazione in fn_get_user_profile

Chiamata nel punto 5 (composizione risultato) per popolare la chiave `azioni_abilitate`:

```sql
v_result := jsonb_build_object(
    ...
    'permessi_area',     script.fn_get_user_permissions_map(p_auth_user_id),
    'azioni_abilitate',  script.fn_get_user_actions_map(p_auth_user_id)
);
```

## Caching

Il risultato e' cacheable lato Redis (L2 `permissions_cache.py`).
Se le azioni cambiano, la funzione si adatta senza toccare Python.
