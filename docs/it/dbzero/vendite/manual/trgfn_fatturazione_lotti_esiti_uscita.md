## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_fatturazione_lotti_esiti_uscita`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti_esiti](/dbzero/vendite/tabelle/fatturazione_lotti_esiti)
>
**Approfondimento funzioni:**
>
• [vendite.fn_escludi_documento_da_giro](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro)
> • [dbops.trgfn_coda_archiviazione](/dbzero/dbops/funzioni/trgfn_coda_archiviazione)

---

### 🎯 Scopo Principale
(latest review 2026-09-08)

Governa l'**uscita di un documento dal giro di fatturazione**, e fa due cose:

1. **Il divieto** — `ESCLUSO` è uno stato **terminale**: un documento tolto da un
   lotto non ci rientra.
2. **Il timbro** — *quando* è uscito e *chi* l'ha deciso li scrive il database,
   mai il chiamante.

Monta come trigger `BEFORE INSERT OR UPDATE OF stato_esecuzione` su
[`vendite.fatturazione_lotti_esiti`](/dbzero/vendite/tabelle/fatturazione_lotti_esiti).

---

### Perché il timbro non usa `data_update` / `user_update`

Quelle due colonne le riscrive **qualunque** aggiornamento successivo della riga:
il momento dell'uscita si perderebbe in silenzio, e senza nessun errore. Servono
colonne dedicate — è lo stesso ragionamento già applicato all'archiviazione delle
code di lavoro.

⭐ E il timbro è **immutabile**: chi passasse con una data propria non la vedrebbe
attecchire. Non c'è modo di far dire alla riga una cosa che il suo stato
smentisce.

---

### Il rifiuto guarda la **direzione**, non la menzione

Un aggiornamento che *nomina* la colonna dello stato scatta anche quando le
riassegna **lo stesso valore**. Un divieto scritto sulla menzione rifiuterebbe
scritture che non cambiano niente — lezione già pagata sul gemello delle code.

Quindi: si rifiuta solo il passaggio che porta **fuori** da `ESCLUSO`.

---

### Perché agisce anche in inserimento, e perché non nasconde il vincolo

Il **timbro** deve valere anche su una riga che nasce già esclusa, o quelle due
colonne resterebbero vuote su un fatto avvenuto.

⛔ Ma in inserimento la funzione **non rifiuta mai**: scrive e basta. È la
condizione che tiene buona la regola generale *«un controllo che agisce anche in
inserimento nasconde il vincolo di tabella»* — qui il vincolo che pretende il
**motivo** continua a valutare dopo, e a rifiutare l'uscita muta.

⚠️ E la matrice delle transizioni resta fuori dall'inserimento: il divieto scatta
solo in aggiornamento, come per tutte le altre entità con un ciclo di stato.

---

### Perché il nome non dice «guard»

`fn_guard_*` è riservato alle funzioni che **verificano e basta**. Questa scrive
la riga: chiamarla guard direbbe che l'unica cosa che fa è rifiutare.

---

### L'errore che solleva

`E_LOTTO_DOC_USCITA_IRREVERSIBILE`, di classe **tecnica** — non un conflitto di
stato.

⚠️ **La differenza conta**: qui non ci arriva un operatore.
[`vendite.fn_escludi_documento_da_giro`](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro)
chiede prima alla sua funzione di controllo, quindi questo rifiuto nasce solo da
una scrittura diretta sulla tabella — cioè da un programma che sbaglia. Dire a
una persona di «rileggere lo stato» la manderebbe a guardare una cosa che non ha
nessun modo di cambiare.

---

### Che cosa succede a una riga che **non** è esclusa

Le due colonne del timbro vengono azzerate. Una riga che dicesse *«non uscita,
uscita il 3 settembre»* sarebbe un dato a metà — due affermazioni che si
smentiscono sulla stessa riga.

> Piano e decisioni: `docs/it/dev/work-done/brief-db-uscita-documento-dal-giro.md`.

---

{% include-markdown "signature-core.md" %}
