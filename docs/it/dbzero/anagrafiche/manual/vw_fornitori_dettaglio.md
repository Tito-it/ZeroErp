## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_fornitori_dettaglio`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori) — la riga di partenza
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — denominazione, codice fiscale e partita IVA
> * [config.stati_fornitore](/dbzero/config/tabelle/stati_fornitore) — lo stato e il flag `blocca_ordini`
> * [config.regimi_fiscali](/dbzero/config/tabelle/regimi_fiscali) — la descrizione del regime
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la lista configurabile che legge la vista
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_fornitore_attivo](/dbzero/anagrafiche/funzioni/fn_check_fornitore_attivo) — la regola «fornitore utilizzabile», che la vista non applica
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — come una vista diventa una lista configurabile

---

### 🎯 Scopo Principale

`anagrafiche.vw_fornitori_dettaglio` mette il fornitore in una riga: il soggetto, lo stato, il pagamento, la
ritenuta, il regime fiscale e la qualifica, con le descrizioni dei cataloghi accanto agli id. È la superficie da cui
si legge la scheda del fornitore e la sorgente della sua lista configurabile.

---

### Una riga per fornitore, con le descrizioni

Ogni fornitore esce una volta, col soggetto del suo ruolo (denominazione, codice fiscale, partita IVA e
l'identificativo fiscale unico, che la lista usa come colonna) e, per ogni riferimento a un catalogo, il codice e
la descrizione da mostrare. Lo stato esce in due forme: `stato_codice_interno`, la chiave stabile da usare nella
logica, e `stato_codice`, da mostrare.

Il soggetto è legato con un join interno, i cataloghi con join esterni: un riferimento mancante lascia vuote le sue
colonne senza far sparire il fornitore.

---

### Che cosa non fa

* **Non filtra.** Un fornitore spento, o in uno stato che blocca gli ordini, esce come gli altri: `attivo` e
  `blocca_ordini` sono colonne da leggere. Chi deve decidere se il fornitore si può usare chiede a
  `anagrafiche.fn_check_fornitore_attivo`.
* **Non porta lo split payment né l'instradamento della fatturazione elettronica**, che sono del soggetto.
* **Non porta le note**, che restano sulla tabella.

---

### Chi vede che cosa

La vista gira coi permessi del proprietario (non è `security_invoker`). Nessuna delle tabelle che legge
(`anagrafiche.fornitori`, `anagrafiche.soggetti_ruoli`, `anagrafiche.soggetti`) ha la visibilità per azienda, e chi
interroga vede tutti i fornitori.

---

### ⚠️ Che cosa oggi non copre

* **La vista non eredita una visibilità futura.** Senza `security_invoker`, una policy aggiunta alle tabelle che
  legge non vale per chi interroga la vista, e nessun test lo segnala.
* **L'applicazione ha la scrittura su una vista che non si scrive.** `zeroerp_app` ha `INSERT`, `UPDATE` e
  `DELETE` sulla vista, che unisce più tabelle e non ha trigger di scrittura: il permesso non serve a niente e non
  dovrebbe esserci.

---

### Test

* `db/pgtap/ui/test-lista-fornitori-seed.sql` — la lista configurabile dei fornitori legge questa vista, con la
  colonna dell'identificativo fiscale.

---

{% include-markdown "signature-core.md" %}
