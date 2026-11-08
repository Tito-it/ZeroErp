## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_attivita_fatturabili_normalize`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — la tabella che normalizza
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — la riga di commessa da cui ogni attività nasce
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il tipo del documento, da cui il tipo di documento fiscale
>
> Approfondimento funzioni:
>
> * [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa) — l'unico scrittore
> * [vendite.fn_get_tipo_doc_fiscale_id](/dbzero/vendite/funzioni/fn_get_tipo_doc_fiscale_id) — il tipo di documento fiscale dal tipo del documento
> * [vendite.fn_get_valuta_id](/dbzero/vendite/funzioni/fn_get_valuta_id) — la valuta dal cliente e dall'emittente

---

### 🎯 Scopo Principale

Completa, prima della scrittura, due campi di un'attività fatturabile che possono arrivare vuoti: il **tipo di documento fiscale** e la **valuta**. Montata `BEFORE INSERT` e `BEFORE UPDATE` delle colonne di competenza, della riga di commessa, del cliente, del tipo di documento fiscale e della valuta (`trg_attivita_fatturabili_normalize_ins_upd`).

---

### Ogni attività nasce da una riga di commessa

Un'attività fatturabile punta sempre la sua riga di commessa con una FK vera,
`commessa_attivita_id`, obbligatoria e unica. La provenienza dell'attività è quella della riga di
commessa: l'attività non ha colonne di provenienza sue.

Per questo la funzione lavora sempre nel ramo della riga di commessa:

* **tipo di documento fiscale**, se manca: dal tipo del documento da cui nasce la riga di commessa
  (`commesse_attivita.sorgente_tipo_id`), con `vendite.fn_get_tipo_doc_fiscale_id`. Una riga di
  commessa senza documento (un onere, una rettifica) nasce dalla commessa, e prende il tipo
  `COMMESSA`;
* **valuta**, se manca e c'è il cliente: dal cliente e dall'emittente della commessa, con
  `vendite.fn_get_valuta_id`.

Le competenze (`competenza_mese`, `competenza_dal`, `competenza_al`) non le tocca: arrivano già
complete dalla riga di commessa.

---

### ⚠️ Il ramo delle competenze non gira mai, e non è un difetto

Il corpo ha un secondo ramo, per le righe **senza** riga di commessa: porta `competenza_mese` al
primo del mese (o al mese di `posticipa_al`), riempie `competenza_dal` e `competenza_al` dalla data
dell'attività, risolve la valuta dal cliente. Con `commessa_attivita_id` obbligatorio quel ramo non
è raggiungibile: la funzione esce sempre prima.

Non serve: l'unico scrittore,
[`vendite.fn_emit_attivita_fatturabili_da_commessa`](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa),
copia competenza e date dalla riga di commessa, che le ha già nella forma giusta
(`competenza_mese` al primo del mese).

---

### Che cosa non fa

* Nessuna validazione di dominio: le fanno i guard dedicati.
* Le cancellazioni non la attivano.

---

### Note di migrazione

* 2026-11-07 — il tipo di documento fiscale si legge dalla riga di commessa; l'attività fatturabile
  perde le sue colonne di provenienza (`sorgente_*` e `sorgente_origine_tipo_id`), e con loro le
  regole della funzione che le normalizzavano (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
