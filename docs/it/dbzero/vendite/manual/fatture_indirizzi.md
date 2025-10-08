## 📘 Documentazione Concettuale – Tabella `vendite.fatture_indirizzi`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)    
> • [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)    

---

### 🎯 Scopo Principale

`vendite.fatture_indirizzi` **semplifica la gestione degli indirizzi di fattura** e garantisce la **ristampa conforme** nel tempo tramite **snapshot** JSON dell’indirizzo al momento dell’emissione.

Per ogni fattura puoi memorizzare **al massimo un indirizzo per tipo** (es. fatturazione, spedizione, fornitura, residenza), evitando duplicazioni e mantenendo la storicità indipendente da successive modifiche anagrafiche.

---

### 🧭 Collocazione nel flusso

1. **Emissione/chiusura fattura** → il motore raccoglie gli indirizzi dai soggetti coinvolti e salva in `snapshot` i campi necessari (via, CAP, città, provincia, nazione, eventuale **email** di invio documento, ecc.).
2. **Stampe / invii** → le stampe e i canali di delivery leggono **solo** dallo snapshot, assicurando coerenza anche a distanza di tempo.
3. **Ristampa conforme** → eventuali variazioni anagrafiche **non** impattano le fatture già emesse.

---

### 🔑 Campi chiave (semantica)

* `fattura_id` → FK alla testata (`vendite.fatture`).
* `tipo_indirizzo_id` → FK al dominio dei tipi (`config.tipi_indirizzi`). Governa la funzione dell’indirizzo (fatturazione, spedizione, …).
* `snapshot jsonb` → **copia completa** dei dati indirizzo/email al momento dell’emissione (struttura flessibile).
* **Unicità per tipo**: vincolo `UNIQUE (fattura_id, tipo_indirizzo_id)`.

> Suggerimento di contenuto `snapshot`: `{ "ragsoc": "ABC S.p.A.", "via": "Via Roma, 1", "cap": "00100", "comune": "Roma", "prov": "RM", "nazione": "IT", "pec": "fatture@abcpec.it", "email": "billing@abc.it" }`

---

### 🔒 Vincoli, indici e trigger

* **PK**: `id`.
* **FK**:

  * `fattura_id` → `vendite.fatture(id)` (ON DELETE CASCADE).
  * `tipo_indirizzo_id` → `config.tipi_indirizzi(id)`.
* **UNIQUE**: uno per tipo per fattura.
* **Indice**: `ix_fatture_indir_fattura` per recupero rapido per fattura.
* **Trigger**: `trg_fatture_indirizzi_a10_ins_upd_only_allowed_tipi` → impedisce l’uso di **tipi non ammessi** per la fattura (lista governata dalla funzione `vendite.trgfn_fatture_indirizzi_only_allowed_tipi`).

---

### 🧪 Esempi d’uso (query applicative)

```sql
-- Recupera tutti gli indirizzi (per stampa/invio) di una fattura
SELECT fi.tipo_indirizzo_id, fi.snapshot
FROM vendite.fatture_indirizzi fi
WHERE fi.fattura_id = :fattura_id
ORDER BY fi.tipo_indirizzo_id;

-- Upsert dell'indirizzo di fatturazione (esempio)
INSERT INTO vendite.fatture_indirizzi (fattura_id, tipo_indirizzo_id, snapshot)
VALUES (:fattura_id, :tipo_fatturazione, :snapshot::jsonb)
ON CONFLICT (fattura_id, tipo_indirizzo_id)
DO UPDATE SET snapshot = EXCLUDED.snapshot,
              user_update = CURRENT_USER,
              data_update = now();
```

---

### ✅ Best practice operative

* **Snapshot completo**: includi anche canali di recapito (PEC/email) nello snapshot per garantire **prova di invio** coerente.
* **Normalizzazione in input**: valida e normalizza i campi prima di salvare (CAP, ISO-country, formati email/PEC).
* **Riduzione variabilità**: limita i **tipi consentiti** lato dominio/trigger, così UI e stampe restano semplici.
* **GDPR**: lo snapshot contiene dati personali → applica policy di **retention** e **access control** adeguate.

---

### 📘 Note progettuali

* L’uso di `jsonb` consente di adattare lo schema ai diversi formati indirizzo internazionali senza migrazioni strutturali.
* La **storicizzazione** è realizzata a livello documento: si fotografa l’indirizzo al momento dell’emissione; update successivi della fattura non dovrebbero alterare gli snapshot se non per correzioni eccezionali (policy di ruolo).
* In caso di **multi-tenant/reseller**, valuta l’inclusione nello snapshot di loghi/brand di stampa pertinenti all’indirizzo di invio.

---

### 👓 Ruolo nel sistema

`vendite.fatture_indirizzi` è il tassello che rende **deterministiche** le stampe e gli invii delle fatture: un solo indirizzo per tipo, formato flessibile, e **ristampe sempre conformi** indipendentemente dalle variazioni anagrafiche successive.
