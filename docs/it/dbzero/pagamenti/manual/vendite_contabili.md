## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione)  
> • [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso)  
> • [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati)  
> • [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)  
> • [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
### 🎯 Scopo Principale
La tabella **`pagamenti.vendite_contabili`** rappresenta la **testata contabile**
per l’aggregazione di movimenti vendite. Serve a raggruppare movimenti per
centro riscossione e data contabile, con eventuale dettaglio del canale
(`ente_incasso`) e stato operativo della testata.

---

### Campi chiave (semantica)

* `codice`: identificativo testata contabile.
* `centro_riscossione_id`: riferimento principale al centro riscossione.
* `ente_incasso_id`: ente/canale specifico (opzionale).
* `compensazione_id`: testata processo compensazione (opzionale, univoca).
* `stato_id`: stato della testata contabile.
* `data_contabile`: data contabile di riferimento.
* `data_conferma` / `user_conferma`: tracciamento conferma testata. ⭐ **Dal
  2026-08-22 le scrive `pagamenti.fn_posta_contabile`**: prima esistevano e
  restavano vuote. La conferma è l'atto di **registrare**, e il `COALESCE` tiene
  la prima volta che è successo.

---

### Regole principali

* `codice` univoco.
* Ogni testata e` collegata a un solo centro riscossione.
* Se `ente_incasso_id` e` valorizzato, deve essere coerente con
  `centro_riscossione_id` della testata (guard applicativa).
* Se `compensazione_id` e` valorizzato:
  * il centro riscossione deve avere `is_compensazione = true`
  * la testata non puo` essere collegata a lotti (`vendite_contabili_lotti`).
* `stato_id` punta al lookup `pagamenti.vendite_contabili_stati`.

---

### Esempio d’uso

```sql
SELECT *
FROM pagamenti.vendite_contabili
WHERE data_contabile = current_date;
```

---

### 🎯 Che cos'è davvero: una **distinta**, non un movimento bancario

L'evidenza è nelle colonne: qui non c'è **nessun importo** e **nessun riferimento
bancario** (CRO, TRN, numero operazione). Il riferimento della banca sta **sulla
riga**. Questa testata non modella *un* bonifico: modella il **documento che
raccoglie N importi arrivati insieme** e li prepara.

⭐ È ciò che rende sensata la registrazione «per testata»: le righe dubbie restano
`SOSPESA` e non si registrano, quindi *«registra la distinta»* significa
naturalmente **registra tutto il pronto, lascia lì il resto**. Con una testata per
bonifico non ci sarebbe nessun «resto» da lasciare.

### `origine` — il cardine da cui pendono le altre regole (2026-08-21)

| Valore | Che cos'è | Chi la crea |
| --- | --- | --- |
| `MANUALE` | il **lotto di lavoro di un operatore** | una persona, digitando |
| `AUTOMATICA` | il **file** arrivato dal canale | l'import *(non ancora costruito)* |
| `GENERATA` | la produce **il sistema** | il giro dei fondi fattura, le compensazioni |

⭐ **Il terzo valore è nato da una misura**, non da una simmetria: l'unico creatore
di distinte esistente è il giro dei fondi, che **non è né l'uno né l'altro** — non
la digita una persona e non arriva da un file. Con due soli valori, il 100% delle
distinte di oggi avrebbe portato una parola falsa.

Tre regole pendono da questa colonna:

* **`importo_dichiarato`** è obbligatorio su `AUTOMATICA`, facoltativo su
  `MANUALE`, **vietato** su `GENERATA` *(due CHECK)*;
* il **raggruppamento per operatore** vale solo su `MANUALE`;
* la **riapertura** `VALIDATA → BOZZA` vale solo su `MANUALE`.

### `importo_dichiarato` — non è il totale delle righe

È **ciò che la sorgente dichiara di aver mandato**. Sull'automatica è
l'**autocontrollo dell'import**: se abbiamo letto male il file la somma non torna e
non nasce niente. Sul manuale è il classico controllo da inserimento dati, e
**scatta al passaggio a `VALIDATA`** — cioè al gesto «ho finito», mentre
l'operatore è ancora nel flusso.

⚠️ La quadratura conta **tutte** le righe attive, `SCARTATA` comprese: quel denaro
è arrivato comunque. Dice *«abbiamo letto tutto ciò che c'era»*, non *«tutto è
nostro»*.

### ⭐ La distinta manuale è **per operatore**, e con ciò il lock sparisce

Il riuso della testata, sul ramo manuale, comprende **chi sta lavorando**. Il
raggruppamento «giornata + canale» non ha un referente nel mondo — nessun
documento reale corrisponde a *«tutti gli incassi banca di lunedì digitati a
mano»* — mentre il lotto di lavoro di una persona ce l'ha.

⭐ Era stata chiesta una funzione di **blocco** perché due operatori non si
pestassero i piedi: con questo raggruppamento **la contesa non esiste**, quindi
non servono colonne di blocco, scadenze, sblocco d'emergenza. *Il presidio più
economico è quello che il modello rende inutile.*

### `stato_id` è obbligatorio, ed è un cancello

Da quando lo stato divide il **brogliaccio** dal **registro** — prima della
conferma la distinta si annulla, dopo no — una testata *senza* stato non sarebbe
né l'uno né l'altro, e passerebbe i filtri di entrambi. Dal 2026-08-21 la colonna
è `NOT NULL` con default `BOZZA`.

### I quattro guard che la difendono

| Guard | Impedisce |
| --- | --- |
| `trgfn_vendite_contabili_guard_transizione` | i salti di stato che la matrice non ammette |
| `trgfn_vendite_contabili_guard_chiusura` | di **chiudere** una distinta che ha ancora righe pronte |
| `trgfn_vendite_contabili_guard_validazione` | di validare con un totale che non quadra, e di riaprire una distinta non manuale |
| `trgfn_vendite_contabili_guard_ente_centro` | le incoerenze fra centro, ente e compensazione |

---

{% include-markdown "signature-core.md" %}
