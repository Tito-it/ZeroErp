## 📘 Documentazione Concettuale – Tabella `vendite.ddt`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)   
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)   
> [vendite.mv_ddt_ordini] – **vista materializzata** delle coppie Testata DDT ↔ Testata Ordine      
> [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt)   

---
### 🎯 Scopo Principale
La tabella **`vendite.ddt`** rappresenta la **testata** dei Documenti di Trasporto. È il fulcro del ciclo logistico tra **Ordini** (evasione/spedizione) e **Fatture** (conto vendita / accompagnatoria).

* Traccia i **metadati di spedizione** (data, mittente/destinatario, causale, vettore).
* Collega le **righe** in `vendite.ddt_righe`.
* Espone lo **stato** operativo tramite `config.stati_doc_ddt` (*DRAFT → EMESSO → SPEDITO → CONSEGNATO → RESO*, + *ANNULLATO*), con transizioni data-driven in `config.transizioni_stati_ddt`.
* Partecipa alle ricostruzioni **ordine↔ddt** via fulfillment (riga↔riga) e alla derivazione **ddt↔ordine** (testata↔testata) tramite `mv_ddt_ordini`.

> ℹ️ **Nota**: la definizione SQL della tabella è generata automaticamente dal progetto; qui si documentano struttura concettuale, vincoli e flussi.

---


### Relazioni chiave

* **`vendite.ddt_righe(ddt_id)`** → righe del documento (1–N).
* **`vendite.ordini_righe_fulfillment(ddt_riga_id)`** → mappatura riga DDT con riga Ordine.
* **`vendite.mv_ddt_ordini(ddt_id, ordine_id)`** → coppie testata↔testata derivate.
* **`config.stati_doc_ddt(id)`** → stato del documento.

> 立 **FK policy**: sui legami fulfillment → righe vige `ON DELETE RESTRICT` (no hard delete). Le cancellazioni sono rimpiazzate da flussi di **storno/annullo**.

---

###  Stati del DDT

Gli stati sono definiti in **`config.stati_doc_ddt`**; le **transizioni ammesse** vivono in **`config.transizioni_stati_ddt`** (matrice data-driven, mirror di `transizioni_stati_ordini`). Ciclo:

```
DRAFT → EMESSO → SPEDITO → CONSEGNATO → RESO   (+ ANNULLATO; RESO anche da SPEDITO)
```

* **Enforcement**: il trigger `vendite.trgfn_ddt_guard_transizione` (fase `_a10_`, `BEFORE UPDATE OF stato_doc_ddt_id`) valida la coppia `(vecchio, nuovo)` contro la matrice attiva (`E_STATO_DDT_TRANSIZIONE_NON_VALIDA`).
* **Gate emissione**: alla transizione a **EMESSO**, `vendite.trgfn_ddt_guard_transizione_approvazione` blocca se esistono componenti BoM CASO A in `PENDING` (`E_COMPONENTE_PREZZO_PENDENTE`) o con prezzo NULL (`E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`).
* **Azioni UI data-driven**: il `meta.ui` di ogni transizione (label/icona/severity) è esposto da `script.fn_available_actions_ddt` → il FE non hardcoda i pulsanti.
* **Numerazione a EMESSO**: il `numero` si assegna alla transizione a EMESSO (no buchi da bozze scartate) via `vendite.trgfn_ddt_gen_numero_emesso` — fuori dal framework `sistema_codici` (mirror fatture); immutabile dopo l'assegnazione (`vendite.trgfn_v_ddt_protect_num`).
* No hard delete: annullo/storno, mai DELETE fisica.

>  La funzione di sync degli **stati ordine** legge anche lo stato del DDT per determinare le quantità **consegnate**.

---

### Vincoli e indici

* **PK**: `id`
* **UQ consigliate**: `anno+serie+numero` (o progressivo per gestore)
* **Indici operativi**:

  * `ix_ddt_vendita_dest_stato_data (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data)`
  * `ix_vendite_ddt_stato_doc_ddt_id (stato_doc_ddt_id)`
  * `ix_ddt_v_sorgente (sorgente_tipo_id, sorgente_uid)` — lookup DDT-per-ordine (multi-DDT, A-1)

> ℹ️ Gli indici reali possono variare in base ai volumi e all’uso (reporting vs operativo).

---

### Flussi di processo collegati

1. **Evasione da Ordine** (`vendite.fn_genera_ddt_da_ordine`)

   * Funzione madre atomica: da un ordine (CONFERMATO / PARZIALMENTE_EVASO) crea testata DDT
     (DRAFT, `sorgente_tipo_id = ORDINE_VENDITA`, `sorgente_uid = ordini.uid`), copia lo
     **snapshot** delle righe (prezzo/sconto/iva) e dei componenti CASO A (A-2), e inserisce il
     **fulfillment** riga↔riga (`qta_evasa`).
   * **Multi-DDT** (A-1): un ordine può generare più DDT (consegne parziali). L'over-shipping è
     bloccato dal guard `trgfn_ordini_ful_guard_consistenza` (`E_QTA_SUPERA_RESIDUO`); l'unicità del
     legame è sul fulfillment `(ordine_riga_id, ddt_riga_id)`, non più sulla testata.
   * **Proiezione stato ordine** (atomica): residuo pieno → `CONFERMATO`, `0 < residuo < pieno` →
     `PARZIALMENTE_EVASO`, residuo 0 → `EVASO` (predicato `fn_ordine_ha_residuo_evasione`).
   * La **MV** `mv_ddt_ordini` riflette le coppie testata↔testata (refresh via
     `dbops.fn_refresh_mv_ddt_ordini`, non nella fn).

2. **Consegna**

   * Al cambio stato del DDT a *CONSEGNATO*, le quantità consegnate possono aggiornare l’**avanzamento ordine** (via trigger di sync).

3. **Push a commessa** (via `fn_list_ddt_da_pushare`)

   * DDT da ordine: eredita billing_account e prezzo via fulfillment; scatta quando `fatturazione_trigger` dell'ordine corrisponde allo stato DDT.
   * DDT autonomo: richiede `billing_account_id` proprio; scatta a SPEDITO/CONSEGNATO.
   * Campi aggiunti: `billing_account_id`, `utility_id`, `valuta_id` (ereditati dall'ordine sorgente via `trgfn_ddt_normalize`), `ddt_righe.prezzo_unitario`.

4. **Fatturazione**

   * Il DDT puo` essere fatturato (fattura differita o accompagnatoria). Le tabelle e logiche di collegamento saranno documentate in un modulo dedicato.

---

###  Regole di coerenza (riassunto)

* **No hard delete** su `ddt` e `ddt_righe`; esistono **trigger** che bloccano la cancellazione diretta delle righe se presenti fulfillment, e in generale **vietano la DELETE** (policy ZeroERP).
* **`storicizza`**: all’operazione di cancellazione (se mai prevista per soli casi tecnici) scatta il trigger che copia in `storico.ddt` / `storico.ddt_righe`. In produzione si preferisce **annullo/storno** a cancellazione.

---

### Query tipiche

* **Selezione DDT per range di date e stato**

  ```sql
  SELECT d.*
    FROM vendite.ddt d
   WHERE d.data BETWEEN :dal AND :al
     AND d.stato_doc_ddt_id = :stato_id
   ORDER BY d.data DESC, d.id DESC;
  ```
* **Ordini collegati a un DDT (via MV)**

  ```sql
  SELECT o.*
    FROM vendite.mv_ddt_ordini m
    JOIN vendite.ordini o ON o.id = m.ordine_id
   WHERE m.ddt_id = :ddt_id;
  ```

---

### Manutenzione MV correlata

* **Refresh manuale**:

  ```sql
  REFRESH MATERIALIZED VIEW CONCURRENTLY vendite.mv_ddt_ordini;
  ```
* **Refresh controllato** (se attivata la funzione di servizio):

  ```sql
  SELECT dbops.fn_refresh_mv_ddt_ordini(true, 3);
  ```

---

### ⚠️ Errori/diagnostica comuni

* `DELETE_BLOCKED_FUL` – tentativo di cancellare riga DDT collegata a fulfillment.
* `DELETE_NOT_ALLOWED` – policy: no hard delete sulle righe DDT/Ordini.
* `STATO_DDT_NON_VALIDO` – cambio stato verso valore non presente in `config.stati_doc_ddt`.

---

### Checklist di conformità

* [ ] UQ corretta su numerazione (o progressivo per gestore)
* [ ] FK a domini/stati coerenti
* [ ] Indici operativi creati
* [ ] Trigger di blocco DELETE attivi su `ddt_righe`
* [ ] MV `mv_ddt_ordini` presente e indicizzata (UNIQUE)
* [ ] Procedure di **storno/annullo** definite nei flussi applicativi

---

### Read-side (lista / dettaglio) e seed trasporto

* **`vendite.vw_ddt_lista`** — vista canonica denormalizzata (stato, destinatario/mittente/vettore,
  trasporto, ordine di origine via `sorgente_uid`) per `<ListaConfigurabile>` (`security_invoker=on`).
  Definizione lista/colonne in `ui.lista_definizione` / `ui.lista_colonna` (`codice = vendite.ddt`).
* **`script.fn_available_actions_ddt`** — capabilities per il drawer (azioni data-driven dalla
  matrice, `can_edit_*`, `push_commessa` via `fn_list_ddt_da_pushare`).
* **Seed trasporto**: `config.causali_trasporto` e `config.aspetti_beni` (valori standard IT) —
  valorizzabili in testata, base per il PDF accompagnatorio.

---

### Scope emittente e RLS (§15)

Il DDT **memorizza** l'emittente fiscale (`emittente_fiscale_id`, `NOT NULL`, FK) — allineato a
ordini/preventivi — come chiave di scope multi-emittente.

* **Valorizzazione**: `trgfn_ddt_normalize` eredita l'emittente dall'ordine sorgente; per lo
  standalone lo risolve dal `billing_account` (`anagrafiche.fn_get_emittente_fiscale_pk`).
* **Guard scrittura** (defense-in-depth): `trg_ddt_a10_guard_emittente_scope_ins_upd`
  (`script.trgfn_guard_emittente_scope('fiscale','emittente_fiscale_id')`) blocca INSERT/UPDATE
  se l'operatore non ha scope sull'emittente; skippa se `app.current_user_id` non e` settato (batch).
* **RLS**: policy `rls_ddt_ef_whitelist` (`FOR ALL`, `script.fn_scope_ef_whitelist`, gate
  `OPERATORE`). Stato a parita` con ordini/preventivi/fatture: **`ENABLE` senza `FORCE`** →
  l'owner-app la bypassa finche` non arriva il `FORCE` (ondata coordinata). Protezione **attiva**
  oggi = filtro applicativo BE su `vw_ddt_lista.emittente_fiscale_id`.

---

### 📘 Note finali

* Questo documento descrive il **comportamento atteso** della tabella `vendite.ddt` nel contesto Zero ERP.
* Gli esempi di query sono indicativi; le implementazioni DRF/Vue 3 riflettono gli stessi vincoli (no hard delete, stati come sorgente della verità).
