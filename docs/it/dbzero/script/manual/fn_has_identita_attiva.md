## Documentazione Concettuale – Funzione `script.fn_has_identita_attiva`

> **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
**Tabelle correlate:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
>
**Funzioni correlate:**
>
[script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin)
> [script.fn_resolve_livello_area](/dbzero/script/funzioni/fn_resolve_livello_area)
> [script.fn_get_user_profile](/dbzero/script/funzioni/fn_get_user_profile)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

La funzione **`script.fn_has_identita_attiva`** è un **helper DRY** che
incapsula il check "l'utente ha un'identità digitale attiva, nella finestra
temporale, per un dato ruolo applicativo".

Introdotta nel refactor §4.6.B.0 WIP multi-face-auth per eliminare la
duplicazione dello stesso `EXISTS` ripetuto in oltre una decina di funzioni
(`fn_resolve_livello_*`, `fn_check_*`, `fn_get_*_map`). Fra i caller
storici figurava anche `fn_get_ruolo_sistema` (wrapper retrocompat),
droppata in Fase 7 cleanup (2026-04-29).

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_auth_user_id` | `integer` | ID dell'utente Django. Fail-closed se `NULL`. |
| `p_ruolo_applicativo` | `config.ruolo_applicativo` | Ruolo dell'identità da verificare (`OPERATORE`, `CLIENTE_PORTALE`, ...). |

---

### Output

`BOOLEAN` — `true` se esiste un'identità corrispondente valida, `false`
altrimenti.

---

### Condizioni verificate

Ritorna `true` se e solo se esiste in `anagrafiche.identita_digitali` una
riga che soddisfa **tutte** le condizioni:

1. `auth_user_id = p_auth_user_id`
2. `ruolo_applicativo = p_ruolo_applicativo`
3. `attivo = true`
4. `valido_dal IS NULL OR valido_dal <= CURRENT_DATE`
5. `valido_al IS NULL OR valido_al >= CURRENT_DATE`

Fail-closed: se una qualsiasi condizione non è verificata (o se l'identità
non esiste), ritorna `false`.

---

### Regole implementative

* `LANGUAGE sql`, `STABLE`: inlineable dal planner (zero overhead rispetto
  all'implementazione inline), cache-friendly per query ripetute nella
  stessa statement.
* Nessuna variabile PL/pgSQL: un singolo `SELECT EXISTS(...)` compatto.
* `p_auth_user_id IS NULL` → `EXISTS` restituisce naturalmente `false`
  (fail-closed implicito, nessun check esplicito necessario).

---

### Parametrizzazione per ruolo

La firma prende `p_ruolo_applicativo` come parametro (anziché hardcoded
su `OPERATORE`) per permettere il riuso diretto nel refactor futuro
**§4.8** del WIP multi-face-auth: le funzioni di risoluzione permessi
dovranno valutare anche identità `CLIENTE_PORTALE`, `FORNITORE_PORTALE`
e `SHOP_CUSTOMER` sul nuovo modello `profili_accesso` generalizzato.

---

### Esempio d'uso

```sql
-- Gate fail-closed all'inizio di un resolver:
IF NOT script.fn_has_identita_attiva(
           p_auth_user_id,
           'OPERATORE'::config.ruolo_applicativo) THEN
    RETURN 'BLOCCATO'::config.livello_accesso;
END IF;
```

```sql
-- Pre-calcolo per uso ripetuto in un CASE su set:
v_has_identita := script.fn_has_identita_attiva(
                      p_auth_user_id,
                      'OPERATORE'::config.ruolo_applicativo);
-- ... poi v_has_identita viene usata nel CASE di jsonb_object_agg
```

---

### Funzioni chiamanti

Al deploy di §4.6 (PR1 DB) la helper è usata da:

* `script.fn_resolve_livello_area`
* `script.fn_resolve_livello_oggetto`
* `script.fn_check_azione_processo`
* `script.fn_check_user_emittente_scope`
* `script.fn_get_emittenti_scope_sr_ids`
* `script.fn_get_user_permissions_map`
* `script.fn_get_user_actions_map`

---

{% include-markdown "signature-core.md" %}
