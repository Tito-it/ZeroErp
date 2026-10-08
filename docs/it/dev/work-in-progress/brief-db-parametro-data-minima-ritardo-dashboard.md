# Brief DB — La data più vecchia che il filtro «ritardo» delle dashboard può chiedere

> **Chi scrive:** sessione backend (`dev/backend-tid`), 2026-10-08. **A chi:** team
> DB (`dev/db-tid`), tramite Tid.
> **Origine:** revisione del codice non committato del 2026-10-08 (tetto di
> intervallo in `qp_int_optional`, `api.md` §Query params). **Decisione di Tid
> (2026-10-08):** il limite è un parametro di configurazione, valore `2020-01-01`.
> **Stato:** ⏳ da applicare a DB. Il BE (§3) parte quando il parametro c'è.

## 1. Cosa si chiede

| # | Cosa | Tipo | Bloccante per il BE |
| --- | --- | --- | --- |
| R-1 | Un parametro `VENDITE_DASHBOARD_RITARDO_DATA_MINIMA`, valore `2020-01-01` | seed `80_data` (`config.parameters`) | sì: il BE lo legge per validare `ritardo_giorni` |

Nessuna funzione e nessun codice d'errore nuovi: il rifiuto resta il
`E_VENDITE_VALIDATION` che il BE solleva già su `ritardo_giorni` non positivo.

## 2. Perché

Le dashboard «aperto» e «backlog» (lista ed export) filtrano i documenti «in
ritardo da oltre N giorni» con
`d.data_riferimento <= current_date - make_interval(days => %s)`
(`vendite/db/vendite_repository.py`). `N` arriva dal query param `ritardo_giorni`.

Oggi il BE controlla solo che `N` sia `> 0` e, dal 2026-10-08, che stia in un
`integer` (il tipo del parametro `days`). Non basta: `current_date - N giorni` esce
dall'intervallo di `timestamp` già intorno a 740 000 giorni. Provato sul DB di
sviluppo il 2026-10-08: con `N = 2000000` si ha `DataError: timestamp too small`,
cioè un **500** al posto di un 400.

Il limite giusto non è il tipo: è **quanto indietro ha senso chiedere**, una scelta
di dominio. Per questo va in configurazione e non in una costante nel codice.

## 3. R-1 — Il parametro

| Campo | Valore |
| --- | --- |
| `code` | `VENDITE_DASHBOARD_RITARDO_DATA_MINIMA` (nome proposto; il team DB lo allinea alla convenzione se serve) |
| `default_value` | `2020-01-01` (ISO `YYYY-MM-DD`) |
| file | `80_data/sql/config/parameters_vendite_defaults.csv`, o quello che il team DB ritiene la sede giusta |
| `description` | La data più vecchia che il filtro «ritardo» delle dashboard vendite (aperto, backlog) può raggiungere: `oggi - ritardo_giorni` non va prima di questa data. Oltre, il BE risponde 400 (`E_VENDITE_VALIDATION`) invece di far arrivare al DB una data fuori intervallo. Letto dal backend (`vendite_service`). Nasce il 2026-10-08 (brief-db-parametro-data-minima-ritardo-dashboard). |

**Da decidere al team DB:**

* **Override** (`config.parameter_overrides`): è un limite tecnico di consultazione,
  uguale per tutti. Un override per utente o emittente non ha un caso d'uso. La
  proposta è non prevederlo, ma la decisione spetta al team DB.
* **Validazione del valore**: se esiste già un guard per i parametri di tipo data,
  conviene agganciarlo. Un valore non ISO lo rifiuterebbe comunque il BE in lettura,
  ma solo alla prima richiesta.

## 4. Ricaduta sul backend (dopo R-1)

* In `vendite_service.py` c'è già **due volte** lo stesso controllo
  `ritardo_giorni > 0` (dashboard aperto e backlog). Il pavimento sarebbe la terza
  copia della stessa regola, quindi si estrae un helper unico (regola del 2) che
  controlla tutte e due le cose:
  `0 < ritardo_giorni` e `oggi - ritardo_giorni >= VENDITE_DASHBOARD_RITARDO_DATA_MINIMA`.
  Fuori da questo → `E_VENDITE_VALIDATION`, con un detail che nomina la data minima.
* Il tetto `integer` già messo in `qp_int_optional` resta: è il tipo, non il dominio.
* Test: il caso sopra il pavimento dà 400, e il caso esattamente sul pavimento passa.
