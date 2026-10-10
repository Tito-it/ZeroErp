# Brief DB — Le righe di un DDT nato da un ordine

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-10, dal collaudo a video di Tid. **A chi:**
> team DB; poi BE/FE (§6).
> **Stato:** 📝 **aperto, decisioni di Tid chiuse il 2026-10-10 (§4), nessun codice.**
> **Nel registro dei difetti DB:** voce **D28** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui.

## 1. La domanda

Su un DDT generato da un ordine, che cosa si cambia in bozza? Le righe evase, cioe' quelle che
portano il legame con una riga d'ordine, si modificano? Se ne aggiungono altre a mano?

## 2. Che cosa c'e' oggi (contratto, letto dalla doc auto-generata)

* **L'evasione** (`vendite.fn_genera_ddt_da_ordine(p_ordine_id, p_righe, p_data)`) crea **sempre una
  bolla nuova** in `DRAFT`: righe, componenti e una riga di `vendite.ordini_righe_fulfillment`
  `(ordine_riga_id, ddt_riga_id, qta_evasa)` per riga. Poi proietta lo stato dell'ordine
  (`CONFERMATO`/`PARZIALMENTE_EVASO`/`EVASO`). Oltre il residuo rifiuta con `E_QTA_SUPERA_RESIDUO`.
* **Il guard del legame** `vendite.trgfn_ordini_ful_guard_consistenza` (articolo, UoM, residuo,
  cliente) e' montato **solo su `ordini_righe_fulfillment`**. Scatta quando il legame si scrive, non
  quando cambia la riga di DDT.
* **Su `vendite.ddt_righe`, in bozza:**

  | Operazione su una riga evasa | Oggi |
  | --- | --- |
  | cancellarla | ⛔ `E_DELETE_BLOCKED_FUL` (`trgfn_dlt_block_ordrig_ddtrig`) |
  | cambiarne quantita', articolo, UoM | ✅ passa, nessuno ricontrolla il fulfillment |
  | aggiungere una riga a mano | ✅ passa |

  Fuori bozza tutto e' fermo (`trgfn_doc_righe_lock_fuori_bozza`).
* **L'invariante del brief dell'evasione**
  ([brief-db-ddt-vendita-evasione-e-stati](../work-done/brief-db-ddt-vendita-evasione-e-stati.md)
  §4 e invariante 1): «`qta_evasa` e' immutabile, append-only». E' la fotografia di cio' che e' stato
  spedito con quel DDT; il reso non la scala, e' un movimento a parte. ⚠️ Nessun lock a DB la presidia:
  `ordini_righe_fulfillment` ha guard, storico e `require_attivo`, non un lock di colonna.
* **Il magazzino** (Lotto 3) **non e' toccato da questo brief e regge gia' le modifiche in bozza**:
  la riga e' l'unita' commerciale, i prelievi (`ddt_righe_prelievi`) quella fisica, e la coerenza
  fra i due la controlla l'emissione (`fn_check_ddt_merce`: somma dei prelievi = quantita' della riga,
  disponibilita'). Il legame con l'**ordine** invece non lo controlla nessuno.

## 3. Perche' e' un difetto, sul modello

* **La quantita' della riga evasa e la `qta_evasa` divergono in silenzio.** Ordine pippo 10, evasi
  10, poi in bozza la riga passa a 6: il magazzino scarica 6, l'ordine resta evaso per 10, e i 4
  mancanti non tornano nel residuo. Nessun errore.
* **L'articolo della riga evasa puo' cambiare.** La riga d'ordine dell'articolo A risulta evasa da
  una riga di DDT che consegna B: e' il caso che il guard del legame rifiuta alla generazione.
* **Per consegnare meno del generato non c'e' una strada.** La riga evasa non si cancella, e il
  verbo d'evasione non aggiunge righe a una bolla esistente: resta solo eliminare la bozza e
  rigenerarla, perdendo trasporto, indirizzi e prelievi gia' compilati.
* **L'invariante e' scritta in un brief, non nel DB.**

⚠️ Nessuna di queste ragioni dipende da quante righe ci sono oggi in quello stato.

## 4. Decisioni di Tid (2026-10-10)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-1** | La riga evasa si modifica liberamente? | ⛔ **No.** Articolo, UoM e quantita' di una riga legata a un fulfillment sono **fermi**: sono la fotografia di cio' che si evade |
| **D-2** | Come si consegna meno del generato (ordine 10, bolla 6)? | Con un **verbo DB «correggi la quantita' evasa»**, ammesso **solo in bozza** e **solo sui DDT nati da un ordine**: cambia nella stessa operazione la quantita' della riga e la sua `qta_evasa`, entro il residuo, e riproietta lo stato dell'ordine. L'invariante non si rompe nel suo significato: `qta_evasa` fotografa cio' che e' **spedito**, e una bozza non e' partita |
| **D-3** | La riga evasa si toglie? | ✅ **Si', in bozza**, col ritiro del suo fulfillment: il residuo torna all'ordine e lo stato si riproietta. Fuori bozza resta fermo |
| **D-4** | `qta_evasa` fuori bozza? | ⛔ **Ferma**, con un lock dichiarato a DB (l'invariante del brief dell'evasione, finalmente scritta) |
| **D-5** | Righe aggiunte a mano su un DDT da ordine? | ✅ **Ammesse** (es. ordine pippo 10, bolla 15: riga evasa 10 + riga a mano pippo 5). Non sono legate all'ordine; vanno al cliente della bolla, che e' quello dell'ordine (D-6 di `brief-db-esecutivi-ba-coppia`) |

## 5. Forma proposta (la sceglie il team DB)

1. **Guard su `vendite.ddt_righe` (UPDATE):** se la riga ha un fulfillment, `articolo_id`,
   `uom_operativa_id`, `quantita` e `qta_operativa` non cambiano, con un codice registrato. Il guard
   deve lasciar passare il verbo del punto 2 (porta del verbo, come le altre GUC-porta dei verbi DDT).
2. **Il verbo** `vendite.fn_ddt_riga_correggi_qta_evasa(p_ddt_riga_id, p_qta_operativa)` (nome di
   lavoro):
   * solo DDT in `DRAFT` con sorgente `ORDINE_VENDITA`; solo righe con fulfillment;
   * nuova quantita' `> 0` ed entro il residuo dell'ordine (stessa formula di
     `fn_ordine_ha_residuo_evasione`, reso-aware), lock come nel guard del legame;
   * aggiorna riga (quantita', e i componenti tramite la propagazione gia' esistente) e `qta_evasa`
     nella stessa transazione; riproietta lo stato dell'ordine.
   * ⭐ **Regola del 2**: la proiezione dello stato dell'ordine oggi sta dentro
     `fn_genera_ddt_da_ordine`. Con il verbo (e col ritiro del punto 3) i consumatori diventano piu'
     d'uno: si estrae in un BB, adottato anche da `fn_genera_ddt_da_ordine`, nello stesso giro.
3. **Cancellazione in bozza:** `trgfn_dlt_block_ordrig_ddtrig`, ramo 2a (`E_DELETE_BLOCKED_FUL`),
   diventa: in bozza la riga si cancella e il suo fulfillment si ritira con lei (poi la proiezione
   del punto 2); fuori bozza resta com'e' (e comunque parla prima il lock delle righe).
   ⚠️ Il ramo 2b (riga usata da resi o riconsegne) resta: in bozza non ci sono resi.
4. **Lock su `ordini_righe_fulfillment.qta_evasa`** fuori bozza del DDT (D-4), con lo stesso porta
   del verbo in bozza. Forma: un BB di lock o una riga di `dbops.automation_lock_columns`, secondo
   cosa serve per l'eccezione «in bozza, solo dal verbo».
5. **Capability:** la riga deve dire al form che cosa e' fermo e se la quantita' passa dal verbo
   (per esempio `evasa`, o i campi fermi per riga nella vista del dettaglio righe). Il FE la legge,
   non ricopia la regola.
6. **Codici** nuovi registrati, con policy e frase di ripiego: guard della riga evasa; verbo fuori
   perimetro (stato, sorgente, riga senza fulfillment); quantita' oltre il residuo riusa
   `E_QTA_SUPERA_RESIDUO`.

### 5.1 Fuori da qui

* **I DDT di riconsegna** (da reso, `fn_genera_ddt_riconsegna`, legame in `resi_righe_riconsegne`):
  Tid ha deciso il verbo **solo per i DDT da ordine**. Le righe di riconsegna restano come oggi; se
  servira' la stessa domanda, sara' un brief suo.
* Il magazzino (Lotto 3): invariato, l'emissione ricontrolla i prelievi sulla quantita' nuova.

### 5.2 pgTAP (fixture fabbricati)

* Ordine pippo 10, DDT generato con 10: `UPDATE` diretto della quantita' della riga evasa →
  rifiutato col codice; `UPDATE` dell'articolo → rifiutato.
* Lo stesso col verbo a 6: riga 6, `qta_evasa` 6, ordine `PARZIALMENTE_EVASO`, residuo 4.
* Verbo oltre il residuo (con un secondo DDT gia' evaso sulla stessa riga) → `E_QTA_SUPERA_RESIDUO`.
* Verbo su un DDT emesso, su un DDT standalone, su una riga a mano → rifiutato.
* Cancellazione della riga evasa in bozza: fulfillment ritirato, residuo 10, stato `CONFERMATO`.
* `UPDATE` di `qta_evasa` su un DDT emesso → rifiutato.
* Ordine pippo 10, bolla con riga evasa 10 + riga a mano pippo 5: si emette; l'ordine resta
  `EVASO` per 10.
* Emissione dopo il verbo: i prelievi devono sommare 6 (Lotto 3, invariato).

## 6. Ricaduta BE/FE (dopo la consegna DB)

* Form riga del DDT: sulla riga evasa articolo e UoM spenti, la quantita' chiama il verbo invece del
  salvataggio della riga; il pulsante di cancellazione segue la capability. Righe a mano invariate.
* Service: un metodo per il verbo, codici nuovi con policy e ripiego.
* Guida [gestione-ddt](../../guide/gestione-ddt.md): una sezione «Le righe di un DDT da ordine»
  (righe evase ferme, correzione della quantita', righe a mano, i due esempi pippo 10→15 e 10→6).
