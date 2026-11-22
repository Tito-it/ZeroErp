## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_gestori_guard`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.gestori](/dbzero/anagrafiche/tabelle/gestori) — la tabella che presidia
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — da cui legge la partita IVA
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_gestori_guard_ruolo_gestore](/dbzero/anagrafiche/funzioni/trgfn_gestori_guard_ruolo_gestore) — l'altro guard della riga, sul tipo del ruolo

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_gestori_guard` è il guard di dominio del gestore: a ogni nascita e modifica della riga
controlla che il ruolo esista, che il soggetto abbia la partita IVA e che nel sistema non ci sia un altro
gestore.

---

### Tre controlli, in quest'ordine

1. **Il ruolo esiste.** Dal ruolo risale al soggetto; un ruolo che non c'è, o non passato, ferma la scrittura.
2. **Il soggetto ha la partita IVA**, non vuota. È la regola del ruolo: il gestore è un'impresa.
3. **Nessun altro gestore.** Basta una riga diversa da quella che si scrive: la modifica del gestore che c'è
   passa, una seconda nascita no.

Il guard scatta prima di `anagrafiche.trgfn_gestori_guard_ruolo_gestore`, che per nome viene dopo: un ruolo che
non esiste risponde con il codice di questo guard, uno che esiste ma non è `GE` con quello del guard di ruolo.
Qualunque colonna cambi, i tre controlli si rifanno.

---

### ⚠️ Che cosa oggi non copre

* **Il gestore unico non regge due nascite contemporanee.** È una lettura della tabella, non un vincolo: due
  transazioni che inseriscono insieme non vedono l'una la riga dell'altra.
* **La partita IVA si guarda solo qui.** Tolta dal soggetto dopo la nascita del gestore, nessuno la richiede
  finché la riga del gestore non si riscrive.
* **Le variabili non seguono le colonne.** Sono dichiarate con tipi scritti a mano, e quella dell'id del gestore
  è `integer` contro una colonna `bigint`.

---

### Codici errore

* `E_GESTORE_SOGGETTO_RUOLO_MANCANTE` — il ruolo non è passato o non esiste.
* `E_RUOLO_RICHIEDE_PIVA` — il soggetto del ruolo non ha la partita IVA.
* `E_GESTORE_SINGLETON_VIOLATO` — c'è già un gestore.

---

### Test

* `db/pgtap/anagrafiche/create-soggetto-gestori.sql` — il secondo gestore rifiutato. Il file è fra i rossi noti
  della baseline.

---

{% include-markdown "signature-core.md" %}
