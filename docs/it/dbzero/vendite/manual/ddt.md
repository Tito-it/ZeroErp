## 📘 Documentazione Concettuale – Tabella `vendite.ddt`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)   
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)   
> [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt)   

---
### 🎯 Scopo Principale
La tabella **`vendite.ddt`** rappresenta la **testata** dei Documenti di Trasporto. È il fulcro del ciclo logistico tra **Ordini** (evasione/spedizione) e **Fatture** (conto vendita / accompagnatoria).

* Traccia i **metadati di spedizione** (data, mittente/destinatario, causale, vettore).
* Collega le **righe** in `vendite.ddt_righe`.
* Espone lo **stato** operativo tramite `config.stati_doc_ddt` (*DRAFT → EMESSO → SPEDITO → CONSEGNATO → RESO*, + *ANNULLATO*), con transizioni data-driven in `config.transizioni_stati_ddt`.
* Partecipa alle ricostruzioni **ordine↔ddt** via fulfillment (riga↔riga); il legame **testata↔testata** si ricava da lì, oppure direttamente da `ddt.sorgente_uid`.

> ℹ️ **Nota**: la definizione SQL della tabella è generata automaticamente dal progetto; qui si documentano struttura concettuale, vincoli e flussi.

---


### Relazioni chiave

* **`vendite.ddt_righe(ddt_id)`** → righe del documento (1–N).
* **`vendite.ordini_righe_fulfillment(ddt_riga_id)`** → mappatura riga DDT con riga Ordine.
* **`config.stati_doc_ddt(id)`** → stato del documento.

> 立 **FK policy**: sui legami fulfillment → righe vige `ON DELETE RESTRICT` (no hard delete). Le cancellazioni sono rimpiazzate da flussi di **storno/annullo**.

---

###  Stati del DDT

Gli stati sono definiti in **`config.stati_doc_ddt`**; le **transizioni ammesse** vivono in **`config.transizioni_stati_ddt`** (matrice data-driven, mirror di `transizioni_stati_ordini`). Ciclo:

```
DRAFT → EMESSO → SPEDITO → CONSEGNATO → RESO   (+ ANNULLATO; RESO anche da SPEDITO)
```

* **Enforcement**: il trigger `vendite.trgfn_ddt_guard_transizione` (fase `_a10_`, `BEFORE UPDATE OF stato_doc_ddt_id`) valida la coppia `(vecchio, nuovo)` contro la matrice attiva (`E_STATO_DDT_TRANSIZIONE_NON_VALIDA`).
* **Gate emissione**: alla transizione a **EMESSO**, `vendite.trgfn_ddt_guard_transizione_approvazione` blocca, se la causale vende, quando esistono componenti BoM CASO A attivi con il prezzo in attesa di approvazione o rifiutato (`E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO`, dal 2026-09-24 attraverso [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati); prima guardava il solo `PENDING` con `E_COMPONENTE_PREZZO_PENDENTE`) o con prezzo NULL (`E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`).
* **Azioni UI data-driven**: il `meta.ui` di ogni transizione (etichetta, conferma, `outlined`) è esposto da `script.fn_available_actions_ddt` → il FE non hardcoda i pulsanti; icona e colore li sceglie dal `key` dell'azione.
* **Numerazione a EMESSO**: il `numero` si assegna alla transizione a EMESSO (no buchi da bozze scartate) via [`vendite.trgfn_ddt_gen_numero_emesso`](/dbzero/vendite/manual/trgfn_ddt_gen_numero_emesso); immutabile dopo l'assegnazione (`vendite.trgfn_v_ddt_protect_num`).
  ⚠️ **rev 2026-08-31**: contatore **e** forma vengono dal **motore dei registri**, non da `config.sistema_codici` — che dal 31 agosto 2026 non ha più una riga `ddt`.
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
   * Il legame **testata↔testata** non ha un oggetto dedicato: si ricava dal
     fulfillment o da `ddt.sorgente_uid`.

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
* **Ordini collegati a un DDT**

  ```sql
  SELECT DISTINCT o.*
    FROM vendite.ordini_righe_fulfillment f
    JOIN vendite.ddt_righe dr  ON dr.id = f.ddt_riga_id
    JOIN vendite.ordini_righe orr ON orr.id = f.ordine_riga_id
    JOIN vendite.ordini o      ON o.id = orr.ordine_id
   WHERE dr.ddt_id = :ddt_id;
  ```

---

### 🗑️ La vista materializzata `mv_ddt_ordini` è stata ritirata (2026-08-05)

Questa pagina documentava una scorciatoia — una vista materializzata che teneva
pronte le coppie testata DDT ↔ testata Ordine — e le istruzioni per aggiornarla.
**Non esiste più** (changeSet `20260805-21` e `-22`).

Il motivo non è un cambio di disegno: era **ferma dalla nascita**. Nessuna
funzione e nessuna vista la leggeva, il backend e il frontend non la nominavano,
e soprattutto **nessuno chiamava il refresh** — né una funzione, né un job. Al
momento del ritiro conteneva 0 righe mentre la sua query ne avrebbe prodotte 15.
Chi l'avesse interrogata avrebbe letto «questo DDT non ha ordini» con la stessa
sicurezza con cui avrebbe detto il vero.

Il legame testata↔testata si ricava dai due percorsi che l'applicazione usa
davvero: `vendite.ordini_righe_fulfillment` (vedi la query qui sopra) e
`vendite.ddt.sorgente_uid`.

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
* [ ] Procedure di **storno/annullo** definite nei flussi applicativi

---

### Read-side (lista / dettaglio) e seed trasporto

* **`vendite.vw_ddt_lista`** — vista canonica denormalizzata (stato, destinatario/mittente/vettore,
  trasporto, ordine di origine via `sorgente_uid`) per `<ListaConfigurabile>` (`security_invoker=on`).
  Definizione lista/colonne in `ui.lista_definizione` / `ui.lista_colonna` (`codice = vendite.ddt`).
* **`script.fn_available_actions_ddt`** — capabilities per il drawer (azioni data-driven dalla
  matrice, `can_edit_*`, `push_commessa` letto da `fn_ddt_push_diagnosi`, la fonte unica da cui deriva anche `fn_list_ddt_da_pushare`).
* **Seed trasporto**: `config.causali_trasporto` e `config.aspetti_beni` (valori standard IT) —
  valorizzabili in testata, base per il PDF accompagnatorio.

---

### Scope emittente e RLS (§15)

Il DDT **memorizza** l'emittente fiscale (`emittente_fiscale_id`, `NOT NULL`, FK) — allineato a
ordini/preventivi — come chiave di scope multi-emittente.

* **Valorizzazione**: `trgfn_ddt_normalize` eredita l'emittente dall'ordine sorgente; per lo
  standalone lo risolve dal `billing_account` (`anagrafiche.fn_get_emittente_fiscale_pk`).
* **Guard scrittura** (defense-in-depth): `trg_ddt_z10_guard_emittente_scope_ins_upd`
  (`script.trgfn_guard_emittente_scope('fiscale','emittente_fiscale_id')`) blocca INSERT/UPDATE
  se l'operatore non ha scope sull'emittente; skippa se `app.current_user_id` non e` settato (batch).
* ⛔ **Chi legge l'emittente gira dopo chi lo risolve** (rev 2026-10-13, `20261013-53`). Su una
  bolla nata da un ordine l'emittente arriva solo con `trg_ddt_normalize_ins_upd`, che non ha
  fascia e viene dopo tutti gli `_a10_`: il default dell'emittente, con `SALTA_CON_SORGENTE`,
  lascia a lui quelle righe. Per questo i quattro BEFORE che leggono l'emittente stanno in fascia
  `_z10_`: `trg_ddt_z10_default_magazzino_ins`, `trg_ddt_z10_gen_numero_emesso_ins_upd`,
  `trg_ddt_z10_guard_emittente_scope_ins_upd`, `trg_ddt_z10_guard_magazzino_ins_upd`. Prima
  erano `_a10_`: la bolla generata da un ordine nasceva senza magazzino predefinito e non si
  emetteva (`E_DDT_MAGAZZINO_OBBLIGATORIO`). È lo stesso ordine del reso. Un trigger nuovo che
  legge l'emittente all'INSERT va in `_z10_`; lo presidia il test 1 di
  `vendite/test-ddt-da-ordine-emittente-prima-dei-lettori-v1`.
* **RLS**: policy `rls_ddt_ef_whitelist` (`FOR ALL`, `script.fn_scope_ef_whitelist`, gate
  `OPERATORE`). Stato a parita` con ordini/preventivi/fatture: **`ENABLE` senza `FORCE`** →
  l'owner-app la bypassa finche` non arriva il `FORCE` (ondata coordinata). Protezione **attiva**
  oggi = filtro applicativo BE su `vw_ddt_lista.emittente_fiscale_id`.

---

### 📘 Note finali

* Questo documento descrive il **comportamento atteso** della tabella `vendite.ddt` nel contesto Zero ERP.
* Gli esempi di query sono indicativi; le implementazioni DRF/Vue 3 riflettono gli stessi vincoli (no hard delete, stati come sorgente della verità).

---

### Corsia di fatturazione: `fatturazione_immediata` (27-07-2026)

Colonna `boolean NOT NULL DEFAULT false` aggiunta dalla slice di simmetria del
flag (brief `brief-db-emissione-fattura-per-documento-sorgente` PARTE B,
migration `20260727-03`). Prima esisteva **solo** su `vendite.preventivi`: le altre
sorgenti esponevano il campo nel contratto delle `fn_list_*_da_pushare` ma con
valore costante `FALSE`, quindi **solo un preventivo poteva essere fatturato
subito** — non per una scelta di dominio, ma per un buco di modello.

| Valore | Corsia | Arriva a |
|---|---|---|
| `true` | immediata (lotto `GIORNALIERO`) | `DEFINITIVA` — numera da sola |
| `false` *(default)* | differita (lotto `MASSIVO`) | `EMESSA` — la numerazione è un atto separato |

**Si stabilisce PRIMA del push.** Il valore viene letto una sola volta, da
`vendite.fn_list_ddt_da_pushare`, e propagato alla commessa dove è **parte della chiave di dedup** di
`fn_get_or_create_commessa`. Dopo il push è inerte, e la modifica è respinta
dal guard
[`trgfn_guard_fatturazione_immediata_immutabile`](/dbzero/vendite/funzioni/trgfn_guard_fatturazione_immediata_immutabile)
(`E_FATT_IMMEDIATA_NON_MODIFICABILE`). Il caso «cambio idea dopo» è coperto
dall'**emissione mirata per gruppo fatturabile**, non da questo flag.

⚠️ **Non governa `prezzo_bloccato`.** L'accoppiamento
`prezzo_bloccato = COALESCE(fatturazione_immediata, false)` esiste **solo sui
preventivi**: qui i due valori sono indipendenti e vanno tenuti tali.

Il default `false` garantisce che l'aggiunta della colonna **non cambi la corsia
di nessun documento esistente**.

