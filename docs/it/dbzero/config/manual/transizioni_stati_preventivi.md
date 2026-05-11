## 📘 Documentazione Concettuale – Tabella `config.transizioni_stati_preventivi`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> [config.transizioni_stati_pratiche](/dbzero/config/tabelle/transizioni_stati_pratiche)
> [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
>
Approfondimento funzioni:
>
[vendite.fn_cambia_stato_preventivo](/dbzero/vendite/funzioni/fn_cambia_stato_preventivo)

---
### 🎯 Scopo Principale
(latest review 03-04-2026)
`config.transizioni_stati_preventivi` definisce la **matrice delle transizioni ammesse**
tra gli stati del preventivo vendita. Pattern identico a `config.transizioni_stati_pratiche`.

La funzione `vendite.fn_cambia_stato_preventivo` consulta questa tabella per validare
ogni transizione di stato, rendendo le regole configurabili senza rilasciare codice.

---

### Matrice transizioni configurata

| id | Da | A | Descrizione |
|----|----|---|-------------|
| 1 | DRAFT (1) | EMESSO (2) | Emissione preventivo |
| 2 | DRAFT (1) | ANNULLATO (9) | Cancellazione bozza |
| 3 | EMESSO (2) | ACCETTATO (4) | Accettazione cliente |
| 4 | EMESSO (2) | RIFIUTATO (5) | Rifiuto cliente |
| 5 | EMESSO (2) | SCADUTO (7) | Scadenza validita' |
| 6 | EMESSO (2) | ANNULLATO (9) | Annullamento operatore |
| 7 | ACCETTATO (4) | ANNULLATO (9) | Annullamento post-accettazione |

```text
DRAFT ---------> EMESSO ---------> ACCETTATO ---------> (push commessa / genera pratica)
  |                |                   |
  |                |                   +-> ANNULLATO (guard commessa attiva)
  |                +-> RIFIUTATO
  |                +-> SCADUTO
  |                +-> ANNULLATO
  +-> ANNULLATO
```

---

### Vincoli

| Vincolo | Tipo | Descrizione |
|---------|------|-------------|
| `uq_transizioni_stati_preventivi` | UNIQUE | `(stato_da_id, stato_a_id)` — una sola regola per coppia |
| `ck_transizioni_stati_prev_da_diverso_a` | CHECK | Lo stato di partenza deve essere diverso da quello di arrivo |
| `ck_transizioni_stati_prev_meta_ui` | CHECK | Transizioni manuali (`meta->>'manuale' != false`) devono avere `action_key` e `label_key` nel JSONB `meta` |

---

### Campo `meta` — contratto obbligatorio

Il campo `meta jsonb NOT NULL DEFAULT '{}'` porta i metadati UI letti da
`script.fn_available_actions_preventivo`. Il contratto e' **obbligatorio** per le
transizioni manuali ed e' imposto dal CHECK `ck_transizioni_stati_prev_meta_ui`.

| Chiave | Tipo | Obbligatoria | Descrizione |
|--------|------|:---:|---|
| `action_key` | `text` | Sì (manuale) | Chiave semantica dell'azione letta dal FE (es. `emetti`, `annulla`) |
| `label_key` | `text` | Sì (manuale) | Chiave i18n per il label del bottone Vue (`$t(label_key)`) |
| `severity` | `text` | No | Severity PrimeVue: `info` / `success` / `danger` |
| `icon` | `text` | No | Classe PrimeIcons (es. `pi pi-send`) |
| `requires_confirm` | `boolean` | No | `true` → il drawer mostra dialog di conferma prima di eseguire |
| `manuale` | `boolean` | No | `false` = transizione automatica (job/trigger), esclusa dalla lista UI. Default: `true` |

**Regola**: ogni volta che si aggiunge una riga a questa tabella, aggiornare anche il seed
`80_data/changelog/20260430-60-update-transizioni-stati-preventivi-meta-ui-mctit.yaml`
(`runOnChange: true`) con l'UPDATE corrispondente. Il CHECK blocca INSERT/UPDATE con meta
incompleto sulle transizioni manuali, rendendo immediatamente visibile un seed dimenticato.

---

### Regole operative

* **Attivo**: il flag `attivo` consente di disabilitare una transizione senza eliminarla.
* **Guard aggiuntivi**: la funzione `fn_cambia_stato_preventivo` applica guard supplementari
  non gestibili dalla sola matrice (es. righe attive per emissione, commessa attiva per annullamento).
* **Meta obbligatorio**: il campo `meta` NON e' piu' opzionale per le transizioni manuali.
  Vedi sezione "Campo meta" sopra e CHECK `ck_transizioni_stati_prev_meta_ui`.

---

### Esempio d'uso

```sql
-- Transizioni ammesse dallo stato corrente di un preventivo
SELECT sdp_a.codice AS stato_destinazione, sdp_a.descrizione
FROM config.transizioni_stati_preventivi t
JOIN config.stati_doc_preventivi sdp_a ON sdp_a.id = t.stato_a_id
WHERE t.stato_da_id = (SELECT stato_doc_preventivo_id FROM vendite.preventivi WHERE id = 42)
  AND t.attivo IS TRUE;
```

---

{% include-markdown "signature-core.md" %}
