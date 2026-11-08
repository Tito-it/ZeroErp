## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_pratiche_gen_codice`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica che riceve il codice
> * [config.sistema_codici](/dbzero/config/tabelle/sistema_codici) — la configurazione del codice, e la riga da cui la funzione nasce
>
> Approfondimento funzioni:
>
> * [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice) — il generatore centrale dei codici
> * [script.trgfn_config_sistema_codici_sync_gen_codice](/dbzero/script/funzioni/trgfn_config_sistema_codici_sync_gen_codice) — crea, sposta e ritira questa funzione dalla configurazione

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_pratiche_gen_codice` assegna il codice della pratica quando chi la
crea non lo fornisce, chiedendolo al generatore centrale `script.fn_generate_codice` con la chiave
`pratica`.

La funzione non calcola niente: riconosce il campo vuoto e chiede il codice.

---

### Le regole

* Scatta prima dell'inserimento di una pratica e prima di un aggiornamento del codice.
* Se il codice è vuoto, o fatto di soli spazi, lo valorizza col generatore; un codice presente non
  viene mai sovrascritto.
* Formato, prefisso e numerazione stanno nella riga `pratica` di `config.sistema_codici`.

---

### ⚠️ Da sapere

* **La chiave è `pratica` al singolare**, mentre schema e tabella sono al plurale. Il legame con
  `config.sistema_codici` è per stringa: rinominare quella riga fa fallire ogni inserimento.
* **Una riga di configurazione con la sequenza spenta dà un codice vuoto, non un errore.** Il difetto
  emergerebbe a valle, non qui.
* **In aggiornamento, svuotare il codice ne genera uno nuovo.** Sul codice della pratica non è montato
  un lock: chi lo svuota in un aggiornamento ottiene un codice diverso, senza errori.

---

### ⚠️ La funzione è generata, non scritta a mano

La funzione, la sequenza e il trigger che la invoca sono creati da
`script.trgfn_config_sistema_codici_sync_gen_codice`, il trigger di `config.sistema_codici`: basta la
riga `pratica` con la tabella e la colonna di destinazione e la sequenza accesa. Per questo tutte le
funzioni `*_gen_codice` del progetto hanno lo stesso corpo: è la stessa funzione, parametrizzata per
tabella.

* **Modificarla a mano non serve.** Il caricamento della configurazione ripassa a ogni migrazione e la
  riscrive dal modello: un ritocco locale sparisce senza traccia.
* **Non si spegne togliendola, si spegne dalla configurazione.** Spegnendo la sequenza, il sync ritira
  da sé trigger e funzione; tolta a mano, ricompare alla migrazione successiva.
* **Cambiare tabella o colonna di destinazione sposta gli oggetti**: il sync ritira i vecchi e li ricrea
  altrove, senza avvisi.

---

### Codici errore

La funzione non solleva errori propri.

* `E_SEQUENZA_NON_CONFIGURATA` — sollevato da `script.fn_generate_codice` quando la riga `pratica`
  manca in `config.sistema_codici`.

---

{% include-markdown "signature-core.md" %}
