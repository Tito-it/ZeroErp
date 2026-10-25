# Governo della qualità del backend Django

> **Ultimo aggiornamento**: 26 settembre 2026
>
> **Destinatari**: chi sviluppa o rivede codice nel backend.
>
> **Vedi anche** — le fonti delle regole (qui non si ricopiano):
>
> * [api.md](../api.md) — URL, layer, base view, envelope, errori, idempotenza, permessi, test
> * [Catalogo building block backend](catalogo-building-block-backend.md) — cosa esiste già in `apps/core` e nei domini
> * [Checklist di scrittura API](/backend/core/manual/api_write_checklist) — i passi per un endpoint nuovo
> * [Sicurezza e qualità statica](../sicurezza-e-qualita-statica.md) — ruff, gitleaks, audit delle dipendenze, `check --deploy`
> * `.codex/AGENTS.md` — regole trasversali, regola zero, regola del 2

---

## A cosa serve questo documento

Le fondazioni del backend sono prese e non si rimettono in discussione. Questo
documento non spiega come si scrive un endpoint: quello sta in
[api.md](../api.md) e nella [checklist](/backend/core/manual/api_write_checklist).
Qui c'è **come si controlla** che il backend resti coerente: quali regole sono
presidiate da un test, quali restano affidate alla revisione, e il debito
dichiarato.

## Le fondazioni (decise)

* Layer `api → service → repository → PostgreSQL`. La logica di business sta nel
  DB, e Django orchestra.
* Solo `APIView` esplicite su quattro base view: `DomainAPIView` (domini
  operativi), `AdminAPIView` (amministrazione software), `PortaleAPIView`
  (portale clienti e fornitori), `ShopAPIView` (negozio). Niente
  `ModelViewSet`, niente router DRF.
* Errori centralizzati: `ServiceError`, `ErrorManager`, `ErrorTranslator`, il
  registro `error_policies` (generato dal catalogo DB) e il middleware API.
* Helper di view in `apps/core/api/endpoint_helpers.py` (`handle_post_json`, …) e attributi dichiarativi sulle view
  (`area_funzionale`, `model_permission`, `post_permission`,
  `is_search_endpoint`, `skip_area_check`, `require_idempotency_key`).
* Test per app in `tests/api/`, `tests/services/` e, dove serve, `tests/db/`
  (sul database vero) e `tests/middleware/`.

## Cosa è presidiato da un test

Una regola con un presidio si rompe in CI, non in revisione. Questi sono i
cancelli in `apps/core/tests/`: chi cambia la regola cambia il test, per
decisione.

| Presidio | Cosa impedisce |
| --- | --- |
| `test_error_codes_declared_guardrail.py` | un codice `E_*` scritto nel codice di produzione (ogni literal che è per intero un codice, dal 2026-10-07; prima i soli `code=` / `error_code=`) e non dichiarato in `error_policies_generated.py`, o ritirato; il debito motivato sta in `_DEBITO` e deve calare |
| `test_error_codes_db_policy_guardrail.py` | un codice `E_*` sollevato da una funzione PL/pgSQL viva senza voce in `error_policies.py` |
| `test_event_codes_declared_guardrail.py` | un `event_code` scritto su `vendite.event_log` e assente da `config.eventi_dominio` |
| `test_schema_openapi_registro.py` + `openapi_schema.baseline.json` | nuovi rilievi drf-spectacular: una view senza `@extend_schema`, cioè un endpoint vuoto nello schema OpenAPI |
| `test_skip_area_check_registro.py` | un `skip_area_check = True` muto (con un'area dichiarata) o non registrato |
| `test_transaction_atomicity_guardrail.py` | un metodo che compone due o più scritture DB fuori da `transaction.atomic()` |
| `test_system_context_usage_whitelist.py` | il ritorno di un canale di connessione `BYPASSRLS` |
| `api/test_superficie_pubblica.py` | admin Django, redirect della root, Swagger esposto senza `API_DOCS_ENABLED` |

Fuori dai test Django: `ruff` (`ruff.toml`), gitleaks, l'header di licenza
(`scripts/check_license.py`) e i guardrail in `scripts/guardrail_*.py`. Sono in
[Sicurezza e qualità statica](../sicurezza-e-qualita-statica.md) e in AGENTS.md.

## Cosa resta affidato alla revisione

Non hanno (ancora) un presidio automatico. In revisione si guarda:

* **base view e helper**: che un endpoint nuovo usi la base view giusta e
  `handle_post_json` per le POST (e per PATCH/PUT/DELETE in modalità forte), `corpo_oggetto` per le altre PATCH/PUT;
* **`try/except Exception` nelle view**: un'eccezione generica nasconde il
  codice d'errore giusto. Dove serve davvero (una scrittura best-effort, un
  canale che non deve mai far fallire la risposta) va motivata nel commento;
* **`is_search_endpoint`** sulle ricerche e sulle liste pesanti (freno
  `DJANGO_API_SEARCH_THROTTLE_RATE`);
* **permessi** dichiarati nel punto giusto (area, oggetto, azione);
* **regola del 2**: la seconda copia di una logica diventa un building block nel
  catalogo, e le copie si ritirano nello stesso giro;
* **typing** dove riduce un rischio reale: `TypedDict` per le righe dei
  repository e i payload normalizzati, return type espliciti nei service
  pubblici, `assert` dopo `ErrorManager.require(...)` e dopo un
  `cursor.fetchone()` che non può mancare. Il backend rifiuta di partire con
  `python -O`, quindi quegli `assert` non spariscono;
* **log con contesto**: codice d'errore, area, funzione o processo. Il
  `request_id` è già su ogni riga.

## Il confine DB ↔ Django

Spostare logica dal SQL a Django **non** è un obiettivo. Una funzione si
classifica solo quando c'è una ragione concreta:

| Stato | Criterio |
| --- | --- |
| `DB-only` | invarianti, coerenza dei dati, trigger, controlli set-based, funzioni chiamate da più canali |
| `Hybrid` | regola nel DB, orchestrazione, policy o flusso UX in Django |
| `Migrated` | logica applicativa che cambia spesso o va composta con servizi esterni |

Non si duplica in Django un vincolo che il DB già garantisce. Al massimo si
aggiunge una pre-validazione, per un errore più parlante, e il DB resta la
difesa finale.

## Workflow dello sviluppatore

```bash
cd backend
./manage-test.sh                            # suite completa, con l'env di .env.systemd
./manage-test.sh apps.vendite.tests -v 2    # un modulo
ruff check .                                # dalla radice del repo: ruff.toml
python scripts/build_docs_zensical.py       # build della documentazione (non `mkdocs build`)
```

I test in `tests/db/` girano sul database vero e saltano se il DB non è
provvisto (`richiedi_db_provvisto`). Il perché e i building block dei test sono
nel [catalogo](catalogo-building-block-backend.md).

## Debito dichiarato

Fatti datati, non obiettivi: si chiudono o si motivano.

* **26-09-2026** — `except Exception` in tre moduli di view, tutti in `apps/core/api/`:
  `endpoint_helpers.py`, `password_reset_views.py`, `auth_views.py`. Vanno
  motivati nel commento o ristretti.
* **26-09-2026** — il ruolo `zeroerp_batch_fatturazione` (`BYPASSRLS`) esiste
  ancora nel database, anche se il backend non lo usa più: il ritiro è un passo
  di provisioning. Vedi [Provisioning ruoli DB](provisioning-db-roles.md).

## Quando si aggiorna

* Il **catalogo** a ogni building block nuovo, nello stesso giro.
* **api.md** solo per regole vincolanti o pattern architetturali.
* **Questo documento** quando nasce o sparisce un presidio, o quando cambia il
  debito dichiarato.
