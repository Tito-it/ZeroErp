## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_sistemazioni_guard_dati`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.sistemazioni](/dbzero/pagamenti/tabelle/sistemazioni) — il registro su cui il guard è montato
> * [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione) — il centro dedicato alla compensazione
>
> Approfondimento funzioni:
>
> * [script.fn_get_fattura_intestazione](/dbzero/script/funzioni/fn_get_fattura_intestazione) — l'intestazione delle fatture, letta fuori dalla row security
> * [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) — il guard di scope montato accanto, che decide chi può scrivere
> * [pagamenti.trgfn_sistemazioni_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_sistemazioni_guard_transizione) — il guard di transizione, che parla prima di questo

---

### 🎯 Scopo Principale

Verifica che un atto di sistemazione sia coerente con se stesso e con i documenti che nomina, all'inserimento e a ogni modifica.

⛔ Non decide chi può scriverlo: quello è `script.trgfn_guard_emittente_scope`, montato accanto
su **entrambe** le colonne di fattura.

---

### Le regole, e chi le sbaglia

| Regola | Chi sbaglia | Codice |
| --- | --- | --- |
| la **destinazione** vuole i documenti che le servono: niente destinazione sul rimborso, una destinazione diversa dall'origine su riporto e compensazione | l'operatore | `E_SISTEMAZIONE_DOCUMENTI_INCOERENTI` |
| il **motivo** c'è dove serve: su un annullamento e su un riporto | l'operatore | `E_SISTEMAZIONE_MOTIVO_OBBLIGATORIO` |
| cliente ed emittente **dichiarati** corrispondono a quelli della fattura di partenza | chi ha scritto la chiamata | `E_PAGAMENTI_CHIAMATA_NON_VALIDA` |
| i due documenti sono **dello stesso cliente e della stessa azienda** | l'operatore | `E_SISTEMAZIONE_DOCUMENTI_NON_ABBINABILI` |
| la distinta di una **compensazione** sta sul centro dedicato | chi ha costruito la distinta | `E_CENTRO_NON_ABILITATO_COMPENSAZIONE` |

⭐ La regola su cliente ed emittente ha un codice **tecnico** apposta: non li sceglie una
persona in un modulo, li **deriva** chi costruisce l'atto. Il lettore del messaggio è
`dbops.error_log`, non l'operatore: il codice si sceglie da chi può rimediare. Lo stesso codice
scatta se la fattura di partenza non risolve emittente e cliente, che è un dato rotto a monte.

⭐ La regola sui due documenti è quella che rende sensata la compensazione: mettere insieme due
documenti di **un solo cliente**. Spostare denaro fra clienti diversi non è una sistemazione, è
un errore di attribuzione.

---

### 🔴 Le fatture si leggono fuori dalla row security

`vendite.fatture` ha la RLS, e il guard gira con i privilegi di chi scrive: leggendola
direttamente direbbe «è di un altro cliente» **anche quando il cliente è lo stesso**, solo
perché una delle due fatture non si vede. La domanda passa perciò da
[fn_get_fattura_intestazione](/dbzero/script/funzioni/fn_get_fattura_intestazione), che è
`SECURITY DEFINER`.

---

### ⚠️ Ospita la regola del centro di compensazione

«Una distinta di compensazione sta sul centro dedicato» è una regola che dipende
dalla **destinazione**, cioè da un dato dell'atto. Sulla distinta non potrebbe scattare: quando la
distinta nasce nessun atto la cita ancora. Qui scatta quando l'atto riceve la sua distinta, cioè
alla conferma.

---

### L'ordine: «puoi toccarlo?» → «è ancora aperto?» → «il contenuto sta in piedi?»

Il guard è agganciato in fase `a20`: i trigger `BEFORE ROW` scattano in ordine alfabetico di
nome, e devono parlare prima i due guard di scope (`a10`) e quello di transizione (`a15`).

* Si guarda anche in `UPDATE`: l'atto vive, e un guard che parlasse solo all'`INSERT`
  lascerebbe correggere la destinazione senza rileggerne i documenti.
* I `CHECK` della tabella sui documenti e sul motivo sono la **rete**, non il presidio: un
  `23514` non dice quale regola è caduta, il guard sì, e nomina il campo.

---

### Codici errore

* `E_SISTEMAZIONE_DOCUMENTI_INCOERENTI` — la destinazione non va d'accordo con i documenti
  indicati.
* `E_SISTEMAZIONE_MOTIVO_OBBLIGATORIO` — manca il motivo su un atto annullato o su un riporto.
* `E_PAGAMENTI_CHIAMATA_NON_VALIDA` — la fattura di partenza non risolve emittente e cliente,
  oppure quelli dichiarati sull'atto non sono i suoi.
* `E_SISTEMAZIONE_DOCUMENTI_NON_ABBINABILI` — il documento di destinazione è di un altro
  cliente o di un'altra azienda.
* `E_CENTRO_NON_ABILITATO_COMPENSAZIONE` — la distinta di una compensazione non sta sul centro
  dedicato.

---

### Test

* `db/pgtap/pagamenti/test-sistemazioni-registro.sql` — i test da 5 a 10: rimborso con
  destinazione, compensazione senza destinazione, destinazione uguale all'origine, riporto
  senza motivo, documenti di clienti diversi (asserito sulla frase), emittente dichiarato
  diverso; i test 12 e 13: una compensazione confermata su una distinta del centro `BANCA` è
  rifiutata con `E_CENTRO_NON_ABILITATO_COMPENSAZIONE`, e l'atto resta in bozza.

---

### Note di migrazione

* 2026-08-22 — nasce con il registro `sistemazioni`. La regola del centro di compensazione si
  sposta qui da `trgfn_vendite_contabili_guard_ente_centro`, dove era appesa alla colonna
  `vendite_contabili.compensazione_id`, sparita quando il legame ha cambiato verso; il codice
  resta `E_CENTRO_NON_ABILITATO_COMPENSAZIONE`, perché regola e rimedio sono gli stessi.

---

{% include-markdown "signature-core.md" %}
