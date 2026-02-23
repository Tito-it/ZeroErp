# test_attivita_pipeline (Django)

## Scopo

Descrivere la struttura, i pattern e la copertura dei test per il dominio
`ATTIVITA_FATTURABILI` della pipeline vendite (BE-3).

## Contesto

I test si trovano in `backend/apps/vendite/tests/` e coprono i tre layer
implementati nelle fasi BE-1, BE-2 e BE-3:

- **Unit test servizi** — `tests/services/`
- **Test HTTP contract API** — `tests/api/`
- **Smoke multi-branch** — `tests/api/`

Tutti i test usano `SimpleTestCase` (nessun accesso reale al DB).

## File di test

| File | Fase | Classe | N. test |
| ---- | ---- | ------ | ------- |
| `tests/services/test_attivita_pipeline_runner.py` | BE-1 | `AttivitaPipelineRunnerUnitTests` | 6 |
| `tests/services/test_attivita_pipeline_step_executor.py` | BE-1 | `AttivitaPipelineStepExecutorUnitTests` | 8 |
| `tests/services/test_attivita_pipeline_repository.py` | BE-1 | `AttivitaPipelineRepositoryUnitTests` | 12 |
| `tests/services/test_attivita_pipeline_service.py` | BE-2 | `AttivitaPipelineServiceUnitTests` | 6 |
| `tests/api/test_attivita_pipeline_api.py` | BE-3.2 | `VenditeAttivitaPipelineApiTests` | 14 |
| `tests/api/test_attivita_pipeline_smoke.py` | BE-3.3 | `AttivitaPipelineSmokeTests` | 3 |

**Totale: 49 test dedicati al dominio attivita fatturabili.**

## Pattern test unitari (services/)

### Mock repository (`_RepoMock`)

Pattern usato in `test_attivita_pipeline_runner.py` e `test_attivita_pipeline_smoke.py`:
implementazione inline della classe repository che sostituisce tutti i metodi DB
con logica in-memory deterministica. Non richiede DB reale.

```python
class _RepoMock:
    def get_or_create_lotto_attivita(self, **kwargs) -> int: return 10
    def is_lotto_attivita_in_esecuzione(self, lotto_id) -> bool: return False
    def list_sorgenti_abilitate(self, utility_id=None) -> list: ...
    def set_lotto_attivita_stato(self, lotto_id, stato_lotto, note=None): ...
    def list_attivita_pipeline_steps(self, ...) -> list: ...
```

### Mock step executor (`_StepExecutorMock`)

Registra le chiamate a `execute_step` senza eseguire handler reali.
Supporta un `side_effect` per simulare eccezioni `_AttivitaBranchBlockError`
o `_AttivitaGlobalBlockError` su branch specifici.

### Mock DB con `connection.cursor`

Usato in `test_attivita_pipeline_repository.py`:

```python
@patch("apps.vendite.db.attivita_pipeline_repository.connection")
def test_*(self, mock_conn):
    mock_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (...)
```

## Pattern test API (tests/api/)

### Autenticazione JWT

```python
@patch(
    "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
    return_value=(Mock(), None),
)
```

Usato su tutti i test che devono bypassare l'autenticazione JWT (`V1` views).
I test `*_v1_requires_jwt` non applicano il mock e verificano il 401.

### Mock service

```python
@patch("apps.vendite.api.views.pr_run_attivita_pipeline")
@patch("apps.vendite.api.views.fn_get_attivita_pipeline_status")
@patch("apps.vendite.api.views.fn_get_attivita_task_runs")
```

Il mock target deve essere nel modulo dove la funzione e` importata (`views`),
non nel modulo sorgente (`attivita_pipeline_service`).

### Idempotency-Key

Tutti i test del `POST /run/` devono includere `headers={"Idempotency-Key": "..."}`.
Il test `test_run_attivita_pipeline_requires_idempotency_key` omette
deliberatamente l'header e verifica il `400 E_IDEMPOTENCY_KEY_REQUIRED`.

## Copertura per endpoint

### POST `/api/v1/vendite/attivita_fatturabili/pipeline/run/` (7 test)

| Caso | HTTP | Verifica |
| ---- | ---- | -------- |
| success | 200 | `data.lotto_id`, `meta.request_id`, service chiamato |
| JSON malformato | 400 | `error="invalid_json"` |
| senza Idempotency-Key | 400 | `E_IDEMPOTENCY_KEY_REQUIRED` |
| senza JWT | 401 | autenticazione richiesta |
| ServiceError E_ATTIVITA_PIPELINE | 400 | `error.code` corretto |
| ID pari a `0` | 200 | `lotto_id=None`, `sorgente_tipo_id=None` in kwargs |
| `sorgente_tipo_id=3` | 200 | valore passato correttamente al service |

### GET `/api/v1/vendite/attivita_fatturabili/pipeline/<id>/status/` (4 test)

| Caso | HTTP | Verifica |
| ---- | ---- | -------- |
| success | 200 | `stato_lotto`, `branch_summary` presente |
| senza JWT | 401 | autenticazione richiesta |
| lotto non trovato | 404 | `E_ATTIVITA_LOTTO_NOT_FOUND` |
| lotto_id non valido | 400 | `E_ATTIVITA_VALIDATION` |

### GET `/api/v1/vendite/attivita_fatturabili/pipeline/<id>/task-runs/` (3 test)

| Caso | HTTP | Verifica |
| ---- | ---- | -------- |
| success con `?limit=50` | 200 | `count`, `task_runs[0].branch_code` |
| senza JWT | 401 | autenticazione richiesta |
| `?branch_code=DEFAULT` | 200 | service chiamato con `branch_code="DEFAULT"` |

## Copertura smoke (test_attivita_pipeline_smoke.py)

| Test | Scenario |
| ---- | -------- |
| S1 | 2 branch (`PREVENTIVI` + `ORDINI`) completano; stato finale `COMPLETATO` |
| S2 | `_AttivitaBranchBlockError` in `PREVENTIVI` non blocca `ORDINI`; lotto `COMPLETATO` |
| S3 | Endpoint lotto `POST /api/v1/vendite/pipeline/run/` → 200 (regressione) |

## Differenze rispetto ai test del dominio lotto

| Aspetto | Lotto (`test_pipeline_api.py`) | Attivita (`test_attivita_pipeline_api.py`) |
| ------- | ------------------------------ | ------------------------------------------ |
| N. test API | 21 | 14 |
| Endpoint status | segnalazioni SDI | stato_lotto + branch_summary |
| Filtro task-runs | assente | `branch_code` query param |
| Smoke | n/a (dominio stabile) | multi-branch PREVENTIVI+ORDINI |

## Dipendenze test

- `apps.core.services.service_errors.ServiceError` — raise nei mock per testare mapping errori
- `apps.vendite.db.attivita_pipeline_repository.AttivitaPipelineStep` — usato in `_RepoMock`
- `apps.vendite.db.attivita_pipeline_repository.AttivitaSorgenteBranchPolicy` — sorgente mock
- `apps.vendite.services.attivita_pipeline_step_executor._AttivitaBranchBlockError` — errore branch smoke
