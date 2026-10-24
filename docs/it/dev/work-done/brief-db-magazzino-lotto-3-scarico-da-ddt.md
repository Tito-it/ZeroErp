# Brief DB — magazzino, Lotto 3: la merce esce con la bolla

> **Destinatario:** team DB (`dev/db-tid`). 🔵 **Richieste a BE/FE in §6**, da fare
> **nello stesso giro di PR**: il cambio di stato della bolla passa da un verbo DB,
> e il backend oggi fa un `UPDATE` diretto. Senza di loro, la prima bolla emessa
> dopo il merge viene rifiutata.
>
> ✅ **Chiuso il 2026-10-14** (sessione BE, su richiesta di Tid): lato DB applicato e verde, richieste a
> BE/FE fatte (giri del [piano BE/FE](../work-in-progress/piano-be-fe-magazzino-lotto-3.md) §3). Quel che
> restava — collaudo a video, CI da zero, la vista della merce in viaggio (P-13.2) — e' raccolto nel piano, §5, e il copione e'
> [collaudo-in-app-magazzino-bolla-e-reso](../work-in-progress/collaudo-in-app-magazzino-bolla-e-reso.md).
>
> **Origine.** [Analisi carico e scarico §8](../work-in-progress/analisi-db-magazzino-carico-e-scarico.md),
> riga «Lotto 3», e la §9 del [brief del Lotto 2](brief-db-magazzino-lotto-2-motore.md),
> che rinvia qui quattro cose: lo scarico da DDT di vendita, la utility di storno,
> il posting dei due trasferimenti, e i verbi del blocco manuale. I prerequisiti
> sono **chiusi**: Lotto 1 (forma), Lotto 2 (primitiva e porta), verbi con
> permesso (24/25-09).
>
> ⏩ **Lato BE/FE al 2026-10-13: R-1…R-5 fatti, da collaudare** — il dettaglio e il collaudo stanno in
> [piano-be-fe-magazzino-lotto-3](../work-in-progress/piano-be-fe-magazzino-lotto-3.md) (giri A1, A2, B1, C1). Resta la CI da zero.
>
> **Stato al 2026-09-28 (notte):** ✅ **LATO DB APPLICATO E VERDE.** I
> ventiquattro changeSet `20260928-60 → -83` sono `EXECUTED` su dbdev, e il mirror
> corretto delle causali di trasporto (`20260709-11`) e' `RERAN`. La corsa pgTAP col
> runner come app e' verde (Tid), comprese le asserzioni di privilegio che la
> prova da owner non poteva far mordere (§4-ter). Verificato sul catalogo: la
> mappatura delle causali ha i `NULL` veri, l'app non ha `INSERT` su
> `movimenti_attesi` ne' `EXECUTE` su `magazzino.fn_posta_ddt`.
> ⏳ **Resta, e non e' del DB**:
> * le richieste a BE/FE (§6), da portare nello stesso giro di PR. Senza R-1
>   una bolla che muove merce non si emette dal backend, e senza R-3 la CI e' rossa;
> * la CI da zero (`ci_apply` + suite), che scrive la sua baseline;
> * la vista di lettura della merce in viaggio (P-13.2), che nasce con il suo
>   lettore;
> * ~~il Lotto **3-bis**, il carico da reso cliente (D-L3-i)~~ — ✅ lato DB
>   applicato e verde il 29-09 ([brief del 3-bis](brief-db-magazzino-lotto-3-bis-carico-da-reso.md)).
>
> *Decisioni:* 🟢 **tutte e undici prese da Tid** (26 e 28-09). Il 26-09 (§3): il magazzino sta sulla **testata** della bolla
> (D-L3-a), il dettaglio fisico sta in una **tabella figlia dei prelievi**
> (D-L3-b), e nella bolla di trasferimento la merce **entra al `CONSEGNATO`**
> (D-L3-c). Il 28-09, con la raccomandazione del brief: la sorgente è il
> **prelievo** (D-L3-d), il cambio di stato è un **verbo** con GUC-porta e
> azione `emetti_ddt` (D-L3-e), la regola del **kit** (D-L3-f), il magazzino
> **predefinito** unico per emittente (D-L3-h), i **verbi del blocco** con
> l'azione `blocca_merce` (D-L3-j), il ritiro di `ddt_righe.lotto`/`seriale`
> (D-L3-k), la mappatura **causale di trasporto → causale di magazzino** con la
> merce presso terzi fuori (D-L3-g), il **reso del cliente in un 3-bis** subito
> dopo (D-L3-i).
>
> **Perimetro:** tutto ciò che fa **uscire** la merce dal registro, o la sposta,
> attraverso un documento: la bolla di vendita (e le altre causali di trasporto
> che muovono merce), la bolla di trasferimento fra depositi, il trasferimento
> interno, lo storno quando un documento si annulla, e il blocco manuale di una
> persona. ⛔ Fuori: il reso del cliente (3-bis, D-L3-i), la merce presso terzi (D-L3-g), gli eventi
> asset, la ricezione acquisti, la produzione — vedi §7.
>
> ⚠️ **Le decisioni già prese non si ridiscutono qui.** Ogni pezzo cita la
> decisione da cui discende: M-* di carico/scarico, D-* dell'analisi aggancio,
> D-L1-* e D-L2-* dei due lotti. Una riga senza una decisione dietro è in §3,
> con una raccomandazione. Se non c'è, è un difetto di questo brief.

---

## 0. In due parole, senza tecnicismi

Il registro del magazzino oggi si scrive solo con l'inventario e la rettifica,
cioè senza un documento commerciale dietro. Questo lotto aggancia il **primo
documento vero**, la bolla, che è anche il modo in cui la merce esce tutti i
giorni.

Perché funzioni, la bolla deve imparare tre cose che oggi non sa:

* **da quale magazzino parte.** Oggi dice a chi va, non da dove parte. Si
  sceglie una volta sulla testata, accanto all'emittente;
* **da quale lotto, seriale o scaffale** esce ogni riga. Una riga di 30 pezzi
  può uscire 20 dal lotto A e 10 dal lotto B: il dettaglio sta in una piccola
  tabella sotto la riga, i **prelievi**. La riga commerciale, con prezzo e
  legame all'ordine, resta una sola;
* **che cosa succede quando si emette o si annulla.** All'emissione la merce
  esce. Se la bolla si annulla, la merce rientra con una riga opposta: il
  registro non si cancella mai.

La bolla di trasferimento fra due depositi fa uscire la merce all'emissione e
la fa **entrare** nel deposito di arrivo solo alla consegna. Nel mezzo la merce
è in viaggio, e non compare in nessuna giacenza.

---

## 1. Il filtro: che cosa entra qui, e perché adesso

Entra ciò che soddisfa **tutte e tre** le condizioni:

1. è **deciso**, o è in §3 con una raccomandazione;
2. **muove merce attraverso un documento** che esiste già (`vendite.ddt`,
   `magazzino.trasferimenti`) o lo **ripara** (lo storno), o è il **blocco**
   che ferma uno scarico (M-3, §7-bis di carico/scarico: *«è alla spedizione
   che il blocco ferma»*);
3. **non chiede un documento nuovo**: la ricezione acquisti, gli eventi asset
   e l'ordine di lavoro sono documenti che non esistono, e hanno un lotto loro.

⭐ **Perché adesso.** Il Lotto 2 ha costruito il registro e lo ha provato con due
operazioni senza documento a monte. Il passo 3 della sequenza di carico/scarico
§8 è *«il primo caso con un documento vero dietro, su una catena che esiste già
ed è collaudata»*. È anche il primo lotto che tocca **un altro dominio**
(`vendite`): il Lotto 2 lo aveva rinviato apposta, perché *«il primo scrittore
deve poter sbagliare da solo»*. Adesso il registro è provato.

⚠️ **E tocca un dominio in esercizio.** Per la D-1 del
[brief sul permesso nel verbo](brief-db-permesso-nel-verbo-di-scrittura.md), un
dominio esistente passa al modello *«una scrittura = un verbo»* quando un
cantiere tocca le sue scritture. Questo lo fa: il cambio di stato della bolla
diventa un verbo DB (D-L3-e).

---

## 2. Le decisioni da cui discende ogni riga

| Decisione | Dove sta | Che cosa impone qui |
| --- | --- | --- |
| **M-1** il verso sta nella quantità | c/s §4 | lo scarico si scrive `−qta`; il guard c'è già |
| **M-2** primitiva + operazioni, nessuna domanda nella scrittura | c/s §5-bis | le operazioni di questo lotto **chiamano** `fn_scrivi_movimento` e non ricontrollano; il controllo che «parla» sta alla conferma |
| **M-3** `disponibile = giacenza − blocchi espliciti`; il blocco è un vincolo, si libera con un atto | c/s §7-bis | la conferma della bolla chiama `fn_check_disponibilita_uscita`; il blocco si apre e si libera con un verbo |
| **M-5** lotto come tabella, seriale = `asset_id`, decide l'articolo, giacenza per ubicazione | c/s §7-quater | i prelievi portano `lotto_id`/`asset_id`/`ubicazione_id`, mai testo |
| **M-6** l'ancora è il magazzino; nessuna operazione attraversa due emittenti | c/s §7-sexies | magazzino della bolla = emittente della bolla; trasferimento solo fra magazzini dello stesso emittente |
| **M-8** si corregge aggiungendo, con una utility, al costo originale | c/s §7-quinquies | l'annullo di una bolla emessa **storna**; la utility nasce qui |
| **D-4 / §6** identità `(sorgente, chiave, causale, asset, lotto, ubicazione)`; *«la chiave la compone l'operazione: un record per tranche»* | aggancio §8-quater, c/s §6 | ogni movimento ha **il proprio record**: è la ragione di D-L3-d |
| **D-6** ogni movimento ha una sorgente `NOT NULL` | aggancio §8-quater | nessuno scarico senza il suo prelievo |
| **D-L1-a** `qta` in UoM base | Lotto 1 §3 | `ddt_righe.quantita` è già base (`trgfn_qta_from_operativa`) |
| **D-L2-c** il costo si decide dalla struttura del movimento | Lotto 2 §3 | uscita → media; gemella IN → costo dell'OUT; storno → originale |
| **D-L2-g** `trasferimenti` = interno; con trasporto = DDT `TRASFERIMENTO` | Lotto 2 §3 | due posting, due documenti |
| **D-L2-m** `usa_ubicazioni` sul magazzino | Lotto 2 §3 | l'ubicazione è obbligatoria o vietata secondo il magazzino, su prelievi e righe di trasferimento |
| **D-1 / D-2 permesso** una scrittura = un verbo; le operazioni di processo chiedono la loro azione | brief permesso §7 | il cambio di stato della bolla e i verbi di magazzino chiamano `script.fn_guard_azione` nella prima riga |

---

## 3. Le decisioni del Lotto 3

### ✅ D-L3-a — Il magazzino sta sulla TESTATA della bolla — Tid, 2026-09-26

`vendite.ddt` prende `magazzino_id` (FK a `magazzino.magazzini`) e, solo per la
causale `TRASFERIMENTO`, `magazzino_arrivo_id`.

**La ragione sul modello**: una bolla è un viaggio, e un viaggio parte da un
posto. Il magazzino è l'**ancora del perimetro** (M-6), e la bolla ha già **un**
emittente sulla testata: le due informazioni stanno allo stesso livello. Il
dettaglio fisico (lotto, seriale, ubicazione) resta sotto la riga (D-L3-b).

**Il costo, dichiarato**: due magazzini dello stesso emittente non escono con
la stessa bolla. Servono due bolle, che è anche ciò che succede fisicamente se
partono da due posti.

Ne discende:

* `magazzino_id` è **nullable** in `DRAFT` ed è **obbligatorio all'emissione**
  quando almeno una riga muove merce (D-L3-f, D-L3-g). È un motivo di
  `fn_check_ddt_emittibile`, non un `NOT NULL`: la bozza si compila per gradi;
* **stesso emittente**: `magazzini.emittente_fiscale_id = ddt.emittente_fiscale_id`,
  e per il trasferimento anche il magazzino di arrivo. Un guard, perché un
  `CHECK` non guarda un'altra tabella;
* `magazzino_arrivo_id` è **obbligatorio se e solo se** la causale è
  `TRASFERIMENTO`, ed è **diverso** da `magazzino_id` (lo stesso magazzino fra
  due scaffali è un trasferimento interno, D-L2-g);
* **immutabili fuori da `DRAFT`**, sullo stampo di
  `trgfn_ddt_guard_causale_immutabile`, che guarda lo stato **vecchio** apposta.

### ✅ D-L3-b — Il dettaglio fisico sta in una tabella figlia: i PRELIEVI — Tid, 2026-09-26

Nuova tabella `vendite.ddt_righe_prelievi`: *«di questa riga, questa quantità,
da questo lotto / seriale / ubicazione»*.

| Colonna | Note |
| --- | --- |
| `id` | chiave |
| `ddt_riga_id` | FK `NOT NULL` alla riga della bolla |
| `ddt_riga_componente_id` | FK nullable a `vendite.ddt_righe_componenti`: valorizzata quando a muoversi è un **componente** del kit (D-L3-f) |
| `qta` | UoM base, `> 0` (il verso lo mette l'operazione, M-1) |
| `lotto_id`, `asset_id` | FK; con `asset_id`, `qta = 1` (M-5 p.4, lo stesso CHECK di `movimenti`) |
| `ubicazione_id` | ubicazione di partenza; obbligatoria o vietata secondo `usa_ubicazioni` del magazzino della bolla (D-L2-m) |
| `ubicazione_arrivo_id` | solo per la bolla `TRASFERIMENTO`, secondo `usa_ubicazioni` del magazzino di arrivo; si compila entro il `CONSEGNATO` |

**Perché una tabella e non spezzare la riga**: la riga è l'unità
**commerciale** (prezzo, IVA, legame all'ordine, reso, fattura); il prelievo è
l'unità **fisica**. Spezzare la riga per lotto moltiplicherebbe prezzo e legame
all'ordine, e un reso o una nota dovrebbero sapere quale delle due metà
guardare.

Ne discende:

* le colonne testuali **`ddt_righe.lotto` e `ddt_righe.seriale` si ritirano**
  (D-L3-k): sono la vecchia forma a testo libero, la stessa che M-5 ha tolto dal
  registro;
* ⚠️ **regola del 2, dichiarata**: la ricezione acquisti (Lotto 4) avrà bisogno
  della stessa forma. Questa è la **prima** occorrenza e resta dove serve, in
  `vendite`. Alla seconda si decide se estrarre un satellite generico;
* è un **satellite della bolla**: RLS con la famiglia dei satelliti DDT
  (`20260909-37/-38`), righe scrivibili **solo in `DRAFT`** con lo stesso
  `trgfn_doc_righe_lock_fuori_bozza` delle righe. Eccezione:
  `ubicazione_arrivo_id` si compila anche dopo l'emissione, fino al
  `CONSEGNATO`.

### ✅ D-L3-c — Nella bolla di trasferimento la merce entra al CONSEGNATO — Tid, 2026-09-26

**OUT** (`TRASF_OUT`) dal magazzino di partenza **all'emissione**; **IN**
(`TRASF_IN`) nel magazzino di arrivo **al `CONSEGNATO`**, con lo stesso
`transfer_uid` e al costo dell'uscita (D-L2-c: la primitiva lo prende da sé,
passo 12). È la frase di D-L2-g, *«OUT all'emissione, IN al ricevimento»*,
agganciata allo stato che esiste.

⚠️ **La conseguenza da dichiarare**: fra `EMESSO` e `CONSEGNATO` la merce è
**in viaggio**. È fuori da `vw_giacenza` di entrambi i magazzini, e la somma
delle giacenze dell'emittente scende. È vero, non un difetto: quella merce non
è su nessuno scaffale. Il `transfer_uid` con una sola gamba **è** la merce in
viaggio, e la si legge da lì (§4, P-9).

Ne discende:

* l'annullo di una bolla di trasferimento è possibile solo da `EMESSO`
  (`CONSEGNATO → ANNULLATO` è disattiva in matrice, `SPEDITO → ANNULLATO` non
  esiste): si storna la sola OUT, perché la IN non c'è ancora;
* ⚠️ una bolla di trasferimento **non deve poter generare un reso cliente**.
  Oggi un reso nasce da qualunque bolla `CONSEGNATO`
  (`trgfn_resi_guard_ddt_consegnato`): è un guard da aggiungere (P-3).

### ✅ D-L3-d — La sorgente del movimento è il PRELIEVO, non la riga — Tid, 2026-09-28: raccomandazione accolta

**Il problema**: l'identità del movimento (`uq_mag_movimenti_identita`) non
contiene l'articolo. Se la sorgente fosse la riga della bolla
(`DDT_VENDITA_RIGA:{riga}`), i due componenti senza lotto di un kit
produrrebbero **la stessa identità** — stessa riga, stessa causale, lotto,
seriale e ubicazione nulli — e il secondo scarico verrebbe rifiutato come
doppio.

**Raccomandazione**: la sorgente è il **prelievo**. Nuova riga di catalogo
`DDT_VENDITA_PRELIEVO` → `vendite.ddt_righe_prelievi`, `key_selector = 'id'`,
scope `MAGAZZINO`. È la condizione 1 di c/s §6 applicata alla lettera: *«la
chiave la compone l'operazione, non il documento — un record per tranche»*. Un
prelievo è un movimento (due per la bolla di trasferimento, distinti dalla
causale), e l'anti-doppio resta pieno.

Ne discende anche che la vista degli orfani (D-9) copre i prelievi **da sé**,
perché si deriva dalle FK verso `config.sorgenti`. E che `DDT_VENDITA_RIGA`
resta la sorgente di ciò che è commerciale (commessa, fattura), non del
movimento.

### ✅ D-L3-e — Il cambio di stato della bolla diventa un VERBO DB — Tid, 2026-09-28: raccomandazione accolta

**Il fatto**: oggi il backend porta la bolla in ogni stato con un `UPDATE`
diretto di `stato_doc_ddt_id` (`ddt_repository.update_stato`), e nessun trigger
tocca il magazzino. Lo scarico deve avvenire **nella stessa transazione**
dell'emissione.

| | Forma | Pro | Contro |
| --- | --- | --- | --- |
| **A** ⭐ | verbo `vendite.fn_cambia_stato_ddt(p_ddt_id, p_stato)`, DEFINER del proprietario, `fn_guard_azione` nella prima riga, che nella stessa transazione chiama il posting di magazzino; l'`UPDATE` di stato diretto si chiude con una **GUC-porta** sullo stampo di D-L2-h | è il modello deciso (permesso D-1/D-2); il movimento ha un autore e un permesso; la porta chiude anche lo stato | il BE cambia (§6); `fn_conferma_reso`/`fn_annulla_reso`, che scrivono lo stato da DB, devono aprire la stessa porta |
| **B** | un trigger `AFTER UPDATE` sullo stato che chiama il posting | nessun cambio BE | lo scarico diventa un effetto collaterale di un `UPDATE`; il permesso lo controlla solo il BE, cioè il contrario della D-1 appena decisa |

**Raccomandazione: A** (✅ accolta, con l'azione `emetti_ddt` proposta sotto — ⚠️ il perimetro esatto dell'azione si conferma col BE, R-4). La porta è la **GUC transazionale nel guard di
transizione**, già usata per `POSTED`. ⛔ Non un `REVOKE` per colonna: il loop
dei grant di `ci_apply` lo annullerebbe (linee-guida-sql §11.8).

✅ **Perimetro della porta — affinato da Tid il 2026-09-28, dopo il censimento
(§5-bis): la porta vale SOLO sui passaggi che toccano il registro.** Il guard di
transizione rifiuta l'`UPDATE` diretto senza GUC quando **entrambe** le cose sono
vere:

* il passaggio è uno di quelli che muovono merce: `→ EMESSO`,
  `EMESSO → ANNULLATO`, `→ CONSEGNATO` di una bolla `TRASFERIMENTO`;
* la bolla **muove merce davvero**: la sua causale di trasporto ha una
  `causale_magazzino_id` (D-L3-g) **e** almeno una riga, o un componente, muove
  un articolo gestito (D-L3-f).

⭐ Il registro è protetto **per intero**: nessuna bolla che muove merce diventa
`EMESSO` senza il suo scarico. Il verbo resta **l'unica strada del BE** (R-1).
Sulle bolle senza merce il permesso resta al solo backend, com'è oggi. ⚠️ Il
limite è dichiarato: è la porta del **registro**, non ancora quella del
permesso su tutta la bolla. Il passaggio di `vendite` al modello pieno resta
per il cantiere che toccherà tutte le scritture della bolla.
⇒ `fn_conferma_reso`/`fn_annulla_reso` non aprono la porta: scrivono
`CONSEGNATO ↔ RESO`, che non muove merce.

⚠️ **Da decidere insieme: quale azione chiede il verbo.** Non esiste un'azione di
processo per la bolla (`azioni_processo` ha solo `registra_magazzino`). La
D-2 del permesso dice che le operazioni di processo chiedono la loro azione.
Proposta: **una** azione nuova `emetti_ddt`, che copre emissione e annullo di
una bolla emessa (sono i due passaggi che muovono merce). Gli altri passaggi
(`SPEDITO`, `CONSEGNATO`) restano sul livello d'area, **tranne** il
`CONSEGNATO` di una bolla di trasferimento, che carica merce e chiede
`registra_magazzino`. Va concordato col BE, che oggi governa il permesso.

### ✅ D-L3-f — Il kit: si muove ciò che è gestito, al livello più alto — Tid, 2026-09-28: raccomandazione accolta

`catalogo.articoli` distingue il composito (`is_composito`) e il gestito
(`gestito_a_magazzino`), ma **nessuna regola li lega**. Una riga di kit può
essere un kit **preassemblato a scaffale** (il padre è gestito) o un kit
**composto al momento** (i componenti sono gestiti, il padre no).

**Raccomandazione**, una regola sola e leggibile dal catalogo:

1. se l'articolo della riga è **gestito**, si muove **lui** (i componenti sono
   descrittivi, anche se gestiti);
2. altrimenti, se è **composito**, si muovono i **componenti gestiti**
   (prelievo con `ddt_riga_componente_id`);
3. altrimenti la riga **non muove merce**.

⛔ Mai entrambi: sarebbe uno scarico doppio della stessa merce fisica.

### ✅ D-L3-g — Quali causali di trasporto muovono merce, e con quale causale di magazzino — Tid, 2026-09-28: raccomandazione accolta

Le otto causali di `config.causali_trasporto` non sono tutte vendite.

| Causale di trasporto | Che cosa è | Proposta |
| --- | --- | --- |
| `VENDITA`, `OMAGGIO`, `CAMPIONATURA` | la merce esce e non torna | `SCARICO_VEN` |
| `TRASFERIMENTO` | fra depositi dello stesso emittente | `TRASF_OUT` / `TRASF_IN` (D-L3-c) |
| `CONTO_VISIONE`, `RIPARAZIONE`, `CONTO_LAVORO` | la merce esce ma **resta nostra**, presso terzi | ⏸️ **non movimenta in questo lotto**: è la domanda della merce presso terzi (proprietà, non valorizzazione, c/s §7-ter). La forma giusta è probabilmente un **magazzino presso terzi**, cioè un trasferimento, e va decisa a sé |
| `RESO` | bolla di reso **a un fornitore** | ⏸️ `SCARICO_RESO_ACQ`, col ciclo acquisti (Lotto 4) |

**Raccomandazione sulla forma**: una colonna nullable
`config.causali_trasporto.causale_magazzino_id` (FK a `magazzino.causali`):
`NULL` = *la bolla non muove merce*. Il posting la legge, e il `TRASFERIMENTO`
si riconosce dalla causale `TRASF_OUT`, senza cercare il codice a mano. Nessun
nuovo vocabolario: è la stessa domanda che `causali.sorgente_tipo_id` (D-L2-i)
ha lasciato aperta, ma rovesciata, ed è 1:1 davvero.

⚠️ **Da dichiarare**: una bolla `CONTO_VISIONE` di articoli gestiti, emessa dopo
questo lotto, **non** scala la giacenza, e la giacenza dirà che la merce è a
scaffale. È un buco dichiarato, non dimenticato.

### ✅ D-L3-h — Il magazzino predefinito: uno per emittente, e fa da default — Tid, 2026-09-28: raccomandazione accolta

`magazzini.predefinito` esiste, ma **nessun vincolo** impedisce due predefiniti
per lo stesso emittente, e nessuno lo legge.

**Raccomandazione**: indice `UNIQUE (emittente_fiscale_id) WHERE predefinito`,
e la bolla prende come **default** il magazzino predefinito del suo emittente
quando `magazzino_id` è nullo (solo all'`INSERT`, sovrascrivibile in `DRAFT`).
⚠️ Prima di scriverlo: verificare se il BB `script.trgfn_default_emittente_fiscale`
ha già la forma per un default di questo tipo. Regola del 2: se è un secondo
«default per emittente», l'estrazione si valuta lì.

### ✅ D-L3-i — Il reso del cliente: dentro o fuori da questo lotto — Tid, 2026-09-28: B, fuori, in un 3-bis subito dopo

`CARICO_RESO_VEN` e la sorgente `RESO_VENDITA_RIGA` esistono dal Lotto 1, ma il
reso **non sa dove rientra la merce, né quando**: nessun magazzino, nessuna data
di ricezione, e l'unico evento è la **conferma** (`fn_conferma_reso`), che è un
atto amministrativo. E la merce resa può essere da verificare o difettosa.

| | Forma | Conseguenza |
| --- | --- | --- |
| **A** | dentro: carico alla conferma del reso, nel magazzino della bolla d'origine | semplice, ma presume che la merce rientri dove era partita, e subito buona |
| **B** ⭐ | **fuori**, lotto suo subito dopo (3-bis): il reso impara il magazzino di rientro e i suoi prelievi (lo stesso satellite, regola del 2) | il ciclo si chiude bene; fino ad allora un reso confermato **non ricarica** la giacenza — buco dichiarato, e non siamo in produzione |

**Raccomandazione: B**, perché «dove e in che stato rientra» è una domanda di
dominio che il lotto non deve assumere. ⚠️ Per la regola *«un'asimmetria fra
due versi si chiude subito»*, il 3-bis va **subito dopo**, non in una fase due.
Nota di coerenza, qualunque sia la scelta: `RESO_VENDITA_RIGA` ha scope
`ROW_VALIDATOR`, non `MAGAZZINO` (riallineamento del 26-09, analisi aggancio
§8). Si decide qui se va rinominato lo scope o se resta così.

### ✅ D-L3-j — Il blocco manuale: due verbi, con quale azione — Tid, 2026-09-28: raccomandazione accolta

Oggi **nessuno** scrive `movimenti_attesi`, e l'app ha ancora `INSERT`/`UPDATE`
sotto RLS (Lotto 2, `20260918-15`). Il blocco è un vincolo che ferma lo scarico
di un altro (M-3): un atto con un autore.

**Raccomandazione**: due verbi DEFINER, `magazzino.fn_apri_blocco(…)` e
`magazzino.fn_libera_blocco(p_id, p_nota)`, con `fn_guard_azione` su **un'azione
nuova `blocca_merce`**. Non si riusa `registra_magazzino`: un blocco è una
**promessa**, non un fatto sulla merce (D-L2-d), e chi può registrare un
inventario non è per forza chi può riservare merce a un cliente. L'app perde
`INSERT`/`UPDATE` su `movimenti_attesi` nel loop dei grant. La liberazione
porta autore, momento e nota (M-3, *«si libera esplicitamente, non si consuma
da sé»*).

### ✅ D-L3-k — `ddt_righe.lotto` e `ddt_righe.seriale` si tolgono — Tid, 2026-09-28: raccomandazione accolta

Sono `varchar`, e **nessuno le legge né le scrive**: zero riferimenti nel codice
DB, nel backend e nel frontend dei DDT (letto il 26-09). Accanto ai prelievi
sarebbero una seconda sede dello stesso dato, a testo libero.

**Raccomandazione**: `DROP` nello stesso lotto, col censimento dei lettori fatto
**di nuovo** al momento di scrivere il changeSet (viste, `manual/`, template di
stampa del motore documentale).

---

## 4. Il lavoro, pezzo per pezzo

> ⚠️ I numeri di changeSet si leggono **al momento di creare il file**: Tid
> applica mentre si scrive, e un numero libero ora non lo è fra un'ora.
> Al 26-09 l'ultimo è `20260926-12`.

| # | Cartella | Che cosa | Discende da |
| --- | --- | --- | --- |
| **P-1** | `00_schema/vendite` | `ddt.magazzino_id`, `ddt.magazzino_arrivo_id` (FK, nullable), con le righe in `dbops.fk_index_policy` | D-L3-a |
| **P-2** | `00_schema/vendite` | `vendite.ddt_righe_prelievi` (colonne di D-L3-b, CHECK `qta > 0` e `asset_id ⇒ qta = 1`, `UNIQUE` sul discriminante fisico per riga/componente); `DROP` di `ddt_righe.lotto`/`seriale` se D-L3-k | D-L3-b, D-L3-k |
| **P-3** | `20_code/vendite` | guard della testata: stesso emittente, arrivo solo e sempre per `TRASFERIMENTO`, arrivo ≠ partenza, immutabilità fuori da `DRAFT`; guard dei prelievi: coerenza col kit (D-L3-f), `usa_ubicazioni`, articolo con `requires_lotto`/`requires_serial`; guard del reso: niente reso da bolla di trasferimento | D-L3-a, -b, -c, -f |
| **P-4** | `00_schema/magazzino` + `00_schema/config` | `trasferimenti_righe.ubicazione_id_da`/`_a`; `chk_mag_trasferimenti_da_a_distinti` → «magazzini diversi **oppure** ubicazioni diverse»; `causali_trasporto.causale_magazzino` (⚠️ *scritta: FK sul **codice_interno** di `magazzino.causali`, non sull'id — la valorizza un CSV, §6b*); `UNIQUE … WHERE predefinito` | D-L2-g, D-L3-g, -h |
| **P-5** | `80_data` | `config.sorgenti.csv`: `DDT_VENDITA_PRELIEVO` (scope `MAGAZZINO`); `causali_trasporto.csv` con la mappatura; `azioni_processo.csv`: `emetti_ddt`, `blocca_merce` — **dal CSV**, mai con un `UPDATE` (§11.2) | D-L3-d, -e, -g, -j |
| **P-6** | `20_code/script` | `fn_check_ddt_emittibile` impara i motivi fisici: magazzino mancante, prelievi mancanti o con somma ≠ quantità della riga o del componente, e per ogni prelievo `fn_check_riga_magazzino` + `fn_check_disponibilita_uscita` (primo motivo). ⭐ È la **conferma che parla** di M-2: la stessa funzione alimenta la capability e il guard di emissione | M-2, M-3 |
| **P-7** | `20_code/magazzino` | ⚠️ *scritta come UNA funzione, `fn_posta_ddt(p_ddt_id, p_fase)` con `USCITA`/`ARRIVO`: due sarebbero state copie (regola del 2)* — operazioni **interne** (non concesse all'app), chiamate dal verbo: un `fn_scrivi_movimento` per prelievo; sorgente il prelievo; articoli non gestiti filtrati prima (la primitiva li rifiuterebbe, Lotto 2 §9) | D-L3-c, -d, -f, -g |
| **P-8** | `20_code/magazzino` | la **utility di storno** `fn_storna_movimenti_sorgente(p_sorgente_tipo_id, p_ids)` — interna; genera lo specchio di ogni movimento non ancora stornato (`STORNO_POS`/`STORNO_NEG`, `storno_di_movimento_id`, sorgente e costo dell'originale). ⭐ Lo storno doppio lo impedisce già `uq_mag_movimenti_storno_di` | M-8 |
| **P-9** | `20_code/vendite` | il verbo `fn_cambia_stato_ddt` (D-L3-e): `fn_guard_azione`, GUC-porta, `UPDATE` dello stato; in coda, secondo la transizione: `→ EMESSO` posting uscita, `→ CONSEGNATO` posting arrivo (solo trasferimento), `EMESSO → ANNULLATO` storno. Il guard di transizione impara la porta. ⚠️ *Scritta: `fn_conferma_reso`/`fn_annulla_reso` NON la aprono — scrivono `CONSEGNATO ↔ RESO`, che dopo l'affinamento di D-L3-e non passa dalla porta* | D-L3-e |
| **P-10** | `20_code/magazzino` | `fn_posta_trasferimento(p_trasferimento_id)` — verbo sullo stampo di `fn_posta_inventario` (`registra_magazzino`, GUC `POSTED`, perimetro): per riga `TRASF_OUT` + `TRASF_IN` con lo stesso `transfer_uid`, nello stesso momento (interno: niente viaggio) | D-L2-g |
| **P-11** | `20_code/magazzino` | `fn_apri_blocco`, `fn_libera_blocco` | D-L3-j |
| **P-12** | `90_end` | la postura, **nelle tre sedi** come nel Lotto 2 (loop `ci_apply/20260205-41`, forward, `provision_db_roles.sql`): `EXECUTE` all'app solo sui verbi; le operazioni interne e la utility in `v_fn_riservate`; `movimenti_attesi` in sola lettura | permesso D-4, D-L3-j |
| **P-13** | `20_code/dbops` + `presidi.csv` | presidi: (1) **bolla emessa senza scarico** — stato ≥ `EMESSO`, magazzino valorizzato, righe che muovono merce, nessun movimento con sorgente i suoi prelievi (natura `ZERO`); (2) **merce in viaggio**, cioè `transfer_uid` con la sola OUT — una vista di **lettura**, non un presidio: la merce in viaggio è normale. ⏸️ *(2) non scritta: nessun lettore oggi — nasce con la scheda che la mostra (BE/FE)* | D-L3-c, D-6 |
| **P-14** | codici | `E_DDT_*` / `E_MAG_*` nuovi registrati coi ripieghi, `reason_key` con chiave i18n (i due presidi della CI che il Lotto 2 ha reso rossi, §4.9-§4.10 di là) | — |
| **P-15** | `db/pgtap` | §5 | M-7 |

---

## 4-bis. ✅ Scritto il 2026-09-28 — che cosa c'è, file per file

> Tre forme precisate scrivendo, dentro le D già prese: (1) la regola del kit, il
> prelievo automatico e la mappatura stanno in **tre funzioni piccole di
> `vendite`** che prendono la **riga** della bolla (`p_ddt vendite.ddt`) — il
> guard `BEFORE UPDATE` deve vedere la causale nuova; (2) i motivi fisici stanno
> in una check a sé, `script.fn_check_ddt_merce`, che `fn_check_ddt_emittibile`
> accoda: portano i `valori` della frase, i motivi di prima no; (3) il
> **prelievo automatico** — voce senza lotto, seriale né ubicazioni: il verbo
> crea da sé l'unico prelievo, l'operatore scrive prelievi solo dove c'è da
> scegliere.

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/config/20260928-60` | `causali_trasporto.causale_magazzino` → `magazzino.causali(codice_interno)` |
| `00_schema/vendite/20260928-61` | `ddt.magazzino_id`, `ddt.magazzino_arrivo_id`, `chk_ddt_magazzino_arrivo_distinto` |
| `00_schema/vendite/20260928-62` | `vendite.ddt_righe_prelievi` + policy `rls_ddt_righe_prelievi_ef_whitelist` + RLS accesa |
| `00_schema/vendite/20260928-63` | `DROP` di `ddt_righe.lotto` / `.seriale` |
| `00_schema/magazzino/20260928-64` | via `chk_mag_trasferimenti_da_a_distinti`; `trasferimenti_righe.ubicazione_id_da`/`_a` + `chk_…_ubicazioni_distinte` |
| `00_schema/magazzino/20260928-65` | `uq_mag_magazzini_predefinito_emittente` |
| `20_code/vendite/20260928-66` | `fn_ddt_causale_magazzino`, `fn_ddt_merce_da_movimentare`, `fn_ddt_muove_merce` |
| `20_code/script/20260928-67` | `fn_check_ddt_merce` (i motivi fisici, con `valori`) |
| `20_code/script/20260928-68` | `fn_check_ddt_emittibile` accoda la check della merce (corpo dalla doc auto-gen) |
| `20_code/vendite/20260928-69` | `trgfn_ddt_default_magazzino` + `trgfn_ddt_guard_magazzino` e i due trigger |
| `20_code/vendite/20260928-70` | `trgfn_ddt_righe_prelievi_guard` (solo in bozza, salvo l'arrivo; regola del kit) |
| `20_code/vendite/20260928-71` | `trgfn_ddt_guard_transizione`: Regola 3, la **porta del registro** |
| `20_code/vendite/20260928-72` | `trgfn_resi_guard_ddt_consegnato`: niente reso da bolla di trasferimento |
| `20_code/magazzino/20260928-73` | `fn_storna_movimenti_sorgente` (la utility di storno, riservata) |
| `20_code/magazzino/20260928-74` | `fn_posta_ddt(p_ddt_id, p_fase)` (riservata) |
| `20_code/vendite/20260928-75` | **il verbo** `fn_cambia_stato_ddt(p_ddt_id, p_stato)` |
| `20_code/magazzino/20260928-76` | i due guard dei documenti interni montati su `trasferimenti` / `trasferimenti_righe` |
| `20_code/script/20260928-77` | `fn_check_documento_interno_registrabile` + famiglia `TRASFERIMENTO` |
| `20_code/script/20260928-78` | `fn_available_actions_documento_interno` + famiglia `TRASFERIMENTO` |
| `20_code/magazzino/20260928-79` | il verbo `fn_posta_trasferimento` |
| `20_code/magazzino/20260928-80` | i verbi `fn_apri_blocco`, `fn_libera_blocco` |
| `20_code/dbops/20260928-81` | fixture pgTAP `fn_pgtap_crea_ddt` |
| `20_code/dbops/20260928-82` | presidio `dbops.vw_ddt_emessi_senza_scarico` |
| `90_end/20260928-83` | la postura, forward su dev |

**E fuori dai changeSet:**
- `80_data`:
  - `config/sorgenti.csv` (id 21 `DDT_VENDITA_PRELIEVO`);
  - `config/causali_trasporto.csv` (colonna nuova in coda, più la `- column:` e la `columnExists` nel mirror `20260709-11`, che è `runOnChange` + `ANY`);
  - `config/azioni_processo.csv` (37 `emetti_ddt`, 38 `blocca_merce`; descrizione di 36 allargata);
  - `config/codici_errore.csv` e `messaggi_errore.csv`: dieci codici, messaggi `it` con id 1144-1153;
  - `dbops/presidi.csv`;
  - `dbops/fk_index_policy.csv`: undici FK, tutte `consentito = false`, e `ddt_riga_id` è coperta dal prefisso dell'`UNIQUE`.
- Postura nelle tre sedi: loop `90_end/ci_apply/20260205-41` (`movimenti_attesi` da `v_tabelle_senza_delete`, che resta vuota, a `v_tabelle_sola_lettura_app`; `fn_posta_ddt` e `fn_storna_movimenti_sorgente` in `v_fn_riservate`) e `scripts/sql/provision_db_roles.sql`.
- pgTAP **nuovi**:
  - `magazzino/test-ddt-scarico-v1` (16);
  - `magazzino/test-ddt-trasferimento-v1` (13);
  - `vendite/test-ddt-magazzino-testata-v1` (9);
  - `magazzino/test-fn-posta-trasferimento-v1` (10);
  - `magazzino/test-blocco-manuale-e-porta-lotto3-v1` (14).
- pgTAP **aggiornati**:
  - `test-fn-posta-rettifica-v1` (il blocco dal verbo);
  - `test-vw-disponibilita-v1` (blocchi dai verbi, 7 → 6);
  - `test-movimenti-attesi-forma-v1`: passa a `pgtap-runner: owner`, perché il suo soggetto (i CHECK) l'app non lo raggiunge più, e prende l'ex test 3 (15);
  - `test-porta-ledger-v1` (test 3: attesi in sola lettura);
  - `script/test-rubinetto-primo-motivo-v1` (da 26 a 29).

## 4-ter. ✅ La prova pre-apply — 2026-09-28, su dbdev, transazione annullata

> ⚠️ **Da owner** (`titodb`), come ogni prova pre-apply
> (la corsa come app arriva solo dopo l'apply, dal runner): la RLS non c'è e i
> privilegi dell'app non si esercitano. L'SQL è **estratto** dagli YAML
> (`changes[].sql.sql`), mai riscritto; i seed sono simulati **leggendo le righe
> nuove dei CSV**. Niente è stato applicato: ogni file chiude in `ROLLBACK`.

| Che cosa | Esito |
| --- | --- |
| i 24 changeSet, in ordine di NN, in una transazione | ✅ compilano |
| `plpgsql_check` sulle 14 funzioni nuove o cambiate | ✅ zero errori; tre avvisi «STABLE con PERFORM volatile» **già esistenti** nelle due funzioni dei documenti interni |
| pgTAP del lotto: scarico 16/16, trasferimento DDT 13/13, testata 9/9, trasferimento interno 10/10, forma degli attesi 15/15, disponibilità 6/6, rettifica 6/6 | ✅ |
| `test-blocco-manuale-e-porta-lotto3-v1` 13/14, `test-porta-ledger-v1` 14/18 | ⚠️ rossi **solo** le asserzioni di comportamento del privilegio (`42501` atteso): da owner il rifiuto non c'è. Verdi come app, **da confermare col runner** |
| regressione su 16 pgTAP esistenti toccati (bolla, resi, capability, sorgenti, vincoli del ledger, orfani, rubinetto, riferimenti morti) | ✅ tutti verdi, salvo il test 16 di `reason-catch-all`, che è **rosso da owner per costruzione** (scope) |

**Che cosa la prova NON copre**:
- la corsa come app, con la RLS;
- il database ricostruito da zero (CI);
- il mirror del CSV risvegliato davvero dall'apply;
- `check_i18n_keys` e il guardrail dei codici del backend, che aspettano le richieste di §6.

## 5-bis. Il censimento dei pgTAP — 2026-09-28

> Letto sui file di `db/pgtap/`. È una lettura di **struttura** (chi nomina che
> cosa), non una misura sui dati.

| Che cosa cambia | pgTAP che lo nominano | Effetto |
| --- | --- | --- |
| `UPDATE` diretto dello stato della bolla | **135 istruzioni in 44 file** (quasi tutte preparazione: portano una bolla a `EMESSO`/`SPEDITO`/`CONSEGNATO` per provare resi, partite merce, cruscotti, push) | ✅ **nessuno**, per l'affinamento di D-L3-e: le loro bolle non muovono merce (articoli non gestiti, `magazzino_id` nullo). ⚠️ Da confermare col runner: è il primo giro del Lotto 3 |
| i motivi di `fn_check_ddt_emittibile` e la capability della bolla | 11 file: `script/test-fn-check-ddt-emittibile-v1`, `-available-actions-requires-righe-v1`, `-capability-motivi-e-nessuna-azione-v1`, `-capability-annulla-aspetto-e-stato-leggibile-v1`, `-fn-available-actions-ddt-reason-catch-all-v1`, `-fn-available-actions-pdf-v1`, `-fn-check-prezzi-autorizzati-v1`, `dbops/test-punti-canale-campo-v1`, `vendite/test-ddt-componenti-senza-prezzo-v1`, `-ddt-read-side-v1`, `-fn-genera-ddt-riconsegna-eredita-v1` | i motivi nuovi scattano **solo** su bolle che muovono merce: le fixture di oggi non li producono. ⚠️ Chi conta **tutti** i motivi o li confronta per uguaglianza va riletto |
| `ddt_righe.lotto`/`seriale` (D-L3-k) | nessuno | — |
| `magazzini.predefinito` (D-L3-h) | nessuno | ⚠️ le fixture `dbops.fn_pgtap_crea_magazzino` vanno rilette: col nuovo `UNIQUE`, due magazzini predefiniti dello stesso emittente sono rifiutati |
| `chk_mag_trasferimenti_da_a_distinti` | `magazzino/test-movimenti-vincoli-v2`, `test-causali-e-sorgenti-seed-v1`, `rls/test-rls-magazzino-perimetro-v1`, `dbops/test-sorgenti-orfane-v1` | il caso «stesso magazzino» passa da rifiutato ad **ammesso con ubicazioni diverse**: l'asserzione che lo pretendeva rifiutato va riscritta |
| scrittura di `movimenti_attesi` dall'app (D-L3-j) | `magazzino/test-fn-posta-rettifica-v1`, `-fn-scrivi-movimento-disponibilita-v1`, `-movimenti-attesi-forma-v1`, `-vw-disponibilita-v1`, `rls/test-rls-magazzino-perimetro-v1` | l'`INSERT` diretto come app sarà **rifiutato**: le fixture dei blocchi passano da `fn_apri_blocco` |
| un reso da una bolla di trasferimento (D-L3-c) | i 25 file che creano resi | nessuno: le loro bolle hanno causale di vendita |
| catalogo delle sorgenti (riga nuova) | `magazzino/test-causali-e-sorgenti-seed-v1`, `dbops/test-sorgenti-orfane-v1` | se contano le righe, la conta sale di uno |

## 5. I pgTAP — i casi si fabbricano, non si cercano

⛔ Regola zero: ogni ramo si prova **costruendo** il caso. Nessun test itera su
ciò che c'è.

* **scarico**: bolla con due prelievi da due lotti ⇒ due movimenti; somma dei
  prelievi ≠ quantità ⇒ rifiuto all'emissione; articolo non gestito ⇒ nessun
  movimento; kit con padre gestito ⇒ un movimento; kit con padre non gestito ⇒
  un movimento per componente gestito, **senza collisione di identità**
  (D-L3-d);
* **disponibilità**: giacenza insufficiente ⇒ motivo in capability **e**
  rifiuto all'emissione; blocco manuale di un altro ⇒ rifiuto; il proprio
  blocco no;
* **annullo**: `EMESSO → ANNULLATO` ⇒ storno al costo originale, giacenza
  tornata; secondo tentativo ⇒ nessuno storno doppio;
* **trasferimento DDT**: all'emissione solo OUT; al `CONSEGNATO` la IN al costo
  dell'OUT; annullo da `EMESSO` ⇒ storno della sola OUT; arrivo = partenza ⇒
  rifiuto; emittenti diversi ⇒ rifiuto;
* **trasferimento interno**: stesso magazzino, ubicazioni diverse ⇒ coppia
  OUT/IN; stessa ubicazione ⇒ rifiuto;
* **porta**: l'app non esegue le operazioni interne né la utility; un `UPDATE`
  diretto dello stato di una bolla ⇒ rifiuto; il verbo senza azione ⇒ rifiuto;
* **blocco**: aprire/liberare dal verbo, e l'app che scrive `movimenti_attesi`
  direttamente ⇒ rifiuto;
* **i presidi trasversali**: `dbops/test-riferimenti-morti-v1`,
  `script/test-rubinetto-primo-motivo-v1`, la postura dei grant, e ogni pgTAP
  che nomina `fn_check_ddt_emittibile` o lo stato della bolla. ⚠️ Cambiare la
  firma o i motivi di una funzione vuol dire censire i pgTAP che la usano,
  **prima**.

⚠️ **Le lezioni dei lotti precedenti valgono qui intere**: Lotto 1 §5 e Lotto 2
§5 (verde in sessione per ragioni sbagliate, DB da zero ≠ dbdev, runner come
app, `MARK_RAN`). Questo lotto tocca per la prima volta **`vendite`**, che ha
molti più pgTAP: il censimento dei test sui DDT va fatto prima di scrivere.

---

## 6. Richieste a BE/FE — nello stesso giro di PR

| # | Richiesta | Perché |
| --- | --- | --- |
| **R-1** | ogni cambio di stato della bolla passa da `vendite.fn_cambia_stato_ddt` (niente più `UPDATE` diretto in `ddt_repository.update_stato`) | la porta (D-L3-e): senza, l'emissione è rifiutata |
| **R-2** | il drawer della bolla: magazzino (e arrivo per `TRASFERIMENTO`) sulla testata, griglia dei prelievi sotto la riga, i motivi fisici nella capability «Emetti» | D-L3-a, -b, P-6 |
| **R-3** | i codici nuovi coi ripieghi e le chiavi i18n — **codici**: `E_DDT_MAGAZZINO_OBBLIGATORIO`, `E_DDT_PRELIEVI_INCOMPLETI`, `E_DDT_MAGAZZINO_INCOERENTE`, `E_DDT_MAGAZZINO_IMMUTABILE`, `E_DDT_STATO_SOLO_DA_VERBO` (TECNICO), `E_DDT_PRELIEVO_INCOERENTE`, `E_RESO_DA_DDT_TRASFERIMENTO`, `E_MAG_BLOCCO_NON_TROVATO`, `E_MAG_BLOCCO_GIA_CHIUSO`, `E_MAG_TRASFERIMENTO_STESSA_POSIZIONE`; **`reason_key`**: `vendite.ddt.azione_reason.{magazzino_mancante, magazzino_arrivo_mancante, prelievi_incompleti, merce_non_prelevabile, merce_non_disponibile}` | la CI (`check_i18n_keys`, guardrail dei codici) |
| **R-4** | le due azioni nuove (`emetti_ddt`, `blocca_merce`) nell'editor profili | D-L3-e, -j |
| **R-5** | aprire e liberare un blocco dalla scheda di disponibilità | D-L3-j |

---

## 7. Che cosa NON entra, e dove sta

| Cosa | Dove | Perché non qui |
| --- | --- | --- |
| il **carico da reso cliente** | 3-bis, subito dopo (D-L3-i): [brief-db-magazzino-lotto-3-bis-carico-da-reso](brief-db-magazzino-lotto-3-bis-carico-da-reso.md) | il reso non sa dove né quando rientra la merce |
| la **merce presso terzi** (conto visione, riparazione, conto lavoro) | decisione a sé (D-L3-g) | è una domanda di proprietà |
| gli **eventi asset** | lotto suo (D-L2-l) | un documento in più |
| la **ricezione acquisti** e il reso a fornitore | Lotto 4 | documento nuovo, e la seconda occorrenza dei prelievi |
| le colonne **impegnata / potenziale / in arrivo** | dopo il satellite D-17 | la soglia dell'impegno è una riga sola per due cicli |
| la tabella ponte **causale ↔ sorgente** | D-L2-i | nessun scrittore riceve ancora la causale da fuori |
| la vista per il **portale** | M-6, senza lotto | — |
| gli **UNIQUE parziali vecchi** sulle testate di magazzino (solo ramo `uid`) | da decidere (analisi aggancio §8, D-2) | non li tocca questo lotto |
| l'apply, i pgTAP col runner, il commit | Tid | non sono autonomi |

---

## 8. Riferimenti

- Le decisioni: [analisi carico e scarico](../work-in-progress/analisi-db-magazzino-carico-e-scarico.md)
  (§5-bis primitiva, §6 identità, §7-bis blocco, §7-quinquies storno, §8
  lotti), [analisi aggancio](../work-in-progress/analisi-db-magazzino-aggancio-documento-e-produzione.md)
  (§8-quater), [Lotto 1](brief-db-magazzino-lotto-1-terreno-vuoto.md),
  [Lotto 2](brief-db-magazzino-lotto-2-motore.md) (§3 D-L2-g,
  D-L2-h; §9), [verbi con permesso](brief-db-magazzino-verbi-con-permesso.md),
  [permesso nel verbo](brief-db-permesso-nel-verbo-di-scrittura.md) (D-1 → D-5).
- Le forme da copiare: il verbo → `magazzino.fn_posta_inventario` (DEFINER,
  `fn_guard_azione`, GUC `POSTED`, perimetro nella `WHERE`); la conferma che
  parla → `script.fn_check_ddt_emittibile` + `fn_raise_primo_motivo_se_presente`;
  l'immutabilità fuori da bozza → `trgfn_ddt_guard_causale_immutabile`; il
  satellite in bozza → `trgfn_doc_righe_lock_fuori_bozza`; la postura →
  `90_end/ci_apply/20260205-41` + `90_end/20260924-42`.

---

## 9. Registro

| Data | Cosa |
| --- | --- |
| 2026-09-26 | Prima stesura. ✅ **Tre decisioni di Tid**: magazzino sulla **testata** della bolla (D-L3-a), **tabella figlia dei prelievi** (D-L3-b), entrata del trasferimento al **`CONSEGNATO`** (D-L3-c). Emerse scrivendo, e aperte con una raccomandazione: la sorgente del movimento è il **prelievo**, perché l'identità non contiene l'articolo e i componenti di un kit collidono (D-L3-d); il cambio di stato della bolla diventa un **verbo** con GUC-porta, perché oggi il BE fa un `UPDATE` diretto (D-L3-e); la regola del kit (D-L3-f); la mappatura **causale di trasporto → causale di magazzino**, con la merce presso terzi fuori (D-L3-g); il magazzino **predefinito** unico per emittente (D-L3-h); il **reso** del cliente in un 3-bis subito dopo (D-L3-i); i due **verbi del blocco** con un'azione propria (D-L3-j); il ritiro di `ddt_righe.lotto`/`seriale`, senza lettori (D-L3-k) |
| 2026-09-28 | ✅ **Sei decisioni di Tid, tutte sulla raccomandazione del brief**: D-L3-d (sorgente = **prelievo**, nuova sorgente `DDT_VENDITA_PRELIEVO`), D-L3-e (verbo **`vendite.fn_cambia_stato_ddt`** con GUC-porta, azione **`emetti_ddt`**), D-L3-f (il kit muove ciò che è gestito, al livello più alto, mai entrambi), D-L3-h (`UNIQUE … WHERE predefinito` e default sulla bolla), D-L3-j (`fn_apri_blocco`/`fn_libera_blocco`, azione **`blocca_merce`**, l'app perde la scrittura su `movimenti_attesi`), D-L3-k (`DROP` di `ddt_righe.lotto`/`seriale`, lettori ricensiti al changeSet). ⏸️ Restano **D-L3-g** e **D-L3-i** |
| 2026-09-28 | ✅ **Le ultime due decisioni di Tid, sulla raccomandazione**: D-L3-g (`config.causali_trasporto.causale_magazzino_id` nullable: `VENDITA`/`OMAGGIO`/`CAMPIONATURA` → `SCARICO_VEN`, `TRASFERIMENTO` → `TRASF_OUT`/`TRASF_IN`; `CONTO_VISIONE`/`RIPARAZIONE`/`CONTO_LAVORO` **non muovono** — merce presso terzi, decisione a sé, buco dichiarato; `RESO` a fornitore col Lotto 4) e D-L3-i (**B**: il reso del cliente in un **3-bis subito dopo**; fino ad allora un reso confermato non ricarica la giacenza, dichiarato). 🟢 **Tutte le undici decisioni prese**: si possono scrivere i changeSet |
| 2026-09-28 | 🔍 **Censimento dei pgTAP (§5-bis)**: 135 `UPDATE` diretti dello stato della bolla in 44 file. ✅ **Tid affina D-L3-e**: la porta vale **solo** sui passaggi che toccano il registro, e solo per le bolle che muovono merce davvero. Il registro resta protetto per intero, i 44 pgTAP di preparazione non si toccano, e il permesso sulle bolle senza merce resta al BE come oggi (limite dichiarato). Gli altri effetti del censimento: 11 test dei motivi di emissione da rileggere, 4 sul CHECK dei trasferimenti, 5 sulle scritture di `movimenti_attesi` |
| 2026-09-28 (sera) | ✅ **Scritto, non applicato.** Ventiquattro changeSet `20260928-60 → -83`, i seed, la postura nelle tre sedi, cinque pgTAP nuovi e sei aggiornati (§4-bis). Forme precisate scrivendo: tre funzioni piccole di `vendite` sulla **riga** della bolla (kit, prelievo automatico, porta); i motivi fisici in `script.fn_check_ddt_merce` perché portano i `valori`; un solo `fn_posta_ddt` con la fase; la colonna della mappatura sul `codice_interno` della causale (§6b); `fn_conferma_reso`/`fn_annulla_reso` fuori dalla porta. ✅ **Prova pre-apply su dbdev in transazione annullata** (§4-ter): compila, `plpgsql_check` pulito, pgTAP del lotto verdi salvo le asserzioni di privilegio (verdi solo come app), nessuna regressione su 16 file esistenti. ⏸️ La vista di **lettura** della merce in viaggio non è scritta (P-13.2): nasce col suo lettore. ⏳ Tid: apply, runner come app, R-1…R-5 |
| 2026-09-28 (notte) | 🔴 **Primo apply di Tid fermo in `80_data`** su `20260709-11` (mirror delle causali di trasporto): la cella vuota di `causale_magazzino` e' entrata come stringa `''`, non come `NULL` — il mirror aveva `nullValue: ""`, che su una colonna `STRING` non vale — e la FK verso `magazzino.causali` l'ha rifiutata. ⚠️ La prova pre-apply (§4-ter) **non poteva vederlo**: simulava il seed leggendo il CSV in Python, dove la cella vuota diventava `NULL`; il loader vero non lo fa. E' la trappola di linee-guida-sql §11.7. **Corretto**: token `NULL` nelle quattro celle e `nullValue: "NULL"` nel mirror, come `sorgenti.csv`. Applicati a quel punto `20260928-60 → -82`; restano il mirror e `90_end/20260928-83`, al prossimo migrate |
| 2026-09-28 (notte) | 🔴 **Runner di Tid:** `vendite/test-ddt-righe-componenti-v1` test 12, trigger su `ddt_righe_componenti` 14 invece di 13. E' il `block_deact` che `ci_apply` genera per `vendite.ddt_righe_prelievi`, figlia via `ddt_riga_componente_id`: voluto (un componente con prelievi non si spegne). Aggiornato il numero esatto, con la ragione accanto. Censiti gli altri pgTAP che guardano i trigger delle tabelle padre dei prelievi e dei magazzini: nessun altro li **conta** — cercano per funzione o per nome |
| 2026-09-28 (notte) | ✅ **Applicato e verde** (Tid): `20260928-60 → -83` `EXECUTED`, mirror `20260709-11` `RERAN` col token `NULL`, suite pgTAP verde col runner come app. Verificati sul catalogo la mappatura delle causali di trasporto (`NULL` veri su conto visione, reso, riparazione e conto lavoro) e la postura (niente `INSERT` su `movimenti_attesi`, niente `EXECUTE` su `fn_posta_ddt`). Il lato DB del Lotto 3 e' consegnato; restano le richieste a BE/FE (§6) e la CI da zero |
| 2026-10-01 | 🧭 **Il registro di magazzino è un servizio dell'anello 2** (Tid): la dipendenza `vendite` → `magazzino` è verso l'interno; il verso inverso — `magazzino.fn_posta_ddt` nello schema `magazzino`, che legge le tabelle di `vendite` — si sposta in `vendite`. [brief-db-magazzino-registro-anello-interno](brief-db-magazzino-registro-anello-interno.md) — scritto lo stesso giorno: `vendite.fn_posta_ddt` (`20261001-18`), la `magazzino.fn_posta_ddt` ritirata in `90_end/20261001-24`, ⏳ da applicare |
| 2026-09-29 | 📝 **Debito documentale chiuso** col giro del 3-bis: `magazzino/manual/movimenti_attesi` (i verbi del blocco, l'app in sola lettura) e `magazzino/manual/magazzini` (il predefinito unico per emittente e il default della bolla) |
| 2026-09-29 | 🔴 **Due registri non censiti dal Lotto 3**, visti dal runner di Tid durante il 3-bis: `vendite.ddt_righe_prelievi` non era in `dbops.storico_scope_policy` (riga 123 aggiunta al CSV), e le esenzioni `movimenti_attesi.stato = CHIUSA` e `trasferimenti.stato_trasferimento = POSTED` di `dbops.stati_check_dichiarazioni` erano diventate debiti estinti (`fn_libera_blocco`, `fn_posta_trasferimento`): tolte dal CSV e da `80_data/changelog/20260929-03`. Dettaglio nel [brief del 3-bis](brief-db-magazzino-lotto-3-bis-carico-da-reso.md) |
| 2026-10-14 | ✅ **Chiuso e archiviato** (sessione BE, su richiesta di Tid). I residui (CI da zero, vista della merce in viaggio P-13.2) passano al §5 del [piano BE/FE](../work-in-progress/piano-be-fe-magazzino-lotto-3.md); il collaudo a video e' [collaudo-in-app-magazzino-bolla-e-reso](../work-in-progress/collaudo-in-app-magazzino-bolla-e-reso.md) |
