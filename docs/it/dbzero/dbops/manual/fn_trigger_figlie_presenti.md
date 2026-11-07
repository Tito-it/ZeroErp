## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_figlie_presenti`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols) — il nome della colonna attivo della figlia, quando non è `attivo`
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — il block che la chiama
> * [dbops.fn_trigger_attivo_argomenti](/dbzero/dbops/funzioni/fn_trigger_attivo_argomenti) — la grammatica con cui legge il montaggio
> * [dbops.fn_trigger_padre_stato](/dbzero/dbops/funzioni/fn_trigger_padre_stato) — la gemella per i require
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, la regola ATTIVO

---

### 🎯 Scopo Principale

Dice se il padre di un trigger block ha ancora **righe figlie che lo usano**: attive, se la figlia
ha la colonna attivo; qualunque, se non ce l'ha. Le cerca **fuori dalla row level security**, con
gli occhi del proprietario del database.

---

### ⭐ Perché fuori dalla row level security

Che un padre sia ancora usato non dipende da chi guarda. Cercate sotto la row level security di chi
spegne il padre, le figlie di un'altra azienda non contavano: un catalogo visibile a tutti si
spegneva con figli attivi che chi lo spegneva non vedeva.

---

### Che cosa riceve e che cosa restituisce

Riceve il **trigger** (la sua tabella e il suo nome) e il valore della colonna referenziata del
padre. Non riceve nomi di tabelle o di colonne: legge gli argomenti dal montaggio, con
`dbops.fn_trigger_attivo_argomenti`.

Restituisce una riga:

* **configurato** — falso se il montaggio nomina una figlia o una colonna FK che non c'è, con il
  motivo in **dettaglio**;
* **colonna attivo della figlia** — quella guardata (col nome di `automation_overrides_cols`, se
  c'è), vuota se la figlia non ce l'ha: il block ne ricava quale dei due codici sollevare;
* **presenti** — se ci sono figlie che tengono acceso il padre.

La colonna attivo della figlia si cerca per nome nel catalogo, non in `information_schema`, che
mostra solo le colonne su cui chi chiede ha un privilegio.

---

### ⛔ Risponde solo per i montaggi delle migrazioni

Stessa difesa di `dbops.fn_trigger_padre_stato`: la tabella del trigger dev'essere del proprietario
di questa funzione, il trigger dev'essere un block ATTIVO, e una figlia sotto row level security
anche per il proprietario ferma la ricerca invece di rispondere «nessuna». Tutti questi rifiuti
escono con `E_DBOPS_CHIAMATA_NON_VALIDA`. Senza questa difesa la funzione direbbe a chiunque se
esistono righe con un valore qualsiasi in una colonna qualsiasi.

---

### Test

* `db/pgtap/dbops/test-guard-attivo-occhi-del-proprietario-v1.sql` — come applicazione: una
  tipologia di listino usata dal listino di un'altra azienda non si spegne; un block
  dell'applicazione su una sua tabella temporanea non cerca niente; il presidio sui proprietari.
* `db/pgtap/dbops/test-trigger-attivo-orfani-v1.sql` — dopo il ritiro degli orfani il padre si
  spegne.

---

{% include-markdown "signature-core.md" %}
