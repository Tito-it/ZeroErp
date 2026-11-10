## 📘 Documentazione Concettuale – Tabella `vendite.attivita_fatturabili`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — la riga di commessa da cui ogni attività nasce, e che porta la provenienza
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse) — la testata della commessa
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'articolo o servizio
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — l'intestazione economica
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — il punto tecnico
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) — il documento emesso
> * [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) — la riga di fattura che consuma l'attività
> * [vendite.note](/dbzero/vendite/tabelle/note) — le note
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_attivita_fattore_alla_data](/dbzero/vendite/funzioni/trgfn_attivita_fattore_alla_data) — il fattore alla data dell'attività, quando la riga non lo porta
> * [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa) — l'emissione dalle righe di commessa
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza, e perché l'attività fatturabile ne resta fuori

---
### 🎯 Scopo Principale

`vendite.attivita_fatturabili` è il **registro centrale delle prestazioni/attività da fatturare** (time & material, canoni, una‑tantum, letture/consumi valorizzati, import batch, ecc.).
Ogni riga rappresenta **una voce fatturabile** riferita a un *articolo/servizio*, a una *istanza tecnica/utility* e, opzionalmente, a un *billing account*.
Queste righe sono **pre‑documentali**: quando il ciclo di fatturazione le preleva, diventano **righe di fattura** (`vendite.fatture_righe`).

Obiettivi principali:

* **Accentramento** della sorgente di verità per tutto ciò che va fatturato.
* **Controllo del periodo di competenza** (mensile o a intervallo) per stabilire **quando** fatturare.
* **Tracciabilità** dallo *stato bozza → approvato → fatturato* con blocchi anti‑doppia fatturazione.
* **Provenienza** univoca: ogni attività nasce da **una** riga di commessa, e una riga di commessa genera al più un'attività.

---

### Collocazione nel flusso di fatturazione

1. **Acquisizione**: le attività arrivano da input manuali, sistemi esterni, motori di calcolo o letture; vengono registrate qui con `data_attivita`, `quantita`, riferimenti a `articolo_id`, `istanza_utility_id`, `billing_account_id` (**obbligatorio**).
2. **Normalizzazione/validazione** (trigger): allineamento della competenza mensile, coerenze su commessa, BA e istanza.
3. **Approvazione**: il flag `approvato` abilita l’eleggibilità al prelievo.
4. **Selezione per fatturazione**: il motore estrae le righe **non fatturate**, **non sospese**, **non posticipate** e **in competenza** (vedi paragrafo successivo).
5. **Generazione documento**: le righe selezionate generano entries su `vendite.fatture_righe` e valorizzano `fattura_riga_id`; `fatturato = true`.
6. **Chiusura batch**: `lock_in_fatturazione` e `lock_batch_id` garantiscono isolamento durante la corsa.

---

### Periodo di competenza & regole di fatturabilità

* `competenza_mese` → **competenza mensile** obbligatoria, al **1° giorno del mese**:
  rappresenta l’**anno/mese di fatturazione**. Come `competenza_dal`, `competenza_al` e
  `posticipa_al`, la copia dalla sua riga di commessa chi emette l’attività
  ([vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)),
  e la riga di commessa la porta già nella forma giusta (il suo `CHECK` sul primo del mese).
  Se `posticipa_al` è valorizzata, sposta l’attività al **nuovo anno/mese** di fatturazione.

  * **Regola**: non fatturare **prima** di quel mese.
* `competenza_dal` / `competenza_al` → competenza **a intervallo** (es. periodo consumi).
* `posticipa_al` → **rimanda** l’eleggibilità al prelievo a una data futura.
* `sospesa = true` → riga **temporaneamente esclusa** dai prelievi, a prescindere dalla competenza.

Tipico filtro di eleggibilità per il motore:

* `approvato = true`
* `fatturato = false`
* `sospesa = false`
* `posticipa_al IS NULL OR posticipa_al <= data_fatturazione`
* rispetto della competenza (`competenza_mese` <= mese fatturazione **oppure** `competenza_al` <= data fatturazione).

---

### Campi chiave (uso applicativo)

* **Identificazione & riferimenti**:
  `uid` (identificativo applicativo), `articolo_id` (servizio/voce), `istanza_utility_id` (punto tecnico), `billing_account_id` (**obbligatorio** — l'intestazione economica), `area_geografica_id` (opz. area di fatturazione).
  `commessa_id` (testata della commessa) e `commessa_attivita_id` (riga di commessa), entrambe
  obbligatorie: sono la provenienza dell'attività (vedi «La provenienza è la riga di commessa»).
* **Dati attività**:
  `data_attivita`, `quantita`, `meta` (estensioni specifiche: matricole, rilevazioni, tariffa applicata, ecc.).
* **Competenza & gating**:
  `competenza_mese`, `competenza_dal`, `competenza_al`, `posticipa_al`, `sospesa`.
* **Stato di processo**:
  `approvato`, `fatturato`, `lock_in_fatturazione`, `lock_batch_id`, `fattura_riga_id` (consumo su documento).
* **Batch alimentazione**:
  `attivita_consumi_id` (testata consumi legacy), `emit_batch_id` (la corsa di emissione), `commessa_id`/`commessa_attivita_id` (il percorso standard).
* **Identità**:
  `uid` (identità applicativa), unica.
* **Governance**:
  `tx_id`, `storicizza`, `user_*`, `data_*`.
* **Economiche & tipo documento**:
  `tipo_doc_fiscale_id`, `valuta_id`, `prezzo_unitario` (snapshot economico),
  `prezzo_bloccato` (freeze prezzo da override/policy).
  Se non è passato, il tipo documento si ricava dal tipo del documento d'origine della riga di commessa (`COMMESSA` quando la riga non ne dichiara uno).
  `natura_doc_id` (fattura, nota di credito, nota di debito) viene dalla commessa;
  `natura_dal_segno` (rev 2026-10-31) marca l'attività che è diventata `NOTA_CREDITO` perché il
  suo documento somma negativo
  ([vendite.fn_lotto_natura_dal_segno](/dbzero/vendite/manual/fn_lotto_natura_dal_segno)): quando
  torna libera ([vendite.fn_libera_attivita_fatturabili](/dbzero/vendite/manual/fn_libera_attivita_fatturabili))
  o viene riemessa dalla commessa riprende la natura `FATTURA` e la marca cade.
* **Misure**:
  `uom_id` (u.m. base), `qta_operativa` (quantita operativa), `uom_operativa_id` (u.m. operativa), `factor_to_base` (fattore conversione verso base).

---

### Il fattore verso la base

`factor_to_base` dice quante unità base vale un'unità della riga. Non ha più un default: un
«1 quando non so» faceva passare 3 cartoni come 3 pezzi.

* **Il fattore scritto si rispetta**: è la fotografia che l'emissione copia dall'attività di
  commessa.
* **Senza fattore** lo legge `vendite.trgfn_attivita_fattore_alla_data`, alla data
  dell'attività (`data_attivita`), per l'unità operativa, o per l'unità della riga se
  l'operativa non c'è, o per l'unità base se non c'è nessuna delle due: 1 per la base, la
  mappatura dell'articolo o la conversione generale in vigore quel giorno per le altre.
* **Senza neanche quello** la riga è rifiutata con `E_UOM_MISSING`, sul campo dell'unità.
* Se un aggiornamento cambia l'unità e non il fattore, il fattore si rilegge per l'unità nuova.

La quantità base (`quantita`) la porta chi scrive: la tabella non la ricalcola.

---

### Vincoli, indici e trigger (logica)

* **Vincoli**:

  * `chk_attivita_competenza_mese_primo`: il giorno di `competenza_mese` deve essere **1**.
  * `chk_attivita_competenza_range`: intervallo `competenza_dal`/`competenza_al` coerente e include `data_attivita`.
* **FK principali**:

  * `articolo_id` → `catalogo.articoli`.
  * `billing_account_id` → `anagrafiche.billing_account` (**NOT NULL** dal 2026-09-10, `ON UPDATE CASCADE`).
    ⚠️ Questa riga diceva «nullable, `ON DELETE SET NULL`»: **erano due cose false**. La nullabilità è caduta con il changeSet `20260910-25`; l'`ON DELETE SET NULL` non c'è mai stato sul vincolo vivo, che non dichiara nessuna azione di cancellazione.
  * `istanza_utility_id` → `anagrafiche.istanze_utilities`.
  * `commessa_id` → `vendite.commesse`, `commessa_attivita_id` → `vendite.commesse_attivita` (entrambe **NOT NULL**).
* **Indici utili al motore**:

  * `ix_attivita_articolo_flags` (articolo + flag `approvato`/`fatturato`).
  * `ix_attivita_billing_competenza` (BA + competenza mensile).
  * `ix_attivita_istanza_data` (istanza + data attività).
  * `ix_attivita_fatturabili_posticipa_sospesa`, `ix_attivita_fatturabili_lock`, `ix_attivita_fatturabili_fattura_riga_id`.
  * **Unique** `uq_attivita_fatturabili_commessa_attivita` su `commessa_attivita_id` → una riga di commessa genera al più un'attività.
* **Trigger**:

  * `trg_attivita_fatturabili_normalize_ins_upd` → risolve `tipo_doc_fiscale_id` (dal tipo d'origine della riga di commessa) e `valuta_id` quando mancanti.
  * `trg_attivita_fatturabili_a10_guard_ba_coerenza_ins_upd` → **coerenza BA/istanza**: la riga e il suo billing account devono nominare la stessa istanza di utility.
    🔴 Fino al 2026-09-10 **non validava niente**: usciva subito quando `commessa_attivita_id` era valorizzato, e quella colonna è obbligatoria — quindi l'uscita valeva per ogni riga. Corretto dal changeSet `20260910-26`.
  * `trg_attivita_fatturabili_a10_guard_commessa_ins_upd` → coerenza col segmento commessa (`commessa_id`/`commessa_attivita_id`).
  * `trg_attivita_fatturabili_a10_guard_fatturato_upd_dlt` → **fail‑fast**: blocca update/delete se già collegate a fattura.

---

### ⭐ La provenienza è la riga di commessa

L'attività fatturabile **non porta le colonne `sorgente_*`** del modello della provenienza:
nasce sempre da una riga di commessa, e la punta con una **FK vera**, `commessa_attivita_id`,
obbligatoria e unica. Da dove venga la merce o il servizio (il documento d'origine, la sua
riga) lo dice la riga di commessa, con la sua provenienza tipizzata; chi ne ha bisogno la
legge da lì, con un join sulla FK.

* **Niente guard della sorgente**: esistenza e cancellazione le tiene la FK, che il guard unico
  non migliorerebbe.
* **Niente copia della provenienza**: una seconda copia del tipo o della chiave sulla riga
  dell'attività sarebbe una seconda verità, da tenere allineata alla riga di commessa.
* **Unicità**: l'indice unico su `commessa_attivita_id` fa sì che una riga di commessa non
  generi due attività.

---

### Best practice operative

* Imporre `approvato = true` come prerequisito di fatturabilità (workflow di approvazione esplicito).
* Usare `posticipa_al` per rinviare selettivamente righe **senza** perdere la tracciabilità del motivo (`exclude_reason`).
* Evitare update manuali su righe già collegate a `fattura_riga_id`; i trigger **bloccano** modifiche distruttive.

---

### Importanza nel sistema

Questa tabella è il **cuore del ciclo di fatturazione**: tutte le voci da fatturare convergono qui, vengono qualificate per **quando** fatturare (competenza, posticipo, sospensione) e, una volta prelevate, diventano **dettaglio di fattura**.
La qualità e la coerenza dei dati in `vendite.attivita_fatturabili` determinano direttamente **completezza, correttezza e ripetibilità** dei documenti emessi.

---

### Snapshot pricing (v5, 14-04-2026)

Le 8 colonne snapshot pricing presenti su [`vendite.commesse_attivita`](/dbzero/vendite/tabelle/commesse_attivita) sono **propagate identiche** su questa tabella per mantenere la tracciabilita' fino al layer di fatturazione. La valorizzazione avviene durante `fn_emit_attivita_fatturabili_da_commessa` (copia diretta dei campi snapshot dall'attivita' sorgente).

| Colonna                          | Tipo          | Note                                                                                    |
| -------------------------------- | ------------- | --------------------------------------------------------------------------------------- |
| `prezzo_base_snapshot`           | numeric(22,10)| Prezzo base listino prima della variazione                                              |
| `origine_prezzo`                 | varchar(32)   | `PROMO` \| `CONTRATTO_OVERRIDE` \| `CONTRATTO_LISTINO` \| `CATEGORIA` \| `MANUALE`      |
| `tipo_variazione_applicata`      | varchar(16)   | `PERCENTUALE` \| `VALORE_FISSO` \| `PREZZO_FISSO` \| `NESSUNA`                          |
| `valore_variazione_applicata`    | numeric(10,4) | Valore della variazione effettivamente applicata                                        |
| `promo_id`                       | bigint        | FK a `vendite.promo_articoli`                                                           |
| `contratto_id`                   | bigint        | FK a `vendite.contratti`; il contratto è del conto di fatturazione della commessa (guard `trgfn_attivita_guard_contratto`) |
| `categoria_cliente_id_snapshot`  | smallint      | FK a `anagrafiche.categorie_clienti`                                                    |
| `classe_utenza_id_snapshot`      | integer       | FK a `config.classi_utenze`                                                             |

CHECK sui domini di `origine_prezzo` e `tipo_variazione_applicata`. Indice dedicato su `origine_prezzo` per filtri dashboard.

---

### Riga di listino coerente (15-10-2026)

`listino_riga_id` (copiata dall'emissione, aggiornata dal riallineamento del prezzo) deve essere
una riga di listino dello stesso articolo e della stessa unità di misura dell'attività, di un
listino dell'azienda della commessa e di una versione non in bozza (dal 16-10-2026). Questa
tabella non porta la versione: conta quella della riga di listino. Lo tiene
[vendite.trgfn_attivita_guard_listino_riga](/dbzero/vendite/manual/trgfn_attivita_guard_listino_riga)
(`E_ATTIVITA_LISTINO_RIGA_INCOERENTE`), lo stesso guard della commessa.

---

### Registro della riga: `tipo_movimento` (17-07-2026)

Insieme alle 8 colonne dello snapshot pricing, l'emissione propaga 1:1 anche
`tipo_movimento` — il **registro** della riga: `NORMALE` (merce/servizio che rispecchia il
documento d'origine), `ONERE` (voce di valore caricata dalla porta dedicata, quantita' 1
fissa), `RETTIFICA` (riservato ai conguagli futuri). CHECK sul dominio, come per
`origine_prezzo`.

Serve qui, e non solo sulla commessa, perche' **il conto della merce si fa su questa
tabella**: il contatore della fatturazione (`tenuti − fatturati`) somma le quantita' delle
sole righe `NORMALE`, e l'esistenza stessa della riga di attivita' fatturabile e' la prova
che quella merce e' stata emessa. Se il registro vivesse solo sulla commessa, il contatore
dovrebbe risalire la catena per sapere se sta guardando merce o un onere.

Semantica e razionale completi: [`vendite.commesse_attivita`](/dbzero/vendite/tabelle/commesse_attivita),
sezione "Registro della riga".

---

### Note di migrazione

* 2026-02-24 — `commessa_id` e `commessa_attivita_id` diventano obbligatorie; l'indice unico
  d'idempotenza sulla sorgente (`uq_attivita_fatturabili_v_sorgente_fk`) lascia il posto a
  `uq_attivita_fatturabili_commessa_attivita`.
* 2026-02-25 — staccato il guard polimorfo della sorgente: nel flusso che passa sempre dalla
  commessa la FK `commessa_attivita_id` garantiva già il padre.
* 2026-11-07 — ritirate le colonne `sorgente_tipo_id`, `sorgente_uid`, `sorgente_riga` (col
  suo default 0) e `sorgente_origine_tipo_id`, con le loro FK: erano una copia della riga di
  commessa e un'impronta d'idempotenza che nessuno leggeva più. La provenienza si legge dalla riga di
  commessa (brief-db-sorgente-documento-e-riga).
* 2026-11-10 — `factor_to_base` perde il `DEFAULT 1`; il fattore lo copia l'emissione dalla
  commessa, e se manca lo legge il trigger alla data dell'attività (brief-db-revisione-catalogo,
  giro 2-bis).

---

{% include-markdown "signature-core.md" %}
