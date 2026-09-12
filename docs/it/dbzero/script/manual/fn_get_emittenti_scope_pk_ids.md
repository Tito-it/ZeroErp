# fn_get_emittenti_scope_pk_ids

### Scopo

Funzione **canonica** per il filtro scope emittenti basato sulla **PK reale** di `anagrafiche.emittenti_fiscali`. Implementa tutti i guard del modello multi-face auth (presenza identita' OPERATORE, super admin, whitelist) e ritorna l'array di PK degli emittenti autorizzati per l'utente.

E' la fn da usare quando il filtro va su una colonna che contiene **PK reale** (es. `vw_preventivi_list.emittente_fiscale_id`, `config.parameter_overrides.emittente_fiscale_id`, `config.user_emittenti_fiscali.emittente_fiscale_id`, `vendite.preventivi.emittente_fiscale_id`).

E' la **single source of truth dei guard**: la gemella `script.fn_get_emittenti_scope_sr_ids` e' implementata come wrapper su questa.

Aggiunta nel refactor 2026-05-02 a chiusura dell'analisi pattern SR vs PK ([refactor-emittente-id-canonico](/dev/work-done/refactor-emittente-id-canonico)).

## Schema

`script`

## Firma

```sql
script.fn_get_emittenti_scope_pk_ids(
    p_auth_user_id integer
) RETURNS bigint[]
LANGUAGE plpgsql STABLE
```

## Semantica del valore di ritorno

| Valore | Significato |
| --- | --- |
| `NULL` | Nessuna restrizione: l'utente vede tutti gli emittenti (super admin) |
| `'{}'::bigint[]` | Nessun accesso. Due casi: l'utente non ha identita' OPERATORE attiva, **oppure** (dal 2026-08-18, P-2a) e' un operatore **senza riga** in `config.user_emittenti_fiscali` |
| Array di PK | Whitelist: l'utente vede solo gli emittenti elencati |

## Logica (catena di controllo)

1. **Identita' OPERATORE attiva?** — `script.fn_has_identita_attiva(p_auth_user_id, 'OPERATORE')`. Se no → ritorna `'{}'` (no access).
2. **Super admin?** — `script.fn_is_super_admin(p_auth_user_id)`. Se si → ritorna `NULL` (no restriction).
3. **Whitelist** — lookup diretto in `config.user_emittenti_fiscali` per recuperare le PK degli emittenti associati all'utente. `array_agg` su array vuoto ritorna `NULL`, che pass-through come "no restriction" (parita' semantica con `_sr_ids`).

## Filtro `ef.attivo` — non applicato

Per costruzione, ogni EF in `config.user_emittenti_fiscali` e' garantito attivo:

* `dbops.trgfn_child_requires_active_parent` su `user_emittenti_fiscali` blocca INSERT/UPDATE su EF non attivo
* `dbops.trgfn_prevent_deactivate_if_children` su `emittenti_fiscali` blocca disattivazione di EF con figli in `user_emittenti_fiscali`

Aggiungere il filtro `ef.attivo = true` qui sarebbe ridondante. Vedi commento su `script.fn_resolve_emittente_for_user` per la stessa motivazione.

## Quando usare `_pk_ids` vs `_sr_ids`

| Filtro su... | Tipo colonna | Usa fn |
| --- | --- | --- |
| `<doc>.<ruolo>_soggetto_ruolo_id` (fatture, ordini, commesse, listini, BA scope, search universale, lista clienti) | SR id (FK `soggetti_ruoli`) | `fn_get_emittenti_scope_sr_ids` |
| `<config>.<ruolo>_fiscale_id` o `<doc>.emittente_fiscale_id` (vw_preventivi_list, parameter_overrides, user_emittenti_fiscali, preventivi rev2) | PK reale (FK `emittenti_fiscali`) | `fn_get_emittenti_scope_pk_ids` |

Vedi guida [`soggetti-e-ruoli-anagrafici §5b`](/it/guide/soggetti-e-ruoli-anagrafici#5b-identificazione-canonica-di-un-ruolo-specializzato--pk-reale-vs-soggetto_ruolo_id) per la spiegazione completa del pattern duale (intenzionale, non da refattorare).

## Esempio d'uso (filtro repository BE)

```python
# preventivi_repository.py — filtro lista preventivi su PK reale
SQL = """
    SELECT * FROM vendite.vw_preventivi_list v
     WHERE (script.fn_get_emittenti_scope_pk_ids(%s) IS NULL  -- super admin
            OR v.emittente_fiscale_id = ANY(script.fn_get_emittenti_scope_pk_ids(%s)))
       AND ...
"""
cursor.execute(SQL, [auth_user_id, auth_user_id])
```

## Caratteristiche

* **Single source of truth dei guard**: `_sr_ids` delega tutti i guard a questa fn (zero drift)
* **STABLE**: cacheable nel piano di query
* **Idempotente**: `runOnChange:true` permette ridefinizioni multiple

## Dipendenze

* `script.fn_has_identita_attiva` (helper multi-face auth §4.6.B.0)
* `script.fn_is_super_admin` (helper multi-face auth)
* `config.user_emittenti_fiscali` (whitelist PK)

## Vedi anche

* [`script.fn_get_emittenti_scope_sr_ids`](/dbzero/script/funzioni/fn_get_emittenti_scope_sr_ids) — gemella, wrapper su questa, per filtri su SR id
* [`script.fn_resolve_emittente_for_user`](/dbzero/script/funzioni/fn_resolve_emittente_for_user) — resolver 1-a-1 operatore↔EF (ritorna PK)
* [Guida soggetti-e-ruoli §5b](/it/guide/soggetti-e-ruoli-anagrafici#5b-identificazione-canonica-di-un-ruolo-specializzato--pk-reale-vs-soggetto_ruolo_id) — pattern PK vs SR id
* [Brief refactor-emittente-id-canonico](/dev/work-done/refactor-emittente-id-canonico) — analisi e decisione
