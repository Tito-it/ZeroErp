# Brief BE + DB + FE — Un solo fuso: quello dell'azienda

> **Chi scrive:** sessione BE (`dev/backend-tid`) il 2026-10-09; allargato lo stesso giorno, su
> richiesta di Tid, da «il giorno di un filtro» a **tutto ciò che dipende da un fuso**.
> **A chi:** Tid (decisioni aperte, §6), poi team DB (§5.1), BE (§5.2), FE (§5.3).
> **Origine:** un test sul DB vero rosso a mezzanotte e mezza (`test_giornale_trasversale_perimetro`
> 1), verificato su richiesta di Tid durante L2 di [piano-be-type-checker.md](../work-done/piano-be-type-checker.md)
> (§5.2). Il test era giusto: il difetto è nel filtro, e il filtro è un caso di una regola più larga.
> **Stato:** 🟡 **in parte deciso.** Deciso (Tid, 2026-10-09): funzione DB + building block BE per i
> filtri per giorno (D-2, B-4), colonne `date` fuori dal perimetro dei *filtri*; tutte le decisioni di §6
> (T-1 … T-8). DB: `20261009-40`…`-61` e la fase `70_dati_sistema` ✅ **applicati, pgTAP verdi, nessuna regressione** (Tid, 2026-10-09). BE L1-L4 e FE L5 fatti il 2026-10-09 (timer con T-9); resta T-5 lato Django, da concordare col team DB (§8.3).
> Censimento su tre lati completato il 2026-10-09 (§4).
> **Storia del documento:** nato come `brief-be-db-giorno-nel-fuso-aziendale`, che aveva già
> assorbito il gemello `brief-db-confine-del-giorno-nel-fuso-aziendale` (stesso giorno, stesso
> difetto); rinominato quando il perimetro è diventato il fuso intero.

## 1. La regola

**Il fuso dell'azienda è uno solo, ed è un dato: `config.parameters.SYSTEM_FUSO_ORARIO`.**
Validato in scrittura (registro `config.parameter_fk_surrogate` → `pg_timezone_names`), letto come
default **nudo** (mai la cascata di override: lo stesso fatto avrebbe date diverse secondo chi lo
guarda), fail-loud se manca. Oggi lo legge una sola sede, `script.fn_data_operativa()`.

Ne discendono tre regole, una per strato, e valgono per ogni installazione, in qualunque fuso:

1. **Un istante si conserva e si confronta come istante** (`timestamptz`; in transito ISO con
   offset). Qui il fuso non entra, e non c'è niente da correggere.
2. **Ogni passaggio fra un istante e il calendario** — «che giorno è oggi», «quando comincia il
   giorno D», «in che giorno/mese cade questo istante», «che ora mostro» — **passa per il fuso
   dell'azienda**, attraverso un building block, mai attraverso il fuso di chi esegue.
3. **Il fuso di chi esegue diventa irrilevante**: la sessione PostgreSQL, il processo Python,
   l'host, il browser. Se cambiarlo cambia un risultato, quello è un difetto.

⛔ Una costante `Europe/Rome` nel codice (oggi `settings.TIME_ZONE`) è una **seconda copia** del dato:
il giorno in cui il parametro cambia, diverge in silenzio. La regola del 2 vale anche per un fuso.

## 2. Il difetto: oggi gli orologi sono quattro

| Chi | Fuso con cui calcola il giorno e l'ora | Da dove |
| --- | --- | --- |
| Sessione DB del backend | **UTC** | Django con `USE_TZ = True` e nessun `TIME_ZONE` in `DATABASES` |
| psql, Liquibase, pgAgent | fuso del **server PG** (oggi Europe/Rome) | file di configurazione del server, non nel repo |
| Processo Python (gunicorn, command, timer) | **`settings.TIME_ZONE = 'Europe/Rome'`**, costante | Django fa `os.environ["TZ"] = TIME_ZONE; time.tzset()` |
| Browser | fuso del **PC dell'utente** | nessuna configurazione |
| *(l'azienda)* | *`SYSTEM_FUSO_ORARIO`* | *letto solo da `fn_data_operativa`* |

Ogni volta che due di questi non coincidono, lo stesso fatto ha due date. A Roma lo si vede fra
mezzanotte e le 02:00 (sessione UTC contro azienda +1/+2). In un'installazione a Tokyo (+9) la
finestra va dalle 00:00 alle 09:00; a New York (−5) dalle 19:00 a mezzanotte, nel verso opposto
(il fatto finisce nel giorno *dopo*); un utente collegato da un altro fuso vede un terzo giorno.

⭐ Non dipende dai dati né dalla popolazione: è la struttura dei predicati e delle conversioni.

È la stessa famiglia che il DB ha già chiuso per la data documento con `script.fn_data_operativa()`,
il cui commento la descrive con le stesse parole. Il lavoro qui è portare quella regola **ovunque**.

## 3. Come lo si è visto

`test_giornale_trasversale_perimetro` 1 scrive una riga di diario **adesso** e la cerca filtrando per
`date.today()`, cioè il giorno del processo Python (Roma). Il filtro calcola il giorno nella sessione
DB (UTC). Di giorno coincidono e il test è verde; a mezzanotte e mezza no. Il test è **giusto** e
non si tocca: farlo ragionare in UTC lo farebbe tornare verde nascondendo il difetto.

**Fatto datato (non è il motivo):** il 2026-10-08 i cinque run di CI-Validate partiti fra le 22:54 e
le 22:58 UTC (00:54-00:58 del 9 a Roma) sono falliti su quel test; quelli delle 12:00, 15:57 e 21:15
UTC dello stesso giorno erano passati.

## 4. Dove sta — censimento del 2026-10-09

Censimento **testuale** su tre lati (DB dalla doc auto-generata, BE da `backend/apps`, FE da
`frontend/src`), esclusi i test salvo dove detto. Trova le forme che conosce: una forma scritta
diversamente sfuggirebbe, ed è ciò a cui servono i presidi (D-8, B-9, F-6). I numeri sono una
fotografia di quel giorno, non il perimetro: il perimetro è la regola di §1.

### 4.1 DB

**a) «Oggi» preso dalla sessione (`CURRENT_DATE`)** — il confronto è date contro date, ma il giorno
è quello di chi esegue:

| Dove | Quanti | Esempi |
| --- | --- | --- |
| Funzioni e trigger di produzione | 62 | trigger `*_normalize` di ddt/ordini/resi/preventivi/contratti (`NEW.data := CURRENT_DATE`, `EXTRACT(YEAR FROM CURRENT_DATE)`); `fn_genera_ddt_da_ordine`, `fn_genera_ddt_riconsegna`, `fn_select_attivita_fatturabili`, `fn_crea_distinta_correzione`, `fn_posta_contabile`, `fn_conferma_sistemazione`; i guard di validità (`fn_veste_utilizzabile` — pesa sul login —, `fn_get_permessi_effettivi_*`, `trgfn_*_guard_transizione_stato`); `trgfn_pratiche_set_data_apertura` |
| di cui con parametro `DEFAULT CURRENT_DATE` | 10 | `fn_crea_operatore_v2`, `fn_crea_risorsa_umana_v2`, `fn_genera_ddt_*`, `fn_select_attivita_fatturabili`, `fn_crea_distinta_correzione`, `fn_get_or_create_vendite_contabile`, `fn_admin_merge_*`, `fn_pgtap_crea_listino` |
| Chiavi di idempotenza giornaliere | 2 | `fn_accoda_chiusura_scadenze` (`CURRENT_DATE::text`), `fn_guardiano_digest` |
| Viste | 6 | `vw_conti_bancari_per_ruolo`, `vw_articoli_componenti_dettaglio`, `vw_articoli_dettaglio`, `vw_bersagli_non_dichiarati`, `vw_offerte_commerciali_lista`, `vw_dash_backlog_documenti` |
| `DEFAULT CURRENT_DATE` di colonna | 28 | `vendite.ddt/preventivi/resi/ordini/contratti.data`, `contratti.valido_dal`, `acquisti.ddt/ordini.data`, `magazzino.rettifiche/trasferimenti/inventari.data`, `shop.ricevute.data_emissione`, `valido_dal` di `identita_digitali`, `billing_account`, `user_override_*`, `template_asset`; `data_registrazione` dei sei registri `dbops`; `storico.comuni/indirizzi_dettaglio/indirizzi.valid_from` |
| Fixture pgTAP in `dbops` | 7 | `fn_pgtap_crea_fattura` scrive `CURRENT_DATE` dove il DEFAULT di produzione è `fn_data_operativa()` |

Già corretti: i DEFAULT di `vendite.fatture.data` e `vendite.commesse.data_apertura`, e
`fn_calcola_data_documento`, `fn_get_pavimento_emissione`, `fn_get_or_create_commessa`.

**b) Istante → giorno nel fuso della sessione:**

| Oggetto | Forma |
| --- | --- |
| `vendite.vw_dash_competenza_attivita` | `date_trunc('month', af.data_insert)::date` |
| `vendite.vw_dash_fatturazione_offerte` | `(o.data_emissione)::date`, `(o.data_insert)::date` |
| `script.trgfn_storico_generic` | `CURRENT_TIMESTAMP` assegnato a `valid_from`/`valid_to` di tipo **date** su `storico.comuni` e `storico.indirizzi_dettaglio` (cast implicito); stesse colonne lette da `fn_get_snapshot_as_of` / `fn_get_record_id_as_of` con un `p_as_of timestamptz` |

**c) Giorno → istante nel fuso della sessione** (mezzanotte della sessione scritta in
`magazzino.movimenti.data_mov`, che è `timestamptz`): `fn_posta_rettifica`, `fn_posta_trasferimento`
(×2), `fn_posta_inventario`, `vendite.fn_posta_ddt`, `vendite.fn_posta_reso`. E
`storico.indirizzi.valid_from`, `timestamptz` con `DEFAULT CURRENT_DATE`.

**d) Job pgAgent** — schedulati nel fuso del server, e girano con `CURRENT_DATE` di quel fuso:
`chiusura_scadenze_daily` (00:05: chiude ciò che ha `valido_al < CURRENT_DATE`), il più sensibile;
`sync_auth_user_expired_daily` (06:00, via `fn_veste_utilizzabile`); `guardiano_digest` (orario,
chiave giornaliera). Gli altri undici lavorano su metadati e non dipendono dal giorno.

**e) pgTAP:** 236 file usano `CURRENT_DATE` come «oggi» delle fixture (1117 occorrenze). Finché la
produzione usa lo stesso `CURRENT_DATE` sono coerenti per costruzione; quando la produzione passa a
`fn_data_operativa()` divergono nella finestra in cui i due giorni differiscono. Fragili già oggi:
`test-fn-accoda-chiusura-scadenze` (`data_insert >= CURRENT_DATE`), `test-fn-posta-inventario-v1`
(`data_mov::date`), `test-fn-guardiano-digest`. Quattro test usano già il fuso dell'azienda
(`test-data-documento-v1` forza `TimeZone = 'UTC'` apposta: è il modello).

**Puliti:** nessuna colonna `timestamp` senza fuso (presidio §11.10 già attivo), nessun CHECK o
policy RLS con `CURRENT_DATE`, nessun `to_char`/`extract` di calendario su un `timestamptz`.

### 4.2 Backend

**a) Filtri per giorno su colonne `timestamptz`** — 12 sedi in 10 file, in quattro forme (il nucleo
originario del brief, confermato dal censimento):

| Forma | Sedi |
| --- | --- |
| **A** `col >= %s::date` / `< %s::date + interval '1 day'` | `vendite_repository.list_giornale_trasversale` (`quando`), `dbops_repository` (`e.occurred_at`), `permissions_audit_repository` (`valid_from`), `pratiche_repository` (`p.data_insert`), `magazzino_repository` (`mv.data_mov`), `email_repository` (`el.data_insert`), `amm_software_repository` (`valid_from`, misto `::timestamptz` / `::date`) |
| **B** `%s::timestamptz`, e confine alto **incluso** (`<=`) | `dbops_repository` (`executed_at`), `maintenance_repository` (`started_at`) |
| **C** `date` Python senza cast, `+1 giorno` calcolato in `gestione_service` | `coda_lavori/repository` (`data_insert`), `pipeline_repository` (coda di stampa) |
| **D** cast sulla colonna: `a.data_insert::date >= %s` (in più non usa l'indice) | `catalogo_repository` (lista articoli) |

E una quinta, istante → mese: `maintenance_repository.py:248-249`,
`to_char(date_trunc('month', started_at), 'YYYY-MM-DD')` (mese di competenza di ripiego).

**b) `CURRENT_DATE` nel SQL dei repository** (giorno UTC): ~30 sedi. Le più gravi scrivono la data di
un documento o di una registrazione: `pipeline_repository.py:1789` (data fattura),
`ddt_repository.py:651`, `resi_repository.py:773`, `pagamenti_repository.py:1055, 2457`,
`clienti_repository.py:224`. Poi validità (`amm_software_repository.py:531, 597`,
`tipi_ruolo_tipi_indirizzo_repository.py:203, 222`, `risorse_umane_core_repository.py:90`), filtri
«valido oggi» (`lookup_repository` ×5, `contratti_repository`, `listini_repository`,
`soggetti_repository`, `pagamenti_repository`, `dbops_repository`, `documenti_repository`) e
anzianità (`vendite_repository.py:1379, 1397, 3135`).

**c) «Oggi» calcolato in Python** con `date.today()` o `timezone.localdate()` (cioè col fuso
costante di `settings`): ~25 sedi. Esempi: default dei form (`vendite_form_defaults_service` ×5,
`catalogo_service.py:166`), guard («attivo oggi»: `listini_service.py:1637`,
`promo_articoli_service.py:460, 487`, `contratti_service.py:1007` — dove Python ragiona in Roma e il
guard DB su `CURRENT_DATE` in UTC), date di documenti (`ordini_service.py:740`,
`preventivi_service.py:695`), il batch `run_fatturazione_batch.py:69`, la scelta della versione del
template di stampa (`document_generation_service.py:1511`), il prompt dell'assistente
(`prompt_builder.py:91`).

**d) Ora mostrata** — la sede unica è `core/services/locale_formatters.in_ora_locale` (export, PDF,
digest), giusta nel meccanismo ma col fuso di `settings`. Fuori sede, tre difetti:

- `password_reset_views.py:234`: l'email di conferma scrive l'ora in **UTC**;
- `presidi_digest.py:717` `_riga_compatta`: `str()` di un `timestamptz`, cioè UTC con `+00:00`;
- `documenti/.../_date_formatting.py:64`: `date.fromisoformat(raw[:10])` su una stringa ISO con
  offset dà il giorno UTC.

**e) API:** `success_response` emette i `timestamptz` così come arrivano dalla sessione, cioè in UTC
con `Z` (verificato su `DjangoJSONEncoder`): corretto, è un istante. In ingresso,
`pratiche_repository.py:1074, 1109` accetta `%s::timestamptz` da una stringa dell'utente: senza
offset PostgreSQL la legge nel fuso della sessione.

**f) Fuori dalla richiesta:** i timer systemd (`backend/deploy/sveglie.json`) usano il fuso
dell'**host** (`fatturazione-differita` il 1° alle 02:00, i digest alle 07:00); i management command
ereditano `settings.TIME_ZONE`. I log (`%(asctime)s`) scrivono l'ora del processo **senza offset**:
ambigua nell'ora del cambio legale.

**g) Test** che dipendono dal fuso: ~40 file con `date.today()`/`CURRENT_DATE`, e due con
`@override_settings(TIME_ZONE="Europe/Rome")` (`test_locale_formatters`, `test_presidi_digest`).

### 4.3 Frontend

Il frontend non conosce il fuso dell'azienda: nessun `timeZone` esplicito, nessuna libreria di date,
tutto nel fuso del browser. La sede unica esiste ed è buona — `core/utils/date.js`, con un presidio
(`datePresidio.spec.js`) contro `toISOString` e i formati scritti a mano — ma ha copie fuori e non
sa di un fuso diverso da quello del PC.

**a) «Oggi» del browser:** `addDaysToToday`, `defaultFiltroDataDa*` (15 store), ~17 default di campo
`new Date()`, i `min-date`, anno e mese correnti della dashboard di competenza e dell'anteprima del
numero di registro. Copie fuori sede: 4 «oggi a mezzanotte» scritti a mano (`ContrattoDrawer` ×2,
`CloneVersioneDrawer`, `severity.js`), `todayLocalDate()` duplicata in 2 drawer, 3 concatenazioni
`YYYY-MM` a mano.

**b) `new Date('YYYY-MM-DD')`**, letta come mezzanotte **UTC** (nei fusi negativi è il giorno prima):
`SoggettoDrawer.vue:182` (`data_nascita`, poi risalvata sbagliata), `FornitoreDrawer.vue:111`,
`PraticaDrawer.vue:158`, `useContoBancarioForm.js:80-81`, `severity.js:205-208` (decide il badge
CHIUSA), `LottiListView.vue:448-456` (mese di competenza). E 8 copie di
`new Date(s + 'T00:00:00')` che fanno a mano ciò che fa `parseIsoDate`.

**c) Il giorno di un istante:** `displayDate` su una stringa timestamp ne prende i primi 10
caratteri, cioè il giorno **UTC** (il JSON arriva con `Z`), mentre `displayTimestamp`/`displayTime`
mostrano l'ora del **browser**: in `GiornaleEventi.vue:86-87` data e ora dello stesso evento possono
non combaciare.

**d) Ora mostrata nel fuso del browser:** `displayTimestamp`/`displayTime` (23 file), la data in
`AppTopbar`, e l'unico DatePicker con ora (`SospensionePraticaDialog`): l'istante inviato è giusto,
ma l'ora che l'utente legge e digita è quella del suo PC.

**e) Test:** nessun `TZ` forzato in vitest: girano nel fuso della macchina.

## 5. Proposta

L'ordine conta: i building block del DB (D-1, D-2) servono a BE; il fuso esposto dal BE (B-1) serve
al FE.

### 5.1 DB

| # | Cosa |
| --- | --- |
| **D-1** | ⭐ **Una sede per il fuso**: `script.fn_fuso_operativo()` (nome a scelta del team DB) legge il default nudo e porta il fail-loud di oggi (assente, vuoto, sconosciuto → `E_CONFIG_MANCANTE`). `fn_data_operativa` la usa, nello stesso giro (regola del 2). È anche ciò che il BE leggerà (B-1): niente seconda lettura del parametro in Python. |
| **D-2** | **I due confini fra istante e giorno**, gemelli di `fn_data_operativa`: `fn_inizio_giorno_operativo(date) → timestamptz` (= `p::timestamp AT TIME ZONE <fuso>`) e `fn_giorno_operativo(timestamptz) → date` (= `(p AT TIME ZONE <fuso>)::date`). `STABLE`; NULL → NULL (i filtri sono opzionali); nel `WHERE` stanno sui **confini**, non sulla colonna, così il predicato resta servito dagli indici. |
| **D-3** | **«Oggi» = `fn_data_operativa()` ovunque**: le 62 funzioni, le 6 viste, i 10 parametri `DEFAULT CURRENT_DATE`, le 2 chiavi di idempotenza giornaliere, i 3 `EXTRACT(YEAR FROM CURRENT_DATE)`. |
| **D-4** | **I 28 `DEFAULT CURRENT_DATE` di colonna** → `DEFAULT script.fn_data_operativa()`, con `SET DEFAULT` in un changeSet a sé e **mai** `ADD COLUMN … DEFAULT fn()`: la funzione legge un seed di `80_data`, e un DEFAULT STABLE viene valutato all'`ALTER` anche a zero righe (muore in CI su un DB nuovo). |
| **D-5** | **Istante → giorno** con `fn_giorno_operativo`: le due viste di dashboard e `trgfn_storico_generic` sulle colonne `date` di `storico.comuni`/`indirizzi_dettaglio` (e il loro uso in `fn_get_snapshot_as_of`). |
| **D-6** | **Giorno → istante** con `fn_inizio_giorno_operativo` nei 6 punti di posting di `magazzino.movimenti.data_mov`. ⚠️ Il team DB conferma la semantica: un movimento datato D nasce alla mezzanotte aziendale di D. E `storico.indirizzi.valid_from` (`timestamptz` con `DEFAULT CURRENT_DATE`): probabilmente `now()`, a giudizio del team DB. |
| **D-7** | **pgTAP**: le 7 fixture `dbops.fn_pgtap_crea_*` e i test passano a `fn_data_operativa()` come «oggi», nello stesso giro di D-3 (altrimenti divergono dalla produzione). D-1/D-2 hanno il loro pgTAP che **costruisce** il confine invece di leggere l'ora: 23:30 UTC del giorno D-1 è il giorno D a Roma; estate (+2) e inverno (+1); il giorno di 23 e di 25 ore; `SET LOCAL TimeZone` a un fuso diverso dal parametro, come fa già `test-data-documento-v1`. |
| **D-8** | **Presidio**: un pgTAP che rifiuta `CURRENT_DATE`, `current_date`, `LOCALTIMESTAMP`, `now()::date` e affini nei corpi di funzioni, viste e DEFAULT (con l'elenco delle eccezioni dichiarate, se ne resterà qualcuna), più il guardrail gemello sui changeSet nuovi, sul modello di `guardrail_timestamp_senza_fuso.py`. |
| **D-9** | **Job pgAgent** (deciso, T-4): sveglia frequente (oraria) e lavoro **una volta per giorno aziendale**, con la chiave d'idempotenza calcolata da `fn_data_operativa()`. Vale per `chiusura_scadenze_daily`, `sync_auth_user_expired_daily` e `guardiano_digest`; i job sui metadati restano come sono. Il fuso del server smette di contare. |

### 5.2 Backend

| # | Cosa |
| --- | --- |
| **B-1** | **Il fuso dell'azienda nel processo**: un building block in `core` che legge il fuso da D-1 (una query, non una copia del parametro), lo tiene in cache di processo e lo **attiva** (`timezone.activate`) in un middleware per ogni richiesta e all'avvio di ogni management command e worker. Nessuna invalidazione (T-6): il fuso si legge all'avvio del processo. Lo stesso BB espone il fuso al frontend (in `/core/me/` o in un bootstrap). |
| **B-2** | **`settings.TIME_ZONE = 'UTC'`** (deciso, T-2): un valore neutro, non una copia del fuso aziendale. Quello che resta legato al fuso del processo (un `date.today()` sfuggito) diventa visibile invece di funzionare per coincidenza. |
| **B-3** | **«Oggi» in Python** solo dal BB (`oggi_aziendale()`, sopra `timezone.localdate()` col fuso attivato): le ~25 sedi di §4.2 c. Dove la data finisce comunque nel DB (date di documenti, `valido_dal` di default) la si **omette** e decide il DB con `COALESCE(%s, script.fn_data_operativa())`: la decisione resta in un livello solo. |
| **B-4** | **Filtri per giorno** (deciso, Tid 2026-10-09): un BB per il predicato «colonna nel giorno da… al…», che restituisce frammento SQL e parametri con i confini da D-2 (`col >= fn_inizio(da) AND col < fn_inizio(a + 1)`). Le 12 sedi di §4.2 a passano al BB nello stesso giro, ognuna col suo test sul DB vero; `maintenance_repository.py:249` usa `fn_giorno_operativo`. |
| **B-5** | **`CURRENT_DATE` nel SQL dei repository** → `script.fn_data_operativa()` (~30 sedi di §4.2 b). |
| **B-6** | **Ora mostrata**: `locale_formatters` resta la sede, e con B-1 prende il fuso dal parametro senza cambiare codice. Si correggono i tre difetti fuori sede di §4.2 d. I due test con `@override_settings(TIME_ZONE=…)` passano all'override del BB. |
| **B-7** | **Istanti in ingresso con offset obbligatorio**: un `timestamptz` che arriva dall'utente senza offset si rifiuta in validazione (`pratiche`, §4.2 e), invece di lasciarlo interpretare alla sessione. |
| **B-8** | **Log in UTC, ISO 8601 con `Z`** (deciso, T-3): il formatter scrive l'offset, e non dipende né dal processo né dal parametro. **Timer systemd** (deciso, T-4): stessa forma di D-9 — sveglia frequente, lavoro una volta per giorno (o mese) aziendale, chiave sul giorno aziendale; `OnCalendar` non porta più un orario di calendario. |
| **B-9** | **Presidi**: le regole `DTZ` di ruff (`date.today()`, `datetime.now()` senza fuso, …) aggiunte a `select` in `ruff.toml` — ruff c'è già, nessuna dipendenza nuova; un test che rifiuta `CURRENT_DATE`, `::date` su colonna e `%s::date` confrontato con un `timestamptz` nelle stringhe SQL dei repository (o, meglio, che i BB di B-4/B-5 siano l'unica strada). |

### 5.3 Frontend

| # | Cosa |
| --- | --- |
| **F-1** | **`date.js` riceve il fuso dell'azienda** (da B-1) e lo usa in tutte le sue funzioni: `displayTimestamp`/`displayTime`/`displayDate` di un istante con `Intl.DateTimeFormat({ timeZone })`; `displayDate` su un timestamp **converte**, non taglia la stringa. |
| **F-2** | **«Oggi» = il giorno dell'azienda**: un BB in `date.js` (`oggiAziendale()`), su cui poggiano `addDaysToToday` e `defaultFiltroDataDa*`. Le copie si ritirano nello stesso giro: i 4 «oggi a mezzanotte» a mano, le 2 `todayLocalDate`, i ~17 `new Date()` di default, i `min-date`, anno e mese correnti, le 3 concatenazioni `YYYY-MM`. Dove il backend manda già un default (`default_date`, `default_valido_dal`, …) il ripiego sul browser sparisce. |
| **F-3** | **Mai `new Date('YYYY-MM-DD')`**: le 7 sedi di §4.3 b passano a `parseIsoDate`, come le 8 copie `'T00:00:00'` e il `parseDate` di `SoggettoDrawer`. |
| **F-4** | **L'ora che l'utente legge e digita** (`SospensionePraticaDialog`, `AppTopbar`) nel fuso dell'azienda (deciso, T-1). |
| **F-5** | **Presidio**: `datePresidio.spec.js` si allarga a `new Date(` con un argomento stringa, `new Date()` fuori da `date.js`, `setHours(0,0,0,0)`, `toLocale*String` senza `timeZone`. E vitest gira con un `TZ` **lontano** da quello dell'azienda (per esempio `Pacific/Pago_Pago`, −11): ciò che dipende dal fuso del PC diventa rosso a ogni ora, non solo di notte. |

### 5.4 Trasversale: la CI vede il fuso a ogni ora

Oggi un difetto di fuso in CI è rosso solo nella finestra notturna, cioè quasi mai. Con un fuso di
esecuzione **ostile** — sessione PG dei pgTAP, processo dei test Django, vitest — lontano da quello
del parametro (per esempio +14 contro +2), la finestra in cui i due giorni differiscono copre metà
giornata, e un test che costruisce il caso lo vede sempre. ⚠️ È un presidio, non la prova: la prova
resta il test che **costruisce** l'istante di confine (D-7, B-4).

## 6. Decisioni (Tid)

### 6.1 Aperte

Nessuna.

### 6.2 Prese

✅ **Tid, 2026-10-09:**

1. Filtri per giorno: funzione DB (D-2) + building block BE (B-4), copie ritirate nello stesso giro.
   Niente calcolo del fuso in Python.
2. Le colonne `date` confrontate con un parametro `date` restano fuori dai *filtri*: non hanno il
   difetto. ⚠️ Rientra invece in perimetro il loro «oggi» quando viene da `CURRENT_DATE` o da
   `date.today()` (D-3, B-3, B-5): il confronto è giusto, il valore di riferimento no.
3. **T-1 — Orari a video nel fuso dell'azienda**, non del browser: liste, drawer, topbar, DatePicker
   con ora. Un solo fuso in tutta l'applicazione, lo stesso dei documenti, dei PDF e degli export.
4. **T-2 — `settings.TIME_ZONE = 'UTC'`** con il fuso dell'azienda attivato dal parametro (B-1, B-2).
5. **T-3 — Log in UTC, ISO 8601 con `Z`** (B-8).
6. **T-4 — Sveglie frequenti, lavoro una volta per giorno aziendale** (D-9, B-8), per pgAgent e
   systemd: nessun requisito sul fuso dell'host, nessuna seconda copia del fuso.
7. **T-6 — Nessun meccanismo per il cambio del fuso a sistema avviato**: niente invalidazione della
   cache. Il backend legge il fuso all'avvio; un cambio del parametro vale dal riavvio successivo.
8. **T-4a — La fatturazione differita parte alla mezzanotte aziendale del 1°**, non più alle 02:00.
   Le 02:00 di `sveglie.json` non hanno una ragione scritta (verificato il 2026-10-09: né la nota né
   il `.timer` la danno), e un orario «di sicurezza» espresso in ore di Roma non ha senso in un
   altro fuso. Ciò che si registra in ritardo sul mese chiuso non lo salvava comunque un margine di
   due ore.
9. **T-5 — Fuso ostile in CI** (§5.4): pgTAP, test Django e vitest girano in un fuso lontano da
   quello del parametro.
10. **T-7 — Il fuso si usa in Python, letto dal DB** (strada a): il backend chiede il fuso al DB
   (D-1) e converte da sé le ore a video e l'«oggi» dei form; il frontend fa lo stesso nel browser
   col fuso ricevuto da B-1. La decisione 1 resta: i confini dei filtri li calcola il DB.
11. **T-8 — Il dato che il codice legge nasce prima dei seed** (Tid, 2026-10-09). Su un
   database da zero tutto `00_schema`/`20_code` gira prima di tutto `80_data`, e
   `SYSTEM_FUSO_ORARIO` nasceva in `80_data` (`20260825-12`) mentre trigger, `DEFAULT` e guard di
   `20_code` lo leggono: un seed anteriore che passasse da quel codice avrebbe fermato la
   creazione del database. **Fase nuova `migrations_v2/70_dati_sistema`** nel master, fra
   l'autogen e `80_data`, per i dati senza cui il codice non gira; `20260825-12` ci è stato
   **spostato** (stesso `logicalFilePath`, cioè stessa identità; cambia solo il percorso del CSV,
   quindi rigira una volta come upsert della stessa riga). Una cartella dentro `00_schema` non
   sarebbe servita: l'autogen ordina per `YYYYMMDD-NN`, non per cartella. Esclusa dall'autogen,
   presidiata dai guardrail di `runOnChange` e delle preCondition; descritta in
   `liquibase-setup-workflow.md`. **Fatto datato:** il 2026-10-09 nessun seed eseguito prima del
   parametro arrivava a quel codice; la fase chiude il caso per costruzione, non per misura.

12. **T-9 — Sveglie calendariali: il controllo sta in un `ExecCondition=`** (Tid, 2026-10-09,
   strada a). Il timer si sveglia ogni ora; `ExecCondition=… run-command.sh e_dovuto <unit>`
   decide se il periodo aziendale (`dovuto` in `sveglie.json`) e' cominciato e se la corsia ha
   gia' una corsa riuscita. Il `comando` resta la riga di «Esegui ora», che esegue sempre. Le
   alternative scartate: un `--forza` aggiunto dal pulsante (la riga del pulsante non sarebbe
   piu' quella del timer) e il pulsante spento sulle sveglie calendariali.

## 7. Fuori da questo brief

- **La correzione dei dati già scritti** con il giorno sbagliato (date di documenti, `data_mov`,
  storico): misurarne l'entità è un fatto, non un motivo; se servirà un recupero, è un brief a sé.
- **Più fusi per azienda** (un'installazione multi-sede in fusi diversi): il modello oggi ha un
  parametro di sistema, e questo brief non lo cambia.
- `test_giornale_trasversale_perimetro` resta com'è: lo fa tornare verde la correzione del filtro.

## 8. Stato dei lavori

### 8.1 DB — ✅ chiuso il 2026-10-09: applicato, pgTAP verdi, nessuna regressione (Tid)

| changeSet | Voce | Cosa |
| --- | --- | --- |
| `20261009-40` | D-1 | `script.fn_fuso_operativo()`: sede unica della lettura e del fail-loud del fuso; `RETURNS config.parameters.default_value%TYPE` |
| `20261009-41` | D-1 | `script.fn_data_operativa()` chiede il fuso alla sede unica |
| `20261009-42` | D-2 | `script.fn_inizio_giorno_operativo(date)` |
| `20261009-43` | D-2 | `script.fn_giorno_operativo(timestamptz)` |
| `20261009-44` … `-50` | D-3 | `CURRENT_DATE` → `script.fn_data_operativa()` in **61** funzioni (un changeSet per schema: anagrafiche 10, catalogo 2, dbops 7, pagamenti 5, pratiche 1, script 15, vendite 21). In un'istruzione SQL `(SELECT script.fn_data_operativa())`, valutata una volta per istruzione; in un'espressione PL/pgSQL e nei `DEFAULT` dei parametri la chiamata diretta. ⚠️ Nel `-46` `fn_accoda_chiusura_scadenze` cambia anche comportamento (vedi D-9) |
| `20261009-51` … `-54` | D-3, D-5 | le 6 viste con `CURRENT_DATE`, e `vw_dash_fatturazione_offerte` / `vw_dash_competenza_attivita` che ricavavano giorno e mese da un istante nel fuso della sessione (ora `fn_giorno_operativo`). `security_invoker` ripetuto com'è oggi, anche nel rollback |
| `20261009-55` (`80_data`) | D-4 | `SET DEFAULT script.fn_data_operativa()` su 25 colonne. In `80_data`, dopo il seed del parametro (`20260825-12`), come `20260913-15`: in `00_schema` il DEFAULT sarebbe attivo per i seed anteriori al parametro |
| `20261009-56`, `-57` | D-6 | `magazzino.movimenti.data_mov` di un movimento datato D = `fn_inizio_giorno_operativo(D)` (5 funzioni di registrazione), non più la mezzanotte della sessione |
| `20261009-58` (`00_schema/storico`) | D-5, D-6 | `storico.comuni` e `storico.indirizzi_dettaglio`: `valid_from`/`valid_to` da `date` a `timestamptz`, `USING` per ruolo che ha scritto (forma di `20260920-03`); `DEFAULT now()` anche su `storico.indirizzi`. Le tre ombre prendono la forma delle altre 114, e il trigger generico dello storico smette di troncare l'istante al giorno della sessione |
| `20261009-59` | D-7 | le 7 fixture `dbops.fn_pgtap_*` prendono «oggi» da `fn_data_operativa`, come il codice che provano |
| `20261009-60` | D-3 | `fn_crea_operatore_v2`, rimasta fuori dal `-44` perché la stava riscrivendo `brief-db-sesso-senza-default`: il corpo è quello vivo dopo il loro `-27` |
| `70_dati_sistema/20260825-12` (spostato) | T-8 | il seed del fuso gira dopo il codice e prima di ogni seed; master, autogen, guardrail e guide aggiornati |
| `20261009-61` (`85_pgagent`) | D-9 | `chiusura_scadenze_daily` ogni ora al minuto 5, `sync_auth_user_expired_daily` ogni ora al minuto 10 (T-4). La chiusura si fa una volta per giorno aziendale perché `fn_accoda_chiusura_scadenze` (`-46`) salta l'azienda con un lavoro già `FATTO` per quel giorno: la chiave idempotente di `fn_accoda_lavoro` protegge solo i lavori vivi. La sync è idempotente. Nomi dei job invariati (`chiusura_scadenze_daily` è anche il codice del processo) |

**pgTAP nuovi:**

- `script/test-fuso-operativo-v1.sql` (22): sede unica, confini d'estate e d'inverno, giorno di 23 e
  25 ore, il caso delle 23:30 UTC, indipendenza dal fuso di sessione (la sessione gira a +14
  apposta), un'azienda a Tokyo, NULL → NULL, fail-loud.
- `dbops/test-oggi-dal-fuso-aziendale-v1.sql` (4) — **D-8, il presidio**: nessuna funzione, vista,
  `DEFAULT` di colonna o di parametro usa `CURRENT_DATE`, `LOCALTIMESTAMP`, `LOCALTIME`,
  `now()::date`, `current_timestamp::date` (commenti esclusi, oggetti delle estensioni esclusi),
  più una controprova che la scansione vede. **Zero eccezioni dichiarate.** Senza le tranche è
  rosso su funzioni, viste e `DEFAULT`.
- `dbops/test-chiusura-scadenze-una-volta-al-giorno-v1.sql` (5): la seconda sveglia del giorno
  con i lavori `FATTO` non accoda e li conta come saltati; un lavoro in `ERRORE` si riaccoda da
  solo.
- ⚠️ **Corsa di Tid su dbdev dopo l'apply (2026-10-09):** questo file e il fratello
  `test-fn-accoda-chiusura-scadenze` rossi al test 1 (2 accodati su 4). Non un difetto della
  funzione: le due aziende vere avevano già il lavoro della giornata `FATTO` (il job era girato), e
  dal `-46` vengono saltate. I test **supponevano** un giorno senza lavori; ora lo **costruiscono**
  (rinominano le chiavi di oggi, come già faceva il test 6 del fratello), e il fratello usa il
  giorno aziendale nelle chiavi. Provati su `zeroerp_ci` migrato, anche simulando il job già
  eseguito: 5/5 e 6/6. ✅ Rilanciati da Tid: verdi.

⭐ **`%TYPE`** (Tid, 2026-10-09). I corpi vengono da `pg_get_functiondef`, che scioglie i `%TYPE`
della firma: quelli già scritti nell'ultimo changeSet di ogni funzione sono stati **ripresi**
(anche nei rollback), e in questo giro si sono ancorati altri 50 parametri, colonne di
`RETURNS TABLE` e variabili che riflettono una colonna. Le voci rimaste a tipo esplicito sono
elencate per funzione nell'intestazione di ogni changeSet, col motivo (contatori, interruttori,
jsonb e testi di lavoro, valori calcolati, chiavi polimorfe, colonne di `django.auth_user`, il
giorno operativo). Argomenti e risultato di ogni funzione sono **byte-identici** al vivo.

**Prove** (SQL estratto dagli YAML, preCondition comprese, in transazione annullata su
`zeroerp_ci`, allineato a `20261009-31`; nessun runner, nessun apply):

- firme delle 67 funzioni riscritte byte-identiche; colonne, tipi e `reloptions` delle 8 viste
  identici; nessun `CURRENT_DATE` residuo in funzioni, viste e `DEFAULT`;
- `plpgsql_check`: zero errori sulle funzioni toccate (trigger compresi, con la loro tabella);
- la conversione dello storico provata su righe costruite (una scritta da `zeroerp_app`, una da
  owner) e ritorno col rollback;
- il `-61` e il suo rollback su `pgagent.pga_schedule`;
- guardrail statici del repo tutti verdi; tre `timestamp` senza fuso dichiarati col marcatore
  (`-42`, `-54`, `-58`: è il passaggio `data::timestamp AT TIME ZONE <fuso>`, che non arriva in
  nessuna colonna);
- **confronto pgTAP**: ogni file che tocca un oggetto cambiato, senza e con l'SQL estratto, stessa
  transazione annullata. Tranche 1-4 su 464 file: esiti identici (3998 `ok`, 230 `not ok` di base,
  dati di `zeroerp_ci`). Tutte le tranche (`-40`…`-60`) su **493 file** (ogni pgTAP che nomina
  un oggetto toccato, le fixture, la registrazione di magazzino, lo storico): esiti identici
  tranne due file caduti per un **deadlock** con un altro lavoro sul database nella stessa
  corsa; rifatti da soli, identici anche loro. I tre pgTAP nuovi sono rossi senza le tranche e
  verdi con; il fratello `test-fn-accoda-chiusura-scadenze` resta 6/6 col `-46` nuovo.
- Costo misurato (fatto datato, non motivo): `fn_data_operativa` ~6 µs a chiamata (20.000 righe:
  122 ms con la chiamata per riga, 2 ms con la sottoquery scalare); `fn_giorno_operativo` ~9 µs a
  riga, quasi tutto nella sottotransazione della rete di sicurezza di `fn_fuso_operativo` (una
  dashboard con mille attività: ~10 ms in più).

### 8.2 DB — resta

- **D-7, seconda metà, con T-5**: i ~236 pgTAP che usano `CURRENT_DATE` come «oggi» delle
  fixture sono coerenti finché sessione e azienda hanno lo stesso giorno; col fuso ostile in CI
  vanno portati a `fn_data_operativa()`. Si fa insieme alla CI ostile, che li fa emergere.
- Il guardrail statico gemello di D-8 sui changeSet non c'è: il presidio guarda il catalogo vivo
  e in CI gira dopo il migrate. Un guardrail anticiperebbe solo l'avviso.
- `script.fn_fuso_operativo` è la lettura che il backend userà (B-1): il `GRANT` a `zeroerp_app`
  c'è.

### 8.3 BE e FE

Ordine dei lotti (sessione backend, 2026-10-09): **L1** B-1, B-2 e il BB di B-3 → **L2** B-4 (filtri
per giorno; rimette verde `test_giornale_trasversale_perimetro`) → **L3** B-5 e le sedi di B-3 →
**L4** B-6, B-7, B-8, B-9 → **L5** F-1 … F-5. T-5 (CI ostile) insieme alla seconda metà di D-7:
Tid ha accettato (2026-10-09) che la CI resti rossa nel frattempo.

#### L1 — ✅ fatto il 2026-10-09 (non committato)

| Voce | Cosa |
| --- | --- |
| B-1 | BB `apps/core/services/fuso_aziendale.py`: `fuso_aziendale()` (da `script.fn_fuso_operativo()` via `CoreRepository.get_fuso_operativo`, cache di processo senza invalidazione, T-6), `oggi_aziendale()`, `attiva_fuso_aziendale()`, `fuso_aziendale_forzato(nome)` per i test. Nessun ripiego: `E_CONFIG_MANCANTE` dal DB, `ImproperlyConfigured` se il nome non e' noto a Python |
| B-1 | `FusoAziendaleMiddleware` (subito dopo `RequestContextMiddleware`) attiva il fuso per ogni richiesta; `apps/core/management/comando_aziendale.ComandoAziendale` per ogni management command (i 10 di oggi ci passano; presidio `test_comandi_fuso_aziendale` trova i comandi sul disco) |
| B-1 | `/core/me/` porta `fuso_aziendale` (nome IANA), dalla stessa cache: e' cio' che il FE leggera' (F-1) |
| B-2 | `settings.TIME_ZONE = 'UTC'` |
| B-3, B-6 | `locale_formatters.in_ora_locale` e `oggi_aziendale` **dichiarano** il fuso, non si appoggiano a quello attivato. Le quattro sedi che leggevano il fuso implicito (`timezone.localdate()`/`localtime()`: `lista_export_service`, `document_generation_service._today`, `vendite_service` ritardo, `LottiPerMeseView`) passano dal BB. I due test con `override_settings(TIME_ZONE=…)` passano a `fuso_aziendale_forzato` |
| test | `ZeroErpTestRunner` legge il fuso vero prima della suite e richiude la connessione (dentro un `SimpleTestCase` la lettura sarebbe vietata, e `JwtAuditMiddleware` si accende solo su una connessione aperta). `tests/db/test_fuso_aziendale_db`: Python e DB danno lo stesso giorno a ±30 min dalla mezzanotte aziendale, d'estate e d'inverno |

Prove: suite Django completa con `ZEROERP_TEST_DB_E2E=1`, 6387 test, un solo rosso **estraneo**
(`test_error_policies_divergenza_db`: il ritiro di `E_VENDITE_RIGA_GIA_PROPAGATA` e' gia' nel DB e
non ancora rigenerato in git, da un altro brief); ruff e cancello mypy verdi.

#### L2 — ✅ fatto il 2026-10-09 (non committato)

| Voce | Cosa |
| --- | --- |
| B-4 | BB `apps/core/db/_helpers.predicato_giorno_operativo(colonna, da, a) -> (sql, params)`: `col >= fn_inizio_giorno_operativo(da) AND col < fn_inizio_giorno_operativo(a + 1)`, giorni dell'azienda e `a` incluso. **Una forma sola**: SQL costante con la guardia `%s::date IS NULL OR …` (Django lega lato client, il planner semplifica), quindi sta sia nei `conditions.append` sia nei `WHERE` costanti col conteggio di ripiego. Colonna validata da regex (finisce interpolata) |
| B-4 | Le 12 sedi di §4.2 a nello stesso giro: giornale trasversale, `audit_log` e `job_run_log` (forma B: anche il confine alto compreso), `error_log`, audit permessi, audit di amm_software (le due forme miste), email log, movimenti di magazzino, pratiche, articoli (forma D, `::date` sulla colonna), coda lavori e coda stampa (forma C: il `+1 giorno` in `gestione_service` sparisce) |
| B-4 | `maintenance_repository.list_job_summary`: il mese di ripiego di `started_at` passa da `fn_giorno_operativo` |
| contratto | Le view che passavano la data come stringa non validata (tracciamento, email ×2, pratiche, audit di amm_software) usano `qp_iso_date_optional`: una data malformata e' `400 E_VALIDATION_INPUT`, non piu' un `500` dal cast nel DB; firme a `date` fino al repository |
| test | `test_predicato_giorno_operativo` (forma); `tests/db/test_predicato_giorno_operativo_db`: confini costruiti a ±30' dalla mezzanotte aziendale d'estate e d'inverno, solo-da/solo-a, sessione a +14, indice utilizzabile con `enable_seqscan = off` e la controprova di `col::date`, le 12 sedi attraversate coi filtri accesi (parametro fuori posto = errore SQL). `test_giornale_trasversale_perimetro` chiede `oggi_aziendale()` invece di `date.today()`: e' la sua stessa domanda (il giorno della riga appena scritta), che con `TIME_ZONE = 'UTC'` `date.today()` non sapeva piu' fare. Quattro test unitari che fissavano la forma vecchia dell'SQL aggiornati |

**Fatto datato (EXPLAIN, 2026-10-09, DB di sviluppo, `enable_seqscan = off`):** col predicato nuovo
i quattro rami di `script.vw_giornale_entita` entrano dai loro indici per tempo
(`ix_event_log_event_time`, `ix_fatturazione_lotti_log_data_ora`,
`ix_fatturazione_lotti_task_runs_started_at`, `ix_fatture_log_data_ora`).

⚠️ **Semantica per sede:** i confini sono provati una volta sul BB; per sede si prova la giuntura
(SQL e parametri). Con una riga costruita la prova solo il giornale. Se si vuole la riga costruita
per ognuna delle 12, e' lavoro a parte: dichiararlo qui come debito, non come fatto.

#### L3 — ✅ fatto il 2026-10-09 (non committato)

| Voce | Cosa |
| --- | --- |
| B-5 | `CURRENT_DATE` → `(SELECT script.fn_data_operativa())` in **31** punti SQL di 15 file (la forma del team DB nelle istruzioni: una valutazione per istruzione): date di documenti e registrazioni (`COALESCE(%s, …)` di fattura, DDT, reso, pagamenti ×2, amm_software), validita' e filtri «valido oggi» (lookup ×5, contratti, listini, soggetti, pagamenti, dbops, documenti), anzianita' (`vendite_repository` ×3), le espressioni letterali di `tipi_ruolo_tipi_indirizzo` e `clienti`. Commenti che descrivevano `CURRENT_DATE` riallineati |
| B-3 | `date.today()` → `oggi_aziendale()` in 20 sedi di 12 file (default dei form, guard «attivo oggi», competenza del batch e del preventivo, scelta del listino, prompt dell'assistente, ...). La testata dell'ordine da offerta **omette** la data: decide il DEFAULT della colonna (`fn_data_operativa()`) |

#### L4 — ✅ fatto il 2026-10-09 (non committato)

| Voce | Cosa |
| --- | --- |
| B-6 | I tre difetti fuori sede: l'email di conferma del reset password scrive l'ora dell'azienda (`format_datetime`, era UTC); le righe di esempio del digest (`_riga_compatta`) scrivono gli istanti nell'ora dell'azienda (era `str()`, UTC con `+00:00`); `_date_formatting` prende il giorno dell'azienda da una stringa ISO con l'ora (tagliava i primi 10 caratteri, il giorno UTC) |
| B-7 | `payload_validators.optional_istante`: un istante in ingresso senza offset e' `400 E_VALIDATION_INPUT`. Sospendi/riattiva pratica lo usano; service e repository ricevono `datetime` |
| B-8 (log) | `apps/core/logging_formatters.FormatterUtcIso` sul formato `verbose`: `2026-10-09T14:32:45.798Z` |
| B-8 (timer) | T-9: `sveglie.json` dichiara `dovuto` sulle tre sveglie calendariali (digest giornaliero 07:00, settimanale lunedi' 07:30, fatturazione differita il 1° dalle **00:00**, T-4a), che si svegliano ogni ora (`*:00`). Comando nuovo `e_dovuto <unit>` (exit 0 lavora / 1 salta / **255** guasto: un guasto che uscisse 1 systemd lo salterebbe in silenzio); `MaintenanceRepository.corsa_riuscita_dal` (conta solo una corsa riuscita da inizio periodo); `ExecCondition=` nei tre `.service`; `jobname_corsia` estratto in `run_fatturazione_batch` per il confronto col dichiarato; il dettaglio del processo espone `dovuto` accanto a `oncalendar`. Presidi: `test_sveglie` 17-21, `test_e_dovuto`, `tests/db/test_corsa_riuscita_dal_db`, `test_contratto_liveness_vs_deploy` (intervallo = periodo + passo), `test-install-timers.sh` verde, unit resi verificati con `systemd-analyze verify`. ⚠️ Sull'host serve `install-timers.sh` per rendere i template nuovi |
| B-9 | ruff **`DTZ`** acceso a zero su tutto il repo (64 rilievi sanati prima: 45 `date.today()` di test e smoke → `oggi_aziendale()`; righe finte del DB costruite naive → `tzinfo=UTC`; `noqa` col motivo sui naive voluti e sulle tre `strptime` che leggono una data). `test_presidio_fuso_sql`: nessun `CURRENT_DATE`/`LOCALTIMESTAMP`/`now()::date` nel codice. `tests/db/test_presidio_fuso_sql_db`: nessuna colonna istante — **elenco dal catalogo del DB** (95 nomi il 2026-10-09; 3 ambigui, `date` altrove, esclusi e calcolati) — passa al calendario della sessione (`col::date`, `col >= %s::date`, `date_trunc(…, col)`); zero rilievi dopo L2, controprova sulle forme ritirate |

Prove L1-L4: suite Django completa con `ZEROERP_TEST_DB_E2E=1`, 6423 test, l'unico rosso e'
l'estraneo `test_error_policies_divergenza_db` (vedi L1); ruff e cancello mypy verdi.

#### L5 (FE) — ✅ fatto il 2026-10-09 (non committato)

| Voce | Cosa |
| --- | --- |
| F-1 | `core/utils/date.js` riceve il fuso dell'azienda (`impostaFusoAziendale`, chiamata dallo store auth a ogni `fetchProfile` con `fuso_aziendale`). `displayTimestamp`/`displayTime` convertono nel fuso dell'azienda (`Intl.DateTimeFormat` con `timeZone`); `displayDate` su una stringa con l'ora prende il **giorno aziendale** (`giornoAziendale`), non i primi 10 caratteri |
| F-2 | `oggiAziendale()`/`oggiAziendaleString()` (giorno dell'azienda in una `Date` locale a mezzanotte); `addDaysToToday` e quindi `defaultFiltroDataDa*` poggiano li'. Ritirate le copie: i default `new Date()` dei form (13), i `toDateString(new Date())` (4), le due `todayLocalDate`, gli «oggi a mezzanotte» a mano (`ContrattoDrawer` ×2, `CloneVersioneDrawer`, `severity.js`, `ArticoloBomDrawer`, `PreventiviDrawer`) via `giornoDi`, anno/mese correnti (dashboard competenza, lotti, registro numerazione, accettazione preventivo, store pratiche), i `min-date`, la concatenazione `YYYY-MM` (`toMeseString`) |
| F-3 | Ogni `new Date('YYYY-MM-DD')` e `new Date(s + 'T00:00:00')` → `parseIsoDate` (data di nascita del soggetto, qualifica del fornitore, scadenza della pratica, conto bancario, badge CHIUSA di `severity.js`, competenza dei lotti, testate di DDT/ordini/resi/preventivi, versioni di listino, UoM articolo) |
| F-4 | `SospensionePraticaDialog`: precarica con `istanteComeOraAziendale(adesso())`, salva `toTimestampString(oraAziendaleComeIstante(d))` — l'operatore legge e digita l'ora dell'azienda (il cambio legale e' provato). `AppTopbar` usa `displayOggiEsteso` |
| F-5 | `datePresidio.spec.js` allargato: fuori da `date.js` niente `new Date()` vuoto, `new Date(x)` a un argomento (ammessi `y.getTime()` e la costruzione numerica), `setHours(`, `toLocaleDateString`/`toLocaleTimeString`; controprova per mutazione (4 rossi su 4). **vitest gira a Pago Pago** (−11, `test.env.TZ`, T-5 lato FE). `date.spec.js` sugli istanti di confine (mutazione: 6 rossi su 8) |
| T-9 | `ProcessoDrawer` mostra `dovuto` in parole («ogni lunedi' dalle 07:30 (ora dell'azienda)», `amministrazione/dovutoSveglia.js` + spec, chiavi it/en) al posto di `*:00` |
| test | `auth.spec` 7 (il profilo consegna il fuso a `date.js`). `npm run verify` verde: lint, guard, 760 test, build |

#### Corretto fuori perimetro (2026-10-09)

`apps/core/tests/_contratto_processi.py` diceva che `*:0/N` con N ≥ 60 «gira ogni ora» e il suo
test lo fissava (`*:0/90` → 60). systemd 257 la **rifiuta** («Failed to parse calendar
specification»: verificati 59 accettato, 60 e 90 rifiutati) e il timer non partirebbe. Ora il
parser solleva, come systemd; il test elenca `*:0/60` e `*:0/90` fra le forme rifiutate e
conosce `*:MM`. Controprova: col vecchio `min(N, 60)` il test e' rosso.

#### Resta

- **T-5 lato Django**: Django tiene la sessione PG dei test sempre in UTC, quindi la finestra
  ostile la apre solo un **parametro** lontano nel DB di CI (es. `SYSTEM_FUSO_ORARIO =
  'Pacific/Kiritimati'` dopo il migrate). Tocca anche i pgTAP: da decidere col team DB insieme
  alla seconda meta' di D-7.
- **La riga di skip conta come corsa riuscita** (trovato in revisione, 2026-10-09):
  `fn_job_run_start` scrive la skip con `ok = TRUE` e `corsa_riuscita_dal` la conta, quindi una
  corsa a mano che tiene il lock all'ora della sveglia e poi fallisce fa saltare il periodo intero
  senza errore. Brief al team DB:
  [brief-db-corsa-saltata-non-e-una-corsa](brief-db-corsa-saltata-non-e-una-corsa.md); il BE
  attende il marcatore strutturale (niente filtro sul testo di `message`).

⚠️ **Da sapere (scritto dopo L1, chiuso in L3):** con `TIME_ZONE = 'UTC'` i ~25 `date.today()` di §4.2 c rispondono il
giorno **UTC** (prima: Roma). Fra mezzanotte e le 02:00 di Roma sbagliano di un giorno: e' il
difetto reso visibile (B-2), si chiude in L3. Anche l'ora dei log e' ora UTC, ma ancora **senza
offset** finche' non arriva B-8 (L4).
