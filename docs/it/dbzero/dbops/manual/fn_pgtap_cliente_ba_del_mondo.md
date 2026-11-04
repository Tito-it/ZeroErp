## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_cliente_ba_del_mondo`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — il legame BA → azienda che si verifica
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — da dove escono le chiavi del cliente
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder) — il cliente dei builder di documento, che la chiama
> * [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo minimo, che la chiama per verificare il cliente che ha appena costruito
> * [dbops.fn_pgtap_azienda_di_chi_agisce](/dbzero/dbops/funzioni/fn_pgtap_azienda_di_chi_agisce) — l'azienda contro cui il legame si confronta
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — i builder che ricevono il cliente di un'altra fixture

---

### 🎯 Scopo Principale

La verifica che il cliente passato a un builder di documento — un billing account costruito
da un'altra fixture — sia dell'azienda di chi agisce, e le sue chiavi: BA, istanza,
soggetto ruolo del cliente e utility.

È un building block con due chiamanti:
[fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder), e
attraverso quella i builder di commessa, contratto, fattura, ordine, lotto e bolla senza
ordine; e [fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente),
che verifica il legame del cliente appena costruito.

---

### ⭐ Si verifica prima di costruire

Se il billing account è legato a **un'altra azienda**, o a nessuna, la funzione solleva
subito, e il messaggio comincia con il nome del builder che l'ha chiesta (`p_chiamante`).
Senza questo controllo la testata nascerebbe e la rifiuterebbe più avanti il guard
emittente/BA del documento, con un messaggio che non nomina la fixture.

Il legame si legge da
[anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account),
che non è sotto la sicurezza per riga: la lettura vale anche quando il test gira come
l'applicazione.

---

### Codici errore

Nessun codice registrato: il rifiuto è un'eccezione senza codice, con il testo che nomina il
chiamante e le due aziende.

---

### Test

Nessun pgTAP la chiama per nome; la provano i file dei builder, sul caso del billing account
di un'altra azienda:

* `db/pgtap/dbops/test-fn-pgtap-cliente-del-builder-v1.sql` — un BA di un'altra azienda
  solleva, nominando il chiamante;
* `db/pgtap/dbops/test-fn-pgtap-crea-contratto-v1.sql` e
  `db/pgtap/dbops/test-fn-pgtap-crea-ordine-v1.sql` — lo stesso rifiuto, attraverso il
  builder.

---

### Note di migrazione

* 2026-10-22 — estratta alla terza copia (regola del 2): lo stesso controllo era scritto nei
  builder della fattura e del contratto, e il terzo, quello dell'ordine, l'ha fatto estrarre.
* 2026-10-24 — i builder non la chiamano più direttamente: passano da
  `dbops.fn_pgtap_cliente_del_builder` (`brief-modello-documento-vendita`, §4-octies).
* 2026-11-04 — la chiama anche `dbops.fn_pgtap_crea_mondo_cliente`, che ne teneva una copia
  sfuggita all'estrazione (`brief-db-revisione-dbops`).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
