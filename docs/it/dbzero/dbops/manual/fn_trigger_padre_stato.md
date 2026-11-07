## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_padre_stato`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — la chiama per l'attivo del padre
> * [dbops.trgfn_child_requires_non_obsolete_parent](/dbzero/dbops/funzioni/trgfn_child_requires_non_obsolete_parent) — la chiama per l'`obsoleto_dal` del catalogo
> * [dbops.fn_trigger_attivo_argomenti](/dbzero/dbops/funzioni/fn_trigger_attivo_argomenti) — la grammatica con cui legge il montaggio
> * [dbops.fn_trigger_figlie_presenti](/dbzero/dbops/funzioni/fn_trigger_figlie_presenti) — la gemella per il block
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, la regola ATTIVO

---

### 🎯 Scopo Principale

Legge lo **stato del padre** per un trigger require: la colonna che il montaggio dichiara (l'attivo,
oppure `obsoleto_dal`) e se la riga padre c'è. La legge **fuori dalla row level security**, con gli
occhi del proprietario del database.

---

### ⭐ Perché fuori dalla row level security

Lo stato di un padre non dipende da chi guarda: un listino attivo è attivo anche per chi non lo
vede. Una funzione trigger gira con l'identità di chi scrive, e il require generato è per di più
**differito**: scatta al commit, col contesto di chi chiude la transazione. Letto sotto la sua row
level security, un padre attivo ma fuori dal suo perimetro risultava «non attivo».

---

### Che cosa riceve e che cosa restituisce

Riceve il **trigger** (la sua tabella e il suo nome) e la chiave del padre come la scrive la figlia.
Non riceve nomi di tabelle o di colonne: legge gli argomenti dal montaggio, con
`dbops.fn_trigger_attivo_argomenti`.

Restituisce una riga:

* **configurato** — falso se il montaggio nomina una tabella o una colonna che non c'è, con il
  motivo in **dettaglio**: il codice lo sceglie il trigger;
* **trovato** — se una riga padre ha quella chiave;
* **valore** — la colonna di stato, in JSON: un booleano o una data in forma ISO, che si rileggono
  senza dipendere dal formato delle date della sessione.

---

### ⛔ Risponde solo per i montaggi delle migrazioni

Una funzione che legge fuori dalla row level security con nomi presi da fuori leggerebbe qualunque
colonna di qualunque tabella per chiunque la chiami. Per questo:

* la tabella del trigger dev'essere del proprietario di questa funzione: un trigger lo monta solo
  chi possiede la tabella, quindi gli argomenti li ha scritti una migrazione. Un trigger costruito
  dall'applicazione su una sua tabella temporanea si rifiuta;
* il trigger dev'essere un require ATTIVO;
* risponde la sola colonna di stato dichiarata, e se la riga esiste.

Se il padre è sotto row level security **anche** per il proprietario (una sicurezza forzata, o un
padre di un altro ruolo), la lettura sarebbe parziale: invece di rispondere «non trovato» si
ferma. Tutti questi rifiuti escono con `E_DBOPS_CHIAMATA_NON_VALIDA`.

---

### ⚠️ Dipende dal proprietario delle tabelle

Attraversa la row level security perché il suo proprietario è anche quello delle tabelle, e la
sicurezza per riga è abilitata e non forzata. È una condizione del modello, presidiata da un pgTAP:
ogni trigger della famiglia sta su tabelle di quel proprietario, senza forzatura, da tutti e due i
lati.

---

### Test

* `db/pgtap/dbops/test-guard-attivo-occhi-del-proprietario-v1.sql` — come applicazione: il require
  differito chiuso da chi non vede il padre passa; un trigger dell'applicazione su una sua tabella
  temporanea non legge niente; il presidio sui proprietari.
* `db/pgtap/dbops/test-guard-attivo-grammatica-e-codici-v1.sql` — il padre assente, e il rifiuto
  di un trigger che non è un require.

---

{% include-markdown "signature-core.md" %}
