# Brief Design — Cruscotti fatturazione a due lenti (Competenza a valle + Backlog a monte)

> **Tipo**: brief di design autorevole (modello + piano di ridisegno) · **Data**: 2026-07-04
> **Owner**: Tid · **Stato**: 🟢 **Fase 0 + 0-bis COMPLETE (2026-07-04)** — disegno unitario
> + tutti i punti aperti chiusi (B/C/D/Lente 1 → decisioni DL-1..8). Prossimo: mini-brief DB
> timestamp (§7) in parallelo + Fase 1 Lente Competenza. Ridisegna
> la dashboard pre-fatturazione a 5 card (design-of-record
> [brief-design-dashboard-fatturazione.md](brief-design-dashboard-fatturazione.md),
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
> [brief-design-dashboard-fatturazione.md](brief-design-dashboard-fatturazione.md) (la
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
| **Layout 5 card su asse proxy-mese** + view/route pre-fatturazione | **Dismesso** a copertura completata dalle due lenti |

**Congelamento**: la dashboard pre-fatturazione attuale resta viva **com'è** (vista
provvisoria) e **non riceve altri investimenti**, finché le due lenti non ne coprono il
perimetro. Non si butta oggi, non si rifinisce: si sostituisce.

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

## 10. Decisioni prese (2026-07-04, Tid)

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

## 11. Piano di sviluppo

| Fase | Dove | Deliverable | Stato |
|---|---|---|---|
| 0 — Disegno unitario | questo brief | due lenti + decomposizione + punti aperti B/C/D | ✅ 2026-07-04 |
| 0-bis — Chiusura punti aperti | con Tid | decisioni **B, C, D, Lente 1** (DL-6/7/8 + C) | ✅ 2026-07-04 |
| DB — Timestamp transito | `dev/db-tid` (brief al team) | **validare** `attivita_fatturabili.data_insert` come data-emissione (casi reset/re-emissione); eventuale vista di comodo (§7) | ⬜ (parallelo; forse nessun oggetto nuovo) |
| 1 — Lente Competenza | `dev/backend-tid` | resolver a valle (commessa→fattura per competenza), **4 blocchi predisposti** (§4) + BE + FE; riusa resolver Commesse | ⬜ |
| 2 — Lente Backlog | `dev/backend-tid` | lista non-collegati per anzianità + `motivo_fermo` + azionabilità; v1 anzianità-proxy | ⬜ (dopo 0-bis; raffinata dal DB) |
| 3 — Dismissione | `dev/backend-tid` | rimozione dashboard pre-fatturazione a copertura completata | ⬜ |
| 4 — Guida | docs | sezione "Cruscotti fatturazione" (linguaggio non tecnico) | ⬜ |
