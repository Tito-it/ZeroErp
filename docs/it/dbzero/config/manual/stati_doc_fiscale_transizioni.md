## 📘 Documentazione Concettuale – Tabella `config.stati_doc_fiscale_transizioni`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale) — il vocabolario degli stati che questa matrice collega
> * [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) — il lotto, che segue i passaggi non riservati alla fattura
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) — la fattura, che segue i passaggi non riservati al lotto
> * [config.azioni_processo](/dbzero/config/tabelle/azioni_processo) — le azioni di processo a cui punta `azione_processo_codename`
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_fatturazione_lotti_guard_stato](/dbzero/vendite/funzioni/trgfn_fatturazione_lotti_guard_stato) — il guard di stato del lotto, che legge la matrice
> * [vendite.trgfn_fatture_guard_stato](/dbzero/vendite/funzioni/trgfn_fatture_guard_stato) — il guard di stato della fattura, che legge la matrice
> * [script.fn_doc_passaggio](/dbzero/script/funzioni/fn_doc_passaggio) — la riga viva di un passaggio, per i verbi, il backend e la capability
> * [vendite.fn_cambia_stato_lotto](/dbzero/vendite/funzioni/fn_cambia_stato_lotto) — il verbo dei passaggi manuali del lotto
>
> Guide:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — la matrice come unica fonte dei passaggi; la forma propria della fattura

---

### 🎯 Scopo Principale

`config.stati_doc_fiscale_transizioni` è la **matrice dei passaggi ammessi** fra gli stati del ciclo
di fatturazione, per i **lotti** e per le **fatture**: una riga è un passaggio da uno stato a un
altro, con l'ambito a cui vale, il permesso che chiede e come lo disegna l'interfaccia.

Lotto e fattura condividono il vocabolario ma hanno macchine a stati distinte: la stessa tabella le
porta entrambe, separate dalle colonne di ambito.

---

### L'ambito: `solo_lotto` e `solo_fattura`

* Il **lotto** segue le righe con `solo_fattura` falso; la **fattura** le righe con `solo_lotto`
  falso. Una riga con entrambi falsi vale per tutti e due.
* La chiave è la quadrupla (stato di partenza, stato di arrivo, `solo_lotto`, `solo_fattura`): lo
  stesso passaggio può avere una riga per il lotto e una per la fattura.
* ⭐ **`ammesso` è la colonna viva** della matrice (questa tabella non ha `attivo`): un passaggio
  conta solo se `ammesso` è vero. Una riga con `ammesso` falso equivale a un passaggio assente.

---

### Il tipo di lotto: `meta.tipo_lotto`

Una riga con `meta.tipo_lotto` vale **solo** per i lotti di quel tipo (per esempio `GIORNALIERO`);
senza la chiave vale per tutti i tipi. Un passaggio che deve valere per più tipi sulla stessa coppia
di stati si scrive **senza** `tipo_lotto`, perché una seconda riga sulla stessa coppia violerebbe la
chiave.

`tipo_lotto` sta solo sui passaggi **di processo** (`meta.manuale` falso): un CHECK lo impone. Un
passaggio che l'operatore preme vale per ogni tipo di lotto.

---

### Chi può: `azione_processo_codename`

La colonna dice l'azione di processo che il passaggio chiede; vuota vuol dire che basta il permesso
sul documento, che controlla il backend. La leggono, tutti da
[`script.fn_doc_passaggio`](/dbzero/script/funzioni/fn_doc_passaggio), i verbi
(`E_PERMESSO_NEGATO`), il backend (il 403 prima della transazione) e la capability del lotto (il
bottone si nasconde a chi non ha l'azione).

L'azione `numera_fatture_lotti` sta su «numera» (`EMESSA → DEFINITIVA`) e su «riporta in bozza»
(`EMESSA → DRAFT`) del lotto. L'annullo del lotto in bozza e tutti i passaggi della fattura, che
sono di processo, non chiedono un'azione.

---

### `meta`: come il passaggio si presenta

* **`manuale`** — obbligatorio e booleano (un CHECK): `true` per i passaggi che l'operatore preme,
  `false` per quelli che scrive la pipeline. I passaggi di processo non compaiono fra i bottoni.
* **`action_key`**, **`label_key`**, **`requires_confirm`**, **`outlined`** — sui passaggi
  manuali, la chiave dell'azione, l'etichetta, la conferma e l'aspetto del bottone. Icona e colore
  non sono dati del database: li sceglie il frontend dall'`action_key`.

---

### Chi legge la matrice

* I **guard di stato** del lotto e della fattura rifiutano ogni cambio che non ha una riga ammessa
  nel proprio ambito (`E_LOTTO_PARAMETRO_NON_COERENTE`); quello del lotto confronta anche il tipo
  di lotto.
* I **verbi**, il **backend** e la **capability** leggono la riga del passaggio da
  [`script.fn_doc_passaggio`](/dbzero/script/funzioni/fn_doc_passaggio).
* ⚠️ Il vocabolario ha una seconda sede che deve dire la stessa cosa: uno stato che la matrice fa
  raggiungere a un lotto deve avere `applica_lotto` in
  [`config.stati_doc_fiscale`](/dbzero/config/tabelle/stati_doc_fiscale). Lo presidia un pgTAP.

Un passaggio si aggiunge, si toglie o si spegne nel CSV
`80_data/sql/config/stati_doc_fiscale_transizioni.csv`, non nel codice. Una riga punta solo a stati
attivi, e uno stato usato dalla matrice non si disattiva.

---

### Codici errore

* `E_LOTTO_PARAMETRO_NON_COERENTE` — il guard di stato del lotto o della fattura: passaggio non ammesso nel suo ambito, o stato non applicabile alla prima assegnazione.
* `E_PERMESSO_NEGATO` — il verbo: chi chiede il passaggio non ha l'azione di processo della riga.

---

### Test

* `db/pgtap/config/test-stati-doc-fiscale-applica-lotto-vs-matrice-v1.sql` — gli stati raggiungibili da un lotto hanno `applica_lotto`.
* `db/pgtap/vendite/test-fattura-lotto-al-modello-v1.sql` — lotto e fattura sul modello del documento.
* `db/pgtap/vendite/test-available-actions-lotto-v1.sql` — i bottoni del lotto dalla matrice.
* `db/pgtap/script/test-doc-azioni-permesse-v1.sql` — il permesso del passaggio dalla sua riga.

---

### Note di migrazione

* 2026-10-24 / 2026-10-27 — arriva `azione_processo_codename` (brief
  `brief-modello-documento-vendita` §15): il permesso del passaggio passa dal codice alla riga.

---

{% include-markdown "signature-core.md" %}
