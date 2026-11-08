## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_termini_pagamento`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento) — il catalogo delle regole
> * [config.modalita_pagamento](/dbzero/config/tabelle/modalita_pagamento) — il **come**, separato dal **quando**
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse) — possiede le proprie condizioni
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — la riga di commessa, che porta la provenienza
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — l'input
>
> Approfondimento funzioni:
>
> * [vendite.fn_build_fattura_key](/dbzero/vendite/funzioni/fn_build_fattura_key) — chiama questa catena
> * [vendite.fn_genera_scadenze_fattura](/dbzero/vendite/funzioni/fn_genera_scadenze_fattura) — **legge** il risultato, non lo ricalcola
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---
### 🎯 Scopo Principale

`vendite.fn_resolve_termini_pagamento(p_attivita_id)` è l'**unica** implementazione
della catena delle condizioni di pagamento. Per una singola attività fatturabile
risponde alla domanda «con quale termine e con quale modalità si paga?»,
restituendo la coppia `(termine_pagamento_id, modalita_pagamento_id)`.

È `STABLE` e non scrive nulla: risolve e basta.

> ⚠️ **Perché è una sola.** Se esistessero due risolutori, prima o poi
> divergerebbero — e divergerebbero **in silenzio**, perché entrambi
> restituiscono un id plausibile. Chi ha bisogno del termine **chiama questa**,
> non lo ricava per conto proprio.

---

### La catena: quattro livelli, ci si ferma al primo che risponde

| # | Livello | Cosa porta |
|---|---|---|
| 1 | **Documento d'origine** | l'**ordine** porta termine *e* modalità; il **preventivo** il solo termine |
| 2 | **Commessa** | entrambi, se valorizzati |
| 3 | **Cliente** del billing account **padre** | entrambi |
| 4 | **Default** `TP_1RATA` | il solo **termine** |

Nessun ramo per i **contratti** e i **DDT**: non hanno colonne di pagamento. Non
è una dimenticanza: è il fatto che fa spaccare la commessa alla fonte (vedi sotto).

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

### 🔁 Il livello 1: il documento d'origine della riga di commessa

L'attività fatturabile non porta una provenienza propria: nasce da una riga di commessa
(`commessa_attivita_id`), ed è **quella riga** a dire da quale documento viene, con tipo e
chiave del modello della provenienza. Il livello 1 risale lì: dall'attività alla riga di
commessa, dalla riga al documento d'origine.

| Tipo d'origine della riga | Che cosa legge |
|---|---|
| `ORDINE_VENDITA` | termine e modalità dell'ordine |
| `PREVENTIVO` | il solo termine del preventivo |
| ogni altro tipo, o nessuno | niente: il livello 1 non risponde e si passa alla commessa |

Il documento si cerca con la regola d'incontro del modello (l'id o l'uid del documento,
secondo la chiave che la provenienza porta).

💡 **La lezione, che vale oltre questa funzione**: *un livello si verifica dal percorso che
lo attraversa, non dal codice che lo dichiara*. Un livello che leggeva un dato che il percorso
reale non produce mai è rimasto irraggiungibile senza errori, e una fattura è uscita con una
rata invece di due, con le rate che quadravano col totale. Il presidio è il test 1 di
`test-resolve-termini-livello-sorgente-v1.sql`, che costruisce l'attività nella **forma** che
l'emissione dalla commessa produce: se quella forma cambia, è il primo a dirlo.

---

### 💡 Perché il termine spacca la commessa alla fonte

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

### Note di migrazione

* 2026-08-03 — il livello 1 risolve la sorgente **effettiva**: l'attività prodotta dalla
  commessa portava come sorgente la commessa stessa, e il livello leggeva quella, senza mai
  trovare ordine o preventivo. Da allora risale alla riga di commessa. La prima stesura di
  questa pagina lo diceva «dormiente perché le tabelle sono vuote»: il motivo era sbagliato.
* 2026-10-08 — il livello 3 (cliente del BA padre) aggancia il cliente **per BA**
  (`cl.billing_account_id = ba.id`). Prima lo agganciava per istanza, contando su «un cliente per
  istanza»: con piu' BA per istanza avrebbe preso il termine di pagamento di un cliente qualunque.
  Deterministico grazie a `uq_clienti_billing_account`. Brief: brief-db-istanza-nasce-col-ba (R-8).
* 2026-11-07 — ritirate le colonne di provenienza dell'attività fatturabile: il livello 1 ha
  una sola strada, la riga di commessa, che porta la provenienza tipizzata
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
