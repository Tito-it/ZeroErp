## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_risorse_umane_guard_identita_attiva`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il rapporto di lavoro che il guard presidia
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — la veste operatore che va spenta prima
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — la stessa regola, generata, per le coppie legate da una chiave esterna
> * [anagrafiche.trgfn_risorse_umane_guard_ultimo_super_admin](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_guard_ultimo_super_admin) — l'altro guard sullo spegnimento del rapporto
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — la veste, il rapporto e la credenziale

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_risorse_umane_guard_identita_attiva` rifiuta lo spegnimento di un rapporto di lavoro finché sullo
stesso ruolo c'è una veste `OPERATORE` accesa.

---

### Figli prima, padre poi, scritto a mano

In tutto il progetto una riga non si spegne finché ha figli accesi: prima si spengono i figli, poi il padre. Per le
coppie legate da una chiave esterna il guard lo genera l'automazione. La veste operatore e il rapporto di lavoro non
sono legati da una chiave esterna: si trovano perché hanno lo stesso `soggetto_ruolo_id`. L'automazione non li vede,
e il guard è scritto a mano.

L'alternativa, lasciar spegnere il rapporto e spegnere la credenziale di conseguenza, farebbe trascinare il figlio
dal padre: un modello diverso da tutte le altre coppie.

---

### Quando scatta

Prima della modifica della colonna `attivo` di un rapporto, e solo quando passa da acceso a spento. Cerca una veste
`OPERATORE` accesa sullo stesso `soggetto_ruolo_id` della riga nuova; se ce n'è più d'una nomina la prima.

Conta il solo interruttore della veste, non le sue date: una veste accesa ma già scaduta ferma comunque lo
spegnimento del rapporto. È coerente con la regola, che guarda lo stato dei figli e non la loro validità.

Il rimedio è spegnere prima la veste e poi ripetere lo spegnimento del rapporto.

Le date del rapporto non sono affar suo: una data di fine o un inizio spostato in avanti chiudono l'accesso
dell'operatore senza spegnere niente, e la credenziale li segue con la sincronizzazione. Per l'ultimo
amministratore li ferma il guard dell'ultimo SUPER_ADMIN.

---

### ⚠️ Che cosa oggi non copre

* **Lo spegnimento insieme allo spostamento.** Se la stessa modifica spegne il rapporto e ne cambia il
  `soggetto_ruolo_id`, il guard cerca la veste sul ruolo nuovo: la veste accesa sul ruolo di prima non lo ferma.

---

### Codici errore

* `E_RISORSA_UMANA_IDENTITA_ATTIVA` — il rapporto ha una veste operatore ancora accesa. È un codice suo, di classe
  `CONFLITTO_STATO`: lo stato della veste può cambiare, e l'interfaccia mostra l'azione disabilitata col motivo.
  Non usa il codice dell'automazione, che nomina una chiave esterna che qui non c'è. Il contesto indica
  l'interruttore da accendere (`attivo`), il rapporto e il ruolo; il messaggio nomina lo username della veste
  ancora accesa, che è ciò che una persona riconosce.

---

### Test

* `db/pgtap/anagrafiche/test-risorse-umane-guard-identita-attiva-v1.sql` — su un operatore costruito con la sua
  funzione di creazione: lo spegnimento con la veste accesa è rifiutato col suo codice e con lo username nel
  messaggio; con la veste spenta prima passa, e la credenziale si spegne; il guard generato di prima non è più
  montato.

Nessun test prova lo spegnimento insieme allo spostamento del ruolo.

---

### Note di migrazione

* 2026-09-12 — prende il posto del guard generato dall'automazione quando la veste e il rapporto erano legati da
  una tabella ponte, `risorse_umane_auth_user`. Dopo che il ponte era diventato una vista, quel guard funzionava
  per caso; col ritiro della vista sarebbe caduto. Il guard nuovo è entrato in servizio prima del ritiro di quello
  vecchio, senza una finestra senza regola.

---

{% include-markdown "signature-core.md" %}
