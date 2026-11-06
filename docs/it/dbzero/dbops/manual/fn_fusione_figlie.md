## 📘 Documentazione Concettuale – Funzione `dbops.fn_fusione_figlie`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_fusione_righe_doppie](/dbzero/dbops/funzioni/fn_fusione_righe_doppie) — la legge per cercare i doppi
> * [dbops.fn_fusione_ripunta_figlie](/dbzero/dbops/funzioni/fn_fusione_ripunta_figlie) — la legge per ripuntare
> * [dbops.fn_admin_merge_comune](/dbzero/dbops/funzioni/fn_admin_merge_comune) — una delle due fusioni che la usano
> * [dbops.fn_admin_merge_stradario](/dbzero/dbops/funzioni/fn_admin_merge_stradario) — l'altra

---

### 🎯 Scopo Principale

Risponde alla domanda «chi riferisce una riga di questa tabella?», leggendo il catalogo: una riga
per ogni chiave esterna dichiarata verso la tabella, con le colonne della figlia e quelle del padre
in coppia. È la sede unica di «chi va ripuntato» quando due righe si fondono.

---

### Che cosa restituisce

* **figlia** — la tabella che riferisce il padre;
* **vincolo** — il nome della chiave esterna;
* **colonne della figlia** e **colonne del padre**, in coppia e nell'ordine del vincolo: vale anche
  per una chiave esterna di più colonne, o verso una chiave che non è la primaria;
* **chiave del padre** — la colonna della chiave primaria con cui si indicano origine e
  destinazione di una fusione.

Su una tabella partizionata le partizioni hanno ciascuna una copia della chiave esterna: conta
solo quella dichiarata, per non ripuntare due volte.

---

### ⭐ Una figlia elencata a mano invecchia

La fusione dei comuni ripuntava una sola figlia, scritta nel corpo, mentre i comuni ne avevano sei.
Leggendo il catalogo, una tabella nuova con una chiave esterna verso il padre entra nelle fusioni
senza toccarle.

---

### ⛔ Quando si ferma

* **Il padre manca, o non ha una chiave primaria di una colonna** → `E_DBOPS_CHIAMATA_NON_VALIDA`:
  origine e destinazione si indicano con quella chiave.
* **Una figlia è sotto RLS per chi la lancia** → `E_MERGE_FIGLIA_SOTTO_RLS`: la fusione ne vedrebbe
  solo una parte e lascerebbe le altre righe sul padre soppresso, senza dirlo. La fusione è uno
  strumento DBA, e si lancia con un ruolo che vede tutto.

---

### Test

`db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql`, test 20, 25 e 26: le figlie di un padre
costruito, con una chiave esterna di due colonne; il padre senza chiave primaria; la figlia sotto
RLS.

---

{% include-markdown "signature-core.md" %}
