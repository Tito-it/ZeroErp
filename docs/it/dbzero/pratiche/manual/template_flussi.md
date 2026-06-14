## 📘 Documentazione Concettuale – Tabella `pratiche.template_flussi`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione)
> [pratiche.handler_flussi](/dbzero/pratiche/tabelle/handler_flussi)
> [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti)
> [pratiche.template_flussi_canali](/dbzero/pratiche/tabelle/template_flussi_canali)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)

---
### 🎯 Scopo Principale
La tabella `pratiche.template_flussi` definisce i **template degli step di workflow** per ciascun tipo_prestazione. Ogni template descrive un flusso tipo: sequenza di esecuzione, obbligatorieta', direzione, handler automatico opzionale e parametri di configurazione.

---

### Ruolo nel processo

* Quando viene creata una pratica di un dato tipo, i flussi vengono istanziati dai template configurati.
* I template definiscono l'**ordine** (`sequenza`), l'**obbligatorieta'**, la **direzione** e la **ripetibilita'** del flusso.
* I template con `handler_id NOT NULL` sono automatizzati; quelli con `handler_id NULL` sono manuali.
* I prerequisiti tra template sono definiti nella tabella `template_flussi_prerequisiti` (DAG).
* La regola di **ripetibilita'** (D3) governa quante istanze dello stesso template possono nascere nella stessa pratica: enforcement a DB nel guard `trg_flussi_a10_guard_ripetibilita_ins` ([fn_check_ripetibilita_flusso](/dbzero/pratiche/funzioni/fn_check_ripetibilita_flusso)).
* L'**obbligatorieta'** vincola la chiusura della pratica (D4): un template `obbligatorio = true` non completato e ancora percorribile blocca la transizione a CHIUSA ([fn_check_chiusura_pratica](/dbzero/pratiche/funzioni/fn_check_chiusura_pratica)). Il ramo morto di un bivio non blocca.
* La **chiusura guidata dal workflow** (`chiude_pratica`): la pratica si chiude in automatico al completamento dei flussi, non con un'azione manuale. Se il tipo prestazione ha un template `chiude_pratica = true` (il "flusso di chiusura", max uno per tipo), la pratica passa a CHIUSA al completamento di quel flusso ([trgfn_flussi_autochiusura_pratica](/dbzero/pratiche/funzioni/trgfn_flussi_autochiusura_pratica)); altrimenti, se il tipo ha almeno un obbligatorio, si auto-chiude quando non restano obbligatori bloccanti. Un tipo senza obbligatori e senza flusso di chiusura non ha un percorso di chiusura deterministico (non si chiude).

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `sequenza` | INTEGER DEFAULT 0. Ordine di esecuzione nel workflow. |
| `obbligatorio` | BOOLEAN DEFAULT false. Se true, il flusso deve essere completato per chiudere la pratica — solo se ancora percorribile: il ramo morto di un bivio non blocca (guard `trg_pratiche_a10_guard_chiusura_flussi_upd`). |
| `chiude_pratica` | BOOLEAN DEFAULT false. true = "flusso di chiusura": al suo completamento la pratica passa a CHIUSA (chiusura guidata dal workflow). Max uno per tipo prestazione (`uq_template_flussi_chiusura`) e implica `obbligatorio = true` (`chk_template_flussi_chiusura_obbligatorio`). Il suo completamento e' ammesso solo a percorso obbligatorio concluso (guard `trg_flussi_a10_guard_chiusura_prematura_upd`). |
| `direzione` | VARCHAR(10) CHECK (ENTRATA, USCITA, INTERNA) DEFAULT 'INTERNA'. Caratterizza il flusso rispetto all'esterno: ENTRATA = dall'esterno verso il gestionale, USCITA = dal gestionale verso l'esterno, INTERNA = operazione interna. |
| `ripetibilita` | VARCHAR(20) CHECK (MAI, SE_NON_POSITIVO, SEMPRE) DEFAULT 'SE_NON_POSITIVO'. Regola di ripetibilita' delle istanze nella stessa pratica: `MAI` = una sola istanza non annullata (es. CONFERMA); `SE_NON_POSITIVO` = nuova istanza solo se l'ultima e' COMPLETATO con esito diverso da POSITIVO (un'istanza ancora aperta blocca — es. APPUNTAMENTO andato male si rifa'); `SEMPRE` = libera (es. contatto telefonico). |
| `handler_params` | JSONB DEFAULT '{}'. Parametri operativi passati all'handler Django in fase di esecuzione (es. `{"stampa_foglio": true, "invio_sms_conferma": true}`). Distinto da `meta` che contiene metadati generici. |

---

### Vincoli

* **UQ composito**: `(tipo_prestazione_id, codice)` — codice univoco per tipo_prestazione.
* **CHECK direzione**: solo valori ENTRATA, USCITA, INTERNA.
* **CHECK ripetibilita**: solo valori MAI, SE_NON_POSITIVO, SEMPRE.
* **FK handler_id nullable**: NULL = step manuale, NOT NULL = step automatizzato.

---

### Convenzioni

* Trigger standard applicati automaticamente da `dbops.fn_run_automations()`.
* `storicizza = true` per tracciamento modifiche alla configurazione.

---

{% include-markdown "signature-core.md" %}
