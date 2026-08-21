## 📘 Documentazione Concettuale – Tabella `magazzino.reservations`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti)
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Prenotazioni di stock** per ordini e ordini di lavoro: merce ancora in giacenza ma già
promessa a qualcuno.

Servono a rispondere a «quanto ne ho **davvero** disponibile», che non è la giacenza: è la
giacenza meno gli impegni.

---

### ⭐ Il legame al documento è polimorfo — e "manuale"

`doc_schema`, `doc_table`, `doc_id`: la prenotazione punta a un documento qualsiasi tramite
schema, tabella e id, senza FK.

È necessario — gli ordini di vendita e gli ODL stanno in tabelle diverse — ma va saputo:
**nessun vincolo garantisce che quel documento esista**, e cancellandolo la prenotazione resta
orfana senza che nulla lo segnali.

⚠️ Il progetto ha altrove un meccanismo di sorgente polimorfa più strutturato
(`config.sorgenti` + `sorgente_tipo_id` + `key_selector`). Questa tabella **non lo usa**: se
il magazzino verrà attivato, allineare i due modelli è una decisione da prendere — averne due
è la premessa perché divergano.

---

### Gli stati

`stato_reservation` nasce `'planned'`. È una stringa con default, non una FK a un vocabolario:
gli stati possibili non sono dichiarati da nessuna parte se non nel codice che li scrive.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
