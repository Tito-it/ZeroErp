# Brief BE/FE — LANDED config-resolver arricchito con `default_tipo_soggetto_dettaglio_id` (Fase 3 refactor anagrafiche)

> **Stato**: LANDED 2026-04-27
> **Branch BE/FE**: `dev/backend-tid`
> **Branch DB**: `dev/db-tid` (landed in parallelo)
> **Origine**: brief DB del 2026-04-27 in risposta alle 5 domande sulla Fase 3 dell'analisi `analisi-refactor.frontend-anagrafiche.md`
> **Pattern**: `config.parameters` + guard trigger (opzione B definitiva, coerente con `DEFAULT_IVA_ID`)

## 1. Decisione di design (recap Q&A)

| Aspetto | Scelta | Motivo |
|---|---|---|
| Storage default | `config.parameters` | Pattern gia' consolidato (`DEFAULT_IVA_ID`); override per emittente gratuiti |
| Naming chiave | `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<RUOLO>` | Vincola al `_dettaglio`, non al padre `tipi_soggetto` |
| `default_value` | `codice_interno` (string) | Stabile via `lock_columns`, no id numerico |
| FK integrity | guard trigger | `parameters` non ha FK reale; trigger valida |
| Granularita' | solo per ruolo | Stato e altre dimensioni rinviate a futuro caso d'uso |
| Numero entry attese | 2 oggi (CL, FO), max 5-6 | Override per emittente prevedibile entro 6-12 mesi |

Scartate **A** (is_default colonna, troppo rigida con N ruoli) e **C** (mini-tabella dedicata, perde override gratuito).

## 2. Cosa ha fatto il DB

- Seed in `config.parameters`:
  - `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL` → `'PR'`
  - `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_FO` → `'PR'`
- Funzione in schema **`config`** (coerente con tabella primaria `config.parameters`)
- Trigger **`_a10_`** (guard puro), con doppia clausola di skip:
  - `WHEN (NEW.code LIKE 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%')` → no overhead sugli altri parametri
  - `OF code, default_value` → niente scatti su update di description/audit
- Defense-in-depth NULL: branch `IF NEW.default_value IS NULL THEN RETURN NEW` come safety net (oggi inarrivabile per NOT NULL constraint, ma robusto)
- Test fixture portatile: `LIMIT 1` su `tipi_soggetto_dettaglio.codice_interno` come default valido (no hardcode `'PR'`) — funziona anche se la baseline cambia
- Doc concettuale copre limitazioni note: niente guard su `parameter_overrides`, niente cascade DELETE da `tipi_soggetto_dettaglio` — entrambi rinviati al primo caso reale

## 3. Cosa ha fatto il BE

### 3.1 Repository — query default + risoluzione id

[`apps/anagrafiche/db/soggetti_repository.py::get_config_resolver()`](../../../../backend/apps/anagrafiche/db/soggetti_repository.py):

- Aggiunta firma opzionale `emittente_fiscale_id: int | None = None`
- Aggiunta query 4: `SELECT script.fn_get_parameter_full(:code, :emittente, NULL, NULL::bigint[], NULL, NULL)`
- Risoluzione `codice_interno` → `id` matchando i `dettagli` gia' caricati (no extra query)
- Fallback a `None` se chiave assente o codice orfano (non tra dettagli ammessi)

```python
return {
    "tipo_ruolo": ruolo["codice"],
    "tipo_ruolo_descrizione": ruolo["descrizione"],
    "nature_ammesse": [...],
    "tipi_soggetto_dettaglio": dettagli,
    "default_tipo_soggetto_dettaglio_id": default_id,  # nuovo
    "min_search_length": 3,                            # nuovo (costante per ora)
}
```

### 3.2 View — schema DRF aggiornato

[`apps/anagrafiche/api/views_ruoli_config.py`](../../../../backend/apps/anagrafiche/api/views_ruoli_config.py): aggiunti i 2 campi al `extend_schema` con descrizione operativa per OpenAPI.

### 3.3 Test — 4 nuovi casi

[`apps/anagrafiche/tests/api/test_config_resolver.py`](../../../../backend/apps/anagrafiche/tests/api/test_config_resolver.py):

- `test_config_resolver_default_present` — `'PR'` configurato → id risolto correttamente
- `test_config_resolver_default_codice_orfano` — codice non tra dettagli → `default_id None`, no errore
- `test_config_resolver_default_assente` — `fn_get_parameter_full` ritorna `None` → `default_id None`
- `test_config_resolver_min_search_length_costante` — campo sempre presente

Aggiornati anche i 3 test esistenti per gestire la 4° query (chiamano fetchone con `(None,)`).

**Test verde**: `Ran 814 tests in 1.600s — OK` (anagrafiche + core)

## 4. Cosa ha fatto il FE

[`frontend/src/core/components/SoggettoResolver.vue`](../../../../frontend/src/core/components/SoggettoResolver.vue):

```diff
- const privato = dettagli.find(d => d.codice_interno === 'PR')
- return privato ? privato.id : dettagli[0].id
+ return configResolver.value?.default_tipo_soggetto_dettaglio_id ?? dettagli[0].id
```

```diff
- :min-length="3"
+ :min-length="configResolver?.min_search_length || 3"
```

```diff
- if (!query || query.length < 3) {
+ const minLen = configResolver.value?.min_search_length || 3
+ if (!query || query.length < minLen) {
```

Niente piu' valore cablato `'PR'`. Niente piu' soglia cablata `3`. Tutto data-driven da backend.

## 5. Override per emittente — pronto, non attivato

L'API repository accetta `emittente_fiscale_id: int | None = None` ma la view oggi passa `None` (no caso d'uso attivo). Quando servira' override per emittente B2B vs B2C:

1. Estrarre `emittente_fiscale_id` dal request context (es. via `PermissionResolver.get_emittente_fiscale_pk()`)
2. Passarlo a `repo.get_config_resolver(tipo_ruolo, emittente_fiscale_id=ctx)`
3. Insert override in `config.parameter_overrides` per quell'emittente
4. La catena `script.fn_get_parameter_full` lo risolve automaticamente

## 6. Limitazioni note (rinviate)

- Suffisso `_<STATO>` (es. `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL_IT`) non implementato — variante futura.
- Guard trigger non valida `parameter_overrides` (solo riga padre). Aggiungere quando arriva il primo caso reale di override.
- Niente cascade DELETE da `tipi_soggetto_dettaglio` (verso parameters): se elimini un `_dettaglio`, il parameter resta orfano. Manuale per ora.

## 7. Riferimenti

- [analisi-refactor.frontend-anagrafiche.md](analisi-refactor.frontend-anagrafiche.md) — Fase 3 sezione del piano (LANDED 27-04)
- Pattern simmetrico: `DEFAULT_IVA_ID` ([clienti_repository.py:34](../../../../backend/apps/anagrafiche/db/clienti_repository.py#L34))
- DB doc concettuale: `docs/it/dbzero/config/manual/trgfn_parameters_guard_default_tipo_soggetto_dettaglio.md` (creata dal team DB)
- Tabella: [`config.parameters`](../../dbzero/config/tabelle/parameters.md)
