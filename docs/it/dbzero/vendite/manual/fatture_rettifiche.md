# 📘 Documentazione Concettuale – Tabella `vendite.fatture_rettifiche`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)
> • [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze)

---

### 🎯 Scopo Principale

`vendite.fatture_rettifiche` modella il **legame N:N** fra **documenti rettificanti** (es. note di credito/debito) e **documenti rettificati** (fatture originarie).

Obiettivi:

* mantenere **storico e tracciabilità** delle rettifiche anche in scenari complessi (più note su una fattura, o una nota che rettifica più fatture);
* semplificare **stampe, controlli e riconciliazioni** evitando campi di riferimento sparsi sulle righe.

---

### Collocazione nel flusso documentale

1. **Generazione rettifica** (es. nota credito): il motore crea la testata su `vendite.fatture` e le eventuali righe (`vendite.fatture_righe`).
2. **Associazione**: per ogni documento originario da rettificare, viene creato un **link** su `vendite.fatture_rettifiche`.
3. **Verifica**: controlli di coerenza economica e fiscale (totali, stati, esercizi) a livello applicativo/trigger.

---

### Campi chiave (semantica)

* `fattura_id` → **documento rettificante** (tipicamente NC/ND). FK `vendite.fatture(id)`.
* `rettificata_id` → **documento rettificato** (fattura originaria). FK `vendite.fatture(id)`.
* Audit: `data_insert`, `user_insert`, `data_update`, `user_update` secondo convenzioni Zero ERP.

> La tabella **non** contiene importi: gli effetti economici sono nella nota, mentre questo legame abilita tracciabilità e navigazione.

---

### Vincoli, indici e coerenze

* **Univocità coppia**: `UNIQUE (fattura_id, rettificata_id)` evita duplicati.
* **FK con CASCADE**: se un documento viene rimosso, i link collegati sono eliminati automaticamente.
* **Indice operativi**:

  * `ix_fatture_ret_fattura (fattura_id)` → “tutte le rettifiche fatte da questo documento”.
  * `ix_fatret_rettificata (rettificata_id)` → “tutte le rettifiche ricevute da questa fattura”.
* **(Consigliato)**: `CHECK (fattura_id <> rettificata_id)` per impedire auto‑riferimenti.
* **(Opzionale)**: regola sul **tipo documento** del rettificante (es. consentire solo NC/ND) via trigger o policy.

---

### Esempi d’uso (query applicative)

```sql
-- 1) Documenti che rettificano una fattura (entrate)
SELECT fr.fattura_id   AS doc_rettificante,
       f.numero,
       f.data
FROM vendite.fatture_rettifiche fr
JOIN vendite.fatture f ON f.id = fr.fattura_id
WHERE fr.rettificata_id = :fattura_orig
ORDER BY f.data, f.id;
```

```sql
-- 2) Documenti rettificati da una nota (uscite)
SELECT fr.rettificata_id AS doc_rettificato,
       f.numero,
       f.data
FROM vendite.fatture_rettifiche fr
JOIN vendite.fatture f ON f.id = fr.rettificata_id
WHERE fr.fattura_id = :nota
ORDER BY f.data, f.id;
```

```sql
-- 3) Inserimento link con protezione anti‑duplicato
INSERT INTO vendite.fatture_rettifiche (fattura_id, rettificata_id)
VALUES (:id_nota, :id_fattura)
ON CONFLICT ON CONSTRAINT uq_fatture_rettifiche_pair DO NOTHING;
```

---

### Best practice operative

* **Coerenza economica**: la somma delle rettifiche non deve superare l’importo rettificato (per NC parziali). Applicare controlli a livello DB o servizio.
* **Coerenza di stato**: vietare rettifiche su documenti **annullati/bozze** (se lo stato è gestito in `vendite.fatture`).
* **Temporalità**: rispettare blocchi d’esercizio/periodo contabile; valutare vincoli deferrable.
* **Idempotenza**: il legame è **deterministico** e privo di meta‑import; l’idempotenza va gestita sulle note (`uid`, `sorgente_*`).

---

### Relazioni (Mermaid)

```mermaid
erDiagram
  vendite_fatture ||--o{ vendite_fatture_rettifiche : rettifica
  vendite_fatture {
    BIGINT id PK
    ...
  }
  vendite_fatture_rettifiche {
    BIGINT id PK
    BIGINT fattura_id FK
    BIGINT rettificata_id FK
  }
```

---

### Integrazione backend/API (DRF – suggerimenti)

* **Endpoint di lettura** per:

  * by `rettificata_id` → elenco note che rettificano la fattura;
  * by `fattura_id` → elenco documenti rettificati dalla nota.
* **Policy**: POST consentito solo a servizi di emissione rettifiche; DELETE ammesso solo in **stato non numerato** (se previsto.
* **Serializer**: esporre info minime (`fattura_id`, `rettificata_id`, `data_insert`) + link HATEOAS alla testata.

---

### 📘 Note progettuali

* Il **dato “causale rettifica”** (testo) se necessario va lasciato alla nota di credito (testata o riga), non qui.
* Per reporting, utile una **vista** che arricchisca i link con numero/data e informazioni di stato delle testate.
* Le **stampe** di fattura possono mostrare le rettifiche collegate (entranti/ uscenti) tramite semplici join.

---

### Ruolo nel sistema

`vendite.fatture_rettifiche` è il **punto unico** per capire “**chi rettifica chi**”, mantenendo il modello pulito:

* relazioni **chiare e normalizzate**;
* query semplici e performanti grazie agli indici dedicati;
* possibilità di aggiungere **regole di business** senza appesantire testata/righe.

{% include-markdown "signature-core.md" %}
