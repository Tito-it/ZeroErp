## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_concedi_livello_area`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.user_override_aree](/dbzero/config/tabelle/user_override_aree) — l'eccezione utente sull'area, che la fixture scrive
> * [config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali) — le aree, una per schema
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_concedi_azione](/dbzero/dbops/funzioni/fn_pgtap_concedi_azione) — il gemello, per le azioni di processo
> * [script.fn_guard_livello_area](/dbzero/script/funzioni/fn_guard_livello_area) — il guard del livello su un'area
> * [script.fn_guard_livello](/dbzero/script/funzioni/fn_guard_livello) — il guard sull'oggetto, che ricade sull'area
> * [dbops.fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore) — l'operatore di fixture, che nasce senza azioni né aree
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — il permesso si costruisce, non si cerca

---

### 🎯 Scopo Principale

Dà a un utente di un test un **livello su un'area funzionale**, con un'eccezione utente valida da
oggi e senza scadenza. Restituisce l'id dell'eccezione.

---

### ⭐ Il permesso si costruisce nel test

Serve ai test dei verbi che chiedono un livello d'area
([`script.fn_guard_livello_area`](/dbzero/script/funzioni/fn_guard_livello_area)) o un livello
d'oggetto che ricade sull'area ([`script.fn_guard_livello`](/dbzero/script/funzioni/fn_guard_livello)).
L'operatore di
[`fn_pgtap_crea_emittente_operatore`](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore) è
tecnico, non super admin, e non ha né azioni né aree: il permesso non si cerca nei dati, si concede.

È il gemello di [`dbops.fn_pgtap_concedi_azione`](/dbzero/dbops/funzioni/fn_pgtap_concedi_azione):
quello concede un'azione di processo, questo un livello d'area.

---

### Il secondo giro scrive il livello nuovo, anche più basso

La fixture è idempotente sulla coppia (utente, area): se l'eccezione c'è già, la riscrive col
livello chiesto e la riapre da oggi. Il livello nuovo vale **anche se è più basso** di quello che
c'era.

⭐ È così che un test costruisce il caso «senza il livello»: concede `TUTTO`, prova che il verbo
passa, poi scrive `LETTURA` o `BLOCCATO` e prova che il verbo rifiuta.

«Oggi» è il giorno operativo, come per il gemello.

---

### Codici errore

Valgono quelli dei trigger della tabella delle eccezioni. Un'area che non esiste, un utente o un
livello mancanti sono eccezioni senza codice sollevate dalla fixture: è la fixture a essere chiamata
male.

---

### Test

Nessun pgTAP dedicato: la usano i test dei verbi con un livello d'area, per esempio
`db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` e
`db/pgtap/pagamenti/test-sistemazione-annullo-riporto.sql`.

---

### Note di migrazione

* 2026-11-25 — nasce e ritira quattro copie dello stesso aiuto scritte dentro i test
  (`pg_temp.livello_area`), nel giro dei verbi del reset del lotto e della sistemazione
  (brief-db-porte-aperte-dalla-sola-guc, D-L a).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
