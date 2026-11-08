## 📘 Documentazione Concettuale – Funzione `vendite.fn_genera_ddt_riconsegna`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne) — il ponte che chiude la voce di coda
> * [vendite.resi](/dbzero/vendite/tabelle/resi) — il reso, da cui la bolla nasce
>
> Approfondimento viste:
>
> * [vendite.vw_resi_da_riconsegnare](/dbzero/vendite/views/vw_resi_da_riconsegnare) — la coda di ri-consegna
> * [vendite.vw_partite_merce](/dbzero/vendite/views/vw_partite_merce) — perché la ri-consegna non si rifattura
>
> Approfondimento funzioni:
>
> * [vendite.fn_genera_ddt_da_ordine](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine) — il gemello, sullo stesso stile
> * [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso) — la conferma del reso
> * [vendite.fn_ddt_trigger_ordine_testata](/dbzero/vendite/funzioni/fn_ddt_trigger_ordine_testata) — l'ordine e la sua corsia, ritrovati dal fulfillment
> * [script.fn_sorgente_provenienza](/dbzero/script/funzioni/fn_sorgente_provenienza) — la provenienza da scrivere, dal reso
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

**Funzione madre atomica** (`SECURITY INVOKER`) che genera il **DDT di ri-spedizione** per un reso
CONFERMATO e chiude l'aggancio duro con la coda di ri-consegna.

Restituisce l'id della bolla. `p_righe` dice, per riga di reso, la quantità per una ri-spedizione
**parziale**; vuoto = tutta la copertura residua. `p_data` vuota = la data operativa.

---

### Logica

1. Guard: reso in stato CONFERMATO (`E_RESO_NON_CONFERMATO`).
2. Nuovo **DDT DRAFT** che **eredita la testata** del DDT d'origine (sezione «L'eredità» qui
   sotto): destinatario, billing/utility/valuta/emittente, e il blocco
   **relazione** — causale di trasporto, aspetto dei beni, modalità di addebito, mittente,
   vettore, `fatturazione_immediata`.
   ⭐ **La bolla nasce dal reso**, sempre: la provenienza è `RESO_VENDITA` con la chiave del reso
   (calcolata una volta da `script.fn_sorgente_provenienza`), e ogni riga porta il reso e la sua
   riga (`sorgente_riga`). Vale anche per il reso **order-backed** (righe con `ordine_riga_id`):
   il legame con l'ordine da cui la merce era partita resta nel fulfillment, e la sua corsia di
   fatturazione la ritrova `vendite.fn_ddt_trigger_ordine_testata`.
3. **Cascata indirizzi**: copia 1:1 gli snapshot di ambito `DDT` dal documento d'origine, con
   gli `origine_*` propagati — modellata sul passo 4-bis del gemello
   [`fn_genera_ddt_da_ordine`](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine). Senza indirizzi
   il guard alzerebbe `E_INDIRIZZO_DOC_OBBLIGATORIO` su un documento che il database ha generato da sé.
4. Per ogni riga *ri-consegna* con copertura residua — letta dall'helper unico
   [`fn_resi_riga_residuo_riconsegna`](/dbzero/vendite/funzioni/fn_resi_riga_residuo_riconsegna),
   cioè `quantità resa − Σ ri-spedito − Σ rinunciato`: crea la `ddt_righe` (articolo, descrizione,
   UoM, quantità — e nel **solo ramo standalone** anche prezzo, sconto e aliquota, vedi sotto) e
   inserisce la riga-ponte `resi_righe_riconsegne` → **chiude la voce di coda**.
5. Se la riga reso ha `ordine_riga_id`: inserisce anche `ordini_righe_fulfillment` → **richiude il
   residuo** dell'ordine (il guard fulfillment è reso-aware, non blocca).
6. **Ri-proietta lo stato ordine** (come `fn_genera_ddt_da_ordine`): dopo la ri-spedizione l'ordine
   torna `EVASO`/`PARZIALMENTE_EVASO` coerente.

Idempotenza per copertura (righe già coperte saltate); niente ri-consegna pendente →
`E_RESO_NESSUNA_RICONSEGNA_PENDENTE` (rollback della testata DDT orfana). Funziona anche per lo
standalone: la coda è agganciata al DDT, non all'ordine.

---

### Non ri-spedisce la quota dichiarata definitiva

Con la chiusura ri-consegna
([`fn_chiudi_riconsegna_reso`](/dbzero/vendite/funzioni/fn_chiudi_riconsegna_reso)), il
residuo che questa funzione legge è **al netto delle rinunce**. Su una riga da 10 con 7
dichiarati definitivi, una richiesta di 10 viene troncata a 3; se tutto è rinunciato la riga
viene saltata fino a `E_RESO_NESSUNA_RICONSEGNA_PENDENTE`.

Il guard del ponte bloccherebbe comunque l'INSERT: la differenza è che la
**quantità è corretta in partenza**, invece di essere una proposta che il guard rifiuta a
valle di un DDT già creato. Difesa in profondità che resta, più correttezza a monte.

Le due funzioni sono le **due uscite della stessa attività**: la merce torna al cliente,
oppure no.

---

### ⭐ L'eredità: cosa il documento porta con sé, e cosa no

La regola — *«il documento figlio eredita la testata del padre»* — è la stessa del gemello che
parte da un ordine: il generatore che parte dalla sorgente **più ricca**, un DDT, non copia meno
di quello che parte dalla più povera.

#### Il criterio, in una riga

> **Eredita ciò che è una SCELTA; non ereditare ciò che è una MISURA.**
> Una scelta vale finché non la si cambia; una misura vale per il viaggio in cui è stata presa.

#### ✅ Eredita — «la relazione»

Descrivono **con chi e perché** la merce si muove, e sono le stesse per il viaggio di andata e
per la ri-consegna: è la stessa relazione commerciale eseguita una seconda volta.

| Colonna | Perché eredita |
|---|---|
| `causale_trasporto_id` | il *perché* del movimento non cambia. È obbligatoria all'emissione e **immutabile** dopo: lasciarla vuota non rimandava una scelta, la spostava su un operatore che non ha il contesto |
| `aspetto_bene_id` | la merce è **la stessa merce**, tornata indietro |
| `modalita_addebito_trasporto_id` | patto sulle spese, non fatto del viaggio |
| `mittente_soggetto_ruolo_id` | spedisce lo stesso soggetto |
| `vettore_soggetto_ruolo_id` | ⭐ vedi il riquadro qui sotto |
| `fatturazione_immediata` | **corsia di instradamento**, non un cancello: la doppia fatturazione è impedita altrove (`vw_partite_merce` / `fn_list_ddt_da_pushare`), quindi è un patto commerciale come gli altri |
| **indirizzi** (ambito `DDT`) | cascata 1:1 dal documento d'origine |

> **⭐ Il vettore: un campo vuoto che il documento AFFERMA**
>
> Sembrava il caso di confine — il vettore è insieme una scelta (l'accordo con quel corriere) e
> un fatto del viaggio — finché non si è guardato **come la stampa rende il vuoto**:
> `template-ddt-vendita.html` scrive `{{ vettore_denominazione or "Mezzo proprio" }}`.
>
> ⛔ Un `NULL` quindi **non tace**: stampa **«Mezzo proprio»**, cioè afferma che la merce
> viaggia col mezzo del venditore, con sotto il riquadro «Firma vettore». È l'unica colonna del
> blocco dove **non decidere produce comunque una frase** — targa, autista e tracking, se vuoti,
> semplicemente non si stampano.
>
> Il confronto vero non era «campo pieno contro campo vuoto», era **«corriere dell'andata
> contro Mezzo proprio»**: fra due affermazioni non verificate vince quella che nel caso
> ordinario è vera. ⚠️ E il campo resta modificabile in qualunque stato — a differenza della
> causale, sul vettore non c'è nessun guard di immutabilità: un corriere ereditato e sbagliato
> si corregge.

#### ⛔ NON eredita — «il viaggio»

Copiarle scriverebbe **fatti falsi** su un documento fiscale di trasporto.

| Colonna | Perché **non** eredita |
|---|---|
| `num_colli`, `peso_lordo`, `peso_netto`, `volume` | ⛔ **sbagliati per costruzione, non «stantii»**: la ri-consegna porta un **sottoinsieme** delle righe e su quelle una **frazione** della quantità. Un peso copiato è il peso di un collo che non è quello che parte |
| `targa`, `autista` | il mezzo e la persona di un viaggio **già avvenuto** |
| `data_ora_partenza`, `data_ora_consegna_prev` | date di un viaggio concluso, su un documento che nasce in bozza |
| `tracking_code` | ⛔ il peggiore: punterebbe il cliente al **collo precedente**. Un codice di tracciamento copiato non è un campo vuoto, è un'informazione sbagliata data a un terzo |

⚠️ Il presidio è nel pgTAP (`test-fn-genera-ddt-riconsegna-eredita-v1.sql`, asserzione 7): la
testata generata ha quelle colonne a `NULL` **anche quando l'origine le ha valorizzate**. Senza,
«non copiare» è un commento, e il primo che allarga la `INSERT` le porta dentro senza che niente
si accenda.

---

### ⭐ Il valore della riga: standalone sì, order-backed no

La domanda — *«il prezzo della riga dovrebbe essere ereditato?»* — ha **due risposte diverse**,
e la differenza è dove sta la sorgente del numero.

| Ramo | Prezzo / sconto / aliquota | Perché |
|---|---|---|
| **order-backed** | ⛔ **non si copiano**, restano `NULL` | il prezzo si risale a `ordini_righe_fulfillment` **al momento della lettura** (il `COALESCE` di `fn_list_ddt_da_pushare`, lo stesso che fa `fn_check_ddt_emittibile`). Copiarlo creerebbe una **seconda copia di un numero che ha già una sorgente**, e le due divergono al primo cambio di prezzo sull'ordine |
| **standalone** | ✅ **si copiano** dalla riga di DDT d'origine | lì quel secondo termine **non esiste**: la funzione non scrive nessun fulfillment, quindi senza la copia la riga non ha niente da cui ereditare |

⭐ **La sorgente è a un salto solo**: `vendite.resi_righe.ddt_riga_id` è `NOT NULL`, quindi ogni
riga di reso punta alla riga di DDT d'origine — che il prezzo, lo sconto e l'aliquota ce li ha.
È la stessa relazione da cui già arrivano articolo, descrizione e unità di misura.

> ⚠️ **Non è `resi_righe` la sorgente del valore.** Quella tabella il prezzo **non ce l'ha**
> (articolo, descrizione, quantità, UoM, tipo, motivo — nessuna colonna di valore): il reso è
> uno snapshot di **quantità**, non di **valore**. Chi cercasse il prezzo lì concluderebbe che
> «non c'è», mentre sta sulla riga a monte.

⚠️ **L'aliquota è una misura di attesa, non la sede.** Con il risolutore IVA la riga prenderà
l'aliquota **da lì**, come ogni altra riga — il documento a monte proietta, la fattura decide —
e **questa copia va tolta**, o saranno due meccanismi per lo stesso campo. Finché il risolutore
non c'è, copiarla è meglio del `NULL`: una riga con prezzo e senza aliquota entra nel riepilogo
IVA del documento con **imponibile pieno e imposta zero**
([`fn_check_ddt_emittibile`](/dbzero/script/funzioni/fn_check_ddt_emittibile), condizione 3-bis).

---

### ⚠️ Due trappole da conoscere prima di toccare questa funzione

**1. L'eredità di catalogo è filtrata su `attivo`, e non è prudenza generica.**
`vendite.ddt` ha tre trigger `require_active_parent` (causale, aspetto, modalità addebito) e
`vendite.ddt_righe` ne ha uno sull'IVA. Ereditare alla cieca da un DDT vecchio che cita un
elemento **ritirato dopo** farebbe **fallire la generazione della ri-consegna** — un errore duro
al posto di un campo vuoto. Con il filtro, la colonna resta `NULL` e il documento si genera lo
stesso.

> ⭐ *Un'eredità che può impedire la generazione non è una comodità: è un guasto nuovo.*

Vale identico per gli indirizzi: il filtro su `config.tipi_indirizzi_allowed` **sembra**
ridondante — le righe d'origine sono già passate dallo stesso controllo — e non lo è, perché un
tipo ritirato dopo resterebbe sulle righe vecchie e farebbe fallire la copia.

**2. La testata d'origine può mancare, e non si solleva.**
Il documento di partenza si legge con un `LEFT JOIN` sulla provenienza del reso: la bolla ha
chiave `id`, e il reso la porta in `sorgente_id` (`chk_resi_sorgente_forma` vuole `sorgente_uid`
vuota; il tipo `DDT_VENDITA` lo fa valere
[vendite.trgfn_resi_guard_cliente_ddt](/dbzero/vendite/funzioni/trgfn_resi_guard_cliente_ddt)).
Il join resta `LEFT`: una bolla invisibile a chi genera lascia le colonne di testata `NULL`, e i
guard dell'emissione fanno il loro mestiere. Sollevare lì romperebbe un percorso che funziona.

⭐ L'eredità di **riga** invece non ne è toccata: passa da `resi_righe.ddt_riga_id`, che è
`NOT NULL`. ⚠️ E le due possono puntare a **DDT diversi**: nessun guard impone che la riga di
reso appartenga al DDT citato dalla testata del reso. È il motivo per cui il prezzo si legge
dalla riga e non dalla testata — una scorciatoia che funzionerebbe finché nessuno costruisce il
caso che il modello permette.

---

### Il freno della fatturazione non si è allentato

⚠️ Ora che la riga standalone **un prezzo ce l'ha**, vale la pena dirlo esplicitamente: una
ri-consegna **non** viene rifatturata. La riga risulta `stato = 'RICONSEGNA'` con
`differenza IS NULL` in [`vw_partite_merce`](/dbzero/vendite/views/vw_partite_merce), e
`fn_list_ddt_da_pushare` la esclude con un predicato esplicito — **a prescindere** dal prezzo,
dallo stato del DDT e da `fatturazione_immediata`.

L'unico caso in cui una ri-consegna **si** fattura è quello giusto: quando una **nota di
credito** ha accreditato la quantità sulla partita d'origine (`riconsegna_quota_nuova > 0`), cioè
quando la merce è uscita dal fatturato e ri-consegnarla è una vendita nuova.

> ⭐ La non-regressione è presidiata (asserzioni 11 e 12 del pgTAP): un prezzo assente
> nasconderebbe l'esito.

---

### Note di migrazione

* 2026-07-26 — il residuo si legge da `fn_resi_riga_residuo_riconsegna`, al netto delle rinunce.
* 2026-08-28 — la bolla eredita la testata del DDT d'origine (relazione, indirizzi) e, nel ramo
  standalone, il valore della riga: prima nasceva senza causale, indirizzi e blocco trasporto, e
  non si emetteva (brief-db-ddt-riconsegna-eredita-testata).
* 2026-11-06 — la bolla nasce sempre dal reso (`RESO_VENDITA`, con la riga del reso in
  `sorgente_riga`); prima il reso order-backed dichiarava come origine l'ordine, con il suo `uid`
  in testo. La testata d'origine si legge con la regola d'incontro sulla provenienza tipizzata del
  reso (brief-db-sorgente-documento-e-riga).
* 2026-11-08 — la bolla d'origine si legge per `sorgente_id` soltanto: la provenienza del reso è
  solo la bolla (brief-db-sorgente-documento-e-riga, G-3).

---

{% include-markdown "signature-core.md" %}
