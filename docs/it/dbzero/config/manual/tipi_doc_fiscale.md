## 📘 Documentazione Concettuale – Tabella `config.tipi_doc_fiscale`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/manual/tipi_doc_fiscale_registri)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale)  
>
### 🎯 Scopo Principale
(latest review 27-01-2026)
La tabella **`config.tipi_doc_fiscale`** rappresenta il catalogo dei **tipi di
documento fiscale** gestiti dal sistema (es. fattura utility, allaccio, rata,
rettifica). Il tipo documento e` la dimensione **funzionale** del documento e
indica il *perche`* del documento, separandolo dalla numerazione contabile.

---

### Ruolo nel processo

* Determina il **tipo** del documento da emettere (logica di business).
* Guida il **raggruppamento** e la selezione delle attivita` fatturabili.
* Viene associato a un **registro** tramite `vendite.tipi_doc_fiscale_registri`.

⛔ **Il tipo non si deriva.** Nessuna regola cablata stabilisce quale tipo spetta a un documento:
ogni azienda lo usa per la propria classificazione, o non lo usa. Il sistema applica al più un
default configurabile e facoltativo, quello della sorgente (`config.sorgenti.tipo_doc_fiscale_id`,
che resta facoltativa). L'unica garanzia è di riga: una riga di commessa emittibile non può
averlo vuoto, e lo fa valere un guard
([vendite.trgfn_commesse_attivita_guard_tipo_doc_emittibile](/dbzero/vendite/funzioni/trgfn_commesse_attivita_guard_tipo_doc_emittibile)),
non un default obbligatorio a monte.

---

### Relazioni principali

* `vendite.fatture.tipo_doc_fiscale_id` → assegna il tipo documento al documento emesso.
* `vendite.tipi_doc_fiscale_registri` → mapping tipo documento → registro.
* `vendite.attivita_fatturabili.tipo_doc_fiscale_id` (quando valorizzato) → qualifica le righe da fatturare.
* `vendite.fatturazione_lotti.tipo_doc_fiscale_id` → determina il tipo documento del lotto.

---

### Best practice operative

* Mantenere `codice` e `codice_interno` **immutabili**.
* Garantire almeno un mapping verso registro per ogni tipo documento attivo.
* Usare `attivo = false` per dismettere tipi storici senza perdita di consistenza.

---

{% include-markdown "signature-core.md" %}
