# Analisi — Emissione fattura on-demand da UI + gestione avanzamento lotti

> **Tipo**: analisi + design · **Data**: 2026-07-26/27 · **Owner**: Tid ·
> **Stato**: 🟢 **ANALISI COMPLETA — design stabilito e confermato** (2026-07-27).
> Tutte le decisioni chiuse (§5). Il
> [brief DB](brief-db-emissione-fattura-per-documento-sorgente.md) è stato
> consegnato, analizzato criticamente e **contiene ora il piano di sviluppo a
> step + il piano pgTAP** (§9-§10 del brief). BE/FE attendono. **Nessun codice
> scritto** per questa slice.
>
> ⚠️ Due punti di questa analisi sono stati **superati** dall'analisi critica DB
> del 2026-07-27: §6.1 (chiuso: nessun conflitto di identità lotto) e §5.3
> (consumi: proposta di esclusione, conferma richiesta). Vedi le note in linea.
>
> **Origine**: manca un modo per **generare una fattura da UI in modo mirato**
> (un cliente, una commessa) senza aspettare il giro notturno. Decisione di
> posizionamento (Tid): la **generazione di 1..N fatture** vive sulla **Lente
> Competenza**; la **gestione dell'avanzamento di stato** vive sui **Lotti**.

---

## 0. TL;DR

- La catena è **un solo processo**, non due job notturni: sorgenti → commessa →
  (emissione = 1° step del lotto) → attività fatturabili → fattura.
- **Competenza fatturazione è già un cockpit d'azione** (Approva / Fattura adesso
  / Rendi definitive), ma "Fattura adesso" è **solo per intero mese**: nessun
  filtro per cliente/utility/commessa.
- **I Lotti già gestiscono l'avanzamento**: il `LottoDrawer` non è diagnostico,
  fa avanza-step / rerun / numera / ristampa / reset. Il pezzo che serviva **c'è**.
- Il gancio per **"fatturare un cliente adesso" esiste già a livello runner**
  (`fn_get_or_create_lotto` sa creare un lotto per billing account): va **esposto**.
- **Design stabilito** (decisioni Tid 2026-07-26):
  1. granularità dell'emissione mirata **fino al documento sorgente** («fattura
     solo questo preventivo») — la commessa **non** isola il documento (§5.1-bis);
  2. flag `fatturazione_immediata` reso **simmetrico su tutte le sorgenti**
     (oggi esiste solo sui preventivi) (§5.4);
  3. **divisione dei compiti**: il *flag* decide l'instradamento **prima** del
     push; la *selezione per documento* è l'azione manuale, usabile **in
     qualsiasi momento** (§5.4);
  4. l'emissione mirata si ferma a **EMESSA** (gate fiscale I-7);
  5. **UI a liste differenziate**: ogni card del funnel scende sull'unità del
     proprio verbo; su `Da emettere` l'unità è il **gruppo fatturabile** =
     documento sorgente **oppure** righe manuali/oneri di una commessa (§5.5).
- **3 difetti del cockpit** rilevati e da correggere a parte (§6-bis): pulsanti
  Approva sempre visibili · verbo «Rendi definitive» sulla card sbagliata ·
  `Emesse non fatturate` è un secchio di residui, non un passaggio.
- **Richiede lavoro DB** → brief dedicato
  [brief-db-emissione-fattura-per-documento-sorgente.md](brief-db-emissione-fattura-per-documento-sorgente.md).
  BE/FE **attendono** ([[feedback_be_fe_attende_prerequisiti_db]]).

---

## 1. La catena reale (confermata sul codice)

```
sorgenti → [push] → commessa / commesse_attivita → [emissione] → attività_fatturabili → [pipeline lotto] → fattura
          |___________ business-operativo ___________|          |__________ fiscale-documentale __________|
```

- **Non esistono due job notturni** «commessa→AF» e «AF→fattura». L'emissione è
  il **primo step (DRAFT) della pipeline del lotto** (task
  `pull_attivita_da_commessa`, handler `pull_attivita_da_commessa_default`,
  `pipeline_step_executor.py:50`). Le attività fatturabili **nascono eseguendo il
  lotto**, non prima.
- Riferimento concettuale: [guida fatturazione](../../guide/fatturazione.md) §Fase 3.

---

## 2. Stato attuale (cosa esiste già)

### 2.1 Competenza fatturazione — il cockpit

Tre verbi sulle card del funnel ([DashboardCompetenzaView.vue](../../../../frontend/src/vendite/views/DashboardCompetenzaView.vue)):

| Verbo | Endpoint | Scope | Si ferma a |
|---|---|---|---|
| Approva | `POST /vendite/fatturazione/approva-competenza/` | mese (+ `commessa_ids[]` opzionale) | — (approva, non fattura) |
| **Fattura adesso** | `POST /vendite/fatturazione/run/` | **solo `competenza_mese`** | **EMESSA** |
| Rendi definitive | `POST /vendite/fatturazione/numera/` | mese | DEFINITIVA (numera) |

**Il limite**: "Fattura adesso" accetta **solo `competenza_mese` + `fino_a_stato`**
(serializer view `views.py:1268-1274`); l'handler forza la corsia **differita**
(`fatturazione_giro_handler.py:36`). Nessun filtro per cliente, utility, commessa
o selezione di attività. Fattura **tutto il mese** (cumulativo ≤ M) nello scope
RLS dell'operatore.

### 2.2 Lotti — già gestione avanzamento

Il [LottoDrawer](../../../../frontend/src/vendite/components/LottoDrawer.vue) **non è
solo diagnostico**: fa avanzare lo stato del lotto da UI. Verbi (mutuamente
esclusivi per stato, bloccati se ci sono segnalazioni critiche):

| Azione | Quando | Endpoint | Permesso |
|---|---|---|---|
| Rerun step | lotto ERRORE | `POST /vendite/pipeline/run/` | `genera_fatture_lotti` |
| Avanza step | non in esecuzione, non EMESSA | `POST /vendite/pipeline/run/` | `genera_fatture_lotti` |
| Rendi definitive | EMESSA | `POST /vendite/fatturazione/lotti/<id>/numera/` | `numera_fatture_lotti` |
| Ristampa documenti | DEFINITIVA | `POST /vendite/fatturazione/lotti/<id>/ristampa/` | (lettura) |
| Reset a bozza | pre-fiscale | `POST /vendite/lotti/<id>/reset-draft/` | `reset_lotto_draft` |
| Reset singola fattura | fattura DRAFT | `POST /vendite/lotti/<id>/fatture/<fid>/reset-draft/` | `reset_lotto_fattura_draft` |

Più le letture: testata + step corrente, tab Fatture, Task-run, Segnalazioni,
anteprima/archivio PDF per fattura.

### 2.3 Il batch notturno e le due corsie

Un solo command `run_fatturazione_batch --modalita {immediata|differita}`, thin
caller del core condiviso `esegui_giro_fatturazione` (stessa implementazione
dell'endpoint `run/`, invariante «mai due implementazioni»).

| Corsia | tipo_lotto | flag commessa | Si ferma a | Cadenza (deploy) |
|---|---|---|---|---|
| **immediata** | GIORNALIERO | `fatturazione_immediata = true` | **DEFINITIVA** (numera da sola) | timer ogni **2 min** |
| **differita** | MASSIVO | `fatturazione_immediata = false` | **EMESSA** | timer **1° del mese 02:00** |

- `_MODALITA` in `fatturazione_driver_service.py:42-45`.
- ⚠️ **I timer del batch NON sono versionati nel repo**: esistono solo come
  esempio nella play-book (`docs/it/dev/backend/play-book-operativo-backend.md`
  §15). Nel repo ci sono solo i systemd dei **drainer**: `coda-lavori` (ogni
  minuto, **abilitato**) e `coda-stampa` (ogni 2 min, **scritto ma non abilitato**,
  attende i GRANT del ruolo batch). Vedi §6.

---

## 3. Come nasce un lotto — il vincolo che governa il design

**Chiave del perimetro-lotto = `(emittente, tipo_doc_fiscale, utility) + competenza`.**

- La discovery `fn_list_emittibili_lane` raggruppa le attività candidate per
  **terna** `(emittente, tipo_doc_fiscale, utility)`, competenza **cumulativa**
  `≤ M` (`docs/it/dbzero/vendite/funzioni/fn_list_emittibili_lane.md`). Il driver
  crea **un lotto per terna** (`fatturazione_driver_service.py:150-167`).
- **Il cliente (billing account) NON è un asse della discovery**: diventa la
  chiave di raggruppamento della **testata fattura dentro** il lotto (una fattura
  per cliente dentro il lotto — `fatture_righe_service.py:_build_group_key`).
- **MA** `fn_get_or_create_lotto` identifica il lotto anche per
  **billing_account_id** (`fn_get_or_create_lotto.md:11,74-112`): passando un BA
  al runner **nasce un lotto per singolo cliente**. È il gancio per l'emissione
  mirata.
- Il runner `run_lotto_pipeline` accetta già `billing_account_id`, `utility_id`,
  `emittente_soggetto_ruolo_id`, `tipo_doc_fiscale_id`, `competenza_mese`
  (`views.py:68-82`) — ma **NON** `commessa_id`. La commessa **non è** un asse di
  segregazione del lotto.
- L'emissione `fn_emit_attivita_fatturabili_da_commessa` è invece **per-commessa**
  (`p_commessa_id, p_only_approved, p_dry_run`), ma è solo lo step di pull dentro
  la pipeline: la generazione fattura resta a livello lotto.

**Cardinalità commessa**: una commessa = **un solo** `(billing_account, utility,
emittente)` (`commesse.billing_account_id` NOT NULL). Quindi "una commessa" mappa
**deterministicamente** su un cliente/utility.

---

## 4. I gap rispetto all'obiettivo

1. Da UI si può emettere **solo "tutto il mese"**: manca il filtro/selezione
   mirata.
2. La granularità nativa di lotto è la **terna**, non il cliente né la commessa —
   però il cliente è raggiungibile via `billing_account_id` sul runner (§3).
3. **"Singola commessa in senso stretto" o "attività scelte" non hanno un asse**:
   richiederebbero un lotto che contiene solo quelle AF (nuovo lavoro DB). Fuori
   perimetro per la decisione presa (vedi §5).
4. Da UI **non si arriva alla fattura numerata "adesso"**: il verbo è cablato su
   differita → EMESSA. L'istantaneo-fino-a-numerata esiste solo via flag
   `fatturazione_immediata` + timer immediata (2 min), non come azione.

---

## 5. Design stabilito (decisioni Tid, 2026-07-26)

### 5.0 Chiarimento di modello: la commessa NON si «avanza» alla fatturazione

Equivoco ricorrente, da fissare: **non esiste** (né serve) un'azione «porta la
commessa in fatturazione». La commessa è un **contenitore da cui si pesca**, non
un flusso da spingere avanti:

1. si **approvano le sue righe** (verbo *Approva* → `stato_approvazione =
   APPROVATA`) → diventano *emettibili*;
2. il **giro le pesca** (*Fattura adesso*, oppure il batch schedulato): la
   discovery `fn_list_emittibili_lane` cerca righe `APPROVATA + NON_EMESSA`.

Gli stati propri della commessa (`chiudi`/`riapri`/`annulla`, da
`fn_available_actions_commessa`) sono il suo **ciclo di vita** e non hanno
relazione con l'avanzamento verso la fattura. Per questo il drawer commessa non
espone — e non deve esporre — un verbo «fattura».

**Dove vive quindi ogni azione** (card della Lente Competenza):

| Card del funnel | Verbo | Permesso |
|---|---|---|
| `Da approvare` | **Approva** | `approva_attivita_commessa` |
| `Da emettere` | **Fattura adesso** (+ qui vanno i **filtri di emissione mirata**) | `genera_fatture_lotti` |
| `Emesse non fatturate` | **Rendi definitive** (numera) | `numera_fatture_lotti` |

> ℹ️ I pulsanti sono gated su permesso **e** su readonly d'area: un operatore
> senza l'azione di processo vede i numeri ma **non** il verbo (comportamento
> corretto, ma fonte di confusione diagnostica: «il pulsante non c'è» ≠ «la
> funzione non esiste»).

### 5.1 Competenza = generazione mirata (perimetro cliente/utility/emittente)

> La granularità **finale decisa** è il **documento sorgente** (§5.1-bis): questo
> paragrafo descrive il perimetro *già supportato oggi dal DB* (fino al cliente),
> che resta la base su cui l'asse-documento si innesta.

- Alla card **"Da emettere"** si aggiungono **filtri di emissione**: utility,
  **cliente (BA)**, emittente. Riuso dei parametri **già esistenti** sul runner
  (`billing_account_id`/`utility_id`/`emittente`) + identità lotto-per-BA di
  `fn_get_or_create_lotto`. Un cliente = **1 fattura**; filtri larghi = **N**.
- **"Fatturare una commessa" = scorciatoia UI**: selezionata la commessa, la si
  **risolve al suo cliente** (una commessa = un BA) e si lancia il giro
  BA-scoped. **Nessun nuovo asse DB.**
- ⚠️ **Semantica onesta**: il giro per-BA fattura **tutto l'emittibile** di quel
  cliente per il perimetro — che **non è solo «cliente + periodo»**, ma
  **cliente + utility + emittente + tipo_doc_fiscale + competenza ≤ M + corsia**
  (immediata/differita mai mescolate). Può quindi includere **altre commesse
  dello stesso cliente**, e attività nate da **documenti sorgente diversi**
  (es. un preventivo *e* un contratto). Cioè "fatturi il cliente", non un
  documento specifico.

### 5.1-bis La commessa NON è il documento (accertamento 2026-07-26)

Fatto verificato che **smonta l'assunto** «per isolare un preventivo basta
selezionare la sua commessa»:

- La commessa è **multi-sorgente per progetto**: modello `ROOT + N COLLEGATO`
  ([brief chiuso 2026-06-09](../work-done/brief-db-commesse-multi-sorgente.md)).
  L'indice `uq_commesse_sorgenti_commessa_root` è **parziale su `ROOT`** → una
  sola sorgente primaria ma **N contributori** ammessi.
- `fn_get_or_create_commessa` riusa la commessa su chiave **(BA, utility,
  tipo_commessa, policy_fatturazione, fatturazione_immediata, emittente,
  competenza_dal/al)**: un preventivo e un contratto che condividono quel
  perimetro finiscono **nella stessa commessa**.
- Corollario: **selezionare una commessa non isola il documento**. La commessa
  aggrega per *perimetro commerciale*, non per documento d'origine.
- Nota fine: `tipo_doc_fiscale_id` sta **sulla riga** (`commesse_attivita`), non
  sulla testata: righe della stessa commessa con tipo doc diverso finiscono in
  **lotti diversi**.

**Scala di granularità reale**:

| Livello | Cosa isola | Stato |
|---|---|---|
| terna (emittente, tipo_doc, utility) + competenza | il giro del mese | ✅ attuale "Fattura adesso" |
| **+ cliente (BA)** | tutto l'emittibile del cliente nel perimetro | ✅ già supportato dal DB, **da esporre** |
| + commessa | **non** il documento (multi-sorgente) | ⛔ nuovo asse DB — non risolve il caso d'uso |
| **+ documento sorgente** | esattamente le righe di quel preventivo/contratto | ⛔ nuovo asse DB — **il livello che isola davvero** |

La traccia del documento d'origine **esiste già sulla riga**
(`commesse_attivita.sorgente_tipo_id` + `sorgente_uid`): il dato per un filtro
per-sorgente c'è; manca **solo** renderlo un asse di discovery/lotto. Scelta
**decisa (Tid 2026-07-26): si va al livello documento sorgente** → brief DB
dedicato, §8 punto 1.

### 5.2 Lotti = gestione avanzamento (già coperto)

**Conferma di posizionamento (Tid, 2026-07-27)**: la gestione degli stati del
lotto — incluso il passaggio **EMESSA → DEFINITIVA (numerazione)** — vive **nei
Lotti**. Il `LottoDrawer` fa già tutto l'avanzamento (§2.2): **non serve
costruirlo**. Unico stato non gestibile da lì: **INVIATA/SDI**, deliberatamente
fuori perimetro.

#### «Rendi definitive» sta in due posti — ed è voluto

| Dove | Ambito | Endpoint |
|---|---|---|
| Competenza | tutti i lotti EMESSA del **mese** (chiusura del mese) | `POST /vendite/fatturazione/numera/` |
| Lotti (drawer) | **quel** lotto | `POST /vendite/fatturazione/lotti/<id>/numera/` |

Non è duplicazione: due ambiti (perimetro vs singolo), stesso core sotto.

#### Rifinitura necessaria per il flusso mirato: l'aggancio al lotto

Dopo un'emissione mirata l'operatore ottiene un lotto in `EMESSA` e deve
raggiungerlo per numerarlo. Cercarlo a mano nell'elenco è UX povera.

✅ **Il dato c'è già**: l'esito del giro espone il `lotto_id` per ogni terna
lavorata (`fatturazione_driver_service.py`, chiave `"lotto_id"` nell'array
`esiti`). Serve quindi solo un **aggancio diretto FE** — al termine
dell'emissione, un «vai al lotto» che apre il drawer giusto. Nessuna
infrastruttura nuova, **solo frontend**.

#### Rifinitura opzionale

Esporre i verbi di avanzamento **anche sulla riga della lista** lotti (oggi solo
dentro il drawer) e/o una colonna di **stato-step** più leggibile.

### 5.3 `fatturazione_immediata`: instradamento ≠ azione manuale

#### Stato attuale (verificato 2026-07-26)

Il flag esiste come **colonna reale solo su `vendite.preventivi`**. Ordini,
contratti, DDT e consumi **non hanno la colonna**: le rispettive
`fn_list_*_da_pushare` restituiscono `FALSE` **hardcoded** (es.
`fn_list_ordini_da_pushare`, riga `FALSE,` nella SELECT list). Il *contratto* è
simmetrico (tutte le fn espongono il campo nella `RETURNS TABLE`), ma il *dato*
no: **solo un preventivo può essere "immediato"**.

Il flag propaga alla commessa ed è **parte della chiave di dedup** di
`fn_get_or_create_commessa` (BA, utility, tipo_commessa, policy_fatturazione,
**fatturazione_immediata**, emittente, competenza_dal/al).

#### I due nastri

| Flag | Corsia | tipo_lotto | Arriva a | Cadenza |
|---|---|---|---|---|
| `true` | immediata | GIORNALIERO | **DEFINITIVA** (numera da sola) | ogni 2 min |
| `false` | differita | MASSIVO | **EMESSA** | mensile (1° del mese) |

#### Perché il flag NON può essere la leva del "fattura questo adesso"

Idea valutata (Tid) e **scartata**: *«modifico il flag sulla singola sorgente e
fatturo solo quella»*. Tre ostacoli, tutti verificati:

1. **Il flag è nell'identità della commessa**, non è un attributo aggiornabile:
   cambiarlo dopo il push non sposta le righe già pushate.
2. **Un documento è legato a una sola commessa per sempre**: `commesse_sorgenti`
   ha `UNIQUE` **globale** su `(sorgente_tipo_id, sorgente_uid)` — ri-pushare
   verso una commessa "immediata" diversa darebbe `E_COMMESSA_ROOT_CONFLITTO`.
3. **Non isolerebbe comunque il documento**: si sposterebbe l'**intera commessa**,
   che è multi-sorgente (§5.1-bis).

#### La divisione dei compiti (decisa)

| Serve a | Strumento | Quando si usa |
|---|---|---|
| «questo va **sempre** fatturato subito» | **flag** `fatturazione_immediata` | **prima** del push: alla creazione/accettazione del documento |
| «fattura **questo**, adesso» | **selezione per documento sorgente** | in qualsiasi momento, anche a lavoro già in commessa |

Sono due concetti distinti e **non vanno sovrapposti**: il flag è
*instradamento automatico* (proprietà del contratto commerciale, decisa a
monte), la selezione è un *atto dell'operatore* (puntuale). Il caso «cambio idea
dopo» è coperto **interamente** dalla selezione per documento: nessun intervento
sul modello della commessa.

#### Decisione: simmetria del flag

Il flag va **esteso a tutte le sorgenti** (ordini, contratti, DDT, consumi):
colonna reale + `fn_list_*_da_pushare` che leggono il valore invece della
costante `FALSE`. Chiude un'asimmetria del modello e rende sensato sia
l'instradamento sia l'eventuale filtro «a fatturazione immediata» in UI.
Confluisce nel brief DB ([[feedback_simmetria_modello_no_meta_scope]]).

> ✅ **Rettifica 2026-07-27 — decisa da Tid: i consumi sono ESCLUSI** (decisione
> D-6 del brief). Un consumo è una lettura, non un accordo commerciale: la corsia
> appartiene al contratto che lo governa, e un flag lì creerebbe due luoghi dove
> decidere la stessa cosa. La costante `FALSE` in `fn_list_consumi_da_pushare`
> resta, commentata come scelta di dominio. **Perimetro definitivo della
> simmetria: ordini, contratti, DDT.**
>
> ⚠️ **Accoppiamento rilevato**: su `fn_list_preventivi_da_pushare` il flag fa
> doppio lavoro (`prezzo_bloccato = COALESCE(fatturazione_immediata, false)`),
> mentre sulle altre sorgenti quello slot è una costante indipendente. Si estende
> **solo** la semantica di instradamento (brief, fatto F11 e garanzia G18).

### 5.4 Fino a EMESSA (gate fiscale I-7)

- L'emissione mirata da UI si **ferma a EMESSA**, coerente con la separazione
  generare↔numerare (permessi distinti). La numerazione resta il verbo
  «Rendi definitive». **Nessun "fattura e numera adesso"** da UI (scartato per
  non indebolire il punto di controllo fiscale).

---

### 5.5 Design UI del cockpit: liste differenziate per stadio

Decisione Tid (2026-07-27), dopo analisi del comportamento attuale.

#### Com'è oggi

Qualunque card si clicchi, il drill-down mostra **sempre la stessa tabella**:
elenco **commesse** (`Commessa · Cliente · N. attività · Valore · Fatturato ·
Data`), cambia solo il filtro per stadio.

Conseguenza: la lista parla di *commesse* mentre l'azione cambia a ogni stadio.
Su `Da emettere` l'operatore vuole fatturare un documento, ma trova una commessa
→ la apre → nel drawer trova i **segmenti** e i pulsanti **Approva**, che in
quello stadio non servono più (difetto D1, §6-bis).

#### Come sarà: ogni card scende sull'unità del proprio verbo

| Card | Drill-down su | Verbo |
|---|---|---|
| `Da approvare` | **commesse** (invariato) | Approva |
| `Da emettere` | **gruppi fatturabili** (§5.5.1) | Fattura |
| `Fatturate` | **fatture / lotti** | Rendi definitive |

**Scambio accettato**: si perde uniformità (tre tabelle invece di una), si
guadagna pertinenza (colonne e pulsanti sempre coerenti con l'azione). Valutato
accettabile: l'utente si abitua, e ogni card ha comunque un verbo diverso.

> Nota: l'obiezione «il numero della card non corrisponde alle righe della
> lista» **non è introdotta** da questo design — esiste già oggi (card conta
> *attività*, lista mostra *commesse*). Il design semmai la rende esplicita.

#### 5.5.1 L'unità di `Da emettere`: il **gruppo fatturabile**

Non è «il documento», perché **non tutte le righe hanno un documento**:

| Origine riga | Documento sorgente |
|---|---|
| Preventivi / Ordini / Contratti / DDT | ✅ (`PREV:` `ORD:` `CTR:` `DDT:`) |
| Consumi | ⚠️ sì tecnicamente (`CONS:<uid>`), ma è una lettura di consumo, non un documento sfogliabile |
| **Oneri** (porta oneri) | ⛔ **SOURCELESS per progetto** (`sorgente_* = NULL`, segment `MAN:<commessa>:<n>`) |

**Il rischio concreto**: raggruppando solo per documento, gli oneri —
**conteggiati** nel numero della card — **non comparirebbero in nessun gruppo**
e nessuna azione mirata li raggiungerebbe. Lavoro invisibile e non azionabile
(sarebbe recuperato solo dal giro schedulato, che non filtra per sorgente).

**Definizione adottata** — un *gruppo fatturabile* è:

- un **documento sorgente** (caso normale), **oppure**
- le **righe manuali/oneri di una commessa** (raggruppate per commessa: è il
  loro unico contenitore naturale).

```text
Card «Da emettere» (29 attività)
 ├─ PRV-0012              Rossi    5 righe   1.000 €   [Fattura]
 ├─ CTR-0007              Rossi    3 righe     500 €   [Fattura]
 ├─ ORD-0033              Bianchi  8 righe   2.300 €   [Fattura]
 └─ Oneri · commessa #42  Rossi    1 riga      500 €   [Fattura]
```

Conseguenza sul filtro di emissione: non «solo per documento», ma **per
documento *oppure* per righe manuali di una commessa** — una variante in più
nello stesso meccanismo, non un meccanismo nuovo (→ requisito del brief DB).

#### 5.5.2 Colonna «N. attività» e riga di totali

- **Colonna `N. attività` per riga**: ✅ **già il pattern in uso** (la lista
  commesse attuale ce l'ha), va solo portata sulle liste nuove. Il suo valore
  non è la riconciliazione col totale di card, ma dire all'operatore **il peso
  di ciò che sta per fatturare** *prima* di agire.
- **Riga di totali sulla lista** (`7 documenti · 29 attività · 12.500 €`):
  **rifinitura raccomandata, voce separata dal blocco principale**. È la vera
  riconciliazione con la card (nessuno somma righe su più pagine) e rende
  evidente quando un filtro di lista sta mostrando un sottoinsieme. Richiede che
  il BE esponga gli aggregati insieme alla pagina: piccolo, ma non gratis → se
  complica, si fa dopo.

---

## 6. Punti aperti — da verificare col team DB prima di implementare

1. ~~**Coesistenza lotto anticipato-per-cliente vs lotto notturno di terna.**~~
   ✅ **CHIUSO 2026-07-27 — nessun conflitto.** `vendite.fatturazione_lotti` ha
   UNIQUE **solo** su `codice` (da sequenza) e `lock_batch_id` (`uuidv7()`):
   nessun vincolo sulla combinazione dimensionale. `fn_get_or_create_lotto` fa
   «get» solo se riceve `p_lotto_id` o `p_lock_batch_id`, che il driver non passa
   mai → il CASO 3 **crea sempre un lotto nuovo**. Un lotto BA-scoped e uno
   BA-NULL sullo stesso perimetro **coesistono**.
   ⚠️ Il rischio vero è a valle e non era stato visto:
   `fn_select_attivita_fatturabili` **non ha nozione di sorgente**, quindi un
   giro mirato rastrellerebbe le AF residue di altri gruppi. Dettaglio e
   contromisura nel brief DB, fatto F8 e garanzia G12.
2. **Deploy riproducibile del batch**: versionare i timer systemd
   `immediata`/`differita` nel repo (oggi solo in play-book) e **abilitare
   `coda-stampa`** dopo i GRANT del ruolo batch. Indipendente da questa slice ma
   collegato: senza drainer stampa abilitato, le fatture numerate non producono
   PDF.

---

## 6-bis. Difetti rilevati nel cockpit (da correggere)

Emersi durante l'analisi, verificati sul codice, **indipendenti** dalla slice di
emissione mirata: si possono correggere subito e separatamente.

| # | Difetto | Evidenza | Effetto |
|---|---|---|---|
| **D1** | Pulsanti **Approva** visibili anche quando non c'è nulla da approvare | `CommessaGestioneDrawer.vue`: il blocco è `v-if="canApprova"` (**solo permesso**); i bottoni sono poi `:disabled` sui contatori | Su commessa già `PRONTA_FATTURAZIONE` i verbi restano a video disabilitati: rumore. **Fix**: aggiungere `total_non_approvate > 0` alla visibilità |
| **D2** | Verbo **«Rendi definitive» sulla card sbagliata** | Il bottone è su `EMESSA_NON_FATTURATA` (`v-if card.nAttivita > 0`), ma numera **i lotti EMESSA del mese**, cioè fatture già create → stadio `FATTURATA` con `stato_fattura = EMESSA` | Quando il mese è tutto fatturato la card va a **0** e **il pulsante sparisce proprio quando serve numerare**; viceversa appare quando non c'è nulla da numerare. Non bloccante (resta la numerazione per-lotto dal drawer) ma il verbo di massa è inaffidabile |
| **D3** | `EMESSA_NON_FATTURATA` **non è un passaggio del percorso** | Nel giro, pull (crea AF) e generazione righe fattura avvengono nello **stesso step DRAFT** → le attività passano da `Da emettere` direttamente a `Fatturate` | Quello stadio raccoglie **residui/anomalie** (AF sospese, posticipate, o rimaste indietro per errore), non lavoro in transito. Va **letto e presentato** come tale — ed è la causa a monte di D2 |

> ⚠️ D2 e D3 sono **dedotti dal codice, non osservati sui dati**: le query di
> verifica girano fuori dal contesto operatore (viste `security_invoker` + RLS)
> e tornano vuote. Conferma a schermo consigliata prima di intervenire.

---

## 7. Incongruenze documentazione rilevate (verificate sul codice)

Tre residui **STALE grave**, tutti riconducibili al refactor rotte `/v1/` e alla
rimozione del sottosistema «lotto-attività» (changeset `20260227-16`):

| # | File | Cosa dice (errato) | Realtà |
|---|---|---|---|
| 1 | `guide/fatturazione.md:58` | endpoint `/api/vendite/run-lotto-pipeline/`, `/run-commesse-push/` | `/api/v1/vendite/pipeline/run/`, `/commesse/push/run/` |
| 2 | `guide/fatturazione.md:305-333` | ER con `ATTIVITA_FATTURABILI_LOTTI` + `lotto_attivita_id` | sottosistema **rimosso** (colonna droppata) |
| 3 | `guide/gestione-commesse.md:294-319` | `fn_emit_attivita_fatturabili_da_commessa` con `p_lotto_attivita_id` | firma reale `(p_commessa_id, p_only_approved, p_dry_run)` |

Le altre verifiche (task `pull_attivita_da_commessa_default`, 7 funzioni DB
citate, batch notturno/corsie, assenza di `pr_run_lotto_pipeline` nelle guide)
sono risultate **coerenti** col codice. `api.md` e `cruscotti-fatturazione.md`
sono allineati.

> **Stato correzioni**: incongruenze #1–#3 corrette contestualmente a questa
> analisi (2026-07-26).

---

## 8. Perimetro implementazione (quando si parte — NON in questa slice)

Ordine proposto. I punti 1-2 sono **DB e vanno per primi**: BE/FE attendono
([[feedback_be_fe_attende_prerequisiti_db]]).

1. **[DB, prerequisito]** asse **documento sorgente** lungo la catena +
   decisione sulla collisione identità lotto → brief
   [brief-db-emissione-fattura-per-documento-sorgente.md](brief-db-emissione-fattura-per-documento-sorgente.md).
2. **[DB]** **simmetria del flag** `fatturazione_immediata`: colonna su
   ordini/contratti/DDT/consumi + `fn_list_*_da_pushare` che leggono il valore
   reale invece della costante `FALSE` (§5.3).
3. **[BE]** endpoint di emissione mirata: perimetro `billing_account_id`,
   `utility_id`, `emittente` (già accettati dal runner) **+ documento sorgente**
   (dalla firma che il DB consegnerà). Scope RLS invariato.
4. **[FE Competenza]** **liste differenziate per stadio** (§5.5): il drill-down
   di `Da emettere` diventa la lista dei **gruppi fatturabili** (documento
   sorgente **oppure** oneri-di-commessa), con colonna **N. attività** per riga
   e il verbo **Fattura** sulla riga. Filtri di perimetro (utility / cliente /
   emittente / «solo a fatturazione immediata»).
4-bis. **[FE]** **aggancio diretto al lotto** creato dall'emissione mirata
   («vai al lotto» → apre il `LottoDrawer` per numerare): il `lotto_id` è già
   nell'esito del giro, serve solo il collegamento (§5.2).
4-ter. **[FE/BE, rifinitura]** **riga di totali** sulle liste del drill-down
   (`N gruppi · M attività · X €`) — riconciliazione immediata con la card;
   richiede gli aggregati dal BE insieme alla pagina (§5.5.2). Voce separata:
   se complica, si fa dopo.
4-quater. **[FE, indipendente]** correzione dei **3 difetti del cockpit**
   (§6-bis): D1 pulsanti Approva, D2 verbo «Rendi definitive» sulla card
   corretta, D3 presentazione di `Emesse non fatturate` come residui.
5. **[FE documenti]** esporre il flag `fatturazione_immediata` in creazione/
   accettazione dei documenti, ora che è simmetrico (§5.3).
6. **[FE Lotti]** (opzionale) verbi di avanzamento in lista + colonna stato-step.
7. **[Deploy]** versionare i timer batch + abilitare coda-stampa (§6.2).

I punti 3-6 sono **riuso/esposizione** di capacità esistenti; la sostanza nuova
è tutta nei punti 1-2.
