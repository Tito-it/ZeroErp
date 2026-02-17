## 📘 Documentazione Concettuale – Tabella `vendite.fatture_sdi_eventi`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture_sdi](/dbzero/vendite/tabelle/fatture_sdi)  
> • [config.stati_sdi](/dbzero/config/tabelle/stati_sdi)  

---

### 🎯 Scopo Principale

(latest review 16-02-2026)  
`vendite.fatture_sdi_eventi` mantiene lo **storico cronologico eventi SDI**
per ciascun tentativo (`fattura_sdi_id`).

Consente di registrare:

* cambi stato intermedi
* notifiche tecniche
* errori di trasporto o applicativi
* payload raw ricevuti dal canale SDI

---

### ✅ Regole principali

* Ogni evento e` legato a una testata `fatture_sdi`.
* `stato_sdi_id` e` opzionale: alcuni eventi possono essere solo tecnici/informativi.
* `origine` distingue eventi esterni (`SDI`) da eventi interni (`SISTEMA`).
* `meta` conserva il payload esteso dell'evento.

---

### 🧩 Note operative

* Lo stato corrente tentativo resta su `fatture_sdi`.
* Questa tabella e` append-only dal punto di vista applicativo (storico).
* `codice_evento` aiuta il mapping con codifiche SDI o adapter esterni.

---

{% include-markdown "signature-core.md" %}
