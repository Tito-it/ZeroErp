# fn_get_ruolo_sistema

> ⚠️ **DEPRECATA** — wrapper retrocompatibile sul modello multi-face auth.
> Solleva `RAISE WARNING` ad ogni chiamata (PR-DB-7.1, 2026-04-29).
> Drop pianificato Sprint N+2 dopo migrazione BE+FE su nuovi helper.

### Scopo

Restituisce il `ruolo_sistema` legacy (`ADMIN | OPERATIVO | DISABILITATO`)
ricostruito al volo dal nuovo modello multi-face introdotto dal
cutover §4.6 (anagrafiche.identita_digitali + binding SUPER_ADMIN).

Il valore non e' piu' memorizzato in alcuna colonna fisica — la "tabella
ponte" `risorse_umane_auth_user` di cui parlava la versione precedente
di questa doc e' stata sostituita da una vista (`20260419-91`) che
calcola `ruolo_sistema` con la stessa CASE che usa questa fn.

> **Vedi anche**
>
> - [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> - [fn_is_super_admin](/dbzero/script/manual/fn_is_super_admin) — predicato moderno per `'ADMIN'`
> - [fn_has_identita_attiva](/dbzero/script/manual/fn_has_identita_attiva) — predicato moderno per `<> 'DISABILITATO'`
> - [risorse_umane_auth_user](/dbzero/anagrafiche/manual/risorse_umane_auth_user) — vista che espone la stessa CASE come colonna calcolata

## Stato

| Fase | Migration | Cosa |
|---|---|---|
| Origine | `20260308-01-create-fn-get-ruolo-sistema` | Versione legacy che leggeva direttamente `risorse_umane_auth_user.ruolo_sistema` (tabella reale). |
| §4.6.C.1 | `20260419-22-update-fn-get-ruolo-sistema-wrapper` | Refactor a wrapper retrocompat post-cutover multi-face. |
| **Fase 7 (questa doc)** | `20260429-10-update-fn-get-ruolo-sistema-deprecation-warning` | Aggiunta `RAISE WARNING` ad ogni chiamata. Body invariato. |
| Pianificata Sprint N+2 | — | DROP della fn + DROP enum `config.ruolo_sistema`. |

## Schema

`script` (cross-dominio).

## Firma

```sql
script.fn_get_ruolo_sistema(
    p_auth_user_id integer
) RETURNS config.ruolo_sistema
```

## Mappatura "vecchio enum → nuovo modello"

| Output | Condizione (modello multi-face) |
|---|---|
| `'DISABILITATO'` | `NOT fn_has_identita_attiva(au_id, 'OPERATORE')` (nessuna identità OPERATORE attiva in finestra) |
| `'ADMIN'` | identità OPERATORE attiva **AND** binding SUPER_ADMIN attivo (= `fn_is_super_admin(au_id)`) |
| `'OPERATIVO'` | identità OPERATORE attiva **AND NOT** SUPER_ADMIN (composizione) |
| `NULL` | `p_auth_user_id IS NULL` |

## Migrazione consigliata per chiamanti

| Pattern legacy | Pattern multi-face |
|---|---|
| `fn_get_ruolo_sistema(au) = 'ADMIN'` | `fn_is_super_admin(au)` |
| `fn_get_ruolo_sistema(au) = 'DISABILITATO'` | `NOT fn_has_identita_attiva(au, 'OPERATORE')` |
| `fn_get_ruolo_sistema(au) = 'OPERATIVO'` | `fn_has_identita_attiva(au, 'OPERATORE') AND NOT fn_is_super_admin(au)` |
| `fn_get_ruolo_sistema(au) <> 'DISABILITATO'` | `fn_has_identita_attiva(au, 'OPERATORE')` |

I primi 2 pattern coprono ~90% dei call site reali (censimento BE 2026-04-29). Il 3° pattern è raro nella pratica — quasi sempre il chiamante voleva dire "operatore utilizzabile", che è il 4° pattern.

## RAISE WARNING

```sql
RAISE WARNING
    'script.fn_get_ruolo_sistema is DEPRECATED (Fase 7 cleanup). Migrate to script.fn_is_super_admin / script.fn_has_identita_attiva. Drop planned 2 sprints from 2026-04-29. Caller p_auth_user_id=%',
    p_auth_user_id;
```

- Livello `WARNING` (non `NOTICE`): garantisce visibilità nei log
  PostgreSQL anche con `client_min_messages` default.
- **Una warning per chiamata**, niente soppressione "warn-once".
  Razionale: nelle 2 sprint di deprecation window il rumore è
  funzionale — evidenzia subito i call site residui non migrati.
  Post-migrazione BE+FE il warning scompare organicamente.
- Hot-path noti che continuano a chiamarla nel periodo di transizione:
  `apps.amm_software.db.amm_software_repository` (lista + riepilogo
  permessi). Sono i primi a essere migrati nella Fase 7 BE.

## Caratteristiche

- `LANGUAGE plpgsql STABLE` — nessuna scrittura DB. `RAISE WARNING`
  produce output cliente, non viola STABLE.
- Riusa `fn_has_identita_attiva` + `fn_is_super_admin` come single
  source of truth: la stessa logica è anche nella vista
  `anagrafiche.risorse_umane_auth_user`.

## Pianificazione drop (Sprint N+2)

Dopo migrazione completa BE+FE (Fase 7 in corso):

1. Drop di questa fn (`DROP FUNCTION script.fn_get_ruolo_sistema(integer)`).
2. Drop colonna calcolata `ruolo_sistema` dalla vista
   `anagrafiche.risorse_umane_auth_user` (`CREATE OR REPLACE VIEW`
   senza la CASE + senza la subquery `sa` su SUPER_ADMIN bindings).
3. Drop ENUM `config.ruolo_sistema` (`DROP TYPE`) — solo dopo che
   nessuna fn/vista lo referenzia più. Verificare con `pg_depend`.
4. Drop arg `p_ruolo_sistema` da `fn_crea_risorsa_umana` /
   `fn_crea_operatore` (BE già non lo passa post-migrazione).

I 4 step in unica PR DB se la coverage test BE+FE è verde, altrimenti
in PR separate per minimizzare il blast radius.

## Riferimenti

- Migration deprecation: `db/changelog/migrations_v2/20_code/script/20260429-10-update-fn-get-ruolo-sistema-deprecation-warning-mctit.yaml`
- Brief Fase 7: `docs/it/dev/work-in-progress/analisi-refactor.frontend-amm-software.md`
- Cutover §4.6.H.2 (prerequisito): `db/changelog/migrations_v2/20_code/anagrafiche/20260419-91-cutover-rua-view-mctit.yaml`
