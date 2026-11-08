## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_contratto`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti) — la testata che la fixture fa nascere
> * [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) — l'offerta da cui nasce un figlio
>
> Approfondimento funzioni:
>
> * [vendite.fn_create_contratto](/dbzero/vendite/funzioni/fn_create_contratto) — la madre di produzione da cui nasce
> * [vendite.fn_push_offerta_a_contratto](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto) — la push da cui nasce il figlio di un'offerta
> * [dbops.fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder) — il cliente su cui nasce
> * [dbops.fn_pgtap_crea_listino](/dbzero/dbops/funzioni/fn_pgtap_crea_listino) — il listino di un contratto attivo
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — l'attivazione dal verbo
> * [vendite.fn_annulla_contratto](/dbzero/vendite/funzioni/fn_annulla_contratto) — il verbo dell'annullo
> * [vendite.fn_documento_legami](/dbzero/vendite/funzioni/fn_documento_legami) — i legami che l'annullo dichiara
> * [vendite.trgfn_attivita_guard_contratto](/dbzero/vendite/funzioni/trgfn_attivita_guard_contratto) — perché un contratto si chiede sul conto della commessa
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP (e degli smoke Python): **un contratto del mondo in una chiamata** — l'azienda con
il suo operatore, il cliente e la testata nello stato scelto — nato dalla madre di produzione.
Restituisce tutte le chiavi.

Prima i test pescavano «il primo contratto che c'è»: su un database nuovo non ce n'è nessuno, e su
quello di sviluppo era il contratto di un'azienda a caso.

---

### ⭐ Nasce dalla madre, come in produzione

Il contratto nasce da `vendite.fn_create_contratto`, che decide numero, testata in bozza e
indirizzo di default. La fixture le dichiara l'azienda: quella di chi agisce, a cui il cliente è
legato. Il figlio di un'offerta nasce invece dalla push, come in produzione (sotto).

---

### Gli stati, per la strada dell'applicazione

Lo stato si giudica prima di costruire.

* **Bozza** (default): lo stato di nascita, senza listino se il test non ne dà uno.
* **Attivo**: un contratto si attiva su un listino, quindi se il test non lo dà la fixture ne
  costruisce uno dell'azienda di chi agisce, per l'utility del cliente. Il passaggio è il verbo
  del contratto, attraverso `dbops.fn_pgtap_porta_a_stato`, che concede l'azione all'operatore: il
  guard di transizione giudica come per l'applicazione (prezzi, indirizzi, righe, contratto
  sovrapposto). Un secondo contratto attivo dello stesso cliente con date sovrapposte lo rifiuta il
  modello: lo costruisce il test, con le sue date.
* **Annullato**: dal verbo dell'annullo. I legami del contratto (un figlio ha la sua offerta) si
  dichiarano come fa chi conferma: la fixture li conta da `vendite.fn_documento_legami` e li passa
  al verbo.
* ⛔ **Cessato non si costruisce**, e nemmeno un altro codice: un contratto cessato vuole la data
  di fine e passa da attivo con la regola della cessazione. È il caso del test; la fixture lo dice
  prima di scrivere.

---

### Il contratto di un cliente già costruito

Senza conto di fatturazione ogni chiamata costruisce un cliente nuovo, nella stessa azienda. Con
il conto di un cliente costruito prima il contratto nasce su quel cliente, e la fixture non
costruisce un cliente in più. È il caso degli smoke del backend: il contratto citato da una riga
di commessa deve essere del conto della sua commessa, quindi si chiede su quel conto.

⚠️ Il conto viene verificato: uno di un'altra azienda ferma subito la fixture, invece di produrre
una testata che un controllo rifiuterebbe più avanti con un messaggio che non la nomina.

---

### Periodo, data e listino del test

Il test può dare inizio e fine di validità, la data del contratto e il listino: passano alla madre,
e il contratto attivo nasce col periodo e il listino voluti, senza ritocchi in bozza. Vuoti,
decide la madre (e un contratto attivo senza listino ne riceve uno del mondo).

---

### Il figlio di un'offerta

In produzione un contratto figlio di un'offerta nasce solo dalla push, che copia dall'offerta
listino, indirizzi, righe e utility e ne giudica lo stato. Con l'offerta la fixture fa nascere il
contratto da lì, sul cliente dell'offerta.

* L'offerta deve essere **accettata**: portarla lì è il caso del test, e se non lo è la push lo
  dice. Un'offerta che non si vede ferma la fixture.
* Il cliente è quello dell'offerta: un conto diverso ferma la fixture.
* Periodo, data e listino li decide la push: chiederli insieme all'offerta ferma la fixture.
* Un figlio annullato non consuma l'offerta: dalla stessa offerta ne può nascere un altro.

---

### Che cosa non scrive

Righe, eccezioni e scheda di fornitura: sono il caso del test (un figlio le eredita dall'offerta,
dalla push). Esce con i vincoli richiusi (`IMMEDIATE`).

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-contratto-v1.sql` — contratto attivo dal nulla, con numero,
  conto ed emittente, e un listino dell'azienda di chi agisce con la versione congelata
  all'attivazione; bozza e annullato sullo stesso cliente; cliente nuovo nella stessa azienda;
  conto di un'altra azienda e stato cessato rifiutati; il figlio di un'offerta annullato col legame
  dichiarato, un secondo figlio attivo della stessa offerta col suo listino, un conto diverso da
  quello dell'offerta rifiutato; periodo, data e listino del test.

---

### Note di migrazione

* 2026-10-21 — nasce su richiesta del backend per lo smoke delle attività di contratto; gli stati
  costruibili sono una decisione di Tid dello stesso giorno.
* 2026-10-22 — la verifica del conto passa al building block comune delle fixture.
* 2026-10-24 — il figlio di un'offerta, periodo, data e listino del test; col conto del test non
  costruisce più un cliente in più (`brief-modello-documento-vendita`, Q-2, R-2, §4-octies).
* 2026-10-26 — attivo dal verbo del contratto: la porta rifiuta l'aggiornamento diretto dello stato
  (`brief-modello-documento-vendita`, §11).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
