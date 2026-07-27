# Brief DB — Emissione fattura mirata per gruppo fatturabile + simmetria `fatturazione_immediata`

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-27 · **Owner**: Tid · **Stato**: ⬜ **DA VALUTARE/SVILUPPARE**
> · **Priorità**: 🟠 MEDIA (abilita un'esigenza operativa reale; additivo,
> nessun dato a rischio).
>
> **Come leggere questo brief**: descrive **cosa serve**, non **come farlo**. Le
> scelte implementative (quali funzioni estendere, forma dei parametri, dove
> mettere i filtri, struttura degli indici) sono **vostre**. Dove abbiamo
> verificato un fatto utile a evitarvi un'indagine, lo trovate in §4 «Fatti
> verificati» — è contesto, non una prescrizione.
>
> **Origine**: [analisi-emissione-fattura-ondemand.md](analisi-emissione-fattura-ondemand.md),
> decisioni Tid 2026-07-26/27.
>
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]])
> → breaking secchi ammessi.
>
> **Conseguenza**: BE e FE **attendono** questo lavoro
> ([[feedback_be_fe_attende_prerequisiti_db]]).

---

## 1. Cosa serve, in una frase

Poter **fatturare su richiesta un sottoinsieme preciso di lavoro** — un singolo
documento sorgente, o gli oneri manuali di una commessa — invece che l'intero
mese, e poter **elencare** questi sottoinsiemi per mostrarli all'operatore.

---

## 2. I casi d'uso (concreti)

**UC-1 — «fattura questo preventivo, adesso»**
Il preventivo PRV-0012 del cliente Rossi è stato accettato oggi. L'operatore
vuole la fattura subito, **senza** trascinare dentro il contratto CTR-0007 dello
stesso cliente, che è nella stessa commessa e nello stesso mese.

**UC-2 — «fattura questa penale, adesso»**
Sulla commessa #42 è stato caricato un onere da 500 € (porta oneri). Non
appartiene ad alcun documento. L'operatore deve poterlo **vedere** e
**fatturare** deliberatamente, non aspettare che il giro mensile lo raccolga.

**UC-3 — «mostrami cosa posso fatturare»**
Prima di agire, l'operatore deve vedere l'elenco di ciò che è fatturabile nel
mese, raggruppato in unità su cui può decidere, con quante righe e quanto valore
ciascuna pesa.

**UC-4 — «questo cliente va sempre fatturato subito»**
Un ordine (non solo un preventivo) deve poter essere marcato come *fatturazione
immediata*, così da essere instradato automaticamente sulla corsia veloce.

---

## 3. Requisiti funzionali

### PARTE A — Emissione mirata

#### A1. Il concetto di **gruppo fatturabile**

L'unità su cui l'operatore decide **non è la commessa** (contiene lavoro di
origini diverse) e **non è sempre un documento** (gli oneri non ne hanno).

Un **gruppo fatturabile** è:

- un **documento sorgente** — preventivo, ordine, contratto, DDT, consumo
  (identificato da tipo + identificativo del documento); **oppure**
- l'insieme delle **righe manuali/oneri di una commessa** — righe senza
  documento sorgente, il cui unico contenitore naturale è la commessa.

Serve che il DB sappia esprimere **entrambe** le forme come criterio di
selezione. È il requisito centrale del brief.

#### A2. Fatturare un perimetro ristretto a uno o più gruppi

Deve essere possibile eseguire il giro di fatturazione limitandolo a **uno o più
gruppi fatturabili** scelti, ottenendo che:

1. vengano fatturate **solo** le righe di quei gruppi;
2. **nessun'altra riga** dello stesso cliente/commessa/mese venga trascinata
   dentro, nemmeno se idonea;
3. le righe non richieste restino **integre e ancora fatturabili** dopo
   l'operazione (nessun effetto collaterale sul loro stato);
4. l'operazione si fermi allo stato **EMESSA** (la numerazione resta un atto
   separato) — coerente col gate fiscale già in vigore.

**Multi-selezione**: il criterio deve accettare **N gruppi in un colpo**, non
solo uno ([[feedback_concentrico_no_yagni]]): l'operatore selezionerà
ragionevolmente più documenti insieme.

#### A3. Elencare i gruppi fatturabili

Serve poter **ottenere l'elenco** dei gruppi fatturabili di un perimetro
(mese di competenza, eventualmente ristretto per cliente/utility/emittente), con
per ciascun gruppo almeno:

| Informazione | Perché serve |
|---|---|
| identificativo del gruppo | per poterlo poi passare come criterio di A2 |
| tipo di gruppo (quale documento, oppure «oneri di commessa») | etichetta a video |
| riferimento leggibile (numero/codice documento, o commessa) | l'operatore lo riconosce |
| cliente | colonna di lista |
| **numero di righe/attività** | dice il *peso* di ciò che si sta per fatturare |
| **valore** | idem |
| commessa di appartenenza | per l'aggancio alle viste esistenti |

⚠️ **Oggi questo elenco non esiste in nessuna forma**: la discovery attuale
lavora a livello di raggruppamento del lotto, non di gruppo fatturabile. È il
dato che alimenta la nuova lista del cockpit.

#### A4. Ripetibilità

Due emissioni mirate **successive** sullo stesso cliente, stesso mese, stessi
parametri di perimetro ma **gruppi diversi** (es. prima il preventivo, poi il
contratto) devono poter **convivere**: la seconda non deve fallire né
interferire con la prima.

> Questo è il punto tecnicamente più delicato e va risolto esplicitamente: oggi
> il contenitore di fatturazione è identificato da una combinazione che **non
> include** il gruppo, quindi due giri mirati sullo stesso perimetro
> ricadrebbero sullo stesso contenitore — che nel frattempo potrebbe essere già
> avanzato di stato. Vedi §6 (decisione vostra).

#### A5. Aggregati per la riga di totali *(rifinitura, priorità bassa)*

Utile poter avere, insieme all'elenco A3, i **totali del perimetro** (numero
gruppi, numero attività, valore complessivo) per mostrare una riga di
riconciliazione. **Voce separabile**: se complica, si rimanda senza bloccare il
resto.

### PARTE B — Simmetria di `fatturazione_immediata`

#### B1. Il fatto

Il flag decide su quale corsia finisce il lavoro:

| Flag | Corsia | Arriva a | Cadenza |
|---|---|---|---|
| `true` | immediata | **DEFINITIVA** (numera da sola) | ogni 2 min |
| `false` | differita | **EMESSA** | mensile |

Ma **il dato esiste solo per i preventivi**: le altre sorgenti restituiscono un
valore fisso `false` al push. Di fatto **solo un preventivo può essere fatturato
subito**, e non per una scelta di dominio ma per un buco di modello.

#### B2. Cosa serve

Che **tutte le sorgenti** (ordini, contratti, DDT — e consumi se il concetto ha
senso lì, valutazione vostra) possano portare l'indicazione «questo va fatturato
subito», e che tale indicazione **arrivi effettivamente** al push e quindi
all'instradamento in corsia.

Nessun'altra modifica: la propagazione alla commessa e il funzionamento delle
corsie **funzionano già** e non vanno toccati.

#### B3. Vincolo semantico da preservare

L'indicazione si stabilisce **prima** che il lavoro entri in commessa. Non deve
diventare un attributo modificabile su lavoro già lavorato: il caso «cambio idea
dopo» è coperto dall'emissione mirata (Parte A), non dal flag.

Se ritenete utile un presidio che lo renda esplicito (impedire la modifica su
documento già pushato), è benvenuto: meglio una regola scritta che una
disciplina affidata alle persone.

---

## 4. Fatti verificati (contesto, per evitarvi l'indagine)

Rilevati sul codice/DB vivo il 2026-07-26/27. Sono **fatti**, non indicazioni
implementative.

1. **La traccia del documento d'origine esiste già riga per riga** su
   `vendite.commesse_attivita` (`sorgente_tipo_id` + `sorgente_uid`). Il dato per
   distinguere i gruppi **c'è già**: manca solo poterlo usare come criterio.
2. **A valle il legame si assottiglia**: su `vendite.attivita_fatturabili` i
   campi sorgente sono rimappati alla commessa, e resta memoria del **tipo** di
   origine ma **non dell'identificativo** del documento. Il collegamento
   all'origine reale passa dalla riga di commessa.
3. **Gli oneri sono sourceless per progetto**: la porta oneri crea righe con
   sorgente nulla e `segment_key` con prefisso `MAN:`, discriminate da
   `tipo_movimento = 'ONERE'`. È **voluto** (brief porta oneri) e non va
   cambiato: è la ragione per cui il criterio deve avere due forme (A1).
4. **La commessa non isola il documento**: è multi-sorgente (`ROOT` + N
   `COLLEGATO`), e un documento è legato a **una sola commessa per sempre**.
   Quindi «filtra per commessa» **non** soddisfa UC-1.
5. **Il documento ha un solo tipo documento fiscale**: il tipo deriva dalla
   configurazione della sorgente, quindi tutte le righe di uno stesso documento
   lo condividono. Gli oneri fanno eccezione (il tipo è scelto al carico).
6. Il flag `fatturazione_immediata` è oggi **colonna reale solo su preventivi**;
   le altre sorgenti lo espongono nel contratto ma con valore costante.

---

## 5. Vincoli non negoziabili

1. **Retro-compatibilità totale.** Il giro schedulato (corsie immediata e
   differita) e il verbo di massa «fattura il mese» **non devono cambiare
   comportamento**. Assenza di criterio = esattamente ciò che accade oggi.
2. **Scope emittente invariato.** Nessun allentamento del perimetro RLS: un
   operatore non deve poter raggiungere, tramite i nuovi criteri, righe che oggi
   non vede.
3. **Nessun effetto collaterale sulle righe non richieste** (A2.3): ciò che non
   si è chiesto di fatturare deve restare esattamente com'era.
4. **Il gate fiscale resta.** L'emissione mirata si ferma a EMESSA; la
   numerazione è un atto separato, con il suo permesso.

---

## 6. Decisioni che spettano a voi

1. **Come garantire la ripetibilità di A4** — cioè come far convivere più
   emissioni mirate successive sullo stesso perimetro. Il nodo esiste **anche**
   per la sola granularità per-cliente, quindi conviene chiuderlo una volta
   sola, qui.
2. **La forma del criterio** di selezione dei gruppi (rappresentazione,
   cardinalità, tipi) e dove applicarlo lungo la catena perché A2.2 e A2.3 siano
   entrambi garantiti.
3. **La forma dell'elenco A3** e se convenga servirlo da una struttura dedicata o
   derivarlo da quelle esistenti.
4. **Se estendere il flag anche ai consumi** (B2) o se lì il concetto non ha
   senso.
5. **Se introdurre il presidio di B3.**

---

## 7. Garanzie attese a fine lavoro

Non «come testare», ma **cosa deve risultare vero**. Da coprire con pgTAP.

| # | Deve essere vero |
|---|---|
| G1 | Senza criterio, il risultato è **identico** a oggi (non-regressione del giro schedulato) |
| G2 | Chiedendo il documento A, vengono fatturate **solo** le righe di A |
| G3 | Se la commessa contiene anche il documento B, le righe di B restano **intatte e ancora fatturabili** |
| G4 | Chiedendo gli **oneri** di una commessa, vengono fatturate solo quelle righe (e sono raggiungibili, cioè non invisibili al criterio) |
| G5 | Chiedendo più gruppi insieme, vengono fatturati **tutti e soli** quelli |
| G6 | Un criterio che non corrisponde a nulla → **zero righe, nessun errore** |
| G7 | Due emissioni mirate successive sullo stesso cliente/mese con gruppi diversi → **entrambe riescono**, nessuna interferenza |
| G8 | L'elenco A3 mostra **sia** i documenti **sia** gli oneri, e i suoi conteggi/valori corrispondono a ciò che l'emissione poi fattura |
| G9 | Un ordine/contratto marcato «fatturazione immediata» viene instradato sulla corsia immediata (B) |
| G10 | Documenti con flag diverso, stesso cliente/utility/periodo → restano su corsie separate (invariante attuale preservato) |

---

## 8. Contratto atteso per BE/FE

Al termine il BE deve poter chiedere:

- *«dammi i gruppi fatturabili del mese M»* (con eventuale restrizione
  cliente/utility/emittente) → per costruire la lista del cockpit;
- *«fattura i gruppi X, Y»* → e ottenere che vengano fatturati solo quelli,
  fermandosi a EMESSA;
- e conoscere **quale contenitore/lotto** è stato prodotto, per portare
  l'operatore direttamente lì a numerare.

Comunicateci: firme definitive, forma del criterio e dell'elenco, esito della
decisione §6.1, e se l'elenco espone gli aggregati di A5.

---

## 9. Riferimenti

- Analisi committente: [analisi-emissione-fattura-ondemand.md](analisi-emissione-fattura-ondemand.md)
  (§5.1-bis commessa≠documento · §5.3 flag · §5.5 design UI e gruppo fatturabile)
- Porta oneri (righe sourceless): [brief-db-immutabilita-quantita-e-porta-oneri.md](brief-db-immutabilita-quantita-e-porta-oneri.md)
- Commessa multi-sorgente: [brief-db-commesse-multi-sorgente.md](../work-done/brief-db-commesse-multi-sorgente.md)
- Guida processo: [fatturazione.md](../../guide/fatturazione.md)
