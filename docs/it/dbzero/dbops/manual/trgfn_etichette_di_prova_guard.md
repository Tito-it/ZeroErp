## 📘 Documentazione Concettuale – Trigger function `dbops.trgfn_etichette_di_prova_guard`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.credenziali_di_prova](/dbzero/dbops/tabelle/credenziali_di_prova) — l'etichetta delle credenziali di prova
> * [dbops.soggetti_di_prova](/dbzero/dbops/tabelle/soggetti_di_prova) — l'etichetta dei soggetti di prova
> * [dbops.installazione](/dbzero/dbops/tabelle/installazione) — l'ambiente dichiarato
>
> Approfondimento viste:
>
> * [dbops.vw_radici_di_prova_in_produzione](/dbzero/dbops/views/vw_radici_di_prova_in_produzione) — il presidio che le etichette alimentano
>
> Approfondimento funzioni:
>
> * [dbops.fn_dati_di_sviluppo_ammessi_su_valori](/dbzero/dbops/funzioni/fn_dati_di_sviluppo_ammessi_su_valori) — la regola sull'ambiente
> * [script.fn_ambiente_installazione](/dbzero/script/funzioni/fn_ambiente_installazione) — il lettore dell'ambiente, che fallisce se manca
> * [anagrafiche.fn_provisiona_dati_di_sviluppo](/dbzero/anagrafiche/funzioni/fn_provisiona_dati_di_sviluppo) — il verbo che scrive le etichette

---

### 🎯 Scopo Principale

**Il guard delle etichette di prova**: un'etichetta nasce solo in un'installazione di
sviluppo, poi non cambia, e si toglie solo insieme a ciò che etichetta. È agganciato alle
due tabelle delle etichette, le credenziali e i soggetti di prova.

---

### ⭐ La nascita: la stessa decisione del verbo

All'inserimento il guard legge l'ambiente vero dell'installazione e chiede alla regola
[fn_dati_di_sviluppo_ammessi_su_valori](/dbzero/dbops/funzioni/fn_dati_di_sviluppo_ammessi_su_valori)
se i dati di sviluppo sono ammessi. È la stessa regola che legge il verbo dei dati di
sviluppo prima di partire, e per questo il rifiuto ha lo stesso codice: è la stessa
decisione, presa in due punti di passaggio.

Un'installazione che non ha dichiarato l'ambiente non arriva alla regola: la ferma prima il
lettore dell'ambiente.

---

### ⛔ Dopo la nascita: niente modifiche, e via solo con la radice

Modifica di una riga e svuotamento di tutta la tabella sono sempre rifiutati. La cancellazione
di una riga è rifiutata finché la sua **radice** c'è: la credenziale di Django per
un'etichetta di credenziale, il soggetto per un'etichetta di soggetto. Togliere l'etichetta di
una radice viva la nasconderebbe al presidio che cerca i dati di prova in produzione.

Quando la radice non c'è più la cancellazione passa: è il caso della cascata della chiave
esterna, che toglie l'etichetta di una credenziale eliminata. Se la tabella delle credenziali
non si può leggere (un database prima dell'installazione di Django) la radice vale viva, e il
rifiuto resta. Per i soggetti la regola è la stessa, ma un soggetto con un'etichetta non si
cancella comunque: il suo legame non è in cascata.

Lo svuotamento non attraversa i trigger di riga: per questo su ogni tabella c'è un secondo
trigger, di istruzione, che chiama la stessa funzione.

⚠️ Il proprietario delle tabelle può disattivare il trigger: contro chi ha quel potere la
difesa sono i ruoli, non il guard. Ciò che sfugge così lo vede il presidio.

---

### Codici errore

* `E_DATI_DI_SVILUPPO_IN_PRODUZIONE` — un'etichetta nuova su un'installazione che non è di
  sviluppo.
* `E_CONFIG_MANCANTE` — un'etichetta nuova su un'installazione senza ambiente dichiarato; lo
  solleva il lettore dell'ambiente.
* `E_ETICHETTA_DI_PROVA_IMMUTABILE` — modifica, svuotamento, o cancellazione con la radice
  ancora viva, su una delle due tabelle.

---

### Test

* `db/pgtap/dbops/test-etichette-di-prova-v1.sql` — in sviluppo un'etichetta di soggetto e
  una di credenziale nascono, poi modifica, cancellazione e svuotamento sono rifiutati; in
  produzione (costruita) un'etichetta nuova è rifiutata; con l'ambiente non dichiarato
  (costruito) il rifiuto è quello del lettore.
* `db/pgtap/dbops/test-credenziale-di-prova-fk-v1.sql` — cancellare la credenziale toglie la sua
  etichetta; la cancellazione diretta, con la radice viva, resta rifiutata, anche per un soggetto.

---

### Note di migrazione

* 2026-10-18 — nasce con le due tabelle delle etichette (`brief-db-processi-accensione-per-ambiente`, R-4).
* 2026-11-09 — la cancellazione è ammessa quando la radice non c'è più (`20261110-56`,
  `brief-db-revisione-dbops`, giro 11): serve alla cascata della chiave esterna delle credenziali.

---

{% include-markdown "signature-core.md" %}
