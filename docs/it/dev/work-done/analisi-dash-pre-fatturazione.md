# Analisi — Dashboard pre-fatturazione: bucket mensile, situazioni anomale, gap temporale

> ✅ **CHIUSA (2026-07-04) — spostata in `work-done`.** Le domande aperte A-E di questo
> documento sono tutte decise; la loro risoluzione vive ora nel design-of-record
> [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md)
> (ridisegno a **due lenti**: Competenza a valle + Backlog a monte). In sintesi: **A** →
> risolta dalla separazione delle lenti (asse competenza vera solo a valle); **B/C/D** →
> decise (DL-6/7/8 + C nel nuovo brief); **E** → già decisa (`20260703-61`). Conservato come
> traccia dell'analisi che ha originato il ridisegno.
>
> **Tipo**: documento di **analisi descrittiva** (capire quanto costruito prima di
> decidere). NON contiene decisioni: le apre. · **Owner**: Tid · **Data**: 2026-07-04.
> **Origine**: revisione UI della dashboard fatturazione con Tid — due domande aperte:
> (1) come è stato fatto il "mese" per aree che non hanno una competenza propria;
> (2)/(3) come rendere leggibili le anomalie e i recuperi tardivi.
> **Correlato**: `brief-design-dashboard-fatturazione.md` (design autorevole, Fasi 1-3
> fatte); `work-done/brief-db-dash-commesse-attivita-annullate-escluse.md` (bug void attività
> commessa); viste `vendite.vw_dash_fatturazione_*`.

---

## 0. Perché questo documento

Prima di aggiungere UI (breakdown del fermo, pagina backlog/arretrati) serve mettere nero
su bianco **cosa la dashboard misura davvero oggi**, area per area. Il punto più delicato,
emerso da Tid, è che **solo le commesse hanno una competenza propria**: per le altre aree
il "mese" è stato *derivato*, e la derivazione non è uniforme. Se non è chiaro questo, ogni
discussione sulle anomalie parte storta.

## 1. Come viene derivato il MESE di competenza, per area

Il "mese" della dashboard (`competenza_mese`) è la chiave dell'asse verticale (pannello
mesi) e del semaforo. Ma dietro quella singola colonna ci sono **cinque derivazioni
diverse**, lette dalle viste vive:

| Area | Espressione del `competenza_mese` | Natura | Grana |
|---|---|---|---|
| **Commesse** | `commesse_attivita.competenza_mese` | **Competenza vera** (NOT NULL, normalizzata dal trigger) | **per attività** |
| **Preventivi** | `COALESCE(testata.competenza_mese, mese(validita_dal), mese(data))` | Competenza **se presente**, altrimenti **proxy** | per documento (testata) |
| **Ordini** | `mese(ordini.data)` | **Proxy**: mese della *data ordine* | per documento |
| **Offerte** | `mese(COALESCE(validita_dal, data_emissione, data_insert))` | **Proxy**: data di validità/emissione | per documento |
| **Contratti** | `generate_series(mese(valido_dal) … LEAST(mese(valido_al), mese corrente))` | **Periodo esploso**: una riga per **ogni mese coperto** | per documento × mese |

### Cosa significa in pratica

* **Commesse** — l'unica con competenza reale e a grana fine: ogni attività dichiara il suo
  mese di competenza (normalizzato al 1°). È la "competenza vera del funnel" (§3.1 del brief
  design). È qui che il concetto di "mese di fatturazione" è pieno.

* **Preventivi** — hanno una `competenza_mese` di **testata** (nullable), scritta
  **all'accettazione**. Finché il preventivo non è accettato (o se non la valorizza), si
  ripiega su `validita_dal`, poi sulla `data`. Quindi: **un preventivo accettato** ha una
  competenza dichiarata; **uno in bozza/emesso** finisce nel mese della sua validità/data —
  che è un **proxy**, non una competenza scelta.

* **Ordini** — **nessuna** competenza. Il mese è quello della **data dell'ordine**. Un ordine
  scritto a maggio per consegne maggio-giugno cade **tutto** nel bucket di maggio. Non
  rappresenta "quando il ricavo è di competenza", ma "quando è stato emesso il documento".

* **Offerte** — **nessuna** competenza. Proxy sulla data di validità/emissione. Come per gli
  ordini, è un "quando è nato il documento", non un "di quale mese è il ricavo".

* **Contratti** — caso a sé: **non un bucket, ma un'esplosione**. Un contratto valido
  gen-dic **pesa su tutti i 12 mesi** (una riga per mese, cap al mese corrente). Corretto per
  un canone ricorrente, ma con la conseguenza che — **finché non esiste il push ricorrente** —
  ogni contratto risulta `CANONE_NON_GENERATO` **ogni mese** della sua validità (vedi §3.2 del
  brief design: `fn_list_contratti_da_pushare` àncora il canone al solo mese di inizio).

### Conseguenza da tenere presente (non è un bug, è semantica)

Quando la dashboard scrive **"Competenza Maggio 2026"**, quella parola vale cose diverse per
le 5 card:

* Commesse → **competenza reale** di maggio;
* Preventivi → competenza **dichiarata** (se accettati) o **proxy** data/validità;
* Ordini/Offerte → **data del documento** in maggio (proxy);
* Contratti → contratti **attivi** a maggio (periodo).

Non è sbagliato — è il compromesso obbligato del fatto che 3 aree su 5 non hanno una
competenza propria. Ma va **esplicitato nell'UI** (o almeno nella guida), altrimenti chi
legge crede che l'asse "mese" abbia lo stesso significato ovunque. **Domanda aperta A** (§5).

## 2. Cosa misura oggi ogni card — totale / transitato / fermo / abortito

Recap grounded sulle viste, per non discutere a memoria:

| Area | Totale (denominatore) | Transitato | Fermo = totale − transitato | Abortito (fuori confronto) |
|---|---|---|---|---|
| **Preventivi** | Σ valore righe attive | righe con `stato_smistamento ≠ RESIDUA` | righe residue | doc con `esito = NEGATIVO` |
| **Ordini** | Σ valore righe `attivo=true` | righe già in commessa (`segment_key` + EMESSA) | righe non pushate | doc con `esito = NEGATIVO` |
| **Offerte** (conteggi) | 1 per offerta viva | 1 se ha contratto/ordine vivo | offerte senza figlio vivo | doc con `esito = NEGATIVO` |
| **Contratti** (conteggi) | 1 per (contratto × mese coperto) | 1 se canone del mese generato | mesi senza canone | — (annullati esclusi a monte) |
| **Commesse** | Σ `prezzo × quantita` attività **computabili** (no void) | attività `stato_emissione = EMESSA` | attività non emesse | commessa `ANNULLATA` (testata) |

✅ **Buco chiuso** (migration `20260703-61`, 2026-07-04): il denominatore commesse ora
esclude le attività void — `stato_emissione = ANNULLATA` e `stato_approvazione = RIFIUTATA`
(salvo `EMESSA + RIFIUTATA`, già transitata), simmetrico all'`attivo = true` degli ordini.
`RIFIUTATA` = void terminale (decisione Tid). Nessun cambio BE/FE (contratto colonne
invariato). Vedi `work-done/brief-db-dash-commesse-attivita-annullate-escluse.md`.

## 3. Tassonomia delle situazioni "ferme" per **azionabilità**

Il numero unico "fermo" della card mescola motivi con azioni opposte. Classificati:

### 3.a Fisiologico / non ancora azionabile (sollecitare = inutile)
| motivo_fermo | Area | Perché non è un ritardo nostro |
|---|---|---|
| `DOC_BOZZA` | prev, ord, off, contr | Documento ancora in lavorazione interna, non ancora "promesso" |
| `IN_ATTESA_ACCETTAZIONE` | prev, off | Palla al **cliente**: aspettiamo la sua decisione |
| `CANONE_NON_GENERATO` | contr | **Limite strutturale**: manca il push ricorrente (non è un ritardo, è un non-ancora-costruito) |

### 3.b Ritardo recuperabile (azionabile da noi — QUI si sollecita)
| motivo_fermo | Area | Azione tipica |
|---|---|---|
| `RIGA_RESIDUA` | prev | Accettato: smistare le righe residue |
| `PUSH_NON_ESEGUITO` / `PUSH_PARZIALE` | ord | Ordine confermato: eseguire il push a commessa |
| `ATTIVITA_NON_APPROVATA` | comm | Approvare l'attività |
| `ATTIVITA_NON_EMESSA` | comm | Emettere l'attività approvata |

### 3.c Anomalia da rivedere (non un semplice ritardo)
| motivo_fermo | Area | Natura |
|---|---|---|
| `FIGLIO_ABORTITO` | off | Contratto/ordine generato poi annullato: XOR permanente → serve **revisione** dell'offerta |

> Nota: le attività di commessa **void** (ANNULLATA/RIFIUTATA), che prima cadevano
> erroneamente nel fermo, sono ora **escluse a monte** dal resolver (§2 ✅,
> `20260703-61`) — non sono più una riga di questa tassonomia.

**Lettura**: il semaforo ⚠ della card oggi urla allo stesso modo per 3.a, 3.b, 3.c. Chi
gestisce vuole distinguere **3.b** (il suo lavoro) da 3.a (fisiologico) e 3.c (anomalia). Il
drill-down già mostra motivo+stato per riga, ma la **card** no. **Domanda aperta B** (§5):
breakdown del fermo per classe (3.a/3.b/3.c) direttamente sulla card / in un mini-riepilogo.

## 4. Gap temporale — oggi non c'è evidenza dei recuperi tardivi

Osservazione di Tid: *"nel transitato potrebbero esserci competenze recuperate dai mesi
precedenti"*. Analisi:

* Ogni elemento sta nel bucket della **sua** competenza (o proxy). **Non c'è travaso** tra
  mesi: il transitato di marzo è roba di marzo. Man mano che si recuperano arretrati, è il
  **fermo di marzo** che cala (non il transitato di maggio che sale).
* **MA** le viste **non espongono la data di transito/emissione**: non si può distinguere
  "transitato **in tempo** (a marzo)" da "**recuperato in ritardo** (lavorato a maggio ma di
  competenza marzo)". Manca del tutto la **dimensione temporale del transito**.

Per rispondere a *"quali competenze sono state recuperate in ritardo"* (e per la pagina
backlog che Tid propone) serve portare nel modello un **timestamp di transito** — es. data di
emissione dell'attività di commessa, o competenza-lotto vs data-contabilizzazione. Oggi non
esiste: è il **prerequisito** sia dell'evidenza dei recuperi sia della pagina arretrati.
**Domanda aperta C** (§5): serve una data di transito? su quale entità? (probabile brief DB).

## 5. Domande aperte (da decidere INSIEME, dopo aver capito quanto sopra)

* **A — Asse "mese" non uniforme**: come comunichiamo che "Competenza Maggio" significa cose
  diverse per area (competenza vera vs proxy-data vs periodo)? Tooltip per card? Nota in
  guida? Etichette diverse ("Competenza" vs "Data" vs "Periodo")?
* **B — Breakdown del fermo per azionabilità** (3.a/3.b/3.c): dove metterlo? Sulla card (mini
  barra/legenda), in un riepilogo sotto le card, o solo come raggruppamento nel drill-down?
* **C — Dimensione temporale del transito**: serve un timestamp per evidenziare i recuperi
  tardivi e alimentare la pagina backlog? Su quale entità e con quale semantica?
* **D — Pagina backlog/arretrati** (idea Tid): per il mese di fatturazione in corso (+1),
  tutte le attività non concluse dei **mesi precedenti**, ordinate per anzianità. Lente
  diversa dalla dashboard ("cosa è scaduto e recuperabile ora" vs "il mese X è pulito").
  Quali aree includere? Ipotesi di lavoro (da confermare): Preventivi + Ordini + Commesse
  pieni; Offerte **solo** per `FIGLIO_ABORTITO`; Contratti **rinviati** finché non c'è il
  push ricorrente (altrimenti ogni contratto ogni mese = rumore).
* **E — RIFIUTATA (approvazione attività commessa)**: ✅ **DECISA** (Tid 2026-07-04):
  **void terminale**, esclusa come ANNULLATA (migration `20260703-61`). La `RIFIUTATA` non è
  oggi cablata all'L3 (che rifiuta il *prezzo* su preventivi/contratti-righe, non le
  attività): fix difensivo-in-avanti.

## 6. Non-obiettivi di questo documento

* Non decide nulla: enumera e struttura. Le decisioni (A-E) si prendono con Tid.
* Non tocca codice né viste. Il solo intervento già avviato è il **brief DB** per il bug void
  attività commessa (§2 ⚠️), perché è un bug logico e va sbloccato a prescindere.
