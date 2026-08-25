## 📘 Documentazione Concettuale – Vista `pagamenti.vw_eccedenze_da_sistemare`

### 🎯 Scopo Principale

(rev 2026-08-22)

**L'elenco** del processo rimborsi: i documenti il cui residuo ha **cambiato
segno**, cioè che in valore assoluto hanno incassato più del totale.

Si legge insieme al suo registro:

```text
vw_eccedenze_da_sistemare   →  che cosa c'è DA FARE
sistemazioni                →  che cosa è STATO FATTO
```

---

### ⭐ La condizione non ha estremi fissi, ed è ciò che la salva

```sql
sign(saldo) = -sign(totale_a_pagare)
```

Su una **fattura** vuol dire *saldo negativo*; su una **nota di credito** vuol
dire *saldo positivo*. La formula è la stessa perché **non nomina né l'una né
l'altra**.

⚠️ Un intervallo `0 ≤ x ≤ totale` su un documento a credito diventa **vuoto**: è
la trappola che questa forma evita per costruzione, ed è la stessa famiglia della
regola di capienza del lotto 5.

### ⭐ «Per cliente» senza perdere il documento

D15-b chiede di raggruppare **per cliente** — *«un modo di interrogare i saldi
del cliente»* — perché la compensazione ha senso solo a quel livello. Ma l'azione
si fa **su un documento**.

⭐ La vista fa entrambe: **una riga per documento**, e le colonne del cliente
calcolate **in finestra** (`eccedenza_cliente`, `documenti_cliente`). Ordinata
per cliente si legge come un elenco per cliente, e ogni riga resta azionabile.
⚠️ Una vista già aggregata avrebbe perso proprio ciò che serve per agire.

### ⭐ `chi_e_in_credito`: la colonna che evita l'errore di verso

| Documento | Residuo | Chi è in credito |
| --- | --- | --- |
| fattura (totale > 0) | negativo → ha incassato **di più** | il **cliente** |
| nota di credito (totale < 0) | positivo → si è restituito **di più** | l'**azienda** |

Farlo dedurre a chi legge è chiedergli di rifare il ragionamento ogni volta, e
sbagliarlo significa **rimborsare denaro che si deve incassare**.

### ⚠️ I due contatori segnalano, non filtrano

Fra la decisione e l'effetto ci sono **due** passi, non uno:

```text
BOZZA        →  nessuno ha ancora fatto niente
CONFERMATA   →  il documento c'è, ma non è ancora REGISTRATO
(registrato) →  i movimenti esistono, e la riga sparisce DA SOLA
```

⛔ Un documento con un atto in bozza **resta nell'elenco**: la decisione è presa
ma il denaro non si è mosso. Toglierlo sarebbe **nascondere**, ed è l'opposto di
*la vista presenta, la persona decide*.

⚠️ Con un solo flag sulla bozza, una fattura con l'atto già confermato e la
distinta ancora da registrare sarebbe comparsa **senza nessun segno** —
indistinguibile da una su cui nessuno ha mai guardato.

### Regole principali

* **È una vista, non una tabella.** Materializzarla richiederebbe un automatismo
  che la tiene aggiornata, cioè *la rincorsa che questo cantiere ha chiuso per
  costruzione*. ⭐ I saldi si **leggono**, non si conservano.
* Il saldo lo dà `pagamenti.fn_get_saldo_fattura`, non una somma riscritta qui:
  due definizioni della stessa cosa divergono al primo aggiustamento.
* Si parte dai documenti che hanno **almeno un movimento**: senza denaro
  registrato il residuo coincide col totale e non può aver cambiato segno.
* `security_invoker = on`: legge tre tabelle con le policy, e senza girerebbe
  come proprietario mostrando a ciascuno i documenti dell'altro.
* ⚠️ La vista prende dalla funzione del saldo **una colonna per nome**
  (`s.saldo`), senza dichiarare la lista degli alias: così una colonna in più
  sulla funzione non la riguarda.

---

### 🕘 Storia

* **25-08-2026** — **ricreata senza cambiare nessuna colonna** (S5-1 del cantiere
  incassi). ⭐ Non è una modifica alla vista: `fn_get_saldo_fattura` è passata da
  due numeri a quattro, e per sostituire una funzione bisogna prima togliere la
  vista che la usa — le due cose viaggiano perciò nello **stesso** changeSet,
  così il database non resta mai senza l'una o senza l'altra. ⚠️ Ricreando si
  ripetono `security_invoker` e i GRANT: sono cose che si perdono **in silenzio**,
  e la prima delle due farebbe vedere a ciascun emittente i documenti dell'altro.
* **22-08-2026** — prima stesura (lotto 7).

---

{% include-markdown "signature-core.md" %}
