## 📘 Documentazione Concettuale – Tabella `vendite.offerte_commerciali_utilities`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> • [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> • [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali)
> • [config.utilities](/dbzero/config/tabelle/utilities)
> • [config.classi_utenze](/dbzero/config/tabelle/classi_utenze)
> • [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze)

---

### 🎯 Scopo Principale

(rev 2026-05-24)

`vendite.offerte_commerciali_utilities` conserva lo **snapshot precontrattuale** dei
dati tecnici e tariffari della utility al momento della creazione dell'offerta commerciale.

E' il **mirror fedele di `vendite.contratti_utilities`** con `offerta_id` al posto di
`contratto_id`. Tutti i campi business di `contratti_utilities` sono presenti per garantire
che `fn_push_offerta_a_contratto` sia una copia 1:1 senza conversioni (§5.1 analisi,
addendum A3).

---

### Relazione 1:1 con l'offerta

Il vincolo UNIQUE su `offerta_id` (`uq_offerte_commerciali_utilities_offerta_id`) impone
la relazione 1:1: **un'offerta ha al piu' uno snapshot utility** (mono-utility §5.1).

Il record viene creato al momento della creazione dell'offerta, copiando i dati
dall'istanza precontrattuale corrente (`anagrafiche.istanze_dati_precontrattuali`).
Nessun aggiornamento automatico successivo e' previsto: variazioni sostanziali
richiedono una revisione dell'offerta.

---

### Campi principali

- `istanza_utility_id` — FK → `anagrafiche.istanze_utilities(id)`. Istanza utility
  oggetto dell'offerta. Coerente con `offerte_commerciali.istanza_utility_id`.
- `utility_id` — FK → `config.utilities(id)`. Utility di riferimento.
- `istanza_dati_precontrattuali_id` — FK → `anagrafiche.istanze_dati_precontrattuali(id)`.
  Tracciabilita verso il record sorgente dei dati precontrattuali. Nullable: se non esiste
  un record precontrattuale, la tabella resta vuota (come in `contratti_utilities`).
- `classe_utenza_id` — FK → `config.classi_utenze(id)`. Snapshot classe utenza.
  NULL per utility senza dimensione classe (commercio / Base).
- `tipo_utenza_id` — FK → `config.tipi_utenze(id)`. Snapshot tipo utenza (pricing v5).
  NULL per utility senza dimensione tipo/classe.
- `param_1_num` / `param_2_txt` — parametri tecnici snapshot dai precontrattuali.
- `meta` — metadati snapshot estensibili.

---

### Coerenza tipo/classe

Il guard `trgfn_contratti_utilities_guard_tipo_classe` si applica **solo su
`contratti_utilities`**, al momento del push, non sull'offerta. Sulla proposta
precontrattuale i dati arrivano gia' validati dall'istanza precontrattuale: duplicare
il guard sarebbe ridondante e causerebbe rifiuti su offerte in cui i dati sono ancora
incompleti o in fase di negoziazione.

---

### Push a contratto

Quando `fn_push_offerta_a_contratto` crea il contratto DRAFT, copia `offerte_commerciali_utilities`
→ `contratti_utilities` con una sostituzione 1:1 di `offerta_id` → `contratto_id`.
Il guard tipo/classe verra' eseguito in quel momento sul contratto.

---

{% include-markdown "signature-core.md" %}

---
