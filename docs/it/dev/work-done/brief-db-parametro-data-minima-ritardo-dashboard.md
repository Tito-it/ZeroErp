# Brief DB — La data più vecchia che il filtro «ritardo» delle dashboard può chiedere

> **Chi scrive:** sessione backend (`dev/backend-tid`), 2026-10-08. **A chi:** team
> DB (`dev/db-tid`), tramite Tid.
> **Origine:** revisione del codice non committato del 2026-10-08 (tetto di
> intervallo in `qp_int_optional`, `api.md` §Query params). **Decisione di Tid
> (2026-10-08):** il limite è un parametro di configurazione, valore `2020-01-01`.
> **Stato:** ✅ R-1 applicato a DB il 2026-10-09 (§5), pgTAP verde. ✅ §4 BE
> fatto il 2026-10-09 (§6), da committare.

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

## 5. Esito DB (2026-10-09, `dev/db-tid`)

**Cosa è stato scritto.**

* Riga **id 60** `VENDITE_DASHBOARD_RITARDO_DATA_MINIMA = 2020-01-01` in coda a
  `80_data/sql/config/parameters_vendite_defaults.csv`. Il codice proposto resta:
  segue la convenzione della famiglia (`VENDITE_<area>_<cosa>`).
  Nessun changeSet nuovo: il mirror `20260430-62-upsert-parameters-vendite-defaults`
  è `runOnChange` + `validCheckSums: ANY` e si risveglia al cambio del file.
* pgTAP `db/pgtap/config/test-parameter-vendite-dashboard-ritardo-data-minima-v1.sql`
  (3 test): la riga c'è, il valore è in forma ISO ed è una data valida.

**Le due decisioni del §3.**

* **D-1 — Nessun override.** È un limite tecnico di consultazione, uguale per
  tutti: la descrizione lo dichiara come per `SYSTEM_FUSO_ORARIO`. ⚠️ **Per il BE:**
  si legge il **default** (`config.parameters.default_value`), non la cascata di
  `script.fn_get_parameter_full`. Nessun guard DB impedisce oggi una riga in
  `config.parameter_overrides` su questo codice: leggendo il default, una riga
  del genere resta senza effetto, e la regola regge senza un guard.
* **D-2 — Nessun guard sul formato del valore.** Non esiste un guard per i
  parametri di tipo data (su `config.parameters` c'è solo il dispatcher
  FK-surrogata, che su questo codice non fa niente), e costruirne uno per un solo
  codice non si giustifica. Il formato lo presidiano il pgTAP sul seed e il
  lettore BE, che deve rifiutare un valore non ISO con un errore di
  configurazione parlante, non con un 500 generico.

**Prova pre-apply (dev, come `zeroerp_app`, in `ROLLBACK`).** Il CSV intero
(13 righe) caricato in una tabella temporanea e riscritto con l'upsert per `id`:
passa, e `default_value::date` dà `2020-01-01`. Id 60 libero sia nei CSV del repo
(massimo 59, `login_attesa_max_secondi`) sia sul DB.

⚠️ **Cosa cambia su dev al risveglio del mirror, oltre alla riga nuova.** Le 12
righe sorelle hanno `storicizza = t` nel CSV e `f` sul DB: il mirror le riporta a
`t`. Codice, valore e descrizione sono identici. È sicuro: il difetto per cui un
UPDATE su un parametro con `storicizza = t` moriva nel trigger di storico
(`parameters_id` contro `parameter_id`) è chiuso dal 2026-09-25
(`brief-db-storico-colonna-fk-dei-trigger`). Il trigger del DB di sviluppo e
`storico.parameters` usano tutti e due `parameters_id`, e l'upsert di prova è passato.

**Applicato (2026-10-09, Tid).** Su dev il mirror `20260430-62` risulta `RERAN`
in `databasechangelog`. La riga id 60 c'è, e le 12 sorelle sono a `storicizza = t`
come previsto. Il pgTAP è verde. Lato DB non resta niente: il brief resta aperto
solo per il §4 (BE).

## 6. Esito BE (2026-10-09, `dev/backend-tid`)

* **Helper unico** `_valida_ritardo_giorni` in `vendite/services/vendite_service.py`,
  usato da `fn_dash_aperto_documenti` e `fn_dash_backlog_documenti` (lista ed
  export passano da lì). Le due copie del `> 0`, con due detail diversi, sono
  ritirate nello stesso giro. Regole: `ritardo_giorni > 0` e
  `ritardo_giorni <= oggi - data_minima` (in giorni). Fuori → `E_VENDITE_VALIDATION`,
  detail con la data minima.
  ⭐ Il confronto è fra **interi di giorni**, mai `oggi - timedelta(N)`: con `N`
  enorme sarebbe Python a sollevare `OverflowError`, di nuovo un 500.
* **Lettura del default** (D-1): BB nuovo `ParameterService.get_default_date`
  (+ `ParameterRepository.get_default_value`), registrato nel catalogo BB backend.
  Assente, vuoto o non ISO (D-2) → `E_CONFIG_MANCANTE`, non un 500.
* **Test**: sul pavimento passa, un giorno oltre dà 400 (tutte e due le
  dashboard), `N = 2000000` dà 400; `get_default_date` su valido, assente/vuoto,
  non ISO. Binding provato sul DB di sviluppo con chiamata reale (dà `2020-01-01`).
* ⚠️ **Aperto, da decidere** — quale «oggi». Il BE confronta con
  `timezone.localdate()` (Europe/Rome); il filtro SQL usa `current_date`, che
  nella sessione Django è **UTC**. Fra mezzanotte e le 02:00 locali i due
  differiscono di un giorno: sul pavimento non produce più un 500 (la data resta
  nell'intervallo), ma il filtro «ritardo» e `anzianita_giorni` delle due
  dashboard contano i giorni sulla data UTC, non su quella operativa
  (`script.fn_data_operativa`, che esiste proprio per questo).
