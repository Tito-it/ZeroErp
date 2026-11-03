## 📘 Documentazione Concettuale – Trigger function `dbops.trgfn_child_requires_active_parent`

> **Ultimo aggiornamento**: 4 novembre 2026
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
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — il gemello sul padre, il *block*
> * [dbops.trgfn_child_requires_non_obsolete_parent](/dbzero/dbops/funzioni/trgfn_child_requires_non_obsolete_parent) — la stessa forma sull'asse `obsoleto_dal`
> * [dbops.fn_trigger_attivo_orfani](/dbzero/dbops/funzioni/fn_trigger_attivo_orfani) — riconosce i require che nominano oggetti spariti
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
anche a mano, con la stessa grammatica, su chiavi polimorfe che non hanno una FK.

---

### Gli argomenti del trigger

In ordine: schema e tabella del padre, nome della colonna attivo del **padre**, colonna FK del
figlio, colonna del padre referenziata dalla FK. La colonna referenziata può essere una `UNIQUE`
diversa dalla chiave primaria; se manca vale `id`, ed è una forma deprecata (vedi sotto). Il
generatore passa sempre tutti e cinque gli argomenti.

---

### Quando il controllo si fa e quando no

* Se il figlio ha la colonna attivo (col nome di `automation_overrides_cols`, se c'è) e la riga
  **non** è attiva, nessun controllo: un figlio spento può puntare a qualunque padre.
* Se la colonna FK è vuota, nessun controllo: la FK è facoltativa.
* Altrimenti il padre si legge per la colonna referenziata, e se la sua colonna attivo non è vera
  la scrittura si rifiuta.

Il valore della FK e della colonna attivo del figlio si leggono dalla riga nuova senza SQL
dinamico; il padre si legge con un'interrogazione dinamica, con il valore convertito al tipo della
colonna referenziata.

---

### ⚠️ Un padre che non si trova risponde «non attivo»

Il ramo «padre non trovato» non scatta mai: il controllo di esistenza dopo l'interrogazione
dinamica guarda un indicatore che quell'interrogazione non aggiorna. Un padre che non si trova
risponde quindi come un padre spento. Con una FK vera il caso non si presenta; si presenta sulle
chiavi polimorfe senza FK.

---

### ⚠️ Legge il padre con gli occhi di chi scrive

La funzione è `SECURITY INVOKER`: la lettura del padre passa dalla row level security di chi
chiude la transazione. Un padre attivo ma **fuori dal perimetro** di chi scrive non si vede, e la
scrittura si rifiuta come se il padre fosse spento. Poiché il trigger è differito, conta il
contesto attivo al momento della verifica, non quello in cui la riga è stata scritta.

---

### ⚠️ Il fallback deprecato scrive nel registro errori a ogni riga

Quando manca il quinto argomento la funzione scrive una riga in `dbops.error_log` (codice
`E_ATTIVO_REQUIRE`, senza sollevare) **a ogni scatto** del trigger, non una volta sola.

---

### Codici errore

Ogni rifiuto esce con `E_ATTIVO_REQUIRE`, con il dettaglio nel contesto:

* il trigger è montato con meno di quattro argomenti;
* la colonna referenziata non esiste sul padre, o il padre o una sua colonna non esistono al
  momento della lettura (configurazione errata);
* il padre non è attivo — e, come detto sopra, non trovato o invisibile.

⚠️ Il codice è di classe tecnica e il suo messaggio parla della generazione della regola, anche
quando il rifiuto è un fatto di dominio (un figlio su un padre spento).

---

### Test

Il comportamento passa da molti pgTAP di dominio che montano o attraversano il require; i più
diretti:

* `db/pgtap/dbops/test-automazione-attivo-eccezioni-v1.sql` — il require non nasce su una FK
  dichiarata eccezione, e c'è sulle altre FK della stessa figlia.
* `db/pgtap/dbops/test-trigger-attivo-orfani-v1.sql` — un require polimorfo senza FK, scritto con
  la grammatica del generatore, non è un orfano.
* `db/pgtap/rls/test-rls-listini-ef-whitelist-write.sql` — documenta la lettura sotto RLS: la
  fixture chiude i vincoli differiti nei panni di chi ha scritto.

---

{% include-markdown "signature-core.md" %}
