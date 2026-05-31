# Regola del 2 — caccia duplicazioni nel frontend Vendite

> **Data analisi:** 2026-05-31
> **Ambito:** solo frontend, dominio `frontend/src/vendite` (offerte, preventivi, contratti, _shared)
> **Profondità:** media
> **Esito:** SOLO REPORT. Nessun file è stato modificato. Questo documento è una
> mappa di lavoro: serve a decidere *se* e *cosa* estrarre più avanti, un pezzo
> alla volta, secondo la "regola del 2" (alla seconda occorrenza di uno schema
> si estrae un building block invece di duplicare).

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

### 1. API dei Componenti BoM (il candidato migliore)

Le stesse quattro chiamate (anteprima / elenco / modifica / cancella componenti)
sono scritte due volte in modo identico:

- `frontend/src/vendite/api/contratti.js` (righe 98-126)
- `frontend/src/vendite/preventivi/api/preventiviApi.js` (righe 121-151)

**Idea di estrazione:** una funzione-fabbrica unica che, dato il percorso base,
genera le quattro chiamate. Si riusa in entrambi i posti.

> ⚠️ Le API analoghe delle **offerte** (`offerteApi.js`) **non** vanno incluse:
> usano un percorso diverso (`eccezioni/` invece di `righe/`). È una differenza
> voluta, non una duplicazione.

### 2. Lettura componenti di una riga (`rowComponenti`)

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

### 3. Gestione della finestra "Componenti"

I componenti grafici della finestra sono già condivisi, ma la **logica che la
governa** (quando aprirla in automatico, come azzerare i dati al cambio
articolo, cosa fare alla conferma) è ripetuta in preventivi e contratti.
Candidato a un composable di orchestrazione.

### 4. Banner di errore prezzo "L2"

Il riquadro rosso che chiede l'approvazione quando il prezzo sfora i limiti è
quasi identico (~95%) tra preventivi e contratti. **Attenzione:** va estratto
solo il riquadro grafico e poco altro; la logica che gira "dietro al bottone" è
diversa nei due casi e va lasciata separata.

### 5. Adattatore delle Note

I drawer delle note di **contratto** e **preventivo** sono identici; quello
delle **offerte** somiglia ma usa nomi di campo diversi. Si possono unificare i
due identici; l'offerta resta a parte.

### 6. Tabella di ricerca/elenco (Vendite)

Le liste di contratti, offerte e preventivi hanno la stessa "ossatura"
(filtri + barra azioni + menu di riga + finestre PDF/Note). Però circa il 70%
del codice resta specifico per ogni dominio (colonne, stati, etichette): il
guadagno di un'astrazione c'è ma è medio, non enorme.

### 7. Recupero valuta dal cliente

Quando si sceglie il cliente, i tre drawer (offerta, contratto, preventivo)
recuperano la valuta predefinita. **Rischio concreto:** solo il drawer dei
preventivi ha una protezione contro le "risposte in ritardo" (race condition)
che gli altri due non hanno. Un'unificazione fatta male potrebbe far perdere
quella protezione o introdurre bug. Da fare solo con molta attenzione.

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
