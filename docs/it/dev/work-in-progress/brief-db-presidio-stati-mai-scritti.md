# Brief DB — Presidio C1: uno stato previsto dal modello e mai scritto

> **Destinatari:** team DB (`dev/db-tid`); una richiesta al backend in **§6**.
>
> **Tipo:** brief di cantiere. Nasce dal candidato **C1** di
> [analisi-presidi-percorso-storto.md](../work-done/analisi-presidi-percorso-storto.md)
> (chiusa il 2026-09-19), che per quattro settimane l'ha misurato senza che
> nessuno lo scrivesse. Qui si scrive.
>
> **Da leggere per primo: §2 — la forma, e i tre modi in cui una misura di
> questo tipo mente.**
>
> **Stato:** 🔵 aperto, nessun changeSet. Prima misura in **§3** (datata
> 2026-09-19, sul DB di sviluppo), che serve a dimensionare il registro — non a
> decidere la forma.
>
> **Origine:** Tid, 2026-09-19 — *«fai sia C1 che C2, così chiudiamo l'analisi e
> abbiamo i brief su cui lavorare»*.

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

## 4. Il pgTAP — `db/pgtap/dbops/test-stati-check-scrittori-v1.sql`

`pgtap-contesto: escluso` (legge solo il catalogo e il registro),
`pgtap-runner: owner` (i test costruiti creano tabella e funzione di prova).

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

Il DB classifica; **dieci valori su 65** oggi si scrivono da Python o passano da
un parametro che Python valorizza, e il DB non li può vedere. Serve il gemello
in `apps/core/tests/`, sulla forma di `test_naming_codice_interno_python`
(ricerca testuale sulle stringhe SQL dei repository, registro chiavato su
`(tabella, colonna, valore)`):

* legge `dbops.vw_stati_check_scrittori` sul DB provvisto
  (`richiedi_db_provvisto`) e prende le righe `SCRITTO_DA_PARAMETRO` e
  `NON_DICHIARATO`;
* per ciascuna cerca il letterale nei `.py` non di test: in una stringa SQL che
  scrive la tabella, **oppure** come argomento di una chiamata alla funzione che
  la vista ha marcato parametrica;
* rosso su una riga che nessuno dei due lati scrive e che il registro non
  conosce; rosso su una riga di registro che ha trovato uno scrittore.

⛔ **Una sede sola per la classificazione**: il test Python non rifà la misura
del DB, la **legge** (guida presidi §6.3). Se rifacesse il giro su `pg_proc` a
modo suo, i due lati risponderebbero cose diverse sullo stesso valore.

---

## 7. Cosa resta

* 🔵 changeSet `00_schema` (registro), `20_code` (due viste), `80_data` (riga
  di `presidi.csv`, seed del registro con le esenzioni decise in §5);
* 🔵 pgTAP §4, con i quattro casi costruiti;
* 🔵 `dbops/manual/` per registro e viste; una riga nella guida presidi §3;
* 🔵 richiesta BE §6, in coda alla richiesta C2
  ([brief-be-presidio-ui-action-e-canale-campi.md](brief-be-presidio-ui-action-e-canale-campi.md)):
  stessa forma, stessi strumenti, un solo giro.
