## 📘 Documentazione Concettuale – Tabella `vendite.attivita_fatturabili`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)    
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)   
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)   
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)   
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)   
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)   
> • [vendite.note](/dbzero/vendite/tabelle/note)   

---
### 🎯 Scopo Principale
(latest review 21-01-2026)
`vendite.attivita_fatturabili` è il **registro centrale delle prestazioni/attività da fatturare** (time & material, canoni, una‑tantum, letture/consumi valorizzati, import batch, ecc.).
Ogni riga rappresenta **una voce fatturabile** riferita a un *articolo/servizio*, a una *istanza tecnica/utility* e, opzionalmente, a un *billing account*.
Queste righe sono **pre‑documentali**: quando il ciclo di fatturazione le preleva, diventano **righe di fattura** (`vendite.fatture_righe`).

Obiettivi principali:

* **Accentramento** della sorgente di verità per tutto ciò che va fatturato.
* **Controllo del periodo di competenza** (mensile o a intervallo) per stabilire **quando** fatturare.
* **Tracciabilità** dallo *stato bozza → approvato → fatturato* con blocchi anti‑doppia fatturazione.
* **Idempotenza** degli import/import batch tramite coppia (`sorgente_tipo_id`, `sorgente_uid`).

---

### Collocazione nel flusso di fatturazione

1. **Acquisizione**: le attività arrivano da input manuali, sistemi esterni, motori di calcolo o letture; vengono registrate qui con `data_attivita`, `quantita`, riferimenti a `articolo_id`, `istanza_utility_id`, `billing_account_id` (**obbligatorio**).
2. **Normalizzazione/validazione** (trigger): allineamento della competenza mensile, coerenze su sorgente, BA e istanza.
3. **Approvazione**: il flag `approvato` abilita l’eleggibilità al prelievo.
4. **Selezione per fatturazione**: il motore estrae le righe **non fatturate**, **non sospese**, **non posticipate** e **in competenza** (vedi paragrafo successivo).
5. **Generazione documento**: le righe selezionate generano entries su `vendite.fatture_righe` e valorizzano `fattura_riga_id`; `fatturato = true`.
6. **Chiusura batch**: `lock_in_fatturazione` e `lock_batch_id` garantiscono isolamento durante la corsa.

---

### Periodo di competenza & regole di fatturabilità

* `competenza_mese` → **competenza mensile** obbligatoria (sempre valorizzata) e al **1° giorno del mese** (es. `YYYY‑MM‑01`).
  Rappresenta l’**anno/mese di fatturazione**. Se non valorizzata, viene derivata
  da `posticipa_al` (se presente). Non viene derivata da `data_attivita`.
  Se `posticipa_al` e` valorizzata, sposta l’attivita al **nuovo anno/mese** di fatturazione.

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
  Con modello commessa attivo:
  `commessa_id` (testata), `commessa_attivita_id` (riga commessa).
* **Dati attività**:
  `data_attivita`, `quantita`, `meta` (estensioni specifiche: matricole, rilevazioni, tariffa applicata, ecc.).
* **Competenza & gating**:
  `competenza_mese`, `competenza_dal`, `competenza_al`, `posticipa_al`, `sospesa`.
* **Stato di processo**:
  `approvato`, `fatturato`, `lock_in_fatturazione`, `lock_batch_id`, `fattura_riga_id` (consumo su documento).
* **Batch alimentazione**:
  `lotto_attivita_id` (lotto alimentazione legacy), `attivita_consumi_id` (testata consumi legacy), `commessa_id`/`commessa_attivita_id` (nuovo percorso standard).
* **Idempotenza import**:
  `uid` (identita` applicativa) e `sorgente_tipo_id`, `sorgente_uid` (vincolo unico parziale per evitare duplicazioni dai sistemi esterni).
* **Governance**:
  `tx_id`, `storicizza`, `user_*`, `data_*`.
* **Economiche & tipo documento**:
  `tipo_doc_fiscale_id`, `valuta_id`, `prezzo_unitario` (snapshot economico),
  `prezzo_bloccato` (freeze prezzo da override/policy).
  In fase di alimentazione il tipo documento segue l’ordine: sorgente → utility (fallback).
  `natura_doc_id` (fattura, nota di credito, nota di debito) viene dalla commessa;
  `natura_dal_segno` (rev 2026-10-31) marca l'attività che è diventata `NOTA_CREDITO` perché il
  suo documento somma negativo
  ([vendite.fn_lotto_natura_dal_segno](/dbzero/vendite/manual/fn_lotto_natura_dal_segno)): quando
  torna libera ([vendite.fn_libera_attivita_fatturabili](/dbzero/vendite/manual/fn_libera_attivita_fatturabili))
  o viene riemessa dalla commessa riprende la natura `FATTURA` e la marca cade.
* **Misure & dettaglio sorgente**:
  `sorgente_riga` (riferimento tecnico riga sorgente), `uom_id` (u.m. base), `qta_operativa` (quantita operativa), `uom_operativa_id` (u.m. operativa), `factor_to_base` (fattore conversione verso base).

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
  * `sorgente_tipo_id` → `config.sorgenti`.
* **Indici utili al motore**:

  * `ix_attivita_articolo_flags` (articolo + flag `approvato`/`fatturato`).
  * `ix_attivita_billing_competenza` (BA + competenza mensile).
  * `ix_attivita_istanza_data` (istanza + data attività).
  * `ix_attivita_fatturabili_posticipa_sospesa`, `ix_attivita_fatturabili_lock`, `ix_attivita_fatturabili_fattura_riga_id`.
  * **Unique parziale** `uq_attivita_fatturabili_v_sorgente_fk` su (`sorgente_tipo_id`, `sorgente_uid`) *WHEN* `sorgente_tipo_id IS NOT NULL` → **idempotenza import**.
* **Trigger**:

* `trg_attivita_fatturabili_normalize_ins_upd` → **normalizza** `competenza_mese` al 1° del mese (obbligatoria, derivata da `posticipa_al` se assente), imposta `sorgente_riga` a `0` se `sorgente_tipo_id` è valorizzato e risolve `tipo_doc_fiscale_id`/`valuta_id` quando mancanti.
  * `trg_attivita_fatturabili_a10_guard_ba_coerenza_ins_upd` → **coerenza BA/istanza**: la riga e il suo billing account devono nominare la stessa istanza di utility.
    🔴 Fino al 2026-09-10 **non validava niente**: usciva subito quando `commessa_attivita_id` era valorizzato, e quella colonna è obbligatoria — quindi l'uscita valeva per ogni riga. Corretto dal changeSet `20260910-26`.
  * `trg_attivita_fatturabili_a10_guard_commessa_ins_upd` → coerenza col segmento commessa (`commessa_id`/`commessa_attivita_id`).
  * `trg_attivita_fatturabili_a10_guard_fatturato_upd_dlt` → **fail‑fast**: blocca update/delete se già collegate a fattura.

---

### ⚠️ Validazione polimorfa della sorgente — NON attiva (decisione, non dimenticanza)

> Registrato qui (doc permanente) perché i brief migrano in work-done —
> decisioni Tid 2026-02-25 e 2026-07-18.

Le colonne `sorgente_tipo_id` / `sorgente_riga` / `sorgente_uid` **non hanno un
guard polimorfo di esistenza**. Storia:

* `20251026-02`: agganciato `trg_attivita_fatturabili_a10_guard_fonte_ins_upd`
  (guard polimorfo, oggi `script.trgfn_guard_sorgente_polimorfa_tipizzata`).
  ⚠️ Il changeSet **droppa e ricrea quel nome di trigger**, che fino a quel
  momento apparteneva a `vendite.trgfn_attivita_fatturabili_guard_fonte`: da lì
  quella funzione è rimasta **orfana in silenzio** — il trigger col suo nome
  continuava a esistere, puntato a un'altra funzione. Nessuno se n'è accorto per
  nove mesi, finché non l'ha trovata `plpgsql_check`
  ([brief-db-bonifica-riferimenti-morti](/dev/work-done/brief-db-bonifica-riferimenti-morti) F1).
  Droppata da `20260804-48`: nominava anche una tabella e una colonna che non
  esistono più, quindi non avrebbe potuto girare nemmeno riagganciandola;
* `20260225-45`: **rimosso deliberatamente** — nel flusso commessa-only la
  sorgente è sempre COMMESSA e la FK `commessa_attivita_id` garantisce già il
  padre; il probe polimorfo era ridondante;
* 2026-07-18 (brief-db-guard-sorgente-polimorfa, D6): **confermato staccato**.

**Condizione di riaggancio** — rivalutare `trgfn_guard_sorgente_polimorfa_tipizzata`
il giorno in cui un flusso scriverà attività fatturabili **non** commessa-only
(import esterni diretti, sorgenti documento senza segmento commessa): solo lì il
guard aggiunge protezione che la FK non dà. Prerequisiti già censiti per quel
giorno:

1. **semantica `sorgente_riga`**: qui NON è la chiave del modello A — il trigger
   normalize la imposta a `0` (sentinella «nessuna riga specifica») quando
   `sorgente_tipo_id` è valorizzato, e il guard tipizzato com'è oggi la
   interpreterebbe come id documento (fallendo sempre su 0). Va risolto il
   conflitto (togliere la sentinella o adattare il guard);
2. drop del DEFAULT 0 su `sorgente_riga`;
3. verifica dei writer (le fn di generazione attività);
4. regressione pgTAP (~20 file toccano questa tabella).

---

### Esempi d’uso (query applicative)

```sql
-- 1) Selezione righe eleggibili per il ciclo del mese M
SELECT *
FROM vendite.attivita_fatturabili a
WHERE a.approvato
  AND NOT a.fatturato
  AND NOT a.sospesa
  AND (a.posticipa_al IS NULL OR a.posticipa_al <= :data_fatturazione)
  AND a.competenza_mese <= date_trunc('month', :data_fatturazione);

-- 2) Marcatura come fatturato (eseguita dal motore dopo creazione riga fattura)
UPDATE vendite.attivita_fatturabili
SET fatturato = true,
    fattura_riga_id = :fattura_riga_id,
    user_update = current_user,
    data_update = now()
WHERE id = ANY(:ids);
```

---

### Best practice operative

* Imporre `approvato = true` come prerequisito di fatturabilità (workflow di approvazione esplicito).
* Usare `posticipa_al` per rinviare selettivamente righe **senza** perdere la tracciabilità del motivo (`exclude_reason`).
* Evitare update manuali su righe già collegate a `fattura_riga_id`; i trigger **bloccano** modifiche distruttive.
* Per import esterni, popolare **sempre** `sorgente_tipo_id` + `sorgente_uid` per ottenere **idempotenza** e facilitare il retry.

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
