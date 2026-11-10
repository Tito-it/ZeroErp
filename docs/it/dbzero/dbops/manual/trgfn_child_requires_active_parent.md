## 📘 Documentazione Concettuale – Trigger function `dbops.trgfn_child_requires_active_parent`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols) — il nome della colonna attivo del figlio, quando non è `attivo`
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — il motore che monta questo trigger, il *require*
> * [dbops.fn_trigger_attivo_argomenti](/dbzero/dbops/funzioni/fn_trigger_attivo_argomenti) — la grammatica degli argomenti
> * [dbops.fn_trigger_padre_stato](/dbzero/dbops/funzioni/fn_trigger_padre_stato) — legge il padre, fuori dalla row level security
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — il gemello sul padre, il *block*
> * [dbops.trgfn_child_requires_non_obsolete_parent](/dbzero/dbops/funzioni/trgfn_child_requires_non_obsolete_parent) — la stessa forma sull'asse `obsoleto_dal`
> * [dbops.fn_trigger_attivo_orfani](/dbzero/dbops/funzioni/fn_trigger_attivo_orfani) — riconosce i require che nominano oggetti spariti
> * [script.fn_bersaglio_di_riga](/dbzero/script/funzioni/fn_bersaglio_di_riga) — il bersaglio del padre, dal catalogo dei tipi
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, la regola ATTIVO

---

### 🎯 Scopo Principale

Il *require* della regola ATTIVO: impedisce a un figlio **attivo** di puntare a un padre **spento**.
Scatta sul figlio all'inserimento e quando cambia la colonna FK (o la colonna attivo del figlio).

Lo monta `dbops.fn_run_automations_attivo` come constraint trigger differito al commit, così un
padre e i suoi figli si possono scrivere in più istruzioni della stessa transazione. Si monta
anche a mano, con la stessa grammatica, dove serve un controllo immediato o su chiavi polimorfe
che non hanno una FK.

---

### Gli argomenti del trigger

Cinque, **tutti obbligatori**, nella grammatica di `dbops.fn_trigger_attivo_argomenti`: schema e
tabella del padre, nome della colonna attivo del **padre**, colonna FK del figlio, colonna del
padre referenziata dalla FK. La colonna referenziata può essere una `UNIQUE` diversa dalla chiave
primaria. Non ci sono ripieghi: un montaggio con un argomento mancante o vuoto si rifiuta.

---

### Quando il controllo si fa e quando no

* Se il figlio ha la colonna attivo (col nome di `automation_overrides_cols`, se c'è) e la riga
  **non** è attiva, nessun controllo: un figlio spento può puntare a qualunque padre. Se il figlio
  non ha la colonna, il controllo vale per ogni riga.
* Se la colonna FK è vuota, nessun controllo: la FK è facoltativa.
* Altrimenti il padre si legge per la colonna referenziata, e la scrittura si rifiuta se il padre
  non c'è o se la sua colonna attivo non è vera.

---

### ⭐ Il padre si legge con gli occhi del proprietario

La lettura la fa `dbops.fn_trigger_padre_stato`, fuori dalla row level security: lo stato di un
padre non dipende da chi guarda. Conta soprattutto perché il trigger è differito: scatta al
commit, col contesto di chi chiude la transazione, che può non vedere un padre scritto da un
altro. La lettura riceve il trigger, non i nomi delle tabelle, e legge gli argomenti dal suo
montaggio.

---

### Codici errore

Per l'operatore, con la colonna FK nel campo e una frase che **non nomina tabelle**:

* `E_ATTIVO_PADRE_NON_ATTIVO` (conflitto di stato) — il padre esiste ed è spento. Porta anche il
  **bersaglio** del padre (tipo e id), quando il catalogo dei tipi ne dichiara la tabella;
* `E_PADRE_INESISTENTE` (dato errato) — nessuna riga del padre ha quella chiave. Con una FK la
  parola l'ha prima il vincolo; succede sulle chiavi polimorfe. Niente bersaglio: punterebbe a una
  riga che non c'è.

Padre, figlia, colonna referenziata e valore stanno nel contesto del registro errori, per chi
ripara il dato.

Per chi monta il trigger:

* `E_TRIGGER_ARGOMENTI_INVALIDI` — argomenti fuori grammatica, una colonna FK che la figlia non
  ha, una tabella o una colonna del padre che non esiste.

`E_ATTIVO_REQUIRE` non lo solleva più questa funzione: è il codice del generatore quando non
riesce a montare il trigger.

---

### ⭐ Quale riga, senza nominare la tabella

Per l'operatore un nome come `anagrafiche.risorse_umane` non vuol dire niente, e su un portale o
uno shop è un'informazione sulla struttura del database che non deve uscire. La frase quindi dice
solo che cosa è successo; **quale** riga lo dice il bersaglio, che il frontend mostra col nome
tradotto del tipo e, dove può, con un pulsante che la apre.

Il bersaglio lo compone `script.fn_bersaglio_di_riga`, solo sul ramo del rifiuto. Un padre senza
tipo (un catalogo come `config.iva`) non ne ha: la frase basta da sola, e il campo evidenziato
dice già quale scelta correggere.

---

### Test

* `db/pgtap/dbops/test-bersaglio-guard-attivo-v1.sql` — la frase del catalogo e il bersaglio del
  padre, con e senza un tipo; il padre assente senza bersaglio.
* `db/pgtap/dbops/test-guard-attivo-grammatica-e-codici-v1.sql` — su tabelle temporanee: il padre
  spento, la frase, il figlio spento che passa, il padre assente su una chiave polimorfa, i
  montaggi sbagliati.
* `db/pgtap/dbops/test-guard-attivo-occhi-del-proprietario-v1.sql` — come applicazione: il require
  differito si chiude nei panni di un operatore che non vede il padre, e passa; la lettura rifiuta
  un trigger costruito dall'applicazione su una tabella sua.
* `db/pgtap/dbops/test-automazione-attivo-eccezioni-v1.sql` — il require non nasce su una FK
  dichiarata eccezione, e c'è sulle altre FK della stessa figlia.
* `db/pgtap/catalogo/test-articoli-approvvigionamento-v1.sql` — test 10, la frase sul catalogo
  vero.

---

### Note di migrazione

* 2026-11-07 — il rifiuto per l'operatore ha codici suoi (prima era `E_ATTIVO_REQUIRE`, tecnico,
  con un messaggio sulla generazione della regola); il padre assente si riconosce (prima rispondeva
  «non attivo»); il padre si legge fuori dalla row level security (prima, sotto quella di chi
  chiudeva la transazione); il quinto argomento è obbligatorio (prima il ripiego su `id` scriveva
  nel registro errori a ogni scatto).
* 2026-11-10 — le due frasi non nominano più tabelle (prima: padre, chiave, valore e figlia come
  `schema.tabella`); il padre spento porta il bersaglio.

---

{% include-markdown "signature-core.md" %}
