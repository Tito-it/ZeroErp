# Brief DB — Valuta su offerte commerciali + contratti (simmetria preventivi)

> **Status**: ✅ APPLICATO 2026-05-29 su `dev/db-tid` — con rettifiche rispetto al brief originale (vedi sezione finale).
> **Target team**: DB (`dev/db-tid`)
> **Origine**: simmetria UI/modello con `vendite.preventivi` (che ha già `valuta_id`)
> **No produzione**: breaking change ammessi (memoria `project_no_produzione_solo_sviluppo`)

---

## Richiesta

Portare `vendite.offerte_commerciali` e `vendite.contratti` allo stesso modello valuta di `vendite.preventivi`:

- Aggiungere colonna **`valuta_id`** su:
  - `vendite.offerte_commerciali`
  - `vendite.contratti`
  - Tipo: `integer`, NULL ammesso (può essere risolto runtime dal BB `resolve_valuta_default` BE se non passato esplicitamente).
  - FK a `config.valute(id)`.
  - Indice FK secondo policy `dbops.apply_fk_index_policy` (registrazione in `dbops.fk_index_policy` se necessario).
- **Backfill** record esistenti: popolare retroattivamente con la valuta default risolta dal BA (catena standard: BA → EF del BA → EF utente_insert → fallback parameter, allineato al resolver BE). Update massivo via SQL.
- **Trigger seed all'INSERT** (`_a*_set_valuta_default`): se `valuta_id IS NULL`, valorizzare automaticamente dal BA via stessa catena DB-side (vedi sotto). Pattern simmetrico ai trigger di seed esistenti su `preventivi`.

## Trigger seed: catena di risoluzione DB-side

Mirror della funzione `apps.anagrafiche.services.valuta_resolver.resolve_valuta_default` BE, da implementare come fn PL/pgSQL `anagrafiche.fn_resolve_valuta_default(p_billing_account_id, p_user_id) RETURNS integer`. Catena:

1. `billing_account.valuta_id` se valorizzato
2. Valuta dell'EF del BA (via `fn_get_emittente_fiscale_pk(p_billing_account_id)` → `emittenti_fiscali.valuta_id`)
3. Valuta dell'EF dell'utente operatore (via `fn_resolve_emittente_for_user(p_user_id)` → `emittenti_fiscali.valuta_id`)
4. **Fallback parameter** `VENDITE_VALUTA_DEFAULT` (`config.parameters`) — anche il BE resolver verrà esteso con questo livello, vedi bug noto sotto.

`p_user_id` derivato da GUC `app.current_user_id` (allineato ai trigger emittente esistenti).

## Motivazione

Oggi su `offerte_commerciali` e `contratti` la valuta non è persistita. Conseguenze:
- Lato API: l'envelope detail non espone `valuta_id`/`valuta_codice` → la UI mostra un drawer senza select valuta (asimmetria con preventivi).
- Lato dominio: non c'è source-of-truth della valuta sul documento per i calcoli totali / pricing in caso di multi-valuta futuro.
- Lato auditing: variazione del default valuta dell'EF nel tempo non lascia traccia sull'offerta/contratto (la valuta fissata al CREATE deve essere immutabile come avviene su preventivi).

## Fuori scope

- Modifiche a `offerte_commerciali_eccezioni`, `contratti_righe` o tabelle di pricing (la valuta sta solo in testata).
- Conversioni multi-valuta runtime (non richieste).
- Aggiornamento simmetrico su `ordini`/`ddt`/`fatture` (già tutti dotati di `valuta_id`).

## Bug noto (BE) da fixare in parallelo

Il BB `resolve_valuta_default` ([backend/apps/anagrafiche/services/valuta_resolver.py:46](../../../backend/apps/anagrafiche/services/valuta_resolver.py)) ha solo 3 livelli (BA → EF del BA → EF utente). **Manca il livello 4 = lookup parameter** (es. `VENDITE_VALUTA_DEFAULT`): se nessuno dei 3 livelli risolve la valuta, ritorna `{}` e la UI preventivi resta vuota. Il fix BE va fatto contestualmente alla fn DB `fn_resolve_valuta_default` (entrambi vanno allineati sui 4 livelli, decisione coerente cross-layer).

---

*Brief DB sintetico — dettaglio implementativo (nome migration, naming trigger `_a*_set_valuta_default_ins`, test pgTAP, ordine apply, registrazione `fk_index_policy`) a discrezione del team DB.*

---

## Rettifiche finali (handoff team DB → BE, 2026-05-29)

Il team DB ha applicato il brief con queste **differenze** rispetto al testo sopra:

| Punto brief originale | Decisione team DB | Razionale |
| --- | --- | --- |
| Nuova fn `anagrafiche.fn_resolve_valuta_default` con 4 livelli | **Riusato `vendite.fn_get_valuta_id` esistente** (catena `BA → emittente → gestore`) | Single source of truth, niente duplicazione |
| Livello 4 = parameter `VENDITE_VALUTA_DEFAULT` | **Niente parameter lato DB**: `config.parameters.default_value` è NOT NULL; un parametro valorizzato impedirebbe il `RAISE E_CONFIG_MANCANTE` rompendo la pipeline `attivita_fatturabili` e i test esistenti | Il fallback gestore copre già il ruolo di default di sistema → livello parameter ridondante |
| Trigger legge GUC `app.current_user_id` per derivare EF utente | **Niente**: l'emittente è già sul record (risolto dal trigger emittente che esegue **prima**) | Il livello "EF-utente" è già gestito a monte dalla catena emittente |
| Nuovo trigger `_a*_set_valuta_default_ins` | **Sì applicato** su `offerte_commerciali` e `contratti` | Pattern simmetrico ai trigger emittente esistenti |

### Catena finale DB (single source of truth)

```text
1) billing_account.valuta_id
2) emittenti_fiscali.valuta_id (emittente del record, già risolto)
3) anagrafiche.gestori.valuta_id (primo per id)
4) RAISE E_CONFIG_MANCANTE
```

### Allineamento BE

Il BB Python `resolve_valuta_default` è stato allineato alla catena DB sostituendo il livello 4 "parameter `DEFAULT_VALUTA`" (mai applicato) con il **livello 4 = fallback gestore** (query diretta `SELECT ... FROM anagrafiche.gestori ORDER BY id LIMIT 1` con JOIN `config.valute`). Niente raise BE (la valuta default è opzionale per form-defaults — il caller decide cosa fare con `{}`).

Catena BE risultante:

```text
1) ba.valuta_id (livello 1 DB)
2) EF-del-BA.valuta_id  (livello 2 DB via BillingAccountRepository.get_emittente_valuta)
3) EF-utente.valuta_id  (proxy del livello 2 DB quando il documento non esiste ancora — solo BE form-defaults)
4) anagrafiche.gestori.valuta_id (livello 3 DB)
5) {} (no raise — equivalente fail-soft del RAISE DB)
```

### Stato lato BE

- [x] Livello 4 BE = fallback gestore applicato ([apps/anagrafiche/services/valuta_resolver.py](../../../backend/apps/anagrafiche/services/valuta_resolver.py))
- [x] Test resolver aggiornati (10 test, livello 4 mockato via `connection.cursor`)
- [x] Test downstream `vendite_form_defaults_service` aggiornati
- [ ] Repository/service `offerte`+`contratti` per persistere/leggere `valuta_id` (work in progress)
- [ ] FE: select valuta nei 2 drawer (post-BE)
