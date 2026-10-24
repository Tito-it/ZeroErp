# Guida — Gestione DDT di vendita

> **Ultimo aggiornamento**: 25 ottobre 2026
>
> **Destinatari**: analisti funzionali, operatori commerciali/logistici,
> sviluppatori backend/frontend, DBA.
>
> **Vedi anche** — schemi DB:
>
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) / [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe) / [vendite.ddt_righe_componenti](/dbzero/vendite/tabelle/ddt_righe_componenti)
> * [vendite.ddt_indirizzi](/dbzero/vendite/tabelle/ddt_indirizzi) / [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment) (evasione)
> * [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt) / [config.transizioni_stati_ddt](/dbzero/config/tabelle/transizioni_stati_ddt)
> * [vendite.vw_ddt_lista](/dbzero/vendite/manual/vw_ddt_lista) / [vendite.vw_ddt_riepilogo_iva_dettaglio](/dbzero/vendite/manual/vw_ddt_riepilogo_iva_dettaglio)
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt) — azioni disponibili sullo stato corrente
> * [vendite.trgfn_ddt_guard_transizione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione) — enforcement del grafo stati
> * [vendite.fn_genera_ddt_da_ordine](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine) — evasione delle righe ordine in un DDT
> * [vendite.fn_ddt_riga_correggi_qta_evasa](/dbzero/vendite/funzioni/fn_ddt_riga_correggi_qta_evasa) / [vendite.trgfn_ddt_righe_guard_riga_evasa](/dbzero/vendite/funzioni/trgfn_ddt_righe_guard_riga_evasa) — la riga evasa: ferma, corretta solo dal verbo
> * [vendite.fn_annulla_ddt](/dbzero/vendite/funzioni/fn_annulla_ddt) / [vendite.fn_ddt_legami](/dbzero/vendite/funzioni/fn_ddt_legami) — l'annullo di una bolla con righe legate a ordini o resi
> * [vendite.fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare) — righe eleggibili al push a commessa
> * [vendite.trgfn_ddt_gen_numero_emesso](/dbzero/vendite/funzioni/trgfn_ddt_gen_numero_emesso) / [vendite.trgfn_v_ddt_protect_num](/dbzero/vendite/funzioni/trgfn_v_ddt_protect_num) — numero assegnato a EMESSO e poi immutabile
> * [vendite.trgfn_ddt_guard_indirizzi_obbligatori](/dbzero/vendite/funzioni/trgfn_ddt_guard_indirizzi_obbligatori) — indirizzo di consegna obbligatorio all'emissione
> * [vendite.trgfn_ddt_normalize](/dbzero/vendite/funzioni/trgfn_ddt_normalize) — eredità dal contesto (BA/utility/valuta/emittente)
> * [script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale) / [script.trgfn_doc_guard_emittente_ba](/dbzero/script/manual/trgfn_doc_guard_emittente_ba) — emittente fiscale di default (il building block unico, montato sui DDT con «lascia NULL» e «salta con sorgente») e coerenza col cliente
> * [vendite.fn_ddt_riga_componenti_init](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_init) / [vendite.fn_ddt_riga_componenti_preview](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_preview) — componenti BoM
>
> **Vedi anche** — API e service backend:
>
> * [API DDT](/backend/vendite/manual/api_ddt)
> * [API Ordini](/backend/vendite/manual/api_ordini) — la sorgente dell'evasione
>
> **Vedi anche** — guide correlate:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — **le regole comuni a tutti i documenti**: nascita, cambio di stato, permesso sul passaggio, emissione, annullo
> * [Gestione Ordini](/guide/gestione-ordini) — la sorgente del DDT (evasione)
> * [Gestione Commesse](/guide/gestione-commesse) — la destinazione del push
> * [Fatturazione end-to-end](/guide/fatturazione) — il push a commessa avvia la pipeline
> * [Documenti e stampe](/guide/documenti-e-stampe) — generazione del PDF di trasporto
> * [Gestione Istanze Utility](/guide/gestione-delle-istanze-utility) — cliente, billing account, istanza
> * [Gestione Indirizzi documento](/guide/gestione-delle-istanze-utility) — l'indirizzo di consegna del DDT
> * [Numerazione dei documenti e codici](/guide/numerazione-documenti-e-codici) — **il motore che assegna il numero**: è lo stesso di ordini, fatture, resi e commesse
> * [Il risolutore IVA di riga](/guide/iva-risolutore-di-riga) — **la sede unica** che decide il codice IVA di una riga

---

## 1. Cosa è un DDT di vendita

Il DDT (Documento Di Trasporto) è il **documento che accompagna la merce** dal
mittente al destinatario. Risponde alla domanda: *"Cosa stiamo consegnando a
questo cliente, in quali quantità, con quale trasporto e a quale indirizzo?"*

A differenza dell'ordine — che è l'**impegno** commerciale a consegnare e
fatturare — il DDT è l'atto della **consegna vera e propria**: registra la merce
che esce, il vettore, l'aspetto dei beni, i colli e il **luogo di consegna**.

Caratteristiche di base:

* è intestato a un **cliente** (billing account, con il relativo soggetto) e ha
  un **destinatario** (chi riceve fisicamente la merce), oltre a **mittente** e
  **vettore** opzionali;
* raccoglie **righe** (articolo, quantità, ed eventualmente prezzo/IVA) e
  **componenti BoM** per gli articoli compositi;
* porta i **dati di trasporto** (causale, aspetto dei beni, modalità di addebito,
  colli, pesi, volume, targa, autista, tracking);
* porta gli **indirizzi di consegna** (snapshot congelato all'emissione);
* ha un **ciclo di vita** logistico: bozza → emesso → spedito → consegnato
  (→ reso), oppure annullato;
* nasce quasi sempre per **evasione** di un ordine, ma può essere creato
  **standalone** a mano;
* all'emissione produce il **PDF di trasporto** con il luogo di consegna;
* può essere **spinto in commessa** (push) per la fatturazione.

> **Il numero si assegna all'EMISSIONE, non alla nascita.** A differenza
> dell'ordine (che nasce già numerato), il DDT resta **senza numero in bozza** e
> lo riceve solo quando viene **emesso** (trigger `trgfn_ddt_gen_numero_emesso`).
> Da quel momento il numero è **immutabile** (`trgfn_v_ddt_protect_num`). È
> coerente con la natura fiscale del documento di trasporto: un DDT numerato è un
> documento "vero" che ha lasciato il magazzino.
>
> ⭐ **Il numero però non se lo fabbrica il DDT.** Il trigger è solo il *momento*
> in cui il DDT chiede il numero: a produrlo è il **motore dei registri**, lo
> stesso che numera ordini, fatture, resi e commesse — progressione per azienda
> emittente, reset annuale, forma (prefisso, cifre, serie) presa dal registro.
> Come funziona, e perché non è il catalogo dei formati usato per i codici
> cliente, sta nella guida
> [Numerazione dei documenti e codici](/guide/numerazione-documenti-e-codici).

---

## 2. Dove si colloca nel flusso

Il DDT è il passaggio dall'**impegno** (ordine) alla **consegna**. La sorgente
naturale è l'ordine confermato; in alternativa nasce standalone.

```text
   ORDINE CONFERMATO ┌───────────────────────────┐
   (righe da evadere) │ evasione: righe + quantità │── 1:N ──┐
                      │  (residuo per riga)        │         │
                      └───────────────────────────┘         ▼
                                                        ┌────────────┐  push   ┌──────────┐
                                                        │    DDT     │────────▶│ COMMESSA │──▶ Fattura
   CREAZIONE STANDALONE ───────────────────────────────▶│  DRAFT →   │         │ (attività│
   (DDT "diretto", con cliente)                          │  EMESSO →  │         │ fatturab.)│
                                                        │  SPEDITO → │         └──────────┘
                                                        │ CONSEGNATO │
                                                        └────────────┘
```

### 2.1 Dall'ordine: evasione (1:N, con residuo per riga)

Un ordine confermato viene **evaso** in uno o più DDT. L'evasione è
**riga-per-riga e per quantità**: per ogni riga d'ordine si consegna una
quantità, e ciò che resta da consegnare è il **residuo**. Per questo il legame
ordine → DDT è **1:N**: dallo stesso ordine possono nascere più DDT (consegne
parziali/multiple).

Il residuo è tenuto da `vendite.ordini_righe_fulfillment` (append-only): ogni
evasione **aggiunge** una quantità evasa, non la sottrae. Quando l'ordine è
completamente evaso, la sua proiezione di stato lo riflette
(`PARZIALMENTE_EVASO` / `EVASO`).

> Una riga d'ordine che ha già un DDT collegato **non è più eliminabile**
> (guard DB `trgfn_dlt_block_ordrig_ddtrig`): la merce risulta in consegna. E
> su un ordine fuori bozza nessuna riga si toglie comunque
> (`trgfn_doc_righe_lock_fuori_bozza`, il meccanismo condiviso).

### 2.2 Standalone (creazione manuale)

È possibile creare un DDT **da zero**, scegliendo il cliente (billing account) e
le righe a mano. In questo caso il DDT nasce senza riferimento a un ordine di
origine (`sorgente_tipo_id`/`sorgente_uid` NULL). Il cliente è **obbligatorio**
alla creazione: da lì il sistema deriva destinatario ed emittente.

---

## 3. Le entità in gioco

### 3.1 Testata `ddt`

Contiene il contesto del documento e del trasporto:

* **chi** (`billing_account_id`) — il cliente; **a chi si consegna**
  (`destinatario_soggetto_ruolo_id`) — derivato dal cliente se non indicato.
* **chi emette** (`emittente_fiscale_id`) — l'emittente fiscale (vedi §7).
* **per cosa** (`utility_id`) e **valuta** (`valuta_id`) — opzionali.
* **quando** (`data`) — default alla data odierna.
* **trasporto**: `causale_trasporto_id`, `aspetto_bene_id`,
  `modalita_addebito_trasporto_id`, `mittente_soggetto_ruolo_id`,
  `vettore_soggetto_ruolo_id`, `num_colli`, `peso_lordo`, `peso_netto`, `volume`,
  `targa`, `autista`, `tracking_code`.
* **da dove arriva** (`sorgente_tipo_id` + `sorgente_uid`) — valorizzata
  dall'evasione (sorgente `ORDINE_VENDITA`); NULL se il DDT è standalone.
* **identità e stato** (`numero`/`anno` — assegnati a EMESSO —, `uid`,
  `stato_doc_ddt_id`).

### 3.2 Righe `ddt_righe`

Ogni riga è una voce di merce consegnata:

* **articolo** (`articolo_id`) e **descrizione**;
* **quantità** in doppia unità: **operativa** (`qta_operativa` +
  `uom_operativa_id`) e **base** (`quantita`, calcolata da `factor_to_base`);
* **prezzo** (`prezzo_unitario`) e **IVA** (`iva_id`) — **opzionali**: un DDT può
  essere di **solo trasporto** (righe senza prezzo).

**Quali articoli ammette** (dal 2026-10-13): solo **merce**, e mai un articolo **«solo
componente»**, che si vende soltanto dentro il kit che lo contiene. Un servizio una tantum va
in commessa, un servizio ricorrente in contratto (tramite un'offerta). La merce è giudicata
dalla **natura con cui la riga è stata venduta**: una riga nata da un ordine porta la natura di lì, anche
se nel frattempo l'articolo è cambiato in anagrafica. Il controllo è uno solo per tutti i
documenti ([`script.fn_check_articolo_riga`](/dbzero/script/manual/fn_check_articolo_riga)), e
il messaggio dice perché e dove va invece l'articolo. Un **kit senza componenti** (dal 2026-10-14) non si mette in nessuna riga: va prima completata la sua distinta.

**Nella ricerca dell'articolo** trovi prima quelli che la riga può usare. Gli altri compaiono dopo, in grigio, col motivo sotto, e non si possono scegliere: chi cerca un codice preciso e non lo trova fra i primi vede perché. La ricerca e il rifiuto al salvataggio usano la stessa regola, quindi un articolo proposto non viene rifiutato dopo.

La **riconsegna** di un reso è esente: restituisce ciò che è uscito, anche se l'articolo nel
frattempo è diventato «solo componente».

> **Prezzo opzionale = DDT di solo trasporto.** Se le righe non hanno prezzo, il
> DDT documenta solo il movimento della merce e il *Riepilogo IVA* resta vuoto
> (le righe senza prezzo sono escluse in vista). Con i prezzi valorizzati, il DDT
> espone anche il riepilogo per aliquota, come gli altri documenti.
>
> ⛔ **L'`iva_id` della riga non si copia dall'articolo.** Lo decide il
> **risolutore IVA di riga**, la stessa funzione che serve preventivi, ordini e
> fatture: guarda l'articolo, poi l'uso della fornitura, poi gli eventuali titoli
> documentati del cliente (dichiarazione d'intento, agevolazioni), e dice anche
> **perché** ha scelto quel codice. La regola completa è nella guida
> [Il risolutore IVA di riga](/guide/iva-risolutore-di-riga).

### 3.3 Componenti BoM `ddt_righe_componenti`

Come nel resto della famiglia vendite, una riga che punta a un **articolo
composito** genera un componente per ogni pezzo della BoM. La composizione è
**immutabile**; se valorizzato, il prezzo del padre è la somma pesata dei figli.

### 3.4 Indirizzi di consegna `ddt_indirizzi`

Il DDT porta gli **indirizzi documento** (building block cross-dominio), con al
centro l'**indirizzo di consegna** (tipo `CON`). Ogni slot è uno **snapshot
congelato**: al momento dell'emissione l'indirizzo viene "fotografato" sul
documento e non cambia più anche se l'anagrafica del cliente viene poi
modificata. Vedi §10.

### 3.5 Note

Il DDT supporta le **note partizionate** (di testata o di riga), con lo stesso
comportamento di preventivi, ordini, offerte e contratti.

---

## 4. Ciclo di vita e stati

⭐ Le regole comuni a tutti i documenti — in che stato si nasce, chi cambia lo stato, quale permesso chiede un passaggio, l'emissione, l'annullo — stanno nel [modello del documento di vendita](/guide/modello-documento-di-vendita), che al §10 dice anche a che punto è il DDT (e il reso) rispetto al modello. Qui ci sono gli stati e i passaggi che sono suoi.

### 4.1 Stati

Il catalogo `config.stati_doc_ddt` prevede sei stati:

| Stato        | Significato                                                          | Modificabile?       | Terminale? | In uso oggi         |
| ------------ | -------------------------------------------------------------------- | ------------------- | ---------- | ------------------- |
| `DRAFT`      | Bozza in preparazione                                                | Sì: testata e righe | No         | sì                  |
| `EMESSO`     | Documento emesso: numero assegnato, PDF prodotto                     | No                  | No         | sì                  |
| `SPEDITO`    | Merce partita (vettore/tracking)                                     | No                  | No         | sì                  |
| `CONSEGNATO` | Merce consegnata al destinatario                                     | No                  | No         | sì                  |
| `RESO`       | Merce resa (totale): flip automatico alla conferma di un reso totale | No                  | —          | sì, motore **resi** |
| `ANNULLATO`  | Bozza/emesso annullato                                               | No                  | Sì         | sì                  |

### 4.2 Transizioni ammesse

Le transizioni sono governate dalla matrice `config.transizioni_stati_ddt`,
**fonte unica di verità** (decide sia cosa mostra la UI, sia cosa il DB accetta):

```text
DRAFT ──(emetti)──▶ EMESSO ──(spedisci)──▶ SPEDITO ──(consegna)──▶ CONSEGNATO
  │                    │                                              │
  └──(annulla)──▶ ANNULLATO ◀──(annulla)──┘                          │ (motore resi)
                                                                      ▼
                                                        CONSEGNATO ⇄ RESO
```

* **DRAFT → EMESSO** (*emetti*): assegna il numero e genera il PDF; richiede
  l'**indirizzo di consegna** (guard DB, vedi §9/§10).
* **EMESSO → SPEDITO** (*spedisci*) e **SPEDITO → CONSEGNATO** (*consegna*):
  avanzamento logistico manuale, con conferma.
* **DRAFT → ANNULLATO** ed **EMESSO → ANNULLATO** (*annulla*): consentiti.
* **CONSEGNATO → RESO** e **RESO → CONSEGNATO**: **automatiche**, guidate dal
  **motore resi** (non pulsanti manuali). Il vecchio "Reso" manuale e la
  transizione `SPEDITO → RESO` sono **disabilitati**. Il DDT entra in `RESO`
  solo per effetto del motore, su reso **totale** (l'annullo del reso lo
  riporta a `CONSEGNATO`). Vedi §11-bis.

### 4.3 Annullare una bolla da ordine o da reso

Una bolla nata da un ordine (o da un reso da ri-consegnare) porta, riga per riga,
il **legame** con la riga d'origine: è ciò che fa risultare l'ordine evaso, o il
reso ri-consegnato. Annullare la bolla **ritira quei legami**: le quantità tornano
da spedire, l'ordine torna da evadere (`CONFERMATO` o `PARZIALMENTE_EVASO`), il
reso torna da ri-consegnare. Se la bolla ha spinto righe in commessa ancora da
emettere, anche quelle si annullano. Vale sia in bozza sia da emessa; da emessa
il magazzino storna anche l'uscita.

Non succede in silenzio. Su una bolla con legami, «Annulla DDT» apre una
**finestra di conferma** che elenca che cosa si riapre: per ogni legame il
documento dall'altra parte (apribile con un clic), la riga e la quantità.
Confermando, l'operatore dichiara quanti legami ha visto: se nel frattempo sono
cambiati, la finestra si ripresenta aggiornata. Una bolla senza legami si annulla
come sempre, con la sola conferma del cambio di stato. La stessa finestra vale
per ordini, preventivi e contratti.

### 4.4 La doppia difesa

1. **In interfaccia**: `fn_available_actions_ddt` legge la matrice e restituisce
   solo le azioni disponibili — i pulsanti senza senso non compaiono.
2. **Nel database**: il trigger `trgfn_ddt_guard_transizione` rifiuta qualsiasi
   cambio di stato non previsto; `trgfn_ddt_guard_indirizzi_obbligatori` blocca
   l'emissione senza indirizzo di consegna.

---

## 5. Azioni disponibili

Le azioni eseguibili sono calcolate dal database (`fn_available_actions_ddt`) ed
esposte come *capability*, così il frontend non replica la logica degli stati.

| Flag                                            | Vero quando                                       |
| ----------------------------------------------- | ------------------------------------------------- |
| `can_edit_testata` / `can_edit_righe`           | il DDT è in `DRAFT`                               |
| `can_push_commessa` (+ `_reason`/`_reason_key`) | ci sono righe eleggibili al push                  |
| `non_editable_fields`                           | l'elenco dei campi bloccati (es. cliente, numero) |

In sintesi:

* **In `DRAFT`**: si **modificano** testata e righe, si **emette** o si
  **annulla**.
* **In `EMESSO`/`SPEDITO`/`CONSEGNATO`**: testata e righe **in sola lettura**;
  disponibili l'avanzamento logistico e — se ci sono righe eleggibili — il **push
  a commessa**.
* **In `RESO`/`ANNULLATO`**: sola lettura.

> ⭐ **Le righe in sola lettura non sono solo un fatto di interfaccia.** Fuori
> dalla bozza il database rifiuta qualsiasi aggiunta, modifica o rimozione di
> riga (`E_RIGA_DOC_NON_BOZZA`): è il meccanismo condiviso «le righe di un
> documento si toccano solo in bozza»
> ([`trgfn_doc_righe_lock_fuori_bozza`](/dbzero/vendite/manual/trgfn_doc_righe_lock_fuori_bozza)),
> lo stesso di ordini e contratti. Una riga già instradata alla fatturazione non
> può quindi essere disattivata o cambiata: le correzioni passano da reso,
> ri-consegna o nota.

---

## 6. Creazione di un DDT

### 6.1 Da ordine (evasione)

Dall'ordine confermato, l'azione **genera DDT** apre l'evasione: si scelgono le
righe e le quantità da consegnare (fino al residuo). Il sistema:

1. crea un DDT in `DRAFT` ereditando il contesto dall'ordine
   (cliente/utility/valuta/emittente, tramite `trgfn_ddt_normalize`);
2. copia le righe evase con quantità e componenti BoM;
3. registra sull'ordine la quantità evasa (`ordini_righe_fulfillment`);
4. valorizza la sorgente come `ORDINE_VENDITA`.

Se non resta residuo, l'evasione segnala che non c'è nulla da consegnare.

### 6.2 Standalone (manuale)

1. **Nuovo DDT** → scegli il **cliente** (billing account): da lì il sistema
   deriva il **destinatario**. Una bolla che non va a un cliente
   (trasferimento, conto lavoro, riparazione) nasce **senza cliente**, col solo
   destinatario.
2. Il DDT nasce in `DRAFT` **senza numero** (arriverà all'emissione).
3. **Aggiungi le righe** (articolo, quantità; prezzo/IVA se serve fatturare).
4. Compila i **dati di trasporto** e imposta l'**indirizzo di consegna**.

> **Bozza "usa e getta".** La creazione salva subito una bozza (auto-save al
> primo cliente o destinatario) per poter aggiungere righe e indirizzi. Se l'operatore esce
> senza inserire nulla, la bozza vuota può essere eliminata. Un DDT **emesso**
> non si cancella: si **annulla**.

### 6.3 Le righe di un DDT da ordine

Una bolla generata da un ordine (o da un reso, con la ri-consegna) ha due tipi di
riga:

| Riga | Come nasce | Che cosa si cambia in bozza |
| --- | --- | --- |
| **evasa** | dall'evasione: porta il legame con la riga d'ordine (o di reso) | descrizione, prezzo, sconto. **Articolo, unità di misura e quantità sono fermi**: sono la fotografia di ciò che si spedisce per conto dell'origine |
| **a mano** | aggiunta dall'operatore | tutto, come su una bolla standalone. Non è legata all'ordine |

* **La quantità della riga evasa** si corregge con **«Correggi quantità
  evasa»**, nel form della riga: cambiano insieme la riga, la quantità evasa
  dell'ordine (o ri-consegnata del reso) e lo stato dell'ordine. Il nuovo valore
  resta entro il residuo dell'ordine. Il pulsante è acceso solo in bozza; spento,
  il suo tooltip dice perché.
* **La riga evasa si toglie** in bozza come le altre: il legame si ritira con
  lei e la quantità torna da evadere.
* **Fuori bozza** niente di tutto questo: righe e legami sono fermi.

Due esempi, sull'ordine di 10 pezzi dell'articolo *pippo*:

* **Si consegnano 15.** Bolla generata con la riga evasa da 10, più una riga
  **a mano** di *pippo* da 5. L'ordine risulta evaso per 10, `EVASO`; i 5 in più
  viaggiano sulla bolla senza toccare l'ordine.
* **Si consegnano 6.** Bolla generata con 10, poi «Correggi quantità evasa» a 6
  sulla riga evasa. L'ordine risulta evaso per 6, `PARZIALMENTE_EVASO`, e i 4
  restano da evadere con una bolla successiva.

---

## 7. Cliente, destinatario ed emittente fiscale

### 7.1 Cliente e destinatario: si scelgono in bozza

Il cliente di un DDT è un **billing account**, cioè una fornitura di un
cliente. Destinatario e utility sono copie di ciò che il billing account già
dice: se il cliente c'è, li scrive il database dal billing account, e un valore
diverso viene rifiutato. Senza cliente il destinatario si sceglie liberamente:
è il deposito o il terzista.

* **In bozza** cliente e destinatario si scelgono, si cambiano e si tolgono.
* **All'emissione** il cliente è obbligatorio se la causale di trasporto manda
  merce a un cliente (vendita, omaggio, campionatura, conto visione); per le
  altre causali può mancare. Il motivo compare sull'azione «Emetti».
* **Dopo la bozza** cliente, destinatario, utility ed emittente non si cambiano
  più: la bolla emessa è un foglio consegnato, e se è sbagliata si annulla e se
  ne fa una nuova.
* **Lungo la catena** il cliente non cambia: un DDT da ordine ha il cliente
  dell'ordine, e ogni riga evade righe d'ordine dello stesso cliente.

Le regole le applica il database; il backend non le ricopia.

### 7.2 Emittente fiscale (legato allo user)

L'emittente del DDT è **legato all'operatore**, come in ordini, preventivi e
contratti. L'interfaccia lo prefilla dal **profilo dell'operatore** (l'admin
globale lo sceglie da un elenco) e lo invia col documento. La colonna resta **memorizzata** sul DDT (con scope RLS per
emittente). Reti di sicurezza a DB:

* se l'operatore non lo indica, lo imposta il trigger di default dell'emittente
  (`trg_ddt_a10_default_emittente_ins`, che esegue il meccanismo condiviso
  `script.trgfn_default_emittente_fiscale`) dal contesto utente; per i DDT da
  evasione il default **non scatta** e l'emittente è **ereditato dall'ordine** da
  `trgfn_ddt_normalize`; senza contesto utente non solleva e lascia decidere al
  `normalize` (dal cliente) o al vincolo;
* se il DDT ha un cliente, l'emittente deve essere **coerente** con esso:
  `script.trgfn_doc_guard_emittente_ba` rifiuta le combinazioni incoerenti.

L'**etichetta** dell'emittente mostrata è sempre la **ragione sociale del
soggetto** emittente, mai il codice tecnico del record.

> Dato che il cliente (billing account) determina univocamente l'istanza e
> l'emittente (relazione 1:1 per utility, vedi
> [Gestione Istanze Utility](/guide/gestione-delle-istanze-utility)), il DDT non
> memorizza una propria istanza: la ricava dal cliente.

---

## 8. Prezzi e totali

### 8.1 Prezzo delle righe

Il prezzo delle righe DDT è **opzionale**:

* nell'**evasione** eredita il prezzo "fotografato" sulla riga d'ordine;
* nello **standalone** l'operatore può digitarlo (o lasciarlo vuoto per un DDT di
  solo trasporto);
* se assente e l'articolo non è composito, può essere risolto dal listino
  tramite il *PricingService*, come negli altri documenti.

### 8.2 Totali e Riepilogo IVA

Quando le righe hanno prezzo, i totali e il **Riepilogo IVA** (una riga per
aliquota) sono calcolati dal database dalla vista dedicata
`vw_ddt_riepilogo_iva_dettaglio` (le righe senza prezzo sono escluse). Se il DDT
è di solo trasporto, il riepilogo resta vuoto e nascosto.

> ⚠️ **Il riepilogo del DDT è «live», non uno snapshot**: si ricalcola a ogni
> modifica delle righe. È una scelta dichiarata — un documento di lavoro non si
> congela, congelarlo creerebbe debito di riconciliazione invece di risolverlo.
> Lo snapshot appartiene ai documenti con un istante di emissione i cui valori
> diventano autorevoli (preventivo, fattura). Il quadro dei due meccanismi, e
> perché non si unificano, è nella guida
> [Il risolutore IVA di riga](/guide/iva-risolutore-di-riga) — che è cosa
> **diversa** dal riepilogo: decide il codice della **singola riga**, mentre qui
> si somma quel che le righe già portano.

---

## 9. Emissione e stampa

Nella famiglia vendite **emettere equivale a rendere definitivo** il documento.
Il percorso principale è l'azione **Emetti**:

1. dal DDT in `DRAFT` si lancia l'emissione;
2. il DB **assegna il numero** (`DRAFT → EMESSO`) e, nella stessa operazione,
   si genera il **PDF di trasporto**;
3. si possono allegare file opzionali.

**Precondizione: l'indirizzo di consegna.** Un DDT non si emette senza
l'indirizzo obbligatorio (tipo `CON`): il guard DB
`trgfn_ddt_guard_indirizzi_obbligatori` blocca l'emissione, e l'interfaccia
avvisa già in fase di bozza. Vedi §10.

Cosa contiene il PDF: numero e data DDT, cliente/destinatario, emittente, dati di
trasporto (causale, aspetto beni, vettore, colli/pesi), **luogo di consegna**,
righe con quantità (e prezzi/IVA se valorizzati) e note.

> **Anteprima vs documento definitivo.** In `DRAFT` è disponibile solo
> l'**anteprima** del PDF. Il documento persistito nasce con l'emissione. Serve
> un **template "DDT_VENDITA" pubblicato** (vedi
> [Documenti e stampe](/guide/documenti-e-stampe)).

---

## 10. Indirizzo di consegna

Il DDT usa il building block **indirizzi documento** condiviso con gli altri
domini di vendita, ma con una specificità: l'indirizzo di **consegna** (tipo
`CON`) è l'ancora del documento ed è **obbligatorio all'emissione**.

Come funziona:

* alla creazione, il sistema **auto-assegna** l'indirizzo di consegna di default
  del cliente (indirizzo di ruolo `CON`, con fallback `FATT`), best-effort;
* l'operatore può cambiarlo dal pannello indirizzi: sceglierne uno
  dall'anagrafica del cliente ("usa questo") o inserire un **indirizzo libero**
  una-tantum;
* al momento dell'emissione lo slot viene **congelato** come snapshot: il PDF e
  il documento riportano l'indirizzo fotografato, indipendente da modifiche
  successive all'anagrafica.

L'ancora di provenienza del DDT è il **destinatario** (chi riceve la merce), non
il billing account: regge anche i DDT verso terzi e i casi con prospect senza BA.

---

## 11. Push a commessa

Quando il DDT è emesso e ha righe eleggibili, l'azione **push a commessa** invia
le righe alle **attività fatturabili** su una commessa (sorgente `DDT_VENDITA`),
che a sua volta alimenta la pipeline di fatturazione. Le righe eleggibili sono
quelle attive, con quantità positiva, non ancora inviate a una commessa. Chi lo
decide è **una** funzione, [`fn_ddt_push_diagnosi`](/dbzero/vendite/funzioni/fn_ddt_push_diagnosi):
per ogni riga dice il motivo per cui *non* è inviabile (nessun motivo =
eleggibile). Il lister del push (`fn_list_ddt_da_pushare`) ne deriva, e il
pulsante del drawer con il suo tooltip leggono la stessa risposta — così ciò che
il pulsante propone e ciò che il push esegue non possono divergere.

> **XOR con l'ordine.** Una stessa merce si fattura **una volta sola**: se la
> fatturazione avviene per DDT non avviene anche per l'ordine di origine, e
> viceversa. Il percorso (fatturazione all'ordine oppure al DDT) dipende dalla
> configurazione del ciclo; il push a commessa è comunque l'unico punto che
> apre la fatturazione. Dettagli in [Gestione Commesse](/guide/gestione-commesse)
> e [Fatturazione](/guide/fatturazione).

---

## 11-bis. Reso della merce

Da un DDT **CONSEGNATO** si può registrare un **reso**, realizzato dal **motore
resi**. Il reso è un documento **autonomo** (`vendite.resi`), non un semplice
cambio di stato del DDT: porta **quantità** (reso parziale: se ne rendono 3 di
10) e **intento** per riga.

Come funziona, dal punto di vista del DDT:

* dal drawer del DDT consegnato, il pannello **"Crea reso"** apre un reso legato
  a quel DDT (righe con quantità ≤ consegnato, guard DB);
* ogni riga di reso ha un **tipo** (`config.tipi_reso`): **a credito**
  (`RESO_A_CREDITO`) o **per ri-consegna** (`RESO_PER_RICONSEGNA`, flag
  `riapre_residuo`);
* il reso ha una sua macchina a stati (`DRAFT → CONFERMATO` + `ANNULLATO`,
  numero alla conferma): gli **effetti scattano alla CONFERMA**, non in bozza;
* alla conferma di un reso **totale** (rese tutte le quantità consegnate) il DDT
  passa **automaticamente** a `RESO`; su reso parziale il DDT resta `CONSEGNATO`
  (la verità fine sta nelle righe di reso). L'annullo del reso ripristina lo
  stato del DDT;
* **reso per ri-consegna** → riapre il **residuo** dell'ordine (l'addendo
  `qta_resa_per_riconsegna`, §2.1): l'ordine torna evadibile e si genera un nuovo
  DDT di ri-consegna (`fn_genera_ddt_riconsegna`);
* **reso a credito** → alimenta la coda "da accreditare" (vista
  `vw_resi_da_accreditare`) per la futura nota di credito. L'accredito scrive una
  **rettifica** nella commessa della riga fatturata che corregge;
* **se si annulla quella commessa** (la rettifica è ancora da emettere, cioè dopo il
  reset del lotto: finché la riga fatturata è emessa la commessa non si annulla),
  l'accredito si annulla con lei e la quota **non risulta più accreditata**: la
  finestra di conferma lo dice («torna da accreditare»), e la coda accrediti la
  ripropone quando la merce torna in fattura. Dettaglio in
  [Gestione Commesse](/guide/gestione-commesse) §«Annullare una commessa».

> Il modello completo del reso (entità, guard, ri-consegna, note di credito) è
> nei brief `work-done/brief-db-resi-vendita.md` e
> `work-done/brief-be-fe-resi-vendita.md`.

---

## 12. Lista DDT

La lista DDT è una **lista configurabile**. Mostra di norma numero, data,
destinatario, codice cliente, causale di trasporto, ordine di origine e stato;
in opzione sono disponibili colonne aggiuntive (emittente — che mostra la
ragione sociale —, id fiscale, ecc.).

Filtri principali: ricerca testuale (numero, destinatario, codice cliente,
codice fiscale/P.IVA), stato, cliente, utility, intervallo di date. La lista
rispetta lo **scope dell'emittente** dell'utente. Dalla lista si aprono il
dettaglio, l'export (CSV/XLSX) e i documenti generati.

---

## 13. Casi d'uso operativi

### 13.1 Evasione totale di un ordine

1. L'ordine viene **confermato**.
2. Dal drawer ordine: "Genera DDT" → seleziona tutte le righe → conferma.
3. Nasce un DDT in `DRAFT` con quelle righe; l'indirizzo di consegna è
   auto-assegnato.
4. "Emetti" → il DDT riceve il numero e produce il PDF.
5. "Spedisci" → "Consegna" per l'avanzamento logistico.

### 13.2 Consegne parziali dallo stesso ordine

1. Prima evasione: solo una parte delle quantità → primo DDT.
2. Più tardi: torna sull'ordine ed evadi il residuo → secondo DDT.
3. Quando il residuo è esaurito, l'ordine risulta `EVASO`.

### 13.3 DDT standalone di solo trasporto

1. Nuovo DDT → cliente → righe **senza prezzo** (solo articolo e quantità).
2. Compila causale, vettore, colli/pesi e l'indirizzo di consegna.
3. "Emetti" → PDF di trasporto (nessun riepilogo IVA).

### 13.4 Bozza creata per errore

1. DDT ancora in `DRAFT` **senza righe/indirizzi** → eliminabile.
2. DDT **emesso** → non si elimina: usa "Annulla" (→ `ANNULLATO`).

---

## 14. Errori principali

Codici sollevati dal dominio DDT (registrati in `error_policies`):

| Codice                               | Quando                                                                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `E_DDT_NOT_FOUND`                    | DDT (o riga/componente) inesistente o fuori dal proprio scope emittente                                      |
| `E_DDT_VALIDAZIONE`                  | Payload non valido (campi vuoti, valori non numerici…)                                                       |
| `E_DDT_CLIENTE_IMMUTABILE`           | Tentativo di cambiare il cliente di un DDT fuori bozza (guard DB)                                            |
| `E_DDT_CLIENTE_OBBLIGATORIO`         | Emissione senza cliente con una causale che manda merce a un cliente (guard DB)                              |
| `E_DOC_CLIENTE_DIVERSO_DA_BA`        | Destinatario o utility diversi da quelli del cliente scelto (guard DB)                                       |
| `E_DOC_CLIENTE_DIVERSO_DA_SORGENTE`  | Cliente diverso da quello dell'ordine o del reso di origine (guard DB)                                       |
| `E_DDT_STATO_TRANSIZIONE`            | Operazione non ammessa nello stato (modifica fuori da `DRAFT`, delete di una bozza con righe → va annullata) |
| `E_DDT_NESSUNA_RIGA`                 | Push senza righe eleggibili                                                                                  |
| `E_DOC_EMITTENTE_BA_INCOERENTE`      | L'azienda che emette non è quella del cliente (stesso codice per i sei documenti di vendita)                 |
| `E_STATO_DDT_TRANSIZIONE_NON_VALIDA` | Cambio di stato non previsto/attivo nella matrice (guard DB)                                                 |
| `E_DDT_RIGA_EVASA_FERMA`             | Articolo, unità di misura o quantità cambiati su una riga evasa da un ordine o da un reso (guard DB): la quantità passa da «Correggi quantità evasa» |
| `E_DDT_RIGA_NON_EVASA`               | «Correggi quantità evasa» su una riga aggiunta a mano o su una bolla senza origine                            |
| `E_QTA_SUPERA_RESIDUO`               | La quantità evasa corretta supera il residuo dell'ordine                                                      |
| `E_DOC_ANNULLO_CON_LEGAMI`           | Annullo di una bolla con legami (ordini, resi, righe di commessa): apre la finestra di conferma (§4.3)        |
| `E_INDIRIZZO_DOC_OBBLIGATORIO`       | Emissione senza l'indirizzo di consegna obbligatorio (guard DB)                                              |
| `E_DOCUMENTI_*`                      | Stampa: template/versione non risolti, input invalido o render fallito                                       |

---

## 15. Pattern e principi di design

### 15.1 Clone strutturale dell'ordine

Il DDT è, per costruzione, un **gemello dell'ordine** (`ddt_service` clona
`ordini_service`): stessa impronta di testata/righe/componenti, stessa matrice
data-driven, stesse note. Cambia la **logica**: dati di trasporto, indirizzo di
consegna obbligatorio, numero all'emissione, prezzo di riga opzionale.

### 15.2 Numero all'emissione (non alla nascita)

L'ordine nasce numerato; il DDT no. Il DDT riceve il numero solo quando **esce
davvero** (emissione), coerentemente con la sua natura fiscale. Prima è una bozza
senza identità documentale.

### 15.3 Evasione append-only + residuo

L'evasione non "consuma" la riga d'ordine: **aggiunge** una quantità evasa
(`ordini_righe_fulfillment`), lasciando lo storico intatto e il residuo
calcolabile. È l'invariante su cui si innesta anche il motore **resi** (che
riapre il residuo per la ri-consegna).

La quantità evasa fotografa ciò che è **spedito**: finché la bolla è in bozza
non è partito niente, e la quantità si corregge (dal solo verbo, insieme alla
riga) o si ritira (togliendo la riga, o annullando la bolla). Fuori bozza è
ferma, e l'unico modo di farla tornare da evadere è l'annullo della bolla.

### 15.4 Emittente legato allo user, etichetta dal soggetto

L'emittente è dell'operatore (non "indovinato" dal cliente), memorizzato sul
documento, con reti di sicurezza DB. A video si mostra la **ragione sociale del
soggetto** emittente, mai il codice tecnico.

### 15.5 Trigger DB come ultima difesa

Cliente e destinatario fermi dopo la bozza, transizioni ammesse, indirizzo di consegna
obbligatorio all'emissione, coerenza emittente/cliente, numero immutabile: sono
tutte regole presidiate da trigger DB. Il backend ha controlli equivalenti solo
per dare messaggi chiari prima del giro al database.

---

## 16. Glossario rapido

| Termine                           | Significato                                                                                                                      |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **DDT**                           | Documento di trasporto: accompagna la merce. Stati: `DRAFT` → `EMESSO` → `SPEDITO` → `CONSEGNATO` (→ `RESO`), oppure `ANNULLATO` |
| **Evasione**                      | Consegna delle righe di un ordine confermato in uno o più DDT (1:N, per quantità, con residuo)                                   |
| **Residuo**                       | Quantità di riga d'ordine non ancora evasa (`quantità − Σ evaso`), append-only                                                   |
| **Emetti**                        | Assegnazione numero + generazione PDF, in un'unica operazione (richiede l'indirizzo di consegna)                                 |
| **DDT di solo trasporto**         | DDT con righe senza prezzo: documenta il movimento merce, nessun riepilogo IVA                                                   |
| **Indirizzo di consegna (`CON`)** | Ancora del DDT, obbligatoria all'emissione; snapshot congelato sul documento                                                     |
| **Push a commessa**               | Invio delle righe eleggibili a una commessa, che avvia la fatturazione (sorgente `DDT_VENDITA`)                                  |
| **Destinatario**                  | Chi riceve fisicamente la merce; ancora di provenienza degli indirizzi documento                                                 |
| **Matrice transizioni**           | `config.transizioni_stati_ddt`: fonte unica di verità per UI ed enforcement                                                      |

---

*Per il dettaglio tecnico delle API REST, formati payload e codici errore vedi la
[documentazione API DDT](/backend/vendite/manual/api_ddt). Le decisioni di
modello sono raccolte negli addendum di sviluppo
(`dev/work-done/brief-db-ddt-vendita-evasione-e-stati.md`,
`brief-db-ddt-emittente-user-e-etichetta-soggetto.md`) e, per il reso, nei brief
della slice resi (`dev/work-done/brief-db-resi-vendita.md`,
`dev/work-done/brief-be-fe-resi-vendita.md`).*

{% include-markdown "signature-core.md" %}
