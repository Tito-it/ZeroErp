# Brief DB — magazzino: il lotto è dell'azienda

> **⏭️ Chi riparte — aggiornato al 2026-11-22**
>
> **Riparte: Tid**, con le quattro decisioni del §4, da prendere una alla volta. Niente è
> scritto: il brief nasce dalla decisione di Tid del 2026-11-22 (*«lotto b, fare un apposito
> brief»*).
>
> | # | Chi | Che cosa | Dove | Aspetta |
> | --- | --- | --- | --- | --- |
> | 1 | Tid | D-L1 … D-L4 | §4 | — |
> | 2 | team DB | P-0 (censimento al momento di scrivere), poi P-1 … P-4 | §5 | 1 |
> | 3 | Tid | apply, pgTAP col runner | §5 | 2 |
> | 4 | sessione BE | R-1, R-2 | §6 | 3 |
> | 5 | team DB | P-5 (guida del dominio), archiviazione | §5 | 4 |
>
> **Brief vicini verificati (2026-11-22):**
> * `work-in-progress/brief-db-magazzino-tutte-le-scritture-dal-verbo` ha i verbi del lotto
>   (`fn_aggiungi_lotto`, `fn_modifica_lotto`) e la R-1 al BE che li adotta. Da lì nasce questo
>   brief (§5.3);
> * `work-in-progress/analisi-db-magazzino-carico-e-scarico` cita i lotti fra le tabelle «uguali
>   per tutti».
>
> Nessuno copre il tema.

---

**Chi scrive:** team DB (`dev/db-tid`), 2026-11-22. **A chi:** Tid (decisioni, §4), poi team DB;
🔵 richieste a BE in §6.

## 0. In due parole

Un **lotto** è una partita di merce, con un codice e una scadenza. Oggi un lotto appartiene solo
all'articolo, e gli articoli sono comuni a tutte le aziende del gestionale. Il lotto «L-123» di un
articolo è quindi uno solo per tutte le aziende. Da qui tre effetti:
* un'azienda può cambiare la scadenza di un lotto che usa un'altra;
* un'azienda non può disattivare un lotto che un'altra sta usando;
* due aziende non possono avere ciascuna il proprio «L-123» dello stesso articolo.

Tid ha deciso che ogni azienda gestisce i suoi lotti (2026-11-22). Il lotto prende l'azienda, come
i magazzini e i seriali.

## 1. La storia della decisione che si cambia

* **2026-09-14, Lotto 1 del magazzino**
  ([brief-db-magazzino-lotto-1-terreno-vuoto](../work-done/2026/brief-db-magazzino-lotto-1-terreno-vuoto.md),
  §4.3 e M-6). `magazzino.lotti` nasce **fuori dal perimetro RLS**, perché è «una definizione, non ha
  `magazzino_id`, e non ha FK verso tabelle protette». Unicità `(articolo_id, codice)`.
* **2026-09-21, backend.** `test_perimetro_emittente_copertura.py`: *«un lotto è dell'ARTICOLO, […] il
  perimetro emittente qui non esiste come dimensione»*. La lista si legge per articolo.
* **Guida del dominio** (`dbzero/magazzino/_dominio-magazzino.md`, §«Il perimetro»): i lotti restano
  fuori *«per costruzione»*, coi vocabolari.
* **2026-11-22**: chiudendo le scritture sui verbi (brief vicino, §5.3), il verbo di modifica vede i
  figli di tutte le aziende. Il lotto in comune diventa visibile come un fatto di dominio, e **Tid
  sceglie il lotto dell'azienda**.

Il ragionamento del 14-09 resta vero sulla forma: senza `magazzino_id` né emittente, il lotto non
aveva una riga da proteggere. Cambia la premessa di dominio: il lotto non è una definizione
dell'articolo, è un fatto dell'azienda che riceve o produce la merce.

## 2. Il punto di partenza — letto il 2026-11-22

Fatti datati, letti su dbdev. Si rifanno al P-0.

* **La tabella.** `magazzino.lotti(id, articolo_id NN, codice NN, data_arrivo NN, data_scadenza,
  attivo, meta, …)`, `UNIQUE (articolo_id, codice)`, FK verso `catalogo.articoli`. Nessuna RLS,
  nessun emittente.
* **Chi la cita**, cioè chi ha `lotto_id`: `movimenti`, `movimenti_attesi`, `inventari_righe`,
  `rettifiche_righe`, `trasferimenti_righe` e `vendite.ddt_righe_prelievi`. Ognuna di queste ha già
  un'azienda, attraverso il suo magazzino o il suo documento.
* **Chi la scrive**: i verbi `magazzino.fn_aggiungi_lotto` e `fn_modifica_lotto` (DEFINER, il livello
  sull'oggetto); l'app ha solo `SELECT` dal 2026-11-22. Il backend li adotta con la R-1 del brief
  vicino.
* **Righe**: 0 su dbdev.
* ⚠️ **Il nome `lotto` è già preso** nel risolutore dell'emittente:
  `script.fn_resolve_emittente_fiscale_id('lotto', …)` e `script.fn_scope_ef_whitelist_via_lotto`
  parlano del **lotto di fatturazione** (`vendite.fatturazione_lotti`). Il lotto di magazzino avrà un
  nome suo.

## 3. Il problema, sul modello

Un lotto senza azienda è una riga che due aziende condividono senza saperlo:
* la scadenza di un lotto di A la può cambiare B;
* la tracciabilità («chi ha spostato la scadenza di questo lotto») attraversa due aziende;
* il codice del lotto, che in realtà è scritto sul cartone del fornitore di **una** azienda, non può
  ripetersi su un'altra.

Con l'azienda sul lotto valgono le regole che il magazzino ha già: la RLS di lettura, il guard di
perimetro in scrittura (D-M6 del brief vicino) e il no-leak dei verbi.

## 4. Decisioni aperte — a Tid

Da prendere una alla volta. Ognuna ha una proposta.

| | Domanda | Opzioni | Proposta |
| --- | --- | --- | --- |
| **D-L1** | Come si lega il lotto all'azienda? | **a** una colonna `emittente_fiscale_id NOT NULL`, come `magazzini` e `assets` · **b** un `magazzino_id`: il lotto sta in un magazzino | ⭐ **a.** Un lotto si sposta fra i magazzini della stessa azienda (trasferimenti): legarlo a un magazzino lo inchioderebbe al primo. L'azienda è quella che riceve la merce, e il default di sessione (`trgfn_default_emittente_fiscale`) la mette da solo, come sul seriale |
| **D-L2** | Il codice è unico per…? | **a** `(emittente, articolo, codice)` · **b** resta `(articolo, codice)` | ⭐ **a.** Due aziende possono ricevere dallo stesso fornitore partite con lo stesso codice. Con **b** la seconda azienda non potrebbe registrarla |
| **D-L3** | I lotti che esistono già | **a** l'azienda dai movimenti del lotto; un lotto mosso da due aziende ferma la migrazione e si guarda a mano · **b** l'azienda di default di ogni installazione · **c** si cancellano | ⭐ **a.** La regola è del modello: un lotto è dell'azienda che lo ha movimentato. Un lotto di due aziende è un dato da capire, non da indovinare. ⚠️ Fatto datato: oggi su dbdev le righe sono zero. La regola vale comunque, per le installazioni che ne avranno |
| **D-L4** | I figli: un movimento, una riga di inventario, un prelievo di bolla col lotto di un'altra azienda | **a** un guard sui sei figli: il lotto è dell'azienda della riga · **b** nessun controllo, basta la RLS | ⭐ **a.** La RLS filtra la lettura, non il riferimento: una FK verso un lotto altrui passa anche se non lo si vede. È la stessa forma di `trgfn_trasferimenti_guard_stesso_emittente`; un BB solo, montato sui sei figli |

## 5. I passi

| Passo | Cosa | Note |
| --- | --- | --- |
| **P-0** | Censimento, al momento di scrivere: pgTAP che creano lotti (oggi da `dbops.fn_pgtap_crea_lotto_di_magazzino`), viste e funzioni che leggono `lotti`, lettori BE | regola del P-0: fatti datati, non motivi |
| P-1 | La colonna, il default di sessione, il guard di perimetro (`trgfn_guard_emittente_scope`, modo `fiscale`), la RLS, l'unicità (D-L1, D-L2); il pregresso (D-L3) | `00_schema` + `20_code`; il nuovo modo del risolutore col nome suo (§2) |
| P-2 | I verbi: `fn_aggiungi_lotto` e `fn_modifica_lotto` leggono la riga nel perimetro (`E_MAG_LOTTO_NON_TROVATO`, no-leak), come ubicazione e magazzino | CREATE OR REPLACE coi `%TYPE` |
| P-3 | Il guard dei figli (D-L4) | un BB, sei montaggi |
| P-4 | pgTAP: perimetro in lettura e scrittura, no-leak dei verbi, unicità per azienda, il guard dei figli, il pregresso | come app; i casi si costruiscono |
| P-5 | Guida del dominio: i lotti escono dall'elenco «uguali per tutti». Registro dei BB | alla chiusura |

## 6. Richieste a BE — nello stesso giro di PR

* **R-1** `test_perimetro_emittente_copertura.py`: `magazzino.lotti` passa fra le tabelle col
  perimetro (oggi è «figli dell'articolo, perimetro_emittente = false»).
* **R-2** La lista dei lotti per articolo resta, ed è filtrata dalla RLS. Il BE censisce i suoi
  lettori e la vista del form del lotto. L'azienda non si sceglie: la mette la sessione.

## 7. Che cosa NON entra

| Cosa | Dove |
| --- | --- |
| il lotto di **fatturazione** (`vendite.fatturazione_lotti`) | è un'altra cosa, col suo nome |
| l'articolo: resta comune a tutte le aziende | — |
| l'apply, i pgTAP col runner, il commit | Tid |

---

## Registro

| Data | Chi | Cosa |
| --- | --- | --- |
| 2026-11-22 | Tid | Dal §5.3 di `brief-db-magazzino-tutte-le-scritture-dal-verbo`: «lotto b» (il lotto è dell'azienda), in un brief apposito |
| 2026-11-22 | DB | Prima stesura: la storia della decisione del 14-09 (§1), i fatti datati (§2), quattro decisioni a Tid con una proposta (§4) |
