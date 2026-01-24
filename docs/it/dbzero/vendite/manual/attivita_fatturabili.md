## 📘 Documentazione Concettuale – Tabella `vendite.attivita_fatturabili`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)    
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)   
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)   
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)   
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)   
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)   
> • [vendite.note](/dbzero/vendite/tabelle/note)   

---

### 🎯 Scopo Principale

(latest review 21-01-2026)
`vendite.attivita_fatturabili` è il **registro centrale delle prestazioni/attività da fatturare** (time & material, canoni, una‑tantum, letture/consumi valorizzati, import batch, ecc.).
Ogni riga rappresenta **una voce fatturabile** riferita a un *articolo/servizio*, a una *istanza tecnica/utility* e, opzionalmente, a un *billing account*.
Queste righe sono **pre‑documentali**: quando il ciclo di fatturazione le preleva, diventano **righe di fattura** (`vendite.fatture_righe`).

Obiettivi principali:

* **Accentramento** della sorgente di verità per tutto ciò che va fatturato.
* **Controllo del periodo di competenza** (mensile o puntuale) per stabilire **quando** fatturare.
* **Tracciabilità** dallo *stato bozza → approvato → fatturato* con blocchi anti‑doppia fatturazione.
* **Idempotenza** degli import/import batch tramite coppia (`sorgente_tipo_id`, `sorgente_uid`).

---

### 🧭 Collocazione nel flusso di fatturazione

1. **Acquisizione**: le attività arrivano da input manuali, sistemi esterni, motori di calcolo o letture; vengono registrate qui con `data_attivita`, `quantita`, riferimenti a `articolo_id`, `istanza_utility_id`, `billing_account_id` (opz.).
2. **Normalizzazione/validazione** (trigger): allineamento della competenza mensile, coerenze su sorgente, BA e istanza.
3. **Approvazione**: il flag `approvato` abilita l’eleggibilità al prelievo.
4. **Selezione per fatturazione**: il motore estrae le righe **non fatturate**, **non sospese**, **non posticipate** e **in competenza** (vedi paragrafo successivo).
5. **Generazione documento**: le righe selezionate generano entries su `vendite.fatture_righe` e valorizzano `fattura_riga_id`; `fatturato = true`.
6. **Chiusura batch**: `lock_in_fatturazione` e `lock_batch_id` garantiscono isolamento durante la corsa.

---

### 📅 Periodo di competenza & regole di fatturabilità

* `competenza_mese` → **competenza mensile**; se valorizzata deve essere il **1° giorno del mese** (es. `YYYY‑MM‑01`).

  * **Regola**: non fatturare **prima** di quel mese.
* `competenza_data` → competenza **puntuale** alternativa (es. attività a data precisa).
* `posticipa_al` → **rimanda** l’eleggibilità al prelievo a una data futura.
* `sospesa = true` → riga **temporaneamente esclusa** dai prelievi, a prescindere dalla competenza.

Tipico filtro di eleggibilità per il motore:

* `approvato = true`
* `fatturato = false`
* `sospesa = false`
* `posticipa_al IS NULL OR posticipa_al <= data_fatturazione`
* rispetto della competenza (`competenza_mese` <= mese fatturazione **oppure** `competenza_data` <= data fatturazione).

---

### 🔑 Campi chiave (uso applicativo)

* **Identificazione & riferimenti**:
  `articolo_id` (servizio/voce), `istanza_utility_id` (punto tecnico), `billing_account_id` (opz. intestazione economica).
* **Dati attività**:
  `data_attivita`, `quantita` (> 0),  `meta` (estensioni specifiche: matricole, rilevazioni, tariffa applicata, ecc.).
* **Competenza & gating**:
  `competenza_mese`, `competenza_data`, `posticipa_al`, `sospesa`.
* **Stato di processo**:
  `approvato`, `fatturato`, `lock_in_fatturazione`, `lock_batch_id`, `fattura_riga_id` (consumo su documento).
* **Idempotenza import**:
  `sorgente_tipo_id`, `sorgente_uid` (vincolo unico parziale per evitare duplicazioni dai sistemi esterni).
* **Governance**:
  `tx_id`, `storicizza`, `user_*`, `data_*`.
* **Economiche & registro**:
  `registro_id` (registro di fatturazione), `valuta_id`, `prezzo_unitario` (snapshot economico).
  In fase di alimentazione il registro segue l’ordine: sorgente → utility (fallback).
* **Misure & dettaglio sorgente**:
  `sorgente_riga` (riferimento tecnico riga sorgente), `uom_id` (u.m. base), `qta_operativa` (quantita operativa), `uom_operativa_id` (u.m. operativa), `factor_to_base` (fattore conversione verso base).

---

### 🔒 Vincoli, indici e trigger (logica)

* **Vincoli**:

  * `chk_attivita_competenza_mese_primo`: il giorno di `competenza_mese` deve essere **1**.
  * `chk_attivita_competenza_data_logica`: `competenza_data` ≥ `data_attivita` (se presente).
* **FK principali**:

  * `articolo_id` → `catalogo.articoli`.
  * `billing_account_id` → `anagrafiche.billing_account` (nullable, `ON DELETE SET NULL`).
  * `istanza_utility_id` → `anagrafiche.istanze_utilities`.
  * `sorgente_tipo_id` → `config.sorgenti`.
* **Indici utili al motore**:

  * `ix_attivita_articolo_flags` (articolo + flag `approvato`/`fatturato`).
  * `ix_attivita_billing_competenza` (BA + competenza mensile).
  * `ix_attivita_istanza_data` (istanza + data attività).
  * `ix_attivita_fatturabili_posticipa_sospesa`, `ix_attivita_fatturabili_lock`, `ix_attivita_fatturabili_fattura_riga_id`.
  * **Unique parziale** `uq_attivita_fatturabili_v_sorgente_fk` su (`sorgente_tipo_id`, `sorgente_uid`) *WHEN* `sorgente_tipo_id IS NOT NULL` → **idempotenza import**.
* **Trigger**:

  * `trg_attivita_fatturabili_normalize_ins_upd` → **normalizza** `competenza_mese` al 1° del mese (YYYY‑MM‑01) e, se `sorgente_tipo_id` è valorizzato, imposta `sorgente_riga` a `0` quando mancante.
  * `trg_attivita_fatturabili_a10_guard_ba_coerenza_ins_upd` → **coerenze BA/istanza/articolo** (regole di dominio).
  * `trg_attivita_fatturabili_a10_guard_fonte_ins_upd` → **validazione sorgente** (`sorgente_tipo_id`/`sorgente_uid`).
  * `trg_attivita_fatturabili_a10_guard_fatturato_upd_dlt` → **fail‑fast**: blocca update/delete se già collegate a fattura.

---

### 🧪 Esempi d’uso (query applicative)

```sql
-- 1) Selezione righe eleggibili per il ciclo del mese M
SELECT *
FROM vendite.attivita_fatturabili a
WHERE a.approvato
  AND NOT a.fatturato
  AND NOT a.sospesa
  AND (a.posticipa_al IS NULL OR a.posticipa_al <= :data_fatturazione)
  AND (
    (a.competenza_mese IS NOT NULL AND a.competenza_mese <= date_trunc('month', :data_fatturazione)) OR
    (a.competenza_mese IS NULL AND (a.competenza_data IS NULL OR a.competenza_data <= :data_fatturazione))
  );

-- 2) Marcatura come fatturato (eseguita dal motore dopo creazione riga fattura)
UPDATE vendite.attivita_fatturabili
SET fatturato = true,
    fattura_riga_id = :fattura_riga_id,
    user_update = current_user,
    data_update = now()
WHERE id = ANY(:ids);
```

---

### ✅ Best practice operative

* Imporre `approvato = true` come prerequisito di fatturabilità (workflow di approvazione esplicito).
* Usare `posticipa_al` per rinviare selettivamente righe **senza** perdere la tracciabilità del motivo (`exclude_reason`).
* Evitare update manuali su righe già collegate a `fattura_riga_id`; i trigger **bloccano** modifiche distruttive.
* Per import esterni, popolare **sempre** `sorgente_tipo_id` + `sorgente_uid` per ottenere **idempotenza** e facilitare il retry.

---

### 👓 Importanza nel sistema

Questa tabella è il **cuore del ciclo di fatturazione**: tutte le voci da fatturare convergono qui, vengono qualificate per **quando** fatturare (competenza, posticipo, sospensione) e, una volta prelevate, diventano **dettaglio di fattura**.
La qualità e la coerenza dei dati in `vendite.attivita_fatturabili` determinano direttamente **completezza, correttezza e ripetibilità** dei documenti emessi.
