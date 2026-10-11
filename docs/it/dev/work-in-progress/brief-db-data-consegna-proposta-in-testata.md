# Brief DB — La data di consegna proposta dalla testata

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-11, su richiesta di Tid. **A chi:** team DB;
> poi BE/FE (§7).
> **Stato:** 📝 **aperto.** Decisioni D-1 … D-4 prese da Tid il 2026-10-11 (§3); resta una domanda,
> D-5 (§3), sulla colonna `acquisti.ordini.data_ora_consegna_prev`.
> **Non è un doppione di:**
> * [brief-db-modifiche-certe-ciclo-vendita-e-articolo](../work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md)
>   P-6: lì si è **scartata** una data di testata come **riassunto** delle righe (seconda fonte di
>   verità). Qui la testata non riassume niente: **propone**, e la verità resta sulla riga (§2);
> * [brief-db-testata-dopo-emissione](brief-db-testata-dopo-emissione.md): è la sede della regola
>   «fuori bozza, quali colonne di testata si cambiano e in quale stato». Le colonne nuove si
>   montano nel suo lock con la sua grammatica (§4.3); la regola non si riscrive qui.

## 1. La domanda

Su un ordine la data di consegna sta solo sulle righe (`data_consegna_richiesta_cliente`,
`data_consegna_confermata`). Un ordine che si consegna tutto insieme obbliga a scrivere la stessa
data riga per riga. Tid chiede una data **sulla testata**, scritta una volta e proposta a tutte le
righe.

## 2. Il modello

* **La testata propone, la riga decide.** La data di testata non è la data di nessuna riga: è il
  valore con cui **nasce** una riga che non ne porta una. Da lì la riga è indipendente.
* ⛔ **Nessuna lettura `COALESCE(riga, testata)`.** Chi legge la data di consegna (situazione merce,
  lista ordini col suo `min`, push dal preventivo, carico/scarico) continua a leggere la **riga**.
  Una data efficace calcolata da due sedi è la seconda fonte di verità che P-6 ha rifiutato.
* Cambiare la data di testata **non tocca** le righe esistenti. Per portarla sulle righe c'è un
  gesto esplicito, che riempie **solo le righe senza data** (D-2).

## 3. Decisioni di Tid (2026-10-11)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-1** | Quali date in testata? | **Entrambe**, ciascuna seme della sua omologa di riga: la richiesta del cliente e la nostra confermata |
| **D-2** | Come arriva sulle righe? | Si scrive prima sulla testata, e ogni riga che nasce senza data la prende. Il gesto «applica alle righe» riempie **solo le righe senza data**: non sovrascrive mai una data scritta |
| **D-3** | Fuori bozza? | Come la riga: la data **confermata** di testata resta modificabile negli stati in cui lo è quella di riga (oggi `CONFERMATO`, `PARZIALMENTE_EVASO`), e lì vale anche il gesto «applica». La data **richiesta** si ferma fuori bozza, come sulla riga |
| **D-4** | Quali documenti? | **Simmetria con tutti i documenti che hanno le due date sulle righe**: `vendite.ordini` e `acquisti.ordini`. Il preventivo ha sulle righe la sola data richiesta, quindi resta fuori |
| **D-5** ❓ | `acquisti.ordini.data_ora_consegna_prev` (timestamp, già in testata, fra i dati di trasporto: analisi-simmetria-ordini-acquisto ⑪) | **Da decidere.** È la proposta di `data_consegna_richiesta` scritta con un altro nome e un altro tipo, o un'altra cosa (l'ora prevista di arrivo del trasporto)? Nel primo caso due colonne direbbero la stessa cosa. Il team DB la legge sul modello e propone; decide Tid |

## 4. Forma proposta (la sceglie il team DB)

### 4.1 Le colonne

| Tabella | Colonne nuove | Nomi |
| --- | --- | --- |
| `vendite.ordini` | `data_consegna_richiesta_cliente date`, `data_consegna_confermata date`, nullable | gli stessi della riga |
| `acquisti.ordini` | `data_consegna_richiesta date`, `data_consegna_confermata_fornitore date`, nullable | gli stessi della riga (D-16: non marcato = nostro, marcato = della controparte) |

Nessun CHECK fra le due date, come sulla riga (scelta di P-3, §2.3 del brief d'origine).

### 4.2 Il seme alla nascita della riga

* BEFORE INSERT sulle righe (`vendite.ordini_righe`, `acquisti.ordini_righe`): se la data della
  riga è NULL e quella di testata no, la riga prende quella di testata. Le due date sono
  indipendenti fra loro.
* Vale per **ogni** strada di nascita della riga: form, push dal preventivo (che porta la sua data
  richiesta e quindi vince), qualsiasi madre futura. Una regola nel DB, non nel form.
* ⭐ **Regola del 2**: due tabelle, stessa logica con nomi di colonna diversi. Un BB parametrico (le
  coppie colonna di riga → colonna di testata come argomenti del trigger), non due funzioni.
* È la scrittura della riga stessa in BEFORE INSERT: non è un riempimento su un documento già nato,
  quindi non passa per D-13 di brief-db-testata-dopo-emissione. Il lock delle righe resta com'è.

### 4.3 Il lock della testata

Le due colonne nuove si montano nel lock della testata con la **grammatica a terne** di
brief-db-testata-dopo-emissione §5-bis.7, in quella sede:

* la data **richiesta**: ferma fuori bozza (terna con stati vuoti);
* la data **confermata**: aperta negli stati dell'eccezione del lock delle righe (oggi
  `CONFERMATO`, `PARZIALMENTE_EVASO`).

⚠️ Gli stati non vanno ricopiati: sono gli stessi argomenti `[4]`/`[5]` del montaggio delle righe.
Se la grammatica non permette di dirlo senza copiarli, il team DB lo segnala: due liste di stati
per la stessa data divergono al primo stato nuovo.

`acquisti` ha oggi il solo modello, senza lock: le colonne nascono e il lock arriva col resto del
cantiere acquisti.

### 4.4 Il gesto «applica alle righe»

* Un verbo per documento, o uno parametrico: `fn_ordine_applica_data_consegna(p_ordine_id, p_quale)`,
  con `p_quale` = richiesta | confermata (nome di lavoro).
* Scrive la data di testata sulle righe **attive** con quella data a NULL; non tocca le altre.
  Ritorna quante righe ha riempito.
* Fuori bozza, solo la confermata e solo negli stati di D-3: l'UPDATE della sola
  `data_consegna_confermata` è già la porta che il lock delle righe lascia aperta.
* **Capability** (azione di documento, blob di `script.fn_available_actions_ordine`), con la sua
  check (linee-guida-sql §12.5). Motivi da coprire: data di testata vuota, nessuna riga senza data,
  stato che non ammette. Uno per data, perché i due gesti si spengono per motivi diversi.
* Codici nuovi registrati, con policy e frase di ripiego.

## 5. pgTAP (fixture fabbricati)

* Testata con le due date, riga inserita senza date → la riga le prende; riga inserita con una
  data → resta la sua; con una sola delle due → prende solo l'altra.
* Push da preventivo con data richiesta sulla riga → resta quella del preventivo; senza → prende
  quella di testata.
* Cambio della data di testata → le righe esistenti non cambiano.
* «Applica»: riempie solo le righe senza data e ritorna il numero giusto; con nessuna riga da
  riempire → il motivo della check.
* Fuori bozza (`CONFERMATO`): la confermata di testata si cambia e si applica, la richiesta no;
  in uno stato fuori dall'eccezione, nessuna delle due.
* Lo stesso seme su `acquisti.ordini_righe`.

## 6. Fuori da qui

* Il preventivo (D-4).
* Una data di testata **calcolata** dalle righe: c'è già, ed è il `min` di `vw_ordini_lista` (P-6).

## 7. Ricaduta BE/FE (dopo la consegna DB)

* Testata ordine: le due date nel form (whitelist di create e update), con le capability per stato
  già lette dal blob (`non_editable_fields`).
* Il gesto «Applica alle righe senza data», uno per data, nella testata o nella sezione righe:
  segue la capability e dice quante righe ha riempito.
* Form riga: nessun cambio. La data proposta la mette il DB; dopo il salvataggio la riga riletta
  la mostra.
* Guida `gestione-ordini`: la data in testata come proposta, il gesto, l'esempio «tutto il 20,
  una riga il 25».
* Acquisti: niente finché non c'è il BE/FE di quel cantiere.
