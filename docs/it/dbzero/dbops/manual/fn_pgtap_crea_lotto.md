## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_lotto`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) — il lotto che la fixture fa nascere
> * [vendite.fatturazione_lotti_esiti](/dbzero/vendite/tabelle/fatturazione_lotti_esiti) — l'esito che trattiene un gruppo
> * [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/tabelle/tipi_doc_fiscale_registri) — perché il tipo documento deve avere un registro
>
> Approfondimento funzioni:
>
> * [vendite.fn_create_fatturazione_lotto](/dbzero/vendite/funzioni/fn_create_fatturazione_lotto) — la madre da cui nasce il lotto
> * [dbops.fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder) — il cliente da cui prende azienda e utility
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — il passaggio di stato per la matrice
> * [vendite.fn_segna_esito_gruppo_lotto](/dbzero/vendite/funzioni/fn_segna_esito_gruppo_lotto) — la porta degli esiti, che qui non si usa
> * [vendite.fn_sync_lotto_fatture_stato](/dbzero/vendite/funzioni/fn_sync_lotto_fatture_stato) — come si muove un lotto con fatture
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: **un lotto di fatturazione dell'azienda di chi agisce in una chiamata**, nato dalla
madre del dominio, portato allo stato che il test chiede e, a richiesta, con l'esito che
«trattiene» un gruppo di documenti.

Cinque pgTAP scrivevano il lotto a mano, con un codice inventato e lo stato scritto direttamente —
tre già emessi o definitivi, un lotto che nessuna funzione del dominio produce — e ognuno
riscriveva la riga dell'esito. Ora la strada ha una sede.

---

### Che cosa decide la fixture e che cosa decide il dominio

* **La nascita** la fa `vendite.fn_create_fatturazione_lotto`: codice, marchio del giro
  (`lock_batch_id`) e stato di bozza li decide lei, come in produzione.
* **Azienda e utility** sono quelle del cliente: quello del conto passato dal test (verificato:
  uno di un'altra azienda ferma la fixture) o uno nuovo del mondo.
* **Il lotto è dell'azienda**, non del cliente: il conto di fatturazione resta vuoto, come in un
  giro massivo. A richiesta il lotto è anche del cliente.
* **Il tipo documento** è quello chiesto, o il primo attivo che ha un registro: la madre lo
  pretende. **La competenza** è quella chiesta, o il mese della data operativa.
* **Lo stato** si giudica prima di costruire — deve essere uno stato fiscale attivo che vale per un
  lotto, altrimenti la fixture si ferma — e si raggiunge per la matrice dei passaggi, sul lotto
  ancora vuoto.

---

### ⚠️ Il gruppo trattenuto

Con una chiave di gruppo la fixture scrive l'esito in errore (`E_PULL_COMMESSA`) che tiene quel
gruppo dentro il lotto: la forma dei test del pull. La riga si scrive direttamente, non dalla porta
`vendite.fn_segna_esito_gruppo_lotto` che la scrive in produzione: per questo l'esito di prova non
porta il momento dell'errore (`errore_quando`), che la porta timbra.

---

### Che cosa non scrive

Le fatture e il loro aggancio al lotto: sono il caso del test. Un lotto con fatture si muove col
verbo del dominio `vendite.fn_sync_lotto_fatture_stato`, non da qui. Esce con i vincoli richiusi
(`IMMEDIATE`).

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-lotto-v1.sql` — lotto in bozza dell'azienda del mondo, senza
  cliente; codice e marchio dalla madre; il tipo documento ha un registro; il cliente di un'altra
  fixture con un lotto nuovo senza cliente; il lotto legato al cliente; definitiva per la matrice
  sul lotto vuoto; l'esito del gruppo trattenuto; uno stato che non esiste rifiutato.

---

### Note di migrazione

* 2026-10-24 — nasce dal modello del documento di vendita (`brief-modello-documento-vendita`, R-4);
  lo stesso giorno, col conto del test non costruisce più un cliente in più.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
