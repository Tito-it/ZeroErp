## 📘 Documentazione Concettuale – Tabella `vendite.listini_versioni`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.listini](/dbzero/vendite/tabelle/listini)  
> • [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)  
>
---

### 🎯 Scopo Principale

La tabella `vendite.listini_versioni` gestisce il versionamento temporale dei listini.
Ogni versione definisce una finestra di validita` e una priorita` operativa.

---

### ✅ Regole principali

* univocita` per `listino_id + codice_versione`;
* `stato` ammessi:
  * `BOZZA`
  * `ATTIVA`
  * `CHIUSA`
* `priorita > 0`;
* `valido_al` maggiore di `valido_dal` se valorizzato;
* no overlap temporale tra versioni attive dello stesso listino
  (`ex_listini_versioni_no_overlap`).

---

### 🧩 Utilizzo previsto

* garantire coerenza storica prezzi per data di riferimento;
* supportare publish controllata di nuove versioni;
* fornire ordinamento secondario in risoluzione prezzi.

---

{% include-markdown "signature-core.md" %}
