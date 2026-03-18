# Building Block Repository — Piano sviluppo backend

> Documento di lavoro per la scomposizione dei repository in building block riutilizzabili.
> Data: 2026-03-13
> Stato: **COMPLETATO** (review 2026-03-13)
>
> Dipende da:
>
> * Building block SQL: `fn_crea_auth_user`, `fn_crea_soggetto_pf`, `fn_crea_risorsa_umana`
> * Orchestratore SQL: `fn_crea_operatore` (refactored)
> * [Componenti Riutilizzabili Frontend](../frontend/componenti-riutilizzabili.md)
> * [Guida Soggetti e Ruoli Anagrafici](/guide/soggetti-e-ruoli-anagrafici)

---

## Motivazione

Il repository `amm_software_repository.py` chiama direttamente `fn_crea_operatore` monolitica.
Con la scomposizione DB in building block atomici, il backend deve:

1. Esporre repository core riutilizzabili che mappano 1:1 i building block SQL
2. Permettere ai domini futuri (clienti, fornitori) di riusare gli stessi repository
3. Allineare la firma Python alla nuova firma SQL (aggiunto `qualifica_id`, CF obbligatorio)

### Principio guida

> **Un repository core per ogni building block SQL**.
> Il dominio (amm_software) chiama l'orchestratore SQL.
> I repository core servono per i domini che compongono diversamente i building block.

---

## Cosa e' cambiato nel DB

| Aspetto | Vecchio (`fn_crea_operatore` monolitica) | Nuovo (orchestratore + building block) |
|---|---|---|
| Struttura | 5 INSERT inline in una funzione | 3 chiamate a building block atomici |
| `qualifica_id` | Hardcoded `c_qualifica_default = 1` | Parametro obbligatorio `p_qualifica_id` |
| `codice_fiscale` | Opzionale | Obbligatorio (guard PF in `fn_crea_soggetto_pf`) |
| Unicita' CF | Lookup su `codice_fiscale` | Lookup su `id_fiscale_univoco_cf_piva` per `stato_id` |
| Tabella auth_user | `public.auth_user` | `django.auth_user` (schema Django) |
| Contatto default | Non creato | Creato da `fn_crea_soggetto_pf` (guard DEFERRED) |

---

## Fase 1 — Repository core (building block Python)

Creare repository riutilizzabili in `apps/core/db/` che mappano i building block SQL.

### 1.1 `apps/core/db/auth_repository.py`

```python
class AuthRepository:
    def crea_auth_user(self, *, username, email, password_hash,
                       first_name=None, last_name=None) -> int:
        """Chiama anagrafiche.fn_crea_auth_user(). Ritorna auth_user.id."""
```

**Riusabile da**: amm_software (operatori), futuro admin, qualsiasi flusso con utente Django.

### 1.2 `apps/core/db/anagrafiche_repository.py`

> Nota: esiste gia' `apps/anagrafiche/db/anagrafiche_repository.py`.
> I building block vanno in `apps/core/db/` perche' sono trasversali.
> Il repository in `apps/anagrafiche/` resta per query specifiche del dominio anagrafiche.

```python
class AnagraficheCoreRepository:
    def crea_soggetto_pf(self, *, cognome, nome, codice_fiscale, email,
                         data_nascita=None, sesso='M', stato_iso2='IT') -> str:
        """Chiama anagrafiche.fn_crea_soggetto_pf(). Ritorna soggetti.id (UUID)."""
```

**Riusabile da**: operatori, clienti PF, fornitori PF.

### 1.3 `apps/core/db/risorse_umane_repository.py`

```python
class RisorseUmaneCoreRepository:
    def crea_risorsa_umana(self, *, soggetto_id, qualifica_id,
                           unita_organizzativa_id=None, valido_dal=None,
                           valido_al=None, auth_user_id=None,
                           ruolo_sistema='OPERATIVO') -> int:
        """Chiama anagrafiche.fn_crea_risorsa_umana(). Ritorna risorse_umane.id."""
```

**Riusabile da**: operatori, admin, dipendenti senza accesso.

---

## Fase 2 — Aggiornare `amm_software_repository.py`

Il metodo `crea_operatore()` deve allinearsi alla nuova firma SQL:

```python
def crea_operatore(self, *, cognome, nome, codice_fiscale, username, email,
                   password_hash, qualifica_id, unita_organizzativa_id=None,
                   data_nascita=None, sesso='M', ruolo_sistema='OPERATIVO',
                   valido_dal=None, valido_al=None) -> int:
```

Cambiamenti:

* Aggiunto `qualifica_id` (obbligatorio)
* `codice_fiscale` da opzionale a obbligatorio
* `unita_organizzativa_id` da obbligatorio a opzionale (il DB lo gestisce)
* Ordine parametri SQL allineato alla nuova funzione

---

## Fase 3 — Aggiornare view `UtentiListView.post()`

```python
# Nuovi campi nel payload
codice_fiscale = (payload.get("codice_fiscale") or "").strip()
qualifica_id = payload.get("qualifica_id")

# Nuove validazioni
ErrorManager.require(bool(codice_fiscale), code="E_AMM_VALIDAZIONE",
                     message="Codice fiscale obbligatorio.")
ErrorManager.require(qualifica_id is not None and int(qualifica_id) > 0,
                     code="E_AMM_VALIDAZIONE",
                     message="Qualifica obbligatoria.")
```

---

## Fase 4 — Test

### 4.1 Test repository core

* `apps/core/tests/db/test_auth_repository.py` — mock cursor, verifica SQL e parametri
* `apps/core/tests/db/test_anagrafiche_core_repository.py` — mock cursor, verifica SQL
* `apps/core/tests/db/test_risorse_umane_core_repository.py` — mock cursor, verifica SQL

### 4.2 Aggiornare test esistenti

* `apps/amm_software/tests/api/test_crea_utente.py` — aggiungere `qualifica_id` e `codice_fiscale` ai payload

---

## Fase 5 — Endpoint lookup qualifiche

Il frontend ha bisogno di un Select per le qualifiche.

```
GET /api/v1/amm-software/lookup/qualifiche/
→ [{ "id": 1, "descrizione": "Amministratore" }, ...]
```

* Aggiungere metodo `list_qualifiche()` in `amm_software_repository.py`
* Aggiungere view `LookupQualificheView` e URL

---

## Matrice riutilizzo repository

| Repository | Metodo | amm_software | clienti | fornitori | profilo |
|---|---|:---:|:---:|:---:|:---:|
| `AuthRepository` | `crea_auth_user` | x | | | |
| `AnagraficheCoreRepository` | `crea_soggetto_pf` | x | x | x | |
| `RisorseUmaneCoreRepository` | `crea_risorsa_umana` | x | | | |
| `AmmSoftwareRepository` | `crea_operatore` | x | | | |

---

## Review finale (2026-03-13)

### Problemi trovati e risolti

| #   | Problema | Tipo | Fix |
| --- | --- | --- | --- |
| 1 | Frontend API mancante `listQualifiche()` | Bug | Aggiunto in `amministrazione.js` |
| 2 | Frontend store mancante lookup qualifiche | Bug | Aggiunto ref, action e export in `utenti.js` |

### Verifica logica duplicata

* **Repository core vs amm_software**: nessuna duplicazione — i repository core (`auth_repository.py`, `anagrafiche_core_repository.py`, `risorse_umane_core_repository.py`) chiamano i building block SQL singoli, `amm_software_repository.py` chiama l'orchestratore SQL `fn_crea_operatore`. Nessuna logica sovrapposta.
* **Validazione view vs DB**: la view valida i campi obbligatori (fail-fast UX), il DB fa le proprie guard (fail-safe). Nessuna logica di business duplicata, solo difesa in profondita'.

### Verifica robustezza

* `qualifica_id` validazione: `int(qualifica_id) > 0` — un valore non numerico solleva `ValueError`, catturato dal middleware `api_exception_middleware` che ritorna 400. Pattern coerente con il resto del codebase.
* `int(uo_id) if uo_id else None` — `uo_id = 0` trattato come None. Accettabile perche' `0` non e' un ID valido e il DB fa guard `<= 0`.
* Tutti i `cursor.fetchone()` hanno `assert row is not None` come da convenzione AGENTS.md.

### Risultati test

* **52 test OK** (42 amm_software + 10 core db) — `0.034s`
* **Frontend build OK** — 417 moduli, zero errori
* **Smoke test** creato: `backend/scripts/tests/smoke-test-amm-software.sh` (13 test, solo GET)

---

## Struttura cartelle risultante

```
backend/apps/
├── core/
│   ├── db/
│   │   ├── (esistenti)
│   │   ├── auth_repository.py              # NUOVO — building block auth_user
│   │   ├── anagrafiche_core_repository.py   # NUOVO — building block soggetto PF
│   │   └── risorse_umane_core_repository.py # NUOVO — building block risorsa umana
│   └── tests/
│       └── db/
│           ├── test_auth_repository.py              # NUOVO
│           ├── test_anagrafiche_core_repository.py   # NUOVO
│           └── test_risorse_umane_core_repository.py # NUOVO
├── amm_software/
│   ├── db/
│   │   └── amm_software_repository.py       # AGGIORNATO — nuova firma
│   ├── api/
│   │   ├── views.py                         # AGGIORNATO — qualifica_id + CF
│   │   └── urls_v1.py                       # AGGIORNATO — lookup qualifiche
│   └── tests/
│       └── api/
│           └── test_crea_utente.py           # AGGIORNATO — nuovi campi
```
