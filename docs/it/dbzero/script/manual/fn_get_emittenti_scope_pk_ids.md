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

1. **Super admin?** — `script.fn_is_super_admin(p_auth_user_id)`. Se si → `NULL` (no restriction).
2. **Veste OPERATORE utilizzabile?** — `script.fn_has_identita_attiva(p_auth_user_id, 'OPERATORE')`. Se no → ritorna `'{}'` (no access). ⭐ Dal 2026-10-18 (`20261018-22`) si chiede **dopo** il super admin: stesso esito (il super admin richiede gia' una veste OPERATORE utilizzabile), una verifica della veste invece di due.
3. **Whitelist** — lookup diretto in `config.user_emittenti_fiscali` per recuperare le PK degli emittenti associati all'utente. Whitelist vuota → `'{}'` (dal 2026-08-18, P-2a: prima `array_agg` su zero righe dava `NULL`, cioè «vede tutto»).
4. **Emittente attivo di sessione** (`app.current_emittente_id`) — l'insieme si interseca con `{attivo}`, anche quello del super admin (`NULL` ∩ `{X}` = `{X}`).

### ⭐ rev 2026-10-18 — la sede delle regole del perimetro

È diventata la **sede unica** delle regole del perimetro emittenti anche per il
database (D-3b-2, `brief-db-plancache-funzioni-con-query-incorporate`
§5quinquies):

* la canonica [`fn_check_user_emittente_scope`](fn_check_user_emittente_scope.md)
  le chiede a lei (`20261018-18`): prima le stesse regole erano scritte due
  volte;
* le policy ef_whitelist dirette la chiamano in una **sottoquery non correlata**,
  quindi **una volta per istruzione**, e passano il risultato a
  [`fn_scope_ef_perimetro`](fn_scope_ef_perimetro.md) (`20261018-19…-21`; una
  sottoquery sola da `20261018-26…-28`);
* `COST 5000` (`20261018-17`): legge vesti, binding e whitelist, ed è nominata
  dalle policy (linee-guida-sql §10.3).

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
* **STABLE**: dentro un'istruzione vede una sola fotografia. ⚠️ Non è una cache
  fra le righe: una chiamata per riga resta una chiamata per riga. «Una volta
  per istruzione» lo dà solo la sottoquery non correlata (InitPlan), come nelle
  policy.
* `COST 5000` (dal 2026-10-18).

## Dipendenze

* `script.fn_has_identita_attiva` (helper multi-face auth §4.6.B.0)
* `script.fn_is_super_admin` (helper multi-face auth)
* `config.user_emittenti_fiscali` (whitelist PK)

## Vedi anche

* [`script.fn_get_emittenti_scope_sr_ids`](/dbzero/script/funzioni/fn_get_emittenti_scope_sr_ids) — gemella, wrapper su questa, per filtri su SR id
* [`script.fn_resolve_emittente_for_user`](/dbzero/script/funzioni/fn_resolve_emittente_for_user) — resolver 1-a-1 operatore↔EF (ritorna PK)
* [Guida soggetti-e-ruoli §5b](/it/guide/soggetti-e-ruoli-anagrafici#5b-identificazione-canonica-di-un-ruolo-specializzato--pk-reale-vs-soggetto_ruolo_id) — pattern PK vs SR id
* [Brief refactor-emittente-id-canonico](/dev/work-done/refactor-emittente-id-canonico) — analisi e decisione
