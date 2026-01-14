## 📘 Documentazione Concettuale – Tabella `catalogo.articoli_componenti`

> 👀 **Vedi anche**
>
> **Approfondimento Tabelle**
> • [`catalogo.articoli`](/dbzero/catalogo/tabelle/articoli)   
> • [`catalogo.note`](/dbzero/catalogo/tabelle/note)   
> • *(opz.)* [`catalogo.unita_misura`](/dbzero/catalogo/tabelle/unita_misura)   
>
> **Approfondimento Trigger/Funzioni**
> • [`dbops.trgfn_tx_id_managed`](/dbzero/dbops/funzioni/trgfn_tx_id_managed)   
> • [`dbops.trgfn_child_requires_active_parent`](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent)   
> • [`script.trgfn_audit_data_user_generic`](/dbzero/script/funzioni/trgfn_audit_data_user_generic)   
> • [`script.trgfn_storico_generic`](/dbzero/script/funzioni/trgfn_storico_generic)  

---

### 🎯 Scopo Principale

(latest review 13-01-26)
`catalogo.articoli_componenti` rappresenta la **distinta base (BoM)** lato **vendita**, con **versionamento temporale**: ogni riga lega un **prodotto** a un **componente** con una finestra di validità (`valid_from`..`valid_to`).

Supporta:

* **quantità/coefficiente** per unità di prodotto (`coeff_qta`),
* **inclusione nel calcolo quantità** (`partecipa_qta`),
* **obbligatorietà** del componente (`obbligatorio`),
* **attivazione/disattivazione logica** (`attivo`) e **storicizzazione**.

---

### 🔗 Relazioni

| Tipo      | Tabella ↔ Campo                           | Descrizione                                                                           |
| --------- | ----------------------------------------- | ------------------------------------------------------------------------------------- |
| FK →      | `catalogo.articoli(id)` ← `prodotto_id`   | Articolo **padre** (prodotto)                                                         |
| FK →      | `catalogo.articoli(id)` ← `componente_id` | Articolo **figlio** (componente)                                                      |
| (trigger) | `catalogo.articoli`                       | Il componente e il prodotto referenziati devono essere **attivi** (guard via trigger) |

> **Nota:** `chk_articoli_componenti_no_selfref` impedisce **self‑reference** (padre=figlio).

---

### 🧱 Struttura logica (campi chiave)

* **Identità**: `id UUID` (PK)
* **Legame**: `prodotto_id UUID` (FK), `componente_id UUID` (FK)
* **Versioning**: `valid_from DATE` (**obbligatorio**), `valid_to DATE` *(NULL = infinito)*
* **Quantità & logica**: `coeff_qta NUMERIC(18,6) ≥ 0`, `partecipa_qta BOOLEAN`, `obbligatorio BOOLEAN`
* **Note**: `note_target_tipo`, `note_id` (FK composita verso `catalogo.note`)
* **Meta & Audit**: `meta JSONB`, `attivo`, `storicizza`, `tx_id`, `user_*`, `data_*`

---

### 🚦 Vincoli & Regole

* **Univocità puntuale**: `UNIQUE (prodotto_id, componente_id, valid_from)` → identifica l’**inizio versione**.
* **Date coerenti**: `valid_to IS NULL OR valid_to > valid_from`.
* **Quantità non negative**: `coeff_qta ≥ 0`.
* **No self‑reference**: `prodotto_id <> componente_id`.
* **Nessuna sovrapposizione nel tempo** per la **stessa coppia** `(prodotto, componente)`:
  `EXCLUDE USING gist (prodotto_id WITH =, componente_id WITH =, daterange(valid_from, COALESCE(valid_to, 'infinity'), '[]') WITH &&)`
  ➜ **richiede estensione** `btree_gist` per supportare `uuid` su GiST.
* **Parent attivi**: sia `prodotto_id` sia `componente_id` devono puntare ad articoli **attivi** (policy ATTIVO: require sul figlio).
* **Solo componente**: un articolo con `is_solo_componente=true` non può essere usato come `prodotto_id`.

---

### 🔍 Indicizzazione

* `ix_articoli_componenti_prodotto_from_to (prodotto_id, valid_from, valid_to)` → espansione distinta per prodotto e per data.
* `ix_articoli_componenti_componente_from_to (componente_id, valid_from, valid_to)` → “dove è usato” il componente.
* **Exclusion** GiST per prevenire **overlap** temporali (vedi sopra) + indice `ix_articoli_componenti_no_overlap_gist`.

---


### 🔎 Query tipiche

**1) Distinta valida per una data**

```sql
SELECT ac.*
FROM catalogo.articoli_componenti ac
WHERE ac.prodotto_id = :prodotto
  AND ac.attivo = true
  AND ac.valid_from <= :data_rif
  AND (ac.valid_to IS NULL OR ac.valid_to >= :data_rif)
ORDER BY ac.obbligatorio DESC, ac.coeff_qta DESC, ac.valid_from DESC;
```

**2) Dove viene usato un componente (oggi)**

```sql
SELECT p.codice AS prodotto, c.codice AS componente
FROM catalogo.articoli_componenti ac
JOIN catalogo.articoli p ON p.id = ac.prodotto_id
JOIN catalogo.articoli c ON c.id = ac.componente_id
WHERE ac.componente_id = :componente
  AND ac.attivo = true
  AND ac.valid_from <= CURRENT_DATE
  AND (ac.valid_to IS NULL OR ac.valid_to >= CURRENT_DATE)
ORDER BY p.codice;
```

**3) Diagnostica: possibili overlap (se l'estensione manca o è stata rimossa)**

```sql
SELECT ac1.id AS id1, ac2.id AS id2
FROM catalogo.articoli_componenti ac1
JOIN catalogo.articoli_componenti ac2
  ON ac1.prodotto_id = ac2.prodotto_id
 AND ac1.componente_id = ac2.componente_id
 AND ac1.id <> ac2.id
 AND daterange(ac1.valid_from, COALESCE(ac1.valid_to, 'infinity'), '[]') &&
     daterange(ac2.valid_from, COALESCE(ac2.valid_to, 'infinity'), '[]');
```

---

### 🧭 Best practice

* **Versioning esplicito**: apri una **nuova riga** con nuovo `valid_from` per variare `coeff_qta` o altri attributi; **non** aggiornare in‑place se vuoi tracciare la storia.
* **Controlli applicativi**: impedisci componenti su articoli che **non sono** `is_composito=true` (vincolo applicativo opzionale).
* **Chiusure automatiche**: se vuoi evitare “open‑ended” duplicati, implementa una procedura che chiude la riga precedente (imposta `valid_to`) quando inserisci una nuova versione.
* **Estensione `btree_gist`**: assicurati che sia installata (`CREATE EXTENSION IF NOT EXISTS btree_gist;`).
* **Storicizza** le modifiche e usa `attivo=false` per dismissioni logiche.

---

### 🧩 Esempio realistico (distinta base)

Esempio: prodotto **SEDIA** con componenti **piedi**, **schienale**, **sedile**, **viti**.

In `catalogo.articoli` esistono:

* `SEDIA` (prodotto finito)
* `PIEDE_SX`, `PIEDE_DX`, `PIEDE_POST_SX`, `PIEDE_POST_DX`
* `SCHIENALE`
* `SEDILE`
* `VITE_M6`

In `catalogo.articoli_componenti` avrai una riga per ciascun componente:

* `prodotto_id = SEDIA`, `componente_id = PIEDE_SX`, `coeff_qta = 1`
* `prodotto_id = SEDIA`, `componente_id = PIEDE_DX`, `coeff_qta = 1`
* `prodotto_id = SEDIA`, `componente_id = PIEDE_POST_SX`, `coeff_qta = 1`
* `prodotto_id = SEDIA`, `componente_id = PIEDE_POST_DX`, `coeff_qta = 1`
* `prodotto_id = SEDIA`, `componente_id = SCHIENALE`, `coeff_qta = 1`
* `prodotto_id = SEDIA`, `componente_id = SEDILE`, `coeff_qta = 1`
* `prodotto_id = SEDIA`, `componente_id = VITE_M6`, `coeff_qta = 8`

---

### 🧩 Esempio realistico (utility gas)

Esempio: prodotto **GAS_FACILE** composto da **MATERIA_PRIMA**, **QVD** e **SPREAD**.

In `catalogo.articoli` esistono:

* `GAS_FACILE` (prodotto/servizio finale)
* `MATERIA_PRIMA`
* `QVD`
* `SPREAD`

In `catalogo.articoli_componenti` avrai una riga per ciascun componente:

* `prodotto_id = GAS_FACILE`, `componente_id = MATERIA_PRIMA`, `coeff_qta = 1`
* `prodotto_id = GAS_FACILE`, `componente_id = QVD`, `coeff_qta = 1`
* `prodotto_id = GAS_FACILE`, `componente_id = SPREAD`, `coeff_qta = 1`

---

### 🕒 Esempio utilizzo temporale

Se la composizione cambia nel tempo, si inserisce **una nuova riga** con un nuovo
`valid_from` e si chiude la precedente con `valid_to`.

Esempio: la quota **SPREAD** aumenta dal 2026-03-01.

* Versione attuale:
  * `prodotto_id = GAS_FACILE`, `componente_id = SPREAD`, `coeff_qta = 1`, `valid_from = 2026-01-01`, `valid_to = 2026-02-28`
* Nuova versione:
  * `prodotto_id = GAS_FACILE`, `componente_id = SPREAD`, `coeff_qta = 1.2`, `valid_from = 2026-03-01`, `valid_to = NULL`

---

### Diagramma ER relazioni (focus BoM)

```mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%
erDiagram
    articoli ||--o{ articoli_componenti : ha_componenti
    articoli ||--o{ articoli_componenti : e_componente_di
```
---

{% include-markdown "signature-core.md" %}

---
