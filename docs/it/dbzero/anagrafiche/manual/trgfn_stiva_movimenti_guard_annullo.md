## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_stiva_movimenti_guard_annullo`

> 👀 **Vedi anche**
>
> [script.fn_check_annullo_movimento_titolo_iva](/dbzero/script/funzioni/fn_check_annullo_movimento_titolo_iva) — l'ammissibilità, che **chiama** ·
> [anagrafiche.fn_annulla_movimento_titolo_iva](/dbzero/anagrafiche/funzioni/fn_annulla_movimento_titolo_iva) — la via normale, che rende derivati i due controlli qui sotto ·
> [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti)

---

### 🎯 Scopo Principale

(rev 2026-08-31 — funzione nata il 2026-08-31)

Presidia le righe che **annullano** un movimento di plafond, cioè quelle con
`annulla_movimento_id` valorizzato.

---

### Due famiglie di controlli, e non sono la stessa cosa

| | Cosa chiede | Dove vive la regola |
| --- | --- | --- |
| **1. Ammissibilità** | «questo movimento si può annullare?» | ⭐ **non qui**: si chiama `script.fn_check_annullo_movimento_titolo_iva` e si solleva il codice del **primo** motivo |
| **2. Coerenza della riga scritta** | stesso titolo, importo opposto | **qui**, ed è difesa contro una scrittura **diretta** |

⭐ **Perché la prima non è scritta qui.** La stessa check spegne il pulsante nel
read-side. Se il predicato fosse riscritto in due posti, «oggi coincidono» sarebbe
il massimo che un test potrebbe provare; così invece **non possono divergere**.

⭐ **Perché la seconda sì.** Passando dalla madre, titolo e importo sono
**derivati** dalla riga annullata e non possono sbagliare. Chi arriva qui con
valori incoerenti sta scrivendo nel registro **direttamente** — e il messaggio lo
dice, perché è `TECNICO`.

⚠️ Non sono ridondanti «tanto ci si passa dalla madre»: la tabella è scrivibile
anche senza, e *un guard che esiste solo perché nessuno lo aggira è un guard che
il primo `INSERT` diretto scavalca.*

---

### ⛔ Il controllo sul TITOLO è il più importante, ed è quello che non si vede

Un annullo collegato a un movimento di **un altro titolo**:

* decurta il **plafond sbagliato**;
* lascia **gonfiato** quello della forzatura che diceva di annullare;
* ⛔ e **non solleva niente**, perché l'accumulatore somma **per titolo** e del
  collegamento non sa nulla: trova entrambi i totali «coerenti».

Si vedrebbe solo guardando **due plafond insieme**. E nel dato reale quell'«altro
titolo» è di **un altro cliente**.

---

### ⛔ Il controllo sull'IMPORTO è ciò che rende vera la promessa

Il senso dell'annullo è che `imponibile_utilizzato` **torni al valore precedente**.
Senza questo controllo, il database ammetterebbe un «annullo» di 100 su una
forzatura di 250: due righe nel registro, il collegamento a posto, e il totale
sbagliato.

> ⚠️ **Ed è il controllo che un test non avrebbe scoperto mancante**: un pgTAP che
> annulla e verifica il totale passa lo stesso, perché il numero giusto lo scrive
> la **fixture**. È un verde che prova la popolazione che si è fabbricato, non la
> regola. Per questo esiste un'asserzione apposta sull'importo sbagliato.

---

### ⛔ `SECURITY DEFINER`, per la stessa ragione della check

Deve **rileggere la riga annullata** per confrontarne titolo e importo, e quella
tabella ha la RLS attiva. Da `INVOKER` una riga fuori perimetro si leggerebbe come
«non esiste», e il guard passerebbe su una premessa non verificata — mentre la FK,
che la RLS la scavalca sempre, il riferimento l'avrebbe accettato.

⚠️ Non è un buco di perimetro: la **madre resta `INVOKER`**, quindi la scrittura
passa comunque dalla policy.

---

### ⚠️ Due dettagli di montaggio che valgono la riga

* **`WHEN` sul trigger, non un `IF` in testa al corpo.** La stragrande maggioranza
  delle righe del registro non è un annullo: col `WHEN` la funzione non viene
  nemmeno invocata, invece di essere chiamata e uscire subito.
* **Solo `BEFORE INSERT`.** L'`UPDATE` non serve: dal 2026-08-31 il registro non
  ne ammette più. Un ramo `UPDATE` qui sarebbe codice irraggiungibile **che sembra
  vivo**.

---

### Contesto di Esecuzione

* **Tipo**: trigger `BEFORE INSERT`, per riga, `WHEN (NEW.annulla_movimento_id IS NOT NULL)`
* **Fascia**: `a10` (guard/blocco)
* **Trigger**: `trg_stiva_movimenti_a10_guard_annullo_ins`

---

### Codici errore

| Codice | Motivo | Classe |
| --- | --- | --- |
| `E_TITOLO_IVA_ANNULLO_NON_AMMESSO` | il codice del **primo** motivo restituito dalla check | `CONFLITTO_STATO` (409) |
| `E_TITOLO_IVA_ANNULLO_INCOERENTE` | titolo diverso, o importo non opposto | `TECNICO` (500) |

⚠️ Il secondo è `TECNICO` perché quei due valori, passando dalla madre, sono
derivati: sbagliarli lo può **solo** un chiamante che scrive direttamente. Su un
`TECNICO` la chiave `campo` **esce** dal contesto — non c'è nessun campo da
accendere.

---

### Test

`db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql`, asserzioni **3**
(non forzatura), **4** (importo), **5** (titolo), **7** (annullo di un annullo).

Cantiere: `brief-db-titoli-iva-movimenti-annullo.md`, fase `B-c`.

---

{% include-markdown "signature-core.md" %}
