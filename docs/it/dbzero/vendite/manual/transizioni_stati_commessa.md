## 📘 Documentazione Concettuale – Tabella `vendite.transizioni_stati_commessa`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)
> [vendite.commesse](/dbzero/vendite/tabelle/commesse)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [config.transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini)
>
Approfondimento funzioni:
>
[vendite.fn_cambia_stato_commessa](/dbzero/vendite/funzioni/fn_cambia_stato_commessa)
> [vendite.trgfn_commesse_guard_transizione](/dbzero/vendite/funzioni/trgfn_commesse_guard_transizione)

---
### 🎯 Scopo Principale
(rev 2026-06-07)
`vendite.transizioni_stati_commessa` definisce la **matrice delle transizioni ammesse**
tra gli stati della commessa. Pattern identico a `config.transizioni_stati_ordini` /
`config.transizioni_stati_preventivi`, ma collocato in schema `vendite` perché lì vive
la tabella stati di riferimento `vendite.stati_commessa` (a differenza di preventivi/ordini,
i cui stati sono in `config.stati_doc_*`).

La tabella chiude un buco di dominio: prima della sua introduzione le commesse erano l'unica
entità del ciclo documentale vendite **senza macchina di transizioni**. Conseguenza: la
commessa nasceva in `BOZZA` e nessun percorso la portava a `PRONTA_FATTURAZIONE`, lasciando
il ramo commessa→fattura dormiente.

Il trigger `vendite.trgfn_commesse_guard_transizione` consulta questa tabella per validare
ogni cambio di stato (`BEFORE UPDATE OF stato_commessa_id`), rendendo le regole configurabili
senza rilasciare codice.

---

### Matrice transizioni configurata

| id | Da | A | Note |
|----|----|---|------|
| 1 | BOZZA (1) | APERTA (2) | avvio commessa |
| 2 | BOZZA (1) | PRONTA_FATTURAZIONE (4) | salto del percorso push |
| 3 | BOZZA (1) | ANNULLATA (6) | |
| 4 | APERTA (2) | IN_ESECUZIONE (3) | |
| 5 | APERTA (2) | PRONTA_FATTURAZIONE (4) | salto del percorso push |
| 6 | APERTA (2) | ANNULLATA (6) | |
| 7 | IN_ESECUZIONE (3) | PRONTA_FATTURAZIONE (4) | |
| 8 | IN_ESECUZIONE (3) | ANNULLATA (6) | |
| 9 | PRONTA_FATTURAZIONE (4) | IN_ESECUZIONE (3) | riapertura pre-fattura |
| 10 | PRONTA_FATTURAZIONE (4) | CHIUSA (5) | |
| 11 | PRONTA_FATTURAZIONE (4) | ANNULLATA (6) | |

```text
BOZZA ---> APERTA ---> IN_ESECUZIONE ---> PRONTA_FATTURAZIONE ---> CHIUSA
  |          |             |                    |  ^
  |          |             |                    +--+  (riapertura PRONTA -> IN_ESECUZIONE)
  +----------+-------------+--------------------+--> ANNULLATA
  (salti diretti BOZZA/APERTA -> PRONTA_FATTURAZIONE: percorso push)
```

`CHIUSA` e `ANNULLATA` sono terminali (nessuna transizione in uscita). I salti diretti
`BOZZA/APERTA → PRONTA_FATTURAZIONE` servono al percorso push: una commessa nata da un
preventivo accettato è già confermata e non deve attraversare gli stati intermedi.

---

### Vincoli

| Vincolo | Tipo | Descrizione |
|---------|------|-------------|
| `uq_transizioni_stati_commessa` | UNIQUE | `(stato_da_id, stato_a_id)` — una sola regola per coppia |
| `ck_transizioni_stati_comm_da_diverso_a` | CHECK | Lo stato di partenza deve essere diverso da quello di arrivo |
| `ck_transizioni_stati_comm_meta_ui` | CHECK | Transizioni manuali (`meta->>'manuale' != false`) devono avere `action_key` e `label_key` nel JSONB `meta` |
| `fk_tsc_da` / `fk_tsc_a` | FK | `stato_da_id` / `stato_a_id` → `vendite.stati_commessa(id)` |

---

### Campo `meta` — contratto UI

Il campo `meta jsonb NOT NULL DEFAULT '{}'` porta i metadati UI per una futura
`fn_available_actions_commessa`. Il contratto è obbligatorio **solo** per le transizioni
manuali (imposto dal CHECK `ck_transizioni_stati_comm_meta_ui`).

| Chiave | Tipo | Obbligatoria | Descrizione |
|--------|------|:---:|---|
| `action_key` | `text` | Sì (manuale) | Chiave semantica dell'azione letta dal FE |
| `label_key` | `text` | Sì (manuale) | Chiave i18n per il label del bottone |
| `severity` | `text` | No | Severity PrimeVue: `info` / `success` / `danger` |
| `icon` | `text` | No | Classe PrimeIcons |
| `requires_confirm` | `boolean` | No | `true` → dialog di conferma prima di eseguire |
| `manuale` | `boolean` | No | `false` = transizione automatica/di processo, esclusa dalla lista UI. Default: `true` |

**Stato attuale del seed**: tutte le 11 righe hanno `meta = {"manuale": false}`. I metadati UI
(action_key/label_key/severity) sono rinviati a quando esisterà una UI commesse /
`fn_available_actions_commessa`; `manuale=false` soddisfa il CHECK e marca le transizioni
come di processo. All'introduzione della UI, arricchire il `meta` delle transizioni manuali.

---

### Regole operative

* **Attivo**: il flag `attivo` consente di disabilitare una transizione senza eliminarla.
* **Guard di dominio**: il trigger `trgfn_commesse_guard_transizione` applica una regola
  supplementare non gestibile dalla sola matrice: la transizione **verso `PRONTA_FATTURAZIONE`**
  è ammessa solo se la commessa ha almeno una riga `commesse_attivita` con
  `stato_approvazione = 'APPROVATA'` e `stato_emissione = 'NON_EMESSA'` (i due livelli —
  emittibilità testata e righe approvate — non possono divergere).
* **INSERT non vincolato**: il guard scatta solo su `UPDATE OF stato_commessa_id` (seed/import
  con stati diretti consentiti).

---

### Esempio d'uso

```sql
-- Transizioni ammesse dallo stato corrente di una commessa
SELECT sc_a.codice AS stato_destinazione, sc_a.descrizione
FROM vendite.transizioni_stati_commessa t
JOIN vendite.stati_commessa sc_a ON sc_a.id = t.stato_a_id
WHERE t.stato_da_id = (SELECT stato_commessa_id FROM vendite.commesse WHERE id = 42)
  AND t.attivo IS TRUE;
```

---

{% include-markdown "signature-core.md" %}
