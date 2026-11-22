## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_contatti_set_default_contatto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti) — la tabella su cui è montata, di cui scrive `is_default` e `default_context`
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il soggetto, di cui scrive `default_contatto_id`
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_contatto](/dbzero/anagrafiche/funzioni/fn_crea_contatto) — il verbo che fa nascere i contatti
> * [script.fn_get_contatto_default](/dbzero/script/funzioni/fn_get_contatto_default) — chi legge il predefinito
>
> Guide:
>
> * [Gestione dei Contatti](/guide/gestione-dei-contatti) — il contatto predefinito nel modello dei contatti

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_contatti_set_default_contatto` tiene il contatto predefinito di ogni soggetto e contesto: a
ogni nascita e a ogni modifica di un contatto ne calcola il contesto, fa predefinito il primo del contesto o
quello marcato, toglie il segno all'altro, e aggiorna il puntatore del soggetto.

---

### Che cosa fa a ogni scrittura

Prima della scrittura di ogni riga di `anagrafiche.contatti`, su qualunque colonna:

* calcola il contesto dalla riga (istanza, poi ruolo, poi soggetto) e svuota `default_context`;
* se la riga è marcata predefinita, toglie il segno agli altri predefiniti dello stesso soggetto e contesto, e
  scrive il contesto sulla riga;
* se non è marcata e il contesto non ha un predefinito, la marca;
* se la riga è, o diventa, il predefinito del contesto `soggetto`, scrive il suo id in
  `anagrafiche.soggetti.default_contatto_id`.

Togliere il segno agli altri è una modifica di quelle righe, e il trigger scatta anche su di loro: lì il
predefinito di prima c'è ancora, e la riga resta senza segno.

---

### ⚠️ Una modifica del predefinito riscrive il soggetto

Ogni scrittura del predefinito del contesto `soggetto` (anche il cambio di un'email) aggiorna il soggetto, pure
quando il puntatore non cambia. Fa scattare quindi i trigger di `anagrafiche.soggetti`, compresi i controlli
differiti al COMMIT: il contatto obbligatorio, gli indirizzi obbligatori, i dati societari.

---

{% include-markdown "it/dbzero/anagrafiche/_contatto-predefinito.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Il predefinito per ruolo e per istanza.** La chiave è soggetto più contesto: marcare il contatto di un ruolo
  toglie il segno a quello di un altro ruolo dello stesso soggetto.
* **Il contesto senza predefinito.** Togliere il segno o cancellare il predefinito non promuove nessuno, e il
  puntatore del soggetto resta sul contatto di prima, anche quando quello esce dal contesto `soggetto`.
* **Il COMMENT di `default_context`** elenca `utility` fra i valori: il trigger scrive `istanza`.

---

### Test

* `db/pgtap/anagrafiche/test-contatti-soggetto-cliente.sql` — un contatto di ruolo marcato predefinito prende il
  contesto `ruolo` e non tocca il puntatore del soggetto.
* `db/pgtap/anagrafiche/test-fn-crea-contatto-v1.sql` — il primo contatto di un soggetto costruito nasce
  predefinito.

Nessun test prova il passaggio del segno fra due contatti dello stesso contesto, né i due ruoli che condividono
un predefinito.

---

{% include-markdown "signature-core.md" %}
