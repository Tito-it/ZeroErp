## 📘 Documentazione Concettuale – Funzione `script.trgfn_notify_permessi_catalogo()`

> 👀 **Vedi anche**
>
> **Chiama:** [script.fn_notify_permessi_catalogo](/dbzero/script/funzioni/fn_notify_permessi_catalogo)
>
> **Tabelle che la usano:** [config.azioni_processo](/dbzero/config/tabelle/azioni_processo) · [config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali) · [config.area_model_overrides](/dbzero/config/tabelle/area_model_overrides) · [config.profili_accesso](/dbzero/config/tabelle/profili_accesso) · [config.profili_accesso_aree](/dbzero/config/tabelle/profili_accesso_aree) · [config.profili_accesso_azioni](/dbzero/config/tabelle/profili_accesso_azioni) · [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings)

---

### 🎯 Scopo Principale
(scritta il 04-10-2026)

È la funzione dei trigger `trg_<tabella>_z90_notify_permessi_ins_upd_dlt`
sulle sette tabelle del **catalogo dei permessi**: aree, azioni, oggetti,
profili e legami dei profili. A ogni scrittura su una di queste tabelle
(inserimento, modifica, cancellazione, svuotamento) avvisa il backend che
deve svuotare la cache dei permessi.

* Scatta **una volta per istruzione**, non per riga: un aggiornamento del seed
  che tocca cinquanta righe produce un solo avviso per tabella.
* Scatta anche su un'istruzione che non tocca nessuna riga: un avviso in più,
  innocuo.
* Il nome della tabella lo prende da PostgreSQL, non da un argomento.

Perché queste sette e non altre: sono la parte di **catalogo** che la catena
dei permessi legge. Le tabelle per utente (override, identità, reparto) restano
fuori: gli override li scrive il pannello, che svuota già la cache
dell'utente; il cambio di reparto ha il suo avviso (canale `cambio_reparto`).

Presidio: `db/pgtap/script/test-notify-permessi-catalogo-v1.sql`.

{% include-markdown "signature-core.md" %}
