# Brief DB — le tre liste del drawer lotto

> **Cos'è.** Il **piano di sviluppo lato database** per portare a
> `<ListaConfigurabile>` le tre tabelle del drawer di un lotto di fatturazione:
> **documenti**, **tentativi dei task**, **segnalazioni**. Nasce dalla nota del
> team BE/FE del **2026-08-21**, che chiedeva «tre `ui.lista_definizione` sullo
> stampo di `vendite.commesse_attivita`».
>
> ⭐ **La richiesta era di seedare tre liste. La misura del terreno dice che una
> sola delle tre è un seed**: la seconda ha una sorgente doppia e divergente da
> riunificare, la terza **non ha una sorgente** — i suoi contatori esistono, le
> sue righe no. Il lavoro DB è reale, e questo documento è la ragione per cui
> non lo si è fatto al volo.
>
> ⛔ **Niente è stato applicato.** Nessuna migrazione, nessuna scrittura sul
> database, nessun CSV toccato. Questo documento è un piano.
>
> **Correlati:** [piano-migrazione-primevue-5.md](piano-migrazione-primevue-5.md)
> §8-bis/§9 (inventario e registro delle liste) ·
> [brief-db-seed-liste-dashboard-e-commessa.md](../work-done/brief-db-seed-liste-dashboard-e-commessa.md)
> (l'8° lotto, il precedente più vicino) ·
> [brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](../work-done/brief-db-perimetro-emittente-liste-e-gerarchia-ba.md)
> (`multi_emittente`).

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| ✅ **Regge** | `multi_emittente = f` su tutte e tre, **per un motivo verificabile** e non per sensazione · `vista_sql = NULL` · il meccanismo di seed (append ai 4 CSV, nessun loader nuovo) | §1.1 |
| 🔴 **La richiesta sottostima il lavoro** | Lista A = seed + passata BE · Lista B = **due sorgenti divergenti** da riunificare · Lista C = **oggetto nuovo** (fn di union che non esiste) | §1.2 |
| 🔴 **Difetti trovati misurando** | Il `codice errore` **non esiste su nessuno dei due log**: nessun writer cattura `CONSTRAINT_NAME` · `fn_list_lotto_task_runs` è codice morto che dice il contrario del BE · il tab dei task tronca a 100 senza dirlo | §1.3 |
| ✅ **Decisioni prese** | D-1…D-9, con le risposte di Tid del 2026-08-21. Q4 **chiusa leggendo il codice**; Q1 chiusa in due giri, il secondo dei quali ha corretto un mio errore di livello (job ≠ task) | §3 |
| 📋 **Il piano** | Tre lotti: **L1** terreno (fn task_runs + codice errore sui log) → **L2** sorgente segnalazioni → **L3** i seed delle tre liste | §5 |
| 🔵 **A carico del BE/FE** | 6 consegne, di cui **3 bloccano** la nascita delle liste. Da concordare **prima** di L3, non in consegna | §4 |
| ✅ **Domande aperte** | **Zero.** Q-1 e Q-2 chiuse il 2026-08-21 | §6 |
| ⭐ **Il perno da non perdere** | «Job» ha un'ancora e non serve una colonna nuova: l'`event_time` dell'ultimo `PIPELINE_STARTED` in `vendite.event_log`. ⚠️ Non il `correlation_id`, che due corse condividono | §3 D-6 |
| ⭐ **STATO** | **L1 e L2 CHIUSI**. L1: 6 changeSet `-38`…`-43` + 2 codici `W_`, **applicati da Tid**. L2: `-44` con `fn_list_lotto_segnalazioni` e 2 pgTAP (11/11 e 8/8), **attende il migrate**. Prossimo: **L3**, i seed delle tre liste — ⛔ ma **BE-1 blocca** e va chiesto ora | §5 · §7 |

---

## 1. Analisi critica — la misura del terreno

Rimisurata il **2026-08-21** contro la doc auto-generata `dbzero`, i CSV di seed,
il presidio `scripts/gen_seed_lista.py` e il codice BE/FE. Non contro gli YAML.

### 1.1 Ciò che regge, e non si riapre

| Punto della nota | Verifica |
| --- | --- |
| **`vista_sql = NULL`** perché le righe arrivano da un endpoint di dominio | ✅ Corretto, ed è la forma delle 6 liste dell'8° lotto. ⚠️ **Con una conseguenza da mettere in conto**: con `vista_sql` nullo il guard `ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente` **salta**. Nessun cancello DB intercetta un `campo_sorgente` sbagliato — l'unico presidio è quello Python, che oggi su queste tre liste non riesce nemmeno a girare (§1.2) |
| **`multi_emittente = f`** perché «si aprono già dentro un lotto, che l'emittente ce l'ha» | ✅ **Confermato strutturalmente, non per sensazione**: `vendite.fatturazione_lotti.emittente_soggetto_ruolo_id` è **NOT NULL**. Un lotto ha un emittente per costruzione, e non può averne due. Coerente col quadro d'insieme: la lista madre `vendite.lotti` (id 12) è `t`, le tre figlie `f`. Il flag è protetto dal trigger owner-only `trgfn_lista_definizione_guard_multi_emittente`, quindi è una scelta di seed presa esattamente dove va presa |
| Il **meccanismo di seed** | ✅ Append ai quattro CSV in `80_data/sql/ui/`, **nessun loader nuovo**: il mirror ri-ancorato `20260806-15` è `runOnChange` e ripesca il CSV. Id liberi: **definizione 45-47**, **colonna 490+**, **preset 45-47** |
| Lo **stampo** `vendite.commesse_attivita` (id 38) | ✅ È il precedente giusto: `vista_sql = NULL`, 15 colonne, ordinamento **dentro una funzione DB** (`fn_list_commessa_attivita`) — l'unica del progetto, e il presidio sa già leggerne la whitelist |

⚠️ **Token NULL diversi per file.** `lista_definizione.csv` dichiara
`nullValue: "NULL"` e vuole il **letterale `NULL`**; gli altri tre dichiarano
`nullValue: ""` e vogliono la **cella vuota**. Sbagliarlo su `vista_sql` produce
`''` invece di NULL, il guard non salta più e l'apply muore con
`E_UI_VISTA_SQL_NON_TROVATA`.

### 1.2 🔴 Le tre liste non sono tre casi dello stesso lavoro

#### Lista A — `vendite.lotto_fatture`: l'endpoint c'è, la whitelist no

`VenditeRepository.list_lotto_fatture` è già **paginato**, con
`_add_scope_emittente` sul perimetro emittente e un `total_count`. È la sola
delle tre che nasce da una base sana.

Ma la sua whitelist di ordinamento — `_SORT_COLUMNS`, costante di modulo in
`vendite_repository.py` — ha **tre voci**: `fattura_id`, `nominativo`,
`totale_doc`. Contro la regola del **nucleo** del presidio (*data,
numero/codice, ragione sociale, BA, id fiscale, utility, totale, stato ordinano
SEMPRE*), le colonne richieste nascono così:

| nucleo | colonna | esito oggi |
| --- | --- | --- |
| data | `data` | 🔴 fuori whitelist |
| numero/codice | `numero` | 🔴 fuori whitelist (`fattura_id` è un'**altra** colonna) |
| ragione sociale | `ragione_sociale_completa` | 🔴 **la chiave BE è `nominativo`** — vedi sotto |
| id fiscale | `id_fiscale_univoco_cf_piva` | 🔴 fuori whitelist |
| stato | `stato_doc_fiscale_descrizione`, `stato_esecuzione` | 🔴 fuori whitelist |
| totale | `totale_doc` | ✅ |

⚠️ **La trappola della ragione sociale.** Il presidio confronta il
`campo_sorgente` del seed con le **chiavi** del dict, non con i valori. La
chiave è `nominativo`, il campo del payload — e quindi il `campo_sorgente` — è
`ragione_sociale_completa`. Marcarla `ordinabile=t` la fa segnalare come
*freccia bugiarda*; marcarla `f` rompe il nucleo. **L'uscita pulita è la
rinomina della chiave lato BE**: è esattamente il difetto di
`anagrafiche.clienti` stanato il 2026-08-01, che era lì da maggio.

E poi il buco vero: **«errore (codice, messaggio, quando)» non è nel payload e
non è sulla riga.** Il ponte `vendite.fatturazione_lotti_fatture` ha
`stato_esecuzione` e nient'altro: niente `error_code`, niente `error_message`,
niente timestamp dell'errore. Tre colonne su undici non hanno una sorgente, e la
sorgente naturale è la stessa della Lista C.

#### Lista B — `vendite.lotto_task_runs`: due sorgenti che dicono cose diverse

L'endpoint `/api/v1/vendite/lotti/<id>/task-runs/` **non è paginato**:
`PipelineRepository.list_lotto_task_runs` fa `LIMIT` (default 100, tetto 500),
**niente offset**, **niente `total_count`**, e `ORDER BY started_at DESC, id
DESC` **inchiodato nella query**. Nessuna whitelist ⇒ la lista non è mappabile
in `WHITELIST_BE` ⇒ il presidio la **salta**, e una lista saltata «è come non
aver fatto il controllo».

⛔ **E ci sono due verità per lo stesso elenco.** Esiste
`vendite.fn_list_lotto_task_runs`, che:

- ordina `started_at **ASC**, id ASC` — il BE ordina **DESC**;
- **non filtra `attivo`** — il BE filtra `attivo IS TRUE`;
- **non è chiamata da nessuno**: il BE legge la tabella direttamente.

Una funzione DB viva che nessuno usa e che, se qualcuno la usasse, darebbe un
elenco diverso da quello a video. È il caso che il progetto vieta
esplicitamente (nessuna logica duplicata fra livelli), e va chiuso in un verso o
nell'altro **prima** di seedare la lista.

Minore ma reale: il contatore del tab mostra `taskRuns.length`. Su un lotto con
più di 100 run dice «100» — un troncamento senza segnale.

#### Lista C — `vendite.lotto_segnalazioni`: non è un seed, è un oggetto nuovo

Oggi **non esiste nessuna sorgente di righe**. `fn_get_lotto_segnalazioni_summary`
ritorna **sei contatori**, e il tab del drawer rende tre `Tag`, non una tabella.
Le righe sarebbero l'unione di `vendite.fatture_log` (per documento) e
`vendite.fatturazione_lotti_log` (per lotto), e delle otto colonne chieste solo
due esistono davvero su entrambe:

| colonna chiesta | dov'è | note |
| --- | --- | --- |
| **quando** | `data_ora` su entrambe | ✅ |
| **messaggio** | `messaggio` su entrambe | ✅ |
| **livello** | `status` su entrambe | ⚠️ **domini diversi a CHECK**: `chk_fatture_log_status` ammette `('W','C')`, `chk_fatturazione_lotti_log_status` ammette `('I','W','C')` |
| **origine** FATTURA/LOTTO | **non esiste** | è il discriminante dell'union, da costruire |
| **documento** (ragione sociale) | **non sul log** | join a `vendite.fatture` → `cliente_snapshot->>'denominazione'`. NULL per costruzione sulle righe LOTTO |
| **importo** | **non sul log** | `f.totale_doc`. NULL sulle righe LOTTO |
| **fase** | solo su `fatturazione_lotti_log` | NULL sulle righe FATTURA — **il complemento esatto** di documento/importo |
| **codice** | ⛔ **da nessuna parte** | vedi §1.3 |

Il precedente formale è `vw_dash_competenza_errori`: union con NULL per metà
delle colonne e `NULLS LAST` sull'ordinamento.

### 1.3 🔴 Tre difetti trovati misurando, che valgono a prescindere dalle liste

**C-1 — Il codice errore non esiste su nessuno dei due log.** Né `fatture_log`
né `fatturazione_lotti_log` hanno una colonna `error_code`, e il `meta` non lo
porta: il pattern in uso (`fn_snapshot_fattura_lotto`, e i gemelli) fa
`GET STACKED DIAGNOSTICS v_err_msg = MESSAGE_TEXT, v_err_state = RETURNED_SQLSTATE`
e scrive `meta = {task, lotto_id, sqlstate, source}`. Ma `sqlstate` per un
errore di dominio è **sempre `P0001`**: come codice non distingue niente. Il
codice vero viaggia nel campo **`CONSTRAINT`** della diagnostica — è il
contratto DB→backend — e **nessuna funzione del database cattura
`CONSTRAINT_NAME`**: zero occorrenze su tutta la doc auto-generata. La colonna
`codice` della Lista C (e quella della Lista A) **non è seedabile finché
qualcuno non comincia a scriverlo**.
⚠️ E non è retroattivo: le righe di log già scritte non hanno il codice e non lo
avranno mai. Il rimedio è forward-only per costruzione.

**C-2 — `fn_list_lotto_task_runs` è codice morto e divergente** (§1.2).

**C-3 — `fatture_log` e `fatturazione_lotti_log` non hanno RLS**, e nemmeno il
ponte: la RLS sta su `fatturazione_lotti`, `fatture`, `fatture_righe`. Quindi
`fn_get_lotto_segnalazioni_summary` incrocia ponte + log **senza alcun filtro di
perimetro**, e i suoi contatori non sanno cosa sia un emittente.
✅ **Non produce un disallineamento** — è la risposta di Tid a Q3, e regge
strutturalmente: il lotto ha un emittente NOT NULL, chi non vede il lotto non
apre il drawer, e i documenti di un lotto stanno tutti sotto quell'emittente.
Ma **la lista nuova deve replicare quella scelta deliberatamente** (§3 D-5),
non ereditarla per distrazione: una `SECURITY INVOKER` che joinasse
`vendite.fatture` filtrerebbe, e allora il banner direbbe «3 critiche» e la
lista ne mostrerebbe 1.

---

## 2. Il seed proposto — tre liste, colonna per colonna

Forma e convenzioni dallo stampo della lista 38 e dall'8° lotto.
⚠️ **`ordinabile` è scritto nella colonna «ord.» come stato di arrivo**: `t`
significa «dopo la consegna BE/DB del §4», mai `t` con la speranza.

### 2.0 Le tre definizioni

| id | codice | descrizione | schema_dati | vista_sql | multi_emittente |
| --- | --- | --- | --- | --- | --- |
| 45 | `vendite.lotto_fatture` | Documenti del lotto | vendite | `NULL` | `f` |
| 46 | `vendite.lotto_task_runs` | Tentativi dei task del lotto | vendite | `NULL` | `f` |
| 47 | `vendite.lotto_segnalazioni` | Segnalazioni del lotto | vendite | `NULL` | `f` |

### 2.1 Lista 45 — `vendite.lotto_fatture`

Tutti i `campo_sorgente` sotto esistono già in `LottoFattureRow`, tranne i tre
marcati **🆕** (§4 BE-3).

| codice | campo_sorgente | tipo col. | tipo dato | formato | allin. | ord.def | ord. | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `numero` | `numero` | identificatore | numeric | | left | 10 | **t** | label FE componibile anno/serie/numero (come `dash_competenza_errori`) |
| `serie` | `serie` | informazione | string | | left | 20 | **t** | |
| `data` | `data` | informazione | date | date_short | left | 30 | **t** | |
| `natura` | `natura_doc_descrizione` | informazione | string | | center | 40 | **t** | Tag FE, severity neutra sulla nota di credito |
| `natura_codice` | `natura_doc_codice` | informazione | string | | left | 41 | f | supporto FE per la severity; `visibile=f` nel preset |
| `cliente` | `ragione_sociale_completa` | informazione | string | | left | 50 | **t** | ⚠️ dipende dalla rinomina BE-1 |
| `id_fiscale` | `id_fiscale_univoco_cf_piva` | informazione | string | | left | 60 | **t** | `sensibile=f`, come sulle liste 6 e 12 |
| `stato_doc` | `stato_doc_fiscale_descrizione` | informazione | string | | center | 70 | **t** | Tag FE |
| `stato_doc_codice` | `stato_doc_fiscale_codice` | informazione | string | | left | 71 | f | i gate FE usano SEMPRE il codice (lezione B-4); `visibile=f` |
| `stato_esecuzione` | `stato_esecuzione` | informazione | string | | center | 80 | **t** | Tag FE |
| `totale_doc` | `totale_doc` | informazione | numeric | currency_eur | right | 90 | **t** | ✅ già in whitelist |
| `totale_a_pagare` | `totale_a_pagare` | informazione | numeric | currency_eur | right | 100 | **t** | |
| `errore_codice` 🆕 | `errore_codice` | informazione | string | | left | 110 | f | §6 Q-2 |
| `errore_messaggio` 🆕 | `errore_messaggio` | informazione | string | | left | 120 | f | testo libero |
| `errore_quando` 🆕 | `errore_quando` | informazione | datetime | datetime_short | center | 130 | f | |
| `azioni` | *(vuoto)* | azione | string | | center | 999 | f | il `RowActionsMenu` c'è già |

**Preset 45** — `lotto_fatture_default`, `ambito=sistema`, `is_default=t`,
`pagina_dimensione=25`, `ordinamento_default` **vuoto** (ordine storico
dell'endpoint: `fllf.fattura_id ASC`). Precedente esplicito: la lista 38 fa così.
`fissata=t` su `numero`; `visibile=f` su `natura_codice` e `stato_doc_codice`.

### 2.2 Lista 46 — `vendite.lotto_task_runs`

| codice | campo_sorgente | tipo col. | tipo dato | formato | allin. | ord.def | ord. | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `fase` | `fase` | identificatore | string | | left | 10 | **t** | il `.vue` mostra la fase e ripiega su `task_code` quando è nulla |
| `task_code` | `task_code` | informazione | string | | left | 20 | **t** | |
| `tentativo` | `tentativo` | informazione | numeric | | right | 30 | **t** | |
| `esito` | `task_stato` | informazione | string | | center | 40 | **t** | Tag FE |
| `inizio` | `started_at` | informazione | datetime | datetime_short | center | 50 | **t** | |
| `fine` | `ended_at` | informazione | datetime | datetime_short | center | 60 | **t** | |
| `errore_codice` | `error_code` | informazione | string | | left | 70 | **t** | ⚠️ obbligata dal nucleo, vedi sotto |
| `errore_messaggio` | `error_message` | informazione | string | | left | 80 | f | testo libero |

Nessuna colonna azioni: sola consultazione, come `dash_competenza_errori`.

**Preset 46** — `lotto_task_runs_default`, `pagina_dimensione=10` (passo
compatto in drawer), `ordinamento_default` = `inizio desc` — cioè l'ordine che
il BE già applica, e **il primo caso in cui va dichiarato** invece che lasciato
implicito, perché il rilancio di uno step aggiunge righe in coda.

⚠️ **Il `codice` logico della colonna decide quali regole del nucleo scattano.**
Il presidio cerca le chiavi del nucleo **dentro `lista_colonna.codice`**, non
dentro `campo_sorgente`: chiamare una colonna `errore_codice` fa scattare la
famiglia *numero/codice* e obbliga `error_code` a essere ordinabile.
È corretto e lo lasciamo. Ma va detto ad alta voce che **rinominare una colonna
per schivare il presidio è possibile** — e non si fa.

### 2.3 Lista 47 — `vendite.lotto_segnalazioni`

Sorgente: `vendite.fn_list_lotto_segnalazioni`, che **non esiste** e nasce in L2.

| codice | campo_sorgente | tipo col. | tipo dato | formato | allin. | ord.def | ord. | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `quando` | `data_ora` | identificatore | datetime | datetime_short | center | 10 | **t** | |
| `livello` | `livello` | informazione | string | | center | 20 | **t** | Tag FE; dominio in D-4 |
| `origine` | `origine` | informazione | string | | center | 30 | **t** | `FATTURA` / `LOTTO` |
| `documento` | `documento_display` | informazione | string | | left | 40 | **t** | NULL sulle righe LOTTO |
| `importo` | `importo` | informazione | numeric | currency_eur | right | 50 | **t** | NULL sulle righe LOTTO |
| `codice` | `error_code` | informazione | string | | left | 60 | **t** | ⛔ vuoto finché non atterra C-1 |
| `messaggio` | `messaggio` | informazione | string | | left | 70 | f | testo libero |
| `fase` | `fase` | informazione | string | | left | 80 | **t** | NULL sulle righe FATTURA |
| `job_corrente` | `job_corrente` | informazione | boolean | yesno | center | 90 | **t** | D-6: `data_ora >=` l'ultimo `PIPELINE_STARTED`. `visibile=f` finché il filtro è acceso |
| `ritirata` | `disabilitato` | informazione | boolean | yesno | center | 100 | f | `visibile=f`; è il filtro, non la colonna |

**Preset 47** — `lotto_segnalazioni_default`, `pagina_dimensione=10`,
`ordinamento_default` = **`livello desc, data_ora desc`** (D-6: dalle più gravi,
poi le più recenti).

⛔ **`livello` non si ordina per il suo valore.** `C/W/I` in ordine alfabetico
mette `C` prima di `I` **per caso** e `W` in fondo **per caso**: sembra
funzionare finché non arriva un quarto livello. Il ramo della whitelist deve
mappare `WHEN 'livello' THEN` su un **rango esplicito** — `CASE status WHEN 'C'
THEN 3 WHEN 'W' THEN 2 ELSE 1 END` — così `desc` significa davvero «dalle più
gravi», ed è ciò che l'operatore ottiene anche cliccando l'intestazione.
⭐ **Il rango sta nella funzione, non in una colonna fantasma**: una colonna
`gravita` seedata solo per far quadrare l'`ordinamento_default` sarebbe catalogo
che non mostra niente — e il presidio, che confronta il default con le colonne
**offerte come ordinabili**, resta soddisfatto perché `livello` lo è.

⚠️ Tutti gli ordinamenti della lista vogliono **`NULLS LAST`**: metà delle
colonne è NULL per costruzione su metà delle righe. È la stessa avvertenza che
`dash_competenza_errori` ha già pagato.

### 2.4 Le chiavi i18n

Il drawer usa oggi `vendite.lotti.col_*` — **la stessa radice della lista 12**,
dove `vendite.lotti.col_stato_doc` esiste già e vale «Stato fiscale» su
un'**altra** colonna. Quattro liste sulla stessa radice significa che
rietichettarne una ne cambia altre tre in silenzio.

**Radici distinte, una per lista**: `vendite.lotto_fatture.col_*`,
`vendite.lotto_task_runs.col_*`, `vendite.lotto_segnalazioni.col_*`, con
`common.col_azioni` per la colonna azioni (già la convenzione delle liste 6 e
12). Le chiavi `vendite.lotti.col_*` oggi usate dal drawer restano dove sono
finché il FE non converte, e si tolgono con la conversione (FE-2).

---

## 3. Le decisioni

Le prime quattro rispondono alle domande dell'analisi del 2026-08-21.

**D-1 — Il drawer si sposta, e il piano lo deve dire.**
`LottoDrawer.vue` è oggi nel **Gruppo B** dell'inventario PrimeVue («tabelle
annidate, **non** vanno su `ListaConfigurabile`»). Risposta di Tid: *«annidate
anche nel senso di liste su diverse tab; comunque sì, segnaliamo nel piano che
stiamo spostando anche queste»*. → Il file passa a **Gruppo A** e §8-bis/§9 va
aggiornato **nello stesso giro** in cui nasce il seed, altrimenti restano due
documenti che dicono il contrario. *(Chi scrive il registro è chi consegna: il
6° lotto ha già insegnato che un inventario non barrato mente in silenzio.)*

**D-2 — L'ordinamento dei task_runs va nella funzione DB.**
Risposta di Tid a Q2, accolta. `vendite.fn_list_lotto_task_runs` viene estesa
con `p_limit / p_offset / p_order_by / p_order_dir` sullo stampo di
`fn_list_commessa_attivita` (`20260802-26`), e **il BE la chiama** al posto della
query diretta. Chiude la duplicazione C-2 e rende la lista verificabile: il
presidio sa già leggere una whitelist da funzione DB (`whitelist_funzione_db`
cerca i rami `WHEN '<nome>' THEN` nella doc auto-generata) — è la strada già
percorsa per la lista 38, l'unica del progetto, e la conferma che «si può
verificare come fatto per altre liste» è esatta.
⭐ **Corollario**: la whitelist va scritta come `CASE p_order_by WHEN 'fase'
THEN … END`, con i nomi **logici** delle colonne del seed. Un `format()` che
concatena il parametro non è leggibile dal presidio (e non sarebbe nemmeno
sicuro).

**D-3 — `attivo` si filtra: vince il BE.**
Nella riunificazione la funzione adotta `attivo IS TRUE`, che è ciò che il
drawer mostra oggi e ciò che l'operatore si aspetta. Il ramo che ignorava
`attivo` non è una scelta documentata: è una funzione ferma a prima che la
colonna esistesse.

**D-4 — I livelli sono tre e il loro dominio dipende dall'origine.**
Risposta a Q4, **chiusa leggendo il codice** e non da decidere:
`LottoSegnalazioniService.evaluate_lotto_status` compone
`critical = fatture_C + lotto_C`, `warning = fatture_W + lotto_W`,
`attention = **lotto_I**`. Quindi «attention» **è** `I` (info) — e il commento
nel service lo dice già: *«nel dominio attuale il terzo livello è "I" (info),
usato come attention operativa»*. Non è un quarto livello e non è il
`fatture_stato_esecuzione_errore_count`, che è il **ponte** e non un log.
⚠️ **La conseguenza per il seed**: `fatture_log` a CHECK ammette solo `('W','C')`,
quindi **una riga di livello INFO è per costruzione una riga di origine LOTTO**.
Filtrare `livello = INFO` restituisce solo righe LOTTO: è un fatto del dominio,
va nell'`etichetta_estesa` della colonna, e **non** va corretto allargando il
CHECK di `fatture_log` (nessuno scrive `I` su una fattura, e non c'è motivo).

**D-5 — La lista segnalazioni non filtra per emittente, e lo dichiara.**
Risposta di Tid a Q3: *«anche il lotto dipende da emittente, quindi non
dovrebbe esserci il disallineamento»* — verificato (§1.3 C-3). La nuova funzione
prende il perimetro **dal lotto** (che ha la RLS) e non ri-filtra le righe una
per una: così lista e contatori del banner contano la stessa popolazione **per
costruzione**, non per coincidenza. Il commento della funzione deve dire perché,
altrimenti al primo lettore sembra una dimenticanza.

**D-6 — «Job» ha un'ancora, ed è `vendite.event_log`. La regola è: ultimo job,
dalle più gravi.**

⭐ **Chiarito l'equivoco (Tid, 2026-08-21): i livelli sono tre, non due.**

| livello | cos'è | dove si vede |
| --- | --- | --- |
| **job** | una corsa di `run_pipeline` | un evento `PIPELINE_STARTED` in `vendite.event_log` |
| **step** | una fase del giro (DRAFT → EMESSA → …) | `stato_doc_fiscale_id` |
| **task** | un passo dello step (4 nel DRAFT) | `fatturazione_lotti_task_runs.task_code` |

Un job contiene più step, uno step contiene più task. La mia lettura precedente
si fermava al task, ed è per questo che sembrava una scelta fra «recente» e
«vivo»: la domanda giusta è **di quale corsa** è la segnalazione.

🔴 **E il job non ha un identificatore sulle righe.** `tentativo` è per
`(lotto_id, task_code, stato_doc_fiscale_id)` — un contatore **per task**, non
per corsa (`fn_start_lotto_task_run`). `tx_id` **non serve**: è una GUC di
**sessione** (`dbops.tx_id`), sopravvive alla singola corsa, e in assenza del
canale dblink degrada a `uuid_nil()`. Il `correlation_id` degli eventi è il
`lock_batch_id`, che nasce col lotto e **non si rigenera a ogni corsa**.

✅ **Quello che funziona è il tempo dell'evento.** Il runner scrive
`PIPELINE_STARTED` su `vendite.event_log` (`domain='PIPELINE'`,
`entity_type='LOTTO'`, `entity_id=lotto_id`, `event_time`) all'inizio di **ogni**
corsa. Quindi:

```sql
-- l'ancora dell'ultimo job
SELECT max(e.event_time)
  FROM vendite.event_log e
 WHERE e.domain = 'PIPELINE' AND e.entity_type = 'LOTTO'
   AND e.entity_id = p_lotto_id AND e.event_code = 'PIPELINE_STARTED'
```

e «segnalazione dell'ultimo job» = `data_ora >= quell'istante`. Non serve
nessuna colonna nuova, non serve un `job_id`, e non serve un'euristica a
finestra. ⚠️ **L'ancora è `event_time`, non `correlation_id`**: due corse dello
stesso lotto condividono il `lock_batch_id` e sarebbero indistinguibili.

**Come si comporta il DB oggi, misurato:**

- **Origine LOTTO** — all'avvio di ogni corsa il runner chiama
  `disattiva_segnalazioni_lotto_be`, che spegne le righe di
  `fatturazione_lotti_log` con `status = 'C'` e `meta->>'scope' = 'LOTTO'`
  (oppure `source = 'fatture_log'`). ⚠️ **Solo le `C`**: i `W` e gli `I` del
  lotto **non vengono azzerati e si accumulano attraverso i job**. Per le
  critiche la regola di Tid è quindi già vera per costruzione; per warning e
  info **no**, ed è lì che il filtro sul job serve davvero.
- **Origine FATTURA** — non viene azzerato **niente**, ed è una scelta scritta
  nel runner: *«i log per-fattura non si toccano: quelli li ritira il task DB
  che li ha scritti, quando il problema è risolto»*. Una segnalazione di fattura
  **sopravvive ai job finché il problema non è risolto**.

→ **Il predicato adottato**: la funzione ritorna **tutte** le segnalazioni vive
(`disabilitato IS FALSE`) con un flag calcolato **`job_corrente`** (vero se
`data_ora >= ancora`), e un parametro `p_solo_job_corrente` che **il preset
accende**. Ordinamento di apertura: **gravità (`C` → `W` → `I`), poi `data_ora`
DESC** — «partendo dalle più gravi», risposta di Tid a Q-1.
⚠️ Quando il filtro è acceso e restano fuori delle righe vive, la lista **deve
dirlo** («+N segnalazioni vive di corse precedenti»): una riga viva che sparisce
senza lasciare traccia è la classe di difetto in cui uno zero sembra un dato.

**D-9 — La regola dell'ultimo job vale sulla LISTA, mai sul GUARD.**
`blocks_next_step` legge lo stesso `fn_get_lotto_segnalazioni_summary` che
alimenta il banner, e **conta tutte le critiche vive**. Restringerlo all'ultimo
job farebbe avanzare un lotto con una critica irrisolta di una corsa
precedente: non è un dettaglio di presentazione, è il cancello che impedisce a
un documento rotto di diventare definitivo. Quindi il **summary non si tocca**,
e la divergenza col default della lista è **voluta e dichiarata** — non è la
divergenza che D-5 vieta, che era sul *perimetro emittente* (chi può vedere), non
sulla *finestra temporale* (cosa si mostra per primo).

**D-7 — Il codice errore si comincia a scrivere, forward-only.**
C-1 non si aggira: la colonna `codice` esiste solo se i writer la scrivono.
I punti di scrittura sono **cinque** e tutti censiti — quattro funzioni DB
(`fn_snapshot_fattura_lotto`, `fn_genera_scadenze_lotto`,
`fn_genera_scadenze_fattura`, `fn_reset_fondi_fattura`) più l'helper unico del
BE (`PipelineRepository._insert_fatture_log`, 2 call site) — e sul lato lotto
c'è **un solo imbuto**, `fn_log_pipeline_fase`. Si aggiunge
`CONSTRAINT_NAME` alla `GET STACKED DIAGNOSTICS` e lo si scrive in
`meta->>'error_code'`.
⭐ **In `meta`, non in una colonna nuova**: è un dato locale al log, non un asse
di ricerca, e le righe storiche non lo avranno comunque — una colonna NOT NULL
sarebbe una bugia e una colonna nullable non aggiunge niente a `meta`.
⚠️ E niente bonifica: le righe già scritte non hanno il codice e non c'è modo di
dedurlo. La colonna nasce vuota sullo storico, ed è giusto che si veda.

**D-8 — Le colonne di supporto FE vanno a catalogo, le chrome no.**
`natura_codice` e `stato_doc_codice` sono **dati** che il FE usa per la severity
e per i gate: vanno a catalogo con `visibile=f`. Le checkbox di selezione e la
colonna di espansione **no**: sono chrome del building block, come stabilito
nell'8° lotto §0.

---

## 4. 🔵 A carico del BE/FE — da concordare PRIMA di L3

Il metodo di questo cantiere è scritto e ha funzionato due volte: *guardare il
residuo prima di comporre il lotto, isolare il blocco che vale più liste,
chiederlo come passata unica*. Qui il blocco che vale di più è **BE-1**.
Nelle richieste si separa **ciò che blocca** da **ciò che migliora**.

| | Cosa | Blocca? |
| --- | --- | --- |
| **BE-1** | Estendere `_SORT_COLUMNS` (`vendite_repository.py`) al nucleo: `numero`, `data`, `id_fiscale_univoco_cf_piva`, `stato_doc_fiscale_descrizione`, `stato_esecuzione`, `serie`, `totale_a_pagare`, `natura_doc_descrizione`. **E rinominare `nominativo` → `ragione_sociale_completa`**: la chiave deve coincidere col campo del payload, che è ciò che il seed dichiara come `campo_sorgente` | 🔴 **sì** — senza, la lista 45 nasce con 5 nuclei rotti |
| **BE-2** | Chiamare `vendite.fn_list_lotto_task_runs` (nuova firma, D-2) al posto della query diretta in `PipelineRepository.list_lotto_task_runs`, esponendo `limit/offset/order_by/order_dir` e il `total_count` nell'envelope paginato | 🔴 **sì** — la lista 46 non ha un endpoint paginato |
| **BE-3** | Aggiungere al payload di `list_lotto_fatture` i tre campi `errore_codice`, `errore_messaggio`, `errore_quando` (D-6: ultima `fatture_log` viva del documento) | 🔴 **sì** per le 3 colonne; le altre 13 non lo aspettano |
| **BE-4** | Nuovo endpoint paginato `/lotti/<id>/segnalazioni/rows/` (o l'estensione di quello esistente) su `vendite.fn_list_lotto_segnalazioni` — l'attuale `/segnalazioni/` resta e continua a servire il banner | 🟡 dopo L2 |
| **BE-5** | Aggiungere `error_code` alla `GET STACKED DIAGNOSTICS` di `_insert_fatture_log` (D-7), simmetrico a quanto fa il DB | 🟡 migliora |
| **FE-1** | Registrare le tre liste in `WHITELIST_BE` (`scripts/gen_seed_lista.py`) e nel registro `_LISTE` di `test_liste_configurabili_seed.py`. ⚠️ Per la 46 il percorso è quello della **doc auto-generata** della funzione, non un sorgente Python | 🔴 **sì** — altrimenti le liste vengono *saltate*, cioè dichiarate a posto senza essere guardate |
| **FE-2** | Convertire i tre tab a `<ListaConfigurabile>`, spostare le chiavi i18n sulle radici nuove (§2.4), aggiornare §8-bis/§9 del piano PrimeVue (D-1) | 🟡 dopo L3 |

⚠️ **Contare le `<Column>` del `.vue` contro le righe seedate prima di dire
«pronta»**: è la lezione di `storico.audit_log`, tre volte. Qui il drawer ha
**due** `<DataTable>` e un tab che tabella non è: un grep sui `field=` non è una
misura.

---

## 5. Il piano — tre lotti

### L1 — Il terreno (non produce nessuna lista)

| # | changeSet | Cosa | Stato |
| --- | --- | --- | --- |
| P-1 | `20260821-38-update-fn-list-lotto-task-runs-paginata-mctit` | `DROP` + ricrea `fn_list_lotto_task_runs` con `p_solo_attivi/p_limit/p_offset/p_order_by/p_order_dir`, filtro `attivo` (D-3), whitelist come `CASE … WHEN 'fase' THEN …` leggibile dal presidio (D-2), `total_count` con le righe. ⚠️ **`DROP` obbligatorio**: `CREATE OR REPLACE` non cambia un `RETURNS TABLE`, e i parametri nuovi creerebbero un **overload** con chiamate ambigue | ✅ **scritto e provato** |
| P-2 | `…-39-update-fn-log-pipeline-fase-error-code-mctit` | L'imbuto del log di lotto accetta `p_error_code` e lo scrive in `meta->>'error_code'` (D-7). ⚠️ `DROP` + `CREATE` anche qui: un parametro nuovo crea un **overload**, e con la vecchia firma viva ogni chiamata a sei argomenti diventa ambigua | ✅ **scritto e provato** |
| P-3 | `…-40-update-fn-snapshot-fattura-lotto-error-code-mctit` | `CONSTRAINT_NAME` nella diagnostica + `error_code` in `meta`, con `jsonb_strip_nulls` | ✅ **scritto e provato** |
| P-4 | `…-41-update-fn-genera-scadenze-lotto-error-code-mctit` | idem | ✅ **scritto e provato** |
| P-5 | `…-42-update-fn-genera-scadenze-fattura-error-code-mctit` | ⭐ **Altra specie**: nessun errore catturato, il codice si **dichiara**. `W_SCADENZE_TOTALE_NEGATIVO` | ✅ **scritto e provato** |
| P-6 | `…-43-update-fn-reset-fondi-fattura-error-code-mctit` | idem, `W_FONDO_MINIMO_NON_RIPRISTINABILE`. ⚠️ `cause` resta accanto: vocabolario locale, non codice di catalogo | ✅ **scritto e provato** |
| S-1 | `80_data/sql/config/codici_errore.csv` | I due `W_` a catalogo, classe `AVVISO`. **Append al solo CSV**, nessun loader nuovo — e **nessuna** entry in `messaggi_errore` (opzione **b**) | ✅ **scritto** |
| T-1 | `db/pgtap/vendite/test-fn-list-lotto-task-runs-paginata.sql` | 13 asserzioni: ordine di default DESC, `total_count` invariante col `limit`, pagina 2 che non ripete la 1, gli 8 nomi della whitelist, fail-loud fuori whitelist (`P0001` **e** `throws_like` sul parametro), `NULLS LAST`, `attivo` | ✅ **scritto, 13/13** |
| T-2 | `db/pgtap/vendite/test-fatture-log-error-code.sql` | 8 asserzioni sul **percorso reale**: una fattura senza termine di pagamento fa sollevare `E_SCADENZE_TERMINE_MANCANTE` alla funzione figlia, e si guarda che cosa il wrapper scrive. ⭐ L'asserzione 5 è quella che misura il difetto (`isnt(..., 'P0001')`): senza, un ritorno alla forma vecchia lascerebbe la chiave presente e il test verde | ✅ **scritto, 8/8** |

**Verifica di P-1 (2026-08-21, in transazione annullata, nulla applicato).**
Corpo compilato e funzione esercitata su un lotto vero (`4210`, 12 task run):
ordine di default identico a quello che il backend produce oggi; `total_count`
invariante al `limit`; tutti e otto i nomi accettati; `p_order_by = 'meta'` e
`p_lotto_id = 0` sollevano **`P0001` / `E_PARAMETRO_INVALIDO`**; `NULLS LAST`
rispettato; la chiamata storica a tre parametri per nome continua a funzionare.
Poi il pgTAP nuovo, con la funzione iniettata nella stessa transazione: **13 ok
su 13**.

⚠️ **Cosa quella corsa NON ha misurato**: è girata come **owner**, quindi con la
RLS scavalcata — il pgTAP vero gira come `zeroerp_app`, e non lo si può
anticipare perché l'utente applicativo non può creare la funzione. Verificato
invece a parte, **come `zeroerp_app`**, tutto ciò che la fixture pretende:
`script.fn_pgtap_emittente_sr_operatore()` risponde, e SELECT/INSERT/UPDATE su
`fatturazione_lotti_task_runs` sono concessi. La corsa come applicazione resta
**da fare dopo il migrate**, insieme alla baseline di `vendite`.
⚠️ E va riverificato che `test-fatturazione-pipeline-task-runtime.sql` (che
chiama la funzione per nome alla riga 337) non regredisca: la firma storica è
preservata apposta, e le sue 2 righe sono entrambe `attivo = true`, ma è una
previsione finché la suite non gira.

**Verifica di P-2 (2026-08-21, in transazione annullata, nulla applicato).**
Sette controlli, tutti verdi: la chiamata a **sei argomenti posizionali** — la
forma esatta del backend — funziona identica e non scrive la chiave; col codice,
`meta->>'error_code'` lo porta e le altre chiavi di `meta` restano; una stringa
di soli spazi **non** crea la chiave; il parametro **vince** su un `error_code`
già presente in `p_meta`; i due guard preesistenti (`p_lotto_id`, `p_status`)
sollevano ancora `P0001` / `E_PARAMETRO_INVALIDO`; e
`pg_get_function_identity_arguments` conferma **una sola** firma — nessun
overload sopravvissuto al `DROP`.

⭐ **Un fatto che C-1 dava per probabile ed è stato misurato**: dentro un
`EXCEPTION`, `GET STACKED DIAGNOSTICS x = CONSTRAINT_NAME` restituisce davvero
il codice di dominio (verificato: `E_PARAMETRO_INVALIDO`). Il codice **c'è**,
va solo preso.

**Verifica di P-3, P-4 e T-2 (2026-08-21, in transazione annullata).**
I due corpi vengono dalla **doc auto-generata** — l'oggetto vivo — con un patch
mirato applicato sopra, **non ricopiati a mano e non ripresi da uno YAML**, che
su queste funzioni sarebbe stale. Entrambi compilano; `pg_get_function_identity_arguments`
conferma **una sola firma per nome, identica a prima** (nessun parametro
cambia, quindi nessun overload).
T-2 gira sul **percorso reale** — fattura senza termine → la figlia solleva →
il wrapper scrive — e dà **8 ok su 8**, comprese le due che presidiano
`fn_log_pipeline_fase` contro la funzione **già applicata**.

### 🔴 Correzione `%TYPE` su tutti e quattro (segnalazione di Tid, 2026-08-21)

**I tipi erano ancorati nella `RETURNS TABLE` ma non nella FIRMA né in tutti i
`DECLARE`.** La regola del progetto li vuole in tutti e tre i posti. Corretti
`-38`, `-39`, `-40`, `-41`, dopo aver verificato **uno per uno** che l'ancora
risolva al tipo identico — un `%TYPE` in firma è una fotografia, e se
risolvesse a un tipo diverso una chiamata esistente smetterebbe di risolvere.

⭐ **La scelta che vale la pena leggere: l'ancora di `p_stato_doc_fiscale_id` è
il CATALOGO, non la colonna.** `fatturazione_lotti_task_runs.stato_doc_fiscale_id`
è `integer`, `config.stati_doc_fiscale.id` è `bigint`, e ciò che il parametro
riceve è **un id di quel catalogo**. L'ancora semantica è la seconda — e per
fortuna è anche l'unica che non cambia il tipo del parametro. Ancorare alla
colonna avrebbe rotto ogni chiamante che passa un bigint.

⚠️ **Restano espliciti, e il codice lo dice invece di lasciarlo sembrare una
dimenticanza**: `p_limit`/`p_offset`/`p_order_by`/`p_order_dir` (la finestra con
cui si guarda un dato non è un dato, e `p_order_by` porta il **nome** di una
colonna, non il suo contenuto), `total_count` (un conteggio), i due `v_order_*`
(frammenti di SQL da interpolare) e `v_err_msg`/`v_err_state` (il testo di un
messaggio e uno sqlstate non sono valori di colonna). `v_err_code` invece **sì**:
è un codice di `config.codici_errore`, ed era la mia incoerenza — in `-39` lo
avevo ancorato, in `-40`/`-41` no.

~~⛔ Ma `-38` e `-39` sono già applicati e non ricevono la correzione~~ →
✅ **RISOLTO il 2026-08-21: Tid ha rifatto girare `-38` e `-39` e ha applicato
il resto.** La divergenza fra file e oggetto vivo non esiste più.

### ✅ P-5 e P-6: non erano lo stesso lavoro, e la decisione è presa

Misurando i cinque punti di scrittura si vede che sono **due specie diverse**, e
D-7 le aveva appiattite:

| | Che cosa fa | Il codice |
| --- | --- | --- |
| `fn_snapshot_fattura_lotto`, `fn_genera_scadenze_lotto`, `fn_log_pipeline_fase` | **cattura** un errore altrui in un `EXCEPTION` | si **prende** da `CONSTRAINT_NAME` ✅ fatto |
| `fn_genera_scadenze_fattura` («Totale a pagare negativo»), `fn_reset_fondi_fattura` («Minimo non ripristinabile: già postato») | **segnala una condizione propria**, `status = 'W'`, nessun errore catturato | non c'è niente da catturare: andrebbe **dichiarato** |

Quei due sono **avvisi**, non errori. Per dargli un codice servirebbero due
`W_` — e la famiglia oggi ha **due sole voci, entrambe infrastrutturali**
(`W_MESSAGGIO_ARITA`, `W_TXID_NOT_REGISTERED`): sarebbero i primi `W_` **di
dominio** del progetto. Non è una riga di codice, è un'estensione di
vocabolario.

⚠️ **E c'è un secondo ostacolo, misurato**: quei due punti scrivono la frase
**direttamente** in `fatture_log.messaggio`, senza passare da
`fn_log_and_raise_error`. Un'entry in `messaggi_errore` sarebbe **una seconda
copia della stessa frase, che nessuno compone** — ed è esattamente la forma che
il cantiere dei segnaposti ha già pagato («due testi scritti due volte che non
si compongono»). Ma un codice **senza** messaggio rompe il patto che le due
`W_` esistenti rispettano.

**Le tre strade erano:** (a) due `W_` con la loro entry in `messaggi_errore`,
accettando la doppia scrittura della frase; (b) due `W_` **senza** messaggio,
dichiarando che per gli avvisi scritti a mano il catalogo è solo un handle;
(c) niente codice, e la colonna «codice» della lista resta vuota sulle righe
`W` — che è il 100% delle righe di quei due punti.

✅ **DECISA da Tid il 2026-08-21: opzione (b).** Nascono
`W_SCADENZE_TOTALE_NEGATIVO` e `W_FONDO_MINIMO_NON_RIPRISTINABILE`, classe
`AVVISO`, **solo** in `codici_errore.csv`.

⭐ **E non è uno strappo: è una forma che il disegno prevede.** Verificato prima
di scrivere, perché era il prerequisito della scelta:

- la **FK va da `messaggi_errore` verso `codici_errore`** (test 3 di
  `test-codici-errore-identita`): un messaggio senza padre è vietato, un codice
  senza figli **no**. Il catalogo dei codici è il genitore, non l'indice dei
  messaggi;
- il cancello di `test-catalogo-messaggi-errore-completo` guarda **dai punti di
  sollevamento verso il catalogo**, mai il contrario: un codice mai sollevato
  non gli passa nemmeno davanti;
- `dbops.vw_codici_errore_da_dichiarare` cerca nei sorgenti i letterali
  **`'E_…'`** — un `W_` non la accende, ed è giusto: non c'è nessuna policy HTTP
  da dichiarare per un avviso che non viaggia in un envelope.

⚠️ **Un effetto di sequenza da sapere**: `80_data` gira **dopo** `20_code`, quindi
fra il migrate delle funzioni e quello del seed le due funzioni scrivono un
codice non ancora a catalogo. È innocuo — nessuna FK sul valore dentro un
`jsonb`, e nessuno lo risolve — ma va saputo invece che scoperto.

⚠️ **Corpo dalla doc auto-generata**, mai dagli YAML: su queste funzioni ci sono
più changeSet sovrapposti e solo l'ultimo conta. E il corpo copiato dall'auto-gen
**non è incollabile così com'è**: manca il `;` dopo `$function$`.

⛔ **I progressivi qui sopra sono indicativi e vanno riverificati al momento di
scrivere il file.** La numerazione `YYYYMMDD-NN` è una **sequenza globale per
data fra tutte le cartelle**, e più cantieri appendono nello stesso giorno: al
2026-08-21 la giornata arriva già a `-20` (il lotto 1 di `pagamenti`), ma il
primo libero va ricontato allora, non ora:

```bash
find db/changelog/migrations_v2 -name "2026MMDD-*" | sed 's#.*/##' | sort | tail -3
```

Stessa cautela sull'`id` di `config.messaggi_errore.csv` se il lotto ne
aggiungesse: è anch'esso una sequenza manuale, e una collisione fra due cantieri
dello stesso giorno è già successa (2026-08-18).

### L2 — La sorgente delle segnalazioni

| # | changeSet | Cosa | Stato |
| --- | --- | --- | --- |
| P-7 | `20260821-44-create-fn-list-lotto-segnalazioni-mctit` | Union `fatture_log` + `fatturazione_lotti_log` con `origine`, `documento_display` (dallo **snapshot** sulla riga fattura), `importo`, `error_code` (da `meta`), `fase`, `disabilitato`, **`job_corrente`** e `riga_key`; 9 parametri; whitelist chiusa col **rango di gravità** su `livello`; `SECURITY INVOKER`, perimetro dal lotto che **solleva** se non lo vede; `NULLS LAST` in entrambi i versi. ⭐ Ritorna `total_count` **e** `fuori_job_count` | ✅ **scritto e provato** |
| T-3 | `db/pgtap/vendite/test-fn-list-lotto-segnalazioni.sql` | 11 asserzioni: union completa, le due metà **complementari**, `p_solo_attive`, `livello=I` che dà **solo** righe LOTTO, ordine per gravità con la `I` in campo, `NULLS LAST` su `importo desc`, fuori-whitelist, e il lotto invisibile che **solleva** | ✅ **11/11** |
| T-4 | `db/pgtap/vendite/test-fn-list-lotto-segnalazioni-job.sql` | 8 asserzioni: nessuna corsa → tutto corrente; una corsa; **due corse** → l'ancora è la seconda; ⛔ e le due **condividono il `correlation_id`**, cioè la prova che da solo non discrimina; `fuori_job_count` che conta le vive escluse | ✅ **8/8** |

⚠️ `fn_list_lotto_segnalazioni` non ha una tabella propria: è una **lettura**.
Solleva in quattro casi, tutti su codici già registrati: `E_PARAMETRO_INVALIDO`
su `p_lotto_id`, su `p_origine`/`p_livello` fuori vocabolario e su `p_order_by`
fuori whitelist; `E_VALORE_MANCANTE` sul lotto non visibile.

**Verifica di L2 (2026-08-21/22, in transazione annullata, nulla applicato).**
Compila; **T-3 11/11** e **T-4 8/8** con la funzione iniettata.

⭐ **Verificato anche che il presidio dei seed sappia leggerne la whitelist**,
invece di darlo per buono: passando al corpo la stessa regex di
`whitelist_funzione_db` escono **esattamente** gli 8 nomi attesi, e nessuno dei
tre letterali del rango di gravità. Regge perché quei letterali sono
**maiuscoli** e la regex accetta solo `[a-z_0-9]+`: chi li mettesse in
minuscolo romperebbe il presidio senza toccarlo, ed è scritto nel changeSet
accanto al `CASE`.

⚠️ **Un dettaglio di forma da sapere**: il file si chiama `20260821-44` ma è
stato scritto a cavallo della mezzanotte. Il numero è libero, l'ordine regge e
la continuità con L1 si legge meglio così — ma se preferisci la data reale,
rinominarlo in `20260822-01` non ha controindicazioni: nessun altro changeSet
lo referenzia.

### L3 — I seed

Un solo changeSet non serve: si appende ai quattro CSV e i mirror `runOnChange`
riallineano.

| File | Righe |
| --- | --- |
| `80_data/sql/ui/lista_definizione.csv` | 3 (id 45-47) — ⚠️ `vista_sql` = letterale `NULL` |
| `80_data/sql/ui/lista_colonna.csv` | ~33 (id 490+) |
| `80_data/sql/ui/lista_preset.csv` | 3 (id 45-47) |
| `80_data/sql/ui/lista_preset_colonna.csv` | ~33 |

Verifica di consegna, **prima** di dire che è pronto:

```bash
backend/.venv/bin/python scripts/gen_seed_lista.py --verifica-ordinamento
```

Deve stampare `ok` sulle tre liste nuove — non «NON MAPPATA», che significa
«non lo so» (FE-1).

### L'ordine, e perché

**L1 prima di L3** perché la lista 46 senza P-1 non ha un endpoint paginato e la
colonna `codice` senza P-2…P-6 sarebbe una colonna vuota per sempre.
**L2 prima di L3** per la stessa ragione, più forte: la lista 47 senza P-7 non
ha proprio da dove leggere.
**BE-1 in parallelo a L1**, chiesto oggi: è l'unica cosa che non dipende da noi
e che, se arriva tardi, fa nascere rossa la sola lista che sarebbe pronta.

---

## 6. Domande — tutte chiuse

**Q-1 — ✅ CHIUSA (Tid, 2026-08-21): ultimo job, dalle più gravi.**
Vale sia per la riga «errore» della lista 45 sia per l'ordinamento della lista
47. La riga della 45 mostra la segnalazione **viva** del documento con gravità
massima e, a parità, la più recente. Il perimetro «ultimo job» ha l'ancora di
D-6 (`event_log.PIPELINE_STARTED`), e la sua conseguenza va dichiarata: le
segnalazioni di fattura **sopravvivono ai job per progetto**, quindi quando il
filtro ne lascia fuori di vive la lista deve contarle, non ingoiarle.

**Q-2 — ✅ CHIUSA (Tid, 2026-08-21): la colonna `codice` nasce subito.**
Su entrambe le liste, insieme al resto del seed. Resta vuota sullo storico —
il codice non è ricostruibile a posteriori (C-1) — e l'`etichetta_estesa` deve
dire da quando è popolata, altrimenti la prima domanda che riceve è «perché è
sempre vuota».
⚠️ Conseguenza sull'ordine dei lotti: la colonna può essere seedata prima che
L1 atterri, ma **non ha senso dichiararla `ordinabile=t` finché è vuota su
tutto**. Nasce `f` sulla lista 45 (dove comunque il campo è nuovo, BE-3) e `t`
sulla 46, dove `error_code` è una colonna vera della tabella e popolata da
sempre.

---

## 7. Registro

### 2026-08-21 · Nascita

Nota del team BE/FE: tre liste da seedare «sullo stampo di
`vendite.commesse_attivita`». Misura del terreno: **una** delle tre è un seed;
la seconda ha due sorgenti divergenti, la terza non ha sorgente. Chiuse Q0
(il drawer si sposta, il piano lo dirà), Q1 (l'ultima viva, con la precisazione
di D-6), Q2 (ordinamento nella funzione DB), Q3 (nessun disallineamento di
perimetro). Q4 chiusa leggendo `LottoSegnalazioniService`: *attention* = `I`.

Tre difetti censiti che valgono a prescindere dalle liste: il **codice errore
non è scritto da nessuno** (C-1), `fn_list_lotto_task_runs` è codice morto e
divergente (C-2), i log non hanno RLS (C-3, innocuo qui ma da dichiarare).

⛔ Nulla applicato.

### 2026-08-21/22 (quarto giro) · ✅ **L2 CHIUSO**

Un changeSet (`20260821-44`) e due pgTAP: **11/11** e **8/8**.
⛔ Non applicato.

`vendite.fn_list_lotto_segnalazioni` unisce i due log con `origine` come
discriminante. Le cose che il codice porta e che il piano non aveva scritto:

- ⭐ **La whitelist è leggibile dal presidio, ed è stato verificato invece di
  sperato**: passando al corpo la stessa regex di `whitelist_funzione_db`
  escono esattamente gli 8 nomi attesi. ⛔ Regge per un motivo fragile e
  scritto accanto al `CASE`: i tre letterali del rango di gravità sono
  **maiuscoli**, e la regex accetta solo `[a-z_0-9]+`. In minuscolo, `WHEN 'c'`
  verrebbe letto come il nome di una colonna ordinabile — *si romperebbe il
  presidio senza toccarlo*.
- ⚠️ **`messaggio` e `disabilitato` sono fuori whitelist di proposito**: il seed
  li offre `ordinabile = f`, e una voce che il seed non offre è una capacità
  irraggiungibile — la seconda direzione del presidio. Il pgTAP lo asserisce,
  così la scelta non si perde.
- ⭐ **`documento_display` viene dallo snapshot sulla riga fattura**, non da un
  join ad anagrafiche: `billing_account` ha la RLS, e il nome sparirebbe per
  una ragione che col log non c'entra.
- ⛔ **Il lotto non visibile SOLLEVA** invece di rispondere zero righe.
- 🔴 **T-4 dimostra il perché dell'ancora**: le due corse della fixture
  condividono il `correlation_id` — è il `lock_batch_id`, che nasce col lotto.
  Se l'ancora fosse quello, le due corse sarebbero la stessa cosa. L'unica che
  discrimina è l'`event_time`.

### 2026-08-21 (terzo giro) · ✅ **L1 CHIUSO**

**Sei changeSet** (`20260821-38` … `-43`), **due codici errore** appesi al solo
`codici_errore.csv`, **due pgTAP nuovi** e **uno esteso**.
✅ `-38` e `-39` **applicati da Tid**, senza regressioni. ⛔ `-40`…`-43` e il
seed dei due codici **attendono il migrate**.

| | Cosa | Prova |
| --- | --- | --- |
| `-38` | `fn_list_lotto_task_runs` paginata, whitelist chiusa, filtro `attivo`, `total_count` con le righe | pgTAP nuovo, **13/13** |
| `-39` | `fn_log_pipeline_fase` accetta `p_error_code` | 7 controlli + T-2 |
| `-40` · `-41` | `fn_snapshot_fattura_lotto` e `fn_genera_scadenze_lotto` **catturano** `CONSTRAINT_NAME` | T-2, **10/10** |
| `-42` · `-43` | `fn_genera_scadenze_fattura` e `fn_reset_fondi_fattura` **dichiarano** un `W_` | T-2 + `test-fondi-fattura`, **21/21** |

⭐ **La cosa che ha cambiato il piano**: misurando i cinque punti di scrittura
si è visto che erano **due specie**, e D-7 le aveva appiattite. Tre *catturano*
un errore altrui e ne prendono il codice da `CONSTRAINT_NAME`; due *segnalano
una condizione propria* e il codice non c'è da prendere — va **dichiarato**.
Da lì la decisione (b) di Tid e i primi due `W_` **di dominio** del progetto.

🔴 **Un mio errore corretto da Tid**: i tipi erano ancorati nella
`RETURNS TABLE` ma **non nella firma** né in tutti i `DECLARE`. Corretti tutti,
verificando uno per uno che l'ancora risolva al tipo **identico**
(`pg_get_function_identity_arguments` su ognuna: una sola firma, invariata).
⭐ E ne è uscita una regola utile: **`p_stato_doc_fiscale_id` si ancora al
CATALOGO, non alla colonna** — `fatturazione_lotti_task_runs.stato_doc_fiscale_id`
è `integer`, `config.stati_doc_fiscale.id` è `bigint`, e ciò che il parametro
riceve è un id di quel catalogo. L'ancora semantica è anche l'unica che non
rompe i chiamanti.

⚠️ **Metodo che ha retto e vale ripeterlo**: i corpi non sono stati ricopiati.
Si estraggono dalla **doc auto-generata** (l'oggetto vivo), si applica un patch
mirato che **fallisce se l'àncora testuale non è unica**, e si ricompone il
changeSet. Su cinque funzioni da 70 a 240 righe, la trascrizione a mano sarebbe
stata il rischio principale.

### 2026-08-21 (secondo giro) · «Job» non era «task»

Tid: *«forse c'è un equivoco: un job contiene più task, giusto? Valgono le
segnalazioni dell'ultimo **job**, partendo dalle più gravi»*. Aveva ragione, e
l'equivoco era mio: avevo letto la domanda al livello del **task**, e da lì
sembrava una scelta fra «la più recente» e «quella ancora viva». Al livello del
**job** la domanda è un'altra — *di quale corsa è questa segnalazione* — e ha una
risposta netta.

⭐ **L'ancora esiste già e non costa niente**: il runner scrive
`PIPELINE_STARTED` in `vendite.event_log` a ogni corsa, quindi «ultimo job» è
`data_ora >= max(event_time)` di quell'evento. Nessuna colonna nuova.
⚠️ **Tre candidati scartati, e vale la pena sapere perché**: `tentativo` conta
per task e non per corsa; `tx_id` è una GUC di **sessione** che sopravvive alla
corsa e degrada a `uuid_nil()` senza il canale dblink; `correlation_id` è il
`lock_batch_id`, che nasce col lotto e **due corse lo condividono**.

Misurato scendendo a controllare, e cambia cosa fa il filtro:

- il runner azzera a ogni corsa **solo le `C`** di `fatturazione_lotti_log` con
  `meta->>'scope' = 'LOTTO'`: i `W` e gli `I` del lotto **si accumulano** fra i
  job. Per le critiche la regola era già vera da sé, per gli altri due livelli
  no — ed è lì che il filtro serve davvero;
- i log **per fattura** non si azzerano mai, per scelta scritta nel runner: li
  ritira il task che li ha prodotti, quando il problema è risolto. Una
  segnalazione di fattura **attraversa i job finché è vera**.

→ **D-9**: la regola dell'ultimo job vale sulla **lista**, mai sul **guard**.
`blocks_next_step` conta tutte le critiche vive: restringerlo alla corsa
corrente farebbe avanzare un lotto con una critica irrisolta di prima.

Chiuse Q-1 (gravità poi data, con rango esplicito: `C/W/I` in ordine alfabetico
funziona **per caso**) e Q-2 (la colonna `codice` nasce subito).
