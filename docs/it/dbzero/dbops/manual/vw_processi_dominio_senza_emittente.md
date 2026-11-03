## 📘 Documentazione Concettuale – Vista `dbops.vw_processi_dominio_senza_emittente`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — i processi dichiarati `DOMINIO`
> * [dbops.processi_bersagli](/dbzero/dbops/tabelle/processi_bersagli) — i bersagli e il percorso dichiarato, col flag del debito
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo in cui la vista è un presidio
>
> Approfondimento viste:
>
> * [dbops.vw_processi_dominio_senza_difesa](/dbzero/dbops/views/vw_processi_dominio_senza_difesa) — il livello 2: il percorso c'è, manca chi lo applica
> * [dbops.vw_liste_multi_emittente_non_certificate](/dbzero/dbops/views/vw_liste_multi_emittente_non_certificate) — un presidio dello stesso genere: la struttura c'è, non che il codice la usi
>
> Guide:
>
> * [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — i controlli che guardano il registro
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — debito dichiarato e allarme

---

### 🎯 Scopo Principale

Il livello 1 del presidio sui processi: i processi dichiarati `DOMINIO` che non possono rispettare
un perimetro emittente, perché non si sa arrivare dalla riga che scrivono al suo emittente.
L'invariante è «nessuna riga non dichiarata».

---

### ⭐ Prende l'omissione prima che il processo giri

A runtime l'omissione non è recuperabile: la row level security non può filtrare su una colonna che
non esiste, e il processo tocca righe di aziende diverse senza che nessun errore lo dica. Non è un
guasto rumoroso: è una fattura emessa per l'azienda sbagliata. La vista lo prende quando il
processo è ancora una riga di catalogo.

Guarda i processi `DOMINIO` attivi e non ritirati.

---

### Quattro motivi

| `motivo` | Che cosa manca |
| --- | --- |
| nessun bersaglio dichiarato | il processo non ha detto dove scrive |
| tabella inesistente | il bersaglio nomina una tabella che non c'è |
| percorso verso l'emittente non dichiarato | il bersaglio c'è, la via no |
| colonna del percorso inesistente | la via è dichiarata, ma la colonna **non esiste più** |

⚠️ **L'ultimo è il più pericoloso**: un percorso assente si vede leggendo la tabella, uno verso una
colonna cancellata sembra a posto. Per questo la vista non si accontenta del campo compilato e
chiede al catalogo del database se la colonna esiste davvero.

---

### ⭐ Debito dichiarato contro allarme

Ogni riga ha uno `stato`, letto da `dbops.processi_bersagli.debito_dichiarato`, e una `nota`, la
nota del bersaglio:

* `DEBITO_DICHIARATO` è un lavoro con un nome: chi l'ha scritto sa perché la riga è lì;
* `NON_DICHIARATO` è un allarme. Un processo senza nessun bersaglio è sempre un allarme: non c'è
  una riga su cui dichiarare il debito.

⛔ Dichiarare un debito non lo assolve: dice «sappiamo perché è qui», non «va bene che ci sia». Lo
stato sta nel dato perché il pannello dei presidi lo legga da lì, invece che da un elenco di
eccezioni scritto nel codice dell'interfaccia.

---

### ⚠️ Che cosa non prova

* Prova che la struttura c'è, non che il codice del processo la usi bene.
* Non prende il verso opposto: un processo che dovrebbe essere `DOMINIO` ma è dichiarato
  manutenzione resta un errore umano.
* Non dice se la tabella è protetta: quello è il livello 2.

---

### Come si svuota

Una riga in [processi_bersagli](/dbzero/dbops/tabelle/processi_bersagli) con la via e la colonna
giuste; oppure, se la tabella non ha davvero un percorso verso l'emittente, la colonna va aggiunta
alla tabella di dominio.

---

### Chi la guarda

Nel catalogo dei presidi è un presidio a stato, guardato ogni giorno, che tocca allo sviluppo. La
vista gira coi privilegi del proprietario.

---

### Test

* `db/pgtap/dbops/test-processi-registro.sql` — nessuna riga `NON_DICHIARATO`; un processo
  `DOMINIO` senza bersagli e un percorso su una colonna inesistente, costruiti, compaiono.
* `db/pgtap/dbops/test-presidi-debito-dichiarato.sql` — un bersaglio scoperto ma dichiarato si
  presenta come debito, uno nuovo e rotto come allarme; le due viste sorelle parlano la stessa
  lingua.

---

### Note di migrazione

* 2026-09-04 — nasce col registro dei processi automatici (`brief-db-processi-automatici-identita-e-perimetro`).
* 2026-09-05 — nascono `stato` e `nota` (`brief-db-processi-automatici-residui-be`, DB-2): prima
  la vista diceva «deve restare vuota» e il seed scriveva «riga attesa» sullo stesso bersaglio.

---

{% include-markdown "signature-core.md" %}
