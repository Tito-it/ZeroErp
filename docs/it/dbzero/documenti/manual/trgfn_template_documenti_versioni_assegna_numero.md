## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_template_documenti_versioni_assegna_numero`

> **Ultimo aggiornamento**: 17 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la tabella delle versioni numerate
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — il lucchetto che tiene fermo il numero dopo la nascita
>
> Approfondimento funzioni:
>
> * [documenti.fn_crea_bozza_da_versione](/dbzero/documenti/funzioni/fn_crea_bozza_da_versione) — la copia, che riceve il numero da qui
> * [documenti.trgfn_template_documenti_versioni_protect_pubblicata](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_protect_pubblicata) — il guard dello stato, che cita il numero
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — il riconoscimento del proprietario della tabella
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — versioni e personalizzazione

---

### 🎯 Scopo Principale

Dà il **numero a una versione nuova** di un modello: il successivo all'ultimo del modello, partendo
da 1. È la sede unica della numerazione: ci passano la versione scritta da zero e la copia di una
versione esistente.

È montata `BEFORE INSERT` per riga su `documenti.template_documenti_versioni`, in fase `a04`.

---

### Chi sceglie il numero

Il numero lo sceglie il database, non chi scrive. Un numero mandato dall'applicazione si sostituisce
con quello giusto: dire «questa è la versione 7» quando il modello ne ha tre non ha senso, e due
strade che numerano da sé finiscono per dare due risposte allo stesso caso.

Fa eccezione il **proprietario della tabella**, cioè il seed e i changeSet che costruiscono i modelli
standard: se scrive un numero, lo tiene. È così che nasce uno standard con le sue versioni, come per
lo stato nel [guard dello stato](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_protect_pubblicata).
Senza numero, anche il proprietario riceve il successivo.

Dopo la nascita il numero **non cambia**, in nessuno stato: lo ferma il lucchetto di colonna
generato da [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns), con
`E_CODICE_NON_MODIFICABILE`. Su una versione fuori bozza parla prima il guard dello stato.

---

### Due nascite nello stesso momento

Due versioni dello stesso modello che nascono insieme, per esempio due copie lanciate da due
persone, non prendono lo stesso numero. Prima di leggere l'ultimo numero la funzione prende un
**lock di transazione sul modello**: la seconda nascita aspetta che la prima finisca, poi legge
l'ultimo numero che la prima ha scritto e prende il successivo. Non c'è un errore da gestire né un
«riprova»: c'è una breve attesa.

Il lock vale per un modello solo: le nascite in modelli diversi non si aspettano.

⚠️ L'attesa funziona al livello di isolamento con cui lavora l'applicazione (`READ COMMITTED`). In
una transazione `REPEATABLE READ` la seconda nascita non vede la riga della prima anche dopo
l'attesa: lì il vincolo di unicità di (modello, numero) rifiuta la scrittura invece di sovrascrivere.
Il vincolo resta come difesa a valle.

Un `INSERT` di più righe nello stesso modello le numera in fila: ogni riga vede quelle già inserite
dalla stessa istruzione.

---

### L'ordine dei trigger

La fase è `a04`, prima di tutti gli altri trigger della tabella. I due rifiuti che parlano per primi
(`a05`), il guard di sola lettura dello standard e il guard dello stato, citano il numero della
versione nella frase che l'operatore legge: devono trovarlo già assegnato. Il lock lo prende anche
una scrittura che uno di quei guard poi rifiuta; costa un'attesa breve, non un esito diverso.

---

### Codici errore

La funzione non solleva errori. Il numero che cambia dopo la nascita lo rifiuta il lucchetto di
colonna (`E_CODICE_NON_MODIFICABILE`).

---

### Test

* `db/pgtap/documenti/test-documenti-numero-versione-v1.sql` — il montaggio e la fase; la prima
  versione di un modello vuoto è 1, la successiva 2; un numero scelto dall'applicazione si
  sostituisce; un `INSERT` di due righe le numera in fila; la nascita tiene il lock del modello fino
  alla fine della transazione; la copia riceve il successivo, anche in un modello vuoto; il numero di
  una bozza non cambia. Che due nascite contemporanee si mettano in fila non si prova in una sessione
  sola: il test asserisce che il lock c'è e che il corpo lo prende prima di leggere.
* La strada del proprietario la percorrono i pgTAP che girano da owner e costruiscono standard col
  loro numero: `test-documenti-template-standard-v1.sql`, `-personalizza-v1.sql`.

---

### Note di migrazione

* 2026-11-17 — nasce. Fino ad allora il numero di una versione nuova lo calcolava il servizio del
  backend, e quello di una copia la funzione della copia, che traduceva la gara sul numero in un
  codice suo («ripeti la copia»). Le nascite si mettono in fila, e quel codice è ritirato.

---

{% include-markdown "signature-core.md" %}
