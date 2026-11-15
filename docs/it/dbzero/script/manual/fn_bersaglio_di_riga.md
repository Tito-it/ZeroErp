## 📘 Documentazione Concettuale – Funzione `script.fn_bersaglio_di_riga`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_entita](/dbzero/config/tabelle/tipi_entita) — il catalogo dei tipi, e la colonna `tabella`
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — la tabella e la pagina di un tipo sorgente
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/manual/trgfn_child_requires_active_parent) — la chiama sul rifiuto «padre non attivo»
> * [dbops.trgfn_child_requires_non_obsolete_parent](/dbzero/dbops/manual/trgfn_child_requires_non_obsolete_parent) — la chiama sul rifiuto «voce ritirata»
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — porta il bersaglio nel canale dell'eccezione
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, la regola ATTIVO

---

### 🎯 Scopo Principale

Dato un errore che riguarda una riga di una tabella, dice **quale cosa** è quella riga, nella forma
che il frontend sa leggere: un **bersaglio**, cioè il tipo (un codice di `config.tipi_entita`) e
l'id. Il frontend lo mostra col nome tradotto del tipo e, dove può, con un pulsante che apre la
riga. Così la frase dell'errore non deve nominare la tabella, che all'operatore non dice niente.

Riceve lo schema e il nome della tabella, la colonna con cui la riga si raggiunge e il suo valore.
Restituisce il bersaglio, oppure niente.

---

### Quando c'è un bersaglio

Il tipo lo dichiara il catalogo, non si indovina:

* per un tipo **non sorgente**, la colonna `config.tipi_entita.tabella` nomina la tabella;
* per un tipo **sorgente**, la tabella è la `target_table` della sorgente in `config.sorgenti`, e la
  sorgente deve avere una pagina (`apribile`): un tipo senza pagina darebbe un pulsante che non
  porta da nessuna parte.

Inoltre la colonna deve essere la **chiave** del tipo (`key_selector`, `id` o `uid`), il valore non
deve essere vuoto, e il tipo non deve essere ritirato.

Se nessun tipo risponde, o ne risponde più di uno, non c'è bersaglio: un bersaglio incerto porta
l'operatore nel posto sbagliato, ed è peggio di nessun bersaglio. Un catalogo come `config.iva` non
ha un tipo, e il suo errore regge con la sola frase e il campo evidenziato.

---

### ⚠️ Il catalogo decide, una volta per tipo

La tabella di un tipo si scrive una sola volta, nel CSV di `config.tipi_entita` (o, per un tipo
sorgente, in quello di `config.sorgenti`), non in ogni trigger che potrebbe puntarla. Un tipo nuovo
che dichiara la sua tabella diventa bersaglio di tutti i rifiuti che la riguardano, senza toccare i
trigger.

Si dichiara solo per un tipo che il frontend apre col solo id. Oggi non la dichiarano, ad esempio,
le versioni di listino (la pagina chiede anche il listino) e le righe dei documenti.

---

### ⚠️ Gira con i privilegi del proprietario

I trigger che la chiamano girano come chi scrive la riga, che non sempre può leggere il catalogo
dei tipi. La funzione legge solo i due cataloghi, che non hanno righe riservate, ed è eseguibile da
tutti come gli altri aiutanti dei trigger: il bersaglio non deve mai togliere il rifiuto a chi
scrive.

---

### Test

* `db/pgtap/dbops/test-bersaglio-guard-attivo-v1.sql` — il catalogo (la tabella esiste e ha la
  chiave, nessuna tabella ha due sedi), il bersaglio di un articolo e di una fattura, nessun
  bersaglio per un catalogo senza tipo, per una colonna che non è la chiave, per una sorgente senza
  pagina; i rifiuti veri dei trigger ATTIVO, con e senza tipo.

---

### Note di migrazione

* 2026-11-10 — nasce, con la colonna `config.tipi_entita.tabella`, perché le frasi dei trigger
  ATTIVO smettano di nominare tabelle.

---

{% include-markdown "signature-core.md" %}
