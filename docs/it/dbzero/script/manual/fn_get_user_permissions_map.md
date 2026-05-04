# fn_get_user_permissions_map

## Scopo

Restituisce la mappa completa dei livelli di accesso per tutte le aree
funzionali attive in un solo roundtrip DB.
Evita chiamate ripetute dal backend e, dalla revisione `20260410-14`,
non usa piu' un loop PL/pgSQL per area.

## Schema

`script`

## Firma

```sql
script.fn_get_user_permissions_map(
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

JSONB con una chiave per ogni area funzionale attiva e valore pari al
livello effettivo risolto:

```json
{
  "anagrafiche": "TUTTO",
  "vendite": "LETTURA",
  "acquisti": "BLOCCATO",
  "catalogo": "TUTTO",
  "pagamenti": "BLOCCATO"
}
```

Valori possibili (enum `config.livello_accesso`):

- `TUTTO`
- `LETTURA`
- `BLOCCATO`

## Logica

1. Valida `p_auth_user_id`
2. Legge una sola volta il contesto utente:
   `is_super_admin` + `has_identita_attiva` + `unita_organizzativa_id`
3. Esegue una query set-based su `config.aree_funzionali`
4. Applica la catena di risoluzione con `LEFT JOIN` su:
   `config.user_override_aree` e `config.profili_accesso_aree`
   (via `fn_get_profili_accesso_applicabili`)
5. Compone il risultato con `jsonb_object_agg`

## Catena di risoluzione (post 04-05-2026 — modello legacy dismesso)

```text
1. Stato identita (multi-face native, post Fase 7 2026-04-29):
   - NOT fn_has_identita_attiva(au, 'OPERATORE') -> BLOCCATO
   - fn_is_super_admin(au) -> TUTTO
2. Override utente area (se presente e valido temporalmente)
3. Profili accesso area (AD_HOC priorita 1, REPARTO/PORTALE priorita 2)
4. Default -> BLOCCATO
```

## Ottimizzazione introdotta

La versione iniziale iterava le aree attive e chiamava il resolver area
una volta per ciascuna.

La versione corrente:

- legge `is_super_admin` + `has_identita_attiva` una sola volta (post Fase 7: era `ruolo_sistema` legacy)
- legge `unita_organizzativa_id` una sola volta
- evita il loop PL/pgSQL
- costruisce la mappa completa in forma set-based

Questo riduce il costo della funzione, soprattutto quando viene chiamata
indirettamente da `fn_get_user_profile`.

## Dipendenze

- `config.aree_funzionali`
- `config.user_override_aree`
- `config.profili_accesso`, `config.profili_accesso_aree`, `config.profili_accesso_bindings`
- `script.fn_get_profili_accesso_applicabili`
- `anagrafiche.risorse_umane_auth_user`
- `anagrafiche.risorse_umane`

## Integrazione con fn_get_user_profile

La funzione viene chiamata da `fn_get_user_profile` per popolare la chiave
`permessi_area` del profilo utente.

## Esempi

```sql
-- Mappa completa aree
SELECT script.fn_get_user_permissions_map(1);

-- Accesso a una singola area
SELECT (script.fn_get_user_permissions_map(1))->>'vendite';

-- Uso indiretto nel profilo
SELECT script.fn_get_user_profile(1);
```
