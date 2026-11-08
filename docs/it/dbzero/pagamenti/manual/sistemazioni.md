## 📘 Documentazione Concettuale – Tabella `pagamenti.sistemazioni`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la distinta che un rimborso o una compensazione generano
> * [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) — il fondo fattura che un riporto genera
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) — i documenti di partenza e di destinazione, e il modello della policy
>
> Approfondimento viste:
>
> * [pagamenti.vw_eccedenze_da_sistemare](/dbzero/pagamenti/views/vw_eccedenze_da_sistemare) — l'elenco di ciò che c'è da sistemare, il compagno di questo registro
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_conferma_sistemazione](/dbzero/pagamenti/funzioni/fn_conferma_sistemazione) — il verbo che trasforma l'atto in un fatto
> * [pagamenti.fn_annulla_sistemazione](/dbzero/pagamenti/funzioni/fn_annulla_sistemazione) — il verbo che scarta l'atto lasciandolo a registro
> * [pagamenti.trgfn_sistemazioni_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_sistemazioni_guard_transizione) — il percorso degli stati
> * [pagamenti.trgfn_sistemazioni_guard_dati](/dbzero/pagamenti/funzioni/trgfn_sistemazioni_guard_dati) — la coerenza dell'atto con i documenti che nomina
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — il processo dei rimborsi, per chi non è tecnico

---

### 🎯 Scopo Principale

Il registro delle sistemazioni: che cosa si è deciso di fare di un'eccedenza di incasso, e che cosa ne è venuto fuori.

⭐ Si legge insieme alla sua vista, e la coppia è il senso di tutto il processo:

```text
vw_eccedenze_da_sistemare   →  che cosa c'è DA FARE
sistemazioni                →  che cosa è STATO FATTO
```

---

### ⭐ Tre destinazioni, e nessuna macchina nuova sotto

| `destinazione` | Che cosa significa | Che cosa genera |
| --- | --- | --- |
| `RIPORTO` | il credito va su un'**altra fattura** del cliente | un **fondo fattura** `origine = MANUALE` |
| `RIMBORSO` | il denaro **esce**, al cliente | una **distinta a importi negativi** |
| `COMPENSAZIONE` | si mette insieme il credito di un documento col debito di un altro | una **distinta sul centro dedicato**, con **due righe che sommano a zero** |

⭐ I meccanismi esistevano già tutti e tre: mancavano l'elenco e il registro.

---

### Il percorso è cortissimo

```text
BOZZA ──► CONFERMATA    (l'atto diventa un FATTO: genera il documento)
  └────► ANNULLATA      (la decisione si scarta, e resta scritta)
```

Un atto nasce sempre in `BOZZA`. ⚠️ Entrambi gli esiti sono **terminali**: da `CONFERMATA` non
si torna perché **il denaro si è già mosso**, e la correzione è una sistemazione nuova, o la
correzione guidata sulla distinta. È la stessa regola della distinta contabile chiusa.
L'unico varco è `CONFERMATA → ANNULLATA` sul solo `RIPORTO`, che fa cadere il fondo insieme
all'atto: lo descrive
[trgfn_sistemazioni_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_sistemazioni_guard_transizione).

⛔ **Non c'è una tabella-matrice** come per le contabili, e non è una dimenticanza: tre stati e
pochi passaggi sarebbero righe che nessuno interroga, e le azioni del frontend **sono i due
verbi**. La regola vive nel guard di transizione, e il codice errore la nomina per esteso
perché chi la cerca nei dati non la trova.

---

### Il significato delle colonne che non si capisce dal nome

* `importo` — quanto si sistema, diverso da zero. ⚠️ **Non** necessariamente tutta
  l'eccedenza: si può rimborsare una parte e riportare il resto, ed è il motivo per cui su una
  fattura possono esistere più sistemazioni.
* `fattura_origine_id` — il documento **che ha l'eccedenza**.
* `fattura_destinazione_id` — dove va il denaro. ⚠️ Obbligatoria su `RIPORTO` e
  `COMPENSAZIONE`, **vietata** su `RIMBORSO`: in un rimborso il denaro esce dal sistema e un
  secondo documento non esiste. E non può coincidere con l'origine.
* `cliente_soggetto_ruolo_id` — ⭐ sta qui perché la decisione si prende **guardando il
  cliente**: compensare significa mettere insieme due documenti **suoi**.
* `emittente_soggetto_ruolo_id` — è il **perimetro**, e la policy lo legge direttamente. Non è
  una denormalizzazione comoda: una sistemazione sta dentro un solo emittente **per natura**.
  Cliente ed emittente non li sceglie una persona: si derivano dalla fattura di partenza, e il
  guard dei dati rifiuta un valore diverso.
* `contabile_id` / `fondo_source_id` — **l'esito**, e sono **due** colonne. Ciascuna è unica:
  una distinta, o un fondo, per atto.
* `data_esecuzione` / `user_esecuzione` — quando e da chi l'atto è diventato un fatto; vuote
  fuori da `CONFERMATA`.
* `motivo` — ⚠️ obbligatorio su `ANNULLATA` e su `RIPORTO`. Il secondo caso non è una scelta di
  stile: il riporto genera un fondo `MANUALE`, e i fondi manuali pretendono la loro ragione.
  Chiederlo alla registrazione evita di rifiutare alla conferma una cosa che si poteva
  sistemare quando l'operatore era ancora nel flusso.

---

### ⭐ Due colonne di esito e non una polimorfa

Le tre destinazioni producono **due specie diverse** di oggetto: un fondo, oppure una distinta.
Una colonna sola avrebbe richiesto un «tipo» accanto per sapere dove guardare, cioè
`destinazione` scritta due volte. Così ciascuna porta la **sua** chiave esterna vera, e un
`CHECK` le lega alla destinazione; un altro lega l'esito allo stato (pieno solo su
`CONFERMATA`).

I `CHECK` sono la **rete**, non il presidio: a parlare per primi sono i guard, che dicono
quale regola è caduta e su quale campo.

---

### 🔴 Il legame con la distinta sta qui

È l'**atto a generare** la distinta, non il contrario, e il legame segue il giro reale:

```text
la vista mostra un'eccedenza
   → una PERSONA sceglie la destinazione
   → l'atto si registra qui
   → alla conferma GENERA una distinta (o un fondo)
   → la distinta registrata genera i MOVIMENTI
```

⭐ Per questo la distinta non sa di essere nata da un atto: lo sa l'atto. L'unicità «una
distinta per atto» la tiene `uq_sistemazioni_contabile`, e chi deve sapere se una distinta
viene da una sistemazione lo chiede al registro.

---

### ⚠️ Il nome: né `compensazioni` né `regolazioni`

Chiamare «compensazione» un bonifico di rimborso sarebbe **falso**: se la tabella copre tre
azioni, il nome deve dirlo. ⛔ E non `regolazioni`, che in contabilità sarebbe la parola più
esatta: in un ERP per le **utilities** «regolazione» significa un'altra cosa, e un nome che in
un dominio vuol dire due cose confonde.

---

### 🔒 Chi la vede

Policy `rls_sistemazioni_ef_whitelist`, `FOR ALL`, gate della veste `OPERATORE` fail-closed, sul
modello di quella di `vendite.fatture`. ⭐ È il pezzo più semplice del perimetro incassi:
l'emittente è **sulla riga** e non va cercato, perché l'atto nasce da una **decisione** e chi
decide sa già per chi. La scrittura sulle due fatture la presidia in più il guard di scope
emittente, montato su entrambe le colonne.

---

### Test

* `db/pgtap/pagamenti/test-sistemazioni-registro.sql` — il registro e i suoi guard: il nome
  nuovo senza residui del vecchio, nessun legame rimasto su `vendite_contabili`, le regole sui
  documenti e sul motivo, cliente ed emittente dichiarati, la nascita in `BOZZA`.
* `db/pgtap/pagamenti/test-sistemazioni-giro-completo.sql` — il giro dall'elenco al documento,
  per rimborso e compensazione.
* `db/pgtap/pagamenti/test-sistemazione-annullo-riporto.sql` — il varco dell'annullamento sul
  riporto confermato.

---

### Note di migrazione

* 2026-08-22 — nasce rinominando `pagamenti.compensazioni`, un guscio senza righe che copriva
  una sola delle tre azioni. Nello stesso passo il legame con la distinta cambia verso: su
  `vendite_contabili` spariscono la colonna `compensazione_id`, la sua FK e il suo unico, e da
  `fn_get_or_create_vendite_contabile` il parametro `p_compensazione_id`; l'unicità «una
  distinta per atto» passa a `uq_sistemazioni_contabile`. Il costo era nullo: zero righe, e
  nessun riferimento in `backend/` o `frontend/`.
* 2026-08-31 — si apre il varco `CONFERMATA → ANNULLATA` sul solo `RIPORTO`.

---

{% include-markdown "signature-core.md" %}
