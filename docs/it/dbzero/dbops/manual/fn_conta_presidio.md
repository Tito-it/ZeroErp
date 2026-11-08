## 📘 Documentazione Concettuale – Funzione `dbops.fn_conta_presidio`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo da cui il conteggio legge tutto
>
> Approfondimento funzioni:
>
> * [dbops.fn_conta_presidio_per_variante](/dbzero/dbops/funzioni/fn_conta_presidio_per_variante) — il conteggio per causa, di cui questa è la somma, e la sede della regola
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — il meccanismo dei presidi

---

### 🎯 Scopo Principale

Dice quante righe di una vista di presidio dichiarata in `dbops.presidi` chiedono un intervento:
è la somma dei gruppi di
[dbops.fn_conta_presidio_per_variante](/dbzero/dbops/funzioni/fn_conta_presidio_per_variante).
Torna un numero, mai le righe.

---

### ⭐ Una somma, non una seconda copia

Il lavoro vero — leggere il catalogo, rifiutare una vista sconosciuta, applicare lo stato atteso,
attraversare la row level security — sta nella funzione per causa, e solo lì. Questa somma i suoi
gruppi: così il conteggio intero e quello per causa non possono divergere, non perché qualcuno si
ricordi di tenerli allineati, ma perché la regola è scritta una volta sola.

Per lo stesso motivo questa funzione è `SECURITY INVOKER`: non legge niente da sé. Il permesso di
contare oltre la row level security lo porta la sede, che gira come il proprietario.

Un presidio con la colonna della causa e nessuna riga da guardare non ha gruppi: la somma di
niente vale zero, non vuoto.

---

### 🔴 Perché il conteggio passa da qui: uno zero può essere una cecità

Alcune viste di presidio attraversano tabelle in row level security, o funzioni che vedono solo
ciò che possiede chi le chiama. Lette da un comando lanciato da un timer, senza un utente in
sessione, tornerebbero **zero righe** — e su una vista che deve restare vuota «zero righe» e «non
ho potuto vedere» si scrivono nello stesso modo. Il digest riferirebbe «tutto a posto» proprio
perché è cieco.

Il conteggio passa da qui per **tutte** le viste del catalogo, non solo per quelle protette: così
l'allarme è onesto ovunque, e chi chiama non deve scegliere.

Le due regole che lo rendono sicuro le applica la sede:

* **torna un numero, mai le righe**: attraversa i perimetri per dire *quanti*, non *quali*. Il
  dettaglio lo guarda una persona con il suo perimetro;
* **conta solo ciò che è a catalogo**, attivo e non ritirato, e il resto lo **rifiuta**: senza
  questo limite sarebbe una porta per contare qualunque relazione del database aggirando la row
  level security. E rifiuta, non torna zero: uno zero sarebbe indistinguibile da una vista sana.

L'alternativa era un ruolo tecnico che scavalca i filtri: avrebbe letto tutto, righe comprese, e
sarebbe stato un debito nuovo fra i processi che aggirano la row level security.

---

### Che cosa conta, esattamente

* **senza colonna di stato** nel catalogo → la vista intera: ogni riga è un allarme;
* **con una colonna di stato** → le righe con uno stato **diverso** da quello atteso. Si conta
  «diverso dall'atteso» e non «uguale a uno degli allarmi», così uno stato nuovo cade
  nell'allarme e non nel silenzio; e un valore assente conta come «non atteso», non esce dal
  conteggio.

⚠️ La colonna `perimetro` del catalogo dice un'**altra** cosa: se chi legge può anche *elencare*
le righe, oltre a contarle.

---

### Codici errore

* `E_PRESIDIO_NON_A_CATALOGO` — la vista chiesta non è in `dbops.presidi`, o è spenta o ritirata,
  o il nome è vuoto. Lo solleva la sede e passa di qui.

---

### Test

* `db/pgtap/dbops/test-catalogo-presidi-v1.sql` — rifiuto di una vista non a catalogo, vista
  intera senza colonna di stato, «diverso dall'atteso» con la colonna.
* `db/pgtap/dbops/test-conta-presidio-per-variante-v1.sql` — la somma è quella dei gruppi, a zero e
  non vuota quando non ci sono gruppi; questa funzione non contiene più il filtro e non è
  `SECURITY DEFINER`; `search_path` pinnato.
* `db/pgtap/dbops/test-riferimenti-morti-v1.sql` — il conteggio della lista di lavoro dei
  riferimenti morti fatto da qui concorda con la misura diretta.

---

### Note di migrazione

* 2026-09-10 — nasce `SECURITY DEFINER` con `brief-db-un-destinatario-per-i-presidi` §4.1, con
  dentro il perimetro e il filtro.
* 2026-10-10 — diventa la somma di `fn_conta_presidio_per_variante` e passa a `SECURITY INVOKER`
  (`brief-db-presidio-processi-testo-per-causa` §6.2).

---

{% include-markdown "signature-core.md" %}
