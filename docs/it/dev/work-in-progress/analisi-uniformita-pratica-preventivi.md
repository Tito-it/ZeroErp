# Analisi — Uniformità pratica ⇄ programma standalone (preventivi/ordini/commesse)

> **Tipo**: analisi di design (non implementativa) · **Data**: 2026-06-29
> **Owner**: Tid · **Stato**: 🟢 aperta — definisce il principio e la riprogettazione.
>
> **Origine**: smoke su pratica `PRA-0000216` (preventivo DIFFERITA, tutta merce).
> A video tutto verde, ma a DB **nessuna commessa**: l'ordine creato è rimasto
> DRAFT. Indagando sono emerse più **divergenze** fra il percorso pratica e il
> programma standalone preventivi.
>
> **Documenti collegati**: [gestione-preventivi.md](../../guide/gestione-preventivi.md)
> (§8 smistamento), [gestione-ordini.md](../../guide/gestione-ordini.md) (§9-§10
> conferma + push commessa), [gestione-pratiche-come-procedere.md](gestione-pratiche-come-procedere.md),
> [analisi-pratiche-domini-anello3.md](analisi-pratiche-domini-anello3.md) (§5 caso vendite).

---

## 1. Il principio (vincolo di progetto, deciso da Tid)

**La pratica non deve divergere dal programma standalone.** Tutto ciò che il
programma di gestione preventivi (e ordini, commesse, ...) offre come scelta
all'operatore — revisione, selezione righe da smistare, modalità di
fatturazione — la pratica **deve offrirlo allo stesso modo**, riusando le stesse
UI/azioni.

Corollario: eventuali **scorciatoie** (es. saltare la selezione righe quando
sono tutte di una sola natura) si implementano **nel programma base**, così la
pratica le eredita. Mai una scorciatoia che esista solo dentro la pratica: i due
percorsi devono restare **uniformi**, una sola fonte di verità del comportamento.

---

## 2. Come funziona davvero il modello preventivo → ordine → commessa

Dal catalogo ogni articolo porta una **natura di vendita** con destinazione fissa
(congelata sulla riga):

| Natura | Destinazione | Percorso reale |
|---|---|---|
| MERCE | ORDINE | preventivo → **ordine** → *(Emetti = conferma)* → *(Push a commessa)* → fattura |
| SERVIZIO_UNA_TANTUM | COMMESSA | preventivo → **commessa** diretta → fattura |
| SERVIZIO_RICORRENTE | CONTRATTO | bloccato sul preventivo → offerta→contratto |

Punto cruciale: **la merce non va mai diretta in commessa**. Passa da un
**ordine** (documento commerciale reale: numero, PDF di conferma, cliente
bloccato). La commessa della merce è solo il *veicolo di fatturazione* a valle
dell'ordine **confermato** (commessa `tipo=AUTO`). Per la merce servono quindi
**tre atti**, due dei quali sull'ordine (guida ordini §9-§10):
1. smistamento preventivo → ordine `DRAFT`;
2. **Emetti** ordine `DRAFT → CONFERMATO` (+ PDF) — obbligatorio prima del push;
3. **Push a commessa** `CONFERMATO → EVASO` → crea commessa AUTO → fattura.

Nel programma standalone tutte e tre sono passi espliciti dell'operatore.

---

## 3. Mappa delle divergenze (standalone vs pratica)

| Scelta operatore | **Standalone** | **Pratica `PREVENTIVI_DIFFERITA`** | Esito |
|---|---|---|---|
| **Accettazione**: modalità fatturazione + competenza | dialog su EMESSO→ACCETTATO, salvati sul preventivo | accettazione = completare il flusso APPROVAZIONE_CLIENTE (handler `accetta_preventivo`); **nessun dialog** | 🔴 modalità **cablata** nel template (`handler_params={"modalita_fatturazione":"DIFFERITA"}`); competenza **mai chiesta** |
| **Selezione righe** da smistare | *Pannello Smistamento*: checkbox per riga (default tutte le residue), un click "Smista" | handler `push_preventivo` smista **tutto automatico** per natura | 🔴 nessuna scelta; pannello bypassato |
| **Revisione** preventivo | disponibile su EMESSO (`crea_revisione` data-driven) | **non esposta** nel percorso pratica | 🔴 mancante |
| **Merce → ordine → commessa** | passi espliciti sull'ordine (Emetti, Push) | handler crea **solo l'ordine DRAFT**; non lo conferma né lo pusha | 🔴 merce **non arriva in commessa**; ordine resta DRAFT |
| Etichetta flusso CONFERMA | — | "Conferma e **push del preventivo a commessa**" | 🟡 fuorviante per la merce (promette commessa, produce ordine) |

### 3.1 Bug/gap concreti accertati

1. **🔴 Merce ferma all'ordine DRAFT (PRA-0000216).** L'handler `CONFERMA_VENDITA`
   per la merce esegue solo `fn_push_preventivo_a_ordine` (ordine DRAFT) e poi
   evade il preventivo. Non c'è Emetti ordine né push ordine→commessa → nessuna
   commessa. Riscontro DB: ordine 143 DRAFT, 0 commesse, preventivo 375 EVASO,
   pratica 290 CHIUSA. *(giornale: `DOMINIO_ORDINE_CREATO` + `DOMINIO_PREVENTIVO_EVASO`,
   nessun `DOMINIO_COMMESSA_CREATA`.)*
2. **🔴 Competenza DIFFERITA mai popolata.** [push_preventivo_handler.py:205-214]
   pretende `meta["competenza_fatturazione"]`, ma il FE pratica non la chiede da
   nessuna parte. Sul caso merce-only il ramo commessa non scatta e non emerge;
   con **righe servizio** in una pratica DIFFERITA la CONFERMA fallirebbe con
   `E_VENDITA_COMPETENZA_RICHIESTA`.
3. **🔴 Revisione non disponibile** nel percorso pratica (lo stesso
   `PreventiviDrawer` non espone `crea_revisione` quando aperto da pratica).
4. **🟡 Descrizione flusso CONFERMA fuorviante** per la merce.

Causa comune: **la pratica reimplementa il workflow in un handler che scavalca le
scelte operatore**, invece di guidare l'operatore alle azioni standalone.

---

## 4. Direzione proposta (uniformità + merce esplicita)

**La pratica orchestra la sequenza, ma ogni passo riusa l'azione/UI standalone.**
Niente più handler monolitico che decide al posto dell'operatore.

| Flusso pratica | Cosa fa (= identico allo standalone) |
|---|---|
| PREVENTIVAZIONE | apre `PreventiviDrawer` (già così) **+ revisione disponibile** come nello standalone |
| APPROVAZIONE_CLIENTE | accettazione con lo **stesso dialog** modalità fatturazione + competenza → salvati sul preventivo (elimina `handler_params` cablati e il gap competenza) |
| SMISTAMENTO | apre lo **stesso Pannello Smistamento** (selezione righe). Merce→ordine, servizi→commessa, selettivi |
| CONFERMA_ORDINE → INVIO_COMMESSA (per la merce) | passi espliciti sull'ordine (Emetti + Push a commessa), come nel programma ordini |

**Scorciatoia uniforme** (richiesta di Tid: saltare la selezione quando non
serve): si implementa **nel Pannello Smistamento standalone** (es. quando tutte
le righe residue hanno un'unica natura, proporre "Smista tutto" senza obbligare
la selezione manuale). Così vale ovunque, pratica inclusa — non una deroga
interna alla pratica.

Opzione scartata (A — "pratica nasconde l'ordine e genera la commessa"):
auto-confermerebbe un documento commerciale reale (l'ordine, con PDF/numero) che
l'operatore non vede mai → perdita di un atto commerciale e divergenza dal
modello. Si preferisce **B (ordine esplicito)**, coerente col flusso standalone.

---

## 5. Decisioni prese (Tid, 2026-06-29)

1. **Smistamento**: la pratica apre lo **stesso Pannello Smistamento** dello
   standalone; in più si aggiunge nel **programma base** una scorciatoia
   **"Smista tutto"** quando le righe residue hanno **un'unica destinazione**
   (es. tutte merce). La comodità vale ovunque, non solo in pratica.
2. **Merce in commessa**: si aggiungono **flussi espliciti di conferma ordine**
   (Emetti ordine + Push a commessa). La merce raggiunge la commessa passando
   per l'ordine, visibile (no auto-nascondi).
3. **Accettazione**: modalità fatturazione + competenza si scelgono nel **dialog
   di accettazione** (come standalone) e si salvano sul **preventivo**; non più
   cablate nel template pratica né attese da `meta`.
4. **Revisione**: **resta** disponibile nella pratica (uniforme); si gestisce
   l'aggancio `pratiche_sorgenti` ROOT → **rev attiva**. La "nuova pratica" resta
   solo per l'abbandono/restart, non per il giro di trattativa.

---

## 6. Piano operativo

> Sequenza: prima i prerequisiti **DB** (brief al team), poi **BE**, poi **FE**.
> Non si tocca BE/FE prima dei prerequisiti DB (vincolo di progetto).

### 6.0 Conseguenza strutturale — fusione dei tipi pratica

`PREVENTIVI_IMMEDIATA` (9002) e `PREVENTIVI_DIFFERITA` (9003) differiscono **solo**
per `handler_params.modalita_fatturazione` cablato sul flusso CONFERMA. Con la
decisione 3 la modalità si sceglie all'accettazione → i due tipi **si fondono in
un unico `PREVENTIVI`**. Meno catalogo, una sola UX. *(Da confermare in apertura
brief DB: migrazione delle pratiche storiche dei due tipi al tipo unico.)*

### 6.1 Nuova sequenza di flussi (tipo unico `PREVENTIVI`)

| Seq | Flusso | Azione = standalone | Note |
|---|---|---|---|
| 10 | RICHIESTA_CLIENTE | (manuale) | invariato |
| 20 | PREVENTIVAZIONE | apre `PreventiviDrawer` **+ revisione** | dec. 4 |
| 30 | APPROVAZIONE_CLIENTE | **dialog accettazione** (modalità+competenza) → preventivo ACCETTATO | dec. 3 |
| 40 | SMISTAMENTO | apre **Pannello Smistamento** (merce→ordine, servizi→commessa) | dec. 1; sostituisce l'handler auto |
| 50 | CONFERMA_ORDINE | **Emetti** ordine `DRAFT→CONFERMATO` (+PDF) | dec. 2; solo se esiste ramo merce |
| 60 | INVIO_COMMESSA | **Push** ordine `CONFERMATO→EVASO` → commessa AUTO | dec. 2; solo se esiste ramo merce |

I flussi 50/60 sono **condizionali** (solo se lo smistamento ha prodotto un
ordine). Il ramo servizi chiude la sua commessa già allo step 40.

### 6.2 DB (brief al team `dev/db-tid`)

- **Seed**: tipo unico `PREVENTIVI` (+ migrazione 9002/9003 → unico), nuovi
  `template_flussi` 10-60, `template_flussi_prerequisiti` esito-aware, `azioni_ui`
  per SMISTAMENTO/CONFERMA_ORDINE/INVIO_COMMESSA, binding `handler_eventi` dove
  serve. Rimuovere `handler_params.modalita_fatturazione` dal CONFERMA.
- **Aggancio revisione**: `pratiche_sorgenti` ROOT deve seguire la **rev attiva**
  del preventivo (fn/trigger su `fn_crea_revisione_preventivo` o risoluzione
  dinamica via `vw_preventivi.is_attiva`). Da progettare nel brief.

### 6.3 BE (`apps/vendite`, `apps/pratiche`)

- **Ritiro/snellimento** dell'handler monolitico `vendita.push_preventivo`: lo
  smistamento torna alle azioni standalone (`genera_ordine`/`push_commessa`)
  guidate dai flussi; l'handler non decide più al posto dell'operatore.
- Accettazione: il path pratica riusa il **service accettazione standalone**
  (persiste modalità+competenza sul preventivo). Rimuove la dipendenza da
  `meta["competenza_fatturazione"]` (chiude **bug §3.1.2**).
- Flussi 50/60: agganciano le azioni ordine esistenti (Emetti, Push commessa) +
  giornale `DOMINIO_*` + `pratiche_sorgenti` (ordine COLLEGATO, commessa COLLEGATO).

### 6.4 FE

- **Pannello Smistamento base**: aggiungere il pulsante **"Smista tutto"** quando
  destinazione unica (riuso in pratica e standalone).
- Pratica: i flussi 40/50/60 aprono le **stesse** UI standalone (pannello
  smistamento, azioni ordine). Drawer preventivo da pratica: **esporre revisione**.
- Accettazione (flusso 30): riusare il **dialog accettazione** standalone.
- Correggere le **descrizioni/etichette** dei flussi (la CONFERMA non promette più
  "push a commessa": ora c'è SMISTAMENTO + CONFERMA_ORDINE + INVIO_COMMESSA).

## 7. Bug chiusi da questo intervento

- 🔴 §3.1.1 merce ferma all'ordine DRAFT → risolto da flussi 50/60.
- 🔴 §3.1.2 competenza DIFFERITA mai popolata → risolto spostando la scelta al
  dialog di accettazione (dec. 3).
- 🔴 §3.1.3 revisione assente → risolto (dec. 4).
- 🟡 §3.1.4 etichetta fuorviante → risolto (nuove etichette flussi).

> Stato: piano approvato a livello di direzione. Prossimo passo operativo =
> **brief DB** (§6.2) come primo deliverable; BE/FE seguono i prerequisiti DB.
