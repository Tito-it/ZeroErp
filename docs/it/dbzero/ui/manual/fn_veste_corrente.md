## 📘 Documentazione Concettuale – Funzione `ui.fn_veste_corrente`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la configurazione di una lista
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — la configurazione di una dashboard
> * [ui.fn_lista_colonne_ricerca_full](/dbzero/ui/funzioni/fn_lista_colonne_ricerca_full) — le colonne della ricerca libera
> * [script.fn_resolve_livello_area](/dbzero/script/funzioni/fn_resolve_livello_area) — una funzione di permesso, che con una veste sbagliata nega
>
> Guide:
>
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — vesti e profili

---

### 🎯 Scopo Principale

La funzione restituisce la veste della sessione (operatore, cliente del portale, …) per le funzioni
che configurano le schermate: liste, dashboard, ricerca libera. La legge dalla variabile di sessione
`app.ruolo_applicativo`, che imposta l'autenticazione.

---

### Senza veste valida, tutte le vesti

* Una veste valida: quella.
* Variabile assente o vuota: `NULL`.
* Un valore che non è una veste: `NULL`, senza errore.

`NULL` vuol dire «tutte le vesti dell'utente»: chi lo riceve considera i profili d'accesso di tutte
le sue identità. Una schermata non smette di aprirsi per una variabile di sessione scritta male.

---

### ⛔ Regola di presentazione, non di permesso

Le funzioni di `script` che decidono se un accesso è consentito, come
[fn_resolve_livello_area](/dbzero/script/funzioni/fn_resolve_livello_area), fanno il contrario: con
una veste non riconosciuta negano. Questa funzione non si usa per decidere un accesso.

---

### ⚠️ Che cosa oggi non copre

* **Il permesso di colonna la usa come se fosse presentazione.** La configurazione della lista e la
  ricerca libera passano il suo `NULL` alla regola dei permessi di colonna, che allora mescola i
  profili di tutte le identità dell'utente: una colonna `BLOCCATO` sotto una veste può tornare
  visibile per un permesso più specifico di un'altra. Il ripiego qui fa da permesso.

---

### Codici errore

Nessuno: la funzione non rifiuta mai.

---

### Test

* `db/pgtap/ui/test-fn-lista-colonne-ricerca-full-v1.sql` — la veste valida, un valore fuori dominio
  e la variabile vuota; sotto la veste di portale il permesso dell'identità operatore non vale.

---

### Note di migrazione

* 2026-09-23 — nasce dalle due copie identiche nella configurazione delle liste e delle dashboard,
  quando la ricerca libera è diventata il terzo lettore.

---

{% include-markdown "signature-core.md" %}
