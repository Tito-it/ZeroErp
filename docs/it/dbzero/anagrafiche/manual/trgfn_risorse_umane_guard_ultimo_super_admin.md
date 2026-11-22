## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_risorse_umane_guard_ultimo_super_admin`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il rapporto di lavoro che il guard presidia
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — la veste operatore appesa allo stesso ruolo
>
> Approfondimento funzioni:
>
> * [script.fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo) — la domanda a cui il guard delega
> * [script.fn_identita_super_admin_senza_scadenza](/dbzero/script/funzioni/fn_identita_super_admin_senza_scadenza) — che cosa vuol dire «SUPER_ADMIN senza scadenza»
> * [anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_ultimo_super_admin) — il gemello sulla veste
> * [anagrafiche.trgfn_risorse_umane_guard_identita_attiva](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_guard_identita_attiva) — chi ferma prima lo spegnimento del rapporto
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — la veste, il rapporto e la credenziale

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_risorse_umane_guard_ultimo_super_admin` rifiuta la modifica del rapporto di lavoro di un
amministratore che lascerebbe il sistema senza nessun SUPER_ADMIN senza scadenza: spegnerlo, dargli una data di
fine, spostarne l'inizio oltre oggi, spostarlo su un altro ruolo.

Un operatore entra solo finché vale anche il suo rapporto di lavoro: una data di fine sul rapporto toglie la
garanzia quanto una sulla veste. La regola intera e le sue quattro sedi stanno nel blocco comune in fondo alla
pagina.

---

### Quando scatta

Dopo la modifica di un rapporto in cui cambia `attivo`, `valido_dal`, `valido_al` o `soggetto_ruolo_id`. Il corpo
lavora solo su quattro transizioni:

* il rapporto passa da acceso a spento;
* il rapporto riceve una data di fine che prima non aveva;
* l'inizio del rapporto passa da un giorno già arrivato a un giorno oltre oggi (il giorno operativo);
* il rapporto si sposta su un altro `soggetto_ruolo_id`: la veste dell'amministratore resterebbe senza rapporto.

Poi cerca, sul ruolo **di prima**, una veste `OPERATORE` con un legame attivo verso un profilo `SUPER_ADMIN`
attivo, accesa o spenta. Se non c'è, tace. Se c'è, chiede a `script.fn_check_almeno_un_super_admin_attivo` com'è il
sistema dopo la scrittura, e rifiuta se non resta nessuno.

Togliere una data di fine o riaccendere il rapporto passa sempre.

---

### Lo spegnimento lo ferma già un altro guard

Finché la veste operatore è accesa, lo spegnimento del rapporto lo rifiuta prima
`anagrafiche.trgfn_risorse_umane_guard_identita_attiva` («figli prima, padre poi»), con un codice suo. Questo guard
resta anche per lo spegnimento, perché non dipende da quell'ordine: le date e lo spostamento li vede solo lui.

---

{% include-markdown "it/dbzero/anagrafiche/_ultimo-super-admin.md" %}

---

### Codici errore

* `E_PROFILO_ULTIMO_SUPER_ADMIN` — dopo la scrittura non resta nessun SUPER_ADMIN senza scadenza. È lo stesso codice
  dei tre gemelli. Il contesto porta il rapporto, la veste trovata e i valori nuovi di `attivo` e delle due date.

---

### Test

* `db/pgtap/anagrafiche/test-super-admin-senza-scadenza-v1.sql` — la data di fine e l'inizio spostato a domani sul
  rapporto dell'ultimo amministratore sono rifiutati.

Nessun test prova lo spostamento del rapporto su un altro ruolo, né lo spegnimento che arriva qui (lo ferma prima
l'altro guard).

---

### Note di migrazione

* 2026-10-07 — nasce insieme alla regola «senza scadenza», quando la fine del rapporto diventa la fine
  dell'accesso dell'operatore.

---

{% include-markdown "signature-core.md" %}
