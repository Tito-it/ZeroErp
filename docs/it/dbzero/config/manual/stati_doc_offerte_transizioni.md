## 📘 Documentazione Concettuale – Tabella `config.stati_doc_offerte_transizioni`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte) — il vocabolario degli stati che questa matrice collega
> * [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) — l'offerta, che segue i passaggi
> * [config.azioni_processo](/dbzero/config/tabelle/azioni_processo) — le azioni di processo a cui punta `azione_processo_codename`
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione) — il guard di transizione, che legge la matrice
> * [vendite.fn_cambia_stato_offerta](/dbzero/vendite/funzioni/fn_cambia_stato_offerta) — il verbo di stato, che fa rispettare la motivazione
> * [script.fn_doc_passaggio](/dbzero/script/funzioni/fn_doc_passaggio) — la riga viva di un passaggio, per i verbi, il backend e la capability
> * [vendite.fn_offerta_proietta_stato_revisione](/dbzero/vendite/funzioni/fn_offerta_proietta_stato_revisione) — scrive i due passaggi automatici, superamento e rientro
>
> Guide:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — la matrice come unica fonte dei passaggi, il permesso sul passaggio

---

### 🎯 Scopo Principale

`config.stati_doc_offerte_transizioni` è la **matrice dei passaggi ammessi** fra gli stati
dell'offerta commerciale: una riga è un passaggio da uno stato a un altro, con il permesso che
chiede, se lo preme l'operatore o lo scrive un automatismo, e come lo disegna l'interfaccia.

Il nome è fuori serie (le altre matrici si chiamano `transizioni_stati_*`): è una divergenza
dichiarata, e nessuna regola dipende dal nome.

---

### I passaggi

| Da | A | Chi | Azione di processo | Motivazione | Che cosa vuol dire |
| --- | --- | --- | --- | --- | --- |
| `BOZZA` | `EMESSA` | operatore | `emetti_offerta` | — | l'emissione al cliente; congela la versione di listino |
| `BOZZA` | `ANNULLATA` | operatore | — | obbligatoria | il ritiro interno della bozza |
| `EMESSA` | `ACCETTATA` | operatore | — | — | il sì del cliente |
| `EMESSA` | `RIFIUTATA` | operatore | — | obbligatoria | il no del cliente |
| `EMESSA` | `SUPERATA` | automatico | — | — | nasce una revisione: il padre è superato |
| `SUPERATA` | `EMESSA` | automatico | — | — | l'ultima revisione viva è annullata: il padre rientra |
| `ACCETTATA` | `ANNULLATA` | operatore | `emetti_offerta` | obbligatoria | l'offerta accettata che non si trasforma |

```text
BOZZA ──> EMESSA ──> ACCETTATA ──> ANNULLATA
  │        │   ▲
  │        │   └─── SUPERATA ── (rientro automatico)
  │        ├──> SUPERATA   (automatico: nasce una revisione)
  │        └──> RIFIUTATA  (no del cliente)
  └──> ANNULLATA  (ritiro interno)
```

`RIFIUTATA` e `ANNULLATA` non hanno passaggi in uscita. `RIFIUTATA` è il no del cliente, e per
questo non si raggiunge dalla bozza: il ritiro interno è l'annullo.

I due passaggi automatici li scrive
[`vendite.fn_offerta_proietta_stato_revisione`](/dbzero/vendite/funzioni/fn_offerta_proietta_stato_revisione),
chiamata dai trigger della revisione e del rientro del padre. Il guard lascia uscire dal superamento
solo se non c'è più una revisione figlia viva (`E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA`).

---

### Chi può: `azione_processo_codename`

La colonna dice l'azione di processo che il passaggio chiede; vuota vuol dire che basta il permesso
sull'offerta, che controlla il backend. Una sola azione per documento, sui passaggi pesanti:
l'emissione e l'annullo dell'accettata. Accettare e rifiutare chiedono il solo permesso
sull'offerta.

La leggono, tutti da [`script.fn_doc_passaggio`](/dbzero/script/funzioni/fn_doc_passaggio), i verbi
(`E_PERMESSO_NEGATO`), il backend (il 403 prima della transazione) e la capability (il bottone si
nasconde a chi non ha l'azione).

---

### `meta`: come il passaggio si presenta

| Chiave | Significato |
| --- | --- |
| `manuale` | obbligatoria e booleana (un CHECK): `false` per i passaggi automatici, che non compaiono fra i bottoni |
| `action_key` | la chiave dell'azione (`emetti`, `annulla`, `accetta`, `rifiuta`) |
| `label_key` | la chiave di traduzione dell'etichetta del bottone |
| `requires_confirm` | il bottone chiede conferma prima di procedere |
| `requires_motivazione` | il passaggio chiede la motivazione: la capability disegna il campo, il verbo [`vendite.fn_cambia_stato_offerta`](/dbzero/vendite/funzioni/fn_cambia_stato_offerta) la pretende (`E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA`) e la rifiuta dove la riga non la chiede (`E_OFFERTA_MOTIVAZIONE_NON_AMMESSA`) |
| `outlined` | l'aspetto del bottone |

Icona e colore non sono dati del database: li sceglie il frontend dall'`action_key`.

---

### Il guard di transizione: la matrice, e ciò che la matrice non può dire

Il trigger
[`vendite.trgfn_offerte_commerciali_guard_transizione`](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione)
scatta a ogni cambio di stato dell'offerta e rifiuta ogni passaggio che non ha una riga attiva
nella matrice (`E_OFFERTA_TRANSIZIONE_NON_AMMESSA`). Poi applica le condizioni che dipendono da
altre tabelle, con gli stessi predicati che la capability usa per spegnere i bottoni:

* **all'emissione**: la versione di listino in vigore, che il passaggio congela sull'offerta
  (`E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`, `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`),
  gli indirizzi del cliente e le righe ammesse;
* **all'emissione e all'accettazione**: i prezzi autorizzati — ma non sul rientro dal superamento,
  che non è un invio al cliente;
* **all'annullo**: nessun contratto o ordine vivo nato dall'offerta.

Il guard scrive anche le date del passaggio: `data_emissione` al primo ingresso in `EMESSA` (un
rientro non la riscrive), `data_accettazione`, `data_rifiuto` e `data_annullamento` all'ingresso nei
loro stati.

---

### Come si cambia

* Un passaggio si aggiunge, si toglie o si spegne (`attivo`) nel CSV
  `80_data/sql/config/stati_doc_offerte_transizioni.csv`, non nel codice.
* Una coppia di stati ha al più una riga, e lo stato di arrivo è diverso da quello di partenza.
* Una riga punta solo a stati attivi, e uno stato usato dalla matrice non si disattiva.

---

### Codici errore

* `E_OFFERTA_TRANSIZIONE_NON_AMMESSA` — il passaggio non ha una riga attiva nella matrice.
* `E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA` — un'uscita dal superamento con una revisione figlia ancora viva.
* `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`, `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA` — l'emissione senza una versione di listino in vigore.
* `E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA`, `E_OFFERTA_MOTIVAZIONE_NON_AMMESSA` — la motivazione mancante dove la riga la chiede, o data dove non la chiede.
* `E_PERMESSO_NEGATO` — chi chiede il passaggio non ha l'azione di processo della riga.

---

### Test

* `db/pgtap/vendite/test-offerta-al-modello-v1.sql` — l'offerta sul modello del documento: verbo, permesso, motivazione.
* `db/pgtap/config/test-transizioni-uscita-manuale-v1.sql` — ogni stato che ha uscite ne ha almeno una che una persona può premere, o dichiara perché non ce l'ha (`meta.nessuna_azione_key` dello stato).
* `db/pgtap/vendite/offerte_commerciali/test-offerte-rientro-padre-revisione-annullata.sql` — il rientro automatico dal superamento.
* `db/pgtap/vendite/offerte_commerciali/test-righe-ammesse-ai-passi-e-annullo-v1.sql` — le righe ammesse all'emissione e l'annullo.

---

### Note di migrazione

* `BOZZA → RIFIUTATA` è stato tolto dalla matrice perché incongruo: il rifiuto è del cliente, il
  ritiro interno è l'annullo.
* 2026-08-28 — nasce il rientro automatico `SUPERATA → EMESSA` (brief
  `brief-db-revisione-attiva-due-domande`).
* 2026-09-28 — icona e colore escono dal `meta` (brief `brief-db-icone-azioni-per-significato`).
* 2026-10-21 — nasce l'annullo dell'accettata `ACCETTATA → ANNULLATA`.
* 2026-10-26 — arriva `azione_processo_codename`, e `requires_motivazione` diventa una regola del
  verbo (brief `brief-modello-documento-vendita` §13).

---

{% include-markdown "signature-core.md" %}
