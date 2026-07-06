## 📘 Documentazione Concettuale – Tabella `pratiche.template_flussi_avanzamento_proiezione`

> 👀 **Vedi anche**
>
Approfondimento oggetti collegati:
>
> [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [pratiche.fn_reconcile_sorgente](/dbzero/pratiche/funzioni/fn_reconcile_sorgente)
> [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)

---
### 🎯 Scopo Principale
(review 06-07-2026 — GUIDA D4, brief-db-guida-avanza-esito-proiettato)

Binding **dedicato e leggero** che dichiara *quando* un milestone (template step) deve
**avanzare automaticamente** perché il documento atteso ha raggiunto un **verdetto proiettato**.

È il tassello `G2` del meccanismo GUIDA: la `template_flussi.attende_sorgente_tipo_id` (`G1`)
dice *quale tipo documento* attende il milestone; questa tabella dice *con quale verdetto*
quel milestone si completa. Quando il documento proietta l'esito
(`pratiche.fn_stato_sorgente.esito`), il motore `pratiche.fn_reconcile_sorgente` porta il
milestone a **COMPLETATO** con quel verdetto.

**Additiva**: senza una riga qui, nessun avanzamento automatico (comportamento pre-GUIDA).

---

### Ruolo nel processo

* **Dedicata** apposta, separata da `pratiche.template_flussi_handler_eventi`: la semantica
  «avanza-su-proiezione» è diversa da «handler server-side su evento di flusso», e non si
  vuole sovraccaricare il `CHECK` sull'evento (`chk_tfhe_evento`).
* L'esito di **completamento** del milestone è **il verdetto proiettato** dal documento
  (mappatura 1:1: i vocabolari coincidono, nessun remap). `esito_richiesto` NULL = «qualsiasi
  verdetto».
* È **config di step versionata**: viene **copiata** da `pratiche.fn_copia_definizione` a
  fork / nuova-versione dell'edizione (ottavo blocco di copia figli).

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `template_flusso_id` | INTEGER NOT NULL. FK a `pratiche.template_flussi` (ON DELETE CASCADE). Il milestone che avanza. Deve essere uno step **non-DOMINIO** (guard). |
| `esito_richiesto` | VARCHAR(50) nullable. Verdetto richiesto per avanzare. NULL = qualsiasi verdetto. Se valorizzato ∈ 4 verdetti (CHECK). FK a `config.esiti_flussi_pratiche(codice)`. |
| `attivo` | BOOLEAN DEFAULT true. Solo i binding **attivi** contano per la mutua-esclusione e per il motore. |
| `meta` | JSONB DEFAULT '{}'. Metadati aggiuntivi. |

---

### Vincoli principali

| Vincolo | Tipo | Descrizione |
|---------|------|-------------|
| `chk_tfap_esito_verdetto` | CHECK | `esito_richiesto IS NULL OR IN ('POSITIVO','NEGATIVO','PARZIALE','NON_APPLICABILE')` — whitelist chiusa dei 4 verdetti (`is_verdetto=true`). |
| `uq_tfap_flusso_esito` | UNIQUE (NULLS NOT DISTINCT) | `(template_flusso_id, esito_richiesto)` — niente binding duplicati; due righe «qualsiasi verdetto» (NULL) sono un duplicato. |
| `fk_tfap_template_flusso` | FK | `template_flusso_id → pratiche.template_flussi(id)` ON DELETE CASCADE. |
| `fk_tfap_esito` | FK | `esito_richiesto → config.esiti_flussi_pratiche(codice)`. |

**Guard config-time** (`pratiche.trgfn_tfap_guard_compatibilita`, BEFORE INSERT/UPDATE):
il binding è ammesso **solo su step non-DOMINIO** e **non può coesistere** con un
`template_flussi_handler_eventi` `COMPLETATO` **attivo** sullo stesso step (mutua esclusione).

---

### Esempio d'uso

```sql
-- Il milestone APPROVAZIONE_CLIENTE avanza quando il preventivo atteso proietta POSITIVO.
INSERT INTO pratiche.template_flussi_avanzamento_proiezione (template_flusso_id, esito_richiesto)
VALUES (
  (SELECT id FROM pratiche.template_flussi
    WHERE codice = 'APPROVAZIONE_CLIENTE' AND tipo_prestazione_id = 9004),
  'POSITIVO'
);
```

---

{% include-markdown "signature-core.md" %}
