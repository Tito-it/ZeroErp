# test_attivita_pipeline (Django)

## Scopo

Descrivere la struttura, i pattern e la copertura dei test per il dominio
`ATTIVITA_FATTURABILI` della pipeline vendite.

## Contesto

I test si trovano in `backend/apps/vendite/tests/` e coprono:

- **Unit test servizi** — `tests/services/`
- **Test HTTP contract API** — `tests/api/`

Tutti i test usano `SimpleTestCase` (nessun accesso reale al DB).

## File di test

| File | Classe | N. test |
| ---- | ------ | ------- |
| `tests/services/test_attivita_pipeline_repository.py` | `AttivitaPipelineRepositoryUnitTests` | 5 |
| `tests/services/test_attivita_pipeline_service.py` | `AttivitaPipelineServiceUnitTests` | 5 |
| `tests/api/test_attivita_pipeline_api.py` | `VenditeAttivitaPipelineApiTests` | 7 |

**Totale: 17 test dedicati al dominio attivita fatturabili.**

## Pattern test unitari (services/)

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
@patch("apps.vendite.api.views.fn_get_attivita_pipeline_status")
@patch("apps.vendite.api.views.fn_get_attivita_task_runs")
```

Il mock target deve essere nel modulo dove la funzione e` importata (`views`),
non nel modulo sorgente (`attivita_pipeline_service`).

## Copertura per endpoint

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

## Differenze rispetto ai test del dominio lotto

| Aspetto | Lotto (`test_pipeline_api.py`) | Attivita (`test_attivita_pipeline_api.py`) |
| ------- | ------------------------------ | ------------------------------------------ |
| N. test API | 21 | 7 |
| Endpoint status | segnalazioni SDI | stato_lotto + branch_summary |
| Filtro task-runs | assente | `branch_code` query param |

## Dipendenze test

- `apps.core.services.service_errors.ServiceError` — raise nei mock per testare mapping errori
