## 📘 Documentazione Concettuale – Tabella `pratiche.regole_generazione`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> * [pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione)
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) (campo `flusso_origine_id`)
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)

---

### 🎯 Scopo Principale

La tabella `pratiche.regole_generazione` configura le **regole di generazione cross-pratica**. Quando un flusso viene completato con un determinato esito, il sistema puo' generare automaticamente (o proporre la generazione manuale di) una nuova pratica di un dato tipo.

---

### 🧱 Ruolo nel processo

* Al completamento di un flusso (stato → COMPLETATO), il trigger `trgfn_flussi_generazione` (DB-5) cerca regole matching con `auto = true` e genera le pratiche target.
* Per regole con `auto = false`, l'operatore puo' attivare la generazione manualmente via API.
* La pratica generata ha `flusso_origine_id` impostato al flusso che l'ha generata — tracciabilita' completa.

---

### ⚙️ Colonne specifiche

| Colonna | Note |
|---------|------|
| `template_flusso_origine_id` | Il flusso che, al completamento, attiva la regola. |
| `tipo_prestazione_dest_id` | Il tipo di pratica da generare. |
| `template_flusso_dest_id` | Il flusso iniziale della pratica generata (nullable: NULL = nessun flusso auto). |
| `esito_richiesto` | CHECK (POSITIVO, NEGATIVO, QUALSIASI). Se NULL, la regola si attiva per qualsiasi esito. |
| `auto` | Se true, generazione automatica al completamento. Se false, solo su richiesta manuale. |

---

### 🔒 Vincoli

* **UQ composito**: `(template_flusso_origine_id, tipo_prestazione_dest_id, esito_richiesto)` — una sola regola per combinazione.
* **Indice parziale**: `uq_pratiche_regole_gen_origine_dest_null_esito` — evita duplicati quando `esito_richiesto IS NULL` (i NULL non sono considerati uguali dal UNIQUE standard).
* **FK `template_flusso_dest_id`**: ON DELETE SET NULL — se il template destinazione viene rimosso, la regola resta ma senza flusso iniziale.

---

### 💡 Esempio

| Regola | Significato |
|--------|-------------|
| Flusso "Sopralluogo" + esito POSITIVO → tipo "Allacciamento" (auto=true) | Al completamento positivo del sopralluogo, genera automaticamente una pratica di allacciamento |
| Flusso "Verifica" + esito NEGATIVO → tipo "Reclamo" (auto=false) | Se la verifica fallisce, l'operatore puo' scegliere di aprire un reclamo |

---

{% include-markdown "signature-core.md" %}
