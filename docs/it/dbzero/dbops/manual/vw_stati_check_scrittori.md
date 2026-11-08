## 📘 Documentazione Concettuale – Vista `dbops.vw_stati_check_scrittori`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.stati_check_dichiarazioni](/dbzero/dbops/tabelle/stati_check_dichiarazioni) — il registro che la misura legge
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, dove la vista è un inventario
>
> Approfondimento viste:
>
> * [dbops.vw_stati_check_da_sanare](/dbzero/dbops/views/vw_stati_check_da_sanare) — la lista di lavoro ricavata da qui
>
> Approfondimento funzioni:
>
> * [dbops.fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione) — il corpo senza commenti degli scrittori, anche delle `BEGIN ATOMIC`
>
> Guide:
>
> * [Presidi e registri del debito — uno stato mai scritto](/guide/presidi-e-registri-del-debito#36-uno-stato-previsto-dal-modello-e-mai-scritto) — il presidio per intero
> * [Linee guida SQL — funzioni `BEGIN ATOMIC`](/linee-guida-sql#5c-funzioni-sql-begin-atomic-perche-come-si-cambiano-come-si-cercano) — perché il sorgente testuale non basta

---

### 🎯 Scopo Principale

La misura del presidio degli stati mai scritti. Risponde a una domanda sola: **c'è uno stato che il
database ammette e che nessuno scrive mai?** Ogni riga è un valore ammesso da una colonna di stato,
con accanto chi lo scrive e se qualcuno se n'era già accorto.

---

### ⭐ Perché serviva

Il difetto non fa rumore. Un vincolo che ammette un valore d'errore promette che il sistema sa dire
«è andata male». Se nessuno scrive quel valore, il sistema non dice niente: le corse chiudono
«completate» con un documento rifiutato, e nessun errore, nessuna pagina, nessun test diventa rosso
da solo. È successo davvero, per mesi, sugli esiti dei lotti di fatturazione — e il valore era
perfino nominato nel riepilogo che lo contava.

---

### ⛔ Il perimetro non è un elenco

La vista ricava il perimetro dai **vincoli del database**: ogni colonna di stato (il nome comincia
con `stato`, oppure è `status`, `esito` o `severity`) che porta un vincolo di appartenenza a un
elenco chiuso. Una tabella nuova con un vocabolario chiuso compare da sola.

⚠️ Il confine fra uno **stato** e una **classificazione** (il tipo di un lotto, un canale, una natura)
è il nome della colonna, ed è una scelta scritta: un valore mai usato in una classificazione è una
configurazione non ancora esercitata, non un fallimento muto.

---

### Chi conta come scrittore

| Scrittore | Come si vede |
| --- | --- |
| il **valore predefinito** della colonna | lo scrive ogni inserimento che non lo nomina, e rende raggiungibile **solo** quel valore |
| una **funzione che scrive la tabella**, PL/pgSQL o SQL | il valore compare nel suo corpo come letterale |
| una funzione che **chiama** uno scrittore | il valore compare dentro la chiamata: è il caso delle funzioni che ricevono lo stato come parametro |

Il corpo di ogni funzione si legge da [fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione):
senza commenti, con i letterali intatti, e anche per le funzioni SQL scritte con `BEGIN ATOMIC`, il
cui sorgente testuale è vuoto. Uno scrittore così conta come gli altri, e un letterale che contiene un
doppio trattino sulla riga dello scrittore non gli taglia il valore.

`scrittori_nomi` dice quali funzioni portano il valore; `scrittori_tabella` elenca le funzioni che
scrivono quella tabella, ed è il punto da cui partire per cercare dal lato del programma.

⛔ **Le fixture dei test non contano**, né quando scrivono né quando chiamano uno scrittore: le
funzioni `fn_pgtap_…` di `dbops` e `script` collaudano il sistema, non lo sono. Se contassero, una
fixture che scrive un valore d'errore farebbe risultare «scritto» proprio lo stato che il sistema
non raggiunge mai. È successo: una fixture che attivava le versioni di listino aveva fatto risultare
estinta una dichiarazione che diceva il vero.

---

### ⚠️ I limiti del criterio

Il criterio è **testuale**, e i suoi limiti sono dichiarati nel test:

* **nominare non è scrivere**: una funzione che nomina il valore senza scrivere la tabella non lo
  rende scritto;
* **a tre salti il letterale non si segue più**: un valore che passa per tre funzioni resta non
  dichiarato;
* **il programma non si vede**: per quei valori il database legge una dichiarazione, che il backend
  verifica dal suo lato;
* **un valore copiato da un'altra colonna non si vede**.

Che il valore venga scritto **nel momento giusto** la vista non lo dice: dice che esiste chi lo
scrive. Che la macchina degli stati sia corretta lo provano i test di dominio.

---

### Le sei risposte

| `esito` | Che cosa vuol dire | Che cosa fare |
| --- | --- | --- |
| `SCRITTO` | almeno una funzione lo scrive, direttamente o passandolo | niente |
| `SCRITTO_DA_DEFAULT` | è il valore predefinito della colonna | niente, ma gli **altri** valori della colonna vanno guardati |
| `DICHIARATO_APPLICAZIONE` | lo scrive il programma; il test del backend lo verifica | niente, finché quel test è verde |
| `ESENTE` | il criterio non lo vede, e qualcuno ha scritto perché | niente, per ora: è un lavoro con un nome e una data |
| `NON_DICHIARATO` | nessuno lo scrive e nessuno l'ha guardato | **allarme**: o si scrive chi lo scrive, o si dichiara con la ragione |
| `DEBITO_ESTINTO` | il registro lo nomina, ma il valore è scritto o non esiste più | togliere la riga dal registro |

⛔ **La regola non è «la vista è vuota»**: la vista elenca anche i valori sani, di proposito, perché
senza sapere come un valore risulta scritto non si capisce perché un altro no. La regola è
**niente `NON_DICHIARATO` e niente `DEBITO_ESTINTO`**, ed è ciò che proietta
`dbops.vw_stati_check_da_sanare`.

---

### Test

* `db/pgtap/dbops/test-stati-check-scrittori-v1.sql` — il perimetro non si restringe di nascosto; i
  casi costruiti uno per uno (valore nuovo non dichiarato, nominare non è scrivere, il default, il
  secondo salto, il limite del terzo, il registro nei due versi); uno scrittore `BEGIN ATOMIC` rende
  `SCRITTO` il suo valore (test 16); un letterale con un doppio trattino sulla riga dello scrittore
  non gli taglia il valore (test 17).

---

### Note di migrazione

* 2026-09-21 — nasce col presidio degli stati mai scritti (`brief-db-presidio-stati-mai-scritti`).
  Il primo conteggio trovava diciotto colonne, il criterio definitivo trentadue: PostgreSQL stampa lo
  stesso vincolo in due forme (colonna di testo e colonna a lunghezza variabile), e la prima ricerca
  ne vedeva una sola.
* 2026-09-22 — stessa misura, estratta una volta invece che provata per coppia: risultato identico,
  costo dimezzato.
* 2026-09-23 — le fixture pgTAP escono dal conto (`brief-db-fixture-che-costruiscono-giro-2`).
* 2026-11-04 — il corpo si legge da `fn_corpo_funzione` (D14 e D15 di `brief-db-revisione-dbops`):
  prima la vista guardava PL/pgSQL e SQL ma leggeva il sorgente testuale, vuoto per le
  `BEGIN ATOMIC`. Un valore scritto solo da una di loro usciva `NON_DICHIARATO`, e una riga `ESENTE`
  su quel valore non diventava mai `DEBITO_ESTINTO`.

---

{% include-markdown "signature-core.md" %}
