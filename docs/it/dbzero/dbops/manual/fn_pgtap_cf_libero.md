## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_cf_libero`

> **Ultimo aggiornamento**: 28 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — dove il codice deve essere libero
>
> Approfondimento funzioni:
>
> * [script.fn_valida_codice_fiscale](/dbzero/script/funzioni/fn_valida_codice_fiscale) — il validatore di dominio che decide il carattere di controllo
> * [dbops.fn_pgtap_piva_libera](/dbzero/dbops/funzioni/fn_pgtap_piva_libera) — la gemella per la partita IVA
> * [dbops.fn_pgtap_crea_operatore_umano](/dbzero/dbops/funzioni/fn_pgtap_crea_operatore_umano) — la fixture che la usa per la persona fisica
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — perché gli identificativi non si scrivono a mano

---

### 🎯 Scopo Principale

Restituisce un **codice fiscale valido e non ancora usato** in `anagrafiche.soggetti`, pronto
per una fixture.

---

### ⭐ Valido e libero, per due ragioni diverse

*Valido* perché i guard di dominio verificano la forma del codice fiscale e rifiuterebbero
una stringa inventata. *Libero* perché l'identificativo fiscale di un soggetto è unico, e i
soggetti lasciati da altre corse non si possono cancellare: un codice scritto a mano nel test
sbatterebbe sull'unicità alla seconda corsa, con un errore che non c'entra con ciò che il
test verifica.

⚠️ È anche il motivo per cui non si scrivono codici fiscali a mano nei test: due file che
usassero la stessa costante si romperebbero a vicenda, e solo quando girano insieme.

---

### ⭐ Il carattere di controllo non si calcola: si cerca

La fixture non reimplementa l'algoritmo del codice fiscale. Varia due lettere di un corpo
fittizio (676 corpi) e, per ogni corpo, prova le 26 lettere finali chiedendo al validatore di
dominio quale accetta. La regola resta così una sola, quella di dominio: se cambia, la fixture
la segue senza modifiche.

⚠️ Non è un generatore di codici fiscali reali: il corpo è fittizio e serve solo a superare
validatore e unicità in un test. I candidati sono uno per corpo, 676 in tutto il database.

⚠️ Perché due lettere e non una: ogni persona fisica di fixture ne consuma uno, e ne consumano
anche i soggetti che restano sul database (i dati di sviluppo, quelli che un chiamante con
`COMMIT` lascia). Con una lettera sola i codici erano 26, e un test che costruiva più persone di
quelle rimaste si fermava nel setup con un errore che con la sua regola non c'entrava.

---

### ⚠️ Libero adesso, non libero per sempre

La fixture vede anche le righe non ancora confermate della transazione, ma un codice diventa
occupato solo quando il soggetto che lo usa è scritto. Due chiamate prima di quella scrittura,
per esempio nella stessa istruzione, rispondono lo **stesso** codice. Chi ne vuole due li
chiede uno alla volta, scrivendo il soggetto in mezzo. A differenza della gemella per la
partita IVA, qui non c'è una variante che salta i primi codici liberi.

---

### Codici errore

Nessun codice registrato: se non trova un codice libero la fixture solleva un'eccezione
senza codice.

---

### Test

Nessun pgTAP dedicato: la esercitano i test che costruiscono persone fisiche, a partire da
quelli che usano [fn_pgtap_crea_operatore_umano](/dbzero/dbops/funzioni/fn_pgtap_crea_operatore_umano).

---

### Note di migrazione

* 2026-08-18 — nasce con la bonifica della baseline pgTAP di vendite (`brief-db-bonifica-baseline-pgtap-vendite`).
* 2026-11-28 — il corpo varia su due lettere: i 26 codici di prima erano esauriti dai soggetti residui e dai SUPER_ADMIN di fixture.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
