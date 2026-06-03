# Regola del 2 — caccia duplicazioni nel frontend Vendite

> **Data analisi:** 2026-05-31
> **Ambito:** solo frontend, dominio `frontend/src/vendite` (offerte, preventivi, contratti, _shared)
> **Profondità:** media
> **Stato:** ✅ **CHIUSO (2026-06-03).** Partito come report, ora tutti i
> candidati hanno una risoluzione (vedi "Esito finale" sotto). Documento
> archiviato in work-done.

## Esito finale (2026-06-03)

**Estratti** (regola del 2 applicata):

- **#1** API Componenti BoM → `core/api/componentiBom` (`makeComponentiBomApi`)
- **#2** `rowComponenti` → `_shared/componenti/rowComponenti.js`
- **#3** logica dialog componenti → `_shared/componenti/useComponentiDialog.js`
- **#4** banner errore L2 → `_shared/pricing/L2ErrorBanner.vue` + `classifyL2Error.js` (solo il riquadro; logica dietro lasciata per dominio)
- **#5** drawer note → `_shared/note/VenditeNoteDrawer.vue` (incluse le offerte, campi label parametrizzati)
- **#7** valuta/default-BA → `_shared/baDefaults/useBaFormDefaults.js` (guard race-condition estesa a tutti e tre)

**NON estratti — e perché:**

- **#6 Tabella ricerca/elenco** → l'ossatura comune (toolbar, kebab, search
  composable) è **già** building block riusati da tutte e tre; il ~70%
  residuo è specifico di dominio (astrazione prematura). In più la base è
  divergente (`ContrattiSearchTable` su `ListaConfigurabile`,
  offerte/preventivi su `<DataTable>`): la riusabilità reale passa da **DEF-8**
  (migrazione a `ListaConfigurabile`), non da un BB scheletro che sarebbe
  throwaway. Dettagli nella sezione #6.
- **Casi 🔴 (`onBaSelected`, finestre emissione, store-action con notifica)** →
  falsa duplicazione: codice simile che risolve problemi diversi per dominio.
  Unificarli peggiorerebbe la leggibilità. Lasciati separati per scelta.
- **Falso allarme "watch UoM mancante"** → verificato NON essere un bug
  (modelli di prezzo diversi: resolver vs inserito a mano). Nessun intervento.

---

> **Nota storica.** Questo documento è nato come **report** (mappa di lavoro)
> per decidere *se* e *cosa* estrarre, un pezzo alla volta, secondo la "regola
> del 2" (alla seconda occorrenza di uno schema si estrae un building block
> invece di duplicare). Le sezioni sotto conservano l'analisi originale con i
> marker di stato per-candidato.

## Com'è stata fatta l'analisi (in breve)

Sono stati lanciati più agenti di ricerca in parallelo sul codice del dominio
vendite, ognuno con un angolo diverso (offerte, preventivi, parte condivisa,
pattern noti del progetto). Hanno prodotto **37 candidati**. Ogni candidato è
poi passato a un secondo agente "scettico" che ha aperto i file alle righe
indicate per verificare se fosse una **vera duplicazione** o solo una
somiglianza apparente.

Risultato del filtro:

| | Conteggio |
|---|---|
| Candidati grezzi | 37 |
| Confermati come duplicazione reale | 15 |
| Scartati (somiglianza superficiale o divergenza giustificata) | 22 |

Il dato importante non è solo "cosa duplicare", ma anche **cosa NON toccare**:
in molti casi due pezzi di codice si somigliano ma risolvono problemi diversi,
e unificarli peggiorerebbe la leggibilità. La verifica ha separato i due casi.

---

## 🟢 Candidati puliti — estrazione consigliata, basso rischio

Qui le occorrenze sono quasi identiche e le differenze trascurabili. Sono i
punti dove la "regola del 2" si applica nel modo più netto.

### 1. API dei Componenti BoM (il candidato migliore) — ✅ FATTO

Le stesse quattro chiamate (anteprima / elenco / modifica / cancella componenti)
sono scritte due volte in modo identico:

- `frontend/src/vendite/api/contratti.js` (righe 98-126)
- `frontend/src/vendite/preventivi/api/preventiviApi.js` (righe 121-151)

**Idea di estrazione:** una funzione-fabbrica unica che, dato il percorso base,
genera le quattro chiamate. Si riusa in entrambi i posti.

> ⚠️ Le API analoghe delle **offerte** (`offerteApi.js`) **non** vanno incluse:
> usano un percorso diverso (`eccezioni/` invece di `righe/`). È una differenza
> voluta, non una duplicazione.

### 2. Lettura componenti di una riga (`rowComponenti`) — ✅ FATTO

La stessa coppia di funzioni (estrai i componenti di una riga / verifica se la
riga ha un "bundle") è copiata identica in due drawer:

- `frontend/src/vendite/components/ContrattoRigheDrawer.vue` (righe 186-203)
- `frontend/src/vendite/offerte/components/OffertaEccezioniDrawer.vue` (righe 38-93)

**Idea di estrazione:** un piccolo composable condiviso.

---

## 🟡 Candidati validi ma con un "ma" — estrazione possibile, serve attenzione

Qui la duplicazione è reale, ma le occorrenze hanno differenze che vanno gestite
con cura: estrarre senza pensarci rischia di nascondere comportamenti diversi o
di far perdere protezioni esistenti.

### 3. Gestione della finestra "Componenti" — ✅ FATTO (2026-05-31)

I componenti grafici della finestra sono già condivisi, ma la **logica che la
governa** (quando aprirla in automatico, come azzerare i dati al cambio
articolo, cosa fare alla conferma) era ripetuta in preventivi, offerte e contratti.

**Estratto** nel composable [`useComponentiDialog`](../../../../frontend/src/vendite/_shared/componenti/useComponentiDialog.js),
adottato dai 3 drawer. Differenze di dominio passate come getter (`isCreate`,
`isComposito`, `isPadreComposito`, `qtaValida`). Fatto insieme al refactor
`qta_operativa` (un'unica passata FE). Verifiche: build FE verde, 271/271 test
BE verdi, smoke DB ok. Documentato nel catalogo BB FE.

> **Aggiornamento (post-analisi quantità).** Questo era il punto da cui è emerso
> il problema dell'asimmetria `quantita` / `qta_operativa` (vedi
> [refactor-quantita-qta-operativa.md](refactor-quantita-qta-operativa.md)).
> All'inizio #3 era classificato "con un ma" proprio perché i tre drawer
> usavano un campo quantità diverso (`form.quantita` in preventivi/offerte vs
> `form.qta_operativa` nei contratti), il che avrebbe richiesto un composable a
> molti input e a rischio. **Dopo il refactor della quantità** tutti e tre i
> drawer leggeranno `form.qta_operativa`: la divergenza che rendeva #3 delicato
> **sparisce**, e #3 diventa **evidentemente una semplice ottimizzazione** —
> non più un intervento "con un ma":
>
> - da 2 a **3 consumer uniformi** (preventivi + offerte + contratti) → "regola
>   del 2" rafforzata;
> - input del composable ridotti a `form` + due getter di lifecycle/dominio
>   (`isCreate`, `isPadreComposito`), non più il campo quantità;
> - watch di auto-apertura, `showComponentiDialog` e prop `:quantita` diventano
>   identici nei tre;
> - rischio ridotto al normale threading reattivo (passare getter/ref corretti).
>
> **Ordine obbligato**: #3 va fatto **dopo** il refactor quantità (DB→BE→FE).
> Farlo prima cristallizzerebbe l'asimmetria dentro il composable.

### 4. Banner di errore prezzo "L2" — ✅ FATTO (2026-06-02)

Il riquadro rosso che chiede l'approvazione quando il prezzo sfora i limiti era
quasi identico (~95%) tra preventivi e contratti. Estratto solo il riquadro
grafico (`_shared/pricing/L2ErrorBanner.vue` + `classifyL2Error.js`); la logica
"dietro al bottone", diversa nei due casi, è rimasta separata.

### 5. Adattatore delle Note — ✅ FATTO (2026-06-03)

I drawer note di **contratto** e **preventivo** erano identici; quello delle
**offerte** divergeva solo per i nomi-campo della label (`articolo_codice`/
`articolo_descrizione` vs `codice_articolo`/`descrizione`), non per le note (la
tabella/API note è la stessa per tutti i domini).

**Estratto** il BB [`VenditeNoteDrawer.vue`](../../../../frontend/src/vendite/_shared/note/VenditeNoteDrawer.vue)
(in `_shared/note/`): assorbe `apiClient` + mappatura righe→opzioni + render del
`NoteDrawer` generico. Parametri di dominio: `dominio`, `id`, `title`, `righe`,
`codeField`/`descField`. I 3 wrapper di dominio (Contratto/Preventivo/Offerta
NoteDrawer) sono ridotti a shim thin che delegano — **inclusa l'offerta** (i
nomi-campo passati come prop), simmetria piena. Call site invariati, build FE
verde.

### 6. Tabella di ricerca/elenco (Vendite) — ❌ NON estrarre (assorbito da DEF-8)

Le liste di contratti, offerte e preventivi avevano la stessa "ossatura"
(filtri + barra azioni + menu di riga + note). **Rivalutato 2026-06-03**:
quell'ossatura è **già** building block core riusati da tutte e tre
(`PageActionsBar`, `RowActionsMenu`, `useSearchTable`, NoteDrawer per dominio
dopo #5). Il ~70% residuo è specifico di dominio (colonne, stati, azioni,
etichette): un BB unico sarebbe astrazione prematura.

Inoltre la base è divergente: `ContrattiSearchTable` è migrata a
`ListaConfigurabile` (2026-06-03), mentre `OfferteSearchTable` /
`PreventiviList` sono ancora `<DataTable>`. La direzione reale è **DEF-8**
(migrare anche offerte/preventivi a `ListaConfigurabile`), che dissolve il
boilerplate tabella senza bisogno di estrarre lo scheletro vecchio.
Conclusione: niente estrazione qui; la riusabilità passa da DEF-8.

### 7. Recupero valuta dal cliente — ✅ FATTO (2026-06-03)

Quando si sceglie il cliente, i tre drawer (offerta, contratto, preventivo)
recuperano la valuta predefinita. Solo il drawer dei **preventivi** aveva la
protezione contro le "risposte in ritardo" (race condition, token latest-wins)
che gli altri due non avevano.

**Estratto** il composable [`useBaFormDefaults`](../../../../frontend/src/vendite/_shared/baDefaults/useBaFormDefaults.js)
(in `_shared/baDefaults/`): incapsula il watcher su `billing_account_id` con la
guard token **inclusa**, valuta BA-wins, skip in edit, e un callback `apply`
opzionale per i default extra (preventivi: `termine_pagamento_id`). I 3 drawer
sostituiscono il watcher inline con la chiamata al composable. **Risultato:
offerte e contratti ereditano la guard race-condition** che prima avevano solo
i preventivi — la protezione è stata *estesa*, non persa. Build FE verde.

---

## 🔴 Casi confermati ma da NON estrarre (falsa duplicazione)

Codice che si somiglia ma risolve problemi diversi: unificarlo
peggiorerebbe le cose. Lasciare separato è la scelta giusta.

- **Selezione cliente + reset campi (`onBaSelected`)** — la logica diverge per
  dominio (utility, categoria, istanza). Astrarre sarebbe prematuro.
- **Finestre di emissione documento** — sono già "involucri sottili" sopra un
  componente generico comune. Un ulteriore livello sarebbe inutile.
- **Azioni degli store con notifica di modifica** — è un modo di scrivere già
  standard nel progetto, non una cattiva duplicazione.

---

## ⚠️ Falso allarme verificato: il "watch UoM mancante" NON è un bug

Durante la caccia era emerso un sospetto: il drawer righe contratto sembrava
"dimenticare" di azzerare il prezzo quando si cambia unità di misura, cosa che
invece i preventivi fanno. **Verificato di persona: non è un bug.**

Il motivo è che i due usano due modelli di prezzo diversi:

- **Preventivi:** il prezzo è **suggerito automaticamente** da un calcolo
  (resolver). Cambiando unità di misura cambia il prezzo di listino, quindi è
  giusto azzerarlo e farlo ricalcolare.
- **Contratti (eccezioni):** **non c'è nessun calcolo automatico.** Il prezzo è
  un valore **inserito a mano dall'operatore** (o precompilato dal listino negli
  ingressi dedicati). Non c'è nulla da "ricalcolare" al cambio unità, e nei casi
  principali articolo e unità non sono nemmeno modificabili.

In pratica il primo agente aveva accorpato due situazioni diverse come se
fossero la stessa cosa. **Nessun intervento necessario.**

---

## Come procedere (proposta)

Nessuna estrazione è stata fatta. Quando si vorrà intervenire, l'ordine
suggerito per rischio crescente è:

1. **API Componenti BoM** (#1) — più pulito, zero controindicazioni.
2. **`rowComponenti`** (#2) — due occorrenze identiche.
3. Poi, valutando caso per caso, i candidati 🟡 (#3–#7).

Per ciascuno, prima di scrivere codice astratto va dichiarato il disegno del
building block e atteso l'OK, come da prassi del progetto.
