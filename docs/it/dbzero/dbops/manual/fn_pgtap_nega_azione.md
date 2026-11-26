## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_nega_azione`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.user_override_azioni](/dbzero/config/tabelle/user_override_azioni) — l'eccezione utente sull'azione, che la fixture scrive
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_concedi_azione](/dbzero/dbops/funzioni/fn_pgtap_concedi_azione) — il gemello che concede
> * [dbops.fn_pgtap_scrivi_override](/dbzero/dbops/funzioni/fn_pgtap_scrivi_override) — la strada del verbo del SUPER_ADMIN
> * [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione) — il guard che il test mette alla prova
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — il permesso si costruisce, non si cerca

---

### 🎯 Scopo Principale

**Nega a un utente di un test un'azione di processo**, con un'eccezione utente valida da oggi e
senza scadenza. Restituisce l'id dell'eccezione.

---

### ⭐ Il caso «azione negata» si costruisce

Serve ai test che provano il rifiuto di un verbo: si concede l'azione, si prova che il verbo passa,
poi la si nega e si prova che il verbo rifiuta. Vale anche quando il profilo dell'utente l'azione la
concede: l'eccezione individuale viene prima.

È il gemello di [`fn_pgtap_concedi_azione`](/dbzero/dbops/funzioni/fn_pgtap_concedi_azione), senza
il tetto d'area: negare non chiede di aprire l'area. Le altre eccezioni dell'utente restano.

---

### Codici errore

Valgono quelli del verbo delle eccezioni. Un'azione che non esiste è un'eccezione senza codice
sollevata dalla fixture.

---

### Test

`db/pgtap/config/test-porta-override-permessi-v1.sql`, `db/pgtap/magazzino/test-reso-carico-v1.sql`.

---

### Note di migrazione

* 2026-11-27 — nasce al posto delle righe `abilitata = false` scritte a mano dai test
  (brief-db-porte-aperte-dalla-sola-guc, giro 10-quater).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
