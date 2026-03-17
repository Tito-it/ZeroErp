## 📘 Documentazione Concettuale – Tabella `vendite.fatture_sdi`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [config.stati_sdi](/dbzero/config/tabelle/stati_sdi)  
> • [vendite.fatture_sdi_eventi](/dbzero/vendite/tabelle/fatture_sdi_eventi)  

---

### 🎯 Scopo Principale

(latest review 16-02-2026)  
`vendite.fatture_sdi` rappresenta la **testata dei tentativi di invio SDI** per fattura.

Serve a tracciare:

* stato corrente del tentativo (`stato_sdi_id`)
* timestamp invio/ricezione
* identificativo assegnato da SDI
* errore sintetico e flag `critical`
* payload tecnico in `meta`

---

### Regole principali

* Una fattura puo` avere piu` tentativi (`tentativo_num` incrementale).
* Vincolo univoco su (`fattura_id`, `tentativo_num`).
* `critical=true` segnala tentativo con errore bloccante.
* Lo storico fine-grained dei passaggi e` in `vendite.fatture_sdi_eventi`.

---

### Note operative

* Usare `identificativo_sdi` per il protocollo restituito dal sistema SDI.
* `meta` conserva dettaglio tecnico (XML ricevute, codici adapter, payload raw).
* La tabella e` volutamente minimale: dettagli estesi e audit eventi sono demandati a `fatture_sdi_eventi`.

---

{% include-markdown "signature-core.md" %}
