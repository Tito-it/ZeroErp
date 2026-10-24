# Guida — Gestione Preventivi vendita

> **Ultimo aggiornamento**: 25 ottobre 2026
>
> **Destinatari**: analisti funzionali, sviluppatori backend/frontend, DBA.
>
> **Vedi anche** — schemi DB:
>
> * [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) / [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe) / [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti)
> * [vendite.preventivi_indirizzi](/dbzero/vendite/tabelle/preventivi_indirizzi)
> * [vendite.vw_preventivi](/dbzero/vendite/manual/vw_preventivi) / [vendite.vw_preventivi_lista](/dbzero/vendite/manual/vw_preventivi_lista)
> * [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi) / [config.transizioni_stati_preventivi](/dbzero/config/tabelle/transizioni_stati_preventivi)
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM versionata immutabile
>
> **Vedi anche** — funzioni DB:
>
> * [vendite.fn_crea_revisione_preventivo](/dbzero/vendite/funzioni/fn_crea_revisione_preventivo) — crea nuova revisione da EMESSO
> * [vendite.fn_push_preventivo_a_ordine](/dbzero/vendite/manual/fn_push_preventivo_a_ordine) — smistamento delle righe merce verso un ordine; porta avanti la data di consegna richiesta
> * [vendite.fn_preventivo_riga_componenti_init](/dbzero/vendite/funzioni/fn_preventivo_riga_componenti_init) — popola componenti BoM su riga padre composito
> * [vendite.fn_preventivo_riga_componenti_preview](/dbzero/vendite/funzioni/fn_preventivo_riga_componenti_preview) — read-only, suggerimento prezzi pre-save
> * [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver pricing bundle-aware
> * [script.fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo) — azioni disponibili sullo stato corrente
>
> **Vedi anche** — API e service backend:
>
> * [API Preventivi](/backend/vendite/manual/api_preventivi)
> * [API Pricing (resolver + limiti L2)](/backend/vendite/manual/api_pricing)
> * [API Approvazioni prezzo (workflow L3)](/backend/vendite/manual/api_approvazioni_prezzo)
>
> **Vedi anche** — guide correlate:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — **le regole comuni a tutti i documenti**: nascita, cambio di stato, permesso sul passaggio, emissione, annullo
> * [Gestione Listini e Pricing v5](/guide/gestione-listini)
> * [Fatturazione end-to-end](/guide/fatturazione) — il push commessa attiva la pipeline fatturazione
> * [Documenti e stampe](/guide/documenti-e-stampe) — generazione PDF preventivo
> * [Gestione Pratiche](/guide/gestione-pratiche) — flusso approvazione prezzo L3
> * [Modello componenti BoM](/dev/manual/modello-componenti-bom)

---

## 1. Cosa è un preventivo

Un preventivo è l'**offerta commerciale** che l'azienda emette verso un cliente per
una specifica fornitura. Risponde alla domanda: *"Quanto costerebbe questo cliente
se accettasse questa configurazione di articoli oggi?"*

Caratteristiche di base:

- è intestato a un **billing account** (cliente) e a una **utility** (servizio:
  Gas, Energia, Idrico, oppure "Base" per commercio)
- raccoglie **righe** (articoli con quantità, UoM, prezzo) e produce un totale
- ha un **ciclo di vita** con stati che vanno da bozza a emesso, fino ad
  accettato o rifiutato
- può essere **revisionato** un numero qualsiasi di volte mantenendo lo stesso
  numero documento
- quando accettato, viene **spinto in commessa** che a sua volta alimenta il
  ciclo di fatturazione

Il numero documento è auto-generato (prefisso `PRV`) e non modificabile.

---

## 2. Le entità in gioco

### 2.1 Testata `preventivi`

Contiene il contesto commerciale del preventivo:

- **chi** (`billing_account_id`, `istanza_utility_id`)
- **per cosa** (`utility_id`)
- **quando** (`data` di emissione, `validita_dal`/`validita_al` dell'offerta)
- **chi emette** (`emittente_fiscale_id`)
- **come fattura** (`valuta_id`, `termine_pagamento_id`)
- **stato** corrente (`stato_doc_preventivo_id`)
- **revisione** (`numero` + `rev`, l'attivazione è derivata — vedi §4)
- **totali** (`totale_imponibile`, `totale_iva`, `totale_documento`) ricalcolati
  da trigger sulle righe

> **`istanza_utility_id` è obbligatoria**: se non viene passata, il sistema la
> deriva automaticamente dal billing account; la coerenza utility/istanza è
> validata (errore `E_PREV_UTILITY_ISTANZA_INCOERENTE`). Anche
> `emittente_fiscale_id`, se assente, è valorizzato di default dal trigger DB
> sull'utente corrente.
>
> ⚠️ **Il `termine_pagamento_id` decide anche quante fatture nascono.** Le
> condizioni di pagamento entrano nei criteri con cui il lavoro si raggruppa a
> valle: un preventivo con un termine diverso **apre una commessa propria** e
> produce una **fattura separata** da quelle degli altri documenti dello stesso
> cliente. È l'unico esito corretto — una fattura sola non potrebbe portare due
> scadenzari — ma va saputo quando ci si aspetta un documento solo:
> [Termini di pagamento §4](/guide/termini-di-pagamento).
>
> **`fatturazione_immediata` e `competenza_mese` non sono campi della bozza** ma
> **dati di processo** richiesti al momento dell'**accettazione** (EMESSO →
> ACCETTATO), tramite un dialog dedicato: `fatturazione_immediata` è obbligatoria;
> `competenza_mese` è obbligatoria solo se la fatturazione **non** è immediata (se
> immediata, la competenza è forzata al primo del mese corrente).

I totali non si scrivono dall'API: sono il riassunto delle righe e vengono
mantenuti coerenti dal database.

### 2.2 Righe `preventivi_righe`

Ogni riga rappresenta una voce dell'offerta:

- articolo + UoM operativa + quantità
- prezzo unitario, sconto percentuale, IVA
- ordine di presentazione
- **data di consegna richiesta dal cliente** (`data_consegna_richiesta_cliente`),
  facoltativa — vedi sotto

#### La quantità e l'unità di misura operativa

L'operatore inserisce la quantità **nell'unità di misura che ha scelto** (la "UoM
operativa": per esempio *scatole*, anche se l'articolo a magazzino è contato in
*pezzi*). È il sistema, non l'operatore, a tradurla nell'unità di misura "base"
usata per i calcoli interni: se una scatola contiene 6 pezzi e si inseriscono 2
scatole, il sistema registra automaticamente 12 pezzi.

In pratica:

- l'operatore vede e digita **2** (scatole) — è il dato di partenza;
- il sistema calcola e salva **12** (pezzi) — è il valore derivato;
- il fattore di conversione (6) viene "fotografato" sulla riga al momento
  dell'inserimento, così resta stabile anche se in futuro cambia a catalogo.

La quantità **può essere negativa** (per gestire resi o storni); non può essere
zero. Questa conversione funziona allo stesso identico modo su preventivi, offerte
e contratti.

Il prezzo unitario può venire dal **resolver pricing** (riempito automaticamente
al cambio articolo/UoM) oppure essere inserito manualmente dall'operatore, con
controlli L1/L2/L3 di autorizzazione che vedremo in §6.

Per gli articoli **compositi** (kit, bundle) la riga è solo la "testata" del
gruppo: i prezzi reali stanno nei componenti BoM (§5).

#### La data di consegna richiesta

Sulla riga di preventivo c'è **solo la richiesta** del cliente
(`data_consegna_richiesta_cliente`), non una data confermata: su un preventivo
non c'è ancora niente da confermare. È facoltativa, si scrive con la riga (un
selettore di data nel form) e compare nella tabella delle righe.

⭐ **Viaggia con la riga verso l'ordine**: quando la riga merce viene smistata
(§8), `fn_push_preventivo_a_ordine` la copia sulla riga d'ordine come richiesta
del cliente, e lì la promessa (`data_consegna_confermata`) nasce vuota. Vedi
[Gestione Ordini §3.5](/guide/gestione-ordini).

⛔ **Non viene prima del preventivo.** Una data richiesta anteriore alla data del
preventivo si rifiuta, dal form di riga e da «Aggiorna date di consegna»; la
stessa data del preventivo e il campo vuoto vanno bene. Al contrario, la data del
preventivo non si sposta *dopo* la richiesta di una riga attiva.

**Nella revisione e nello smistamento.** Anche `fn_crea_revisione_preventivo`
copia la data sulla riga della revisione nuova. La revisione e l'ordine nascono
però con la data di oggi: una richiesta **già passata** arriva vuota sulla
copia, e si riscrive lì (la copia è in bozza). La revisione precedente e il
preventivo smistato conservano la loro.

**In blocco.** Finché il preventivo è in `DRAFT`, l'azione **«Aggiorna date di
consegna»** della barra del drawer scrive la stessa data richiesta su più righe:
*solo quelle senza data*, oppure *tutte*, che sovrascrive anche le date già
scritte e chiede prima conferma col numero di righe. È anche il modo rapido di
rimettere la data sulle righe di una revisione nuova. Fuori bozza l'azione non
compare. Una riga col prezzo in attesa di approvazione non si modifica, e ferma
il gesto per intero: nessuna riga cambia. Lo stesso gesto, sull'ordine, in
[Gestione Ordini §3.5](/guide/gestione-ordini).

#### Quali articoli possono stare su un preventivo

Sul preventivo puoi mettere **merce** e **servizi una tantum**. **Non** puoi
inserire articoli a **servizio ricorrente** (canone/abbonamento): nella ricerca
dell'articolo compaiono in grigio, col motivo sotto, e non si possono scegliere; il
motivo ti invita a usare l'**offerta commerciale**. Lo stesso vale per un articolo
che si vende solo dentro un kit e per un kit senza componenti. La ricerca e il
rifiuto al salvataggio usano la stessa regola. Il motivo è semplice — la ricorrenza ha un suo ciclo di vita
([offerta → contratto → fatturazione periodica](gestione-offerte-commerciali.md))
che non passa dal preventivo. Ogni articolo porta con sé questa "natura" dal
catalogo, e l'operatore non può cambiarla sulla riga.

> **Come funziona sotto il cofano.** Ogni articolo ha una *natura di vendita*
> (`catalogo.articoli.natura_vendita_id` → `config.nature_vendita`) con una
> *destinazione*: `MERCE → ordine`, `SERVIZIO_UNA_TANTUM → commessa`,
> `SERVIZIO_RICORRENTE → contratto`. Quando aggiungi una riga, il sistema copia e
> **congela** la natura dall'articolo sulla riga
> ([`script.trgfn_righe_natura_vendita`](/dbzero/script/manual/trgfn_righe_natura_vendita)).
> Se la destinazione è `CONTRATTO`, l'inserimento è bloccato subito con l'errore
> `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`; lo stesso vale per un articolo «solo
> componente», che si vende solo dentro il suo kit, e per un kit senza componenti
> (dal 2026-10-14), che va prima completato. Le regole stanno in un controllo
> unico ([`script.fn_check_articolo_riga`](/dbzero/script/manual/fn_check_articolo_riga)),
> sono *data-driven* (valgono per qualunque natura mappata a contratto) e scattano
> all'inserimento, non alla conferma. Le destinazioni operative del preventivo
> sono quindi solo **ordine** e **commessa**.

### 2.3 Componenti BoM `preventivi_righe_componenti`

Quando una riga punta a un articolo `is_composito = TRUE`, il sistema crea
automaticamente un record per ogni **componente** definito nella BoM
dell'articolo. Il prezzo del padre è la **somma pesata** dei prezzi figli, mai
inserita a mano.

I componenti BoM portano:

- riferimento al componente del catalogo + UoM + quantità (= padre × `coeff_qta`)
- prezzo unitario (modificabile dall'operatore con autorizzazioni)
- snapshot del coefficiente quantità al momento della creazione
- origine prezzo (PROMO / CONTRATTO_OVERRIDE / CONTRATTO_LISTINO / CATEGORIA / MANUALE)
- stato approvazione prezzo (L3)

La struttura del bundle (quali componenti, in che quantità relative) è
**immutabile per documento**: l'operatore può cambiare i prezzi, non la
composizione. Vedi [modello componenti BoM](/dev/manual/modello-componenti-bom)
per il dettaglio.

### 2.4 Indirizzi `preventivi_indirizzi`

Snapshot multi-tipo (consegna, fatturazione, ecc.) congelati alla creazione.
Sono **autonomi**: una modifica all'indirizzo del cliente in anagrafica non
retroagisce sul preventivo già emesso. La revisione li copia 1:1 nella nuova rev.

### 2.5 Documenti generati

Quando il preventivo viene stampato/inviato, il sistema produce un PDF tramite
il motore documentale parametrico:

- in stato **DRAFT** la stampa è solo **anteprima** (PDF temporaneo, niente
  persistenza)
- al passaggio **DRAFT → EMESSO** il PDF viene generato e salvato come
  documento ufficiale collegato al preventivo
- da EMESSO in poi le ristampe restituiscono il documento salvato (non
  rigenerato), per preservare il layout storico

Vedi [documenti e stampe](/guide/documenti-e-stampe) per i template e il motore.

---

## 3. Ciclo di vita e stati

⭐ Le regole comuni a tutti i documenti — in che stato si nasce, chi cambia lo stato, quale permesso chiede un passaggio, l'emissione, l'annullo — stanno nel [modello del documento di vendita](/guide/modello-documento-di-vendita), che al §10 dice anche a che punto è il preventivo rispetto al modello. Qui ci sono gli stati e i passaggi che sono suoi.

### 3.1 Stati e transizioni

Gli stati sono governati da `config.stati_doc_preventivi` e le transizioni
ammesse da `config.transizioni_stati_preventivi`:

| Stato       | Significato                                                 | Modificabile?                     |
| ----------- | ----------------------------------------------------------- | --------------------------------- |
| `DRAFT`     | Bozza in costruzione                                        | Sì: testata, righe, indirizzi     |
| `EMESSO`    | Inviato al cliente, in attesa di risposta                   | No (escluso azioni di stato)      |
| `ACCETTATO` | Cliente ha accettato — pronto per lo smistamento downstream | No                                |
| `EVASO`     | Tutte le righe smistate a ordine/commessa senza residuo     | No (terminale operativo positivo) |
| `RIFIUTATO` | Cliente ha rifiutato — chiusura negativa del numero         | No (terminale)                    |
| `SCADUTO`   | Validità offerta scaduta automaticamente (job notturno)     | No (terminale)                    |
| `ANNULLATO` | Annullamento manuale                                        | No (terminale, **abortito**)      |

Le transizioni manuali permesse:

```text
DRAFT      → EMESSO     (emetti)
DRAFT      → ANNULLATO  (annulla)
EMESSO     → ACCETTATO  (accetta)
EMESSO     → RIFIUTATO  (rifiuta)
EMESSO     → ANNULLATO  (annulla)
ACCETTATO  → ANNULLATO  (annulla)
```

> **Rifiutare non è annullare.** Un preventivo EMESSO che il cliente non vuole si
> **rifiuta** (è il "no" del cliente) o **scade**; l'annullo è la rinuncia di chi
> lo ha emesso. Annullare un preventivo che ha già spinto lavoro in commessa
> chiede una conferma (§3.2).

`EMESSO → SCADUTO` è automatica (job notturno quando supera `validita_al`).
`ACCETTATO ↔ EVASO` è automatica, nei due versi, e la fa il database: il preventivo
è `EVASO` quando non resta residuo su **nessun** ramo, e torna `ACCETTATO` appena uno
dei due ne ha di nuovo (vedi §8); non c'è un pulsante.

Le azioni disponibili in ogni momento sono esposte dal backend tramite
[`fn_available_actions_preventivo`](/dbzero/script/funzioni/fn_available_actions_preventivo)
e arrivano al frontend come array `available_actions`. Le capability derivate
(`can_edit_testata`, `can_edit_righe`, `can_push_commessa`, `can_genera_ordine`,
`can_create_revisione`) governano la disabilitazione dei pulsanti. In stato
ACCETTATO compaiono **due** azioni distinte e simmetriche: `push_commessa` (se
restano righe-servizio da smistare) e `genera_ordine` (se restano righe-merce da
smistare) — vedi §8.

### 3.2 Annullare un preventivo che ha generato altro

* **Il preventivo annullato.** Se ha spinto righe in commessa ancora da emettere,
  annullarlo le annulla. Non succede in silenzio: «Annulla preventivo» apre una
  **finestra di conferma** con le righe di commessa che tornano annullate, e
  l'operatore dichiara quante ne ha viste. Le righe **già emesse** non si
  riaprono: bloccano l'annullo.
* **L'ordine annullato.** Se si annulla un ordine nato dallo smistamento, le righe
  del preventivo che occupava si liberano e si possono ordinare di nuovo; un
  preventivo `EVASO` torna `ACCETTATO` (in automatico, non è un pulsante).
* **La commessa annullata.** Se si annulla la commessa in cui sono finite le righe
  di servizio (con la conferma, vedi
  [Gestione Commesse](/guide/gestione-commesse) §«Annullare una commessa»), le righe
  escono dalla commessa e tornano **da mandare in commessa**; un preventivo `EVASO`
  torna `ACCETTATO` e di nuovo smistabile.

⚠️ **Il preventivo con un ordine vivo non si annulla**: prima l'ordine
(`ORDINE_GIA_GENERATO`). Con righe in una commessa viva **non ancora emesse**, invece,
si annulla con la conferma: è un'eccezione voluta, perché la commessa raccoglie righe
di più documenti, e il blocco costringerebbe ad annullarla tutta (dettaglio nella
guida delle commesse).

#### Il preventivo misto

Ogni riga del preventivo va da una parte sola: la merce nell'ordine, i servizi in
commessa. Il preventivo è `EVASO` quando **nessuna** delle due strade ha un residuo,
e torna `ACCETTATO` appena **una** delle due ne ha di nuovo.

| Cosa si annulla | Il preventivo |
| --- | --- |
| l'ordine | le righe di merce tornano da ordinare, torna `ACCETTATO`; le righe in commessa restano |
| la commessa | le righe di servizio tornano da mandare, torna `ACCETTATO`; l'ordine resta vivo |
| tutti e due, uno dopo l'altro | ognuno riapre la sua parte; `ACCETTATO` una volta sola |
| il preventivo, con un ordine vivo | bloccato: prima l'ordine |
| il preventivo, senza ordine, con righe in commessa non emesse | con la conferma; le righe escono dalla commessa |

⭐ **Si torna indietro un passo alla volta.** Nella catena preventivo → ordine →
commessa, annullare la commessa riapre solo l'ordine: il preventivo non si muove,
perché le sue righe le usa ancora l'ordine.

### 3.3 Stati terminali e stato "abortito"

`config.stati_doc_preventivi` ha un campo `is_abortito` che marca lo stato
**ANNULLATO** come "rinuncia". Tutti gli altri stati terminali (RIFIUTATO,
SCADUTO, ACCETTATO, EVASO) sono conclusioni del documento ma **non rinunce**: il
numero ha trovato un esito definitivo.

Questa distinzione è importante per la logica revisione (§4): solo gli stati
abortiti permettono al predecessore di "riprendere vita".

---

## 4. Revisioni

### 4.1 Cos'è una revisione

Una revisione è una **nuova istanza** dello stesso numero preventivo, con un
contatore `rev` incrementato. Permette di aggiornare l'offerta dopo che il
cliente ha chiesto modifiche, senza perdere lo storico della precedente
proposta.

```text
PRV-0001 rev=0  EMESSO     ← prima offerta inviata
PRV-0001 rev=1  DRAFT      ← revisione in corso (post-creazione)
```

Caratteristiche:

- una revisione si crea **solo da uno stato EMESSO**
- non possono coesistere due revisioni DRAFT per lo stesso numero
- ⚠️ dal 2026-09-24 una revisione **non si crea se un prezzo è in attesa di
  approvazione**: prima serve l'esito del responsabile. La revisione ricopia le
  righe con il loro stato di approvazione, e una riga in attesa ricopiata
  resterebbe legata alla richiesta della versione vecchia, in attesa per
  sempre. Un prezzo **approvato** o **rifiutato** invece si ricopia com'è (il
  rifiutato si corregge sulla revisione). «Crea revisione» resta a video,
  spento con il motivo
- la nuova revisione nasce **DRAFT** e diventa la "rev attiva" del numero
- la rev precedente resta in DB come storico (stato EMESSO conservato)

### 4.2 Cosa viene copiato nella nuova rev

La funzione [`fn_crea_revisione_preventivo`](/dbzero/vendite/funzioni/fn_crea_revisione_preventivo)
copia in transazione atomica:

- testata (campi commerciali + dati cliente)
- righe attive (`preventivi_righe` con `attivo=TRUE` e `quantita > 0`) —
  compresa la **data di consegna richiesta dal cliente**
  (`data_consegna_richiesta_cliente`, dal 2026-09-14): è ciò che il cliente
  ha chiesto, non una promessa nostra, e la rev N+1 la eredita come eredita
  articolo e quantità. ⚠️ Fino a quel giorno la revisione la perdeva: la copia
  nomina le colonne una per una, e una colonna non nominata non passa
- …e comprese le **marche di approvazione prezzo** (`stato_approvazione_prezzo`,
  `pratica_approvazione_prezzo_id`, dal 2026-09-14): un prezzo fuori policy
  approvato o in attesa resta marcato anche sulla rev N+1, e una riga in attesa
  resta congelata — come già per le offerte. Fino a quel giorno la revisione le
  perdeva, per la stessa ragione della data
- componenti BoM (`preventivi_righe_componenti`, con FK rimappata sulle nuove
  righe via `ROW_NUMBER`)
- indirizzi (`preventivi_indirizzi`)

Non viene copiato lo stato (la nuova rev è sempre DRAFT) né il numero documento
generato per la rev precedente (il nuovo rev mantiene lo stesso `numero`).
⚠️ Non viene copiata nemmeno la **data di consegna richiesta** delle righe
(§2.2): nella nuova revisione va reinserita.

### 4.3 Predicato `is_attiva` derivato

ZeroERP non mantiene un flag persistito "questa è la rev attiva": il predicato
è **calcolato dalla view `vw_preventivi`** come:

> "è la rev viva del numero" = "il suo stato **non è abortito** **e** non esiste
> una rev superiore non-abortita per lo stesso numero"

Il termine sul proprio stato garantisce che una revisione
**annullata in cima** alla catena non si dichiari attiva "guardando solo verso
l'alto": senza di esso `is_attiva` non sarebbe univoco (due rev attive per lo
stesso numero) nel caso "rev0 EMESSO + rev1 ANNULLATO".

Conseguenza pratica nei casi limite:

| Sequenza                      | rev N attiva?                               | rev N+1 attiva? |
| ----------------------------- | ------------------------------------------- | --------------- |
| rev 0 EMESSO, rev 1 DRAFT     | no (superseded)                             | sì              |
| rev 0 EMESSO, rev 1 ANNULLATO | **sì** (rev 1 è abortita, non conta)        | no              |
| rev 0 EMESSO, rev 1 RIFIUTATO | no (rev 1 conclude il numero negativamente) | sì              |

Il caso "**revisione annullata rifluisce al predecessore**" è quello tipico
dell'operatore che sbaglia a revisionare: la revisione viene annullata e il
preventivo originale torna disponibile per nuove operazioni (annullamento,
accettazione, ulteriore revisione). Senza ricorrere a interventi manuali.

### 4.4 Filtro lista e storico

La lista preventivi mostra di default solo le rev attive (una per numero).
Esiste un toggle "Mostra storico revisioni" che espone tutte le righe,
incluse quelle annullate o superseded. Il filtro lato API è il parametro
`solo_attiva` (default `true`).

### 4.5 Differenza col modello offerte

Preventivi e offerte gestiscono le revisioni in **due modi diversi**, per una
ragione precisa.

| Aspetto                                                         | **Preventivi**                                                                                        | **Offerte**                                                                                            |
| --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Cosa succede alla versione precedente quando nasce la revisione | **resta EMESSA/viva**; il sistema calcola "qual è la versione valida" senza chiudere la precedente    | passa **subito a SUPERATA** (stato chiuso e definitivo, imposto in automatico)                         |
| Se abbandono/annullo la revisione appena iniziata               | la precedente **torna automaticamente la versione valida**: si può accettarla o revisionarla di nuovo | la precedente **resta chiusa** (SUPERATA): non torna indietro. Per riprovare si fa una nuova revisione |
| Come nasce il concetto di "versione valida"                     | da un **calcolo** (`is_attiva`), non da uno stato dedicato                                            | dallo **stato** (SUPERATA/ANNULLATA = non valida)                                                      |

Il preventivo **è lo stesso documento** (stesso numero, più revisioni) e il flusso
previsto è *"comincio una revisione, ci ripenso, la versione emessa di prima resta
valida"*. Per questo la precedente **non** viene mai chiusa: se annullo la bozza
di revisione, la versione emessa torna da sola quella valida (vedi la tabella dei
casi limite in §4.3). **Non** esiste uno stato "SUPERATO" sui preventivi proprio
perché chiuderebbe la precedente e romperebbe questo ritorno.

L'offerta invece è un **documento a sé** per ogni revisione (OFC-… diversi in
catena): chiudere la precedente non crea problemi, perché se serve si emette una
nuova offerta. Dettaglio nella
[guida offerte §4.3](gestione-offerte-commerciali.md).

Sui cruscotti entrambi i modelli sono corretti: i preventivi escludono le
revisioni non valide tramite `is_attiva`, le offerte escludono la SUPERATA
(è un esito negativo).

---

## 5. Articoli compositi e BoM

### 5.1 Cosa succede quando aggiungi un composito

Inserendo una riga preventivo con articolo `is_composito = TRUE`, il sistema:

1. apre il dialog di **anteprima componenti** che pre-popola i prezzi dei
   figli BoM via [`fn_preventivo_riga_componenti_preview`](/dbzero/vendite/funzioni/fn_preventivo_riga_componenti_preview)
2. l'operatore conferma (oppure modifica i prezzi suggeriti, con controlli
   L1/L2/L3) e salva
3. il backend crea in transazione atomica:
   - una riga padre in `preventivi_righe` con prezzo iniziale 0 (placeholder)
   - N righe figlie in `preventivi_righe_componenti` (una per ogni figlio
     attivo nella BoM valida alla data del preventivo)
4. trigger DB ricalcola il prezzo padre come SUM(figli × `coeff_qta_snapshot`)

Se la BoM del padre non ha figli validi alla data del preventivo, il sistema
solleva `E_DOC_COMPOSITO_BOM_VUOTA` e blocca la creazione della riga (la
configurazione del catalogo è incoerente per la data scelta).

### 5.2 Cosa può modificare l'operatore

Per BoM contratto immutabile:

- ✅ **prezzi unitari** dei componenti, con controlli di autorizzazione
- ✅ **IVA** del componente (deve restare coerente col padre)
- ❌ **non** può aggiungere o rimuovere componenti dalla composizione
- ❌ **non** può cambiare `coeff_qta` (è snapshot immutabile)

Componenti **obbligatori** (definiti nella BoM con `obbligatorio=TRUE`) non
ammettono prezzo zero: il trigger DB rifiuta con
`E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO`. Componenti opzionali ammettono
prezzo zero.

### 5.3 Esposizione in fattura

Ogni componente porta la sua **esposizione in fattura**, decisa nella distinta
base dell'articolo (il preventivo la mostra, non la cambia). Dice cosa vedrà il
cliente quando il kit arriverà in fattura:

- **Nascosto** → il componente non compare; il suo prezzo è già dentro il prezzo
  del kit
- **Descrittivo** → compare come riga sotto il kit, **senza prezzo**; il suo
  prezzo è già dentro il prezzo del kit
- **Valorizzato** → compare come riga sotto il kit **con il suo prezzo e il suo
  importo**, che non vengono più sommati al prezzo del kit

L'esposizione è solo di **presentazione finale**: non incide sulla composizione
del preventivo né sui calcoli, e il totale del documento è lo stesso in tutti e
tre i casi. Le regole complete sono nella
[guida fatturazione](/guide/fatturazione) (§ *Come si espone un kit*). Fino al
2026-10-01 era un sì/no («esposto in fattura»: no = nascosto, sì = descrittivo).

---

## 6. Pricing applicato

### 6.1 Resolver

Quando l'operatore seleziona articolo + UoM, il backend chiama il
[resolver pricing v5](/guide/gestione-listini#3-resolver-i-3-stadi-in-dettaglio)
che valuta in sequenza promo → contratto → categoria/listino e restituisce un
prezzo candidato + origine. Il frontend pre-compila il campo prezzo nel form.

Per articoli compositi il resolver è **bundle-aware**: passa il padre come
contesto (`p_articolo_padre_contesto`), così se esiste un listino bundle
dedicato (`listini_righe_componenti`) i figli ricevono prezzi specifici per
quel bundle, altrimenti fallback al pricing standalone.

### 6.2 Controlli L1 / L2 / L3

L'operatore può modificare il prezzo proposto dal resolver. Le modifiche
passano per tre livelli di autorizzazione, gestiti dal motore L1/L2/L3 dei
limiti pricing:

- **L1 — Override manuale**: il flag `prezzo_override_manuale` deve essere
  abilitato sul profilo operatore
- **L2 — Limiti sconto/maggiorazione**: la deviazione rispetto al prezzo
  resolver non può eccedere le soglie configurate (es. sconto max 15%). Oltre
  il limite, il save è bloccato salvo richiesta approvazione
- **L3 — Workflow approvazione**: l'operatore può chiedere autorizzazione al
  superiore tramite una **pratica APPROVAZIONE_PREZZO** dedicata. La riga
  resta in stato `PENDING` finché approvata o rifiutata

Vedi [API Approvazioni prezzo](/backend/vendite/manual/api_approvazioni_prezzo)
e [gestione pratiche](/guide/gestione-pratiche) per il workflow completo.

### 6.3 Snapshot resolver

Ogni riga (e ogni componente BoM) salva nel campo `prezzo_resolver_context` un
**audit JSONB** con i valori che hanno determinato il pricing: origine, listino
applicato, contratto/promo riferiti, eventuale override manuale. Questo
snapshot sopravvive a future modifiche del listino e permette di ricostruire
"perché in quel momento il prezzo era X".

### 6.4 Preventivo congelato da pricing pendente

**La regola (database, dal 2026-09-24):** un prezzo che nessuno ha autorizzato non
esce dalla bozza. Se almeno una riga **attiva** o un componente BoM **attivo** ha
il prezzo in attesa di approvazione (**PENDING**) o **rifiutato** (**REJECTED**),
il preventivo:

- **non può essere emesso** (DRAFT → EMESSO);
- **non può essere accettato** (→ ACCETTATO);
- **può sempre essere annullato**: l'annullamento è la via d'uscita dell'operatore.

Il database solleva `E_DOC_PREZZO_PENDENTE` (prezzi in attesa) o
`E_DOC_PREZZO_RIFIUTATO` (prezzi rifiutati); se ci sono entrambi, esce prima
l'attesa. Gli stessi motivi spengono i pulsanti **Emetti** e **Accetta** con il
loro tooltip, perché bottone e database leggono la stessa funzione:
[script.fn_check_prezzi_autorizzati](/dbzero/script/funzioni/fn_check_prezzi_autorizzati),
chiamata da [script.fn_check_preventivo_emettibile](/dbzero/script/funzioni/fn_check_preventivo_emettibile)
per l'emissione e da [vendite.trgfn_preventivi_guard_transizione](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione)
per l'accettazione.

Per rimediare, l'operatore attende l'esito della pratica oppure corregge o
toglie la riga: riportando il prezzo a un valore accettabile lo stato di
approvazione si azzera e il preventivo torna emettibile.

La singola riga **PENDING** resta non modificabile finché la pratica è aperta
(guard per riga); la testata e le altre righe restano modificabili in DRAFT.

> ⚠️ **Il backend, oggi, spegne di più.** Fino al ritiro del debito dichiarato in
> `preventivi_service.get_preventivo` (richiesta al team backend del brief
> `brief-db-preventivi-congelamento-pricing`, §6), il backend riscrive ancora a video
> le azioni e mette la testata in sola lettura quando c'è un prezzo in attesa o
> rifiutato. La regola vera è quella del database, descritta sopra.

---

## 7. Workflow end-to-end

### 7.1 Flusso tipico

```text
   ┌──────────────────┐
   │  Nuovo preventivo │
   │  (Nuovo cliente   │
   │   o esistente)    │
   └────────┬──────────┘
            │
   ┌────────▼──────────┐
   │     DRAFT         │
   │ Operatore compila │
   │ testata + righe   │
   └────────┬──────────┘
            │
            │ Stampa anteprima PDF se serve
            │
   ┌────────▼──────────┐    ┌─────────────────────┐
   │     EMESSO        │◀───┤  Genera PDF, salva  │
   │ Cliente vede      │    │  in documenti       │
   └────┬────┬──────┬──┘    └─────────────────────┘
        │    │      │
        │    │      └──────────── (job notturno) ──▶ ┌─────────┐
        │    │                                       │ SCADUTO │
        │    │ rifiuta                               └─────────┘
        │    └──▶ ┌─────┐
        │         │ RIF │      (DRAFT → ANNULLATO: annulla solo da bozza)
        │ accetta └─────┘
   ┌────▼──────────────┐
   │     ACCETTATO     │  smistamento per natura (due rami, selettivi)
   └───┬───────────┬───┘
       │ merce     │ servizio una tantum
       │ genera    │ push
       │ ordine    │ commessa
   ┌───▼─────┐ ┌───▼──────┐
   │ ORDINE  │ │ COMMESSA │
   │ (DRAFT) │ │          │
   └────┬────┘ └────┬─────┘
        └─────┬─────┘
              │ quando NON resta residuo su NESSUN ramo
        ┌─────▼─────┐
        │   EVASO   │  (terminale operativo positivo)
        └───────────┘
```

### 7.2 Revisione (deviazione dal flusso)

Da EMESSO l'operatore può creare una nuova rev DRAFT, modificare e ri-emettere.
Il numero documento resta lo stesso, il contatore `rev` incrementa.

Una rev annullata torna a far valere il predecessore (vedi §4.3).

---

## 8. Smistamento downstream (ordine e commessa)

Quando un preventivo arriva in stato **ACCETTATO**, le sue righe vengono **smistate
per natura** (vedi §2.2): la **merce** va a un **ordine di vendita**, i **servizi
una tantum** vanno a **commessa**. Non c'è quindi un unico "push commessa" per tutte
le righe, ma **due azioni distinte**, entrambe disponibili dal *Pannello
Smistamento* e governate dalle capability sullo stato e sul residuo righe:

- **Genera ordine** (`can_genera_ordine`): smista le righe **merce** (natura con
  destinazione `ORDINE`) verso un nuovo **ordine** in DRAFT, tramite
  `fn_push_preventivo_a_ordine`. Lo smistamento è **selettivo** (si scelgono le
  righe) e **idempotente a livello di riga**: ogni riga merce è smistabile una sola
  volta. Dallo stesso preventivo possono nascere più ordini (consegne parziali).
  La riga d'ordine nasce con la **data di consegna richiesta** della riga di
  preventivo (§2.2) e senza data confermata.
- **Push commessa** (`can_push_commessa`): smista **solo** le righe **servizio una
  tantum** (destinazione `COMMESSA`) verso una commessa, applicando la politica di
  fatturazione (immediata/differita). Anche questo smistamento può essere selettivo.

Ogni riga-servizio eleggibile produce **una** attività commessa (idempotente sul
re-push). **Non** c'è espansione dei compositi in più attività: una riga padre
composita genera una sola attività; la distinta BoM resta sul preventivo ai fini di
prezzo/anteprima, non viene esplosa in commessa.

> **Le righe ricorrenti non passano di qui**: sono bloccate già all'inserimento
> (§2.2) e si gestiscono dall'offerta commerciale → contratto.

### Quando il preventivo diventa EVASO (gate bi-ramo)

Il preventivo transita a **EVASO** **solo** quando non resta residuo da smistare su
**nessun** ramo: né righe-merce non ancora portate a ordine, né righe-servizio non
ancora in commessa. Poiché il push commessa smista solo i servizi, un preventivo che
contiene anche righe-merce non ancora ordinate **resta ACCETTATO** finché anche quel
ramo è completato. In altre parole: *EVASO significa "tutte le righe smistate", non
"push commessa eseguito"*.

La regola ha **una sede sola**, nel database:
[`vendite.fn_preventivo_proietta_stato_smistamento`](/dbzero/vendite/funzioni/fn_preventivo_proietta_stato_smistamento),
che legge il residuo dei due rami (`fn_preventivo_ha_residuo_ordine`,
`fn_preventivo_ha_residuo_commessa`). La chiamano la generazione dell'ordine
(`fn_push_preventivo_a_ordine`) e il trigger delle righe di commessa, che a ogni
riga del preventivo che nasce, cambia stato di emissione o esce dalla commessa
riproietta il preventivo: per questo l'annullo di una commessa lo riporta da solo
ad `ACCETTATO`. Una riga di commessa `ANNULLATA` non conta come «già mandata».

> **Percorso pratica.** Quando lo smistamento avviene nel contesto di una pratica,
> l'orchestratore `CONFERMA_VENDITA` (handler `vendita.push_preventivo`) esegue
> entrambi i rami in un'unica transazione.

Da lì in poi la pipeline fatturazione opera sulle commesse/ordini a valle e produce
le fatture. Vedi [fatturazione end-to-end](/guide/fatturazione) e
[Gestione Ordini di vendita](/guide/gestione-ordini).

Importante: dopo lo smistamento le righe già portate a valle sono **congelate**.
Le modifiche vanno fatte sull'ordine o sulla commessa, non più sul preventivo.

---

## 9. Casi d'uso operativi

### 9.1 Cliente chiede una modifica al preventivo già inviato

1. Apri il preventivo in stato EMESSO
2. Crea **nuova revisione** → rev N+1 DRAFT
3. Modifica righe / prezzi nella DRAFT
4. Emetti → la nuova rev diventa quella corrente, la precedente resta storico

### 9.2 L'operatore ha sbagliato la revisione

1. Sulla rev N+1 **in DRAFT** clicca **Annulla** (l'annullamento manuale è ammesso
   solo da DRAFT; se la rev N+1 è già EMESSO va prima rifiutata/fatta scadere, oppure
   si crea un'ulteriore revisione)
2. Stato → ANNULLATO
3. La rev N (precedente) torna automaticamente "attiva" — l'operatore può
   accettarla, rifiutarla, oppure creare un'altra revisione

Non serve nessuna riattivazione manuale: la logica `is_attiva` derivata gestisce
il fallback per costruzione.

### 9.3 Cliente VIP richiede sconto oltre soglia

1. L'operatore modifica il prezzo riga oltre il limite L2
2. Il frontend rileva il blocco e propone "Richiedi approvazione"
3. Confermando, il sistema crea una pratica `APPROVAZIONE_PREZZO` collegata
   alla riga, e marca lo stato approvazione = `PENDING`
4. Il responsabile riceve la pratica nella coda approvazioni, decide
   APPROVATO / RIFIUTATO con eventuale nota
5. La riga si sblocca (approvato) o torna al prezzo precedente (rifiutato)

Vedi [API Approvazioni prezzo](/backend/vendite/manual/api_approvazioni_prezzo).

### 9.4 Articolo composito (es. "Kit installazione caldaia")

1. Aggiungi una riga selezionando il kit dal lookup articoli
2. Si apre automaticamente il dialog **anteprima componenti** con i figli BoM
   pre-popolati di prezzo (resolver bundle-aware)
3. Conferma o modifica prezzi singoli (con eventuali approvazioni L3 se servono)
4. Salva: la riga padre viene creata, i componenti sono persistiti come righe
   figlie, il prezzo padre = SUM(figli × coeff)
5. In EDIT successivo puoi modificare i prezzi figli dal pannello componenti;
   il padre si aggiorna automaticamente

### 9.5 Preventivo annullato e ricreato

L'annullamento è terminale. Per ripartire serve un nuovo preventivo (nuovo
numero PRV). Non c'è "ripristino" da ANNULLATO. La logica è: la sequenza
PRV-0042 è morta, ne emetti un'altra (PRV-0043).

Va ricordato che l'annullamento manuale è disponibile **solo da DRAFT**: da EMESSO
in poi non esiste un "Annulla", la chiusura semantica passa dal **rifiuto** o dalla
**scadenza**. L'eliminazione fisica (hard-delete) è possibile solo su una **bozza
priva di righe e pratiche**; una bozza con righe non si cancella, si annulla.

---

## 10. Errori principali

Codici lanciati dal dominio preventivi (registrati in `error_policies`):

| Codice                                      | HTTP | Quando                                                                                |
| ------------------------------------------- | ---- | ------------------------------------------------------------------------------------- |
| `E_PREV_VALIDAZIONE`                        | 400  | Payload incoerente (modalità, riferimenti)                                            |
| `E_PREV_NOT_FOUND`                          | 404  | Preventivo / riga / componente inesistente                                            |
| `E_PRICING_SCONTO_ECCESSIVO`                | 400  | L2: sconto oltre limite, no richiesta approvazione                                    |
| `E_PRICING_MAGGIORAZIONE_ECCESSIVA`         | 400  | L2: maggiorazione oltre limite                                                        |
| `E_PRV_REVISIONE_STATO_NON_AMMESSO`         | 400  | Crea revisione da stato diverso da EMESSO                                             |
| `E_PRV_REVISIONE_BOZZA_ESISTENTE`           | 400  | Esiste già una DRAFT per quel numero                                                  |
| `E_DOC_COMPOSITO_BOM_VUOTA`                 | 400  | Composito senza figli BoM validi alla data                                            |
| `E_DOC_COMPONENTE_OBBLIGATORIO`             | 400  | Tentativo disattivare componente obbligatorio                                         |
| `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` | 400  | Prezzo 0 su obbligatorio                                                              |
| `E_BOM_IVA_DISCORDANTE`                     | 400  | IVA componente ≠ IVA padre (vincolo BoM)                                              |
| `E_PREZZO_LISTINO_NON_TROVATO`              | 400  | Resolver non trova listino applicabile                                                |
| `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C`   | 400  | Modalità C: articolo non in contratto                                                 |
| `E_PREV_UTILITY_ISTANZA_INCOERENTE`         | 400  | Creazione: utility non coerente con l'istanza selezionata                             |
| `E_DOC_PREZZO_PENDENTE`                     | 409  | Emissione o accettazione con un prezzo in attesa di approvazione (§6.4)               |
| `E_DOC_PREZZO_RIFIUTATO`                    | 409  | Emissione o accettazione con un prezzo rifiutato (§6.4)                               |
| `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`     | 400  | Riga con natura ricorrente (destinazione CONTRATTO): usa l'offerta commerciale (§2.2) |

`E_PREVENTIVO_RIGHE_PRICING_PENDENTI` è **ritirato** dal 2026-09-24: bloccava solo
l'accettazione e solo per i prezzi in attesa. Lo sostituiscono i due `E_DOC_PREZZO_*`.

Codici dello **smistamento / orchestratore `CONFERMA_VENDITA`** (vedi §8 e
[API Preventivi](/backend/vendite/manual/api_preventivi)):

| Codice                                           | HTTP | Quando                                                                                        |
| ------------------------------------------------ | ---- | --------------------------------------------------------------------------------------------- |
| `E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO`    | 409  | Smistamento a ordine da un preventivo non ACCETTATO                                           |
| `E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE`       | 422  | Smistamento a ordine senza righe-merce residue (tutte già allocate o nessuna di natura merce) |
| `E_VENDITA_PREVENTIVO_NON_ACCETTATO`             | 400  | `CONFERMA_VENDITA`: il preventivo non è ACCETTATO                                             |
| `E_VENDITA_PREVENTIVO_GIA_PUSHATO`               | 400  | `CONFERMA_VENDITA`: niente da smistare ma ordine/commessa già esistenti                       |
| `E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA` | 400  | `CONFERMA_VENDITA`: modalità di fatturazione non valida (≠ IMMEDIATA/DIFFERITA)               |
| `E_VENDITA_COMPETENZA_RICHIESTA`                 | 400  | `CONFERMA_VENDITA`: modalità DIFFERITA senza competenza                                       |

Per il dettaglio dei codici pricing e degli errori L1/L2/L3 vedi
[gestione listini §10](/guide/gestione-listini) e
[API Pricing](/backend/vendite/manual/api_pricing).

---

## 11. Pattern e principi di design

### 11.1 Stato derivato vs persistito

ZeroERP preferisce stati derivati dove possibile per evitare drift fra flag
e dati strutturali. `is_attiva` sui preventivi è l'esempio tipico: non c'è
una colonna che dice "questa è la rev attiva", c'è una vista che lo deriva
da (`rev`, stato del successore).

Vantaggio: nessun trigger di sincronizzazione, nessuna casistica
"il flag dice X ma i dati dicono Y", nuovi flussi non rompono la coerenza.

### 11.2 Snapshot e immutabilità

Le entità che vengono "fissate" al momento dell'emissione (indirizzi snapshot,
componenti BoM `coeff_qta_snapshot`, prezzo_resolver_context audit) **non
retroagiscono** ai cambiamenti dell'anagrafica/catalogo. Il preventivo è una
fotografia commerciale ad un istante.

Una revisione produce un **nuovo snapshot** ricalcolato sui dati correnti, non
modifica lo snapshot della rev precedente.

### 11.3 Trigger DB come ultima difesa

I controlli più stringenti (modalità contratto coerente, IVA BoM coerente,
intersezione BoM-listino valida) sono **trigger DB**: anche se un frontend
bypassa i controlli applicativi, il DB rifiuta. Backend e frontend hanno
controlli equivalenti per UX migliore (errori parlanti pre-roundtrip), ma
la fonte di verità è sempre il DB.

### 11.4 BoM modello unificato cross-dominio

Lo stesso modello componenti BoM viene riusato su `vendite.preventivi_righe`,
`vendite.contratti_righe`, `vendite.ordini_righe`, `vendite.ddt_righe` (e in
futuro acquisti). Stessi guard, stessi trigger di ricalcolo padre, stessa UI.
Vedi [modello componenti BoM](/dev/manual/modello-componenti-bom) per la
simmetria del pattern a 3 livelli (struttura, listino, documento).

---

## 12. Glossario rapido

| Termine           | Significato                                                                                                                 |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Preventivo**    | Offerta commerciale verso un cliente, ciclo di vita DRAFT → EMESSO → ACCETTATO → EVASO (oppure RIFIUTATO/ANNULLATO/SCADUTO) |
| **Revisione**     | Nuova istanza dello stesso numero preventivo con `rev` incrementato. Si crea da EMESSO                                      |
| **is_attiva**     | Predicato derivato: "non esiste rev superiore non-abortita per lo stesso numero"                                            |
| **is_abortito**   | Metadato di stato: TRUE solo per ANNULLATO. Marca la rev come rinuncia, abilita fallback al predecessore                    |
| **Composito**     | Articolo con `is_composito=TRUE` che ha una distinta base (BoM). Prezzo padre = SUM figli × coeff                           |
| **BoM**           | Bill of Materials, distinta base del composito (`articoli_componenti`). Immutabile per design                               |
| **L1/L2/L3**      | Livelli di autorizzazione pricing: Override Manuale / Limiti soglie / Workflow approvazione                                 |
| **Push commessa** | Smistamento delle sole righe-servizio una tantum del preventivo ACCETTATO in commessa, per innescare la fatturazione        |
| **Genera ordine** | Smistamento delle righe-merce del preventivo ACCETTATO verso un ordine di vendita (riga-per-riga, 1:N)                      |
| **EVASO**         | Stato terminale positivo: tutte le righe smistate (ordine + commessa), nessun residuo. Gate bi-ramo                         |
| **Snapshot**      | Copia congelata di dati al momento di un evento. Non retroagisce ai cambi anagrafica                                        |

---

*Per il dettaglio tecnico delle API REST, formati payload e codici errore vedi
[API Preventivi](/backend/vendite/manual/api_preventivi). Per il modello
componenti BoM e le decisioni di design vedi
[modello-componenti-bom](/dev/manual/modello-componenti-bom).*

---
{% include-markdown "signature-core.md" %}
