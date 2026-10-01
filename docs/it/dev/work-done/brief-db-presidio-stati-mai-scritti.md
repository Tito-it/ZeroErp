# Brief DB — Presidio C1: uno stato previsto dal modello e mai scritto

> **Destinatari:** team DB (`dev/db-tid`); una richiesta al backend in **§6**,
> che resta **viva** dopo la chiusura del lato DB.
>
> **Tipo:** brief di cantiere. Nasce dal candidato **C1** di
> [analisi-presidi-percorso-storto.md](analisi-presidi-percorso-storto.md)
> (chiusa il 2026-09-19), che per quattro settimane l'ha misurato senza che
> nessuno lo scrivesse. Qui si scrive.
>
> **Da leggere per primo: §2 — la forma — e §3-ter — quello che la scrittura
> ha smentito.**
>
> **Stato:** ✅ **CHIUSO LATO DB e archiviato in `work-done/` il 2026-09-21.**
> Letto dalle sorgenti: **applicato** su dbdev alle 11:37 (`20260921-15`, `-16`,
> `-17`, `-19` `EXECUTED` in `databasechangelog`; mirror `presidi` `RERAN`);
> a DB vivo il registro `dbops.stati_check_dichiarazioni` ha **40 righe** (26
> `APPLICAZIONE`, 14 `ESENTE`), `dbops.vw_stati_check_da_sanare` è a **zero**,
> la vista ottimizzata (0,6 s) è quella in `pg_class`, i due presidi sono a
> catalogo; **baseline pgTAP lanciata da Tid, nessuna regressione**
> (`dbops/test-stati-check-scrittori-v1.sql`, 14 test). Doc auto-gen
> rigenerata con l'apply. ✅ **E la richiesta BE §6 è chiusa il 21-09
> pomeriggio**: `backend/apps/core/tests/test_stati_check_scrittori_python.py`
> verifica le 26 righe `DICHIARATO_APPLICAZIONE` nei due versi — con il
> **secondo salto** (service → repository), perché il criterio «stesso file»
> del §6 dava rosso su 8 righe su 26 per l'architettura a tre layer, non per un
> difetto (dettaglio in
> [brief-be-presidio-ui-action-e-canale-campi.md §7](brief-be-presidio-ui-action-e-canale-campi.md)).
> ✅ L'ultima riga al team DB — `presidi.csv`, `presidiato_da` di
> `vw_stati_check_da_sanare` → il nome del file — è scritta il 21-09 sera.
>
> **Due cose che la scrittura ha smentito del brief** (§3-ter): il perimetro è
> **32 colonne / 114 valori**, non 18 / 65 (la regex del §3 vedeva una sola
> delle due forme di cast del `CHECK`); e la decisione 4 — stringere il `CHECK`
> del log dei lotti — è **ritirata**: `APERTO` è scritto 1193 volte per **copia**
> dal padre, un quarto canale che il criterio testuale non vede.
>
> **Origine:** Tid, 2026-09-19 — *«fai sia C1 che C2, così chiudiamo l'analisi e
> abbiamo i brief su cui lavorare»*; sei decisioni prese il 21-09 («ok procedi»).

---

## 1. Il difetto, sul modello

Una colonna di stato con un `CHECK` di appartenenza (`stato = ANY(ARRAY[...])`)
è una **promessa del modello**: ogni valore ammesso è uno stato che il sistema
sa raggiungere. Se un valore è ammesso e **nessuno lo scrive mai**, la promessa
è vuota, e il sistema è **muto** proprio sul caso che quel valore doveva
raccontare — che di regola è il fallimento.

**Il caso che ha fatto nascere il candidato** (analisi §3 C1): `ERRORE` stava
nel `CHECK` di `stato_esecuzione` dal primo giorno, con un contatore dedicato
nella summary; nessuno l'ha scritto fino al 2026-08-21, e le corse chiudevano in
`COMPLETATO` anche con un documento rifiutato. Il modello aveva il posto giusto
per la verità e nessuno lo riempiva. ⚠️ **E la summary lo nominava**: un
presidio che cercasse il letterale nei corpi delle funzioni sarebbe stato verde
— è la prima delle tre trappole del §2.

⛔ **Non è una misura sui dati.** «Zero righe in stato `ERRORE`» non dice niente
(Regola zero): il presidio guarda **chi può scrivere** quel valore — funzioni,
default di colonna, repository — cioè la struttura, non la popolazione.

---

## 2. La forma — un registro, una vista, un pgTAP, una riga di catalogo

È la forma di `dbops.vw_rls_perimetro_scoperto` + `dbops.rls_perimetro_debito`
(`20260909-75/76/77`, pgTAP `rls/test-rls-perimetro-scoperto.sql`), che è il
precedente più vicino: una vista che **classifica** ogni caso invece di
filtrarlo, un registro delle esenzioni con la **ragione obbligatoria**, un test
che pretende «nessun `NON_DICHIARATO`» **e** «nessun `DEBITO_ESTINTO`».

### 2.1 Il perimetro: che cos'è una «colonna di stato»

Il vincolo `CHECK (col = ANY (ARRAY['A','B',...]))` su **una** colonna, letto
da `pg_constraint` — non da un elenco di tabelle. Sono **18** oggi (§3), e la
vista li trova da sola: una tabella nuova con un vocabolario chiuso entra nel
perimetro senza che nessuno la iscriva.

Fuori dal perimetro, **dichiarato**:

* gli stati **a catalogo** (`config.stati_doc_*`, `vendite.stati_commessa`,
  FK verso una tabella di stati): lì il vocabolario non è nel DDL e la
  raggiungibilità la governa la matrice delle transizioni, che ha già i suoi
  presidi (brief «vie d'uscita per l'operatore», R3);
* i vocabolari che **non sono stati** ma classificazioni (`tipo_lotto`,
  `key_selector`, `run_as`, `canale`, `natura`): un valore mai usato lì è una
  *scelta di configurazione* non ancora esercitata, non un fallimento muto.
  ⚠️ Il confine si dichiara con un filtro sul **nome della colonna**
  (`stato*`, `status`, `esito*`, `severity`), e il filtro è un fatto della
  vista scritto nel suo commento: chi vuole allargarlo tocca una riga.

### 2.2 Che cosa conta come «scrittore»

Tre canali, e vanno guardati **tutti e tre** o il presidio è cieco:

| Canale | Dove si legge | Come |
| --- | --- | --- |
| **default di colonna** | `pg_attrdef` | il valore del `DEFAULT` è scritto **da ogni INSERT** che non lo nomina: `DRAFT`, `IN_VALIDAZIONE`, `OK`, `INFO` sono così |
| **funzione PL/pgSQL viva** | `pg_proc.prosrc` | il letterale compare in un corpo che fa `UPDATE <tabella>` o `INSERT INTO <tabella>` — **non** un corpo che lo nomina soltanto (trappola 1) |
| **repository Python** | `backend/apps/*/db/*.py`, `services/*.py` | idem, sulle stringhe SQL — **ed è la metà che il DB non vede** (§6) |

⭐ **Un valore passato come parametro** (`fn_segna_esito_gruppo_lotto(p_stato)`)
è scritto dalla funzione e nominato dal chiamante Python: la funzione da sola
non basta e il Python da solo non basta. Il verso giusto è: la funzione scrive
la **colonna** (`SET stato_esecuzione = p_stato`), il chiamante nomina il
**valore**. Il presidio SQL classifica questi casi come `SCRITTO_DA_PARAMETRO`
e li passa al lato Python (§6), che verifica che il letterale esista in un
chiamante. ⛔ Non si dichiarano esenti «perché lo scrive Python»: è la classe
in cui il caso originale è vissuto per mesi.

### 2.3 Le tre trappole, dichiarate prima di scrivere

1. **Nominare non è scrivere.** La summary che conta `FILTER (WHERE stato =
   'ERRORE')` nomina il valore in un corpo che non scrive quella tabella. La
   vista deve chiedere il letterale **e** un `UPDATE`/`INSERT` sulla tabella nello
   stesso corpo — e resta un'approssimazione: un `UPDATE t SET x = 1 WHERE stato
   = 'ERRORE'` passa. Si dichiara come limite nel commento della vista, e si
   chiude per caso quando un pgTAP costruisce il caso (§4, test 5).
2. **Il default nasconde uno scrittore assente.** `magazzino.trasferimenti`
   ha `DRAFT` per default e nessuno scrive `CONFIRM`/`POSTED`/`CANCEL`: il
   default rende `DRAFT` raggiungibile e gli altri tre no. Un presidio che
   guardasse solo «almeno un valore scritto» sarebbe verde su una tabella che
   non sa uscire dalla bozza.
3. **L'esenzione per categoria.** «È un cantiere aperto» (magazzino Lotto 2)
   vale oggi ed è falso il giorno del rilascio: la riga di registro porta la
   **ragione tecnica e la data**, e il verso di ritiro (test 2) la fa uscire
   quando lo scrittore compare. Una riga senza data è la riga che nessuno
   rilegge.

### 2.4 I pezzi

| Pezzo | Nome | Fase |
| --- | --- | --- |
| il registro | `dbops.stati_non_scritti_esenzioni` (`tabella`, `colonna`, `valore`, `ragione NOT NULL`, `data_registrazione`, `obsoleto_dal`) — `UNIQUE (tabella, colonna, valore)` | `00_schema` |
| la misura | `dbops.vw_stati_check_scrittori` — **una riga per (tabella, colonna, valore)** con `scrittori_fn int`, `ha_default bool`, `parametrico bool`, e la classificazione `esito ∈ {SCRITTO, SCRITTO_DA_DEFAULT, SCRITTO_DA_PARAMETRO, ESENTE, DEBITO_ESTINTO, NON_DICHIARATO}` | `20_code` |
| la lista di lavoro | `dbops.vw_stati_non_scritti_da_sanare` = la vista sopra `WHERE esito IN ('NON_DICHIARATO','DEBITO_ESTINTO')` | `20_code` |
| il pgTAP | `db/pgtap/dbops/test-stati-check-scrittori-v1.sql` (§4) | — |
| la riga di catalogo | `dbops.presidi`: `vw_stati_non_scritti_da_sanare`, natura **`CANCELLO`**, `presidiato_da` = il pgTAP, cadenza `MAI` — un cancello non va nel digest (guida presidi §2-bis) | `80_data` (CSV) |
| il seed del registro | le righe che la prima misura (§3) e Tid decidono **esenti**, con la ragione | `80_data` (CSV, `loadUpdateData`) |

⚠️ **Il registro nasce piccolo** (guida presidi §6.4): non si registra tutto ciò
che la misura sputa. I casi del §3 si dividono fra *da sanare* (scrittore da
scrivere), *esenti con ragione* e *da spegnere* (una tabella senza scrittori è
un'altra domanda, §5).

---

## 3. La prima misura — 2026-09-19, DB di sviluppo, criterio testuale

*Fatto datato. Il criterio è quello del §2.2 (letterale + `UPDATE`/`INSERT`
sulla tabella nello stesso corpo, default di colonna, stessa ricerca sui `.py`
non di test). Serve a dimensionare, non a decidere.*

**18** colonne di stato con vocabolario nel `CHECK`, **65** valori. Con i tre
canali del §2.2:

| Esito (grezzo) | Valori | Che cosa c'è dentro |
| --- | --- | --- |
| scritto da una funzione | 30 | `fatturazione_lotti.*`, `fatture_fondi_fattura_source.*`, `commesse_push_log.*`, `fatture_log.*`… |
| scritto **solo** da Python | 10 | `coda_lavori` `FATTO/ERRORE/ANNULLATO`, `idempotency_keys` (tutti e tre), `fatture_stampa_coda` `FATTO/ERRORE`, `fatturazione_lotti_log` `CHIUSO/ERRORE` |
| scritto dal **default** | 6 | `DRAFT` (rettifiche, trasferimenti), `IN_VALIDAZIONE` (sepa), `OK` (consumi), `W` (lotti_log), `INFO` (event_log) |
| **nessuno scrittore trovato** | **19** | sotto |

I 19 senza scrittore, già divisi per che cosa sono — e **nessuna** delle righe
sotto è una decisione, sono le domande per Tid:

| Tabella · colonna | Valori | Che cosa sembra | Da fare |
| --- | --- | --- | --- |
| `vendite.fatturazione_lotti_esiti.stato_esecuzione` | `COMPLETED`, `RUNNING` | **parametrici**: `fn_segna_esito_gruppo_lotto(p_stato)` scrive la colonna, i letterali vivono in Python (`COMPLETED` in 11 file) | il caso `SCRITTO_DA_PARAMETRO` del §2.2 — verifica al lato BE (§6). ⚠️ È la **stessa tabella** del caso originale |
| `vendite.attivita_consumi.stato_calcolo` | `ERRORE`, `WARNING` | **un C1 vero**: il calcolo dei consumi ha due stati di fallimento nel `CHECK` e **nessuno** li scrive, né SQL né Python; `OK` è il default. La decomposizione tariffaria è *rimandata* (2026-06-16) | decidere: esente con ragione e data (**«rimandata, il vocabolario è del cantiere consumi»**), o si sana quando il cantiere apre |
| `vendite.event_log.severity` | `ERROR`, `WARN` | i due repository Python che scrivono `event_log` passano la severity come **parametro**; il criterio testuale non li vede perché il letterale sta in un altro file | `SCRITTO_DA_PARAMETRO` → lato BE |
| `vendite.fatturazione_lotti_log.stato_operativo` | `APERTO` | il log riceve `CHIUSO`/`ERRORE` da `pipeline_repository`; nessuno logga l'apertura | probabile C1 piccolo: o si logga l'`APERTO`, o il `CHECK` del log non deve copiare quello del padre |
| `dbops.audit_log.status` | `OK`, `ERROR`, `WARN`, `DRYRUN` | `fn_audit_begin` scrive `START`; la chiusura sta in `fn_audit_log_once` con il valore **per parametro** | `SCRITTO_DA_PARAMETRO` — i chiamanti sono changeSet e job, non Python: qui il lato che verifica è **SQL**, cercando il letterale nei chiamanti della funzione |
| `magazzino.rettifiche`, `magazzino.trasferimenti` | `CONFIRM`, `POSTED`, `CANCEL` (+`DRAFT` per default) | **Lotto 2 in corso** (`brief-db-magazzino-lotto-2-motore.md`): il motore che li scrive è il cantiere aperto | esenti **con data**; il verso di ritiro li toglie quando il Lotto 2 li scrive |
| `pagamenti.sepa_mandati.stato` | `ATTIVO`, `SOSPESO`, `REVOCATO`, `SCADUTO` | **zero** funzioni la scrivono, **zero** file Python la nominano, una sola funzione la legge: è una tabella senza scrittori | non è un C1: è un candidato per `analisi-software-per-dati-morti` — decisione a parte (§5) |
| `dbops.automazione_chiusura_scadenze.tipo_stato` | `VARCHAR`, `FK` | non è uno stato: è il **tipo** della colonna di stato che l'automazione governa — falso positivo del filtro sul nome (`tipo_stato`) | il filtro del §2.1 esclude `tipo_*`; caso da scrivere nel test 3 come «fuori perimetro per costruzione» |

⭐ **La lezione della misura**, prima ancora del presidio: dei 19, **tre** sono
C1 veri o probabili (`attivita_consumi`, `fatturazione_lotti_log.APERTO`, e la
domanda su `sepa_mandati`), **dieci** sono parametrici e li vede solo il lato
Python, sei sono un cantiere aperto. Un presidio SQL da solo avrebbe detto
«19 rossi», di cui la maggioranza falsi: è la ragione per cui la vista
**classifica** e non filtra, e per cui la metà Python non è un'opzione.

---

## 3-bis. Rilettura del 2026-09-21 — verifiche sul DB vivo e tre correzioni di forma

*Fatti datati (dev, 2026-09-21, prima di qualunque changeSet). Le correzioni di
forma sono argomentate sul modello; le misure servono solo a dire dove il
disegno del §2 mentiva.*

### 3-bis.1 Il §3 regge, con una riga già cambiata

* Il perimetro del §2.1 scritto in forma **positiva** — `^stato`, `^status$`,
  `^esito`, `^severity$` — trova **17** colonne: le 18 del §3 meno
  `automazione_chiusura_scadenze.tipo_stato`, che esce **per costruzione**
  dall'ancora `^stato`, senza nessun ramo «escludi `tipo_*`» (un ramo di
  esclusione è il nascondiglio classico; qui non serve). I valori sono 63 + 2.
* ⭐ `magazzino.rettifiche`: `CONFIRM` e `POSTED` hanno oggi **una funzione
  scrittrice ciascuno** (il Lotto 2 li ha scritti fra il 19 e il 21). Resta
  `CANCEL`, e restano i tre di `trasferimenti`. Non è un dato che decide
  niente: è la prova che il **verso di ritiro** (test 3, `DEBITO_ESTINTO`) non
  è teorico — se il registro fosse nato il 19 con sei righe «Lotto 2», il 21
  ne avrebbe già due da togliere.
* I dieci valori «solo Python» del §3 sono confermati: per ognuno esiste
  almeno un `.py` non di test che nomina **tabella e valore** (`coda_lavori`
  3, `idempotency_keys` 3, `fatture_stampa_coda` 2, `fatturazione_lotti_log`
  2). `sepa_mandati`, `attivita_consumi.ERRORE/WARNING` e
  `trasferimenti.CONFIRM`: **zero** file, come detto.

### 3-bis.2 Correzione A — «parametrico» non si legge dal `SET col = p_x`

Il §2.2 immagina di riconoscere `SCRITTO_DA_PARAMETRO` dalla forma
`SET stato_esecuzione = p_stato`. **La forma che il linguaggio ammette è anche
posizionale**, ed è quella in uso: `fn_segna_esito_gruppo_lotto` fa
`INSERT INTO … (lotto_id, gruppo_key, stato_esecuzione, …) VALUES (…, p_stato, …)`,
`fn_audit_log_once` e `fn_audit_begin` idem su `status`, `fn_log_event` su
`severity`. Provato con `col\s*=\s*p_[a-z_]+` su tutte e 63 le coppie: **zero**
riconoscimenti, compresi i quattro casi che il §3 chiama parametrici. Legare
la posizione della colonna nell'elenco a quella del valore nel `VALUES` è un
parser, non una regex — e un presidio che «capisce un caso su cinque boccia a
caso» (AGENTS.md).

⇒ **Il parametro non si cerca: si fa il secondo salto.** Una funzione che
scrive la tabella (`UPDATE t` / `INSERT INTO t` nel corpo) è uno *scrittore
della tabella* a prescindere dal valore. Il valore si cerca **(a)** nel corpo
dello scrittore — scrittore diretto — oppure **(b)** nel corpo di chi **nomina**
lo scrittore — scrittore indiretto. Nessuna delle due chiede di sapere come il
valore viaggia dentro la funzione.

### 3-bis.3 Correzione B — il secondo salto chiude `audit_log` a DB, e il limite si dichiara

Misurato con il criterio (b) sui chiamanti di `fn_audit_log_once`/`fn_audit_end`/
`fn_audit_begin`: `OK` 10 funzioni, `WARN` 8, `DRYRUN` 13, `ERROR` 3 (tutte
`dbops.fn_run_automations_*`, `fn_storico_*`, `fn_admin_merge_*`). I quattro
valori che il §3 rimandava a «una verifica SQL a mano nei chiamanti» escono
**`SCRITTO`** dalla vista, con `scrittori_indiretti` valorizzato e
`scrittori_fn = 0`. Il limite — **due salti e non tre** — va nel commento della
vista: un valore che passa per due funzioni intermedie resterebbe invisibile,
ed è il caso costruito da aggiungere al pgTAP (§4, test 8) perché sia un
limite scritto e non un punto cieco.

### 3-bis.4 Correzione C — il §4 e il §6 si contraddicono, e il registro deve dire CHI verifica

Il test 2 del §4 pretende «nessuna riga `NON_DICHIARATO`»; il §6 dice che il
test Python «prende le righe `NON_DICHIARATO`» e cerca il letterale nei `.py`.
I dieci valori scritti solo da Python (§3-bis.1) sono `NON_DICHIARATO` per il
database — legittimamente, perché il database **non può** vederli — quindi il
pgTAP sarebbe rosso il giorno uno, o quei dieci finirebbero nel registro come
«esenti», che è la trappola 3 del §2.3 nella sua forma peggiore: un'esenzione
che nessun verso di ritiro può togliere, perché il DB non saprà mai se il
Python ha smesso di scriverli.

⇒ **Il registro porta un `canale`, e il canale dice quale lato lo verifica:**

| `canale`       | Che cosa dichiara la riga                                                            | Chi la verifica, e in quale verso                                                                                         |
| -------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| `APPLICAZIONE` | «questo valore lo scrive un repository Python» (anche via funzione con parametro)     | il test BE del §6: il letterale deve esistere in un `.py` non di test che nomina la tabella **o** uno scrittore della tabella; se sparisce → **rosso** (verso di ritiro Python) |
| `ESENTE`       | «non lo scrive nessuno, e sappiamo perché» — ragione tecnica e data                   | il pgTAP: se un scrittore compare a DB → `DEBITO_ESTINTO`, riga da togliere (verso di ritiro DB)                            |

Per **entrambi** i canali `ragione NOT NULL` e `data_registrazione`; e una
riga `APPLICAZIONE` il cui valore trova uno scrittore a DB esce anch'essa
`DEBITO_ESTINTO` — la dichiarazione era vera e non serve più. Gli esiti della
vista diventano quindi: `SCRITTO` (diretto o indiretto, con i due conteggi),
`SCRITTO_DA_DEFAULT`, `DICHIARATO_APPLICAZIONE`, `ESENTE`, `DEBITO_ESTINTO`,
`NON_DICHIARATO`. ⛔ `SCRITTO_DA_PARAMETRO` **non è più un esito**: la
colonna `scrittori_tabella` (le funzioni che scrivono la tabella) resta come
indizio per chi legge, ed è ciò che il test BE usa per cercare il letterale
accanto al nome della funzione e non solo della tabella.

⚠️ «Una sede sola per la classificazione» (§6) resta vera: il DB classifica,
il Python **legge** `DICHIARATO_APPLICAZIONE` e verifica la dichiarazione — non
rifà la misura.

### 3-bis.5 Tre note di forma sul §2.4 e sul §4

* **Nomi**: la tabella non è un registro di sole esenzioni (metà delle righe
  sono dichiarazioni vere) — proposta `dbops.stati_check_dichiarazioni`;
  viste `dbops.vw_stati_check_scrittori` (misura) e
  `dbops.vw_stati_check_da_sanare` (lavoro). La forma «`<misura>` +
  `<misura>_da_sanare`» è quella di `riferimenti_morti`.
* **`REVOKE` all'app** (§4, ultima riga): il precedente `rls_perimetro_debito`
  **non** ce l'ha — è scritto dal CSV e letto da tutti con i grant standard.
  Una postura più stretta vale **tre sedi** (AGENTS.md §11.8) e qui non compra
  niente: l'applicazione non ha nessun verbo su quel registro. Si segue il
  precedente; se un giorno la postura dei registri di debito si stringe, si
  stringe per tutti in un cantiere `dbops`.
* **`dbops.presidi`**: `CANCELLO`, `registro = dbops.stati_check_dichiarazioni`,
  `presidiato_da` = il pgTAP **e** il test BE (sono due lati dello stesso
  cancello, come `vw_codici_errore_da_dichiarare`), cadenza `MAI`.
  `colonna_stato`/`stato_atteso` NULL: la `_da_sanare` è già il filtro.

### 3-bis.6 Il pgTAP, riscritto per le correzioni (sostituisce l'indice del §4)

```text
Indice test (plan 9):
  1) ⭐ il perimetro vede le 17 colonne di oggi — o sono uscite dal CHECK davvero (elenco letto dal catalogo, non un numero)
  2) ⛔ IL PRESIDIO: nessuna riga NON_DICHIARATO in vw_stati_check_da_sanare
  3) ⛔ e nessuna DEBITO_ESTINTO: una riga di registro (qualunque canale) il cui valore ha trovato uno scrittore a DB va tolta
  4) ⛔ un valore NUOVO nel CHECK di una tabella di prova esce NON_DICHIARATO (COSTRUITO)
  5) ⛔ una funzione che NOMINA il valore in un WHERE senza scrivere la tabella NON lo rende SCRITTO (COSTRUITO — trappola 1)
  6) ⭐ un DEFAULT di colonna rende SCRITTO_DA_DEFAULT il solo valore del default, non gli altri (COSTRUITO — trappola 2)
  7) ⭐ una funzione che scrive la tabella per POSIZIONE (INSERT … VALUES (…, p_x, …)) e un chiamante che passa il letterale → SCRITTO con scrittori_indiretti = 1 e scrittori_fn = 0 (COSTRUITO — correzione A+B)
  8) ⚠️ il LIMITE: il letterale a TRE salti resta NON_DICHIARATO (COSTRUITO — dichiara il punto cieco)
  9) ⭐ una riga APPLICAZIONE il cui valore trova uno scrittore a DB esce DEBITO_ESTINTO (COSTRUITO — la dichiarazione non è un'esenzione)
```

### 3-bis.7 Raccomandazioni sulle cinque decisioni del §5

1. `severity` **dentro**, e il filtro si scrive nella forma positiva del
   §3-bis.1 — nessun ramo di esclusione.
2. `attivita_consumi.ERRORE/WARNING`: **`ESENTE`** con ragione e data («la
   decomposizione tariffaria è rimandata dal 2026-06-16; il vocabolario è del
   cantiere consumi, che quando apre scrive i due stati e fa uscire la riga»).
   Sanare oggi vorrebbe dire scrivere un calcolo che non esiste.
3. `sepa_mandati`: quattro righe **`ESENTE`** con ragione «tabella senza
   scrittori: candidata ad analisi-software-per-dati-morti, decisione a parte»
   — così il registro resta onesto e la domanda è archiviata dove si legge.
   ⚠️ È già nel registro RLS (`rls_perimetro_debito` id 70, «cantiere
   pagamenti»): due registri che la nominano sono la fotografia giusta di una
   tabella senza modello.
4. ~~`fatturazione_lotti_log.stato_operativo`: **stringere il `CHECK`** a
   `CHIUSO`/`ERRORE`~~ — ⛔ **RITIRATA scrivendo** (§3-ter.2): `APERTO` è
   scritto 1193 volte per **copia** dal padre in `fn_log_pipeline_fase`; il
   `CHECK` stretto avrebbe rotto il log. Registrato `ESENTE` con quella ragione.
5. **`CANCELLO`**, come scritto. Il digest ripeterebbe un rosso che la CI ha
   già fermato.

⚠️ Sotto le cinque c'è una **sesta**, che il §5 non nomina: il `canale` del
§3-bis.4. Senza, il brief non è eseguibile (§4 contro §6).

---

## 3-ter. Scritto il 2026-09-21 — quello che la scrittura ha smentito del §3-bis

*Fatti datati sul DB di sviluppo, e due correzioni che nessuna rilettura da
scrivania avrebbe trovato: le ha trovate il codice.*

### 3-ter.1 Il perimetro non era 18 colonne: è 32, e la misura aveva un difetto

La regex del §3 (e della rilettura del mattino) cercava `= ANY (ARRAY[` e
vedeva la sola scrittura **text** del `CHECK`. Su una colonna **varchar**
PostgreSQL stampa `((stato)::text = ANY ((ARRAY['A'::character varying, …])::text[]))`,
e quella forma restava fuori: **14 colonne** (email_log, email_outbox,
documenti_generati, template_documenti_versioni, inventari, movimenti_attesi,
sistemazioni, workflow_definizioni, commesse_attivita ×2,
documenti_fatturazione_canali, attivita_fatturabili, fatturazione_lotti_fatture,
listini_versioni). Con `= ANY \(\(?ARRAY\[` il perimetro è **32 colonne, 114
valori**. È la trappola già pagata da `valori_check` nel backend (catalogo BB:
«i due CHECK scrivono i letterali con cast diversi, una regex per caso ne
avrebbe coperto uno solo»). ⚠️ *Anche la misura è un programma*: il pgTAP tiene
l'elenco delle 32 come prova anti-restringimento, e il test 12 costruisce la
forma varchar.

Con il criterio definitivo (default, scrittore diretto, secondo salto):
**64 SCRITTO, 10 SCRITTO_DA_DEFAULT, 40 NON_DICHIARATO** → 40 righe di
registro, **26 `APPLICAZIONE`** (tutte verificate: per ognuna un `.py` non di
test che nomina tabella o scrittore *e* il letterale) e **14 `ESENTE`**.

### 3-ter.2 ⛔ La decisione 4 è ritirata: `APERTO` nel log È scritto, per copia

`fn_log_pipeline_fase` fa `SELECT l.stato_operativo INTO v_stato_operativo FROM
vendite.fatturazione_lotti … ; INSERT INTO fatturazione_lotti_log (…,
stato_operativo, …) VALUES (…, v_stato_operativo, …)`: il log riceve lo stato
**copiandolo dal padre**, e su dev ci sono 1193 righe `APERTO`. Il §3 diceva
«nessuno logga l'apertura» ed era falso; stringere il `CHECK` avrebbe rotto il
log a ogni fase di un lotto aperto. ⇒ È un **quarto canale** che il criterio
testuale non può vedere — la **copia colonna→colonna** — dichiarato come limite
c) nel commento della vista, e `APERTO` entra nel registro come `ESENTE` con
quella ragione. ⚠️ Corollario: `ESENTE` significa «esente dal criterio», non
«non scritto»; il `COMMENT` della colonna `canale` lo dice.

### 3-ter.3 Tre cose emerse scrivendo

* **Costo**: la prima stesura della vista impiegava **26 s** (2240 funzioni,
  3,5 MB di sorgente, regex per ogni coppia). Con `funzioni` e `scrittori`
  `MATERIALIZED` e un `strpos` prima di ogni regex: **0,6 s**, stesso
  risultato. Il pgTAP la interroga 14 volte: ~8 s in tutto, sotto il tetto
  dei 90 s della baseline.
* **Il registro è a 40 righe, non «piccolo»** (guida presidi §6.4) — ma 26 sono
  dichiarazioni vere, non debito, e le 14 di debito sono quattro famiglie
  nominate (documenti ×3, magazzino Lotto 2 ×4, `sepa_mandati` ×4,
  `attivita_consumi` ×2, la copia ×1). Il verso di ritiro ha già lavorato prima
  di nascere: fra il 19 e il 21 il Lotto 2 ha scritto `CONFIRM`/`POSTED` su
  rettifiche e inventari, e le sei righe magazzino del §3 sono quattro.
* **Il presidio è stato fatto fallire** prima di dichiararlo finito: tolta la
  forma varchar dalla regex → rossi 1, 3, 12, 14; tolto il secondo salto →
  rossi 2, 8, 14. Il conto atteso era scritto prima di eseguire.

### 3-ter.4 I file

| Pezzo | File |
| --- | --- |
| registro | `00_schema/dbops/20260921-15-create-stati-check-dichiarazioni` (`canale` CHECK `APPLICAZIONE`/`ESENTE`, chiave naturale a quattro, `ragione` ≥ 40, audit + tx_id espliciti come il precedente) |
| misura | `20_code/dbops/20260921-16-create-vw-stati-check-scrittori` |
| lista di lavoro | `20_code/dbops/20260921-17-create-vw-stati-check-da-sanare` |
| seed | `80_data/changelog/20260921-19-upsert-dbops-stati-check-dichiarazioni` + `80_data/sql/dbops/stati_check_dichiarazioni.csv` (40 righe, upsert sulla chiave naturale). ⚠️ `-18` era occupato da un changeSet nato in parallelo lo stesso pomeriggio |
| catalogo | due righe in `presidi.csv`: `vw_stati_check_scrittori` = `INVENTARIO`, `vw_stati_check_da_sanare` = `CANCELLO` (il mirror `20260910-35` è `runOnChange`) |
| pgTAP | `db/pgtap/dbops/test-stati-check-scrittori-v1.sql`, plan 14, `runner: owner` |
| doc | `dbops/manual/` ×3, guida presidi §3.6 |

⚠️ In CI il test 2 legge `pg_proc` del DB da zero: una funzione che esiste
solo su dev (dbdev non nasce da zero) può rendere un valore `SCRITTO` qui e
`NON_DICHIARATO` là. Nessun rosso atteso, ma è il primo posto dove guardare
se la CI dissente.

---

## 4. Il pgTAP — `db/pgtap/dbops/test-stati-check-scrittori-v1.sql`

`pgtap-contesto: escluso` (legge solo il catalogo e il registro),
`pgtap-runner: owner` (i test costruiti creano tabella e funzione di prova).

⚠️ Indice della prima stesura (19-09); quello scritto è a **14 test** e sta nel
file (§3-ter.4), con l'indice a plan 9 del §3-bis.6 come passaggio intermedio.

```text
Indice test (plan 7):
  1) ⭐ il perimetro vede le 18 colonne della prima misura — o sono uscite dal CHECK davvero
  2) ⛔ IL PRESIDIO: nessuna riga NON_DICHIARATO in vw_stati_non_scritti_da_sanare
  3) ⛔ e nessuna DEBITO_ESTINTO: una riga di registro il cui valore ha trovato uno scrittore va tolta
  4) ⛔ un valore NUOVO nel CHECK di una tabella di prova esce NON_DICHIARATO (COSTRUITO)
  5) ⛔ una funzione che NOMINA il valore in un WHERE senza scriverlo NON lo rende SCRITTO (COSTRUITO — la trappola 1)
  6) ⭐ un DEFAULT di colonna rende SCRITTO_DA_DEFAULT il solo valore del default, non gli altri (COSTRUITO — la trappola 2)
  7) ⭐ una funzione che scrive la colonna da un parametro esce SCRITTO_DA_PARAMETRO, non SCRITTO (COSTRUITO)
```

⚠️ Il test 2 è a **conteggio esatto zero**, non a soglia: il debito sta nel
registro con la ragione, non in un numero (guida presidi §2-bis, «il debito si
tiene con un registro, non con un numero»). ⚠️ E il file entra nei due presidi
trasversali che ogni funzione nuova attraversa (riferimenti morti, rubinetto del
primo motivo): qui non ci sono funzioni nuove, solo viste — ma il registro nuovo
in `dbops` entra nel perimetro della postura (`REVOKE` app: è un registro di
debito, si scrive dal CSV e dal migratore, non dall'applicazione).

---

## 5. Decisioni per Tid

1. **Il perimetro del nome** (§2.1): `stato*`, `status`, `esito*`, `severity`.
   `severity` è uno stato? Ho detto sì perché `ERROR`/`WARN` mai scritti sono
   esattamente «muto sul fallimento». Si può togliere con una riga.
2. **`vendite.attivita_consumi.stato_calcolo`**: esente con data, o si apre il
   cantiere? È l'unico C1 vero **fuori** da un cantiere già aperto.
3. **`pagamenti.sepa_mandati`**: tabella senza scrittori. Non la sana questo
   brief; va in `analisi-software-per-dati-morti` o si decide qui che è il
   primo pezzo di un dominio futuro (e allora è esente con quella frase).
4. **`fatturazione_lotti_log.stato_operativo = APERTO`**: si logga l'apertura o
   si stringe il `CHECK` del log? Un `CHECK` copiato dal padre promette una
   simmetria che il log non ha.
5. **La riga di catalogo è `CANCELLO` e non `REGISTRO`**: gira in CI e blocca.
   Se Tid preferisce vederla anche nel digest (come `vw_riferimenti_morti`),
   diventa `REGISTRO` con cadenza settimanale — ma allora presidia due volte la
   stessa cosa, e la guida lo chiama rumore.

---

## 6. Richiesta al backend — la metà Python del presidio

Il DB classifica; **26 valori su 114** oggi li scrive un repository Python
(direttamente, o passandoli a una funzione come `fn_segna_esito_gruppo_lotto`
o `fn_log_event`), e il DB non li può vedere: stanno nel registro con
`canale = APPLICAZIONE`. Serve il gemello in `apps/core/tests/`, sulla forma di
`test_naming_codice_interno_python` (ricerca testuale sui `.py` non di test):

* legge `dbops.vw_stati_check_scrittori` sul DB provvisto
  (`richiedi_db_provvisto`) e prende le righe con esito
  **`DICHIARATO_APPLICAZIONE`**;
* per ciascuna pretende **almeno un `.py` non di test** che contenga il
  letterale (`'FATTO'` o `"FATTO"`) **e** nomini la tabella
  (`nome_tabella`) **oppure** una delle funzioni in `scrittori_tabella` (il
  nome senza schema). È il criterio con cui le 26 righe sono state verificate
  il 21-09 (§3-ter.1), e i file trovati sono scritti nella `ragione`;
* **rosso** su una riga `APPLICAZIONE` che nessun file soddisfa più: è il
  verso di ritiro che il DB non può fare, e senza questo test la
  dichiarazione sarebbe un'esenzione permanente;
* ⭐ **e il verso opposto**: una riga `NON_DICHIARATO` che un `.py` soddisfa
  è una dichiarazione mancante — rosso con il messaggio «dichiarala
  `APPLICAZIONE` in `stati_check_dichiarazioni.csv`», così il registro non
  può calare di nascosto nel verso permissivo.

⛔ **Una sede sola per la classificazione**: il test Python non rifà la misura
del DB, la **legge** (guida presidi §6.3). Se rifacesse il giro su `pg_proc` a
modo suo, i due lati risponderebbero cose diverse sullo stesso valore.

⚠️ Il presidio `presidi.csv` dichiara già questo test in `presidiato_da`
accanto al pgTAP: finché non esiste, il lato Python del cancello è una
promessa scritta, e lo si dice qui.

---

## 7. Cosa resta

* ✅ changeSet `00_schema` (registro), `20_code` (due viste), `80_data` (seed
  + due righe di `presidi.csv`) — scritti e **applicati** il 21-09 (11:37);
* ✅ pgTAP a 14 test, nove casi costruiti — **verde in baseline** (Tid, 21-09:
  nessuna regressione);
* ✅ `dbops/manual/` per registro e viste; guida presidi §3.6; doc auto-gen
  rigenerata con l'apply;
* ✅ **richiesta BE §6** — chiusa il 21-09:
  `apps/core/tests/test_stati_check_scrittori_python.py` (3 test, opt-in
  `ZEROERP_TEST_DB_E2E=1`), verde 26/26 e fatto fallire prima di dichiararlo
  finito. ⚠️ Con una correzione al criterio del §6: **due salti**, non «lo
  stesso file» — il letterale sta nel service e la tabella nel repository per
  regola di `api.md`, e un criterio a un file bocciava la forma corretta. Il
  legame è un simbolo definito **solo** in file scrittori, commenti e docstring
  esclusi; i limiti stanno in testa al file. 🔵 `presidi.csv`, `presidiato_da`
  di `vw_stati_check_da_sanare`: al posto di «richiesta §6 del brief» va il nome
  del file — una riga del team DB;
* 🔵 i tre C1 veri del cantiere **documenti** (`documenti_generati.ANNULLATO/
  ARCHIVIATO`, `documenti_generati_eventi.KO`) e la domanda su `sepa_mandati`
  (dati morti) restano dichiarati nel registro con la data: sono lavori con un
  nome, non di questo brief, e il verso `DEBITO_ESTINTO` li farà uscire da soli.
