## 📘 Documentazione Concettuale – Tabella `pratiche.template_flussi`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione)
> [pratiche.handler_flussi](/dbzero/pratiche/tabelle/handler_flussi)
> [pratiche.azioni_ui](/dbzero/pratiche/tabelle/azioni_ui)
> [pratiche.template_flussi_handler_eventi](/dbzero/pratiche/tabelle/template_flussi_handler_eventi)
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
* I template con `azione_ui_id NOT NULL` **offrono un'attivita' UI interattiva** nel flusso (es. aprire il drawer di un preventivo dentro la pratica): la chiave e' risolta dal registry frontend ([azioni_ui](/dbzero/pratiche/tabelle/azioni_ui)). Concern ortogonale all'handler: `handler_id` automatizza lato server, `azione_ui_id` lancia un'attivita' interattiva lato client; un template puo' avere l'uno, l'altro, entrambi o nessuno.
* I prerequisiti tra template sono definiti nella tabella `template_flussi_prerequisiti` (DAG).
* La regola di **ripetibilita'** (D3) governa quante istanze dello stesso template possono nascere nella stessa pratica: enforcement a DB nel guard `trg_flussi_a10_guard_ripetibilita_ins` ([fn_check_ripetibilita_flusso](/dbzero/pratiche/funzioni/fn_check_ripetibilita_flusso)).
* L'**obbligatorieta'** vincola la chiusura della pratica (D4): un template `obbligatorio = true` non completato e ancora percorribile blocca la transizione a CHIUSA ([fn_check_chiusura_pratica](/dbzero/pratiche/funzioni/fn_check_chiusura_pratica)). Il ramo morto di un bivio non blocca.
* La **chiusura guidata dal workflow** (`chiude_pratica`): la pratica si chiude in automatico al completamento dei flussi, non con un'azione manuale. Se il tipo prestazione ha un template `chiude_pratica = true` (il "flusso di chiusura", max uno per tipo), la pratica passa a CHIUSA al completamento di quel flusso ([trgfn_flussi_autochiusura_pratica](/dbzero/pratiche/funzioni/trgfn_flussi_autochiusura_pratica)); altrimenti, se il tipo ha almeno un obbligatorio, si auto-chiude quando non restano obbligatori bloccanti. Un tipo senza obbligatori e senza flusso di chiusura non ha un percorso di chiusura deterministico (non si chiude).
* Ogni template appartiene a una **edizione di workflow** (`definizione_id` →
  [workflow_definizioni](workflow_definizioni.md)): il set di template di
  un'edizione E' la definizione. In assenza di valore esplicito, l'INSERT si
  aggancia al preset del tipo ([auto-default](trgfn_template_flussi_default_definizione.md)).
* L'**asse esito** (`modalita_esito`/`esito_default`) governa come lo step ottiene
  l'esito e quale classe di esito e' ammessa al completamento — invarianti config-time
  in [trgfn_template_flussi_guard_modalita_esito](trgfn_template_flussi_guard_modalita_esito.md),
  guard runtime in [trgfn_flussi_guard_esito_classe](trgfn_flussi_guard_esito_classe.md).
* L'**avanzamento su esito proiettato** (GUIDA D4): un template step può dichiarare
  `attende_sorgente_tipo_id` (il tipo documento il cui verdetto lo fa avanzare) e, insieme al
  binding [template_flussi_avanzamento_proiezione](template_flussi_avanzamento_proiezione.md),
  il milestone si completa **automaticamente** quando il documento proietta il verdetto
  ([fn_reconcile_sorgente](fn_reconcile_sorgente.md)). Additivo: senza mappa/binding,
  comportamento di oggi (nessun avanzamento automatico). Ammesso solo su step **non-DOMINIO**.
* **Immutabilità strutturale «Leggera» (strategia C)**: se l'edizione di appartenenza è
  un **fork già emesso** (`emittente_fiscale_id` valorizzato, stato PUBBLICATA o RITIRATA)
  la struttura è protetta — `INSERT`/`UPDATE` di template e figli **vietati** (UPDATE del
  solo `descrizione` ammesso). Il `DELETE` è vietato **solo** su **PUBBLICATA** (in uso):
  una **RITIRATA** resta **cancellabile** (housekeeping) pur non essendo modificabile.
  Errore `TEMPLATE_DEFINIZIONE_CONGELATA` (514). Il **preset** (emittente NULL) e le
  `BOZZA` restano liberamente editabili.
  Guard: [trgfn_template_flussi_guard_immutabile](trgfn_template_flussi_guard_immutabile.md)
  e [trgfn_template_flussi_figli_guard_immutabile](trgfn_template_flussi_figli_guard_immutabile.md);
  predicati [fn_check_definizione_struttura_bloccata](fn_check_definizione_struttura_bloccata.md)
  (INSERT/UPDATE) e [fn_check_definizione_congelata](fn_check_definizione_congelata.md) (DELETE).

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
| `azione_ui_id` | INTEGER nullable, FK → [`pratiche.azioni_ui`](/dbzero/pratiche/tabelle/azioni_ui). NULL = nessuna attivita' interattiva offerta dal flusso. NOT NULL = il frontend offre il lancio dell'attivita' dichiarata (es. APRI_PREVENTIVO). Specchio FE di `handler_id`. |
| `modalita_esito` | VARCHAR(20) CHECK (MANUALE, AUTOMATICO, CONTESTUALE, DOMINIO) DEFAULT 'MANUALE'. Come lo step ottiene l'esito: MANUALE = form esito; AUTOMATICO = avvia+completa con `esito_default` (solo INTERNA); CONTESTUALE = default pre-selezionato confermato in un'unica azione; **DOMINIO** = esito calcolato da un BB di dominio (es. SMISTAMENTO → `vendite.completa_smistamento`), nessuna scelta operatore, al completamento solo esiti di ramo `is_verdetto=false` (guard 504). |
| `esito_default` | VARCHAR(20) nullable, FK → `config.esiti_flussi_pratiche(codice_interno)`. Obbligatorio per AUTOMATICO/CONTESTUALE (Inv1, 494) e deve essere un verdetto (Inv4, 506); **vietato** con DOMINIO (Inv3, 505). |
| `definizione_id` | INTEGER NOT NULL. Edizione di workflow di appartenenza ([workflow_definizioni](workflow_definizioni.md)); default automatico al preset del tipo. FK **composita** con `tipo_prestazione_id` → coerenza tipo per costruzione. |
| `attende_sorgente_tipo_id` | BIGINT nullable, FK → [`config.sorgenti`](/dbzero/config/tabelle/sorgenti). GUIDA D4/G1: tipo documento il cui verdetto proiettato fa avanzare questo milestone ([fn_reconcile_sorgente](fn_reconcile_sorgente.md) + binding [template_flussi_avanzamento_proiezione](template_flussi_avanzamento_proiezione.md)). NULL = step non projection-driven (comportamento di oggi). Copiato da `fn_copia_definizione`. |

---

### Vincoli

* **UQ per-definizione**: `uq_template_flussi_definizione_codice (definizione_id, codice)` —
  il codice e' il contratto stabile dei BB runtime dentro l'edizione (contratto C5);
  `uq_template_flussi_chiusura_definizione (definizione_id) WHERE chiude_pratica` = max un
  `chiude_pratica` per edizione.
* I vecchi vincoli **per-tipo** (`uq_pratiche_template_flussi_tipo_codice`,
  `uq_template_flussi_chiusura`) sono stati **rimossi in Fase 2** (`20260703-05`): con le
  edizioni versionate un tipo puo' avere piu' definizioni (preset + fork + versioni) con
  gli **stessi codici**, quindi i vincoli per-tipo diventerebbero errati.
* **CHECK direzione**: solo valori ENTRATA, USCITA, INTERNA.
* **CHECK ripetibilita**: solo valori MAI, SE_NON_POSITIVO, SEMPRE.
* **FK handler_id nullable**: NULL = step manuale, NOT NULL = step automatizzato.
* **FK azione_ui_id nullable** (`fk_template_flussi_azione_ui`): NULL = nessuna attivita' UI, NOT NULL = attivita' interattiva offerta dal flusso. Indice FK non creato (tabella di configurazione minuscola): registrato in `dbops.fk_index_policy` con `consentito = false`.

---

### Convenzioni

* Trigger standard applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).
* `storicizza = true` per tracciamento modifiche alla configurazione.

---

{% include-markdown "signature-core.md" %}
