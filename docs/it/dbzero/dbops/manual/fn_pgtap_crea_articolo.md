## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_articolo`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la riga che la fixture fa nascere
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — da dove viene l'unità di misura base
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/funzioni/trgfn_articoli_guard_struttura_se_usato) — perché la struttura si sceglie alla nascita
> * [dbops.fn_pgtap_crea_magazzino](/dbzero/dbops/funzioni/fn_pgtap_crea_magazzino) — il magazzino in cui l'articolo si movimenta
> * [dbops.fn_pgtap_listino_aggiungi_articoli](/dbzero/dbops/funzioni/fn_pgtap_listino_aggiungi_articoli) — l'articolo dentro un listino
> * [dbops.fn_pgtap_articolo_correggi_struttura](/dbzero/dbops/funzioni/fn_pgtap_articolo_correggi_struttura) — la correzione dopo l'uso, dalla porta del super admin
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: **un articolo costruito intero, con la struttura che il test sceglie** — gestito a
magazzino, per lotti, per matricola, composito, tipologia di listino, natura, causale d'onere — e
un'unità di misura base attiva.

Pescare un articolo dal catalogo darebbe un articolo qualunque: per esempio uno non gestito a
magazzino, cioè un `E_MAG_ARTICOLO_NON_GESTITO` che sembra un test rosso.

---

### ⭐ La struttura si sceglie alla nascita

Un articolo **usato** non cambia più struttura: il guard di struttura congela otto colonne —
composito, solo componente, natura di vendita, causale d'onere, tipologia di listino, gestito a
magazzino, a lotti, a matricola. La fixture le accetta tutte e le scrive alla nascita: chi le
vuole diverse dal default le passa qui, per nome.

⛔ **Non si corregge l'articolo dopo con un `UPDATE`.** Una correzione regge solo se arriva prima
che l'articolo venga usato; sbagliato l'ordine, il test diventa rosso con un
`E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE` che non nomina la fixture. Restano legittimi gli `UPDATE`
che sono **l'oggetto** del test (il guard stesso, un cambio di struttura su un articolo non
usato). Per cambiare la struttura di un articolo già usato c'è
`dbops.fn_pgtap_articolo_correggi_struttura`, che passa dal verbo del super admin.

---

### I default

* **Gestito a magazzino** sì, senza lotti né matricola, non composito: è l'articolo che serve a
  un test di magazzino.
* **Unità di misura base**: quella chiesta, se il test la sceglie (chi misura le conversioni deve
  sceglierla, perché le conversioni valgono solo fra unità della stessa tipologia); altrimenti la
  prima attiva del catalogo. La colonna è bloccata dopo la nascita: o si sceglie qui, o mai più.
  Un'unità chiesta che non esiste o è spenta ferma la fixture con un errore che nomina il
  parametro, invece di arrivare alla chiave esterna; un catalogo delle unità vuoto la ferma con un
  errore che dice di caricare il seed.
* **Natura di vendita**: non passata, resta quella di default della tabella; la fixture non la
  ricopia.
* **Combinazioni** (un onere su una natura di merce, una tipologia spenta): le giudicano i guard
  della tabella, la fixture non le ripete.

La descrizione dell'articolo è derivata dal codice; il codice lo dà il test, e deve essere
libero.

---

### Test

Non ha un test suo: la usano la gran parte dei file di magazzino e di vendita, e i test delle
altre fixture che costruiscono righe (per esempio
`db/pgtap/dbops/test-fn-pgtap-crea-commessa-attivita-v1.sql` e
`db/pgtap/dbops/test-fn-pgtap-crea-ddt-senza-ordine-v1.sql`).

---

### Note di migrazione

* 2026-09-18 — nasce con il motore del magazzino (`brief-db-magazzino-lotto-2-motore`).
* 2026-09-23 — l'unità di misura base si può scegliere.
* 2026-10-17 — tutte le colonne di struttura si scelgono alla nascita, quando il guard di
  struttura sugli articoli usati rende fragile la correzione con un `UPDATE` successivo.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
