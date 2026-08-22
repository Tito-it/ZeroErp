## 📘 Documentazione Concettuale – Funzione `vendite.fn_close_commessa_push_run`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse_push_log](/dbzero/vendite/tabelle/commesse_push_log)  
>
**La funzione che apre ciò che questa chiude:**
>
• [vendite.fn_start_commessa_push_run](/dbzero/vendite/funzioni/fn_start_commessa_push_run)  
>
### 🎯 Scopo Principale
`vendite.fn_close_commessa_push_run` **chiude** il giro aperto in testa alla
corsa: gli scrive sopra l'esito, il risultato per handler e la durata.

---

### I due rifiuti, e perché ci sono

Chiudere è l'operazione in cui si può sbagliare, e sono due gli sbagli possibili.

| Cosa si sta facendo | Risposta |
| --- | --- |
| chiudere con `IN_ESECUZIONE` (o con uno stato vuoto o sconosciuto) | ⛔ **rifiutato**: quello non è un esito. Un giro «chiuso in esecuzione» resterebbe aperto per sempre agli occhi di chiunque lo conti, e assomiglierebbe a una corsa interrotta senza esserlo |
| chiudere una riga che non è aperta — perché non esiste, o perché qualcuno l'ha già chiusa | ⛔ **rifiutato**: chi chiama ha perso il filo della propria corsa. Sovrascrivere un esito già registrato farebbe perdere la storia di **due** corse, non di una |

> ⚠️ Entrambi i rifiuti sono di classe **tecnica**: quei valori non li produce
> nessuna persona in un modulo, li produce un programma che sbaglia. Chi legge il
> messaggio è chi ha scritto la chiamata, e infatti il messaggio nomina il
> parametro.

---

### Regole principali

* `stato` viene normalizzato in maiuscolo e deve essere uno fra `COMPLETATO`,
  `PARZIALE`, `ERRORE`.
* ⭐ **Chi chiude senza ripetere `source_types` o `risultato` non cancella quello
  che l'apertura aveva dichiarato**: si sovrascrive solo ciò che si passa.
* `durata_ms` è facoltativa ma non può essere negativa. È la misura del
  chiamante: il database non la ricalcola, perché il tempo che conta include
  anche ciò che è successo fuori dal database.
* La chiusura è atomica: due chiusure in corsa non possono vincere entrambe, e la
  seconda riceve il rifiuto di riga non aperta.

---

### ⭐ Un presidio che vale la pena conoscere

L'elenco degli esiti finali vive in **una sola sede** dentro la funzione: lo
usa il controllo e lo compone il messaggio d'errore. La ragione è concreta —
questa funzione nasce da un difetto in cui il vincolo della tabella ammetteva
quattro stati e la funzione che ci scriveva ne ammetteva tre, e **nessuno dei due
poteva accorgersene**.

Il collegamento fra i due elenchi lo tiene un test
(`db/pgtap/vendite/test-commesse-push-log-function-v1.sql`, asserzione 13), che
rilegge il vincolo dalla tabella: il giorno in cui qualcuno aggiunge un quinto
stato, a dirlo è il test e non la prima scrittura andata storta.

---

{% include-markdown "signature-core.md" %}
