# fn_get_operatore_detail

### Scopo

Riga di **dettaglio operatore + capability** per il drawer admin
"Operatore" (P1 2026-04-29). Sostituisce la query SQL inline che viveva
in `apps.amm_software.db.amm_software_repository.get_operatore_detail`,
spostando in DB l'unica fonte di verità per il dettaglio operatore — in
linea con la filosofia DB-first del progetto.

Aggiunge **6 campi capability** che guidano la UX del drawer (azioni
concesse / vietate / non applicabili) e ne riportano il motivo:

* `can_invite` / `invite_reason`
* `can_disable` / `disable_reason`
* `can_demote_super_admin` / `demote_reason`

> **Vedi anche**
>
> - [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> - [fn_check_operatore_invitabile](/dbzero/script/funzioni/fn_check_operatore_invitabile) — capability `can_invite` riusa lo stesso JSONB
> - [fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin) — flag `is_super_admin` (GUC-aware)
> - [fn_check_ultimo_super_admin_attivo](/dbzero/script/funzioni/fn_check_ultimo_super_admin_attivo) — primitiva di `can_disable` / `can_demote_super_admin`

## Schema

`script` (cross-dominio: legge `django.*`, `anagrafiche.*`, `config.*`).

## Firma

```sql
script.fn_get_operatore_detail(
    p_auth_user_id INTEGER
) RETURNS TABLE (...)
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_auth_user_id` | `INTEGER` | Sì | ID utente Django (`django.auth_user.id`). Tipo esplicito perché `%TYPE` su colonne `django.*` è anti-pattern Liquibase ordering. |

## Output

Tabella a riga singola (0 righe se `p_auth_user_id` non esiste o è `NULL`/≤0).

### Anagrafica utente

| Colonna | Tipo | Sorgente | Note |
|---|---|---|---|
| `auth_user_id` | `INTEGER` | `django.auth_user.id` | Tipo esplicito (regola django) |
| `username` | `VARCHAR(150)` | `django.auth_user.username` | |
| `email` | `VARCHAR(254)` | `django.auth_user.email` | |
| `first_name` | `VARCHAR(150)` | `django.auth_user.first_name` | |
| `last_name` | `VARCHAR(150)` | `django.auth_user.last_name` | |
| `is_active` | `BOOLEAN` | `django.auth_user.is_active` | |
| `last_login` | `TIMESTAMPTZ` | `django.auth_user.last_login` | `NULL` se mai loggato |

### Anagrafica soggetto/identità

| Colonna | Tipo | Sorgente |
|---|---|---|
| `soggetto_id` | `anagrafiche.soggetti.id%TYPE` (`uuid`) | `s.id` |
| `soggetto_cognome` | `anagrafiche.soggetti.cognome%TYPE` | `COALESCE(s.cognome, au.last_name)` |
| `soggetto_nome` | `anagrafiche.soggetti.nome%TYPE` | `COALESCE(s.nome, au.first_name)` |
| `ragione_sociale_completa` | `anagrafiche.soggetti.ragione_sociale_completa%TYPE` | `s.ragione_sociale_completa` |
| `codice_fiscale` | `anagrafiche.soggetti.codice_fiscale%TYPE` | `s.codice_fiscale` |
| `risorsa_umana_id` | `anagrafiche.risorse_umane.id%TYPE` | `ru.id` |
| `attivo` | `anagrafiche.risorse_umane.attivo%TYPE` | `ru.attivo` |
| `valido_dal` | `TEXT` | `ru.valido_dal::text` (retrocompat Python) |
| `valido_al` | `TEXT` | `ru.valido_al::text` |
| `unita_organizzativa_id` | `config.unita_organizzative.id%TYPE` | `ru.unita_organizzativa_id` |
| `unita_organizzativa_nome` | `config.unita_organizzative.descrizione%TYPE` | `uo.descrizione` |
| `ruolo_applicativo` | `TEXT` | `id.ruolo_applicativo::text` (enum `config.ruolo_applicativo`) |
| `is_super_admin` | `BOOLEAN` | `script.fn_is_super_admin(au.id)` (GUC-aware) |
| `invito_inviato_at` | `anagrafiche.identita_digitali.invito_inviato_at%TYPE` | `id.invito_inviato_at` |
| `deve_cambiare_password` | `anagrafiche.identita_digitali.deve_cambiare_password%TYPE` | `id.deve_cambiare_password` |

### Override e perimetro

| Colonna | Tipo | Significato |
|---|---|---|
| `override_aree_count` | `BIGINT` | `COUNT(*) FROM config.user_override_aree` |
| `override_azioni_count` | `BIGINT` | `COUNT(*) FROM config.user_override_azioni` |
| `emittenti_count` | `BIGINT` | `COUNT(*) FROM config.user_emittenti_fiscali` |
| `emittenti_descrizione` | `TEXT` | `string_agg` ordinato delle ragioni sociali / descrizioni |

### Capability (P1 2026-04-29)

| Colonna | Tipo | Logica |
|---|---|---|
| `can_invite` | `BOOLEAN` | `(fn_check_operatore_invitabile(au.id) ->> 'invitabile')::boolean` |
| `invite_reason` | `TEXT` | `fn_check_operatore_invitabile(au.id) ->> 'motivo'` (NULL se invitabile) |
| `can_disable` | `BOOLEAN` | `NOT fn_check_ultimo_super_admin_attivo(au.id)` |
| `disable_reason` | `TEXT` | Stringa it-IT con motivo lockout, NULL se concessa |
| `can_demote_super_admin` | `BOOLEAN` o `NULL` | `NULL` se l'utente non è SA (azione **non applicabile**); altrimenti `NOT fn_check_ultimo_super_admin_attivo(au.id)` |
| `demote_reason` | `TEXT` | NULL se non SA o se concessa; stringa it-IT con motivo lockout altrimenti |

> **Convenzione `NULL` su `can_demote_super_admin`**: distingue tra
> "azione vietata" (`false` con motivo) e "azione non applicabile"
> (`NULL`). Il frontend usa il segnale per **nascondere** il pulsante
> demote se `NULL`, **disabilitarlo con tooltip** se `false`, mostrarlo
> attivo se `true`.

## Caratteristiche

* `LANGUAGE plpgsql` **STABLE** — *deferred parsing* obbligatorio per i
  riferimenti a `django.*` (in CI Liquibase precede `manage.py migrate`,
  vedi memoria
  [feedback_django_refs_in_liquibase](/dev/work-done/refactor-operatore-emittenti#7bis6)).
  Wrapping minimo: `BEGIN ... RETURN QUERY ... END`.
* **Read-only**, nessun side effect.
* `LEFT JOIN` su `identita_digitali`: utenti senza identità OPERATORE
  vengono comunque ritornati (campi anagrafici a `NULL`), capability
  comunque calcolate sull'`auth_user`.
* **0 righe** se `p_auth_user_id` non esiste o è `NULL` / ≤0 (semantica
  lookup-by-id, coerente col Python originale; nessun raise).

## Tipi nel `RETURNS TABLE`: regola applicata

| Sorgente colonna | Tipo dichiarato | Ragione |
|---|---|---|
| `django.auth_user.*` | **Esplicito** (`INTEGER`, `VARCHAR(N)`, `BOOLEAN`, `TIMESTAMPTZ`) | Schema django creato a runtime *dopo* Liquibase: `%TYPE` fallirebbe in CI |
| `anagrafiche.*`, `config.*` | **`%TYPE`** sulla colonna sorgente | Coerenza automatica con eventuali `ALTER TYPE` upstream |
| Cast enum a `text`, `count(*)`, capability | Esplicito | Nessuna colonna sorgente diretta |

## Ottimizzazioni vs query Python originale

* `emittenti_count` + `emittenti_descrizione`: 2 sotto-query separate →
  un solo `LEFT JOIN LATERAL` aggregato (singola scansione su
  `user_emittenti_fiscali`).
* CTE `ctx`: le 3 funzioni capability (`fn_check_operatore_invitabile`,
  `fn_is_super_admin`, `fn_check_ultimo_super_admin_attivo`) calcolate
  una sola volta per riga.
* Override (`uoa`, `uoz`): mantenute come scalar subquery — tabelle
  distinte, indici FK presenti, scan singolo per ciascuna; `LATERAL`
  non porterebbe guadagno.

## GUC awareness

* `fn_is_super_admin` è gated su `app.ruolo_applicativo`: in contesti
  non-OPERATORE (portale/shop) ritorna `false` fail-closed.
* Il drawer è **admin-only** → contesto OPERATORE → `is_super_admin` ed
  `is_last_sa` valutate sui dati reali.
* Se la funzione venisse mai chiamata da un namespace portale/shop, le
  capability di disable/demote si comporterebbero come "non SA" per
  costruzione (semantica conservativa, non un bug).

## Dipendenze

### Tabelle

* `django.auth_user`
* `anagrafiche.identita_digitali`, `soggetti_ruoli`, `soggetti`,
  `risorse_umane`, `emittenti_fiscali`
* `config.unita_organizzative`, `user_override_aree`,
  `user_override_azioni`, `user_emittenti_fiscali`

### Funzioni

* `script.fn_is_super_admin(integer)` — GUC-aware (sostituisce la chiamata storica a `fn_get_ruolo_sistema`, droppata in Fase 7 2026-04-29)
* `script.fn_check_operatore_invitabile(integer)` — capability invito
* `script.fn_check_ultimo_super_admin_attivo(integer)` — capability lockout

## Chi la chiama

* Backend `apps.amm_software.db.amm_software_repository.get_operatore_detail`
  (post follow-up: la query inline viene sostituita da
  `SELECT * FROM script.fn_get_operatore_detail(%s)`).
* Endpoint `GET /api/v1/amm-software/operatori/<auth_user_id>/`.
* Test pgTAP: `db/pgtap/script/test-fn-get-operatore-detail.sql`.

## Riferimenti

* WIP: [refactor operatore-emittenti — Fase 1 capability operatore (P1)](/dev/work-done/refactor-operatore-emittenti)
* Migration: `db/changelog/migrations_v2/20_code/script/20260429-02-create-fn-get-operatore-detail-mctit.yaml`
* Helper capability: [fn_check_ultimo_super_admin_attivo](/dbzero/script/funzioni/fn_check_ultimo_super_admin_attivo)

## Esempio

```sql
-- Drawer aperto su un operatore SA tra molti
SELECT can_invite, can_disable, can_demote_super_admin,
       disable_reason, demote_reason
  FROM script.fn_get_operatore_detail(42);
-- can_invite=false, can_disable=true, can_demote_super_admin=true,
-- disable_reason=NULL, demote_reason=NULL

-- Drawer su un operatore SA che è l'unico SA attivo
SELECT can_disable, disable_reason,
       can_demote_super_admin, demote_reason
  FROM script.fn_get_operatore_detail(7);
-- can_disable=false,
-- disable_reason='Ultimo SUPER_ADMIN attivo: disabilitarlo causerebbe il lockout del sistema',
-- can_demote_super_admin=false,
-- demote_reason='Ultimo SUPER_ADMIN attivo: la rimozione del binding causerebbe il lockout del sistema'

-- Drawer su un operatore non-SA
SELECT can_demote_super_admin, demote_reason
  FROM script.fn_get_operatore_detail(99);
-- can_demote_super_admin=NULL, demote_reason=NULL  (azione non applicabile)
```

## Note di migrazione

* La funzione **non rompe** il contratto dei chiamanti Python esistenti:
  i 3 service in `AmmSoftwareService` che oggi richiamano
  `_repo.get_operatore_detail` ricevono i 6 nuovi campi nel `dict` —
  ignorati dai consumer che non li usano.
* Follow-up backend: sostituire il blocco SQL inline in
  `amm_software_repository.get_operatore_detail` con
  `SELECT * FROM script.fn_get_operatore_detail(%s)`. Single source of
  truth in DB.
