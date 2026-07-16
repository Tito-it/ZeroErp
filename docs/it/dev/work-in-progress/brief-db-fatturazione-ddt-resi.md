# Brief DB — DDT e resi: fatturazione corretta e visibile nelle lenti

> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-16 · **Owner**: Tid
> **Stato**: ☐ DA REALIZZARE
> **Origine**: analisi 2026-07-16 con Tid. Le due lenti a monte (Situazione aperta, Backlog)
> sono state disegnate prima che esistessero DDT e resi e non li conoscono. Nell'analisi sono
> emersi **due bug di fatturazione a monte** che le dashboard non possono vedere: mostrerebbero
> la doppia fatturazione come transito legittimo. Si chiudono insieme — stessa funzione, stesso
> apply.
> **Design-of-record**: [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md)
> §6-quater, decisioni **DL-19..26**.
> **Non si tocca la Lente 1 (Competenza)**: parte dalla commessa ed è sorgente-agnostica — il
> DDT che pusha ci entra da solo. Decisione Tid.
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]) → **breaking
> secchi**, nessuna fase di compatibilità, nessun doppio binario, guard restrittivi da subito.
> Numeri temporaneamente sbagliati **non sono un criterio di progetto** (decisione Tid).

---

## 0. Il rilievo di radice, in una frase

`config.tipi_reso.riapre_residuo` è un flag **logistico**: dice se la merce torna indietro per
sempre o se verrà rispedita. Oggi decide anche cosa succede ai **soldi**. Sono due domande
diverse, e da questa sovrapposizione discendono i bug del §1.

La domanda che governa i soldi è un'altra — **«quella merce l'avevamo già fatturata?»** — ed è
un **fatto** già scritto nel DB, non una scelta di nessuno. Oggi nessun oggetto lo guarda.

## 1. I quattro rilievi

### 1a. La ri-consegna fattura una seconda volta

Ordine 10 pz, `fatturazione_trigger = CONSEGNATO`. DDT₁ 10 pz consegnato → push → **fattura
10**. Reso 3 pz `RESO_PER_RICONSEGNA` → conferma → riapre il residuo (parziale: nessun flip).
Riparo e ri-spedisco: `fn_genera_ddt_riconsegna` crea DDT₂ **col suo `ordini_righe_fulfillment`**
→ DDT₂ è a tutti gli effetti pushabile → consegnato → push → **fattura altri 3**.

**Totale fatturato: 13 pz su un ordine da 10**, senza nessuna nota di credito — perché il reso
*per ri-consegna*, per costruzione, non alimenta la coda accrediti.

La logistica è corretta (residuo 10 − 10 + 3 = 3, DDT₂ evade, ordine EVASO). È la fatturazione
a contare due volte, perché è per riga-DDT e le righe DDT sono append-only fra DDT₁ e DDT₂.

**L'asimmetria che lo prova**: la reso-awareness del 2026-07-13 è stata applicata a
`fn_ordine_ha_residuo_evasione` v2 e a `trgfn_ordini_ful_guard_consistenza` v2 — cioè ai
consumatori **logistici** — ma **non** a `fn_list_ddt_da_pushare`, il consumatore **di
billing**. Al push nessuno chiama l'helper.

### 1b. Nota di credito su merce mai fatturata

`vw_resi_da_accreditare` filtra `stato = CONFERMATO AND tipi_reso.riapre_residuo = false`.
**Non verifica che la merce sia mai stata fatturata.**

Con `trigger = CONSEGNATO` e un reso **totale a credito** prima che il batch giri: il flip
`CONSEGNATO → RESO` toglie il DDT dall'eleggibilità → quella merce **non viene mai fatturata**
→ ma sta in coda accrediti, e la futura NC accrediterebbe merce che il cliente non ha mai
pagato. Con `trigger = SPEDITO` lo stesso reso è invece corretto (il push era già avvenuto a
SPEDITO). **La correttezza dipende dal trigger e dal tempismo del batch, non dai fatti.**

### 1c. Bug orfano del push DDT

`fn_list_ddt_da_pushare`, ramo order-backed:

```sql
AND sdd.codice_interno = src.src_fatturazione_trigger   -- uguaglianza STRETTA
```

Un DDT con `trigger = SPEDITO` che passa a `CONSEGNATO` prima che il batch giri **non è più
eleggibile: non verrà mai fatturato, e nulla lo segnala.**

È lo stesso bug corretto sugli **ordini** il 2026-07-10 — il commento vivo in
`fn_list_ordini_da_pushare` lo dice: *«l'eleggibilita' push NON dipende piu' dallo stato di
spedizione ... Esclusi solo DRAFT/ANNULLATO ... e FATTURATO»*. Sul DDT non è stato replicato.
Che sia un'asimmetria e non una scelta lo prova il ramo **standalone** della stessa funzione,
che usa già la logica giusta: `sdd.codice_interno IN ('SPEDITO','CONSEGNATO')`.

### 1d. Il buco cieco delle lenti (e un falso positivo già vivo)

**Buco cieco.** Ordine con `trigger = CONSEGNATO`: quando il DDT ha evaso tutte le righe
l'ordine passa a **EVASO** → `fase = CHIUSO` → **esce dalla Situazione aperta**. Ma il DDT è
ancora SPEDITO, non ha pushato, in commessa non c'è nulla → **la Lente 1 non lo vede**. E il
DDT non è in nessuna union. **Quel valore, che diventerà fattura, non è in nessuna delle tre
viste.**

**Falso positivo, già vivo oggi.** [vw_dash_fatturazione_ordini](../../dbzero/vendite/views/vw_dash_fatturazione_ordini.md)
**non conosce affatto `fatturazione_trigger`** → marca `PUSH_NON_ESEGUITO` (🟠 RECUPERABILE,
azione *«Esegui il push in commessa»*) su ordini che non pusheranno **mai**, perché
`fn_list_ordini_da_pushare` filtra `fatturazione_trigger = 'CONFERMATO'`. **Azione impossibile
suggerita all'utente.** Precede il DDT (bastava un billing account con
`fatturazione_ordini = CONSEGNATO`) ma ora diventa la norma.

## 2. Il principio (DL-26, Tid 2026-07-16)

> **Si fattura la merce che il cliente tiene in mano alla fine.**

Invariante per riga: `fatturato − accreditato = merce tenuta dal cliente`.

Il fatto *"già fatturata?"* non decide **se** correggere — va corretto sempre — decide solo
**come**: se la merce non è ancora impegnata in fatturazione si **toglie** prima del push; se
lo è, si **accredita**.

Le quattro combinazioni, con 10 pz consegnati e 3 resi:

| | Merce **non** fatturata | Merce **già** fatturata |
|---|---|---|
| **A credito** | non fatturarla → 7. *Oggi*: coda dice "accredita 3" su merce mai pagata ❌ | fattura 10, accredita 3 → 7 ✅ (unico caso già corretto) |
| **Per ri-consegna** | fattura 7 + 3 alla ri-spedizione → 10. *Oggi*: 10 + 3 = **13** ❌ | ha già pagato 10, la ri-consegna non rifattura → 10. *Oggi*: **13** ❌ |

## 3. Cosa serve — il motore (NON come)

I pezzi 3b/3c/3d sono **tre facce della stessa regola**, non alternative. Verificate le sei
combinazioni reali (incluse quelle di reso totale col flip a RESO): con tutti e tre tornano
tutte; togliendone uno se ne rompe almeno una.

### 3a. La regola di eleggibilità — fonte unica (**farlo per primo**)

*«Il push è dovuto per questa riga DDT?»* ha **due consumatori**: la fn di push e il resolver
DDT delle dashboard (§4a). Deve avere **una fonte sola** condivisa, non due copie che
divergono ([[feedback_regola_del_2_estrai_bb]]). Precedente in casa:
`fn_available_actions_ddt` già riusa `fn_list_ddt_da_pushare` come predicato — ma **per riga**,
inservibile su una vista di dashboard che ne valuta migliaia. Serve una forma **set-based**;
quale, lo scegliete voi.

È il primo step perché tutto il resto ci si appoggia.

### 3b. Prima della fattura, **sottrai**

Quando una riga DDT va in fatturazione, la quantità va ridotta di **tutta la merce tornata
indietro** da resi CONFERMATI su quella riga DDT, **di qualunque tipo**. Se si azzera, la riga
non pusha.

⚠️ **L'helper esistente `fn_ordine_riga_qta_riconsegna` NON è riusabile tal quale**: conta solo
i resi con `riapre_residuo = true` (nasce per la logistica) ed è aggregato per
`ordine_riga_id`. Qui serve la somma per `ddt_riga_id`, **tutti i tipi**. È il rilievo del §0
un livello più in basso: un filtro logistico dentro una domanda economica.

**Il confine**: la sottrazione è possibile solo finché la merce non è **già impegnata in
fatturazione** (esiste attività EMESSA per il `segment_key` di quella riga DDT). Da lì in poi
la correzione è un accredito (§3c), non una sottrazione.

### 3c. Dopo la fattura, **accredita** (la coda guarda i fatti)

`vw_resi_da_accreditare` deve smettere di chiedere *"che tipo di reso è?"* e chiedere *"questa
merce è già impegnata in fatturazione?"*. Nuova popolazione: righe reso CONFERMATE la cui merce
ha un'attività EMESSA, **qualunque tipo di reso**. Chi non ce l'ha **esce** dalla coda (chiude
1b). Breaking secco: la forma vecchia sparisce.

La coda deve **distinguere due popolazioni** (serve a §3d, al backlog §4d e alla slice NC):

| Popolazione | Quando | Natura |
|---|---|---|
| NC **dovuta** | tipo *a credito*: la merce non torna più | obbligo — è lavoro arretrato |
| NC **facoltativa** | tipo *per ri-consegna*: la merce tornerà fuori | opzione — vedi §5 |

### 3d. La ri-consegna rifattura solo se la merce non è coperta

Una riga di un DDT di ri-consegna fattura **solo se** la merce originale non è coperta da una
fattura viva: **se non era stata fatturata**, oppure **se è stata accreditata**.

Oggi la nota di credito non esiste → la seconda condizione è sempre falsa → la regola
operativa da costruire ora è: **la ri-consegna non fattura se la merce originale era già
impegnata in fatturazione**. Quando la slice NC arriverà si aggiunge *«…o è stata accreditata»*
senza rework ([[feedback_concentrico_no_yagni]]).

Come esprimere *"questa riga DDT non fattura"* è vostro: una colonna esplicita sulla riga DDT
(ispezionabile, ma è stato nuovo) oppure un predicato dentro l'eleggibilità (§3a) che risale il
ponte `resi_righe_riconsegne` (nessuno stato nuovo, ma richiede la risalita). Purché sia una
fonte sola.

### 3e. Fix orfano push DDT (§1c)

L'eleggibilità order-backed deve valere **dallo stato-trigger in poi**, non solo **a** quello
stato — allineandosi a quanto già fatto sugli ordini il 2026-07-10 e al ramo standalone della
stessa funzione. `RESO`/`ANNULLATO` restano fuori (verificare: con §3b un DDT flippato a RESO
ha comunque quantità azzerata, quindi l'esclusione è ridondante — ma va **confermata**, non
dedotta).

## 4. Cosa serve — le lenti (NON come)

### 4a. Resolver DDT — sesta area della union (DL-21)

Nuovo resolver `vw_dash_fatturazione_ddt`, stessa forma dei cinque gemelli, unito in
`vw_dash_fatturazione_documenti`. Da lì **entrambe** le lenti lo prendono da sole: il serbatoio
filtra `fase <> CHIUSO`, il backlog filtra `classe <> FISIOLOGICO`. Il FE è già fail-visible
sulle aree extra (le accoda, non dà 400).

Punti di attenzione emersi dall'analisi:

- **Valore**: il DDT **non ha importi in testata**. Le righe da evasione possono avere
  `prezzo_unitario` **NULL** ed ereditarlo dalla riga ordine → serve la stessa
  `COALESCE(ddt_righe.prezzo_unitario, ordini_righe.prezzo_unitario)` che fa
  `fn_list_ddt_da_pushare`. ⚠️ **`vw_ddt_righe_iva_base` NON è riusabile**: filtra
  `prezzo_unitario IS NOT NULL` → perderebbe proprio quelle righe.
- **`data_riferimento` = `ddt.data`**. Non esiste una data di spedizione/consegna reale
  (`data_ora_consegna_prev` è *prevista*). Coerente con DL-17.
- **`motivo_fermo` trigger-aware** — deve distinguere *"in viaggio"* da *"in ritardo"*, e il
  predicato *"il push è dovuto?"* **non va ricopiato**: è §3a.

  | Situazione | Motivo | Classe |
  |---|---|---|
  | DRAFT | `DOC_BOZZA` (esistente) | 🟢 FISIOLOGICO |
  | stato **prima** del trigger | `IN_TRANSITO` (**nuovo**) | 🟢 FISIOLOGICO |
  | stato **dal trigger in poi**, non pushato | `PUSH_NON_ESEGUITO` (esistente) | 🟠 RECUPERABILE |
  | idem, push parziale | `PUSH_PARZIALE` (esistente) | 🟠 RECUPERABILE |

### 4b. Ordini trigger-aware (DL-20)

Il resolver ordini deve conoscere `fatturazione_trigger`: con `trigger ∈ {SPEDITO, CONSEGNATO}`
non è l'ordine a pushare → **nuovo motivo `IN_ATTESA_DDT`, classe FISIOLOGICO**.

Effetto: l'ordine **resta nel serbatoio** (giusto — è aperto e pre-commessa) e **sparisce dal
backlog** (giusto — non c'è niente da fare su di lui). Nessun caso speciale nel FE: la regola
di classe DL-6/DL-7 fa tutto da sola.

### 4c. Ordine al residuo nel serbatoio (DL-23)

**Problema**: ordine 1.000 €, trigger CONSEGNATO, metà spedita. L'ordine è PARZIALMENTE_EVASO →
nel serbatoio con valore **pieno** 1.000 €; il DDT ci starebbe con 500 € → le due card dicono
1.500 € per un valore che diventerà fattura di 1.000. **I 500 già spediti contati due volte.**

**Decisione Tid**: nel serbatoio l'ordine porta il **valore ancora da spedire**
(`ordinato − evaso`), non il valore pieno. Card sommabili, staffetta ordine→DDT pulita: quando
spedisco tutto l'ordine va a zero e sparisce, il DDT prende in carico i 1.000, e in ogni
istante la somma fa 1.000. Chiude anche il buco cieco del §1d.

- ⚠️ È il residuo **da spedire** (via `ordini_righe_fulfillment`), **non** il "non transitato":
  per un ordine trigger CONSEGNATO il transitato è sempre 0 e non aiuta.
- ⚠️ **La formula esiste già ed è reso-aware**: `fn_ordine_ha_residuo_evasione` v2 +
  `fn_ordine_riga_qta_riconsegna` (`quantita − Σ qta_evasa + Σ qta_riconsegna`). **Riusarla,
  non riscriverla.**
- ❓ **Da confermare, non da dedurre**: un ordine con `trigger = CONFERMATO` può generare DDT?
  Se non può, per lui residuo ≡ totale e la sua card non cambia. Se può, cambia anche per lui.
- Accettato: l'area Ordini diventa l'unica con misura **netta**, le altre restano lorde.

### 4d. Ramo resi sul Backlog (DL-24)

**I resi NON entrano in `vw_dash_fatturazione_documenti`**: quella union è il funnel
pre-commessa, e `config.sorgenti.RESO_VENDITA` (id 15) è **`REVERSE_FLOW`**, non
`PUSH_COMMESSA` — la migration `20260714-07` lo motiva esplicitamente. Entrano **solo nel
Backlog**, con un ramo dedicato:

| Popolazione | Fonte | Motivo (nuovo) | Classe |
|---|---|---|---|
| Riga reso per ri-consegna, copertura incompleta | `vw_resi_da_riconsegnare` | `RICONSEGNA_NON_ESEGUITA` — azione *«Genera il DDT di ri-consegna»* | 🟠 RECUPERABILE |
| Riga reso la cui NC è **dovuta** | `vw_resi_da_accreditare` (forma **§3c**) | `NC_DOVUTA` | 🟢 FISIOLOGICO **oggi** |

- `RICONSEGNA_NON_ESEGUITA` è 🟠 a pieno titolo: l'azione esiste (`fn_genera_ddt_riconsegna`) e
  la sua **mancata esecuzione blocca la fatturazione** (il residuo dell'ordine resta riaperto
  per sempre).
- `NC_DOVUTA` è 🟢 finché il ramo NC non esiste — stessa forma di `CANONE_NON_GENERATO`. Con la
  slice NC diventa 🟠 cambiando **una riga di seed**, nessun rework.
- ⚠️ Le NC **facoltative** (§3c/§5) **non** sono arretrato: sono un'opzione dell'operatore →
  **fuori dal backlog**.
- **Misura a conteggi** (i resi non hanno importi): `valore_fermo` NULL — mai 0 — e
  `unita_ferme` = righe. Precedente DL-11 (Offerte/Contratti).
- ❓ **Grana, da confermare**: il backlog è per documento, ma `tipo_reso` è **per riga** → un
  reso misto contribuisce a entrambi i motivi. Raccomandazione: **una riga backlog per
  (reso × motivo)**.

### 4e. Seed `config.motivi_fermo` — quattro nuovi

| `codice_interno` | classe | azione |
|---|---|---|
| `IN_ATTESA_DDT` | FISIOLOGICO | — (fattura il DDT, non l'ordine) |
| `IN_TRANSITO` | FISIOLOGICO | — (merce in viaggio, push non ancora dovuto) |
| `RICONSEGNA_NON_ESEGUITA` | RECUPERABILE | Genera il DDT di ri-consegna |
| `NC_DOVUTA` | FISIOLOGICO | — (ramo NC non ancora costruito) |

## 5. La scelta umana — dove vive (DL-26, Tid)

La scelta *«emetto la nota di credito?»* esiste **in una sola casella** delle quattro (§2):
merce **già fatturata** + reso **per ri-consegna**. Altrove la decidono i fatti.

**È una scelta sola, non due**: accreditare e rifatturare sono la stessa decisione vista dai due
lati — se emetti l'NC il cliente non ha più pagato quella merce e la ri-consegna **deve**
rifatturare; se non la emetti la fattura è in piedi e la ri-consegna **non deve**. All'utente si
chiede una cosa sola; il resto si deriva. Il conto torna in entrambi i casi: la scelta cambia le
carte, non i soldi.

**Non è un campo da congelare alla creazione del reso**: la decisione può arrivare dopo («passa
del tempo prima della nuova spedizione e il cliente la richiede» — Tid). È un'**azione sulla
coda accrediti**, esercitabile **fino alla ri-spedizione**: da lì in poi quella merce è
sistemata, e un eventuale credito successivo è un reso nuovo.

**In questa slice non c'è nulla da costruire** per la scelta (l'NC non esiste): serve solo che
il modello non la impedisca — cioè la coda distingue dovuta/facoltativa (§3c) e §3d legge un
fatto che oggi è sempre falso.

## 6. Cosa NON serve (deciso, per chiudere le domande)

- **DL-22 — fase DDT invariata.** `CONSEGNATO` e `RESO` restano `fase = CHIUSO`. Conseguenza
  voluta: un DDT **dovuto e non pushato** compare nel **Backlog** e **non** nel serbatoio —
  corretto per costruzione (non sta aspettando: è in ritardo).
- **DL-25 — `area <> 'COMMESSE'` resta com'è.** Con i resi fuori dalla union (§4d) non è più
  una blacklist da manutenere: è una frase sola e stabile, *«escludi il punto di arrivo»*. La
  commessa non è un'eccezione da ricordare, è il traguardo. Filtrare per
  `config.sorgenti.scope` sarebbe lavoro a comportamento invariato: il criterio resta
  disponibile nel DB se un giorno servisse.
- **Lente 1 (Competenza)**: invariata.

## 7. Fuori perimetro

- **Emissione della nota di credito** (slice NC): qui solo la coda che la alimenta, resa
  veritiera.
- **Valorizzazione economica dei resi**: i resi non hanno prezzi (asimmetria voluta dalla
  slice); l'importo si ricava da `ddt_righe.prezzo_unitario` (COALESCE con la riga ordine). È
  della slice NC.
- Movimenti di magazzino.

## 8. Cosa comunicare indietro a BE/FE

- La forma scelta per *"questa riga DDT non fattura"* (§3d): se è una colonna, il BE la espone.
- La nuova forma di `vw_resi_da_accreditare` (colonne + popolazione + distinguo
  dovuta/facoltativa): il BE ha già `GET /vendite/resi/da-accreditare/` e il FE ha la coda a
  tab → vanno adeguati. **Breaking secco**, nessuna compat.
- **Due aree nuove** (`DDT`, `RESI`): il FE le accoda da solo (fail-visible), ma servono label
  i18n e la rotta *apri documento* in `vendite/dashboardAree.js`.
- Il **ramo resi ha misura a conteggi** (`valore_fermo` NULL) → card come Offerte/Contratti.
- **Quattro motivi nuovi** → i18n (`dash_comune`).
- La **card Ordini del serbatoio cambia significato**: da "valore dell'aperto" a "valore ancora
  da spedire" (§4c) → etichetta e guida da rivedere.
- Eventuali nuovi codici errore.

## 9. Avanzamento

| # | Step | Stato |
|---|---|---|
| 1 | Regola di eleggibilità a **fonte unica**, set-based (§3a) — primo, ci si appoggia il resto | ☐ |
| 2 | Push reso-aware: sottrai la merce tornata (tutti i tipi, per `ddt_riga_id`, fino all'attività EMESSA) (§3b) | ☐ |
| 3 | `vw_resi_da_accreditare` sui fatti + distinguo dovuta/facoltativa (§3c, breaking) | ☐ |
| 4 | La ri-consegna non fattura se la merce era già impegnata in fatturazione (§3d) | ☐ |
| 5 | Fix orfano push DDT: eleggibilità dallo stato-trigger in poi (§3e) | ☐ |
| 6 | Resolver `vw_dash_fatturazione_ddt` + union (§4a) | ☐ |
| 7 | Resolver ordini trigger-aware → `IN_ATTESA_DDT` (§4b) | ☐ |
| 8 | Ordine al residuo da spedire nel serbatoio (§4c, riusare la formula esistente) | ☐ |
| 9 | Ramo resi sul backlog (§4d) — dopo lo step 3 | ☐ |
| 10 | Seed 4 motivi (§4e) | ☐ |
| 11 | pgTAP: le sei combinazioni del §2 + caso orfano + flip a RESO + buco cieco chiuso + falso positivo ordini sparito + somma serbatoio coerente + resi solo nel backlog | ☐ |
| 12 | Apply dev + comunicazione a BE/FE (§8) | ☐ |

> **Due domande aperte per Tid** (marcate ❓ nel testo): §4c — un ordine `trigger = CONFERMATO`
> può generare DDT? · §4d — grana del backlog resi: una riga per (reso × motivo)?
