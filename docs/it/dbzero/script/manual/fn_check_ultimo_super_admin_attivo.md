# fn_check_ultimo_super_admin_attivo

### Scopo

Predicato per-utente: ritorna `true` **sse** rimuovere il privilegio
`SUPER_ADMIN` da `p_auth_user_id` porterebbe il sistema a 0 super-admin
attivi (lockout).

È la primitiva alle capability `can_disable` e `can_demote_super_admin`
del [drawer Operatore](/dbzero/script/funzioni/fn_get_operatore_detail)
(P1 2026-04-29). Allinea la semantica del guard 384
(`E_PROFILO_ULTIMO_SUPER_ADMIN`) — che lavora "globale, post-transizione" —
a una **vista per-utente** consultabile a costo zero per l'UI.

> **Vedi anche**
>
> - [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> - [fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo) — check globale (no parametro), usato dai trigger
> - [fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin) — check per-utente (no lockout)

## Schema

`script` (cross-dominio: legge `anagrafiche.identita_digitali` +
`config.profili_accesso*`).

## Firma

```sql
script.fn_check_ultimo_super_admin_attivo(
    p_auth_user_id INTEGER
) RETURNS boolean
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_auth_user_id` | `INTEGER` | Sì | ID utente Django (`django.auth_user.id`). Tipo esplicito per la regola anti-pattern Liquibase/Django ordering: niente `%TYPE` su colonne `django.*`. |

## Output

| Stato rilevato | Risultato |
|---|---|
| `p_auth_user_id` è `NULL` | `false` |
| `p_auth_user_id` non è SUPER_ADMIN attivo | `false` |
| `p_auth_user_id` è SUPER_ADMIN ma esiste **almeno un altro** SUPER_ADMIN attivo | `false` |
| `p_auth_user_id` è l'**unico** SUPER_ADMIN attivo del sistema | `true` |

## Definizione: SUPER_ADMIN **senza scadenza**

Dal 07-10-2026 (decisione di Tid) «SUPER_ADMIN» qui vuol dire **senza scadenza**:
[`fn_identita_super_admin_senza_scadenza`](/dbzero/script/funzioni/fn_identita_super_admin_senza_scadenza)
(binding e profilo attivi, identità utilizzabile oggi, nessuna data di fine su veste e
rapporto, credenziale non bloccata). La funzione chiede quel building block due volte:
per l'utente in esame e per «nessun altro».

⭐ È la stessa definizione di
[`fn_check_almeno_un_super_admin_attivo`](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo),
dallo stesso building block: fino al 07-10-2026 quella guardava solo `attivo` e questa
anche la finestra, e le due funzioni dell'anti-lockout rispondevano su due regole diverse.

Conseguenza per il drawer: un amministratore che ha **già** una data di fine non è
«l'ultimo», perché spegnerlo non riduce la garanzia, e il pulsante resta acceso.

## Algoritmo

Singola valutazione boolean, senza materializzazione:

1. `p_auth_user_id IS NOT NULL`
2. `EXISTS` (target è SUPER_ADMIN senza scadenza) — short-circuit alla prima riga
3. `NOT EXISTS` (un altro auth_user è SUPER_ADMIN senza scadenza) — short-circuit
   alla prima riga "altra"

Dal 07-10-2026 i due `EXISTS` non ricopiano più un blocco di filtri: chiamano entrambi
il building block, per riga di `identita_digitali`. Il blocco duplicato «per le
prestazioni» era il punto in cui le due metà potevano divergere, e l'insieme dei
SUPER_ADMIN è piccolo.

## Caratteristiche

* `LANGUAGE sql STABLE` — read-only, cache-friendly (non inlineabile: contiene `EXISTS`).
* **Pure check**: non solleva mai eccezioni; l'enforcement resta nei
  trigger guard 384.
* Nessun riferimento a `django.*` → `LANGUAGE sql` ammesso (vedi
  [memoria pattern Liquibase ordering](/dev/work-done/refactor-operatore-emittenti#7bis6)).
* **Non GUC-aware**: la chiamata vale per qualsiasi sessione.

## Capability di drawer derivate

| Capability del drawer | Logica |
|---|---|
| `can_disable` | `NOT fn_check_ultimo_super_admin_attivo(au.id)` |
| `can_demote_super_admin` | `NULL` se non SA, altrimenti `NOT fn_check_ultimo_super_admin_attivo(au.id)` |

> Le capability sono **preview** delle decisioni del trigger 384, non
> garanzie. Una concorrenza tra drawer e altre sessioni può comunque
> portare il guard a respingere l'UPDATE: il client deve gestire l'errore
> `E_PROFILO_ULTIMO_SUPER_ADMIN` indipendentemente dal valore di capability
> letto pochi millisecondi prima.

## Dipendenze

- `anagrafiche.identita_digitali`
- `config.profili_accesso`
- `config.profili_accesso_bindings`
- `config.tipo_profilo_accesso` (enum, valore `SUPER_ADMIN`)
- `config.ruolo_applicativo` (enum, valore `OPERATORE`)

## Chi la chiama

- [`script.fn_get_operatore_detail`](/dbzero/script/funzioni/fn_get_operatore_detail) — proietta `can_disable` / `can_demote_super_admin` nel drawer admin operatore.
- Test pgTAP: `db/pgtap/script/test-fn-check-ultimo-super-admin-attivo.sql`.

## Riferimenti

- WIP: [refactor operatore-emittenti — Fase 1 capability](/dev/work-done/refactor-operatore-emittenti)
- Codice errore `E_PROFILO_ULTIMO_SUPER_ADMIN` (id 384) in
  `config.messaggi_errore`.
- Migration: `db/changelog/migrations_v2/20_code/script/20260429-01-create-fn-check-ultimo-super-admin-attivo-mctit.yaml`

## Esempio

```sql
-- Multi super-admin: l'utente non è "ultimo" → capability di disable concessa
SELECT script.fn_check_ultimo_super_admin_attivo(42);
-- false

-- Single super-admin: l'utente è l'ultimo → drawer mostra disable bloccato
SELECT script.fn_check_ultimo_super_admin_attivo(7);
-- true

-- Utente non super-admin (qualunque scenario)
SELECT script.fn_check_ultimo_super_admin_attivo(99);
-- false
```
