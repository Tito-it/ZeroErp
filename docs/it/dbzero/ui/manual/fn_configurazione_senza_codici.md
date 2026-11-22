## 📘 Documentazione Concettuale – Funzione `ui.fn_configurazione_senza_codici`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — l'elenco `colonne`
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — l'elenco `widget`
>
> Approfondimento funzioni:
>
> * [ui.trgfn_voce_ritira_dalle_preferenze](/dbzero/ui/funzioni/trgfn_voce_ritira_dalle_preferenze) — la usa al ritiro di una colonna o di una card

---

### 🎯 Scopo Principale

`ui.fn_configurazione_senza_codici` restituisce la configurazione di una preferenza senza le voci di
certi codici, in uno dei suoi elenchi: le colonne di una lista o le card di una dashboard. Non scrive
niente e non solleva errori.

---

### Che cosa fa

* Toglie dall'elenco indicato le voci il cui codice è fra quelli dati. Le altre voci restano, nel
  loro ordine e con i loro campi.
* Se l'elenco resta vuoto, la chiave esce: quella parte della preferenza torna a seguire il preset.
* Se l'elenco manca, non è un elenco o non ha voci di quei codici, la configurazione torna com'è. Un
  elenco vuoto salvato dalla persona resta com'era.
* Le altre chiavi della configurazione (le righe per pagina, il numero di card) non si toccano.

---

### Una sede

La stessa operazione serve al ritiro di una colonna, al ritiro di una card dal pool e alla bonifica
delle voci rimaste dai ritiri di prima: chi la chiede la chiede qui.

---

### Codici errore

Nessuno.

---

### Test

* `db/pgtap/ui/test-ui-ritiro-voce-preferenze-v1.sql` — le voci tolte e le altre nel loro ordine,
  l'elenco vuoto che esce, la configurazione senza voci di quei codici che torna com'è.

---

### Note di migrazione

* 2026-11-22 — nasce col ritiro delle voci dalle preferenze.

---

{% include-markdown "signature-core.md" %}
