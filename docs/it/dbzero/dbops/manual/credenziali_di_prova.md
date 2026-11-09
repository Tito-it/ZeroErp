## 📘 Documentazione Concettuale – Tabella `dbops.credenziali_di_prova`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.soggetti_di_prova](/dbzero/dbops/tabelle/soggetti_di_prova) — la gemella: l'etichetta dei soggetti di prova
> * [dbops.installazione](/dbzero/dbops/tabelle/installazione) — l'ambiente che decide se un'etichetta può nascere
>
> Approfondimento viste:
>
> * [dbops.vw_radici_di_prova_in_produzione](/dbzero/dbops/views/vw_radici_di_prova_in_produzione) — il presidio che legge le etichette
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_provisiona_dati_di_sviluppo](/dbzero/anagrafiche/funzioni/fn_provisiona_dati_di_sviluppo) — il verbo dei dati di sviluppo, unico scrittore
> * [dbops.trgfn_etichette_di_prova_guard](/dbzero/dbops/funzioni/trgfn_etichette_di_prova_guard) — il guard: nasce solo in sviluppo, poi non cambia

---

### 🎯 Scopo Principale

**L'etichetta delle credenziali di prova**: una riga per ogni credenziale creata dal verbo
dei dati di sviluppo (gli utenti `dev.*`), con la sua chiave, che è lo username con cui la
credenziale è nata.

L'etichetta nasce nella stessa transazione della credenziale. L'applicazione la legge: la
lista degli operatori la usa per nascondere gli utenti di prova (con un filtro attivo di
default) e per mostrarli col contrassegno «di prova».

---

### ⭐ La chiave riconosce l'utente anche dopo una rinomina

Il verbo dei dati di sviluppo è idempotente: alla corsa successiva ritrova la credenziale
dalla chiave dell'etichetta, non dallo username di oggi, quindi la riallinea anche se nel
frattempo è stata rinominata. Uno username uguale a una chiave ma senza etichetta non è un
utente di prova: il verbo lo rifiuta invece di adottarlo.

---

### ⛔ Non cambia, va via solo con la credenziale, in produzione non nasce

* La scrive **solo** il verbo dei dati di sviluppo; all'applicazione la scrittura è revocata.
* Un'etichetta nasce solo in un'installazione dichiarata `SVILUPPO`.
* Modifica e svuotamento della tabella sono sempre rifiutati, e così la cancellazione di
  un'etichetta finché la sua credenziale c'è: togliere l'etichetta di un utente che esiste lo
  nasconderebbe al presidio che cerca i dati di prova in un database di produzione.

---

### ⭐ L'etichetta segue la credenziale

La colonna dell'utente ha una chiave esterna verso le credenziali di Django, in cascata:
quando un amministratore elimina una credenziale di prova
([fn_elimina_credenziale](/dbzero/script/funzioni/fn_elimina_credenziale)), la sua etichetta
va via con lei. Il guard lo ammette perché, a quel punto, la credenziale non c'è più: un'etichetta
senza utente non nasconde niente. L'etichetta non conta come «storia» della credenziale: la
regola che dice se una credenziale si può eliminare guarda solo i legami che la trattengono, e
una cascata non la trattiene.

La chiave esterna nasce dove c'è lo schema di Django: come gli altri legami verso le
credenziali, la crea l'ultima fase della migrazione, e su un database in cui Django non è
ancora installato non c'è.

---

### Codici errore

Li solleva il guard [trgfn_etichette_di_prova_guard](/dbzero/dbops/funzioni/trgfn_etichette_di_prova_guard):

* `E_DATI_DI_SVILUPPO_IN_PRODUZIONE` — un'etichetta nuova su un'installazione che non è di
  sviluppo;
* `E_CONFIG_MANCANTE` — un'etichetta nuova su un'installazione che non ha dichiarato
  l'ambiente;
* `E_ETICHETTA_DI_PROVA_IMMUTABILE` — modifica, svuotamento, o cancellazione con la credenziale
  ancora viva.

---

### Test

* `db/pgtap/dbops/test-etichette-di-prova-v1.sql` — l'applicazione legge e non scrive; in
  sviluppo l'etichetta nasce, poi modifica, cancellazione e svuotamento sono rifiutati; in
  produzione e con l'ambiente non dichiarato un'etichetta nuova è rifiutata.
* `db/pgtap/anagrafiche/test-fn-provisiona-dati-di-sviluppo-v1.sql` — il verbo etichetta gli
  utenti che crea e li ritrova dalla chiave.
* `db/pgtap/dbops/test-credenziale-di-prova-fk-v1.sql` — la chiave esterna c'è dove c'è Django;
  cancellare la credenziale toglie l'etichetta, mentre la cancellazione diretta resta rifiutata;
  la regola di eliminabilità non conta l'etichetta come storia.

---

### Note di migrazione

* 2026-10-18 — nasce con il verbo dei dati di sviluppo (`brief-db-processi-accensione-per-ambiente`, R-4).
* 2026-11-09 — la chiave esterna verso `django.auth_user`, in cascata (`90_end/20261110-57`), e il
  guard che ammette la cancellazione quando la credenziale non c'è più (`20261110-56`)
  (`brief-db-revisione-dbops`, giro 11). Prima l'etichetta sopravviveva alla credenziale.

---

{% include-markdown "signature-core.md" %}
