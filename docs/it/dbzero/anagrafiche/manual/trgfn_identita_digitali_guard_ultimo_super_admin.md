## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — la veste che il guard presidia
> * [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings) — il legame che fa di una veste un SUPER_ADMIN
>
> Approfondimento funzioni:
>
> * [script.fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo) — la domanda a cui il guard delega
> * [script.fn_identita_super_admin_senza_scadenza](/dbzero/script/funzioni/fn_identita_super_admin_senza_scadenza) — che cosa vuol dire «SUPER_ADMIN senza scadenza»
> * [anagrafiche.trgfn_risorse_umane_guard_ultimo_super_admin](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_guard_ultimo_super_admin) — il gemello sul rapporto di lavoro
> * [config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin](/dbzero/config/funzioni/trgfn_profili_accesso_bindings_guard_ultimo_super_admin) — il gemello sul legame
> * [config.trgfn_credenziali_guard_ultimo_super_admin](/dbzero/config/funzioni/trgfn_credenziali_guard_ultimo_super_admin) — il gemello sul blocco della credenziale
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — la veste, il rapporto e la credenziale
> * [Architettura multi-face auth](/guide/architettura-multi-face-auth) — vesti, profili e legami

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin` rifiuta la modifica di una veste che lascerebbe il
sistema senza nessun SUPER_ADMIN senza scadenza: spegnerla, darle una data di fine, spostarne l'inizio oltre oggi.

È la sede della regola sul lato della veste. La regola intera, le sue quattro sedi e ciò che conta come
«senza scadenza» stanno nel blocco comune in fondo alla pagina.

---

### Quando scatta

Dopo la modifica di una veste in cui cambia `attivo`, `valido_dal` o `valido_al`. Il corpo lascia passare subito
tutto ciò che non riduce la garanzia, e lavora solo su tre transizioni:

* la veste passa da accesa a spenta;
* la veste riceve una data di fine che prima non aveva;
* l'inizio della veste passa da un giorno già arrivato a un giorno oltre oggi (il giorno operativo).

Poi guarda se la veste ha un legame attivo verso un profilo `SUPER_ADMIN` attivo: se non ce l'ha, la garanzia non
può peggiorare e il guard tace. Altrimenti chiede a `script.fn_check_almeno_un_super_admin_attivo` com'è il sistema
dopo la scrittura, e rifiuta se non resta nessuno.

Spostare la fine a una data diversa quando una data c'era già non è a rischio: quella veste non era senza
scadenza.

---

### Perché un guard sulla veste

Il legame di una veste spenta resta acceso: la veste smette di contare senza che il legame venga scritto, e il
guard sui legami non lo vedrebbe. Lo stesso vale per una data di fine messa sulla veste. Ogni tabella da cui la
garanzia si perde ha il suo guard, e tutti chiedono alla stessa funzione.

---

{% include-markdown "it/dbzero/anagrafiche/_ultimo-super-admin.md" %}

---

### Codici errore

* `E_PROFILO_ULTIMO_SUPER_ADMIN` — dopo la scrittura non resta nessun SUPER_ADMIN senza scadenza. È lo stesso codice
  dei tre gemelli. Il contesto porta la veste, la sua credenziale, il suo ruolo applicativo e i valori nuovi di
  `attivo` e delle due date.

---

### Test

* `db/pgtap/anagrafiche/test-super-admin-senza-scadenza-v1.sql` — la data di fine sulla veste dell'ultimo
  amministratore, l'inizio spostato a domani e lo spegnimento sono rifiutati; la data di fine a un amministratore
  quando ne resta un altro, e a un operatore che non è amministratore, passa; togliere la data di fine passa.
* `db/pgtap/config/test-profili-accesso-guard-ultimo-super-admin.sql` — lo spegnimento della veste che porta
  l'ultimo legame `SUPER_ADMIN` è rifiutato.

Nessun test prova il caso della veste che cambia credenziale, ruolo o tipo.

---

### Note di migrazione

* 2026-06-29 — il profilo `SUPER_ADMIN` si riconosce dal tipo invece che dal codice.
* 2026-09-25 — la funzione delegata impara che una credenziale bloccata non conta, e nasce il gemello sul blocco.
* 2026-10-07 — il guard guarda anche le date, e la regola diventa «senza scadenza»: prima scattava solo sullo
  spegnimento, e una data di fine messa all'ultimo amministratore lo faceva scadere senza che nessuno la fermasse.

---

{% include-markdown "signature-core.md" %}
