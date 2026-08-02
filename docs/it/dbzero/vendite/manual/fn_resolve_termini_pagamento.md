## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_termini_pagamento`

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento) — il catalogo delle regole
> • [config.modalita_pagamento](/dbzero/config/tabelle/modalita_pagamento) — il **come**, separato dal **quando**
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse) — possiede le proprie condizioni (D-R)
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — l'input
>
> **Funzioni:**
>
> • [vendite.fn_build_fattura_key](/dbzero/vendite/funzioni/fn_build_fattura_key) — chiama questa catena
> • [vendite.fn_genera_scadenze_fattura](/dbzero/vendite/funzioni/fn_genera_scadenze_fattura) — **legge** il risultato, non lo ricalcola

---
### 🎯 Scopo Principale
(latest review 02-08-2026)

`vendite.fn_resolve_termini_pagamento(p_attivita_id)` è l'**unica** implementazione
della catena delle condizioni di pagamento. Per una singola attività fatturabile
risponde alla domanda «con quale termine e con quale modalità si paga?»,
restituendo la coppia `(termine_pagamento_id, modalita_pagamento_id)`.

È `STABLE` e non scrive nulla: risolve e basta.

> ⚠️ **Perché è una sola.** Se esistessero due risolutori, prima o poi
> divergerebbero — e divergerebbero **in silenzio**, perché entrambi
> restituiscono un id plausibile. La Fase 3b del cantiere satelliti è servita
> esattamente a togliere il secondo. Chi ha bisogno del termine **chiama questa**,
> non lo ricava per conto proprio.

---

### La catena: quattro livelli, ci si ferma al primo che risponde

| # | Livello | Cosa porta |
|---|---|---|
| 1 | **Documento sorgente** | l'**ordine** porta termine *e* modalità; il **preventivo** il solo termine |
| 2 | **Commessa** (D-R) | entrambi, se valorizzati |
| 3 | **Cliente** del billing account **padre** | entrambi |
| 4 | **Default** `TP_1RATA` | il solo **termine** |

Nessun ramo per i **contratti** e i **DDT**: non hanno colonne di pagamento. Non
è una dimenticanza — è il fatto che ha deciso D-R (vedi sotto).

---

### Quattro cose non ovvie, tutte pagate

**1. I due campi scendono la catena in modo INDIPENDENTE.** Il preventivo porta il
termine ma non la modalità, quindi i due possono fermarsi a livelli diversi. Solo
il termine ha un default: `config.modalita_pagamento` non ha una riga
«predefinita», e sceglierne una arbitrariamente finirebbe **sulla fattura
elettronica** — meglio un campo vuoto che un dato inventato in un documento
fiscale.

**2. Il cliente si risolve dal billing account PADRE**, non da quello
dell'attività. La fattura si emette sul padre, quindi le condizioni sono le sue.
Prenderle dal figlio spaccherebbe in N ciò che deve restare una fattura sola.

**3. La commessa sta PRIMA del cliente**, ed è deliberato: è il livello più
specifico, e **cambiare le condizioni di un cliente non deve riscrivere quelle
delle commesse già aperte**.

**4. 🔴 Ogni livello legge in variabili PROPRIE.** La fusione avviene dopo, con
`COALESCE` in codice. Il motivo è una trappola di PL/pgSQL che è già costata una
correzione: un `SELECT ... INTO` che **non trova righe mette le variabili a
NULL**. Leggere direttamente in `v_termine`/`v_modalita` farebbe **cancellare** al
livello a valle ciò che il livello a monte aveva già risolto — e il caso reale
esiste: la JOIN del livello cliente è *inner*, quindi un BA padre senza riga
cliente dà zero righe e avrebbe azzerato il termine trovato sul documento.
«Non ho trovato niente» non è «ho trovato NULL».

---

### 🔎 Stato dei dati: il livello 1 oggi è dormiente

Misurato: `vendite.ordini` e `vendite.preventivi` hanno **zero righe** e tutte le
attività arrivano da commessa. Il livello «documento sorgente» è quindi una
**predisposizione** che si accenderà al primo uso reale, non un ramo in esercizio.

Se ne tenga conto leggendo i test: quel livello non è esercitato, ed è dichiarato
nei file invece di essere taciuto.

---

### 💡 Perché il termine spacca la commessa alla fonte (D-R)

Le condizioni di pagamento sono parte della **chiave di raggruppamento** della
commessa: un documento con condizioni diverse non riusa una commessa esistente,
**ne apre una nuova**.

La strada alternativa — lasciare aggregare tutto e poi risalire dalla fattura al
documento che l'ha originata — è stata scartata su una misura: una singola
commessa arriva a **32 sorgenti di 4 tipi diversi**, e fra queste **contratti e
DDT non hanno colonne di pagamento**. Risalire avrebbe spaccato le fatture per
*assenza del campo* invece che per una scelta di qualcuno.

Decidendo alla fonte, la divergenza si vede **quando la si crea**, invece di
comparire mesi dopo come una fattura in più che nessuno sa spiegare.

---

### Errori

| Codice | Quando |
|---|---|
| `E_PARAMETRO_INVALIDO` | `p_attivita_id` nullo o non positivo |
| `E_VALORE_MANCANTE` | attività inesistente |

Assenza di condizioni **non è un errore**: è il caso che il livello 4 esiste per
coprire.

---
{% include-markdown "signature-core.md" %}
