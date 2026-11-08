## 📘 Documentazione Concettuale – Tabella `vendite.ddt`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe) — le righe della bolla
> * [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment) — il legame riga d'ordine ↔ riga di bolla
> * [vendite.resi](/dbzero/vendite/tabelle/resi) — il reso da cui nasce la bolla di riconsegna
> * [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt) — il vocabolario degli stati
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento d'origine
>
> Approfondimento viste:
>
> * [vendite.vw_ddt_lista](/dbzero/vendite/views/vw_ddt_lista) — la lista delle bolle
>
> Approfondimento funzioni:
>
> * [vendite.fn_genera_ddt_da_ordine](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine) — la bolla che evade un ordine
> * [vendite.fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna) — la bolla che riconsegna un reso
> * [vendite.fn_documento_legami](/dbzero/vendite/funzioni/fn_documento_legami) — i documenti collegati alla bolla
> * [vendite.trgfn_doc_guard_delete_solo_bozza](/dbzero/vendite/funzioni/trgfn_doc_guard_delete_solo_bozza) — si cancella solo la bozza vuota
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico della provenienza
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

La tabella **`vendite.ddt`** rappresenta la **testata** dei Documenti di Trasporto. È il fulcro del ciclo logistico tra **Ordini** (evasione/spedizione) e **Fatture** (conto vendita / accompagnatoria).

* Traccia i **metadati di spedizione** (data, mittente/destinatario, causale, vettore).
* Collega le **righe** in `vendite.ddt_righe`.
* Espone lo **stato** operativo tramite `config.stati_doc_ddt` (*DRAFT → EMESSO → SPEDITO → CONSEGNATO → RESO*, + *ANNULLATO*), con transizioni data-driven in `config.transizioni_stati_ddt`.
* Partecipa alle ricostruzioni **ordine↔ddt** via fulfillment (riga↔riga); il legame **testata↔testata** è la provenienza della bolla.

---


### Relazioni chiave

* **`vendite.ddt_righe(ddt_id)`** → righe del documento (1–N).
* **`vendite.ordini_righe_fulfillment(ddt_riga_id)`** → mappatura riga DDT con riga Ordine.
* **`config.stati_doc_ddt(id)`** → stato del documento.

> ⚠️ Una riga di bolla con un fulfillment, o che è l'origine di un reso, non si cancella (`E_DELETE_BLOCKED_FUL`, `E_DELETE_RIGA_DOC_REFERENZIATA`).

---

### Da quale documento nasce la bolla

La bolla dice il documento da cui nasce con le colonne del modello della provenienza:
`sorgente_tipo_id` e la chiave del documento (`sorgente_id`, perché ordine e reso si
riconoscono dall'id). I tipi sono due:

* **l'ordine** (`ORDINE_VENDITA`) — la bolla che lo evade. È la condizione perché
  `vendite.trgfn_ddt_normalize` erediti dall'ordine conto di fatturazione, utility, valuta ed
  emittente;
* **il reso** (`RESO_VENDITA`) — la bolla di riconsegna, che riporta al cliente la merce rientrata.

La bolla nata da sola le ha tutte vuote; la forma la tiene `chk_ddt_sorgente_forma`. Il guard
unico `script.trgfn_guard_sorgente` verifica che il documento d'origine esista e ne blocca la
cancellazione finché una bolla lo cita; fuori bozza la provenienza è ferma
(`E_DOC_SORGENTE_FUORI_BOZZA`). Le righe portano a loro volta la provenienza della riga d'ordine
o di reso.

---

###  Stati del DDT

Gli stati sono definiti in **`config.stati_doc_ddt`**; le **transizioni ammesse** vivono in **`config.transizioni_stati_ddt`** (matrice data-driven, mirror di `transizioni_stati_ordini`). Ciclo:

```text
DRAFT → EMESSO → SPEDITO → CONSEGNATO → RESO   (+ ANNULLATO; RESO anche da SPEDITO)
```

* **Enforcement**: il trigger `vendite.trgfn_ddt_guard_transizione` (fase `_a10_`, `BEFORE UPDATE OF stato_doc_ddt_id`) valida la coppia `(vecchio, nuovo)` contro la matrice attiva (`E_STATO_DDT_TRANSIZIONE_NON_VALIDA`).
* **Gate emissione**: alla transizione a **EMESSO**, `vendite.trgfn_ddt_guard_transizione_approvazione` blocca, se la causale vende, quando esistono componenti BoM CASO A attivi con il prezzo in attesa di approvazione o rifiutato (`E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO`, attraverso [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati)) o con prezzo NULL (`E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`).
* **Azioni UI data-driven**: il `meta.ui` di ogni transizione (etichetta, conferma, `outlined`) è esposto da `script.fn_available_actions_ddt` → il FE non hardcoda i pulsanti; icona e colore li sceglie dal `key` dell'azione.
* **Numerazione a EMESSO**: il `numero` si assegna alla transizione a EMESSO (no buchi da bozze scartate) via [`vendite.trgfn_ddt_gen_numero_emesso`](/dbzero/vendite/funzioni/trgfn_ddt_gen_numero_emesso); immutabile dopo l'assegnazione (`vendite.trgfn_v_ddt_protect_num`).
  Contatore **e** forma vengono dal **motore dei registri**, non da `config.sistema_codici`.
* ⛔ **Si cancella solo la bozza vuota**: nello stato in cui nasce e senza righe attive
  (`vendite.trgfn_doc_guard_delete_solo_bozza`: `E_DELETE_DOC_NON_BOZZA`,
  `E_DELETE_DOC_CON_RIGHE`). Una bolla emessa si annulla.

>  La funzione di sync degli **stati ordine** legge anche lo stato del DDT per determinare le quantità **consegnate**.

---

### Vincoli e indici

* **PK**: `id`
* **UQ consigliate**: `anno+serie+numero` (o progressivo per gestore)
* **Indici operativi**:

  * `ix_ddt_vendita_dest_stato_data (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data)`
  * `ix_vendite_ddt_stato_doc_ddt_id (stato_doc_ddt_id)`
  * `ix_ddt_v_sorgente_id` e `ix_ddt_v_sorgente` — le bolle di un documento d'origine, per
    ognuna delle due chiavi (multi-DDT)

> ℹ️ Gli indici reali possono variare in base ai volumi e all’uso (reporting vs operativo).

---

### Flussi di processo collegati

1. **Evasione da Ordine** (`vendite.fn_genera_ddt_da_ordine`)

   * Funzione madre atomica: da un ordine (CONFERMATO / PARZIALMENTE_EVASO) crea testata DDT
     (DRAFT, con provenienza l'ordine: tipo `ORDINE_VENDITA` e la sua chiave), copia lo
     **snapshot** delle righe (prezzo/sconto/iva) e dei componenti CASO A, ognuna con la
     provenienza della riga d'ordine, e inserisce il
     **fulfillment** riga↔riga (`qta_evasa`).
   * **Multi-DDT**: un ordine può generare più DDT (consegne parziali). L'over-shipping è
     bloccato dal guard `trgfn_ordini_ful_guard_consistenza` (`E_QTA_SUPERA_RESIDUO`); l'unicità del
     legame è sul fulfillment `(ordine_riga_id, ddt_riga_id)`, non più sulla testata.
   * **Proiezione stato ordine** (atomica): residuo pieno → `CONFERMATO`, `0 < residuo < pieno` →
     `PARZIALMENTE_EVASO`, residuo 0 → `EVASO` (predicato `fn_ordine_ha_residuo_evasione`).
   * Il legame **testata↔testata** non ha un oggetto dedicato: si ricava dal
     fulfillment o dalla provenienza della bolla.

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

* La testata si cancella solo bozza vuota; le righe si toccano solo in bozza, e una riga con un
  fulfillment o che è l'origine di un reso non si cancella.
* **`storicizza`**: alla modifica e alla cancellazione scatta il trigger che copia in `storico.ddt` /
  `storico.ddt_righe`.
* Gli ordini collegati a una bolla si leggono dal fulfillment (riga di bolla → riga d'ordine →
  ordine), o dalla provenienza della testata.

---

### ⚠️ Errori/diagnostica comuni

* `E_DELETE_BLOCKED_FUL` – tentativo di cancellare una riga di bolla collegata a un fulfillment.
* `E_DELETE_RIGA_DOC_REFERENZIATA` – la riga è l'origine di un reso.
* `E_STATO_DDT_TRANSIZIONE_NON_VALIDA` – transizione di stato non ammessa dalla matrice.
* `E_DOC_SORGENTE_FUORI_BOZZA` – cambio della provenienza fuori bozza.

---

### Checklist di conformità

* [ ] UQ corretta su numerazione (o progressivo per gestore)
* [ ] FK a domini/stati coerenti
* [ ] Indici operativi creati
* [ ] Trigger di blocco DELETE attivi su `ddt_righe`
* [ ] Guard unico della provenienza montato su testata e righe
* [ ] Procedure di **storno/annullo** definite nei flussi applicativi

---

### Read-side (lista / dettaglio) e seed trasporto

* **`vendite.vw_ddt_lista`** — vista canonica denormalizzata (stato, destinatario/mittente/vettore,
  trasporto, ordine di origine risolto dalla provenienza) per `<ListaConfigurabile>` (`security_invoker=on`).
  Definizione lista/colonne in `ui.lista_definizione` / `ui.lista_colonna` (`codice = vendite.ddt`).
* **`script.fn_available_actions_ddt`** — capabilities per il drawer (azioni data-driven dalla
  matrice, `can_edit_*`, `push_commessa` letto da `fn_ddt_push_diagnosi`, la fonte unica da cui deriva anche `fn_list_ddt_da_pushare`).
* **Seed trasporto**: `config.causali_trasporto` e `config.aspetti_beni` (valori standard IT) —
  valorizzabili in testata, base per il PDF accompagnatorio.

---

### Scope emittente e RLS

Il DDT **memorizza** l'emittente fiscale (`emittente_fiscale_id`, `NOT NULL`, FK) — allineato a
ordini/preventivi — come chiave di scope multi-emittente.

* **Valorizzazione**: `trgfn_ddt_normalize` eredita l'emittente dall'ordine sorgente; per lo
  standalone lo risolve dal `billing_account` (`anagrafiche.fn_get_emittente_fiscale_pk`).
* **Guard scrittura** (defense-in-depth): `trg_ddt_z10_guard_emittente_scope_ins_upd`
  (`script.trgfn_guard_emittente_scope('fiscale','emittente_fiscale_id')`) blocca INSERT/UPDATE
  se l'operatore non ha scope sull'emittente; skippa se `app.current_user_id` non e` settato (batch).
* ⛔ **Chi legge l'emittente gira dopo chi lo risolve**. Su una
  bolla nata da un ordine l'emittente arriva solo con `trg_ddt_normalize_ins_upd`, che non ha
  fascia e viene dopo tutti gli `_a10_`: il default dell'emittente, con `SALTA_CON_SORGENTE`,
  lascia a lui quelle righe. Per questo i quattro BEFORE che leggono l'emittente stanno in fascia
  `_z10_`: `trg_ddt_z10_default_magazzino_ins`, `trg_ddt_z10_gen_numero_emesso_ins_upd`,
  `trg_ddt_z10_guard_emittente_scope_ins_upd`, `trg_ddt_z10_guard_magazzino_ins_upd`: in `_a10_`
  la bolla generata da un ordine nascerebbe senza magazzino predefinito e non si emetterebbe
  (`E_DDT_MAGAZZINO_OBBLIGATORIO`). È lo stesso ordine del reso. Un trigger nuovo che
  legge l'emittente all'INSERT va in `_z10_`; lo presidia il test 1 di
  `vendite/test-ddt-da-ordine-emittente-prima-dei-lettori-v1`.
* **RLS**: policy `rls_ddt_ef_whitelist` (`FOR ALL`, `script.fn_scope_ef_whitelist`, gate
  `OPERATORE`). Stato a parita` con ordini/preventivi/fatture: **`ENABLE` senza `FORCE`** →
  l'owner-app la bypassa finche` non arriva il `FORCE` (ondata coordinata). Protezione **attiva**
  oggi = filtro applicativo BE su `vw_ddt_lista.emittente_fiscale_id`.

---

### Corsia di fatturazione: `fatturazione_immediata`

Colonna `boolean NOT NULL DEFAULT false`: dice se la bolla si fattura subito o nel giro
differito, come per gli altri documenti che vanno in commessa.

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

---

### Note di migrazione

* 2026-07-27 — arriva `fatturazione_immediata`: prima il flag esisteva solo sul preventivo
  (brief-db-emissione-fattura-per-documento-sorgente).
* 2026-08-05 — si ritira la vista materializzata `mv_ddt_ordini` (coppie testata DDT ↔ testata
  ordine): nessuno la leggeva né la aggiornava, ed era ferma a zero righe.
* 2026-08-26 — la testata si cancella solo in bozza.
* 2026-08-31 — numero e forma passano al motore dei registri.
* 2026-09-24 — il gate di emissione legge i prezzi da `script.fn_check_prezzi_autorizzati`, con
  `E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO` al posto di `E_COMPONENTE_PREZZO_PENDENTE`.
* 2026-10-13 — i trigger che leggono l'emittente passano in fascia `_z10_`.
* 2026-11-06 — la provenienza passa al modello: la chiave testuale `sorgente_uid` diventa la
  coppia tipizzata `sorgente_id` / `sorgente_uid` (uuid) col guard unico, e la bolla di
  riconsegna dichiara come origine il reso (brief-db-sorgente-documento-e-riga).
* 2026-11-07 — la cancellazione, fino ad allora concessa a ogni bozza, vuole la bozza vuota.

---

{% include-markdown "signature-core.md" %}

