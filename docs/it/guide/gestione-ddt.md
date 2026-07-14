# Guida — Gestione DDT di vendita

> **Ultima revisione**: 14 luglio 2026 — modello del documento di trasporto
> (testata trasporto + righe + componenti BoM + indirizzi di consegna), nascita
> per **evasione** di un ordine (1:N, con residuo per riga) oppure **standalone**
> manuale, azioni **data-driven** via `fn_available_actions_ddt` con matrice
> transizioni in `config.transizioni_stati_ddt`, **numero assegnato all'emissione**
> (non alla nascita), indirizzo di consegna obbligatorio all'emissione, stampa
> PDF con luogo di consegna, push a commessa per la fatturazione.
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
> * [vendite.fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare) — righe eleggibili al push a commessa
> * [vendite.trgfn_ddt_gen_numero_emesso](/dbzero/vendite/funzioni/trgfn_ddt_gen_numero_emesso) / [vendite.trgfn_v_ddt_protect_num](/dbzero/vendite/funzioni/trgfn_v_ddt_protect_num) — numero assegnato a EMESSO e poi immutabile
> * [vendite.trgfn_ddt_guard_indirizzi_obbligatori](/dbzero/vendite/funzioni/trgfn_ddt_guard_indirizzi_obbligatori) — indirizzo di consegna obbligatorio all'emissione
> * [vendite.trgfn_ddt_normalize](/dbzero/vendite/funzioni/trgfn_ddt_normalize) — eredità dal contesto (BA/utility/valuta/emittente)
> * [vendite.trgfn_ddt_default_emittente](/dbzero/vendite/funzioni/trgfn_ddt_default_emittente) / [vendite.trgfn_ddt_guard_emittente_ba](/dbzero/vendite/funzioni/trgfn_ddt_guard_emittente_ba) — emittente fiscale di default e coerenza col cliente
> * [vendite.fn_ddt_riga_componenti_init](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_init) / [vendite.fn_ddt_riga_componenti_preview](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_preview) — componenti BoM
>
> **Vedi anche** — API e service backend:
>
> * [API DDT](/backend/vendite/manual/api_ddt)
> * [API Ordini](/backend/vendite/manual/api_ordini) — la sorgente dell'evasione
>
> **Vedi anche** — guide correlate:
>
> * [Gestione Ordini](/guide/gestione-ordini) — la sorgente del DDT (evasione)
> * [Gestione Commesse](/guide/gestione-commesse) — la destinazione del push
> * [Fatturazione end-to-end](/guide/fatturazione) — il push a commessa avvia la pipeline
> * [Documenti e stampe](/guide/documenti-e-stampe) — generazione del PDF di trasporto
> * [Gestione Istanze Utility](/guide/gestione-delle-istanze-utility) — cliente, billing account, istanza
> * [Gestione Indirizzi documento](/guide/gestione-delle-istanze-utility) — l'indirizzo di consegna del DDT

---

## 1. Cosa è un DDT di vendita

Il DDT (Documento Di Trasporto) è il **documento che accompagna la merce** dal
mittente al destinatario. Risponde alla domanda: *"Cosa stiamo consegnando a
questo cliente, in quali quantità, con quale trasporto e a quale indirizzo?"*

A differenza dell'ordine — che è l'**impegno** commerciale a consegnare e
fatturare — il DDT è l'atto della **consegna vera e propria**: registra la merce
che esce, il vettore, l'aspetto dei beni, i colli e il **luogo di consegna**.

Caratteristiche di base:

- è intestato a un **cliente** (billing account, con il relativo soggetto) e ha
  un **destinatario** (chi riceve fisicamente la merce), oltre a **mittente** e
  **vettore** opzionali;
- raccoglie **righe** (articolo, quantità, ed eventualmente prezzo/IVA) e
  **componenti BoM** per gli articoli compositi;
- porta i **dati di trasporto** (causale, aspetto dei beni, modalità di addebito,
  colli, pesi, volume, targa, autista, tracking);
- porta gli **indirizzi di consegna** (snapshot congelato all'emissione);
- ha un **ciclo di vita** logistico: bozza → emesso → spedito → consegnato
  (→ reso), oppure annullato;
- nasce quasi sempre per **evasione** di un ordine, ma può essere creato
  **standalone** a mano;
- all'emissione produce il **PDF di trasporto** con il luogo di consegna;
- può essere **spinto in commessa** (push) per la fatturazione.

> **Il numero si assegna all'EMISSIONE, non alla nascita.** A differenza
> dell'ordine (che nasce già numerato), il DDT resta **senza numero in bozza** e
> lo riceve solo quando viene **emesso** (trigger `trgfn_ddt_gen_numero_emesso`).
> Da quel momento il numero è **immutabile** (`trgfn_v_ddt_protect_num`). È
> coerente con la natura fiscale del documento di trasporto: un DDT numerato è un
> documento "vero" che ha lasciato il magazzino.

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
> (guard DB `trgfn_dlt_block_ordrig_ddtrig`): la merce risulta in consegna.

### 2.2 Standalone (creazione manuale)

È possibile creare un DDT **da zero**, scegliendo il cliente (billing account) e
le righe a mano. In questo caso il DDT nasce senza riferimento a un ordine di
origine (`sorgente_tipo_id`/`sorgente_uid` NULL). Il cliente è **obbligatorio**
alla creazione: da lì il sistema deriva destinatario ed emittente.

---

## 3. Le entità in gioco

### 3.1 Testata `ddt`

Contiene il contesto del documento e del trasporto:

- **chi** (`billing_account_id`) — il cliente; **a chi si consegna**
  (`destinatario_soggetto_ruolo_id`) — derivato dal cliente se non indicato.
- **chi emette** (`emittente_fiscale_id`) — l'emittente fiscale (vedi §7).
- **per cosa** (`utility_id`) e **valuta** (`valuta_id`) — opzionali.
- **quando** (`data`) — default alla data odierna.
- **trasporto**: `causale_trasporto_id`, `aspetto_bene_id`,
  `modalita_addebito_trasporto_id`, `mittente_soggetto_ruolo_id`,
  `vettore_soggetto_ruolo_id`, `num_colli`, `peso_lordo`, `peso_netto`, `volume`,
  `targa`, `autista`, `tracking_code`.
- **da dove arriva** (`sorgente_tipo_id` + `sorgente_uid`) — valorizzata
  dall'evasione (sorgente `ORDINE_VENDITA`); NULL se il DDT è standalone.
- **identità e stato** (`numero`/`anno` — assegnati a EMESSO —, `uid`,
  `stato_doc_ddt_id`).

### 3.2 Righe `ddt_righe`

Ogni riga è una voce di merce consegnata:

- **articolo** (`articolo_id`) e **descrizione**;
- **quantità** in doppia unità: **operativa** (`qta_operativa` +
  `uom_operativa_id`) e **base** (`quantita`, calcolata da `factor_to_base`);
- **prezzo** (`prezzo_unitario`) e **IVA** (`iva_id`) — **opzionali**: un DDT può
  essere di **solo trasporto** (righe senza prezzo).

> **Prezzo opzionale = DDT di solo trasporto.** Se le righe non hanno prezzo, il
> DDT documenta solo il movimento della merce e il *Riepilogo IVA* resta vuoto
> (le righe senza prezzo sono escluse in vista). Con i prezzi valorizzati, il DDT
> espone anche il riepilogo per aliquota, come gli altri documenti.

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

### 4.1 Stati

Il catalogo `config.stati_doc_ddt` prevede sei stati:

| Stato | Significato | Modificabile? | Terminale? | In uso oggi |
|---|---|---|---|---|
| `DRAFT` | Bozza in preparazione | Sì: testata e righe | No | ✅ |
| `EMESSO` | Documento emesso: numero assegnato, PDF prodotto | No | No | ✅ |
| `SPEDITO` | Merce partita (vettore/tracking) | No | No | ✅ |
| `CONSEGNATO` | Merce consegnata al destinatario | No | No | ✅ |
| `RESO` | Merce resa (totale) | No | — | 🔄 motore **resi** (slice in corso) |
| `ANNULLATO` | Bozza/emesso annullato | No | Sì | ✅ |

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

- **DRAFT → EMESSO** (*emetti*): assegna il numero e genera il PDF; richiede
  l'**indirizzo di consegna** (guard DB, vedi §9/§10).
- **EMESSO → SPEDITO** (*spedisci*) e **SPEDITO → CONSEGNATO** (*consegna*):
  avanzamento logistico manuale, con conferma.
- **DRAFT → ANNULLATO** ed **EMESSO → ANNULLATO** (*annulla*): consentiti.
- **CONSEGNATO → RESO** e **RESO → CONSEGNATO**: **automatiche**, guidate dal
  **motore resi** (non pulsanti manuali). Il vecchio "Reso" manuale e la
  transizione `SPEDITO → RESO` sono **disabilitati**. Il reso — parziale/totale,
  a credito o per ri-consegna — è materia della **slice RESI** (in corso): il
  DDT entra in `RESO` solo per effetto del motore, su reso **totale**. Vedi la
  guida/brief resi.

### 4.3 La doppia difesa

1. **In interfaccia**: `fn_available_actions_ddt` legge la matrice e restituisce
   solo le azioni disponibili — i pulsanti senza senso non compaiono.
2. **Nel database**: il trigger `trgfn_ddt_guard_transizione` rifiuta qualsiasi
   cambio di stato non previsto; `trgfn_ddt_guard_indirizzi_obbligatori` blocca
   l'emissione senza indirizzo di consegna.

---

## 5. Azioni disponibili

Le azioni eseguibili sono calcolate dal database (`fn_available_actions_ddt`) ed
esposte come *capability*, così il frontend non replica la logica degli stati.

| Flag | Vero quando |
|---|---|
| `can_edit_testata` / `can_edit_righe` | il DDT è in `DRAFT` |
| `can_push_commessa` (+ `_reason`/`_reason_key`) | ci sono righe eleggibili al push |
| `non_editable_fields` | l'elenco dei campi bloccati (es. cliente, numero) |

In sintesi:

- **In `DRAFT`**: si **modificano** testata e righe, si **emette** o si
  **annulla**.
- **In `EMESSO`/`SPEDITO`/`CONSEGNATO`**: testata e righe **in sola lettura**;
  disponibili l'avanzamento logistico e — se ci sono righe eleggibili — il **push
  a commessa**.
- **In `RESO`/`ANNULLATO`**: sola lettura.

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

1. **Nuovo DDT** → scegli il **cliente** (billing account); da lì il sistema
   deriva il **destinatario**.
2. Il DDT nasce in `DRAFT` **senza numero** (arriverà all'emissione).
3. **Aggiungi le righe** (articolo, quantità; prezzo/IVA se serve fatturare).
4. Compila i **dati di trasporto** e imposta l'**indirizzo di consegna**.

> **Bozza "usa e getta".** La creazione salva subito una bozza (auto-save al
> primo cliente) per poter aggiungere righe e indirizzi. Se l'operatore esce
> senza inserire nulla, la bozza vuota può essere eliminata. Un DDT **emesso**
> non si cancella: si **annulla**.

---

## 7. Cliente, destinatario ed emittente fiscale

### 7.1 Cliente e destinatario immutabili

Una volta creato il DDT, **cliente e destinatario non si cambiano più**
(`billing_account_id` bloccato). Il DDT denormalizza il cliente sul billing
account **e** sul destinatario: cambiare il BA lascerebbe il destinatario
stantìo. La regola è **"cambiare cliente = nuovo DDT"**. Il blocco è applicato
dal backend e, in modo autoritativo, dal database.

### 7.2 Emittente fiscale (legato allo user)

L'emittente del DDT è **legato all'operatore**, come ordini/preventivi/contratti
(uniformazione 2026-07-13). L'interfaccia lo prefilla dal **profilo
dell'operatore** (l'admin globale lo sceglie da un elenco) e lo invia col
documento. La colonna resta **memorizzata** sul DDT (con scope RLS per
emittente). Reti di sicurezza a DB:

- se l'operatore non lo indica, lo imposta `trgfn_ddt_default_emittente`
  (dal contesto utente; per i DDT da evasione è **ereditato dall'ordine**);
- se il DDT ha un cliente, l'emittente deve essere **coerente** con esso:
  `trgfn_ddt_guard_emittente_ba` rifiuta le combinazioni incoerenti.

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

- nell'**evasione** eredita il prezzo "fotografato" sulla riga d'ordine;
- nello **standalone** l'operatore può digitarlo (o lasciarlo vuoto per un DDT di
  solo trasporto);
- se assente e l'articolo non è composito, può essere risolto dal listino
  tramite il *PricingService*, come negli altri documenti.

### 8.2 Totali e Riepilogo IVA

Quando le righe hanno prezzo, i totali e il **Riepilogo IVA** (una riga per
aliquota) sono calcolati dal database dalla vista dedicata
`vw_ddt_riepilogo_iva_dettaglio` (le righe senza prezzo sono escluse). Se il DDT
è di solo trasporto, il riepilogo resta vuoto e nascosto.

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

- alla creazione, il sistema **auto-assegna** l'indirizzo di consegna di default
  del cliente (indirizzo di ruolo `CON`, con fallback `FATT`), best-effort;
- l'operatore può cambiarlo dal pannello indirizzi: sceglierne uno
  dall'anagrafica del cliente ("usa questo") o inserire un **indirizzo libero**
  una-tantum;
- al momento dell'emissione lo slot viene **congelato** come snapshot: il PDF e
  il documento riportano l'indirizzo fotografato, indipendente da modifiche
  successive all'anagrafica.

L'ancora di provenienza del DDT è il **destinatario** (chi riceve la merce), non
il billing account: regge anche i DDT verso terzi e i casi con prospect senza BA.

---

## 11. Push a commessa

Quando il DDT è emesso e ha righe eleggibili, l'azione **push a commessa** invia
le righe alle **attività fatturabili** su una commessa (sorgente `DDT_VENDITA`),
che a sua volta alimenta la pipeline di fatturazione. Le righe eleggibili sono
quelle attive, con quantità positiva, non ancora inviate a una commessa
(`fn_list_ddt_da_pushare`).

> **XOR con l'ordine.** Una stessa merce si fattura **una volta sola**: se la
> fatturazione avviene per DDT non avviene anche per l'ordine di origine, e
> viceversa. Il percorso (fatturazione all'ordine oppure al DDT) dipende dalla
> configurazione del ciclo; il push a commessa è comunque l'unico punto che
> apre la fatturazione. Dettagli in [Gestione Commesse](/guide/gestione-commesse)
> e [Fatturazione](/guide/fatturazione).

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

| Codice | Quando |
|---|---|
| `E_DDT_NOT_FOUND` | DDT (o riga/componente) inesistente o fuori dal proprio scope emittente |
| `E_DDT_VALIDAZIONE` | Payload non valido (cliente mancante, campi vuoti, valori non numerici…) |
| `E_DDT_CLIENTE_IMMUTABILE` | Tentativo di cambiare cliente/destinatario di un DDT già creato |
| `E_DDT_STATO_TRANSIZIONE` | Operazione non ammessa nello stato (modifica fuori da `DRAFT`, delete di una bozza con righe → va annullata) |
| `E_DDT_NESSUNA_RIGA` | Push senza righe eleggibili |
| `E_DDT_EMITTENTE_BA_INCOERENTE` | Emittente non coerente col cliente selezionato |
| `E_STATO_DDT_TRANSIZIONE_NON_VALIDA` | Cambio di stato non previsto/attivo nella matrice (guard DB) |
| `E_INDIRIZZO_DOC_OBBLIGATORIO` | Emissione senza l'indirizzo di consegna obbligatorio (guard DB) |
| `E_DOCUMENTI_*` | Stampa: template/versione non risolti, input invalido o render fallito |

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

### 15.4 Emittente legato allo user, etichetta dal soggetto

L'emittente è dell'operatore (non "indovinato" dal cliente), memorizzato sul
documento, con reti di sicurezza DB. A video si mostra la **ragione sociale del
soggetto** emittente, mai il codice tecnico.

### 15.5 Trigger DB come ultima difesa

Cliente/destinatario immutabili, transizioni ammesse, indirizzo di consegna
obbligatorio all'emissione, coerenza emittente/cliente, numero immutabile: sono
tutte regole presidiate da trigger DB. Il backend ha controlli equivalenti solo
per dare messaggi chiari prima del giro al database.

---

## 16. Glossario rapido

| Termine | Significato |
|---|---|
| **DDT** | Documento di trasporto: accompagna la merce. Stati: `DRAFT` → `EMESSO` → `SPEDITO` → `CONSEGNATO` (→ `RESO`), oppure `ANNULLATO` |
| **Evasione** | Consegna delle righe di un ordine confermato in uno o più DDT (1:N, per quantità, con residuo) |
| **Residuo** | Quantità di riga d'ordine non ancora evasa (`quantità − Σ evaso`), append-only |
| **Emetti** | Assegnazione numero + generazione PDF, in un'unica operazione (richiede l'indirizzo di consegna) |
| **DDT di solo trasporto** | DDT con righe senza prezzo: documenta il movimento merce, nessun riepilogo IVA |
| **Indirizzo di consegna (`CON`)** | Ancora del DDT, obbligatoria all'emissione; snapshot congelato sul documento |
| **Push a commessa** | Invio delle righe eleggibili a una commessa, che avvia la fatturazione (sorgente `DDT_VENDITA`) |
| **Destinatario** | Chi riceve fisicamente la merce; ancora di provenienza degli indirizzi documento |
| **Matrice transizioni** | `config.transizioni_stati_ddt`: fonte unica di verità per UI ed enforcement |

---

*Per il dettaglio tecnico delle API REST, formati payload e codici errore vedi la
[documentazione API DDT](/backend/vendite/manual/api_ddt). Le decisioni di
modello sono raccolte negli addendum di sviluppo
(`dev/work-done/brief-db-ddt-vendita-evasione-e-stati.md`,
`brief-db-ddt-emittente-user-e-etichetta-soggetto.md`) e, per il reso, nel brief
della slice resi (`dev/work-in-progress/brief-db-resi-vendita.md`).*

{% include-markdown "signature-core.md" %}
