# Brief BE/FE — LANDED `fn_get_evento_stato_corrente_cliente` data-driven (Fase 4 refactor anagrafiche)

> **Stato**: LANDED 2026-04-28
> **Branch BE/FE**: `dev/backend-tid`
> **Branch DB**: `dev/db-tid` (landed in parallelo)
> **Pattern**: data-driven cessazione (terza occorrenza dopo contratti, listini-versioni, promo articoli — tutti landed in aprile)

## 1. Cosa ha fatto il DB

Nuova funzione `anagrafiche.fn_get_evento_stato_corrente_cliente(p_cliente_id bigint)` `STABLE PARALLEL SAFE`, RETURNS TABLE `(data_evento_stato date, tipo_evento text)`.

Decisioni di design adottate:

- **2 colonne, no label di stato** — `stato_cliente_id` esiste gia' sulla tabella, niente duplicato semantico
- **Pareggio sosp = riatt** → vince `RIATTIVAZIONE` (operazione successiva nel flow normale)
- **Caso anomalo riatt senza sosp** → ritorna `RIATTIVAZIONE` (la fn legge, non valida consistenza dati)
- **Guard parametro**: `p_cliente_id IS NULL OR <= 0` → `E_PARAMETRO_INVALIDO`
- **Cliente inesistente** → `E_VALORE_MANCANTE` (pattern coerente con `vendite.fn_get_commessa_stato`)

Output `tipo_evento`: `'SOSPENSIONE' | 'RIATTIVAZIONE' | NULL`.

## 2. Cosa ha fatto il BE

### 2.1 Repository — LATERAL JOIN nel detail

[`apps/anagrafiche/db/clienti_repository.py::get_cliente()`](../../../backend/apps/anagrafiche/db/clienti_repository.py): aggiunto `LEFT JOIN LATERAL anagrafiche.fn_get_evento_stato_corrente_cliente(cl.id) AS evt(data_evento_stato, tipo_evento_stato) ON TRUE` nella query del dettaglio.

```sql
LEFT JOIN LATERAL anagrafiche.fn_get_evento_stato_corrente_cliente(cl.id)
         AS evt(data_evento_stato, tipo_evento_stato) ON TRUE
```

Vantaggi rispetto a query separata:

- Atomic: una sola round-trip al DB
- Idiomatico per output set-returning (`STABLE PARALLEL SAFE` lo permette)
- Niente cambio API contract: `data_evento_stato` e `tipo_evento_stato` arrivano come campi standard del response detail

Niente modifica a `list_clienti` (lista non mostra il computed, non serve).

### 2.2 Test

[`apps/anagrafiche/tests/services/test_clienti_service.py`](../../../backend/apps/anagrafiche/tests/services/test_clienti_service.py): 2 nuovi test:

- `test_get_cliente_propagates_evento_stato_corrente` — mock con `data_evento_stato='2026-04-05'`, `tipo_evento_stato='RIATTIVAZIONE'` → verifica propagazione
- `test_get_cliente_evento_stato_null_when_no_dates` — mock con NULL → verifica passaggio NULL al frontend

I test esistenti (33) non hanno richiesto modifiche.

**Totale test**: 832/832 verdi.

## 3. Cosa ha fatto il FE

[`frontend/src/anagrafiche/components/ClienteDrawer.vue`](../../../frontend/src/anagrafiche/components/ClienteDrawer.vue): rimosso il computed `dataSospRiattDetail` con la logica `sosp > riatt`. Sostituito con lookup diretto sui campi backend:

```diff
- // Calcola data sospensione/riattivazione da mostrare.
- const dataSospRiattDetail = computed(() => {
-   if (!detail.value) return null
-   const sosp = detail.value.data_sospensione
-   const riatt = detail.value.data_riattivazione
-   if (!sosp && !riatt) return null
-   if (sosp && !riatt) return { label: t('clienti.col_sospeso_il'), date: sosp }
-   if (!sosp && riatt) return { label: t('clienti.col_riattivato_il'), date: riatt }
-   return sosp > riatt
-     ? { label: t('clienti.col_sospeso_il'), date: sosp }
-     : { label: t('clienti.col_riattivato_il'), date: riatt }
- })
+ const EVENTO_LABEL_KEY = {
+   SOSPENSIONE: 'clienti.col_sospeso_il',
+   RIATTIVAZIONE: 'clienti.col_riattivato_il',
+ }
+ const dataSospRiattDetail = computed(() => {
+   if (!detail.value?.data_evento_stato || !detail.value?.tipo_evento_stato) return null
+   const labelKey = EVENTO_LABEL_KEY[detail.value.tipo_evento_stato]
+   if (!labelKey) return null
+   return { label: t(labelKey), date: detail.value.data_evento_stato }
+ })
```

Frontend ora **solo presentazione**: prende il `tipo_evento_stato` dal backend e mappa a label i18n. Zero logica di dominio nel componente.

Forward-compat: se in futuro arriverà un terzo `tipo_evento` (es. `CHIUSURA`), basta aggiungere una entry a `EVENTO_LABEL_KEY` (e relativa traduzione i18n) — niente refactor della regola.

## 4. Cambio comportamento osservabile

### Per chi usa l'UI

Nessun cambio funzionale visibile. La label mostrata e la data sono identiche prima/dopo il refactor. Cambia chi calcola: prima Vue, ora PostgreSQL.

### Per chi usa l'API

Il GET `/api/v1/anagrafiche/clienti/<id>/` ora include due campi nuovi nel response:

```json
{
  "data_sospensione": "2026-03-10",
  "data_riattivazione": "2026-04-05",
  "data_evento_stato": "2026-04-05",
  "tipo_evento_stato": "RIATTIVAZIONE"
}
```

I campi `data_sospensione` e `data_riattivazione` restano disponibili per backward compat (nessun client va aggiornato per forza, ma per coerenza pattern v5 chi rifa il computed lo prende da `tipo_evento_stato`).

## 5. Pattern emerso (terza occorrenza data-driven)

Il pattern **stato corrente data-driven** ora ha tre occorrenze su anagrafiche / vendite / catalogo:

| Funzione DB | Tabella | Coppie risolute | Output |
|---|---|---|---|
| (memoria stato terminale) | listini.versioni | `valido_dal`/`valido_al` vs CURRENT_DATE | stato CHIUSA virtuale |
| (memoria stato terminale) | vendite.contratti | `valido_dal`/`valido_al` vs CURRENT_DATE | CESSATO virtuale |
| (memoria stato terminale) | vendite.promo_articoli | `valido_dal`/`valido_al` vs CURRENT_DATE | SCADUTA / FUTURA / INIZIATA |
| `anagrafiche.fn_get_evento_stato_corrente_cliente` | anagrafiche.clienti | `data_sospensione` vs `data_riattivazione` | tipo_evento + data |

Variante interessante del pattern: qui non c'e' un periodo di validita' (range `[da, a]`) ma due date discrete e indipendenti. La fn risolve la discrasia per il consumer.

## 6. Riferimenti

- [analisi-refactor.frontend-anagrafiche.md](analisi-refactor.frontend-anagrafiche.md) — Fase 4 (LANDED 28-04)
- DB doc concettuale: `docs/it/dbzero/anagrafiche/funzioni/fn_get_evento_stato_corrente_cliente.md`
- Pattern memoria: `feedback_stato_terminale_con_data.md`
- Tabella: [`anagrafiche.clienti`](../../dbzero/anagrafiche/tabelle/clienti.md)
