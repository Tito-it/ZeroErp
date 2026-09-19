# Collaudo in-app · Osservabilità: il pallino, gli errori tecnici, il giornale eventi, il lotto fermo

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il piano — il *perché* di ogni scelta sta
> in [piano-be-fe-osservabilita-pallino-e-superfici.md](../work-done/piano-be-fe-osservabilita-pallino-e-superfici.md)
> e nell'analisi madre [analisi-osservabilita-log.md](../work-done/analisi-osservabilita-log.md);
> qui c'è solo **cosa fare, cosa deve succedere, e cosa fare se non succede**.
>
> **Perché esiste.** Il cantiere è chiuso a codice su tutti i lati: DB applicato
> (`20260919-01 → -07`), BE e FE mergiati (`9c11a485b`), presidi verdi. Ma le
> **due schermate nuove non le ha mai aperte nessuno**, e il pallino in topbar
> l'ha visto solo chi l'ha scritto. Di questo cantiere è stato provato il
> **percorso**, mai **l'esito** — ed è stata proprio la prova di CI di stasera,
> non un test, a trovare due cose che nessuno vedeva (le due liste globali nel
> pgTAP, il `SELECT` su `job_run_log` che esisteva solo su dev).
>
> **Stato**: ✏️ scritto il 2026-09-19, da eseguire.
> **Ambiente**: sviluppo (`dbdev`). Le due liste a catalogo (`dbops.error_log`,
> `vendite.giornale`) **ci sono già** (seed applicato: il pgTAP del perimetro le
> vede).
> **Utente**: due vesti, e servono entrambe — un **super admin** (Errori
> tecnici e pallino stanno dietro `AdminAPIView`) e un **operatore** di un
> emittente (il Giornale eventi è sotto RLS: la sua metà del collaudo è il
> perimetro).

---

## ⛔ Prima di cominciare

| | Cosa | Perché conta |
| --- | --- | --- |
| **Dato** | Serve **almeno un errore tecnico** in `dbops.error_log` e **almeno un lotto con un errore** nel giornale. Se dev è troppo pulito: un lotto giornaliero lanciato su una commessa incompleta li produce entrambi | Una lista vuota prova solo che il vuoto ha una frase |
| **Contesto** | Sapere quale emittente ha l'operatore con cui entri | Metà delle prove del §3 chiede «e l'altro emittente cosa vede?» |
| **CI** | I due fix DB del 19-09 sera (`20260919-08` e il provisioning di `maintenance`) sono da committare: **non toccano il collaudo** su dev, dove il grant c'era a mano | Se in CI «Processi automatici» è rosso, è quello |

---

## 1. Il pallino dei presidi (topbar)

Entra come **super admin**.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **1.1** | Guarda la topbar, **subito dopo** il pulsante delle code | Un pulsante con l'ingranaggio e un badge. A presidi tutti a posto: **un badge verde con `0`** — «visto e vuoto», non «niente da dire» | Se non c'è niente, il silenzio è di nuovo ambiguo: era il problema della #8 |
| **1.2** | Passa col mouse | Tooltip «Presidi di sistema: tutto a posto — letti alle HH:MM», oppure «N da guardare, M non letti — letti alle …» | Senza l'ora non sai se è di adesso o di stamattina |
| **1.3** | Click | Vai a **Amministrazione → Processi automatici**, senza schermate nuove | — |
| **1.4** | Nel pannello, premi **Ricarica** | Il pallino si aggiorna **subito** (non aspetta i 5 minuti): chi ha appena letto il dato vero non lascia il pallino indietro | Se resta vecchio, il patto col pannello non c'è |
| **1.5** | Confronta i colori: testata del pannello e pallino | ⭐ **Lo stesso vocabolario**: allarmi (con righe) in **rosso**, non letti in **giallo**, in entrambi i posti. Il 19-09 dicevano il contrario l'uno dell'altro, corretto | Due sedi per un colore divergono |
| **1.6** | Se hai un presidio con righe (o ne provochi uno): guarda il pallino | Badge **rosso col numero**; se c'è anche un non-letto, **due badge**, prima gli allarmi | — |
| **1.7** | Ramo mobile (stringi la finestra): apri il kebab utente | La voce **«Presidi di sistema»** c'è, con lo stesso numero | — |
| **1.8** | 🔴 Esci, entra come **operatore** | ⛔ **Il pallino non compare** (403 → spento per sempre, non «riprova»); nemmeno nel kebab mobile | Se compare, il permesso dei presidi è saltato: sono viste che nominano tutte le aziende |

---

## 2. Errori tecnici (`dbops.error_log`)

Super admin. È la lista **per chi ripara**, non per l'operatore.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **2.1** | **Amministrazione → Errori tecnici** (accanto ad Audit Log e Log Email) | Titolo «Registro degli errori tecnici», lista con **Quando, Area, Funzione, Codice, Classe, Messaggio, Transazione** | Se risponde «lista non trovata», il seed non è applicato: `make db-migrate` |
| **2.2** | Leggi una riga | ⭐ **Messaggio, causa e soluzione sono quelli del catalogo** (`config.messaggi_errore`), non ricostruiti; **Classe** dice se è un guasto (`TECNICO`) o un rifiuto legittimo | Un messaggio con `%s` grezzi è un segnaposto non riempito: difetto di chi solleva, non della lista |
| **2.3** | Filtro **Area**: scrivi `script`, poi `backend` | È un **testo libero**, non una tendina: `database`, `script`, `dbops`, `backend` non stanno in nessun catalogo, e una tendina li avrebbe nascosti | Se è una tendina, metà del registro non si vede |
| **2.4** | Filtro **Funzione (prefisso)**: `fn_` | Solo le righe che **cominciano** così; con `_` dentro il nome (es. `fn_guard_`) non prende tutto: l'underscore è escapato | Se `fn_` porta anche `fnx…`, il jolly non è escapato |
| **2.5** | Filtro **Codice** esatto, poi **Transazione** (incolla un `tx_id`) | Righe di quel solo codice; di quella sola transazione | — |
| **2.6** | Filtro data | Il floor standard: senza date, **gli ultimi due mesi al 1° del mese** — è consultazione, non coda di lavoro | — |
| **2.7** | Ordina per una colonna, poi per **Messaggio** | Quando/Area/Funzione/Codice/Classe ordinano; **Messaggio non è ordinabile** (è una frase) | Un `order_by` fuori lista deve dare **400**, non ordinare a caso in silenzio (rilievo 4 del 19-09) |
| **2.8** | Kebab riga → **Dettaglio** | Drawer «Errore E_…» con il **Contesto (appunti tecnici)** come JSON **com'è** — a monospazio, non riscritto; se manca: «Nessun contesto registrato» | ⛔ Un contesto «ripulito» è la cosa che il vincolo del Passo A vieta |
| **2.9** | Kebab riga → **Copia tx_id** | Toast «tx_id copiato negli appunti» | — |
| **2.10** | Kebab riga → **Giornale di questa transazione** | ⭐ Il ponte: si apre **Vendite → Giornale eventi** già filtrato sul **Filo** di quel `tx_id`. È il percorso «dal guasto tecnico alla storia di dominio» | Se la voce non c'è: sei senza l'area vendite — è un'offerta, non una promessa |
| **2.11** | Dal giornale, torna su Errori tecnici e riapri il giornale dal menu | ⭐ Il filo **non è più forzato**: l'URL si è pulito dopo l'uso | Se il `tx_id` rimane appeso a ogni ritorno, è il difetto corretto il 19-09 |
| **2.12** | **Esporta** | Il file rispetta le colonne che hai scelto; **Causa** e **Soluzione** ci sono anche se a video no (esportabili, non visibili) | — |
| **2.13** | 🔴 Come **operatore**, prova l'URL `/amm-software/error-log` | Rifiutato: è dietro il permesso dell'amministratore, come Audit Log | — |

---

## 3. Giornale eventi (`vendite.giornale`)

Entra come **operatore** di un emittente. È la Storia di **tutte** le entità
insieme, filtrata per gravità.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **3.1** | **Vendite → Fatturazione → Giornale eventi** (accanto a Lotti) | Lista con **Quando, Gravità, Registro, Entità, Riferimento, Cosa, Chi, Transazione, Correlazione**. Il toggle **«Solo errori» è acceso** di default | Se risponde «lista non trovata»: seed |
| **3.2** | Leggi la colonna **Gravità** | Tag colorato; con «Solo errori» acceso vedi le `ERROR` **e** le righe **senza gravità** (quelle che dichiarano un difetto) — la frase sotto il toggle lo dice | — |
| **3.3** | Spegni «Solo errori» | Compaiono anche gli **avvisi** (`WARN`). Le `INFO` non arrivano da qui: sono nella Storia dell'entità | — |
| **3.4** | Leggi **Riferimento** | Il **codice del lotto** o il **numero della fattura** (con la natura); una bozza senza numero mostra il ripiego, non `/` vuoto | Il rilievo 3 del 19-09: `serie/numero` a mano dava `''` e il ripiego non scattava mai |
| **3.5** | Leggi **Cosa** | L'etichetta dell'evento (dal catalogo `config.eventi_dominio`), non il codice grezzo; se manca la chiave, il codice | — |
| **3.6** | Tendina **Registro** → `TASK_RUN` | Solo le corse di task. ⚠️ **Quando** è l'**inizio** della corsa (R-6, chiuso a DB il 19-09): non un orario del giorno dopo | Se vedi orari «del futuro», la vista è tornata a `COALESCE(ended_at, …)` |
| **3.7** | Tendina **Entità** | Le voci vengono dal **catalogo** (`config.tipi_entita`, lookup dedicato), non da una lista scritta nel FE | — |
| **3.8** | Kebab riga su un **LOTTO** → «Apri …» | Si apre il lotto (per rotta, `?open=`); la scheda **Storia** è lì dentro — nessun secondo pulsante «Storia» in lista, per scelta | — |
| **3.9** | Kebab riga su una **FATTURA** → «Apri …» | Si apre la fattura | — |
| **3.10** | Kebab riga su un **TASK_RUN** | ⛔ **Nessun pulsante «Apri»**: non è un bersaglio raggiungibile, e un pulsante che non porta da nessuna parte è una promessa vuota | — |
| **3.11** | Campo **Filo**: incolla un `tx_id` | Solo le righe di quella transazione. ⚠️ R-2: `LOTTO_LOG` e `FATTURA_LOG` hanno correlazione **vuota per costruzione** — filtrare per filo le **perde**, ed è per questo che il default non filtra | — |
| **3.12** | Guarda la nota sotto la lista | «N segnalazioni ritirate nascoste» quando ce ne sono: le disabilitate non spariscono in silenzio, si contano | — |
| **3.13** | **Esporta** | Stesso BB delle altre liste; le date nel formato di locale | — |
| **3.14** | 🔴 **La prova del perimetro.** Esci, entra come operatore dell'**altro** emittente | ⛔ **Le righe del primo non ci sono**, e il **conteggio** in fondo dice il numero **visto**, non il totale | Se le vedi, la RLS della vista non morde: fermati e segnala |
| **3.15** | 🔴 Come **super admin in «Tutti gli emittenti»** | La schermata **chiede di scegliere un emittente** in alto (422), come `Fatture`: questa lista **non** è certificata multi-emittente — la vista non proietta l'emittente della riga | È voluto (registro del piano, 19-09); la strada per «Tutti» è una colonna in più nella vista: richiesta DB, non urgente |

---

## 4. Il lotto fermo — il verdetto ha una sede sola

Operatore, su un **lotto giornaliero con un errore** (una commessa che non
si può emettere basta).

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **4.1** | Apri il lotto → il **banner** | Dice «fermo» con il motivo, e il pulsante del passo successivo è **spento** | — |
| **4.2** | **Amministrazione → Processi automatici** (super admin) | Fra i presidi c'è **«lotti fermi»** (`dbops.vw_lotti_fermi_da_guardare`) e conta **lo stesso lotto** — dopo un'ora dal fermo, per costruzione | ⭐ È la prova che il verdetto è **uno**: banner, presidio, digest e pallino leggono la stessa colonna `fermo` a DB. Se il banner dice fermo e il presidio no (o viceversa), ci sono due sedi |
| **4.3** | Risolvi il lotto (o annullalo) e ricarica | Banner e presidio **cambiano insieme** | — |
| **4.4** | Scheda **Storia** del lotto e della fattura (ripasso del Passo A) | Le righe dei tre registri in ordine di tempo; sul `TASK_RUN` l'orario è l'inizio; il `context` **c'è** qui (è forense), mentre nel Giornale eventi **no** | — |

---

## 5. 🔴 I punti già noti, da confermare a video

Non sono domande: sono cose decise o dichiarate, che il collaudo deve **vedere**.

| | Cosa | Dove sta scritto |
| --- | --- | --- |
| **§3.15** | Il Giornale eventi su «Tutti gli emittenti» chiede un emittente. Per farlo multi serve `emittente_soggetto_ruolo_id` nei quattro rami della vista: **richiesta DB non urgente** | piano §10, registro 19-09 (pezzo G, nota ⚠️) |
| **§3.6-3.7** | La tendina **Registro** è ancora una **seconda sede** nel FE (quattro letterali) finché non esiste `config.registri_giornale`: brief DB [brief-db-registri-giornale-catalogo.md](brief-db-registri-giornale-catalogo.md). Quando arriva, la tendina porta le **etichette** invece di `EVENT_LOG` grezzo | PROJECT_CONTEXT «Aperto» |
| **R-5** | Sul giornale convivono **due generazioni** di righe: le vecchie con transazione vuota, le nuove col giro. A video sono indistinguibili, e resta così | analisi §3-quater |
| **R-7** | Il **rumore**: un lotto sporco ripete la stessa storia N volte. Il toggle «Solo errori» ne toglie una parte; la de-duplicazione **non è stata fatta**, per scelta: si guarda col pannello davanti | analisi §3-quater |

---

## 5-bis. 🟠 Trovato a video — il presidio parla a chi lo mantiene, non a chi deve agire

**Il fatto (Tid, 2026-09-19, sul pannello Processi automatici).** Con due
presidi accesi — `dbops.vw_articoli_a_magazzino_prontezza` (`NESSUNO_MARCATO`)
e `dbops.vw_lotti_fermi_da_guardare` (16 righe) — il testo mostrato sotto ogni
riga era *«complicato da capire»*. La stessa cosa detta in chat in due righe
(«nessun articolo è marcato gestito a magazzino: marcane uno dal drawer
articolo» · «sono 16 lotti di prova con critiche vive da giugno: rilanciali o
annullali») ha reso l'azione ovvia, e i due presidi si sono spenti in pochi
minuti.

**Perché succede, sul modello.** Il testo che il pannello mostra è il
`COMMENT` della vista (`presidi_repository.py`, `obj_description`): un testo
scritto **per chi mantiene il presidio** — spiega perché esiste, cita i brief,
dichiara il perimetro e la cadenza. Chi lo legge in-app è **l'operatore**, che
ha una domanda sola: *cosa vuol dire, e cosa devo fare*. Il pannello risponde
alla domanda sbagliata perché l'unico dato che ha in mano è stato scritto per
un altro lettore. La `nota` di `presidi.csv` va nella stessa direzione ma resta
prosa da sviluppatore, e il commento della vista **deve** restare tecnico: non è
lui da riscrivere.

**Cosa manca.** Una seconda voce per presidio, **l'azione**: una frase
imperativa, scritta per l'operatore, che dice cosa fare per spegnere il
presidio (o, per i presidi che una persona non può spegnere, chi avvisare).
Forma proposta: colonna `azione_operatore` in `dbops.presidi`, alimentata dal
CSV come tutto il resto del catalogo; il pannello la mostra **per prima**, con
la descrizione tecnica sotto, ripiegabile. Lato BE/FE è una colonna in più
nella proiezione del pannello e nel digest.

⚠️ È una richiesta **DB** (colonna + una riga di CSV per ognuno dei presidi a
catalogo) più BE/FE a valle: **non c'è ancora un brief**, sta qui come nota
del collaudo finché Tid non decide di aprirlo.

---

## 6. Registro

| Data | Cosa |
| --- | --- |
| **2026-09-19** | ✏️ Stesura, alla chiusura dell'analisi e del piano (archiviati in `work-done/` lo stesso giorno). Tutto a codice, **niente visto a video**. Prima della stesura: i due rossi CI del commit `9c11a485b` — l'elenco delle liste globali nel pgTAP e il `SELECT` di `zeroerp_app` su `maintenance.job_run_log` che esisteva solo su dev — chiusi lato DB, da committare |
| **2026-09-19** | Primo giro a video sul pannello Processi automatici (Tid): due presidi accesi erano entrambi **stati del dato** di dev, non difetti — spenti marcando un articolo a magazzino e chiudendo i 16 lotti di prova. Trovato che la descrizione mostrata è scritta per chi mantiene il presidio, non per chi deve agire → **§5-bis**, senza brief per ora |
