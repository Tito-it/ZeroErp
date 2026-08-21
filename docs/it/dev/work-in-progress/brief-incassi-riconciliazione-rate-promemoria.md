# Cantiere contabili di pagamento — posting e abbinamento rata ↔ incasso

> ⭐ **Dal 2026-08-09 questo non è più un promemoria: è il brief del cantiere
> «contabili di pagamento».** Nato il 02-08 come elenco di cose lasciate
> indietro, dichiarava di sé *«non è un piano e non contiene decisioni»*. Ora le
> decisioni ci sono, e stanno in **§2-bis**.
>
> ℹ️ **Il nome del file resta quello**, benché ora sia stretto: ci puntano la
> guida [gestione-dei-pagamenti.md](/guide/gestione-dei-pagamenti) e
> [fatturazione-roadmap.md](fatturazione-roadmap.md), e un rename romperebbe
> due link per guadagnare un titolo più bello.
>
> **Cos'è.** Il cantiere che porta l'area `pagamenti` da modello disegnato a
> modello in esercizio: **posting** (riga contabile → movimento) e
> **abbinamento** (incasso → singola rata). Contiene la misura del terreno, le
> decisioni prese col loro perché, e quelle ancora aperte.
>
> **Scritto il 2026-08-02**, alla chiusura del cantiere satelliti della fattura,
> dove queste voci erano elencate come «fuori scope» in tre documenti diversi.
> Ordine di lavorazione deciso da Tid: **1) incassi/riconciliazione → 2) blocco
> `2.4 DatiPagamento` → 3) SDI**.
>
> ⭐ **Rimisurato il 2026-08-09**, alla ripresa del lavoro. Tre righe della
> misura originale non reggevano, ed è emerso che **il pezzo mancante è due, non
> uno**: prima ancora dell'aggancio alla rata manca il **posting** riga contabile
> → movimento, con tre buchi logici sullo stesso confine (§1-bis). Le sezioni
> superate sono **marcate, non cancellate**.
>
> 🔴 **Nota di nome, da leggere prima di progettare.** In questo schema
> «**contabile**» è la *contabile bancaria*: il documento che raccoglie N importi
> arrivati insieme e li prepara. **Non è contabilità.** Lo schema `contabilita`
> (piano dei conti, partita doppia) esiste ma è **vuoto, 0 tabelle**, ed è
> tutt'altro mestiere. I due nomi si somigliano e chi li confonde progetta la
> cosa sbagliata.
>
> **Fonti**: `brief-db-generazione-scadenze-fattura.md` §6 e §7 (chiuso),
> `dbzero/vendite/manual/fatture_scadenze.md`, `guide/gestione-dei-pagamenti.md`.
>
> ---
>
> ⭐ **Dal 2026-08-21 il PIANO DB sta altrove**:
> [brief-db-posting-e-abbinamento-rata.md](brief-db-posting-e-abbinamento-rata.md).
> **Questo documento resta la sede delle decisioni di dominio**; là stanno i
> passi, le misure aggiornate e le domande aperte prima dello sviluppo.
> ⚠️ **Divisione del lavoro, per non far divergere le due sedi**: una decisione
> di dominio si aggiorna **qui**; una misura del terreno o un passo si aggiorna
> **là**. Mai il contrario.
>
> 🔴 **E quel documento corregge tre cose che qui sono scritte al presente e non
> lo sono più** (rimisurate il 2026-08-21):
>
> | Dove | Cosa non regge più |
> | --- | --- |
> | §1-bis, §6 | `vendite.fn_sync_pagamento_fondo_fattura` — «il guscio vuoto che sembra il posting» — **non esiste più**: ritirata con la Fase E del cantiere fondi il 2026-08-15 |
> | §1-bis **B-2** | «postare una riga non abbinata produrrebbe una violazione NOT NULL (23502)» è **falso**: il trigger di mirror ha **già** il guard e solleva un `P0001`. 🔴 Il difetto vero è un altro — solleva `E_GENERICO`, come **tutte e quattro** le funzioni di `pagamenti` |
> | §7 | La «metà fondi» della slice 1 **è fatta** (Fasi A/B/C/E/F applicate il 15-16/08), e con essa cade il riquadro rosso sulla sua scadenza. ⭐ **La dipendenza si è invertita**: ora è la **Fase D** del cantiere fondi ad aspettare il processo rimborsi di `pagamenti` (§4-bis **D8 b**) |
>
> 🔴 E aggiunge **cinque difetti nuovi** che questo brief non conosce, tre dei
> quali **bloccano la slice 1** — il più grave: `pagamenti.centri_riscossione`
> **non può contenere più di due righe**, quindi il passo 3 di §2-bis D9-d-1
> («aggiungere banca, poste, cassa») oggi non è eseguibile. Vedi §1.4 di là.

---

## 1. Il pezzo mancante, in una frase

**Un incasso è agganciato alla fattura, non alla rata.**

Verificato sul DB il 2026-08-02, **riconfermato il 2026-08-09**: nell'intero
database **non esiste alcuna colonna `scadenza_id`**.
`pagamenti.vendite_movimenti` porta `fattura_id` e `billing_account_id`, e si
ferma lì.

Da questo singolo fatto discendono **tutte** le voci aperte qui sotto. Non sono
lavori indipendenti che per caso si somigliano: sono conseguenze dello stesso
anello mancante, ed è la ragione per cui vanno riprese insieme e in quest'ordine.

⭐ Dal 2026-08-09 l'anello mancante si è rivelato **doppio**: vedi §1-bis.

---

## 1-bis. 🔴 Il pezzo mancante è **due**, non uno (rimisurazione 2026-08-09)

Il promemoria del 02-08 dice «manca l'aggancio alla rata». È vero, e **non è
tutto**: manca anche il gradino prima.

> **Nessuna funzione, in tutto il database, scrive `pagamenti.vendite_movimenti`.**

Misurato cercando `INSERT INTO pagamenti.vendite_movimenti` nel corpo di ogni
funzione di ogni schema: **zero risultati**. Il **posting** — il passaggio
«riga contabile postabile → movimento effettivo» descritto dalla
[guida](/guide/gestione-dei-pagamenti) e disegnato nella lookup degli stati —
è **documentato ma non implementato**.

Ne segue che oggi `pagamenti.fn_get_saldo_fattura` restituisce, per costruzione,
**sempre `totale_a_pagare`**: sottrae movimenti che nessuno crea.

### ~~⚠️ Attenzione a una funzione il cui nome dice il contrario~~

> ✅ **CHIUSA il 2026-08-15, verificata il 2026-08-21**: la funzione è stata
> **ritirata** (`DROP`) con la coda della Fase E del cantiere fondi, e **non
> esiste più** nel database. Il paragrafo resta perché spiega *perché* la guida
> descriveva il posting come se esistesse — non perché ci sia ancora qualcosa da
> fare.

Cercando il posting si incontrava
`vendite.fn_sync_pagamento_fondo_fattura(p_fattura_figlia_id)`, che restituisce
`TABLE(inserted_movimenti, updated_movimenti, annullati_source)`. Nome e colonne
dicono **movimenti**: sembra il pezzo che stiamo cercando.

✅ **Non lo è.** Letto per intero, il corpo è un guscio: delega **tutto** a
`fn_sync_contabili_fondo_fattura` e si limita a rinominare `inserted_righe` →
`inserted_movimenti`. **Non crea nessun movimento**, e **nessuna funzione del
database la chiama**.

🔴 È probabilmente una delle ragioni per cui la guida descrive il posting come se
esistesse. Chi cerca il posting la trova, e si ferma. Segnalata anche in
[brief-db-fondo-fattura-ricalcolo-e-governo.md](brief-db-fondo-fattura-ricalcolo-e-governo.md)
§2, dove si decide se rinominarla o ritirarla (F-4).

### ⚠️ Il buco logico che questo apre, e che è **armato**, non teorico

Il fondo fattura usa i **due** saldi come una bilancia.
`vendite.fn_genera_fondi_fattura_source` calcola:

```text
importo_target = fn_get_saldo_fattura(residuo per MOVIMENTI)
               − fn_get_saldo_fattura_contabili(righe POSTABILI in lavorazione)
```

e genera un fondo quando la differenza è ≠ 0. Il secondo termine è vivo: la
catena `fn_ricalcola_totali_fattura` → `fn_sync_contabili_fondo_fattura` crea
davvero testata e righe contabili. Il primo termine è **inerte**.

Finché una riga resta in `ABBINATA` (`is_postabile = true`) la bilancia sta in
pari. Ma `POSTATA` ha `is_postabile = false` e `is_final = true`: **nel momento
in cui qualcuno porta una riga a POSTATA senza creare il movimento
corrispondente, la riga esce dal secondo termine e non entra nel primo** — la
differenza rimbalza a `totale_a_pagare` e il fondo **si rigenera**.

🔴 **Non è un difetto latente da correggere: è un vincolo su chi scriverà il
posting.** Portare una riga a `POSTATA` e creare il movimento devono essere la
**stessa unità atomica** (regola «una azione = una unità atomica», madre DB —
[api.md §Atomicità](/dev/api) e linee-guida-sql §5b). Oggi non si vede perché
nessuno mette righe in `POSTATA`: il giorno che qualcuno lo farà, si vedrà come
fondi fattura duplicati, e sembrerà un problema di fondi fattura.

#### ⭐ Verificato il 2026-08-15: con un posting **atomico** la bilancia regge da sé

Il conto, fatto sui due termini nel passaggio `ABBINATA → POSTATA`:

```text
prima :  target = totale − 0          − importo    =  totale − importo
dopo  :  target = (totale − importo)  − 0          =  totale − importo
```

I due termini **si scambiano lo stesso importo**. Quindi il rischio B-1 non è
«il posting sposta la bilancia»: è tutto e solo nella **non-atomicità**, che
D3-b risolve per costruzione. Non c'è un secondo lavoro da fare — c'è da **non**
scrivere il posting in due pezzi.

⚠️ **Ma il posting fa un'altra cosa, e va saputa adesso.** La riga contabile che
il fondo fattura crea è `ABBINATA`, cioè **postabile**: il giorno del posting
diventerà un `vendite_movimenti` vero. Ed è **giusto** — la fattura sorgente è
davvero stata saldata, per **trasferimento** su un'altra fattura e non per
cassa. Segue il limite di dominio scritto in §4: *ogni misura di «incassato»
deve escludere i centri non-cassa*. Analisi: [brief-db-fondo-fattura…](brief-db-fondo-fattura-ricalcolo-e-governo.md) §8.2 Fase F.

### Conseguenza sull'ordine dei lavori

L'ordine di Tid (incassi → `2.4 DatiPagamento` → SDI) **non cambia**. Cambia il
contenuto del primo passo: «incassi» non è solo la riconciliazione alla rata, è
**posting + riconciliazione**, e le due si progettano insieme perché la seconda
decide dove il primo scrive.

### ⚠️ Altri due buchi sullo stesso confine (misurati 2026-08-09)

**B-2 — La riga contabile ammette il NULL che il movimento vieta.**

| Colonna | `vendite_contabili_righe` | `vendite_movimenti` |
| --- | --- | --- |
| `fattura_id` | **nullable** | **NOT NULL** |
| `billing_account_id` | **nullable** | **NOT NULL** |

Ed è coerente col dominio: `DA_ABBINARE` significa letteralmente *«l'importo è
arrivato, non so ancora a chi attribuirlo»*, cioè `fattura_id IS NULL`.
L'abbinamento **è** la scrittura di quella FK.

~~Ma il trigger `trgfn_vendite_movimenti_sync_contabile_from_riga` copia i tre
campi dalla riga al movimento: postare una riga non abbinata produrrebbe una
**violazione NOT NULL (23502)**, non un errore di dominio parlante.~~

> 🔴 **Sbagliato, rimisurato il 2026-08-21.** Il trigger **ha già** il guard: se
> la riga non ha `fattura_id` o `billing_account_id` chiama
> `script.fn_log_and_raise_error` e solleva un `P0001` *prima* che la `NOT NULL`
> entri in gioco. La `23502` non si vede mai su quel percorso.
>
> **Il difetto vero è di specie diversa, e peggiore: il codice è `E_GENERICO`** —
> e non solo lì: **tutte e quattro** le funzioni di `pagamenti` sollevano
> `E_GENERICO`, su una quindicina di punti.
>
> ⚠️ Il guard esistente ha però un buco proprio: scatta **solo** se
> `contabile_riga_id IS NOT NULL`. Un movimento scritto senza riga — la colonna è
> nullable — non incontra nessun controllo.

**Il requisito resta, cambiando forma**: il posting deve rifiutare *prima*, con
un codice suo — ma non è «aggiungere un guard che manca», è **dare un nome** a un
rifiuto che già esiste e **bonificare i vicini**. Passi P-6 e P-7 del
[piano DB](brief-db-posting-e-abbinamento-rata.md).

🔴 **E non esiste alcun vincolo che leghi lo stato ai dati.** Oggi si può
scrivere `ABBINATA` con `fattura_id` NULL, o `DA_ABBINARE` con la fattura già
valorizzata: la macchina a stati del catalogo e il contenuto delle colonne sono
due cose slegate. Serve un guard `stato ↔ nullità` — è lo stesso guard che dovrà
reggere l'abbinamento alla **rata**, quindi si scrive **una volta sola**, nella
forma decisa da §2-bis D1.

**B-3 — Lo scope emittente è presidiato in scrittura e scoperto in lettura.**

| Tabella | Guard in scrittura | RLS in lettura |
| --- | --- | --- |
| `vendite_movimenti` | ✅ `trgfn_guard_emittente_scope('fattura','fattura_id')` | ❌ assente |
| `vendite_contabili_righe` | ❌ **nessuno** | ❌ assente |
| `vendite_contabili` | ❌ nessuno (guard ente/centro sì, scope no) | ❌ assente |

Due asimmetrie, non una. Il movimento non si può **creare** fuori scope, ma una
volta creato chiunque lo **legge**; e la riga contabile — che è il vero punto
d'ingresso operativo — può puntare a una fattura di **qualunque** emittente senza
che nessuno lo fermi. Dettaglio e conseguenze in §4.

---

## 2. Stato di partenza, misurato

> 🔴 **La tabella del 02-08 era in tre punti sbagliata** e va letta nella
> versione qui sotto. La causa dell'errore è annotata in §5 perché è una trappola
> ripetibile, non una svista.

### Misura corrente — 2026-08-09

| Cosa | Stato |
| --- | --- |
| Colonna di aggancio rata → incasso | **non esiste** (nessun `scadenza_id` nel DB) |
| Funzione che scrive `vendite_movimenti` | **non esiste** (il posting non è implementato) |
| `vendite.fatture_scadenze` | **2 righe** — 2 fatture su 12, una rata ciascuna |
| Transazionali `pagamenti` (contabili, righe, movimenti, compensazioni, lotti, enti_incasso, sepa_mandati) | **0 righe** |
| Cataloghi `pagamenti` | **seminati** — vedi sotto |
| Schema `contabilita` | **nessuna tabella** |
| RLS su `pagamenti.*` | **assente** su tutte (⚠️ vedi §4) |
| Area funzionale `pagamenti` | **già a catalogo**, `config.aree_funzionali` id 7 |
| Codici errore di dominio pagamenti | **nessuno** (esistono solo gli `E_SCADENZE_*`, lato vendite) |
| App Django `apps/pagamenti/` | stub vuoto (`views.py` = una riga di commento) |
| `frontend/src/pagamenti/` | due `.gitkeep` |

### ⭐ I cataloghi ci sono già, e sono il vocabolario su cui innestarsi

Questa è la correzione che cambia di più il lavoro: il promemoria diceva «le
altre 9 tabelle di `pagamenti`, **tutte a 0 righe**». Le **transazionali** lo
sono; i **cataloghi** no.

| Tabella | Righe | Contenuto |
| --- | ---: | --- |
| `centri_riscossione` | 2 | `FONDI_FATTURA` (`is_fondo_fattura`), `COMPENSAZIONI` (`is_compensazione`) |
| `vendite_contabili_stati` | 5 | BOZZA → IMPORTATA → VALIDATA → CHIUSA / ANNULLATA (`is_final` sulle ultime due) |
| `vendite_contabili_righe_stati` | 7 | IMPORTATA → DA_ABBINARE → **ABBINATA** (`is_postabile`) → SOSPESA / SCARTATA / POSTATA / ~~STORNATA~~ (**ritirata**, §2-bis D9-a) |
| `enti_incasso` | 0 | nessun canale fisico configurato (né banca né PSP) |

🔴 **La macchina a stati dell'abbinamento è già disegnata a catalogo.**
`DA_ABBINARE → ABBINATA → POSTATA`, con `SOSPESA` per il dubbio, è **esattamente**
il vocabolario di una riconciliazione. (`STORNATA` c'era, ed è stata **ritirata**:
§2-bis D9-a.) Non va
inventato un secondo insieme di stati: andava deciso **a quale livello vive
l'abbinamento** — deciso il 2026-08-09, **sulla riga contabile e fino alla
rata**: vedi §2-bis D1.

⚠️ **La riga più importante resta l'ultima del promemoria originale**: fino al
2026-08-02 le rate non esistevano affatto. Il piano rate è stato acceso allora, e
al 09-08 conta **2 righe in tutto**. Qualunque disegno verrà validato su terreno
praticamente vuoto — vedi §5, ultimo punto.

**Cosa esiste già** e non va riscritto: `fn_get_saldo_fattura` (residuo, con
l'avvertenza di §1-bis), `fn_get_saldo_fattura_contabili` (in lavorazione),
`fn_get_or_create_vendite_contabile` (punto d'ingresso unico per la testata), la
testata `vendite_contabili` con righe e stati, i centri di riscossione, gli enti
di incasso, i mandati SEPA e le compensazioni.

#### ~~Misura originale del 2026-08-02~~ — SUPERATA, tenuta per storia

| Cosa | Stato dichiarato al 2026-08-02 |
| --- | --- |
| Colonna di aggancio rata → incasso | **non esiste** (nessun `scadenza_id` nel DB) — ✅ ancora vero |
| `pagamenti.vendite_movimenti` | tabella presente, **0 righe** — ✅ ancora vero |
| Le altre 9 tabelle di `pagamenti` | presenti, **tutte a 0 righe** — ❌ **falso** per i 3 cataloghi |
| Schema `contabilita` | **nessuna tabella** — ✅ ancora vero |
| `vendite.fatture_scadenze` | **si popola da oggi**: il generatore è entrato con la Fase 4 — ✅ vero, ma a una settimana di distanza sono **2 righe** |

---

## 2-bis. ⭐ Le decisioni prese (2026-08-09, Tid)

Tre decisioni portanti. Sono qui col loro **perché** e con **ciò che le
ribalterebbe**: un brief che scrive solo l'esito costringe chi arriva dopo a
riaprire il ragionamento da capo per capire se vale ancora.

---

### D1 ✅ L'abbinamento vive **sulla riga contabile**, e arriva **alla rata**

**Cosa si fa.** Una colonna `scadenza_id` **nullable** su
`pagamenti.vendite_contabili_righe`, con rispecchiamento su
`pagamenti.vendite_movimenti` tramite il trigger di sincronizzazione che **già
esiste** (`trgfn_vendite_movimenti_sync_contabile_from_riga`, che oggi copia
`contabile_id`, `fattura_id` e `billing_account_id`).

**Cosa NON si fa.** Nessuna tabella di allocazione N:N.

**Perché.** La domanda del promemoria originale — *«FK singola o tabella
N:N?»* — era mal posta: **la tabella di allocazione esiste già e si chiama
`vendite_contabili_righe`**. È nata per dire «di questo bonifico, questo pezzo va
lì»: la testata è il movimento bancario, le righe sono i pezzi. Un incasso di
1.000 € che copre tre rate diventa tre righe sotto la stessa contabile,
esattamente come oggi diventa tre righe se copre tre fatture.

> **Il modello spezza già. Stiamo solo spezzando più fine.**

Una tabella N:N introdurrebbe **due posti che dicono la stessa cosa** —
l'importo sulla riga e la somma degli importi allocati — e due posti che devono
sempre coincidere prima o poi non coincidono.

⭐ **Il momento in cui si spezza è quello giusto, e non è ovvio.** Quando il
denaro arriva non si sa ancora come spalmarlo: si registra **una riga sola**, in
stato `DA_ABBINARE`. La si spezza dopo, quando si è capito. Ed è innocuo, perché
`DA_ABBINARE` **non è postabile**: nessun movimento esiste ancora, quindi
spezzare, correggere e rispezzare non tocca niente a valle. *La decisione viene
prima della scrittura.*

**Cosa comporta:**

- guard di **quadratura**: Σ delle righe abbinate a una rata ≤ importo della
  rata. ⚠️ Serve in ogni caso: **è un costo del problema, non della scelta**.
  🔴 **Ma il limite superiore è forzabile — vedi il riquadro qui sotto**;
- guard di **coerenza**: `scadenza_id` deve appartenere alla `fattura_id` della
  stessa riga (le due colonne convivono e possono contraddirsi);
- il guard **stato ↔ nullità** di §1-bis B-2 si scrive **qui e una volta sola**:
  è la stessa regola («che cosa deve essere valorizzato in quale stato»).

⚠️ **Da collaudare prima di impegnarsi**: la FK punterebbe a
`vendite.fatture_scadenze`, che **ha la RLS attiva**. Un pgTAP deve verificare
che l'integrità referenziale si comporti allo stesso modo per l'operatore e per
il canale di sistema — non è dato per scontato.

**Cosa la ribalterebbe.** Una regola fiscale o di revisione che imponga *«a un
movimento bancario deve corrispondere un solo incasso registrato»*: allora
spezzare produrrebbe N incassi dove la regola ne vuole uno. **Escluso da Tid il
2026-08-09**, e comunque il modello la violerebbe già oggi, perché spezza già per
fattura.

#### 🔴 D1-bis — Il sovra-incasso esiste, e va **registrabile con forzatura**

> Decisione di Tid, 2026-08-09: *«in un mondo perfetto è così, però capita — nel
> mondo utilities spesso — che un cliente paghi erroneamente importi maggiori.
> Concordo con il controllo, ma dobbiamo permettere una forzatura.»*

**Prima però una precisazione che toglie metà del problema.** Il guard **non
impedisce di incassare**: impedisce di **caricare una rata** con più di quanto
vale. Ricevere i soldi non è mai rifiutato — la riga contabile si crea comunque.

E dato che con D1 **la riga è l'unità di allocazione**, il caso ordinario si
risolve **spezzando, senza forzare niente**:

```text
arrivano 1.200 su una rata da 1.000
  ├── riga 1.000  →  rata            (abbinata, quadra)
  └── riga   200  →  DA_ABBINARE     (o su un'altra rata, o su un'altra fattura)
```

⭐ È la strada **preferibile** quando un'altra destinazione esiste: l'eccedenza
resta denaro identificato e disponibile, invece di sparire dentro una rata che
non la giustifica.

**La forzatura serve quando una destinazione non c'è** — nessuna altra rata,
nessun'altra fattura aperta — e l'operatore vuole comunque dichiarare: *«lo so,
ha pagato di più, registralo così»*.

##### Come dev'essere fatta

| Requisito | Perché |
| --- | --- |
| **Esplicita** | il default resta il rifiuto: si forza dicendolo, mai per silenzio del sistema |
| **Motivata** | un motivo obbligatorio sulla riga. Precedente nello stesso modello: `motivo_sospeso` |
| **Gated** da un'azione di processo | non ogni operatore. ⭐ Sull'area `pagamenti` esiste **già** un'azione — `approva_rimessa` (id 5) — e il progetto ha già il pattern a due tempi in `vendite`: `prezzo_override_manuale` + `approva_prezzo_override`. Da decidere se riusare o aggiungerne una propria (io ne aggiungerei una: la semantica è diversa) |
| **Visibile dopo** | una rata sovra-incassata deve **comparire in un elenco**. Senza, la forzatura diventa il modo di far sparire denaro invece che di registrarlo: è soldi che dobbiamo restituire o applicare altrove |

##### ⚠️ I due estremi si somigliano nella formula, non nella natura

```text
0  ≤  Σ imputato a una rata  ≤  importo della rata
│                                │
│                                └── 🔓 forzabile: lo causa il CLIENTE, ed è un
│                                       fatto del mondo reale
└── 🔒 non forzabile: significa aver restituito più di quanto incassato su
       quella rata. Nessun cliente può provocarlo — è solo un errore di chi opera
```

🔴 **Non rendere simmetrico l'override solo perché la formula è simmetrica.**
Sono due cose diverse travestite da estremi dello stesso intervallo.

##### 🔴 Il fondo fattura **non si genera da solo** su un sovra-incasso

Decisione di Tid, 2026-08-09: *«il calcolo di generazione del fondo fattura per
sovra-incasso non deve essere un automatismo sempre attivo — deve essere
gestito.»*

Con un sovra-incasso `fn_get_saldo_fattura` va **sotto zero**, il che è corretto:
la fattura ha un credito e il residuo è una sottrazione. Il problema è cosa ne fa
l'automatismo esistente.

✅ **Misurato sul corpo della funzione il 2026-08-09.**
`vendite.fn_genera_fondi_fattura_source` ha **un solo filtro sull'importo**:

```text
… AND (saldo − saldo_contabile) <> 0        ← l'unica condizione
```

Nessun limite inferiore. Quindi con un saldo negativo:

| Ramo | Cosa farebbe oggi |
| --- | --- |
| `INSERT` | crea un fondo di **importo negativo**, in stato **`DISPONIBILE`** |
| `UPDATE` | porta un fondo esistente a importo negativo, e lo **lascia** `DISPONIBILE` (`ANNULLATO` scatta **solo** a importo esattamente zero) |

✅ E niente lo ferma a valle: `vendite.fatture_fondi_fattura_source.importo`
**non ha alcun CHECK**. Un fondo negativo `DISPONIBILE` verrebbe poi **assegnato
a una fattura figlia** dal task `applica_fondi_lotto`.

**Cosa si fa quindi:**

- ~~l'automatismo prende un **limite inferiore**: genera un fondo solo per
  `importo_target > 0`, che è il caso per cui è nato (minimo non raggiunto, somma
  da recuperare). Il **verso opposto non è un fondo**: è denaro in eccesso, cioè
  un fatto di natura diversa;~~
- l'eccedenza resta **visibile e in attesa di una persona**: saldo negativo sulla
  fattura + l'elenco delle rate sovra-incassate. La decisione — rimborsare,
  **compensare** (`pagamenti.compensazioni` esiste ed è il candidato naturale),
  applicare a una fattura futura — è un gesto **governato**, non un effetto
  collaterale di un batch notturno.

##### 🔴 Il primo punto era sbagliato — corretto il 2026-08-15 con Tid

> **«Il verso opposto non è un fondo» è falso.** Il verso opposto **è** un fondo,
> ed è metà del meccanismo.

Le due soglie di `anagrafiche.emittenti_fiscali_utilities` non sono «un minimo e
un tetto»: sono i **due capi di una banda che contiene lo zero**. Con l'esempio
reale di Tid (`minimo_soglia_max = +10`, `minimo_soglia_min = −500`):

```text
                −500 €              0              +10 €
    ────────────────┼───────────────┼───────────────┼──────────────
     RIMBORSO       │      F O N D O   F A T T U R A     │  PAGAMENTO
     (credito       │  a credito  ·  a debito            │  ordinario
      troppo grande)│  si riporta sulla fattura dopo     │  del cliente
```

Una fattura fra −500 e 0 **deve** diventare di minimo e riportare avanti un
**credito**: è esattamente a cosa serve il capo inferiore. Un filtro
`importo_target > 0` avrebbe spento quella metà — e il difetto sarebbe stato
invisibile, perché il meccanismo avrebbe continuato a funzionare *nell'altro
verso*.

**Il pericolo vero non era il segno: era la mancata corrispondenza col
documento.** Una fattura da 8 € su cui qualcuno scrive una riga contabile da 40 €
produce un fondo di −32 su un documento che vale +8. Il controllo giusto è:

```text
l'importo non è zero
ha lo stesso segno del totale_a_pagare della fattura sorgente
non lo supera in valore assoluto
```

⚠️ E **non** si scrive come «compreso fra 0 e il totale»: su una sorgente a
credito gli estremi si invertono — la trappola già registrata in §5, che qui si
presenterebbe come **caso ordinario** e non di bordo.

⚠️ Va in un **guard trigger**, non in un CHECK: deve leggere `vendite.fatture`.

Piano completo: [brief-db-fondo-fattura…](brief-db-fondo-fattura-ricalcolo-e-governo.md)
§8.1 F-5 e §8.2 D-3.

##### 🔴 E una seconda scoperta: «soglia non impostata = meccanismo spento» vale solo a metà

| Configurazione | Dovrebbe | Fa oggi |
| --- | --- | --- |
| nessuna delle due | spento | ✅ spento |
| entrambe | attivo sulla banda | ✅ corretto |
| **solo il minimo** | ⛔ errore | 🔴 `soglia_max IS NULL` rende vera la condizione: **ogni** fattura sopra il minimo diventa «di minimo» |

Chi imposta `−500` e dimentica `+10` non ottiene un meccanismo a metà: ottiene
**tutto il fatturato trasformato in fondi riportati**. ✅ **Deciso da Tid il
2026-08-15**: dev'essere un **errore di configurazione**, con un CHECK «entrambe
o nessuna» (passo D-0 dell'altro brief).

~~⚠️ **Una domanda che questa scelta apre e che non chiudo io**: un fondo **già
esistente** il cui target diventa negativo — lo si lascia com'è, o lo si porta ad
`ANNULLATO` come già accade a importo zero?~~

✅ **Chiusa il 2026-08-15** ([brief-db-fondo-fattura…](brief-db-fondo-fattura-ricalcolo-e-governo.md)
§8.1 F-2): **si lascia com'è**. Portarlo ad `ANNULLATO` sarebbe uno stato
cambiato da un pagamento, cioè l'automatismo che scrive che §3-bis ha escluso —
e la coerenza («il fondo non è più recuperabile») la dà la **rilettura al momento
dell'atto** (D-3), non una scrittura anticipata. Il fondo non più giustificato
non viene applicato e compare nell'elenco: nessuno lo cancella al posto di una
persona.

###### 🔴 Quando va fatta: **nella slice 1**, e il motivo è di tempistica

Questa non è una modifica in `pagamenti`: tocca **`vendite`**, ed è **codice
vivo** — entrambi i task, `genera_fondi_source_lotto` e `applica_fondi_lotto`,
sono `attivo = true` nel registry della pipeline di fatturazione.

Oggi però il ramo negativo è irraggiungibile, e ✅ misurando il 2026-08-09 si vede
che è chiuso da **due serrature indipendenti**:

| Serratura | Stato oggi | Chi la apre |
| --- | --- | --- |
| ~~`f.minimo IS TRUE`~~ | **0 fatture a minimo** su 12 (e 0 fondi generati) | ~~una configurazione, in qualunque momento~~ |
| ~~saldo negativo~~ | ~~impossibile: **nessun movimento esiste**~~ | ~~🔴 **la slice 1**, per definizione~~ |

~~🔴 **La slice 1 apre la seconda serratura.**~~ ~~Da quel momento basta la prima —
una fattura a minimo, che è un dato di configurazione — perché un sovra-incasso
generi un fondo negativo `DISPONIBILE` e lo faccia assegnare a una fattura
figlia.~~

##### 🔴 Rimisurato il 2026-08-15: **la tabella qui sopra è sbagliata su entrambe le righe**

**La conclusione operativa non cambia — il limite inferiore va fatto — ma cambia
la scadenza, e in peggio.**

**Seconda riga.** Il fondo non si genera su `saldo`: si genera sulla
**differenza** `saldo − saldo_contabile`, e il **secondo** termine non ha niente
a che vedere coi movimenti. Basta che la somma delle righe contabili
`is_postabile` di una fattura superi il suo residuo perché il target vada sotto
zero, **con zero movimenti nel database**. E niente lo impedisce: il guard di
quadratura è la **slice 2**, non la 1.

> ⭐ Quindi la seconda serratura **non è un vincolo: è l'assenza di scrittori**.
> Oggi l'unica funzione che scrive `vendite_contabili_righe` è
> `fn_sync_contabili_fondo_fattura`, che scrive un importo che per costruzione
> non supera il residuo e che al giro dopo si scorpora da sé. La serratura si
> apre col **primo altro scrittore**: l'import del flusso (D6), una correzione a
> mano, o la slice 1 — quello che arriva prima, e non è detto sia il posting.

**Prima riga.** `minimo` non è «una configurazione»: è **riscritto a ogni
ricalcolo** da `fn_ricalcola_totali_fattura`, confrontando `totale_a_pagare` con
le soglie di `anagrafiche.emittenti_fiscali_utilities`. Si apre **da sola**, al
primo ricalcolo dopo che qualcuno ha valorizzato `minimo_soglia_min` — nessuno
deve accendere niente su una fattura.

**Quindi il limite inferiore resta dentro la slice 1** (è lì che qualcuno mette
le mani sulle righe contabili), ma **la scadenza non è la slice 1**: è il primo
scrittore di righe contabili, chiunque sia. Se un altro lavoro tocca prima quel
terreno, il tampone va con lui.

🔴 **E il limite inferiore da solo non basta**, cosa che il 2026-08-09 non era
stata vista. Togliendo l'`ANNULLATO` automatico a target zero, un fondo non più
giustificato **resta `DISPONIBILE`** e `applica_fondi_lotto` lo assegna comunque
a una figlia. Serve nello stesso lotto di lavoro un **guard all'applicazione**
che rilegga la capienza della sorgente **nell'istante in cui muove il denaro** —
è il passo D-3 del piano: [brief-db-fondo-fattura…](brief-db-fondo-fattura-ricalcolo-e-governo.md) §8.2 Fase A.

ℹ️ Misurato **leggendo** i corpi vivi (doc auto-generata) e la struttura delle
tabelle, non eseguendo SQL.

ℹ️ Regole di lavorazione, trattandosi di una funzione esistente: nuovo changeSet
con numerazione successiva, e **corpo preso dalla doc auto-generata**, mai da un
YAML di migrazione (che è quasi sempre stale).

##### 🔴 Fattura a credito: il cliente può pagare lo stesso, e va registrato

Decisione di Tid, 2026-08-09: se `totale_a_pagare < 0` e il cliente paga
comunque, **la registrazione dev'essere permessa**.

⭐ E il modello la regge già, per una ragione che vale la pena vedere: una fattura
con totale negativo **ha zero rate per progetto** (il generatore non le crea, e
`fatture_scadenze.importo >= 0` aveva già deciso che un documento a credito non
si rateizza).

Quindi **non c'è nessuna rata da sforare**: il pagamento si registra sulla
**fattura**, con `scadenza_id` NULL — una possibilità che D1 ha già ammesso, la
stessa che serve alla coda «da abbinare». Il guard di quadratura per rata non
entra nemmeno in gioco.

##### ⚠️ E qui c'è la trappola: **non aggiungere una quadratura per fattura**

Verrebbe naturale replicare il controllo un livello sopra —
`0 ≤ Σ imputato alla fattura ≤ totale_a_pagare`. **Sarebbe un difetto**, ed è
proprio questo il caso che lo rivela:

```text
totale_a_pagare = −50   →   intervallo [0, −50]   →   VUOTO
                            ogni pagamento rifiutato, sempre
```

🔴 **Un intervallo i cui estremi possono invertirsi non è un guard: è una porta
chiusa che si presenta come un controllo.** Se una quadratura per fattura si
farà, va definita **solo per `totale_a_pagare > 0`**.

⚠️ **Il progetto ha già pagato esattamente questa trappola**, e la nota è a due
click: in [fatture_scadenze](/dbzero/vendite/manual/fatture_scadenze) la query di
controllo quadratura porta il filtro `totale_a_pagare > 0` con l'avvertenza che
*«non è un dettaglio: senza, le fatture a base zero o negativa comparirebbero
come squadrature»*. Stessa causa, stesso rimedio, un livello più in là.

---

### D2 ✅ Lo stato della rata è **derivato**, mai scritto

**Non è stata una scelta libera: è già decisa dai fatti.** Le rate sono
**congelate** oltre DRAFT/EMESSA da un guard sui satelliti della fattura — una
colonna di stato su `fatture_scadenze` non si potrebbe scrivere nemmeno
volendolo.

Quindi: `fn_get_saldo_rata`, gemella di `pagamenti.fn_get_saldo_fattura`, che
risponde per rata come quella risponde per fattura. Nessuna colonna nuova su
`fatture_scadenze`, e la regola generale del progetto («derivare, e
materializzare solo quando il costo di ricalcolo lo impone») resta intatta.

---

### D3 ✅ Il posting: contabile intera, madre DB, e la correzione è **un importo negativo**

**Che cos'è il posting.** Il gesto che trasforma l'intenzione in fatto: la
contabile compilata è un foglio di lavoro — finché non si posta, la fattura
risulta ancora da pagare per intero. Postare fa passare la riga da `ABBINATA` a
`POSTATA` e **fa nascere il movimento**, cioè la cosa che il residuo sottrae.

| | Decisione | Perché |
| --- | --- | --- |
| **a** | **Unità = la testata contabile**, non la singola riga | La contabile **è** il movimento bancario: postata a metà resta un documento per un pezzo fatto e per un pezzo brogliaccio, che nessuno sa più leggere. ⭐ Il caso difficile si risolve da sé: una riga dubbia va in **`SOSPESA`**, che non è postabile — quindi «posta la contabile» significa naturalmente *«registra tutto il pronto, lascia lì il resto»*. Nessun meccanismo nuovo |
| **b** | **Una sola `SELECT fn_...()`** (madre DB), non orchestrazione Python | B-1 pretende che cambio di stato e creazione del movimento siano **inseparabili**. Una funzione sola lo è **per costruzione**; l'orchestrazione lo ottiene solo se qualcuno si ricorda di scriverlo. Fra una garanzia strutturale e una da ricordare si sceglie la prima. Ed è la regola del progetto: operazione di soli dati ⇒ sta nel database |
| **c** | **Ripetizione tecnica = silenzio; seconda azione voluta = messaggio** | L'indice unico impedisce già il doppio movimento: la domanda non è cosa si rompe, è **cosa vede la persona**. Il replay di una richiesta ripetuta è già gestito dal meccanismo generale; un operatore che riclicca «conferma» su una contabile già registrata deve **sentirselo dire**, perché il silenzio direbbe «fatto» a chi sta cercando di cambiare qualcosa e non ha cambiato niente |
| **d** | 🔴 **Lo storno NON esiste come concetto.** Esiste la contabile, e una contabile può avere **importi negativi** | Decisione di Tid, 2026-08-09 — vedi sotto |

#### 🔴 (d) La correzione non è un tipo di documento: è un importo di segno opposto

⚠️ **Questa riga ha sostituito, lo stesso giorno, una versione che introduceva
una «contabile di storno» con un'etichetta sua.** La versione precedente apriva
tre domande — chi porta lo stato `STORNATA`, come si lega lo storno
all'originale, come si impedisce lo storno dello storno — e la terza faceva
intravedere una catena senza fine.

**Quelle tre domande erano un artefatto dell'etichetta, non del problema.** Nel
momento in cui un documento «è di storno», qualcuno può chiedersi che cosa sia lo
storno di uno storno, e nasce una gerarchia che il denaro non ha:

> **Il denaro non ha versi, ha segni.**

Tolta l'etichetta, le tre domande non si semplificano: **smettono di esistere**,
perché non c'è più l'oggetto di cui parlavano. Una correzione è una contabile
normale, con la sua data — quella in cui ci si è accorti — e importi di segno
opposto. Il documento originale non si tocca: resta la fotografia di ciò che fu
deciso quel giorno.

#### ⭐ Ciò che rende sicura la (d) è **un solo controllo, simmetrico**

Non è l'assenza dell'etichetta a mettere al riparo: è la quadratura di D1, letta
con **due estremi** invece di uno.

```text
0  ≤  somma di quanto è imputato a una rata  ≤  importo della rata
```

Un controllo solo, che **non sa niente di storni**: conta soldi su una rata. Il
limite in alto impedisce di incassare più del dovuto; quello in basso impedisce
di correggere più di quanto si è incassato.

⭐ **Qui cade il timore della catena infinita.** Con quel controllo attivo, si può
registrare −100, +100, −100 all'infinito senza che accada nulla di male: la somma
resta sempre dentro i limiti. Una catena lunga è **disordinata, non pericolosa** —
costa righe, non correttezza. Faceva paura solo perché era stata raccontata come
una gerarchia; **come somma, si difende da sé**.

#### ⭐ Due conferme che la forma è quella giusta

**Il modello la ospitava già.** Il `CHECK` sulle righe contabili vieta l'importo
**zero**, non il negativo; i movimenti non hanno vincolo di segno; il residuo,
essendo una somma, torna indietro da solo quando arriva un movimento negativo.
Nessuna macchina nuova.

**E regge un caso che non è una correzione.** Fra qualche slice arriveranno gli
**insoluti**: un addebito SEPA che torna indietro. Economicamente è identico a una
correzione, ma **non è l'errore di nessuno** — è un fatto che arriva dalla banca,
dentro un file, senza che un operatore lo decida. Qui è una riga negativa come le
altre e funziona senza che nessuno abbia previsto il caso. Con l'etichetta si
sarebbe dovuto decidere se un insoluto «è uno storno», e qualunque risposta
avrebbe fatto sembrare l'errore della banca un errore dell'operatore, o
viceversa.

> Una forma che regge due eventi diversi senza doverli distinguere è il segno che
> è la forma giusta.

#### A cosa si rinuncia, e dove potrà stare

Si rinuncia a sapere **perché** un importo è negativo: correzione, rimborso,
insoluto, addebito bancario. **È responsabilità di chi opera** (Tid): i saldi
dicono il valore economico, che è ciò che conta.

Se un giorno servisse classificarlo, **il posto c'è già e non richiede struttura
nuova**: il **centro di riscossione** classifica l'origine, e la riga ha `meta` e
un campo di motivazione. Non si sta chiudendo una porta, si sta solo non
aprendola adesso.

---

### D9 ✅ Il governo degli stati della contabile — transizioni dichiarate, `STORNATA` ritirato, annullamento solo in bozza

Decisioni di Tid del 2026-08-09, conseguenti a D3.

#### a) 🔴 `STORNATA` si ritira

Non esiste più il gesto che ce la portava (D3-d), e **uno stato che nessuno può
raggiungere è una promessa che il modello non mantiene**: chi legge il catalogo
fra un anno progetterebbe pensando che funzioni.

Si ritira col pattern del progetto — **`obsoleto_dal`, non `attivo = false`** —
che toglie la voce dal selezionabile senza rompere eventuali riferimenti. ✅
Verificato il 2026-08-09: **nessuna funzione, vista, tabella, riga di backend o
di frontend nomina `STORNATA` in `pagamenti`**; le quattro funzioni che parlano
di «storno» stanno tutte in `vendite` (resi, commesse, cleanup, ricalcolo
totali) e sono un altro dominio. Il ritiro non tocca niente.

#### b) ⭐ `pagamenti` deve avere le sue transizioni dichiarate

Misurato: **`pagamenti` non ha alcuna tabella di transizioni**, mentre ce l'hanno
DDT, ordini, preventivi, contratti, resi, pratiche, commesse, offerte e documenti
fiscali. Le righe contabili hanno **un elenco di stati e nessuna regola su come
ci si passa**: oggi qualunque salto è ammesso, compreso uscire da uno stato
dichiarato finale.

Va colmato, con la stessa forma già in uso — `(stato_da_id, stato_a_id, attivo,
meta)` — per **entrambe** le macchine: testata e righe.

ℹ️ **Dove metterle**: le transizioni stanno dove stanno gli stati. `config` per i
domini con stati in `config`; `vendite.transizioni_stati_commessa` per quelli con
stati in `vendite`. Gli stati contabili vivono in `pagamenti`, quindi lì vanno le
loro transizioni.

⭐ **Questa è la sede naturale del guard di §1-bis B-2** (stato ↔ nullità): una
transizione dichiarata dice *quando* si può passare, il guard dice *a quali
condizioni sui dati*. Sono due metà della stessa regola e conviene scriverle
insieme.

#### c) ✅ Una contabile non confermata si può **annullare**; una confermata no

Lo stato `ANNULLATA` esiste già sulla testata (`is_final = true`), e con D3-d
prende un significato preciso e stretto:

| Momento | Correzione |
| --- | --- |
| **prima** della conferma | **si annulla** la contabile: è ancora un foglio di lavoro, non ha toccato niente |
| **dopo** la conferma | **non si annulla**: si registra una contabile nuova con importi di segno opposto |

È la linea che divide il brogliaccio dal registro, ed è la stessa che rende
coerente tutto il resto: prima si cancella perché non è successo niente, dopo si
corregge perché è successo.

#### d) ⚠️ Due difetti trovati verificando, da sanare nella slice 1

**D9-d-1 — 🔴 I centri di riscossione non sono seminati: sono stati inseriti a
mano.**

`vendite_contabili.centro_riscossione_id` è già **NOT NULL** — su questo il
modello è a posto. Il problema è il **contenuto**, e a guardarlo bene è più
grande di «manca una riga».

I due centri esistenti sono **entrambi interni** (`FONDI_FATTURA`,
`COMPENSAZIONI`): non c'è un centro per la banca, le poste o la cassa, quindi
**una contabile di incasso reale oggi non è creabile**. Ma la misura di come ci
sono arrivati dice di peggio:

| Evidenza | Cosa significa |
| --- | --- |
| `user_insert = postgres`, `data_insert = 2026-02-17` (entrambe le righe) | inserite **a mano**, non da una migrazione |
| Nessun file in `80_data` nomina `centri_riscossione` | **non esiste né CSV né loader** |

🔴 **Su un database ricostruito da zero — cioè in CI — `centri_riscossione` è
vuota.** Non manca solo la banca: mancano anche i fondi fattura e le
compensazioni, cioè i due centri da cui dipendono `fn_sync_contabili_fondo_fattura`
e l'intero ramo compensazioni.

⚠️ **Ed è invisibile per costruzione.** Tutti e quattro i pgTAP di `pagamenti`
usano il modulo «cerca il centro, se non c'è inserilo»: si fabbricano il dato che
il seed non fornisce, quindi non se ne accorgono. Due dei quattro sono già rossi
in baseline con causa `ERRORE_FIXTURE`, il che rende la cosa ancora più facile da
attribuire ad altro. *È esattamente la trappola «il DB di sviluppo non è un DB
ricostruito da zero»: verificando solo su dev si misura una macchina, non la
riproducibilità.*

#### La soluzione — ~~quattro~~ **cinque** passi, non uno

> 🔴 **Ne manca uno davanti, scoperto il 2026-08-21: il passo 3 oggi non è
> eseguibile.** `uq_centri_riscossione_compensazione` è un UNIQUE **totale** su
> una colonna booleana — il `where: "is_compensazione = true"` fu scritto su un
> `addUniqueConstraint`, che quell'attributo **non ha**, ed è stato ignorato in
> silenzio. Conseguenza: la tabella può contenere **al massimo due righe**, una
> per valore del flag. Sono esattamente le due che ci sono, il che rende il
> vincolo **saturo e indistinguibile da uno rispettato**.
>
> Prima dei quattro passi qui sotto va quindi un **passo 0**: sostituire il
> vincolo con un **indice unico parziale** (`WHERE is_compensazione`) e dargli il
> gemello su `is_fondo_fattura`, che oggi non ha nessuna unicità. Dettaglio e
> lezione in [brief-db-posting-e-abbinamento-rata.md](brief-db-posting-e-abbinamento-rata.md)
> §1.4 C-1; passo **P-1** del piano.
>
> ⚠️ E un **passo 5** in coda: `id` è `GENERATED BY DEFAULT AS IDENTITY`, e un
> loader con id espliciti **non avanza la sequenza**. `pagamenti` non è coperto
> da nessun resync (`20260616-02` copre solo `config`): senza, il primo insert
> automatico collide con la pkey.

Il modello da copiare è a due file di distanza: `vendite_contabili_stati` ha già
CSV + mirror `loadUpdateData` (`runOnChange: true` + `validCheckSums: ANY`).

1. **creare** `80_data/sql/pagamenti/centri_riscossione.csv` — oggi non esiste;
2. ⚠️ **backfillare per prime le due righe già nel DB** (id 37 e 38, con i loro
   valori): un mirror che parte senza di esse le lascia fuori su dev e non le
   crea in CI. È la regola del progetto — *prima si porta nel CSV ciò che c'è
   già, poi si aggiunge*;
3. **aggiungere** i centri reali (banca, poste, cassa) come righe nuove;
4. **creare il loader** `80_data/changelog/...-upsert-pagamenti-centri-riscossione.yaml`
   sul modello di `20260213-04`.

ℹ️ Gli id 37 e 38 sono non sequenziali, assegnati a mano: vanno nel CSV **così
come sono**. Oggi nessuna riga li referenzia (0 contabili), ma il CSV è la sede
della verità e deve descrivere il DB, non correggerlo.

**D9-d-2 — ⚠️ Lo stato della testata è nullable.**

`vendite_contabili.stato_id` ammette **NULL**, e il calcolo del saldo contabile
tratta la testata senza stato come **non finale** (`is_final = false OR NULL`).
Finché lo stato era decorativo era innocuo; da quando **è il cancello fra
brogliaccio e registro** (punto c) è un buco: una contabile senza stato non è né
bozza né confermata, e passa i filtri di entrambe.

**La soluzione:** `NOT NULL` con default `BOZZA` — che è già il default della
funzione di ingresso `fn_get_or_create_vendite_contabile`, quindi si tratta di
far dire alla colonna ciò che il codice fa già. Il backfill è banale: **0 righe**
in tabella.

ℹ️ Conseguenza da non dimenticare nello stesso changeSet: il ramo `OR NULL` di
`fn_get_saldo_fattura_contabili` diventa **codice morto**. Va tolto quando la
colonna diventa obbligatoria, non lasciato lì a raccontare un caso che non può
più accadere.

---

### D5 ✅ Il perimetro dei soldi non attribuiti si deriva **dal conto di incasso**

**Il problema.** Quando 1.000 € arrivano in banca non hanno ancora una fattura, e
il perimetro dell'operatore si risolve **dalla fattura**. Applicare la regola
normale renderebbe la coda «da abbinare» **invisibile a tutti** — non «visibile a
chi non dovrebbe»: invisibile. E una lista vuota sembra una lista di cose finite.
Non è teoria: su questo sistema gli emittenti fiscali sono **due, entrambi
attivi**.

**La regola di dominio che risolve** (Tid, 2026-08-09):

> Un emittente è un'azienda con **partita IVA propria**; due emittenti non
> possono avere la stessa partita IVA; quindi — almeno in Italia — **hanno conti
> correnti diversi**.

Ne segue che **il denaro ha un padrone dal primo istante**: l'ha deciso il
cliente scegliendo su quale conto pagare. Il sistema oggi butta via
quell'informazione e poi si accorge di non averla.

#### ⭐ L'anagrafica c'è già, quasi tutta

Misurato il 2026-08-09 — `anagrafiche.soggetti_ruoli_conti_bancari`:

| Cosa | Stato |
| --- | --- |
| Uso del conto | `INCASSO` · `PAGAMENTO` · `RIMBORSO` · `GENERICO` — **«incasso» è già a vocabolario** (CHECK) |
| Conto predefinito | **unico garantito**: indici unici parziali su `(soggetto_ruolo, uso)` e `(soggetto_ruolo, istanza_utility, uso)` dove `predefinito` |
| Validità nel tempo | `valido_dal` / `valido_al` — si sostituisce un conto senza perdere la storia |
| IBAN | **unico in tutto il sistema** (`uq_conti_bancari_iban`) |
| Risolutore | `script.fn_get_conto_bancario_predefinito(soggetto_ruolo, uso, istanza_utility)` → `vw_conti_bancari_per_ruolo` (con fallback `RUOLO`→`SOGGETTO`) |
| Aggancio all'emittente | `emittenti_fiscali.soggetto_ruolo_id` **NOT NULL** — la catena è chiusa |
| Precedente d'uso | `pagamenti.sepa_mandati.soggetto_ruolo_conto_id` punta già al conto in questo modo |

**La catena emittente → conto di incasso è completa e qualcuno l'ha già
percorsa.**

#### 🔴 Ma a noi serve al contrario, e in quel verso non è garantita

| Verso | Domanda | Garanzia |
| --- | --- | --- |
| azienda → conto | «qual è il conto di incasso di X?» | ✅ **unica** (indice su `predefinito`) |
| **conto → azienda** | «questi soldi su questo conto, di chi sono?» | ❌ **nessuna**: nulla vieta che lo stesso conto con uso `INCASSO` sia legato a due soggetti diversi |

La regola di dominio di Tid è vera nel mondo, **ma il database non la sa**.
Finché quel legame serviva a stampare l'IBAN in fattura, l'ambiguità era un
fastidio. Nel momento in cui ci si appoggia il **perimetro di sicurezza**, una
riga ambigua diventa un varco: due aziende sullo stesso conto e ciascuna vede i
soldi dell'altra, **senza che compaia nessun errore da nessuna parte**.

> ⭐ **Regola generale che vale oltre questo caso:** una verità di dominio su cui
> si appoggia un perimetro di sicurezza deve diventare un **vincolo**, non
> restare un'assunzione. Il costo di scriverla è un indice; il costo di non
> scriverla non si vede finché non è successo.

#### Cosa manca, in tutto

| | Cosa | Natura |
| --- | --- | --- |
| **1** | `enti_incasso` non punta al conto: conosce la **filiale** (`bank_branch_id`), non il conto corrente | struttura — **una colonna**, `soggetto_ruolo_conto_bancario_id`, **obbligatoria** per `tipo = BANCA` come già lo è la filiale |
| **2** | Nessun vincolo «un conto `INCASSO` appartiene a un solo emittente» | **il pezzo importante**: è ciò che regge il perimetro |
| **3** | Nessuno dei 2 emittenti ha oggi un conto `INCASSO` configurato (i 4 legami esistenti sono di altri soggetti) | dato, non difetto: configurazione |

⚠️ **Il rischio della scelta, e come si chiude.** Un ente configurato senza conto
produrrebbe una coda invisibile — cioè **lo stesso difetto di partenza
travestito**. Si chiude rendendo il conto **obbligatorio alla configurazione**:
fallisce dove se ne accorge chi può rimediare, non in esercizio dove non se ne
accorge nessuno.

**Cosa la ribalterebbe.** Che due emittenti incassino sullo stesso conto: il
conto non distinguerebbe più niente. Escluso dalla regola di dominio sopra —
ed è proprio il caso che il vincolo (2) rende **impossibile invece che
improbabile**.

---

## 3. Le attività aperte

### 3.0 🔴 Posting riga contabile → movimento — **nuovo, 2026-08-09**

Aggiunto alla rimisurazione. È il gradino che mancava sotto la 3.1: senza, la
metà «incasso» del modello non produce mai un movimento e il saldo finanziario
resta finto.

✅ **Deciso il 2026-08-09** (§2-bis **D3** e **D9**): unità = **la testata
contabile** (saltando le righe `SOSPESA`), forma = **una sola `SELECT fn_...()`**
madre DB, ripetizione = silenzio sul replay tecnico e messaggio sulla seconda
azione voluta.

E la correzione **non è un documento speciale**: prima della conferma si
**annulla**, dopo si registra una contabile nuova con **importi negativi**. Lo
stato `STORNATA` è **ritirato**. Nessuna domanda residua.

⚠️ **Tre vincoli non negoziabili**, tutti da §1-bis:

1. transizione a `POSTATA` e creazione del movimento nella **stessa
   transazione** (B-1);
2. il posting **rifiuta prima** una riga non abbinata, con un codice suo — non
   lascia sbattere la violazione NOT NULL 23502 (B-2);
3. riga e movimento **non si scrivono nella stessa CTE**. Con la RLS attiva padre
   e figlio nella stessa snapshot non si vedono e il `WITH CHECK` nega
   fail-closed: si spezza in due statement, in `plpgsql`, mai in `sql`.
   Trappola già pagata altrove nel progetto.

### 3.1 🔴 Riconciliazione rata ↔ incasso — è il prerequisito di tutto il resto

L'unico lavoro **strutturale** dell'elenco (insieme alla 3.0, che ne è il
gradino). Le altre tre voci si sbloccano da sole quando questa atterra.

✅ **La forma è decisa** (§2-bis D1 e D2): `scadenza_id` sulla riga contabile,
rispecchiato sul movimento, nessuna tabella N:N, stato della rata derivato.
Restano da definire in fase di scrittura:

- **incasso parziale su una rata** — ammesso per costruzione (la riga può valere
  meno della rata); da definire solo *come si racconta* una rata coperta a metà,
  che è una domanda di lettura, non di modello;
- **eccedenza** — che cosa succede se l'abbinato supera la rata. Il guard di
  quadratura lo **nega**; resta da decidere se l'operatore vede un rifiuto o una
  proposta di spezzare la riga;
- **abbinamento automatico** — vedi **D4** in §4-bis: **fuori dalla prima slice**.

> ~~Le domande originali del 02-08 su questo punto~~ — «FK o N:N?», «derivato o
> materializzato?» — sono **chiuse** in §2-bis: la prima perché la tabella di
> allocazione esisteva già, la seconda perché il congelamento delle rate non
> lasciava alternativa.

### 3.2 ⏸️ Blocco `2.4 DatiPagamento` del payload FatturaPA

**Ora possibile**, perché le rate esistono. Verificato il 02-08 e
**riconfermato il 09-08**: `fn_prepare_sdi_payload` **non nomina mai** né
`DatiPagamento` né le scadenze — il blocco non è generato.

È **completezza fiscale, non un abbellimento**: una fattura elettronica senza
condizioni di pagamento è incompleta. Appartiene al cantiere SDI ma dipende da
qui, ed è la ragione per cui Tid l'ha messo **secondo** e non ultimo.

ℹ️ Nota: questo blocco descrive **come si pagherà**, non se è stato pagato —
quindi in teoria non richiede la 3.1. In pratica conviene farlo dopo, per non
scrivere due volte il lettore delle rate.

⭐ **È anche il punto in cui si dichiara al cliente il riferimento di pagamento**
(§3.6): il blocco che rende completa la fattura elettronica è lo stesso che
renderebbe esatto l'abbinamento automatico (D4). Da tenere presente scrivendolo.

### 3.3 ⏸️ Portale clienti — `GET /api/portale/scadenze/`

Endpoint previsto e mai scritto (al 09-08 `apps/portale/` lo nomina solo in un
commento di `urls.py`/`views.py`, fra i «futuri endpoint MVP»). Senza la 3.1
mostrerebbe **il piano rate e basta**, senza poter dire quali rate siano già
pagate: su un portale rivolto al cliente è un difetto grave, perché la domanda
che il cliente si fa è esattamente quella.

### 3.4 ⏸️ Lista scadenze / scadenzario

Oggi **non esiste** alcuna lista scadenze in `ui.lista_definizione` (riverificato
il 09-08: nessun codice che nomini scadenze, pagamenti, incassi o movimenti), e
**non serve**: il piano rate si vede già nel drawer fattura tramite il building
block `ScadenzeSintesi` / `useScadenzeSintesi`, che mostra `—` finché le rate non
arrivano e si accende da sé.

🔴 **Da non confondere**: «elenco del piano rate» e «scadenzario» sono due cose
diverse. Il primo si può fare adesso e aggiungerebbe poco al drawer. Il secondo —
scaduto / insoluto / da incassare, con solleciti e colorazioni — **richiede la
3.1**, perché senza stato di pagamento ogni sua colonna sarebbe falsa su una
fattura già incassata.

Se e quando la lista si farà, valgono i cinque prerequisiti di
[piano-migrazione-primevue-5.md](piano-migrazione-primevue-5.md), e il primo è
lavoro BE vero: **non esiste una rotta scadenze paginata**.

### 3.5 ⏸️ `sepa_mandati` — pezzo di modello orfano (nuovo, 2026-08-09)

`pagamenti.sepa_mandati` esiste con vincoli, stati (`IN_VALIDAZIONE`/`ATTIVO`/…),
formato UMR, snapshot IBAN e **due indici unici parziali** sul mandato attivo per
`(billing_account, schema)` e `(istanza_utility, schema)`.

Ma: **non è nell'elenco tabelle della guida** `gestione-dei-pagamenti.md` e
**non ha documentazione `manual/`**. È l'unica tabella dello schema in questa
condizione.

Non è un lavoro strutturale — è un **debito documentale** che diventa una
trappola quando qualcuno progetterà l'incasso da addebito diretto SEPA e non
troverà, leggendo la guida, il pezzo che gli serve. Da chiudere prima o insieme
alla 3.0/3.1.

---

### 3.6 💡 Riferimento di pagamento in fattura — **proposta**, non ancora decisa

> Aggiunta il 2026-08-09 su richiesta di Tid, ragionando su D4. **È una
> proposta**: sta qui perché è a cavallo fra due attività (l'abbinamento
> automatico e il blocco `2.4`) e andrebbe persa in entrambe.

#### Il problema che risolve

Un bonifico che arriva porta importo, data, IBAN del pagatore e una **causale a
testo libero**. Da lì si prova a risalire alla fattura, ma gli indizi non valgono
uguale:

| Indizio | Affidabilità |
| --- | --- |
| IBAN del pagatore → **chi è il cliente** | 🟢 certo *se* il conto è in archivio — e `anagrafiche.soggetti_conti_bancari` ne ha già 8 |
| importo uguale a una rata | 🟡 forte ma ambiguo: due rate dello stesso importo si assomigliano, e chi paga due fatture insieme non corrisponde a nessuna |
| causale che nomina il numero fattura | 🟡 buona quando c'è, ma è testo scritto da una persona: «fatt 123», «ft. 0123/2026», «saldo come da accordi» |

⚠️ **L'IBAN risolve il cliente, non la fattura**: dice *di chi* sono i soldi, non
*per cosa*. Restringe a due o tre documenti aperti, non chiude.

🔴 **Si sta lavorando dalla parte sbagliata.** Si può scrivere un motore di
indovinelli sempre più furbo che legge le causali, **oppure mettere sulla fattura
un codice che il cliente riporta nel bonifico** — e allora non c'è più niente da
indovinare.

✅ Verificato il 2026-08-09: **in tutto il sistema non esiste un riferimento di
pagamento da stampare in fattura.** (`vendite_contabili_righe.riferimento_ente`
esiste ma è l'opposto: è il dato che *arriva* dalla banca, non quello che *noi
chiediamo* al cliente di riportare.)

#### La proposta: **RF, lo standard ISO 11649** — non un id inventato

La tentazione è mettere in fattura un numero nostro. Meglio di niente, ma uno
standard esiste già e compra tre cose che un id nudo non ha:

```text
RF 78 12345
│  │  └── il nostro riferimento (fino a 21 caratteri)
│  └───── due cifre di controllo, calcolate (mod 97, come l'IBAN)
└──────── prefisso fisso
```

| Cosa compra | Perché conta |
| --- | --- |
| **Cifra di controllo** | un refuso viene **scartato**, non abbinato per sbaglio a un'altra rata. Verificato: `RF7812345` è valido, `RF1812345` no |
| **Campo strutturato SEPA** | nei flussi bancari torna indietro in un **campo suo**, non annegato nella causale a testo libero |
| **È uno standard** | banche e software contabili del cliente lo trattano già; non chiediamo a nessuno di imparare una nostra convenzione |

#### Che cosa ci mettiamo dentro: **la rata, non la fattura**

Discende da D1. Se il riferimento nomina la **fattura**, resta da indovinare
*quale rata*; se nomina la **rata**, l'abbinamento è totale in un colpo solo:
cliente, fattura, rata e importo atteso.

La forma più semplice è l'**id della rata** (`vendite.fatture_scadenze.id`), che
è già una chiave univoca e immutabile. Esempi reali:

```text
rata id 7       →  RF097
rata id 12345   →  RF7812345
rata id 100248  →  RF93100248
```

⚠️ **E degrada bene**, che è il requisito vero. Un cliente che paga due rate
insieme può citarne una sola: il sistema riconosce comunque cliente e fattura con
certezza, vede che l'importo supera la rata citata e **propone la ripartizione**.
Meglio di niente in ogni caso intermedio — un identificatore che funziona solo
quando tutto è perfetto non serve a nulla.

#### Derivato, non memorizzato

Due funzioni pure, nessuna colonna nuova, nessuna tabella:

- `fn_riferimento_pagamento(scadenza_id)` → la stringa `RF…`;
- `fn_scadenza_da_riferimento(rf)` → l'id, **dopo aver validato la cifra di
  controllo** (senza quella validazione lo standard non serve a niente).

Coerente con la preferenza del progetto: derivare, e materializzare solo se il
costo lo impone.

⚠️ **L'alternativa da valutare**: il riferimento finisce **stampato** su un
documento fiscale e in mano a un cliente. Se un giorno l'algoritmo cambiasse, le
fatture vecchie produrrebbero un codice diverso da quello che il cliente ha in
mano. C'è un precedente per l'altra strada — `fatture.termine_pagamento_snapshot`
congela ciò che è stato usato — e la stessa logica direbbe di congelare anche
questo. Da decidere: il rischio è basso ma non nullo.

ℹ️ **Non c'è un problema di riservatezza**: l'id della rata è progressivo e
lascerebbe intuire i volumi, ma il **numero di fattura** è già progressivo per
legge e già stampato. Non aggiunge nessuna informazione.

#### Dove comparirebbe, e perché l'ordine di Tid lo prepara già

| Dove | Nota |
| --- | --- |
| **PDF della fattura**, accanto a ogni rata del piano | è il posto che il cliente guarda per pagare |
| **Blocco `2.4 DatiPagamento`** della fattura elettronica | ⚠️ il campo esatto va verificato sulle specifiche FatturaPA prima di impegnarsi |
| **Portale clienti** (§3.3) | accanto alla rata da pagare |

⭐ **La sequenza decisa da Tid — incassi → `2.4` → SDI — prepara da sé il terreno
all'abbinamento automatico, senza essere stata pensata per farlo.** Il blocco
`2.4` è esattamente il punto in cui il riferimento viene dichiarato al cliente.
Non è un motivo per cambiare l'ordine: è un motivo per **non affrettare D4**,
perché il pezzo che la rende facile arriva subito dopo.

---

## 3-bis. ⭐ Il punto sul flusso di denaro — tre livelli che non si mescolano

> Principio di chiusura fissato con Tid il 2026-08-09, dopo che il ragionamento
> su sovra-incassi, fondi, rimborsi e automatismi si era attorcigliato. Vale per
> tutto il cantiere e per chiunque tocchi l'area dopo.

**Da dove nasceva il groviglio.** Il fondo fattura è **un numero ricalcolato** che
però **muove denaro** (viene assegnato a una fattura figlia). Le due cose insieme
producono la rincorsa: ogni incasso sposta il numero, ogni spostamento cambia i
conti, e serve un altro automatismo che insegue.

**Il punto è separare tre livelli:**

| | Che cosa | Regola |
| --- | --- | --- |
| **1 · I fatti** | contabili, righe, movimenti: ogni euro entrato o uscito, con la sua destinazione (fattura, rata) o **senza**, se non ce l'ha ancora | si **aggiungono**, non si aggiornano **mai**. Sono la tracciabilità completa |
| **2 · I saldi** | residuo per fattura, residuo per rata, credito del cliente (= entrato senza destinazione) | si **leggono**, non si conservano. Non vanno «aggiornati all'incasso»: sono coerenti per costruzione perché **non esistono finché non li chiedi** |
| **3 · Le decisioni** | rimborsare, portare avanti su una fattura futura, compensare | le prende una **persona**, e ognuna diventa un fatto di livello 1 |

### ⭐ Perché così la rincorsa è **impossibile**, non solo improbabile

Un ciclo richiede che **un automatismo riscriva un numero che un altro rilegge**.
Se l'unica scrittura è l'aggiunta di un fatto e tutto il resto è derivato, non
c'è niente che possa rincorrersi: **un saldo non insegue sé stesso**.

### La regola pratica per queste slice

> **Nessun automatismo tocca il fondo in base agli incassi.** Il fondo esistente
> resta com'è, e la fattura compare in un elenco da guardare.

Un'«attività pre-fatturazione» ha senso — ma **non sana: presenta**. È l'elenco
delle decisioni da prendere prima di fatturare, non un automatismo che aggiusta.

### ⭐ E il rimborso non è da costruire

La guida dice che il movimento rappresenta *«l'incasso **o il rimborso**
definitivo»*: i rimborsi sono **già** nel vocabolario del modello. E dato che con
D3-d la correzione è **una contabile con importi negativi**, un rimborso è la
stessa identica cosa — denaro che esce, registrato come tutto il resto. Nessuna
macchina nuova: è quella che stiamo già facendo.

ℹ️ Il ripensamento del **meccanismo** dei fondi (che un numero ricalcolato muova
denaro da solo) resta un problema vero, ma è un cantiere suo, in `vendite`:
[brief-db-fondo-fattura-ricalcolo-e-governo.md](brief-db-fondo-fattura-ricalcolo-e-governo.md).
Qui ci si ferma a **non farlo peggiorare**.

---

## 4. Limiti di dominio da non aggirare

Sopravvivono a questo promemoria e valgono per chiunque tocchi l'area.

**Non esiste uno stato di pagamento della rata.** Finché è così, nessuna colonna
«scaduta / insoluta / da incassare», nessuna colorazione di sollecito, nessun
filtro «da incassare»: su una fattura già incassata sarebbero **tutti falsi**.
Meglio non mostrare un dato che mostrarne uno che mente.

**«Prossima rata» è un concetto temporale, non di pagamento.** La regola vive già
in `useScadenzeSintesi` — la prossima per data, e se sono tutte passate l'ultima —
ed è **una per tutto il prodotto**. Chi la ricalcolasse per conto proprio farebbe
dire a due schermate cose diverse sullo stesso documento.

**⚠️ Lo scope emittente in `pagamenti` è a metà.** (Nuovo, 2026-08-09.)

Misurato su `pg_class.relrowsecurity` e sui trigger: nessuna tabella di
`pagamenti` ha RLS, mentre `vendite.fatture` e `vendite.fatture_scadenze` sì. In
**scrittura** però `vendite_movimenti` è presidiata: porta
`trgfn_guard_emittente_scope('fattura', 'fattura_id')`, che nega la creazione di
un movimento su una fattura fuori scope.

Quindi non è «lo scope manca», è **lo scope è asimmetrico**, e le due metà vanno
distinte perché costano decisioni diverse:

- **in lettura, nulla.** Il giorno in cui si espone una lista incassi, mostrerà a
  chiunque movimenti di fatture che l'operatore non può aprire. La fattura è
  filtrata, il suo incasso no;
- **in scrittura, solo il movimento.** `vendite_contabili_righe` — che è il vero
  punto d'ingresso operativo, quello su cui atterra un flusso bancario — **non ha
  nessun guard di scope**: può puntare a una fattura di qualunque emittente. Il
  cancello scatta solo alla fine, al posting, quando l'operatore ha già lavorato
  la riga.

✅ **Deciso il 2026-08-09 (§2-bis D5): il perimetro si deriva dal conto di
incasso**, non dalla fattura. Il denaro ha un padrone dal primo istante — l'ha
scelto il cliente pagando su quel conto — e questo scioglie il nodo della riga
con `fattura_id IS NULL`, che altrimenti sarebbe **invisibile a tutti**.

Restano da scrivere le tre cose dell'elenco in §2-bis D5: la colonna del conto
sull'ente di incasso, il vincolo di unicità conto → emittente, e la
configurazione dei conti dei due emittenti.

**⚠️ «Incassato» non è «postato»: le misure devono escludere i centri non-cassa.**
(Nuovo, 2026-08-15.)

Non tutti i movimenti sono denaro arrivato. Il fondo fattura produce già oggi
righe contabili `ABBINATA` sul centro `FONDI_FATTURA`, e il giorno del posting
diventeranno movimenti veri: la fattura sorgente **è** stata saldata, ma per
**trasferimento** su un'altra fattura, non per cassa. Lo stesso vale per il
centro `COMPENSAZIONI`.

| Domanda | Che cosa si somma |
| --- | --- |
| «questa fattura è ancora da pagare?» | **tutti** i movimenti — il trasferimento la salda davvero |
| «quanto è **entrato** in banca?» | solo i centri di cassa: `is_fondo_fattura` e `is_compensazione` vanno **esclusi** |

🔴 **La distinzione va messa nella prima misura che si scrive, non aggiunta
dopo.** Un cruscotto di incassato che somma tutto conta come denaro arrivato
qualcosa che è stato solo spostato, e l'errore non si vede: il numero è
plausibile e cresce nel verso giusto. `centri_riscossione` porta già le due
colonne che servono — è la ragione per cui esistono.

---

## 4-bis. Le domande ancora aperte

Non bloccano il disegno: si decidono entrando nella slice che le riguarda. Sono
qui perché una domanda non scritta si ripresenta come sorpresa.

> **D1, D2, D3, D5 e D9 sono decise** e stanno in §2-bis, in ordine logico più
> che numerico (D9 segue D3 perché ne discende). **D7 è stata assorbita da
> D3-d**: senza il concetto di storno, la domanda non ha più oggetto.

| | Domanda | Orientamento (non deciso) |
| --- | --- | --- |
| **D4** | L'**abbinamento automatico** è nella prima slice? | **No** — vedi il riquadro sotto |
| **D6** | L'**import del flusso** bancario è nella prima slice? | **No** — vedi il riquadro sotto |
| ~~**D7**~~ | ~~Lo **storno** è una riga di segno opposto o un cambio di stato?~~ | **Chiusa da D3-d il 2026-08-09**: non è né l'uno né l'altro, perché lo storno non esiste come concetto. È una contabile con importi negativi |
| **D8** | Come interagiscono **note di credito** e compensazioni col saldo per rata? | 🟡 **Aperta, ma dal 2026-08-18 molto più precisa.** `pagamenti.compensazioni` resta il candidato. ⭐ Il design NC ([brief-design-note-credito-resi.md](brief-design-note-credito-resi.md) §12.4-bis.7) ha stabilito che una NC ha `totale_a_pagare` **negativo** e quindi **nessuna rata** — `fn_genera_scadenze_fattura` lo tratta già (*«saldo a favore del cliente»*, D-D caso 3) e `fn_assign_numero_fattura` lo presidia (*«un documento non positivo non si rateizza»*). Ne discende che **la NC non entra nel saldo per rata: non ne ha**. Il credito si regola in due modi, e solo il secondo è aperto: (a) **dentro la banda del minimo** → fondo fattura negativo applicato alla fattura successiva, ✅ già progettato; (b) **fuori dalla banda** → nessun fondo automatico e nessuna rata, quindi serve il **processo rimborsi**, che la doc di `fatture_fondi_fattura_source` nomina già (fondo `origine = MANUALE`, motivo obbligatorio, *«arriva dal processo rimborsi di `pagamenti`»*) ma che **non esiste**. 🔴 **La domanda vera di D8 è (b): dove si vede un credito grande che va rimborsato?** — oggi da nessuna parte |

### ⚠️ D4 e D6 sono **due mestieri diversi**, e vanno tenuti separati

Chiarito il 2026-08-09: fino a quel giorno stavano sotto un'unica etichetta
(«abbinamento automatico») e non è la stessa cosa.

| | Cosa fa | Che cosa risparmia |
| --- | --- | --- |
| **D6 · importare** | leggere il file della banca e creare la contabile con le sue righe: data, importi, IBAN del pagatore, causale | la **digitazione** |
| **D4 · abbinare** | decidere a quale cliente, fattura e rata va ciascun importo | il **ragionamento** |

⭐ **Sono indipendenti in tutti e due i versi**, ed è il punto pratico:

- si può **importare senza abbinare** — il file entra, le righe restano
  `DA_ABBINARE`, la persona le attribuisce a mano. È già molto;
- si può **abbinare senza importare** — una contabile digitata a mano può
  ricevere ugualmente una proposta.

*Il file non porta con sé l'abbinamento, e l'abbinamento non ha bisogno del file.*

**Perché D4 resta fuori dalla slice 1.** `enti_incasso.regole_match` è un
contenitore di regole, ma una regola di abbinamento **si tara sui casi veri**:
quali causali scrivono davvero i clienti, quanto spesso pagano importi tondi,
quanto spesso accorpano due fatture. Con **zero incassi e zero flussi** le regole
si scriverebbero immaginando i casi, che è il modo migliore per costruire un
automatismo che sbaglia su ciò che non era stato immaginato. E c'è una ragione
più semplice: finché non esiste l'abbinamento **manuale**, un automatismo non ha
dove atterrare — propone, e poi?

**Perché D6 resta fuori dalla slice 1.** `enti_incasso` è a **0 righe**: non
esiste un canale configurato da cui un file possa arrivare, e prima serve la
colonna del conto decisa in D5.

#### ✅ Una cosa di D4 si può però decidere subito: **propone, non decide**

Il modello ha già la risposta pronta, e non costa niente riconoscerla ora: gli
stati `DA_ABBINARE` («non so») e `SOSPESA` («ho un dubbio») esistono.

> Un abbinamento automatico **incerto lascia la riga dov'è e propone**. Solo un
> indizio **certo** — il riferimento strutturato di §3.6 — può portarla ad
> `ABBINATA` da solo.

Così l'automatismo **non può sbagliare in silenzio**: al massimo non aiuta. È il
criterio che rende sicuro accenderlo, quando sarà il momento.

⚠️ **D4 e D6 insieme dicono cos'è la prima slice**: contabile inserita a mano,
abbinata a mano, postata. Nessun file, nessuna regola automatica. È poco, ed è
apposta: è il percorso più corto che produce **un movimento vero**, e finché non
esiste un movimento vero tutto il resto si progetta al buio.

---

## 5. Trappole già pagate, da non ripagare

- ⚠️ **`AlertScadenzeWidget.vue` non c'entra.** Nonostante il nome, riguarda le
  **versioni di listino** in scadenza senza successore, non le rate di fattura.
  Chi lo trova cercando «scadenze» sta guardando un altro dominio.
- ⚠️ **Il guard D-K presidia già la coerenza rate ↔ totale** in numerazione
  (sei condizioni, `E_FATTURA_NON_NUMERABILE_INCOERENTE`). Chi lavorerà agli
  incassi lo troverà sul percorso: **non è da allentare**: una fattura le cui
  rate non quadrano col totale non deve prendere un numero fiscale, e a maggior
  ragione non deve entrare in riconciliazione. (Vive in
  `vendite.fn_assign_numero_fattura`, che insieme a `fn_genera_scadenze_fattura`
  è **l'unico** altro lettore di `fatture_scadenze` in tutto il DB.)
- ⚠️ **Il piano rate è uno snapshot congelato.** Oltre DRAFT/EMESSA le rate non
  si toccano più (guard satelliti). La riconciliazione scrive quindi **altrove** —
  sulla riga contabile, per D1 — e mai «aggiorna la rata come pagata»
  modificando `fatture_scadenze`. È anche la ragione per cui D2 non era una
  scelta libera.
- 🔴 **Un'etichetta sul documento crea gerarchie che il dominio non ha**
  (2026-08-09, da D3-d). Chiamare «contabile di storno» un documento fa nascere
  la domanda su cosa sia lo storno di uno storno, e con essa la paura di una
  catena infinita — che poi si vorrebbe fermare con un guard. Ma **il denaro non
  ha versi, ha segni**: tolta l'etichetta la domanda non si semplifica, sparisce,
  e la sicurezza viene da un controllo sulla **somma** (`0 ≤ Σ ≤ importo`) che
  rende una catena lunga soltanto disordinata. *Prima di presidiare un caso
  ricorsivo, verificare di non averlo introdotto con un nome.*
- ⚠️ **Un catalogo pieno di righe irraggiungibili insegna cose false**
  (2026-08-09, da D9-a). `STORNATA` sarebbe rimasta a elenco senza più nessun
  gesto capace di assegnarla: chi legge un catalogo lo legge come un'offerta di
  possibilità. Si ritira con `obsoleto_dal`, mai con `attivo = false`.
- ⚠️ **Un intervallo simmetrico non ha due estremi della stessa natura**
  (2026-08-09, da D1-bis). `0 ≤ Σ ≤ importo` si legge come una sola regola, ma
  sforare in alto è un **fatto del mondo** provocato dal cliente (il sovra-incasso
  capita, nelle utilities spesso) mentre sforare in basso è **solo un errore di
  chi opera**. Il primo va reso forzabile, il secondo no: *la forma della formula
  non è un argomento sulla natura di ciò che vieta.*
- 🔴 **Un intervallo i cui estremi possono invertirsi non è un guard: è una
  porta chiusa travestita da controllo** (2026-08-09, da D1-bis). `0 ≤ Σ ≤
  totale_a_pagare` sembra il fratello maggiore della quadratura per rata, ma su
  un documento a credito diventa `[0, −50]`, cioè **vuoto**: rifiuterebbe ogni
  pagamento, sempre, e sembrerebbe un guard che funziona. Il progetto ha già
  pagato la stessa trappola un livello più sotto — il filtro `totale_a_pagare >
  0` nella quadratura rate/totale. *Prima di replicare un controllo a un livello
  superiore, verificare che gli estremi non possano scambiarsi di posto.*
- ~~⚠️ **Un automatismo tarato su un verso non va lasciato correre nell'altro**
  (2026-08-09, da D1-bis).~~ 🔴 **Trappola ritirata il 2026-08-15: era essa
  stessa un errore.** Il verso «negativo» **non** era un altro fatto — era metà
  del meccanismo (la banda `−500 / +10`, vedi D1-bis). La lezione che resta è
  l'opposta, e vale di più:
- 🔴 **Prima di dedurre l'intenzione di un automatismo dal suo comportamento,
  leggere la configurazione che lo governa** (2026-08-15). Dal solo filtro
  `<> 0` sembrava evidente che la funzione fosse «nata per un verso» e lasciata
  correre nell'altro per distrazione. Le due soglie dicevano il contrario: il
  verso opposto era **previsto**, e il tampone proposto lo avrebbe spento. *Il
  codice mostra cosa fa, non cosa deve fare: quello sta nei parametri.*
- ⚠️ **Un difetto e un comportamento voluto possono avere lo stesso sintomo**
  (2026-08-15, stessa misura). Un fondo negativo può essere il credito riportato
  dalla banda (corretto) oppure una riga contabile più grande della fattura
  (difetto). Un guard — o un test — che guarda **il segno** non li distingue; a
  distinguerli è la **corrispondenza con la sorgente**. *Prima di presidiare un
  sintomo, contare quante cause diverse lo producono.*
- 🔴 **Una serratura su un solo termine non chiude una differenza** (2026-08-15,
  rimisurando §2-bis D1-bis). Il fondo negativo era dato per irraggiungibile
  perché `fn_get_saldo_fattura` non può andare sotto zero senza movimenti: vero,
  ma il fondo si genera su `saldo − saldo_contabile`, e il **secondo** termine
  non c'entra coi movimenti. La finestra si apriva da un lato che nessuno stava
  guardando. *Quando una condizione nasce da un'espressione, la serratura va
  cercata sull'espressione — non sul termine che si è letto per primo.*
- ⚠️ **Una serratura che non è un vincolo è solo l'assenza di scrittori**
  (2026-08-15, stessa misura). «Nessuno lo fa» regge finché non arriva il primo
  che lo fa, e non lascia traccia di essersi rotta: non c'è un errore, c'è un
  dato sbagliato. *Prima di appendere una scadenza a un cantiere («lo apre la
  slice 1»), verificare se la porta ha una serratura o soltanto nessuno che
  passa di lì.*
- ⚠️ **Un flag riscritto da un calcolo non è una configurazione** (2026-08-15).
  `vendite.fatture.minimo` sembra un dato che qualcuno imposta: lo riscrive
  `fn_ricalcola_totali_fattura` confrontando il totale con le soglie
  dell'emittente. Si accende **da solo** al primo ricalcolo dopo il seed delle
  soglie. *Prima di dire «lo apre una configurazione, quando vorremo», cercare
  chi scrive quella colonna.*
- 🔴 **Togliere un automatismo scopre ciò che l'automatismo copriva**
  (2026-08-15). Il tampone «niente `ANNULLATO` automatico» è giusto — ma quel
  ramo era anche l'unica cosa che impediva di **applicare** un fondo non più
  dovuto. Toglierlo da solo peggiora la situazione invece di migliorarla: serve
  contestualmente il guard che rilegge la capienza **al momento dell'atto**.
  *Un automatismo sbagliato fa spesso due mestieri: prima di spegnerlo, chiedersi
  quale dei due stava reggendo qualcosa.*
- ⚠️ **Una forzatura senza un elenco a valle è un modo per nascondere, non per
  registrare** (2026-08-09, da D1-bis). Chi concede un override deve dire anche
  **dove si vede dopo**: un sovra-incasso è denaro da restituire o da applicare
  altrove, e se non compare da nessuna parte la forzatura ha solo spostato il
  problema fuori dalla vista.
- ⚠️ **Una verità di dominio su cui poggia un perimetro di sicurezza deve
  diventare un vincolo** (2026-08-09, da D5). «Due emittenti hanno conti
  diversi» è vero nel mondo e il database non lo sa: finché serviva a stampare un
  IBAN era un fastidio, come base del perimetro è un varco. Il costo di scriverla
  è un indice; il costo di non scriverla non si vede finché non è successo.
- ⚠️ **Le tabelle vuote non sono tabelle assenti.** Le 10 tabelle di `pagamenti`
  esistono con vincoli, trigger e manuali: prima di progettare qualcosa di nuovo,
  leggere `guide/gestione-dei-pagamenti.md` — buona parte del modello c'è già e
  aspetta solo di essere usata.
- 🔴 **`pg_stat_user_tables.n_live_tup` non è un conteggio** (2026-08-09). È la
  stima dell'autovacuum, e su tabelle scritte una volta sola da un seed Liquibase
  dice **0** per tutte e dieci le tabelle di `pagamenti`. È da lì che nasce la
  riga sbagliata del 02-08. Per misurare la popolazione di uno schema
  **`SELECT count(*)`, tabella per tabella** — la stima è per il planner, non per
  una decisione di progetto. *La misura è un programma e può avere il suo
  difetto.*
- 🔴 **Il terreno di prova è quasi vuoto: 2 rate, 0 movimenti, 0 contabili.**
  Nessuna misura sui dati veri potrà smentire un'ipotesi sbagliata di disegno, e
  i pgTAP dovranno costruirsi ogni fixture da zero. Vale in particolare la
  trappola già registrata altrove: *un ramo si verifica dal percorso che lo
  attraversa, non dal codice che lo dichiara* — qui non c'è **nessun** percorso
  reale che lo attraversi, quindi ogni fixture rischia di confermare un ramo
  morto. Asserire la **quadratura** (Σ allocazioni ≤ importo rata, Σ movimenti =
  Σ righe postate) più che i singoli valori.

---

## 6. Dove guardare quando si riprende

| Cosa | Dove |
| --- | --- |
| Il modello pagamenti esistente | [gestione-dei-pagamenti.md](/guide/gestione-dei-pagamenti) |
| Le rate: struttura, formula, cosa NON sono | [dbzero/vendite/manual/fatture_scadenze.md](/dbzero/vendite/manual/fatture_scadenze) |
| Il catalogo dei termini | [dbzero/config/manual/termini_pagamento.md](/dbzero/config/manual/termini_pagamento) |
| Il residuo per fattura, già pronto (⚠️ §1-bis) | `pagamenti.fn_get_saldo_fattura` |
| Il saldo in lavorazione | `pagamenti.fn_get_saldo_fattura_contabili` |
| Il punto d'ingresso della testata | `pagamenti.fn_get_or_create_vendite_contabile` |
| La bilancia dei due saldi (il buco logico) | `vendite.fn_genera_fondi_fattura_source` — ⚠️ la serratura sta sulla **differenza**, non su `saldo`: §2-bis D1-bis |
| Chi crea davvero righe contabili oggi | `vendite.fn_ricalcola_totali_fattura` → `fn_sync_contabili_fondo_fattura` — ed è **l'unica** funzione del DB che scrive `vendite_contabili_righe` |
| Dove `vendite.fatture.minimo` viene **scritto** | `vendite.fn_ricalcola_totali_fattura` (soglie su `anagrafiche.emittenti_fiscali_utilities`) |
| L'anagrafica conti (uso `INCASSO`, predefinito unico) | `anagrafiche.soggetti_ruoli_conti_bancari` + `conti_bancari` |
| Il risolutore azienda → conto | `script.fn_get_conto_bancario_predefinito` → `anagrafiche.vw_conti_bancari_per_ruolo` |
| Il precedente che punta già al conto | `pagamenti.sepa_mandati.soggetto_ruolo_conto_id` |
| Come sono nate le rate (cantiere chiuso) | `work-done/brief-db-generazione-scadenze-fattura.md` |
| Atomicità: una azione = una unità di lavoro | [api.md §Atomicità](/dev/api) + `linee-guida-sql` §5b |
| ⚠️ Il guscio vuoto che sembra il posting | `vendite.fn_sync_pagamento_fondo_fattura` — vedi §1-bis. ✅ **Deciso il 2026-08-15: si ritira** (`DROP`), il difetto è che esiste |
| Il meccanismo dei fondi, cantiere a parte | [brief-db-fondo-fattura-ricalcolo-e-governo.md](brief-db-fondo-fattura-ricalcolo-e-governo.md) — dal 2026-08-15 ha il suo **piano** in §8: la Fase A è la metà «fondi» della slice 1 |

---

## 7. Il cantiere, in tre slice

L'ordine non è una preferenza: ogni slice rende **vera** una cosa che la
successiva dà per scontata.

| | Slice | Contenuto | Chiude |
| --- | --- | --- | --- |
| **1** | **Posting, stati e correzione** | madre DB `ABBINATA → POSTATA` + movimento, atomica, per testata; **transizioni dichiarate** su testata e righe + guard stato ↔ nullità; `STORNATA` ritirato; annullamento solo in bozza; `stato_id` NOT NULL; **CSV + loader per `centri_riscossione`** (oggi inesistenti: le 2 righe sono state inserite a mano) con backfill delle esistenti e aggiunta dei centri reali; 🔴 **la Fase A del cantiere fondi** — ⚠️ **non** «limite inferiore `> 0`», che era sbagliato (D1-bis): CHECK «entrambe le soglie o nessuna», sorgente solo **DEFINITIVA**, guard di **corrispondenza col documento** e di capienza all'applicazione, chiave a nove elementi ([brief-db-fondo-fattura…](brief-db-fondo-fattura-ricalcolo-e-governo.md) §8.2); codici errore di dominio a catalogo con la loro classe | B-1, B-2, D3, D9, la metà «fondi» di D1-bis. Rende **vero** `fn_get_saldo_fattura`, che oggi risponde sempre `totale_a_pagare` |
| **2** | **Abbinamento alla rata** | `scadenza_id` sulla riga + mirror sul movimento; guard di quadratura (**con forzatura motivata e gated sul limite superiore**, D1-bis) e di coerenza; `fn_get_saldo_rata`; elenco delle rate sovra-incassate | D1, D1-bis, D2. Rende derivabile «questa rata è pagata» — la domanda da cui dipendono 3.2, 3.3 e 3.4 |
| **3** | **Perimetro e coda operativa** | conto sull'ente di incasso, vincolo di unicità conto → emittente, RLS in lettura; poi BE e FE | D5, B-3. Rende la coda «da abbinare» **visibile a chi deve** |

~~🔴 **La scadenza della metà «fondi» non è la slice 1** (rimisurato il
2026-08-15, §2-bis D1-bis). La finestra del fondo negativo la apre il **primo che
scrive righe contabili** — l'import del flusso, una correzione a mano, o la
slice 1: quello che arriva prima. La collocazione qui resta giusta perché è qui
che si mette mano a quel terreno, ma se un altro lavoro ci arriva prima, il
tampone va **con lui**, non aspetta il suo turno.~~

> ✅ **CHIUSO il 2026-08-15, verificato il 2026-08-21.** La metà «fondi» **non è
> più della slice 1: è fatta.** Fasi A, B, C, E ed F del cantiere fondi
> applicate il 15-16/08 (changeSet `20260815-03`…`-23`), pgTAP verdi, baseline
> `vendite` senza regressioni. La colonna «Contenuto» della slice 1 qui sopra va
> letta **senza** il suo ultimo blocco.
>
> ⭐ **E la dipendenza si è invertita**: del cantiere fondi resta la sola
> **Fase D** (l'atto manuale), ferma **per scelta finché `pagamenti` non ha un
> processo rimborsi** — cioè finché non si chiude la **D8 (b)** di §4-bis. Non è
> più questo cantiere a portarsi dietro lavoro di `vendite`: è `vendite` ad
> aspettare questo.
>
> ⚠️ **Ma il posting arma due difetti in `vendite` che nessuno aveva visto**, ed
> entrambi vanno nella slice 1 insieme alla madre: il sync dei fondi
> **riscriverebbe righe già postate**, e un fondo interamente postato **si
> auto-annullerebbe**. Misure e passi in
> [brief-db-posting-e-abbinamento-rata.md](brief-db-posting-e-abbinamento-rata.md)
> §1.4 C-2 e C-3.

⚠️ **La slice 1 non tocca le rate**, e va bene così: è il gradino sotto tutto il
resto, e si può collaudare senza aver deciso niente della 2.

⭐ **E contiene la correzione fin da subito** (Tid, 2026-08-09). Non è ampliare il
perimetro: un gesto che non si può correggere non è utilizzabile da una persona,
e rimandare la correzione alla slice 3 significherebbe collaudare la 1 e la 2 con
un operatore che al primo errore resta fermo. Dopo D3-d costa anche poco, perché
la correzione **non è un meccanismo**: è una contabile con importi negativi.

🔴 **Prerequisito senza il quale la slice 1 non parte**, e non è «una riga di
seed»: `centri_riscossione` **non ha né CSV né loader**, e le sue due righe —
entrambe interne — sono state inserite **a mano** il 17-02-2026. Su un DB
ricostruito da zero la tabella è **vuota**, quindi in CI non funzionano neanche
fondi fattura e compensazioni. I quattro pgTAP non lo rivelano perché si
fabbricano il centro da soli. Vedi §2-bis D9-d-1 per i quattro passi.

⚠️ **Prerequisiti trasversali**, da non scoprire a metà strada: nessun codice
errore di dominio `pagamenti` esiste a catalogo (vanno seminati **con la loro
classe**, il backend li deriva da lì); l'area funzionale `pagamenti` invece c'è
già (`config.aree_funzionali` id 7); l'app Django e la cartella frontend sono
stub vuoti.

---

## 8. Registro delle revisioni

| Data | Cosa è cambiato |
| --- | --- |
| 2026-08-21 | ⭐ **Estratto il piano DB in un brief suo**: [brief-db-posting-e-abbinamento-rata.md](brief-db-posting-e-abbinamento-rata.md). Qui restano le **decisioni di dominio**, là i **passi e le misure** — con la regola esplicita di quale sede si aggiorna per cosa, perché due documenti sullo stesso cantiere aperto divergono al primo aggiornamento (lezione già pagata dal cantiere fondi). 🔴 **Tre punti di questo brief corretti perché parlavano al presente di cose non più vere**: `fn_sync_pagamento_fondo_fattura` **non esiste più** (ritirata il 15/08); **B-2 era sbagliato a metà** — il trigger di mirror ha **già** il guard e solleva `P0001`, e il difetto vero è che tutte e quattro le funzioni di `pagamenti` sollevano `E_GENERICO`; il riquadro sulla **scadenza della metà «fondi»** è chiuso, perché quella metà è **fatta** (Fasi A/B/C/E/F applicate il 15-16/08) e **la dipendenza si è invertita** — la Fase D del cantiere fondi aspetta il processo rimborsi di `pagamenti`, cioè la **D8 (b)** di §4-bis. 🔴 **Cinque difetti nuovi misurati** e scritti là, tre bloccanti: `centri_riscossione` **non può contenere più di due righe** (il `where:` su `addUniqueConstraint` fu ignorato: il passo 3 di D9-d-1 oggi non è eseguibile, annotato in loco); `fn_sync_contabili_fondo_fattura` **riscriverebbe righe già postate**; un fondo interamente postato **si auto-annullerebbe**. ⭐ La lezione trasversale ai due: *verificare che un'identità algebrica si conservi non è verificare che i consumatori la usino ancora bene* — §1-bis prova che «la bilancia regge da sé» ed è vero, ma il codice che quei termini li **riscrive** non regge |
| 2026-08-15 (sera) | 🔴 **Il tampone di D1-bis era sbagliato, e l'ha smontato Tid spiegando cosa sono davvero le due soglie.** *«Il verso opposto non è un fondo»* è **falso**: `minimo_soglia_min` e `minimo_soglia_max` sono i **due capi di una banda che contiene lo zero** (esempio reale: `−500 / +10`), e il capo inferiore esiste **apposta** per riportare avanti i **crediti**. Un filtro `importo_target > 0` avrebbe spento metà del meccanismo, in silenzio. Il controllo giusto è la **corrispondenza col documento** (stesso segno del totale della sorgente, non superiore in valore assoluto), in un **guard trigger** perché un CHECK non può leggere `vendite.fatture`. 🔴 Seconda scoperta: **«soglia non impostata = meccanismo spento» vale solo a metà** — se manca il *massimo* la condizione diventa vera per tutti e **ogni** fattura diventa di minimo: configurazione incompleta = meccanismo **spalancato**. Deciso da Tid: dev'essere un errore di configurazione (CHECK «entrambe o nessuna»). Ritirata la trappola *«un automatismo tarato su un verso»* di §5, che era essa stessa l'errore, e sostituita con le due lezioni vere: **leggere la configurazione prima di dedurre l'intenzione**, e **un difetto e un comportamento voluto possono avere lo stesso sintomo**. ✅ Confermato il perimetro del processo rimborsi (in `pagamenti`, tre uscite, passaggio **passivo**: se le va a cercare da sé) |
| 2026-08-15 | 🔴 **Rimisurata la tabella delle «due serrature» di D1-bis: sbagliata su entrambe le righe.** Il fondo si genera sulla **differenza** `saldo − saldo_contabile` e il secondo termine non dipende dai movimenti: la seconda serratura **non è la slice 1**, è **l'assenza di scrittori di righe contabili** (il guard di quadratura è la slice **2**), e si apre col primo altro scrittore — import del flusso, correzione a mano, o slice 1. E `minimo` non è una configurazione: lo **riscrive** `fn_ricalcola_totali_fattura` dal confronto fra totale e soglie dell'emittente, quindi si accende da solo. La conclusione operativa non cambia (il limite inferiore resta nella slice 1), cambia la **scadenza**. 🔴 Aggiunto che **il limite inferiore da solo peggiora le cose**: senza l'`ANNULLATO` automatico un fondo non più dovuto resta `DISPONIBILE` e viene comunque **applicato** — serve nello stesso lotto il guard che rilegge la capienza al momento dell'atto. ✅ Chiusa la domanda lasciata aperta in D1-bis (fondo esistente con target negativo: **si lascia com'è**) e decisa F-4 (`fn_sync_pagamento_fondo_fattura` si **ritira**). ⭐ Verificato che con un posting **atomico** la bilancia di B-1 **regge da sé** (i due termini si scambiano lo stesso importo): il rischio è tutto nella non-atomicità. ⚠️ Nuovo limite di dominio in §4: «incassato» ≠ «postato» — le misure di cassa devono **escludere i centri non-cassa** (`is_fondo_fattura`, `is_compensazione`), perché il fondo diventerà un movimento vero ma per **trasferimento**. Quattro trappole nuove in §5. Fonte: il piano del cantiere fondi, [brief-db-fondo-fattura…](brief-db-fondo-fattura-ricalcolo-e-governo.md) §8 |
| 2026-08-02 | Stesura originale alla chiusura del cantiere satelliti fattura |
| 2026-08-09 (mattina) | Rimisurato il DB. Corrette 3 righe della tabella §2 (cataloghi seminati, non a zero); aggiunta §1-bis — **il posting non esiste**, più tre buchi logici misurati: B-1 bilancia dei due saldi, B-2 nullità riga↔movimento e stato slegato dai dati, B-3 scope emittente asimmetrico; aggiunte 3.0 (posting) e 3.5 (`sepa_mandati` orfana); riscritto il limite di scope in §4; due trappole nuove in §5 (`n_live_tup`, terreno vuoto) |
| 2026-08-09 (notte, 6) | ⭐ Fissato con Tid il **principio di chiusura sul flusso di denaro** (§3-bis): **i fatti si aggiungono, i saldi si leggono, le decisioni le prende una persona**. Ne discende che la rincorsa degli incassi è **impossibile per costruzione**, non solo improbabile: un ciclo richiede un automatismo che riscriva un numero, e non ce ne sono. Regola pratica: nessun automatismo tocca il fondo in base agli incassi; l'attività pre-fatturazione **presenta, non sana**. Annotato che il **rimborso non è da costruire** (il movimento copre già «incasso o rimborso», e con D3-d è una contabile negativa). Trovato e segnalato `vendite.fn_sync_pagamento_fondo_fattura`: nome e colonne promettono movimenti, il corpo delega tutto a `fn_sync_contabili_fondo_fattura` e **nessuno la chiama** — probabile causa dell'equivoco «il posting esiste». Estratto il cantiere del meccanismo fondi in un **brief proprio**: `brief-db-fondo-fattura-ricalcolo-e-governo.md` |
| 2026-08-09 (notte, 5) | Collocata la modifica ai fondi: **va nella slice 1, non dopo**. Misurato che il ramo negativo è oggi chiuso da **due serrature** — `minimo IS TRUE` (0 fatture su 12) e saldo negativo (nessun movimento) — e che **è la slice 1 ad aprire la seconda**. Da lì basta una configurazione a minimo perché un sovra-incasso generi un fondo negativo `DISPONIBILE` assegnato a una figlia. Annotato che entrambi i task fondi sono `attivo = true` (codice vivo, dominio `vendite`) e le regole di lavorazione su funzione esistente |
| 2026-08-09 (notte, 4) | Su indicazione di Tid, due aggiunte a **D1-bis**. **(1)** Il fondo fattura **non si genera da solo** su un sovra-incasso: misurato che `fn_genera_fondi_fattura_source` filtra solo `<> 0`, quindi con saldo negativo creerebbe un fondo **negativo e `DISPONIBILE`** (e `ANNULLATO` scatta solo a zero) che `applica_fondi_lotto` assegnerebbe a una figlia — senza alcun CHECK a fermarlo. L'automatismo prende un **limite inferiore** (`> 0`) e l'eccedenza diventa **lavoro governato** (rimborso / compensazione / applicazione futura). Aperta: che fare di un fondo esistente il cui target diventa negativo. **(2)** Una fattura con `totale_a_pagare < 0` **si può pagare**: ha zero rate per progetto, quindi il pagamento si registra sulla **fattura** con `scadenza_id` NULL e nessuna quadratura per rata entra in gioco. 🔴 Fissato di **non** replicare la quadratura a livello fattura: l'intervallo si invertirebbe. Due trappole nuove in §5 |
| 2026-08-09 (notte, 3) | Aggiunta **D1-bis** su indicazione di Tid: il **sovra-incasso è un fatto reale** (frequente nelle utilities) e va **registrabile con forzatura**. Precisato che il guard non impedisce di incassare ma di caricare una rata oltre il suo valore, e che il caso ordinario si risolve **spezzando la riga** senza forzare nulla. La forzatura è **esplicita, motivata, gated** (esiste già `approva_rimessa` sull'area pagamenti; pattern a due tempi già in `vendite`) e **visibile in un elenco**. 🔴 Fissata l'asimmetria: **il limite superiore è forzabile, quello inferiore no**. Verificato che `fatture_fondi_fattura_source.importo` **non ha CHECK**, quindi un saldo negativo può generare un fondo negativo sulle fatture a minimo. Due trappole nuove in §5 |
| 2026-08-09 (notte, 2) | Separate **D4** (abbinare) e **D6** (importare), che stavano sotto un'unica etichetta e sono **due mestieri indipendenti nei due versi**. Deciso subito un criterio di D4: l'automatismo **propone, non decide** — solo un indizio certo può portare una riga ad `ABBINATA` da solo, così non può sbagliare in silenzio. Aggiunta **§3.6**: proposta di un **riferimento di pagamento in fattura** in standard **ISO 11649 (`RF…`)** costruito sull'id della **rata** — cifra di controllo che scarta i refusi, campo strutturato SEPA, funzioni derivate senza colonne nuove. Verificato che oggi **nessun riferimento di pagamento esiste** in tutto il sistema. Annotato il legame con §3.2: il blocco `2.4` è dove il riferimento si dichiara, ed è già il passo 2 dell'ordine di Tid |
| 2026-08-09 (notte) | 🔴 **Il difetto D9-d-1 si è rivelato più grande della sua prima stesura.** Non «manca il centro banca»: `centri_riscossione` **non ha né CSV né loader** e le due righe esistenti sono state **inserite a mano** (`user_insert = postgres`, 17-02-2026). Su un DB ricostruito da zero la tabella è **vuota** — in CI mancano anche fondi fattura e compensazioni. Invisibile perché tutti e quattro i pgTAP di `pagamenti` si fabbricano il centro da soli. Scritta la soluzione in quattro passi (CSV nuovo, backfill delle 2 righe esistenti, centri reali, loader sul modello di `20260213-04`). Aggiunto a D9-d-2 il ramo `OR NULL` di `fn_get_saldo_fattura_contabili` che diventa codice morto |
| 2026-08-09 (tarda sera) | 🔴 **Semplificata D3-d: lo storno smette di essere un concetto.** Intuizione di Tid a partire dal timore della catena di storni: non un documento etichettato, ma una contabile normale con **importi negativi**. Le tre sotto-domande d-1/d-2/d-3 **non si semplificano: spariscono**, perché erano un artefatto dell'etichetta. La sicurezza passa al controllo **simmetrico** `0 ≤ Σ ≤ importo rata`. Aggiunta **D9** (governo degli stati): `STORNATA` **ritirato** con `obsoleto_dal`, **transizioni dichiarate** su testata e righe — `pagamenti` era l'unico dominio senza —, **annullamento solo prima della conferma**. Trovati due difetti verificando: **manca il centro di riscossione per la banca** (una contabile di incasso reale oggi **non è creabile**) e **`stato_id` è nullable** proprio ora che diventa il cancello fra brogliaccio e registro. Due trappole nuove in §5 |
| ~~2026-08-09 (sera)~~ | ~~Decisa **D3-d**: storno come **contabile di storno** etichettata, con le sotto-domande d-1/d-2/d-3~~ — **superata la sera stessa**, vedi riga sopra. Restano valide le parti (a), (b), (c) di D3: testata come unità, madre DB, replay silenzioso e seconda azione parlante |
| 2026-08-09 (pomeriggio) | **Da promemoria a brief di cantiere.** Aggiunta §2-bis con le decisioni **D1** (abbinamento sulla riga contabile fino alla rata, niente tabella N:N), **D2** (stato rata derivato — chiusa dai fatti) e **D5** (perimetro dal conto di incasso + vincolo di unicità conto → emittente), ciascuna col suo perché e con ciò che la ribalterebbe. Misurata l'anagrafica conti bancari: **esiste già quasi tutta**, manca l'aggancio dell'ente al conto e il vincolo nel verso conto → azienda. Aggiunta §4-bis con le 5 domande residue (D3, D4, D6, D7, D8) e §7 col piano a tre slice. Chiarito in testata che «contabile» qui è la contabile **bancaria**, non la contabilità |
