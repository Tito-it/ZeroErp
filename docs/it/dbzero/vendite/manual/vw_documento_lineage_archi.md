## 📘 Documentazione Concettuale – Vista `vendite.vw_documento_lineage_archi`

> 👀 **Vedi anche**
>
> Approfondimento:
>
> [vendite.vw_documento_lineage_nodi](/dbzero/vendite/views/vw_documento_lineage_nodi)
> [vendite.vw_documento_lineage](/dbzero/vendite/views/vw_documento_lineage)
> [vendite.fn_documento_lineage](/dbzero/vendite/funzioni/fn_documento_lineage)
> [config/manual/sorgenti.md — Convenzione chiave sorgente](/dbzero/config/manual/sorgenti)

---

### 🎯 Scopo Principale

`vendite.vw_documento_lineage_archi` è il **grafo di genealogia/transito**
dei documenti vendite in forma **normalizzata**: **una riga per arco** (relazione
padre→figlio tra due documenti). È la base da cui derivano sia la summary
`vw_documento_lineage` sia il traversal `fn_documento_lineage`.

Nessun dato nuovo: tutti gli archi sono **ricostruiti** dal modello esistente. Il nodo
target è decorato (stato/fase/is_abortito) tramite `vw_documento_lineage_nodi`.

---

### 🔗 Gli archi (dal design §2)

| Arco | Da → A | Card. | Fonte |
|---|---|---|---|
| **A** | Preventivo → Ordine | 1:1 | `ordini.documento_origine_tipo='PREVENTIVO'/_id` (enum CHECK) |
| **B** | Preventivo → Commessa | 1:1 | `commesse_sorgenti` (sorgente PREVENTIVO) — `ruolo=ruolo_link` |
| **C** | Offerta → Contratto | 1:1 | `contratti.offerta_id` |
| **D** | Offerta → Ordine | 1:1 | `ordini.documento_origine_tipo='OFFERTA'/_id` |
| **E** | Ordine → Commessa | 1:1 | `commesse_sorgenti` (sorgente ORDINE_VENDITA) |
| **F** | Contratto → Commessa | **1:N** | `commesse_sorgenti` (sorgente CONTRATTO) |
| **G** | Commessa → Fattura | **1:N** | `attivita_fatturabili.fattura_riga_id` → `fatture_righe` → `fatture` |
| **H** | Ordine → DDT | **1:N** | `ddt.sorgente_uid`(uuid)=`ordini.uid` (tradotto a `ordini.id`) |
| **R** | DDT → Reso | **1:N** | `resi.sorgente_uid`(uuid)=`ddt.uid` — **ramo INVERSO** |

Le **colonne tipizzate dirette** in uuid (`ddt.sorgente_uid`, `resi.sorgente_uid`) sono
tradotte alla chiave nodo con un JOIN alla tabella target (regola brief §0 Q1). I tipi
sono risolti per `codice_interno` (§6d), mai id letterali.

---

### 📑 Campi chiave esposti

* **Sorgente arco**: `from_tipo_id`, `from_uid`, `from_codice`
* **Destinazione arco**: `to_tipo_id`, `to_uid`, `to_codice`
* **Stato del target** (dal nodo): `to_stato_codice_interno`, `to_fase`, `to_is_abortito`
* **`ruolo`**: `ROOT`/`COLLEGATO` dove esiste (archi da `commesse_sorgenti`), altrimenti NULL
* **`arco`**: lettera diagnostica `A`..`H`, `R`

---

### Esempio d'uso

```sql
-- Tutti gli archi uscenti/entranti di un documento (bidirezionale per costruzione).
SELECT arco, from_codice, to_codice, to_fase, ruolo
FROM vendite.vw_documento_lineage_archi
WHERE (from_tipo_id, from_uid) = (:tipo, :uid)     -- uscenti
   OR (to_tipo_id,   to_uid)   = (:tipo, :uid);    -- entranti
```

---

### Note operative

* **Arco R = flusso inverso** (merce che torna): compare nella genealogia, ma è
  **escluso dalla frontiera forward** della summary. Il reso non è mai un discendente
  forward di un altro documento.
* **Arco G**: `attivita_fatturabili.fattura_riga_id` (soft-link a `fatture_righe.id`,
  `NULL` = non ancora fatturata) → `DISTINCT` per non duplicare la coppia commessa→fattura.
* **`security_invoker=on`**: RLS emittente del chiamante (reloption da ri-specificare ad
  ogni `CREATE OR REPLACE`).
* Test: `db/pgtap/vendite/test-documento-lineage-v1.sql`.

---

{% include-markdown "signature-core.md" %}
