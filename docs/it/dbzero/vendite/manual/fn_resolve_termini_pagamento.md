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

### 🔁 Il livello 1 e la sorgente EFFETTIVA

> 🔴 **Rettifica 2026-08-03.** La prima stesura di questa pagina diceva che il
> livello 1 era «dormiente perché `ordini` e `preventivi` hanno zero righe».
> **Il motivo era sbagliato**: non scattava nemmeno a tabelle piene.

Il **pull riscrive la sorgente**: l'attività che genera porta
`sorgente = COMMESSA`, per disegno. Il resolver leggeva quel valore, non
trovava né `ordini` né `preventivi`, e saltava — su **35 attività su 35**, cioè
sulla totalità di ciò che arriva in fattura. Il livello non era dormiente, era
**strutturalmente irraggiungibile**, e la catena a quattro livelli ne aveva uno
decorativo.

Il costo l'ha pagato una fattura vera: termine a 2 rate impostato su preventivo e
ordine, documento uscito con **una** rata — e **senza errori**, perché le rate
quadravano col totale.

Da `20260803-03` il livello 1 risolve la **sorgente effettiva** e copre due
strade:

| Strada | Come |
|---|---|
| attività inserita **direttamente** con sorgente documento | `a.sorgente_uid` — invariata |
| attività prodotta dal **pull** (`sorgente = COMMESSA`) | risale via `a.commessa_attivita_id` → `commesse_attivita.sorgente_tipo_id` + `sorgente_uid` |

**Perché dalla riga di commessa e non da `sorgente_origine_tipo_id`**:
`attivita_fatturabili` conserva il **tipo** d'origine ma **non l'uid**. Si saprebbe
che viene da un ordine, non da *quale*. La riga di commessa conserva entrambi, e la
JOIN è totale (35 su 35).

⚠️ **La sovrascrittura è filtrata sui due tipi che il livello 1 gestisce**
(`ORDINE_VENDITA`, `PREVENTIVO`), e non è una restrizione di comodo: la sorgente è
**polimorfa** e `commesse_attivita.sorgente_uid` è `TEXT`, mentre
`attivita_fatturabili.sorgente_uid` è `UUID`. Per convenzione preventivo e offerta
usano l'uid, gli altri `id::text`: assegnare senza filtro farebbe **esplodere il
cast** al primo contratto o consumo che arrivasse lì. Per contratti e DDT il
livello 1 non avrebbe comunque nulla da leggere — non hanno colonne di pagamento.

💡 **La lezione, che vale oltre questa funzione**: *un livello si verifica dal
percorso che lo attraversa, non dal codice che lo dichiara*. Il primo test scritto
per verificarlo lo aveva **confermato** — perché costruiva l'attività a mano con
un `sorgente_tipo_id` che il pull non produce mai. Il presidio è ora il test 1 di
`test-resolve-termini-livello-sorgente-v1.sql`, che asserisce la **forma** che il
pull produce: se cambia, è il primo a dirlo.

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
