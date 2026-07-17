# Brief Design — Cruscotti fatturazione a due lenti (Competenza a valle + Backlog a monte)

> **Tipo**: brief di design autorevole (modello + piano di ridisegno) · **Data**: 2026-07-04
> · **Ultimo aggiornamento**: 2026-07-17 (motore rifondato a **contatore**, DL-27 +
> emendamenti 23/24/26 — vedi nota di rev in §6-quater)
> **Owner**: Tid · **Stato**: 🟢 **Le tre viste sono in piedi e committate** (Lente 1
> Competenza, Lente 2 Backlog, Situazione aperta v2). **Prossimo**: §6-quater — far entrare
> **DDT e resi** nelle due lenti a monte, insieme ai due bug di fatturazione che l'analisi
> ha fatto emergere (DL-19..28,
> [brief-db-fatturazione-ddt-resi.md](brief-db-fatturazione-ddt-resi.md)). Poi Fase 4 guida.
> Ridisegna
> la dashboard pre-fatturazione a 5 card (design-of-record
> [brief-design-dashboard-fatturazione.md](../work-done/brief-design-dashboard-fatturazione.md),
> Fasi 1-3 fatte e committate `50347da0c`, **non pushate**) sostituendola con **due
> lenti** semanticamente omogenee.
>
> **Origine**: revisione con Tid (2026-07-04) della
> [analisi-dash-pre-fatturazione.md](../work-done/analisi-dash-pre-fatturazione.md). La Domanda A
> ("l'asse mese non è uniforme: solo Commesse ha competenza vera") non è un problema di
> etichette da spiegare in guida: è il **sintomo** che la dashboard attuale risponde a
> **due domande diverse su un asse solo**. Decisione Tid: soluzione **massima** (ridisegno
> pulito), **percorso unico** con disegno unitario in testa e consegna in due fasi.
>
> **Documenti collegati**:
> [brief-design-dashboard-fatturazione.md](../work-done/brief-design-dashboard-fatturazione.md) (la
> pre-fatturazione attuale, che questo brief decompone) ·
> [analisi-dash-pre-fatturazione.md](../work-done/analisi-dash-pre-fatturazione.md) (Domande A-E) ·
> [Guida fatturazione](../../guide/fatturazione.md) ·
> [fatturazione-roadmap.md](fatturazione-roadmap.md).

---

## 1. Il problema — un asse solo per due domande

La dashboard pre-fatturazione attuale mette 5 card ("Preventivi, Ordini, Offerte,
Contratti, Commesse") su **un unico asse mensile**, chiamato "competenza". Ma la
competenza **vera** (economica, del funnel) esiste in **un solo punto**:
`vendite.commesse_attivita.competenza_mese` (NOT NULL, normalizzata al 1° dal trigger).
Tutto converge lì prima di diventare fattura.

Verifica sui campi-tempo reali delle tabelle sorgente (2026-07-04):

| Area | Campi-tempo esistenti | Qualità competenza |
|---|---|---|
| **Commesse** (attività) | `competenza_mese` NOT NULL, `competenza_dal/_al`, `data_attivita` | **Vera, a grana attività** |
| **Contratti** | `validita` daterange NOT NULL | **Vera, come periodo** (esplosione mensile corretta) |
| **Preventivi** | `competenza_mese` nullable (scritta all'accettazione), `validita_dal/_al`, `data` | Dichiarata **solo se accettato**, altrimenti proxy |
| **Ordini** | **solo `data`** (né `ordini_righe` né `ordini_righe_fulfillment` hanno una data consegna/erogazione) | **Proxy puro — vincolo duro di modello** |
| **Offerte** | `validita_dal` NOT NULL, `data_emissione/_accettazione` | **Proxy puro** |

**Conclusione di modello**: le aree a monte (Preventivi non accettati, Ordini, Offerte)
**non hanno** e non possono derivare una competenza economica finché non transitano in
commessa. Forzarle su un asse "competenza" produce un asse che significa cose diverse in
ogni colonna. Non è un difetto di UI: è il segnale che stiamo sovrapponendo due domande.

Le due domande, separate:

1. **"Il mese di competenza M è completo?"** — di tutto ciò che è *di competenza* M,
   quanto è arrivato a fattura? È una domanda **a valle** (commessa → attività fatturabili
   → lotti → fattura), su competenza **vera**. Omogenea per costruzione.
2. **"Cosa è fermo a monte e va spinto ora?"** — quali documenti non sono ancora entrati
   nel funnel di competenza, da quanto tempo, e cosa serve per sbloccarli? È una domanda
   **a monte**, il cui asse naturale **non è la competenza** (i fermi non ce l'hanno): è
   l'**anzianità** e l'**azionabilità**.

## 2. Il principio — due lenti, non una dashboard

Si sostituisce la dashboard a 5 card con **due lenti distinte**, ciascuna col suo asse:

* **Lente 1 — Competenza (a valle).** Ospita **solo ciò che ha competenza vera**:
  l'attività di commessa e la sua progressione fino alla fattura. Asse = mese di
  competenza. Coincide con la "dashboard reale di fatturazione" (commessa→fattura,
  con tutti gli step dei lotti) di cui si parla nel §12 del brief pre-fatturazione.

* **Lente 2 — Backlog / da collegare (a monte).** Ospita **i non-collegati**: preventivi
  con righe residue, ordini non pushati, offerte orfane, contratti senza canone. Asse =
  **anzianità** + **azionabilità** (`motivo_fermo` + classe). È la pagina arretrati
  (Domanda D dell'analisi).

Perché due e non una: un elemento **non ancora collegato a una commessa non ha un mese di
competenza** — per costruzione non può stare sull'asse della Lente 1. Non lo perdiamo: è
**esattamente** la popolazione che i resolver attuali già marcano `is_fermo`. Cambia solo
*dove* lo mostriamo (Lente 2), non *come* lo individuiamo.

> **Domanda A → risolta dal disegno.** La Lente 1 ha un asse competenza uniforme (una sola
> semantica: la competenza commessa). La Lente 2 non usa affatto l'asse competenza. Sparisce
> l'ambiguità del "Maggio significa 5 cose diverse".

## 3. Come si individuano i "non-collegati" (non si perde nulla)

I resolver attuali già calcolano, per area, chi è fermo — è la Lente 2 pronta come
popolazione:

| Area | "Non ancora collegato" = | Predicato (già in vista oggi) |
|---|---|---|
| Preventivi | righe `stato_smistamento = RESIDUA` | NOT EXISTS attività EMESSA per `PREV:<uid>:R:<riga>` |
| Ordini | righe senza commessa | NOT EXISTS attività EMESSA per `ORD:<uid>:R:<riga>` |
| Offerte | senza contratto/ordine vivo | LEFT JOIN figli nullo (o figlio abortito) |
| Contratti | mese senza canone | NOT EXISTS attività EMESSA su `sorgente_uid + competenza_mese` |

`motivo_fermo` (10 codici già definiti: `RIGA_RESIDUA`, `PUSH_NON_ESEGUITO`,
`PUSH_PARZIALE`, `SENZA_FIGLIO`, `FIGLIO_ABORTITO`, `CANONE_NON_GENERATO`, `DOC_BOZZA`,
`IN_ATTESA_ACCETTAZIONE`, `ATTIVITA_NON_APPROVATA`, `ATTIVITA_NON_EMESSA`) è già il
vocabolario di segnalazione della Lente 2.

## 4. Lente 1 — Competenza (a valle)

**Domanda**: per mese di competenza M, di tutto il valore *di competenza M* quanto è
non-emesso / emesso-non-fatturato / fatturato, e in che stato è la fattura?

**Spina dati** (tutta a valle, competenza NOT NULL — nessun proxy):

```text
commesse_attivita (competenza_mese M)
   └─ stato_emissione EMESSA ─► attivita_fatturabili (competenza_mese M)
                                   └─ fattura_riga_id NOT NULL ─► riga fattura
                                                                    └─ stato doc fiscale (BOZZA/numerato/inviato…)
```

Metriche per mese M (bozza, da rifinire in Fase 1):

* **In commessa non emesso** — attività di competenza M `stato_emissione ≠ EMESSA`
  (approvate da emettere / da approvare). = il "residuo interno" del mese.
* **Emesso non ancora fatturato** — in `attivita_fatturabili` con `fattura_riga_id IS NULL`.
* **Fatturato** — `fattura_riga_id IS NOT NULL`, con **breakdown per stato documento
  fiscale** (`config.stati_doc_fiscale`: bozza/numerato/inviato SDI…) → quanto del
  fatturato di M è davvero consolidato vs ancora in pipeline lotti.
  **Misura (deciso Tid 2026-07-06, chiude DB-6 del brief DB)**: come "fatturato" si
  mostra **sempre `imponibile_riga`** (`valore_fatturato`, il valore reale della
  fattura); il teorico `prezzo_snapshot × quantita` resta la misura degli stadi
  non ancora fatturati del funnel.
* **Log/errori** — fatture ferme in errore (`vendite.fatture_log.critical`,
  `fatturazione_lotti_task_runs`) che toccano competenza M.

**Scope v1 (deciso, 2026-07-04)**: **tutti e 4 i blocchi** (funnel 1→2→3 + breakdown
per stato fattura 3a + pannello errori 4) sono in v1. Sviluppo **a step**, ma **predisposto
fin da subito** — sviluppo **concentrico** (memoria `feedback_concentrico_no_yagni`): il
contratto delle viste, dell'API e del FE va dimensionato per accogliere tutti i blocchi
dall'inizio, anche se popolati/rifiniti in tempi successivi. Nessun taglio "v1.1" da
ricucire dopo.

Riusa il **resolver Commesse** attuale (già su competenza vera) come primo anello, e assorbe
le idee v2 del §12 pre-fatturazione (riconciliazione commesse↔fatturato, breakdown per stato
fattura, log fatturazione). Escluse le attività **void** (`20260703-61`: ANNULLATA /
RIFIUTATA salvo EMESSA+RIFIUTATA).

**Dimensione temporale (recuperi tardivi)** — vedi §7: per distinguere "di competenza M
**ed emesso a M**" da "di competenza M **ma emesso in ritardo**" serve un **timestamp di
transito/emissione** (Domanda C). È un raffinamento della Lente 1, non un cancello: la
prima versione può ignorarlo.

## 5. Lente 2 — Backlog / da collegare (a monte)

**Domanda**: cosa è fermo prima della commessa, da quanto, e cosa devo fare per sbloccarlo?

**Popolazione**: i non-collegati del §3, uniti in una lista per **anzianità** (non per
competenza), con `motivo_fermo` e **classe di azionabilità**.

**Meccanismo della classe (deciso B, 2026-07-04)** — la gravità **non** si deriva dallo
stato grezzo (ambiguo: lo stesso `ACCETTATO` può essere a posto o recuperabile). Si deriva
dal `motivo_fermo`, che i resolver **già** producono combinando *stato* + *"è transitato?"*
(il `NOT EXISTS` sulla commessa). La classe è quindi una **mappatura statica
`motivo_fermo → classe`**, decisa dal dominio una volta e collocata in una **lookup
centralizzata** (config table `motivo_fermo` con colonna `classe`, o costante centralizzata
lato app — collocazione da fissare in Fase 2, DB-first preferito). Il FE già decodifica
`motivo_fermo` in etichetta i18n: aggiunge solo colore/classe letti dalla lookup.

| `motivo_fermo` | Classe | Azione |
|---|---|---|
| `DOC_BOZZA` | 🟢 3.a fisiologico | — (in lavorazione interna) |
| `CANONE_NON_GENERATO` | 🟢 3.a fisiologico | — (manca il push ricorrente, limite strutturale) |
| `SENZA_FIGLIO` | 🟢 3.a fisiologico | — (offerta accettata da convertire; scelta, non ritardo) |
| `IN_ATTESA_ACCETTAZIONE` | 🔵 3.d sollecito cliente | sollecita il **cliente** (non lavoro interno; filtro dedicato) |
| `RIGA_RESIDUA` | 🟠 3.b recuperabile | smista le righe |
| `PUSH_NON_ESEGUITO` / `PUSH_PARZIALE` | 🟠 3.b recuperabile | pusha in commessa |
| `ATTIVITA_NON_APPROVATA` | 🟠 3.b recuperabile | approva l'attività |
| `ATTIVITA_NON_EMESSA` | 🟠 3.b recuperabile | emetti l'attività |
| `FIGLIO_ABORTITO` | 🔴 3.c anomalia | rivedi l'offerta |

Il numero che conta per il lavoro quotidiano è il **🟠 3.b**. Esposizione in UI: contatori
di riepilogo in cima (`🟠 n · 🔵 n · 🔴 n`, il 🟢 fisiologico resta fuori) + colonna colore
per riga + **filtro per classe** (incluso il filtro "sollecito cliente" 🔵).

**Perimetro aree (deciso D, 2026-07-04)** — non è una scelta a mano per area: **discende
dalla regola di classe**. Il backlog mostra **tutto il non-verde** (🟠 + 🔴) di ogni area,
**più** il 🔵 sollecito cliente in filtro dedicato. Conseguenze automatiche:

* **Preventivi / Ordini / Commesse** → contribuiscono col loro 🟠 (`RIGA_RESIDUA`,
  `PUSH_NON_ESEGUITO/PARZIALE`, `ATTIVITA_NON_APPROVATA/NON_EMESSA`).
* **Offerte** → **solo** `FIGLIO_ABORTITO` (🔴); `SENZA_FIGLIO`/`DOC_BOZZA` sono 🟢, fuori.
* **Contratti** → **niente** finché manca il push ricorrente (`CANONE_NON_GENERATO`/
  `DOC_BOZZA` = 🟢). Rientreranno quando il push ricorrente esisterà e un canone mancante
  diventerà un ritardo reale.
* **🔵 sollecito cliente** (`IN_ATTESA_ACCETTAZIONE` di Preventivi/Offerte) → nel backlog
  ma in **sezione/filtro a parte**, separato dal lavoro interno.

Il backlog è quindi *"la lista 🟠 + 🔴 + 🔵 ordinata per anzianità"*, con una regola sola e
uniforme — nessun caso speciale codificato a mano.

**Anzianità**: v1 può usare la **data documento** come proxy ("fermo da…"); il timestamp di
transito (§7) la rende precisa e abilita il concetto "recuperato in ritardo".

## 6. Decomposizione della dashboard pre-fatturazione attuale

Non si "refactora in place": si **ripartisce**. Cosa migra e cosa si dismette:

| Elemento attuale (`50347da0c`) | Destino |
|---|---|
| Resolver **Commesse** (competenza vera) | **Sopravvive** → primo anello Lente 1 |
| Popolazione **fermo** + `motivo_fermo` (5 resolver) | **Sopravvive** → contenuto Lente 2 |
| `core/components/charts/DonutTransito.vue` | **Riusabile** in entrambe le lenti |
| Store/API/BB FE, i18n `motivo_fermo` | **Riusabili** (ricomposti) |
| Aggregata **mensile per proxy** (`vw_dash_fatturazione_mensile`) | **Dismessa** (asse proxy non ha più senso) |
| **Layout 5 card su asse proxy-mese** + view/route pre-fatturazione | ~~Dismesso a copertura completata~~ → **Trasformato** (deciso 2026-07-07): stessa rotta, diventa la vista **Situazione aperta** (§6-bis); si dismette solo l'impianto mensile |

**Congelamento**: la dashboard pre-fatturazione attuale resta viva **com'è** (vista
provvisoria) e **non riceve altri investimenti**, finché le due lenti non ne coprono il
perimetro. Non si butta oggi, non si rifinisce: si sostituisce.

## 6-bis. Fase 3 ridefinita — trasformazione in "Situazione aperta" (2026-07-07, Tid)

> ⚠️ **Superato in parte dalla revisione v2 (§6-ter, 2026-07-08).** L'impianto DB/BE/FE
> descritto qui (stock per fase con misura transitato, tutte le fasi incluso CHIUSO,
> toggle `solo_aperti`) è stato **consegnato e mergiato (PR #938)** ma, alla validazione
> in-app, Tid ha ridefinito la semantica: la Situazione aperta diventa il **serbatoio
> pre-commessa** (documenti aperti che, se conclusi, andrebbero in commessa ma non ci sono
> ancora arrivati), **elimina il concetto "transitato"** e mostra la composizione **per
> fase dei soli aperti-non-chiusi**. Le parti ancora valide di questa sezione (perimetro
> 4 aree, riuso BB, misura mista, esclusione abortiti/COMMESSE) restano; le parti superate
> (transitato, fase CHIUSO, `solo_aperti`) sono rimpiazzate dal §6-ter. Vedi DL-14..18.

Con le Lenti 1-2 mergiate (PR #932), la Fase 3 non butta la 5-card: la **trasforma**
nella vista **"Situazione aperta"** — lo **stock dei documenti aperti** (Preventivi,
Ordini, Offerte, Contratti; **no Commesse**, coperte dalla Lente 1) raggruppato per
**`fase` normalizzata**, **senza asse temporale**. È una **terza domanda**, diversa da
entrambe le lenti: la Lente 1 guarda il mese di competenza, la Lente 2 il lavoro da
sbloccare ora (solo non-verde 🟠🔴🔵, filtro `classe <> FISIOLOGICO` dentro
`vw_dash_backlog_documenti`). Qui si fotografa **tutto** l'aperto, inclusi i fisiologici
🟢 (bozze, offerte da convertire, contratti in essere) che la dismissione secca avrebbe
reso invisibili — revisione della "perdita voluta" registrata a valle della Fase 2.
Radici mai collegate prima: la proiezione stato dominio (`script.vw_stato_sorgente`,
`fase` uniforme per le 4 aree documento) e il recap §2
dell'[analisi-dash-pre-fatturazione](../work-done/analisi-dash-pre-fatturazione.md)
(valido nel contenuto, invalido solo nell'asse mensile).

**Decisioni DL-9..13**: registro in §10. Punti di design chiave:

* **Perimetro unico** — vista dettaglio `vw_dash_aperto_documenti` (union 4 aree,
  `NOT is_abortito`, **tutte le fasi** — DL-13: vista DB neutra, il FE decide quali
  card mostrare) + aggregata gemella `vw_dash_aperto_riepilogo` (`area × fase`) per le
  card; il BE non replica filtri. ⚠️ Correzione al claim D-6 del primo brief BE: i
  resolver non-contratti **marcano** gli abortiti (`is_abortito`), non li escludono —
  l'esclusione vive nella vista stock.
* **Contratti de-esplosi (DL-12)** — 1 riga per contratto vivo (sparisce il rumore che
  li aveva esclusi dal backlog), giudizio di transito **sospeso**
  (`is_transitato`/`motivo_fermo` NULL) finché non esiste il push ricorrente;
  predisposto ad accendersi dopo — e a quel punto i contratti entrano anche in Lente 2.
* **Misura (DL-11)** — € imponibile Preventivi/Ordini, conteggi (`NULL`, mai 0) per
  Offerte/Contratti; il contratto dati prevede entrambe le colonne (accensione futura
  senza ristrutturare).
* **Riuso** — `DonutTransito`, `dashboardAree.js`, store/BB FE, vocabolario i18n
  `motivo_fermo` (da ricollocare in gruppo condiviso, caveat noto). **Dismessa
  davvero**: solo `vw_dash_fatturazione_mensile` + pannello 12 mesi/semaforo/stepper.

Brief operativo DB: [brief-db-situazione-aperta.md](../work-done/brief-db-situazione-aperta.md) —
atterrato con `20260707-03..06` (resolver de-esploso, `vw_dash_aperto_{documenti,riepilogo}`,
drop mensile), pgTAP verdi. ✅ Rework `security_invoker` sul resolver contratti (perso dal
`CREATE OR REPLACE` del `-03`) **eseguito dal team DB e verificato** (2026-07-07, brief DB §5).

## 6-ter. Revisione v2 — "Situazione aperta" come serbatoio pre-commessa (2026-07-08, Tid)

**Origine**: validazione in-app della v1. Emerso che il concetto **"transitato"** (ereditato
dal DNA della 5-card: "transitato vs fermo") **non ha più senso** in una vista senza asse
temporale — totalizza *dalla notte dei tempi* documenti già passati avanti o conclusi, che
non sono azionabili. La domanda vera è più stretta: **"quali documenti aperti, se conclusi,
andrebbero in commessa/fatturazione ma non ci sono ancora arrivati, e in che fase sono?"**

**Collocazione nella pipeline** (allineamento con Tid): la Situazione aperta v2 è il
**serbatoio a monte della commessa** — il pezzo mancante *prima* della Lente 1 (che parte
dalla commessa, dove nasce la competenza vera). Non condivide l'asse con la Lente 1: i
documenti aperti **non hanno competenza** (è il DNA §1), la acquisiscono solo transitando
in commessa. Legame **sequenziale** (cosa sta per entrare → cosa è entrato ed è di
competenza M), non un dato unificabile.

**Distinzione dal Backlog confermata** (Tid): restano due viste. Entrambe filtrano gli
aperti, ma con **tagli diversi** — Backlog = *cosa sbloccare ora* (`classe <> FISIOLOGICO`,
per anzianità/azionabilità); Situazione aperta = *dove sono tutti gli aperti* (`fase <>
CHIUSO`, tutte le classi, per fase/maturità). Una bozza sta solo nella Situazione aperta;
una riga-residua sta in entrambe con due letture diverse. Nessuna collisione.

**Decisioni v2 (DL-14..18, registrate in §10)**:

* **DL-14 — Semantica**: serbatoio pre-commessa. **Eliminato il concetto "transitato"**:
  nel nuovo perimetro è ~0 per costruzione (mostriamo solo i non-transitati). Spariscono
  dalle viste/BE/FE `is_transitato` / `valore_transitato` / `unita_transitate` / `is_aperto`
  (colonna) / `n_aperti`.
* **DL-15 — Perimetro**: `is_aperto = true AND fase <> 'CHIUSO'` — **entrambi** i filtri
  (l'`is_aperto` toglie i transitati-non-chiusi tipo *accettato già smistato*; il
  `fase<>CHIUSO` toglie i chiusi-non-transitati tipo *offerta superata*). **4 aree**
  (Preventivi/Ordini/Offerte/Contratti — serbatoio completo, a diverse distanze dalla
  commessa: P/O a 1 salto, Offerte a 2, Contratti con relazione sospesa dal push ricorrente
  ma tenuti come "in essere"). No COMMESSE, no abortiti (invariato). **Rimosso il toggle
  `solo_aperti`** (il perimetro è ora fisso solo-aperti).
* **DL-16 — Grafico card**: **donut a spicchi per fase** (composizione degli aperti
  dell'area fra le 3 fasi vive: ⚪ APERTO bozza → 🔵 IN_ATTESA cliente → 🟠 IN_CORSO da
  lavorare), palette `faseDocumentoSeverity`. Legge la *maturità verso la commessa*.
  CHIUSO esce dalle fasi (da 4 a 3). Misura mista invariata (DL-11): valore per P/O,
  conteggio per Offerte/Contratti.
* **DL-17 — Filtro ritardo**: soglia **"aperti da oltre N giorni"** (preset), anzianità =
  **data documento** (`data_riferimento`, già esistente — costo DB zero; NON serve il
  timestamp "in fase da", rinviato a un'eventuale v3). Applicato **solo alla lista**
  drill-down: le **card restano la fotografia completa** dello stock (scelta Tid — la card
  è lo stato, il filtro affina la sola esplorazione).
* **DL-18 — Contratti**: restano (giudizio sospeso `is_transitato NULL` → sempre "aperti"):
  nel perimetro compaiono DRAFT + ATTIVO (i CESSATO escono con `fase<>CHIUSO`, gli ANNULLATO
  sono abortiti). Un contratto ATTIVO figura come IN_CORSO — la fase normalizzata astrae
  "attivo/in essere", limite noto della normalizzazione, accettato.

**Brief operativi v2** — ✅ **ESEGUITI E COMMITTATI** (verificato nel codice 2026-07-16):
[brief-db-situazione-aperta-v2.md](../work-done/brief-db-situazione-aperta-v2.md) (viste, PR #944) →
[brief-be-fe-situazione-aperta-v2.md](../work-done/brief-be-fe-situazione-aperta-v2.md)
(endpoint + FE, commit `6daf0a65d`; poi `8887f4113` ha aggiunto l'ordinamento alle liste delle
tre dashboard). Riscontri: `solo_aperti` non esiste più in nessun file, `ritardo_giorni` è in
BE/FE/store/test, `DonutBase.vue` + `DonutFasi.vue` sono in `core/components/charts/`.

## 6-quater. DDT e resi nelle lenti (2026-07-16, Tid) — DL-19..28

> ⚠️ **Rev 2026-07-17 — il motore è stato rifondato.** La verifica sul DB vivo ha dimostrato
> che la forma descritta più sotto e in DL-26 (*«prima della fattura si sottrae, dopo si
> accredita»* — tre predicati coordinati) **non regge**: i predicati si sommano (doppia
> correzione) e perdono la configurazione di default `trigger = CONFERMATO` (dettaglio:
> brief DB §3f). Sostituita dal **contatore** `tenuti − fatturati` — **DL-27**, con
> emendamenti a DL-23/24 e precisazione di DL-26 (il **principio** resta intatto; cambia il
> *come*). La fonte operativa autorevole del motore è ora il
> [brief DB](brief-db-fatturazione-ddt-resi.md) **§3 riscritto**; i punti di design qui sotto
> restano validi come storia e contesto, salvo dove il registro §10 li emenda.

**Origine**: Tid ha interrotto questo brief accorgendosi che **mancava un'area intera — il
DDT** — e che nel frattempo era arrivata anche la slice **resi**. Le due lenti a monte sono
state disegnate quando quelle aree non esistevano, e non le conoscono. La Lente 1
(Competenza) **non si tocca**: parte dalla commessa ed è sorgente-agnostica, il DDT che pusha
ci entra da solo (decisione Tid, confermata dall'analisi).

**Il punto di innesto era già pronto**: entrambe le lenti pescano dalla union
`vw_dash_fatturazione_documenti`, quindi **un solo resolver DDT** aggiunto lì le alimenta
entrambe, e `fase`/`motivo_fermo` fanno da soli la ripartizione fra serbatoio e backlog. Il
costo è quasi tutto DB.

**L'analisi ha però fatto emergere quattro rilievi, due dei quali sono bug di fatturazione**
che le lenti non possono vedere (mostrerebbero la doppia fatturazione come transito
legittimo). Sintesi — dettaglio e numeri in
[brief-db-fatturazione-ddt-resi.md](brief-db-fatturazione-ddt-resi.md) §1:

* **Buco cieco** — con `trigger = CONSEGNATO`, l'ordine evaso va a `fase = CHIUSO` ed esce dal
  serbatoio mentre il DDT non ha ancora pushato: quel valore **non è in nessuna delle tre
  viste**.
* **Falso positivo già vivo** — il resolver ordini non conosce `fatturazione_trigger` e marca
  `PUSH_NON_ESEGUITO` 🟠 su ordini che non pusheranno mai (XOR ordine/DDT): azione impossibile
  suggerita all'utente.
* **La ri-consegna fattura due volte** — il DDT generato da `fn_genera_ddt_riconsegna` è
  pushabile: 13 pz fatturati su un ordine da 10. La reso-awareness del 13/07 è stata applicata
  ai consumatori *logistici* e non a `fn_list_ddt_da_pushare`, il consumatore *di billing*.
* **NC su merce mai fatturata** — `vw_resi_da_accreditare` filtra sul **tipo** di reso e non
  verifica se la merce sia stata fatturata.

**Il rilievo di radice**, da cui discendono gli ultimi due: `tipi_reso.riapre_residuo` è un
flag **logistico** che oggi decide anche cosa succede ai **soldi**. La domanda che governa i
soldi è un'altra — *«quella merce l'avevamo già fatturata?»* — ed è un **fatto** nel DB, non
una scelta. Nessuno lo guarda.

**Decisioni DL-19..28**: registro in §10 (DL-23/24/26 emendati, DL-27 = il contatore, DL-28 = solo trasporto via causale). Punti di
design chiave (come formulati il 2026-07-16 — per il motore vale la rev in testa alla sezione):

* **Resi = REVERSE_FLOW, non serbatoio (DL-24)** — lo dice il DB stesso:
  `config.sorgenti.RESO_VENDITA` ha `scope = REVERSE_FLOW`, mentre tutto il serbatoio è
  `PUSH_COMMESSA`/`PUSH_CONTRATTO`. In più sarebbe **doppio conteggio**: `fn_conferma_reso`
  riapre il residuo e riproietta l'ordine a PARZIALMENTE_EVASO, quindi **l'ordine rientra da
  solo** nel serbatoio. I resi vanno **solo nel Backlog**, spaccati in due dal flag che già
  c'è: `RICONSEGNA_NON_ESEGUITA` 🟠 (l'azione esiste e la sua mancata esecuzione blocca la
  fatturazione) e `NC_DOVUTA` 🟢 (stessa forma di `CANONE_NON_GENERATO`: si accende 🟠 con la
  slice NC cambiando una riga di seed).
* **Ordine al residuo (DL-23)** — nel serbatoio l'ordine porta il valore **ancora da spedire**,
  non quello pieno: altrimenti la merce già in viaggio è contata due volte (ordine 1.000 +
  DDT 500 = 1.500 per un valore che farà fattura di 1.000). Chiude anche il buco cieco: la
  staffetta ordine→DDT tiene la somma a 1.000 in ogni istante. Costo accettato: Ordini diventa
  l'unica area con misura **netta**.
* **Il principio (DL-26)** — *si fattura la merce che il cliente tiene in mano alla fine*.
  Invariante per riga: `fatturato − accreditato = merce tenuta`. Il fatto "già fatturata?" non
  decide **se** correggere (sempre) ma **come**: prima della fattura si sottrae, dopo si
  accredita.
* **La scelta umana è una sola e vive sulla coda (DL-26)** — esiste in **una** delle quattro
  combinazioni (merce già fatturata + reso per ri-consegna): *«emetto la nota di credito?»*.
  Accreditare e rifatturare sono la stessa decisione vista dai due lati → all'utente si chiede
  una cosa sola, il resto si deriva. Non è un campo da congelare alla creazione del reso (la
  decisione può arrivare dopo, se il cliente la chiede): è un'azione sulla coda accrediti,
  esercitabile **fino alla ri-spedizione**.
* **Un brief solo, non due (2026-07-16)** — motore e read-side erano stati separati per
  sequenza ("prima i fix, sennò il backlog mostra numeri sbagliati"); Tid ha rimosso quel
  criterio (**non siamo in produzione**: i numeri temporaneamente sbagliati non sono un costo
  di progetto). Senza quel motivo il taglio non regge: i due pezzi **riscrivono la stessa
  funzione** (`fn_list_ddt_da_pushare`) e condividono la regola di eleggibilità, che deve
  avere **una fonte sola** e un proprietario chiaro.

## 7. Prerequisito DB — timestamp di transito (Domanda C) ✅ deciso

Oggi le viste **non espongono** *quando* un'attività è stata emessa: non si distingue,
dentro il transitato, **"fatto in tempo"** da **"recuperato in ritardo"** (analisi §4).

**Deciso (Tid 2026-07-04):**

* **Evento da datare** = l'**emissione dell'attività di commessa**
  (`stato_emissione → EMESSA`) — il punto comune del funnel (tutto passa da lì).
* **Fonte del timestamp = `vendite.attivita_fatturabili.data_insert`** (verificato
  2026-07-04). All'emissione, `fn_emit_attivita_fatturabili_da_commessa` **inserisce** la
  riga in `attivita_fatturabili` con `commessa_attivita_id` (link), `competenza_mese` e
  `data_insert = now()`: *quando è stata emessa* e *di che competenza è* sono **già lì,
  affiancati**. Il confronto `date_trunc('month', data_insert)` vs `competenza_mese` dà
  direttamente il "recuperato in ritardo", **senza campi nuovi**.
* ⚠️ **Correzione a una prima ipotesi errata**: l'idea iniziale "esporre dal log
  `commesse_attivita_log`" **non regge** — il manuale del log dichiara che traccia
  *push/pull e riallineamenti prezzo*, **non** l'emissione, e nessuna funzione/trigger
  risulta scrivervi l'evento di emissione. Fonte **scartata**.
* **Ambito DB minimo**: potenzialmente **nessun oggetto nuovo** — il resolver della Lente 1
  legge `attivita_fatturabili` direttamente. Un mini-brief DB serve solo a **validare** che
  `data_insert` sia una data di emissione affidabile nei **casi limite** (reset lotto /
  re-emissione: se una riga AF viene ricreata, `data_insert` si sposta) ed eventualmente
  esporre una vista di comodo. **Fallback** (solo se `data_insert` non è affidabile): colonna
  `data_emissione` dedicata su `attivita_fatturabili`/`commesse_attivita` + backfill.
* **Ambito funzionale**: raffinamento della **Lente 1** (recuperi tardivi per mese di
  competenza). **Non** serve al backlog: i suoi elementi non sono ancora transitati → la loro
  anzianità si misura sulla **data documento** ("fermo da…").
* **Non bloccante**: Lente 1 v1 (senza recuperi tardivi) e Lente 2 v1 (anzianità-proxy)
  partono senza attendere la validazione DB.
* ✅ **Validazione eseguita (2026-07-06)** — vedi
  [brief-db-fatturazione-due-lenti.md](../work-done/brief-db-fatturazione-due-lenti.md) §2:
  `data_insert` confermata affidabile (reset lotto = solo UPDATE, nessuna re-emissione
  possibile, colonna mai aggiornata); unico caveat latente C1 (collisione `segment_key`
  nel ramo UPDATE di `fn_emit`) documentato con test-sentinella. Nessun campo nuovo.

## 8. Punti aperti da chiudere con Tid

* **B — Azionabilità** — ✅ **CHIUSA** (Tid 2026-07-04): tripartizione 3.a/3.b/3.c via
  mappatura statica `motivo_fermo → classe` (§5); `SENZA_FIGLIO` = 🟢 fisiologico; UI con
  contatori + colonna colore + filtro per classe.
* **C — Timestamp di transito** — ✅ **CHIUSA** (Tid 2026-07-04): evento = emissione
  attività di commessa (`stato_emissione → EMESSA`); **fonte = `attivita_fatturabili.data_insert`**
  (già affiancato a `competenza_mese`, nessun campo nuovo — vedi verifica §7; ipotesi "log"
  scartata). Raffinamento Lente 1, non serve al backlog. → mini-brief DB solo per validare i
  casi limite (§7).
* **D — Perimetro aree del backlog** — ✅ **CHIUSA** (Tid 2026-07-04): discende dalla regola
  di classe (backlog = non-verde 🟠+🔴), niente casi speciali a mano; `IN_ATTESA_ACCETTAZIONE`
  entra come classe 🔵 **sollecito cliente** in filtro dedicato (§5).
* **Lente 1 — metriche v1** — ✅ **CHIUSA** (Tid 2026-07-04): **tutti e 4 i blocchi** in v1
  (funnel 1→2→3 + stato-fattura 3a + errori 4), sviluppo a step ma **predisposto** dall'inizio
  (concentrico, §4).

## 9. Non-obiettivi

* Non si tocca il modello dati dei documenti (proiezione read-only, come la pre-fatturazione).
  L'unico intervento DB previsto è **additivo**: esporre il timestamp di transito (§7).
* Valore € di Offerte/Contratti (resta come da D-2/D-3 del brief pre-fatturazione: v2).
* Push ricorrente dei contratti: fuori scope (ne dipende solo la lettura `CANONE_NON_GENERATO`).

## 10. Decisioni prese (Tid — DL-1..8: 2026-07-04 · DL-9..13: 2026-07-07 · DL-14..18: 2026-07-08 · DL-19..26: 2026-07-16 · DL-27/28 + emendamenti 23/24/26: 2026-07-17)

| # | Decisione | Scelta |
|---|---|---|
| DL-1 | Approccio | **Massima** (ridisegno pulito), non ponte incrementale |
| DL-2 | Struttura | **Due lenti**: Competenza (a valle) + Backlog (a monte), asse distinto |
| DL-3 | Percorso | **Unico** con disegno unitario in testa (questo brief) + 2 fasi per dipendenza |
| DL-4 | Pre-fatturazione attuale | **Congelata** e poi dismessa; sopravvivono resolver Commesse, fermo/`motivo_fermo`, BB FE |
| DL-5 | Timestamp transito (C) | Evento = emissione attività commessa (`→ EMESSA`); **fonte = `attivita_fatturabili.data_insert`** (già presente con `competenza_mese`, nessun campo nuovo; ipotesi "log" scartata). Raffina Lente 1; non bloccante; mini-brief DB solo per validare casi limite |
| DL-6 | Azionabilità backlog (B) | Classe = mappatura statica `motivo_fermo → classe` (lookup DB-first); `SENZA_FIGLIO` = 🟢 fisiologico; UI contatori + colore + filtro |
| DL-7 | Perimetro backlog (D) | Backlog = **non-verde** (🟠+🔴) da tutte le aree, regola unica senza casi speciali a mano; `IN_ATTESA_ACCETTAZIONE` = nuova classe 🔵 **sollecito cliente** in filtro dedicato |
| DL-8 | Scope Lente 1 v1 | **Tutti e 4 i blocchi** (funnel 1→2→3 + stato-fattura 3a + errori 4) in v1; sviluppo a step ma **predisposto** dall'inizio (concentrico, no tagli da ricucire) |
| DL-9 | Situazione aperta — collocazione | **Terza vista autonoma** sulla rotta della 5-card: Fase 3 = **trasformazione**, non dismissione secca (§6-bis) |
| DL-10 | Situazione aperta — raggruppamento | **`fase` normalizzata** su card/filtri (già in union, zero DB); stato nativo + `motivo_fermo` come dettaglio nel drill-down |
| DL-11 | Situazione aperta — misura | **Mista** (conferma D-2/D-3/D-4): imponibile € Preventivi/Ordini, conteggi Offerte/Contratti |
| DL-12 | Situazione aperta — contratti | **Consistenza pura**: stock per fase, giudizio transito **sospeso** fino al push ricorrente; contratto dati predisposto ad accendersi dopo; resolver **de-esploso** (1 riga per contratto vivo) |
| DL-13 | Situazione aperta — perimetro fasi | ~~Lo stock include tutte le fasi (anche CHIUSO)~~ **superato da DL-15** (v2 esclude CHIUSO). Resta valido: abortiti esclusi in vista (`NOT is_abortito`) + vista dettaglio gemella `vw_dash_aperto_documenti` come **perimetro unico** di card e drill-down |
| DL-14 | Situazione aperta **v2** — semantica | **Serbatoio pre-commessa**: documenti aperti che se conclusi vanno in commessa ma non ci sono ancora arrivati. **Eliminato il "transitato"** (~0 nel perimetro): spariscono `is_transitato`/`valore_transitato`/`unita_transitate`/`is_aperto`(col)/`n_aperti` (§6-ter) |
| DL-15 | Situazione aperta v2 — perimetro | `is_aperto = true AND fase <> 'CHIUSO'` (**entrambi**: toglie i transitati-non-chiusi e i chiusi-non-transitati); 4 aree, no COMMESSE, no abortiti; **rimosso il toggle `solo_aperti`** |
| DL-16 | Situazione aperta v2 — grafico | **Donut a spicchi per fase** (3 fasi vive APERTO/IN_ATTESA/IN_CORSO, palette `faseDocumentoSeverity`) = composizione/maturità degli aperti; misura mista invariata (DL-11) |
| DL-17 | Situazione aperta v2 — filtro ritardo | Soglia **"aperti da oltre N giorni"** su **data documento** (`data_riferimento`, costo DB zero); applicato **solo alla lista** (card = fotografia completa) |
| DL-18 | Situazione aperta v2 — contratti | Restano (giudizio sospeso → sempre aperti): compaiono DRAFT + ATTIVO; CESSATO escono con `fase<>CHIUSO`. ATTIVO figura come IN_CORSO (astrazione fase normalizzata, accettata) |
| DL-19 | **Bug orfano push DDT** (§6-quater) | `fn_list_ddt_da_pushare` order-backed usa l'**uguaglianza stretta** `stato = trigger`: un DDT che supera lo stato-trigger esce per sempre dall'eleggibilità e **non viene mai fatturato, senza segnalazione**. Stesso bug corretto sugli ordini il 2026-07-10; il ramo standalone della stessa fn ha già la logica giusta (`IN (...)`) → è un'asimmetria, non una scelta. **Si corregge**: eleggibile **dallo** stato-trigger **in poi** |
| DL-20 | **Ordini XOR nel backlog** | Il resolver ordini diventa **trigger-aware**: con `trigger ∈ {SPEDITO, CONSEGNATO}` non è l'ordine a pushare → nuovo motivo **`IN_ATTESA_DDT` = 🟢 FISIOLOGICO**. L'ordine **resta** nel serbatoio (è aperto e pre-commessa) e **sparisce** dal backlog (non c'è nulla da fare su di lui). Nessun caso speciale FE: la regola di classe DL-6/DL-7 fa tutto |
| DL-21 | **DDT nelle lenti** | **Un solo resolver** `vw_dash_fatturazione_ddt` nella union `vw_dash_fatturazione_documenti` → alimenta **entrambe** le lenti; `fase`/`motivo_fermo` ripartiscono da soli. `motivo_fermo` trigger-aware: prima del trigger = 🟢 `IN_TRANSITO` (in viaggio), dal trigger in poi e non pushato = 🟠 `PUSH_NON_ESEGUITO`/`PUSH_PARZIALE` (codici riusati). Il predicato "il push è dovuto?" ha **fonte unica** condivisa con la fn di push, mai ricopiato. **⚠️ EMENDATO 2026-07-17 (proposta Tid) — popolazione dichiarata: solo i DDT con un ruolo di fatturazione** = standalone + order-backed con trigger `SPEDITO/CONSEGNATO`; **esclusi** gli order-backed con trigger `CONFERMATO` («si segue l'ordine»: non fattureranno mai loro, e l'ordine porta già il valore pieno per DL-23 emendato). Chiude in un colpo il falso positivo (`PUSH_NON_ESEGUITO` perpetuo con azione impossibile — il §1d sul DDT) **e** il doppio conteggio speculare (ordine pieno 1.000 + DDT 500 = 1.500), senza motivi dedicati né azzeramenti. Criterio = lo stesso discriminatore XOR del lister (`!= 'CONFERMATO'`), fonte unica anche nella popolazione. Dettaglio: brief DB §4a |
| DL-22 | **Fase DDT** | **Invariata**: `CONSEGNATO`/`RESO` restano `fase = CHIUSO`. Conseguenza voluta: un DDT **dovuto e non pushato** compare nel **Backlog** e non nel serbatoio — corretto per costruzione (non sta aspettando: è in ritardo) |
| DL-23 | **Ordine al residuo nel serbatoio** | L'ordine porta il valore **ancora da spedire** (`ordinato − evaso`), non il pieno: altrimenti la merce in viaggio è contata due volte (1.000 + 500 = 1.500 per un valore da 1.000). Residuo **da spedire** (fulfillment), NON "non transitato" (per trigger CONSEGNATO il transitato è sempre 0). **Formula già esistente e reso-aware** (`fn_ordine_ha_residuo_evasione` v2 + `fn_ordine_riga_qta_riconsegna`): riusarla. Accettato: Ordini unica area con misura **netta**. **⚠️ EMENDATO 2026-07-17**: la misura netta vale **solo quando il DDT è il veicolo di billing** (`trigger ∈ {SPEDITO, CONSEGNATO}`); con `trigger = CONFERMATO` — verificato: quell'ordine **può** generare DDT, ma fattura il pieno alla conferma e il suo DDT non pusherà mai — l'ordine resta al **valore pieno**, altrimenti 1.000 € spediti-non-pushati mostrerebbero 0 € (nuovo buco cieco sul default). Stesso lavoro di DL-20, non un secondo. ~~staffetta che «chiude il buco cieco» / «in ogni istante la somma fa 1.000»~~ **falso** (a CONSEGNATO il DDT esce dal serbatoio per DL-22: il valore vive nel Backlog; la somma regge solo nella finestra EMESSO/SPEDITO) — l'argomento valido resta il **doppio conteggio** |
| DL-24 | **Resi — dove** | **NO serbatoio** (tre argomenti convergenti: `sorgenti.RESO_VENDITA` = `REVERSE_FLOW` per dichiarazione del DB; sarebbe **doppio conteggio** perché `fn_conferma_reso` riapre il residuo e **l'ordine rientra da solo**; violerebbe la semantica DL-14). **SÌ Backlog**, ramo dedicato (fuori dalla union documenti, che è il funnel pre-commessa): `RICONSEGNA_NON_ESEGUITA` 🟠 (azione esiste, la mancata esecuzione **blocca la fatturazione**). NC **facoltative** = opzione, non arretrato → fuori. Misura a **conteggi** (i resi non hanno importi), precedente DL-11. **⚠️ EMENDATO 2026-07-17**: il secondo motivo si chiama **`MERCE_RESA_GIA_FATTURATA`** (~~`NC_DOVUTA`~~ — nomina il **fatto**, non il rimedio: le NC non sono ancora definite e il motivo non deve pre-decidere la risposta) ed è 🟢 perché **nessuna azione esiste oggi** (NC assente, correzione manuale vietata dall'immutabilità); la popolazione non è più «il tipo di reso» ma la **differenza negativa del contatore** (DL-27, il tipo resta come etichetta); ~~«stessa forma di `CANONE_NON_GENERATO`»~~ **precedente falso** (verificato: seed morto, nessuna vista lo emette — la tesi regge perché questo ramo il brief DB lo costruisce davvero) |
| DL-25 | **Perimetro serbatoio** | **Nessuna azione**: `area <> 'COMMESSE'` resta. Con i resi fuori dalla union (DL-24) non è più una blacklist da manutenere ma una frase stabile — *«escludi il punto di arrivo»*: la commessa non è un'eccezione da ricordare, è il traguardo. Filtrare per `sorgenti.scope` sarebbe lavoro a comportamento invariato; il criterio resta disponibile se servisse |
| DL-26 | **Fatturazione dei resi (il principio)** | **Si fattura la merce che il cliente tiene in mano alla fine** — invariante per riga `fatturato − accreditato = merce tenuta`. Radice del guasto: `riapre_residuo` è un flag **logistico** che oggi decide anche i **soldi**; la domanda economica è *«era già fatturata?»*, un **fatto** nel DB che nessuno guarda. **La scelta umana** (*«emetto NC?»*) esiste in **una** sola combinazione (già fatturata + per ri-consegna), è **una sola** (accredito ⇔ rifatturo: il resto si deriva, il conto torna comunque) e **non si congela alla creazione del reso**: è esercitabile **fino alla ri-spedizione**. **⚠️ PRECISATO 2026-07-17 (→ DL-27)**: l'invariante è **quantitativa** e va implementata come tale — ~~«non ancora fatturata → sottrai · già fatturata → accredita»~~ non sono **due regole** da coordinare (così formulate producevano doppia correzione, brief DB §3f) ma **due letture del segno** di `tenuti − fatturati`; anche *«la ri-consegna rifattura solo se non coperta»* non è una regola: è il conto che torna da sé. **Il principio resta invariato**: cambia che ora si *calcola* invece di coordinarsi |
| DL-27 | **Il contatore — la forma del motore** (2026-07-16/17) | Fonte unica **set-based** per **partita di merce**: `tenuti − fatturati`, e **il segno decide** (positivo → fattura la differenza · negativo → accredita · zero → niente). **Tenuti** = Σ consegnati − Σ resi (CONFERMATI, attivi, tutti i tipi) + Σ ri-consegnati. **Fatturati** = Σ `attivita_fatturabili.quantita` delle righe AF della partita, via `commessa_attivita_id` — **frontiera = EMISSIONE** (*«lo stato EMESSA serve una NC»*, Tid: l'esistenza della riga AF **è** la frontiera; predicato `= 'EMESSA'` whitelist). **Chiave partita** = `ordine_riga_id` + catena DDT/ponte per lo standalone (**NO sorgente polimorfa**: servono archi pesati, non identità di nodo — guida sorgente-polimorfa §6; precedente ROW_VALIDATOR archiviato). Consumatori: fn di push, coda accrediti, resolver DDT dashboard, `available_actions`. Decisioni figlie chiuse: fix flip a RESO (`= 'CONFERMATO'`, i resi DRAFT non contano — difetto corretto in `fn_conferma_reso` + `fn_annulla_reso`) · **contratto alla slice NC** (la NC deve essere attribuibile alla merce e portare una quantità, o il contatore non la vede) · quantità immutabili + porta oneri (brief dedicato, valori negativi restano ammessi in catena per predisposizione a conguagli/storni futuri). **Capitolato di verifica**: le 10 righe della tabella §3a del [brief DB](brief-db-fatturazione-ddt-resi.md) |
| DL-28 | **DDT di solo trasporto — l'intento si dichiara con la causale** (2026-07-17) | Il DDT ammette righe senza prezzo per design («solo trasporto»), ma il lister non le esclude → standalone senza prezzi a SPEDITO = «da fatturare» con prezzo vuoto. L'intento **non si inferisce** dall'assenza di prezzo (ambiguo: dimenticanza o scelta): si dichiara col campo che l'operatore già compila. **Colonna `fatturabile` su `config.causali_trasporto`** (seed: VENDITA = sì; CONTO_VISIONE/RESO/RIPARAZIONE/CAMPIONATURA/TRASFERIMENTO/CONTO_LAVORO/OMAGGIO = no — i casi ambigui come OMAGGIO sono una cella di seed, non codice; pattern `tipi_reso.riapre_residuo`). **Gate all'emissione** (mirror gate indirizzi): causale fatturabile → ogni riga con prezzo **risolvibile** (proprio o da ordine via COALESCE), altrimenti blocco parlante — il prezzo dimenticato diventa errore, non silenzio; causale obbligatoria all'emissione. Lister e popolazione resolver (DL-21) escludono i non fatturabili: la card resta «dentro chi fattura, fuori chi no». Scartata l'alternativa flag in testata DDT (due verità da allineare con la causale). Dettaglio: brief DB §4a |

## 11. Piano di sviluppo

| Fase | Dove | Deliverable | Stato |
|---|---|---|---|
| 0 — Disegno unitario | questo brief | due lenti + decomposizione + punti aperti B/C/D | ✅ 2026-07-04 |
| 0-bis — Chiusura punti aperti | con Tid | decisioni **B, C, D, Lente 1** (DL-6/7/8 + C) | ✅ 2026-07-04 |
| DB — Timestamp transito | `dev/db-tid` (brief al team) | **validare** `attivita_fatturabili.data_insert` come data-emissione (casi reset/re-emissione); eventuale vista di comodo (§7) | 🟢 **FATTO** ([brief-db-fatturazione-due-lenti.md](../work-done/brief-db-fatturazione-due-lenti.md), 2026-07-06): validazione ✅ `data_insert` affidabile (nessun campo nuovo) e **substrato DB di ENTRAMBE le lenti applicato+testato** — migrations `20260706-01..15` EXECUTED, pgTAP competenza (15) + backlog (14) verdi; lookup classi `config.motivi_fermo` (DL-6), viste `vw_dash_competenza_*` (Lente 1, 4 blocchi), `vw_dash_backlog_*` (Lente 2) e fix `-15` security_invoker famiglia 5-card (V-1: bypassava la RLS emittente, ora chiuso). Non committato |
| 1 — Lente Competenza | `dev/backend-tid` | resolver a valle (commessa→fattura per competenza), **4 blocchi predisposti** (§4) + BE + FE; riusa resolver Commesse | 🟢 **FATTO + REVIEW** (2026-07-06, non committato): BE 3 endpoint GET `dashboard-competenza/{,attivita/,errori/}` (pivot 4 stadi + breakdown 3a + errori) + 32 test; FE `DashboardCompetenzaView` (12 mesi semaforo, card stadi, donut copertura, pannello errori, drill-down attività + filtro ritardi), rotta/nav/i18n; doc `api_dashboard_competenza.md`. **Review multi-agent (8 finder) + fix applicati**: DB-6 single-source BE-side (`valore_display` per cella + blocco `totali` per mese: il FE rende, non sceglie la misura); pannello errori pilotato da (mese, aggregata) non dal conteggio (bug: mesi consecutivi con pari n_errori → pannello vuoto); competenza drill-down derivata da (anno, mese) e non da `mesi[]` stale (bug: fetch anno sbagliato su stepper/reload a cavallo d'anno); `date_trunc` su bucket errori (lotti senza CHECK primo-del-mese); stadi fuori whitelist accodati fail-visible; clamp anno 2000-2100; fallback i18n a codice grezzo; semaforo con badge ⚠/✖ indipendenti; pivot su accumulatore Decimal tipizzato. **Estrazione BB (ok Tid 2026-07-06)**: `usePagedDashFetch` (fetch paginata cruscotti: guard versione + rientro pagina-oltre-l'ultima; adottato da fermi/attivita'/errori nei 2 store) + `useDashMesiNav` / `DashMesiSidebar` / `DashMeseStepper` (telaio anno/12-mesi/stepper condiviso, i18n `dash_mesi.*`; adottato da ENTRAMBE le view — la 5-card eredita cosi' anche i fix clamp-anno e competenza race-free su cambio anno). `COUNT(*) OVER()` sulla lista errori (una sola valutazione della union per pagina, fallback count solo su pagina-oltre-l'ultima). Rinviato con motivazione: `scrollable/scroll-height` sulle DataTable interne — 8/10 tabelle interne del repo non lo usano; applicarlo a 2 sole creerebbe una terza variante (standard: "il miglioramento si applica a tutte le schermate, mai a una sola") → eventuale allineamento globale come task dedicato. Catalogo BB FE aggiornato. 1016 test verdi + build FE ok. Da validare in-app |
| 2 — Lente Backlog | `dev/backend-tid` | lista non-collegati per anzianità + `motivo_fermo` + azionabilità; v1 anzianità-proxy | 🟢 **FATTO** (2026-07-06, non committato): BE 2 endpoint GET `dashboard-backlog/{,documenti/}` (contatori 3 classi sempre presenti in ordine UI 🟠🔵🔴, classi extra accodate fail-visible; lista ordinata BE-side per anzianità DESC, filtri classe/area whitelist, `COUNT(*) OVER()`) + 17 test; FE `DashboardBacklogView` (card classi = filtro toggle, filtro area, tabella con motivo decodificato/azione suggerita dalla lookup/fermo-da-gg/stato per area, apri documento via `?search=`), store su `usePagedDashFetch`, severity `classeBacklogSeverity`, rotta/nav/i18n it+en (vocabolario `motivo_fermo` e label aree riusati dalla 5-card); doc `api_dashboard_backlog.md` + api.md + catalogo BB. **Review multi-agent (8 finder) + fix applicati**: filtro `classe` de-whitellistato (era fail-closed mentre il riepilogo è fail-visible: una 4ª classe futura dava card non drillabile → 400; ora classe sconosciuta = lista vuota, area resta whitellistata perché strutturale); empty-state onesto (`loaded` in `usePagedDashFetch`: il verde "backlog vuoto" solo dopo fetch riuscita, mai su errore/pre-caricamento); `resetAll()` nel BB (la pageSize non sopravvive più al logout, fix su tutti e 3 gli store); clamp `GREATEST(anzianità,0)` (niente "fermo da -N gg" su date future) + `anzianita_max` null quando l'età è sconosciuta (≠ 0 gg); ORDER BY su `data_riferimento` (colonna base, ordine identico); unità ferme rese in card; stili inline morti rimossi. **Regola del 2 APPLICATA (ok Tid 2026-07-06)**: `vendite/dashboardAree.js` (config aree route+severity+kind + `buildApriDocumentoAction`, adottata da 5-card e Backlog), `applyPageEvent` in `usePagedDashFetch` (uccide le 4 copie del handler paginator), `labelOrCode` in core/utils (decodifica i18n fail-visible, adottata in 8 siti: dashboard+pratiche+catalogo), `validate_enum_param` in core list_helpers (unifica 5 blocchi whitelist nei service vendite). **"Apri documento" CORRETTO (ok Tid)**: una ricerca ESTERNA (deep-link `?search=`, ricerca universale, AI) ora azzera i default temporali `data_da`/`data_a` della lista target in `useSearchTable` — i documenti più vecchi di anno-1 (i più urgenti del backlog) sono trovabili; le ricerche digitate in pagina non toccano i filtri data; toolbar allineata via sync store→ref in `useStoreFilterBindings` (bindSelect/bindDate ora osservano lo store). Cataloghi BB BE+FE aggiornati. 1635 test verdi (vendite+core) + build FE ok |
| 3 — Trasformazione in "Situazione aperta" (§6-bis) | DB: `dev/db-tid` · BE/FE: `dev/backend-tid` | DB: resolver contratti de-esploso + `vw_dash_aperto_*` + drop mensile ([brief-db-situazione-aperta.md](../work-done/brief-db-situazione-aperta.md)) · BE/FE: ritiro endpoint 5-card + restyle pagina + ricollocare i18n in gruppo condiviso | 🟢 **DB FATTO 2026-07-07** (migrations `20260707-03..06` EXECUTED, pgTAP verdi 28+10+14+15, regressione lenti zero, PR #936; rework `security_invoker` resolver contratti ✅ eseguito e verificato, brief DB §5). 🟢 **BE+FE FATTI 2026-07-07** (non committati): BE 2 endpoint GET `dashboard-aperto/{,documenti/}` (riepilogo 4 aree × 4 fasi sempre presenti fail-visible + drill-down con filtri area whitelist/fase passthrough/`solo_aperti` default true) + 21 test, ritirati endpoint/service/repo/test/doc 5-card; FE `SituazioneApertaView` (card area con DonutTransito + chip fasi = filtro, lista per "in essere da", toggle solo-aperti), store `dashboardAperto` su `usePagedDashFetch`, severity `faseDocumentoSeverity`, **rotta rinominata `/vendite/situazione-aperta`** (menu "Situazione aperta"; deroga alla lettera di DL-9 "stessa rotta": l'URL `dashboard-fatturazione` sarebbe stato fuorviante — la dashboard di fatturazione vera ora è la Lente 1); i18n `motivo_fermo`/`area_*`/`fase_*` ricollocati nel gruppo condiviso `dash_comune` (Backlog aggiornato). Doc `api_dashboard_aperto.md` + api.md + cataloghi BB. **Review critica 2026-07-07 (8 finder, 10 fix applicati)**: filtro `area` passthrough fail-visible (card accodate drillabili, mai 400), valori € delle aree extra non più persi (decisione data-driven), donut card senza la fase CHIUSO (fotografa la pipeline viva), vocabolario `fasi` top-level nel riepilogo (alimenta il filtro FE), `solo_aperti` strict con default single-source nel service, misura euro/count letta dal payload (via la copia FE `kind`), + 5 estrazioni regola del 2 ok Tid (`qp_str_upper`, `_query_paged_view` — che risolve anche il rientro da pagina stantia in UNA valutazione della union con clamp SQL + pagina effettiva nell'envelope adottata da `usePagedDashFetch` —, `dashAreaLabel`/`dashFaseLabel`/`dashMotivoLabel`, `useDashRiepilogo`, `DashEmptyState`). 1630 test verdi vendite+core, build FE ok, mergiato **PR #938**. **Da validare in-app** |
| 3-bis — Situazione aperta **v2** (§6-ter) | DB: `dev/db-tid` → BE/FE: `dev/backend-tid` | DB: viste ridotte al serbatoio-aperti-non-chiusi + drop colonne transitato ([brief-db-situazione-aperta-v2.md](../work-done/brief-db-situazione-aperta-v2.md)) · BE/FE: donut per fase, filtro "oltre N giorni" solo-lista, via toggle solo_aperti ([brief-be-fe-situazione-aperta-v2.md](../work-done/brief-be-fe-situazione-aperta-v2.md)) | ✅ **FATTO E COMMITTATO** — DB PR #944; BE/FE `6daf0a65d`, poi `8887f4113` (ordinamento liste sulle 3 dashboard). Verificato nel codice 2026-07-16 |
| 3-ter — **DDT e resi nelle lenti** (§6-quater) | DB: `dev/db-tid` (brief) → BE/FE: `dev/backend-tid` | DB: **contatore** `tenuti − fatturati` (DL-27, fonte unica) + fix flip a RESO + coda accrediti = differenza negativa + fix orfano + resolver DDT + ordini trigger-aware + ordine al residuo (DL-23 emendato) + ramo resi backlog + 4 motivi ([brief-db-fatturazione-ddt-resi.md](brief-db-fatturazione-ddt-resi.md)) · BE/FE: brief a valle, da scrivere | 🟡 brief DB **rifondato 2026-07-17** (§3 riscritto a contatore dopo verifica su DB vivo — la forma a 3 predicati non reggeva, §3f; **cancelli tutti chiusi**: frontiera EMESSA, chiave partita, resi DRAFT, ordine CONFERMATO) — **PRONTO PER IL TEAM DB**. Restano 2 ❓ non bloccanti (§4a quinto ramo `vw_stato_sorgente_ddt` · §4d grana backlog resi). Brief satellite: [immutabilità quantità + porta oneri](brief-db-immutabilita-quantita-e-porta-oneri.md) (priorità sotto, indipendente) |
| 4 — Guida | docs | sezione "Cruscotti fatturazione" (linguaggio non tecnico) | ⬜ (dopo 3-ter) |
