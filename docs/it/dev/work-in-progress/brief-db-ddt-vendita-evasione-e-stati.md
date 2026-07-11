# Brief DB — DDT vendita: evasione da ordine, multi-DDT e macchina a stati

> **Tipo**: brief DB (target `dev/db-tid`) · **Data**: 2026-07-09 · **Owner**: Tid
> **Design-of-record**:
> [analisi-ddt-vendita-stato-e-sviluppi.md](analisi-ddt-vendita-stato-e-sviluppi.md)
> (mappa stato, regole di business, decisioni D-1..D-4 / A-1..A-3).
> **Gate**: BE/FE partono a oggetti DB applicati ([[feedback_be_fe_attende_prerequisiti_db]]).
> **Azioni DB al team DB** ([[feedback_db_actions_passaggio_team]]): questo brief
> descrive *cosa* implementare; DDL/fn/trigger/pgTAP li scrive il team DB su
> `dev/db-tid` (Liquibase v2, un changeSet per file, `runOnChange` per fn/trigger).
>
> **Vedi anche**: [/dbzero/vendite/tabelle/ddt](/dbzero/vendite/tabelle/ddt) ·
> [ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment) ·
> [fn_push_preventivo_a_ordine](/dbzero/vendite/funzioni/fn_push_preventivo_a_ordine)
> (pattern doc→doc di riferimento) ·
> [config.transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini) (mirror).
>
> **✅ STATO: CHIUSO — REALIZZATO E COMMITTATO** — slice principale (write-side + read-side,
> 2026-07-09) **+ addendum scope §15** (colonna emittente memorizzata + RLS `rls_ddt_ef_whitelist`
> + vista, 2026-07-10) applicati e **committati** su `dev/db-tid` (`114185433`), pgTAP verdi, doc
> manual/auto-gen rigenerata. Consuntivo §14; addendum realizzato §15. Le sezioni §1-§13 sono il
> capitolato; §14/§15 sono ciò che è stato effettivamente fatto. **Unico residuo = slice RESI
> (§12), FUTURA e separata** (predisposizione già in essere, non parte di questa slice).

---

## 1. Scopo

Attivare a livello DB il **DDT di vendita da ordine (evasione)**, con **multi-DDT**
per consegne parziali e **macchina a stati data-driven**, così che il DDT possa
**transitare in commessa** per la fatturazione differita. Il DDT standalone (senza
ordine) è coperto dallo stesso modello (testata con `billing_account` proprio, senza
`sorgente_uid`): non richiede una fn dedicata, solo la CRUD BE.

## 2. Decisioni recepite (dal design-of-record)

| #   | Decisione                                              | Impatto DB                                                                                    |
| --- | ------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| A-1 | **Multi-DDT per ordine** (consegne parziali)           | Rimuovere l'unicità `un DDT per sorgente` sulla testata (§3)                                  |
| A-2 | **Copia snapshot ordine** (no ri-risoluzione resolver) | `fn_genera_ddt_da_ordine` copia prezzi/componenti dall'ordine (§4)                            |
| A-3 | **Stati con RESO**                                     | `config.transizioni_stati_ddt` con `DRAFT→EMESSO→SPEDITO→CONSEGNATO→RESO` (+`ANNULLATO`) (§5) |

**Decisioni DB (Tid, 2026-07-09)** — rifiniture emerse dall'analisi critica sul codice vivo,
recepite nelle sezioni sotto:

| #   | Decisione                                                                           | Impatto DB                                                        |
| --- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| C1  | Testata DDT: sorgente = **ORDINE_VENDITA** (id 6), non DDT_VENDITA                  | §4.3 — condizione perché `trgfn_ddt_normalize` erediti il billing |
| C2  | Enforcement residuo = **guard esistente** (`E_QTA_SUPERA_RESIDUO`), no nuovo codice | §4.2 — niente logica duplicata                                    |
| C3  | Idempotenza = **predicato residuo + lock del guard**, nessun token                  | §4.7                                                              |
| C5  | `PARZIALMENTE_EVASO` nuovo + `EVASO` invariato + formula reso-aware                 | §4 (sync stato) + §12                                             |
| C6  | Numero DDT assegnato a **EMESSO** (no buchi fiscali), non in DRAFT                  | §4.3 + §6                                                         |
| C8  | Snapshot A-2 completo: aggiungere `sconto_percentuale` + `iva_id` a `ddt_righe`     | §3 + §4.4                                                         |

## 3. Modifica modello — abilitare multi-DDT

Oggi `vendite.ddt` ha UNIQUE **`uq_ddt_v_sorgente_fk`** su
`(sorgente_tipo_id, sorgente_uid) WHERE sorgente_tipo_id IS NOT NULL` → **un solo
DDT per ordine**. Per le consegne parziali servono **N DDT per ordine**.

- **Rimuovere la UNIQUE** `uq_ddt_v_sorgente_fk` e sostituirla con un **indice
  non-unique** `ix_ddt_v_sorgente` su `(sorgente_tipo_id, sorgente_uid)` (lookup
  DDT-per-ordine e MV restano performanti).
- **Invarianti che restano** (non toccare): UNIQUE `(anno, serie, numero)`,
  UNIQUE `uid`, UNIQUE fulfillment `(ordine_riga_id, ddt_riga_id)`.
- `trgfn_ddt_normalize` (eredità billing da `ordini.uid`) continua a funzionare con
  più DDT che condividono lo stesso `sorgente_uid`: **verificare** che non assuma
  unicità. ⚠️ **Attenzione C1**: `trgfn_ddt_normalize` eredita `billing_account_id/
  utility_id/valuta_id` **solo se** la sorgente è `ORDINE_VENDITA` — quindi la fn deve
  scrivere `sorgente_tipo_id = ORDINE_VENDITA` (id 6), non `DDT_VENDITA`. Con `DDT_VENDITA`
  l'eredità billing NON scatta (bug silenzioso). Vedi §4.3 e §7 (allineamento a `codice_interno`).

**Colonne mancanti su `ddt_righe` (C8 — snapshot A-2 completo).** `ordini_righe` ha
`sconto_percentuale` e `iva_id` a livello di riga; `ddt_righe` **no**. Copiare lo snapshot
senza queste colonne perderebbe sconto e IVA di riga. **Aggiungere a `vendite.ddt_righe`**:
`sconto_percentuale numeric` e `iva_id bigint` (+ FK a `config.iva`), così la copia A-2 (§4.4)
è 1:1 anche su questi campi. (I componenti CASO A sono già 1:1: `ordini_righe_componenti` e
`ddt_righe_componenti` hanno colonne identiche a meno di `riga_ordine_id`↔`riga_ddt_id`.)

> ⚠️ Il progetto non è in produzione: breaking change ammesso, nessuna fase di
> compatibilità ([[project_no_produzione_solo_sviluppo]]).

## 4. Funzione di evasione — `vendite.fn_genera_ddt_da_ordine`

Pattern di riferimento: [`fn_push_preventivo_a_ordine`](/dbzero/vendite/funzioni/fn_push_preventivo_a_ordine)
(copia righe, snapshot, idempotenza di riga, transizione atomica, link sorgente).

**Firma proposta** (il team DB affini tipi/nomi):

```
vendite.fn_genera_ddt_da_ordine(
  p_ordine_id      bigint,
  p_righe          jsonb DEFAULT NULL,   -- [{ordine_riga_id, qta_da_evadere}], NULL = tutto il residuo
  p_data           date  DEFAULT CURRENT_DATE,
  p_emittente_sr_id bigint DEFAULT NULL  -- per snapshot componenti CASO A
) RETURNS bigint   -- ddt_id creato
```

**Logica (atomica, una funzione madre — DB-first):**

1. **Guard**: ordine esiste e in stato che ammette evasione (CONFERMATO/…); `p_ordine_id > 0`.
2. **Residuo per riga (C2 — no logica duplicata)**: `residuo = ordini_righe.quantita −
   COALESCE(Σ qta_evasa in ordini_righe_fulfillment, 0)` (nota: la colonna è `quantita`, non
   `quantita_ordinata`). La fn usa il residuo **solo per decidere** quanto evadere:
   `min(richiesto, residuo)`, righe con residuo 0 → saltate. **L'enforcement dell'over-shipping
   NON va reimplementato nella fn**: lo fa già `trgfn_ordini_ful_guard_consistenza` all'INSERT
   del fulfillment, con lock `FOR UPDATE` (serializzazione anti over-fulfillment concorrente) e
   `E_QTA_SUPERA_RESIDUO`. Riusare quel codice — **non** registrare `E_DDT_EVASIONE_ECCEDE_RESIDUO`.
3. **Crea testata** `vendite.ddt`: **`sorgente_tipo_id` = ORDINE_VENDITA (id 6, C1)** —
   NON `DDT_VENDITA`, altrimenti `trgfn_ddt_normalize` non eredita il billing; `sorgente_uid`
   = `ordini.uid`; stato iniziale `DRAFT`. Billing/utility/valuta ereditati da
   `trgfn_ddt_normalize`. **Numerazione (C6): il `numero` NON si assegna in DRAFT** ma alla
   transizione a EMESSO (no buchi fiscali) — `trgfn_ddt_gen_codice` va modificato di conseguenza
   (assegna solo se stato = EMESSO), verificando l'interazione col lock su `numero`
   (`trg_ddt_a10_lock_columns_upd`, che deve consentire il primo valore all'emissione).
4. **Crea righe** `vendite.ddt_righe` **copiando lo snapshot dell'ordine (A-2)**:
   `articolo_id`, `descrizione`, `uom_operativa_id`, `factor_to_base`,
   **`prezzo_unitario`, `sconto_percentuale`, `iva_id` copiati dalla riga ordine** (C8: le ultime
   due sono le colonne nuove di §3), `quantita`/`qta_operativa` = qta evasa. ⚠️ Verificare che
   `ddt_righe` non abbia un trigger che ricalcoli/azzeri il prezzo del padre composito dai
   componenti (come accade sugli ordini): sovrascriverebbe lo snapshot copiato (C9).
5. **Componenti CASO A (A-2)**: per le righe composite, **copiare** i
   `ordini_righe_componenti` nella `ddt_righe_componenti` (snapshot prezzo, coeff,
   iva, origine_prezzo, stato_approvazione), **senza** richiamare il resolver. Se
   servisse comunque un ramo di ri-init, esiste [`fn_ddt_riga_componenti_init`](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_init)
   — ma per A-2 la strada è la copia.
6. **Crea fulfillment** `vendite.ordini_righe_fulfillment(ordine_riga_id,
   ddt_riga_id, qta_evasa)` per ogni riga → è ciò che "collega" DDT e ordine e
   alimenta `mv_ddt_ordini`.
7. **Idempotenza (C3 — nessun token, come i push preventivo/ordine)**: la coppia fulfillment
   `(ordine_riga_id, ddt_riga_id)` NON è una chiave di idempotenza (ogni chiamata crea un DDT
   nuovo → coppia sempre nuova). L'idempotenza è data dal **residuo**: rieseguire "tutto il
   residuo" salta ciò che è già evaso; se tutto a 0 → `E_DDT_NIENTE_DA_EVADERE`. La **concorrenza**
   (doppio submit) è coperta dal `FOR UPDATE` del guard: la seconda chiamata trova residuo 0 e
   fallisce con rollback atomico dell'intera fn. Una chiamata con quantità esplicita resta una
   consegna **deliberata** (responsabilità del chiamante) — coerente con `p_righe_ids` di
   `fn_push_preventivo_a_ordine`.
8. **Refresh MV**: lasciare a `dbops.fn_refresh_mv_ddt_ordini` (job/allineamento), non nella fn.

**Errori** (registrare in `error_policies.py` lato BE): `E_DDT_ORDINE_NOT_FOUND`,
`E_DDT_ORDINE_STATO_NON_EVADIBILE`, `E_DDT_NIENTE_DA_EVADERE` (tutte le righe a residuo 0).
L'over-shipping **non** ha un codice proprio: lo solleva il guard fulfillment con
`E_QTA_SUPERA_RESIDUO` (C2) — quel codice va comunque registrato in `error_policies.py`.

**Sync stato ordine (DECISO 2026-07-09, Tid).** Il flusso-DDT introduce il nuovo stato
`config.stati_doc_ordini.PARZIALMENTE_EVASO` (`fase=IN_CORSO`, `terminale=false`, `esito`
allineato alla convenzione esito-proiezione). `EVASO` **resta invariato** (`terminale=true`)
e viene riusato per "spedizione completa": NON va flippato a `terminale=false` perché è
load-bearing — `ordini_service.py` lo assegna dopo il push a commessa (flusso CONFERMATO,
guard re-push `_STATI_PUSHABILI={CONFERMATO}`) e `terminale` risale in `script.vw_stato_sorgente`
(proiezione stato dominio). La riapertura da reso si abilita **via matrice**, non toccando
`terminale` (il guard `trgfn_ordini_guard_transizione` legge solo la matrice).

- **Predicato residuo (reso-aware fin da ora):** `vendite.fn_ordine_ha_residuo_evasione(p_ordine_id)`
  = TRUE se almeno una riga ha `residuo > 0`, con
  `residuo = quantita − Σ qta_evasa + Σ qta_resa_per_riconsegna` (l'addendo reso è 0 finché
  non atterra la slice resi — vedi §12 — ma la formula non si riscrive più).
- **Proiezione stato in `fn_genera_ddt_da_ordine` (atomica, specchio §8 di `fn_push_preventivo_a_ordine`):**
  `residuo pieno → CONFERMATO`, `0 < residuo < pieno → PARZIALMENTE_EVASO`, `residuo = 0 → EVASO`.
- **Matrice `transizioni_stati_ordini` da seedare:** `CONFERMATO→PARZIALMENTE_EVASO`,
  `PARZIALMENTE_EVASO→EVASO` (attive); `CONFERMATO→EVASO` già presente (id 4);
  `EVASO→PARZIALMENTE_EVASO`, `EVASO→CONFERMATO`, `PARZIALMENTE_EVASO→CONFERMATO` (attive,
  **predisposte reso**: seedate ma non percorse finché non c'è il motore resi).
- **`qta_evasa` è immutabile (append-only):** il reso non la scala mai, è un movimento con segno
  separato (vedi §12). Non introdurre doppio push: la fatturazione la fa il DDT (§8), non l'ordine.

## 5. Macchina a stati DDT — `config.transizioni_stati_ddt` (A-3)

**Mirror di `config.transizioni_stati_ordini`** (stessa forma):
colonne `id, stato_da_id, stato_a_id, attivo, meta jsonb, audit`; UNIQUE
`(stato_da_id, stato_a_id)`; CHECK `stato_da_id <> stato_a_id`; CHECK `meta_ui`
(payload UI per azioni data-driven: label/icona/severity, come ordini); FK a
`config.stati_doc_ddt`; trigger `child_requires_active_parent` su entrambi i lati.

**Seed matrice** (stati da [stati_doc_ddt.csv](../../db/changelog/migrations_v2/80_data/sql/config/stati_doc_ddt.csv): DRAFT=1, EMESSO=2, SPEDITO=4, CONSEGNATO=5, RESO=7, ANNULLATO=6):

| stato_da   | stato_a    | note                              |
| ---------- | ---------- | --------------------------------- |
| DRAFT      | EMESSO     | emissione (gate componenti, §6)   |
| DRAFT      | ANNULLATO  |                                   |
| EMESSO     | SPEDITO    |                                   |
| EMESSO     | ANNULLATO  |                                   |
| SPEDITO    | CONSEGNATO |                                   |
| SPEDITO    | RESO       | reso da spedito                   |
| CONSEGNATO | RESO       | reso da consegnato                |
| CONSEGNATO | ANNULLATO  | (valutare: annullo post-consegna) |

`meta.ui` per label/icona/severity delle azioni (data-driven, come
`available_actions` di ordini — così il FE non hardcoda i pulsanti).

**Guard transizione (C7)**: trigger `_a10_` su `vendite.ddt` `UPDATE OF stato_doc_ddt_id`
che verifica la coppia `(vecchio, nuovo)` contro la matrice attiva (fail-fast
`E_STATO_DDT_TRANSIZIONE_NON_VALIDA`). Non esiste un helper generico condiviso: gli ordini
usano una fn dedicata `trgfn_ordini_guard_transizione` (legge la matrice, no-op se lo stato non
cambia) — **specchiarla** in `vendite.trgfn_ddt_guard_transizione` che legge
`config.transizioni_stati_ddt`. Nota: è un trigger **distinto** dal guard approvazione di §6;
i due `_a10_` coesistono su `UPDATE OF stato_doc_ddt_id` (come sugli ordini). Grep dei pgTAP
esistenti prima di agganciarlo (i DDT sono oggi dormienti → rischio basso).

## 6. Gate emissione — wiring `trgfn_ddt_guard_transizione_approvazione`

La funzione [`trgfn_ddt_guard_transizione_approvazione`](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione_approvazione)
**esiste ma non è agganciata** al DDT. Va registrato il trigger su `vendite.ddt`
`UPDATE OF stato_doc_ddt_id` che, sulla transizione a **EMESSO**, blocca se esistono
componenti CASO A con `stato_approvazione_prezzo='PENDING'`
(`E_COMPONENTE_PREZZO_PENDENTE`) o `prezzo_unitario IS NULL`
(`E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`). Simmetrico al guard testata del preventivo.

> **Numerazione a EMESSO (C6).** La transizione a EMESSO è anche il punto in cui si assegna il
> `numero` DDT (no buchi fiscali da bozze scartate): `trgfn_ddt_gen_codice` va reso condizionale
> allo stato EMESSO invece di assegnare all'INSERT in DRAFT. Coordinare l'ordine di esecuzione
> dei `_a10_` (transizione, approvazione, gen_codice/lock) perché il primo `numero` passi il lock.

## 7. Rifinitura gap (stesso brief)

- **Seed `config.causali_trasporto`** (oggi CSV vuoto): almeno il set standard IT
  (vendita, c/visione, reso, riparazione, campionatura, trasferimento…). **Verificare
  anche il seed di `config.aspetti_beni`** (referenziato da `ddt.aspetto_bene_id`).
- **`trgfn_ddt_normalize`**: risolve la sorgente per `codice` (mutabile) → allineare a
  **`codice_interno`** (immutabile), come `fn_list_ddt_da_pushare` (robustezza lookup).
- **Documentare `mv_ddt_ordini`** in `/dbzero/vendite/…` (manual) e **correggere il
  manual `ddt.md`** (colonne inesistenti: `data_documento`, `soggetto_destinatario_id`).

## 8. Invariante XOR push (ordine vs DDT) — da presidiare

Quando `ordini.fatturazione_trigger ∈ {SPEDITO, CONSEGNATO}`: **pusha il DDT, non
l'ordine**. Verificare che [`fn_list_ordini_da_pushare`](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare)
**escluda** gli ordini con trigger ≠ CONFERMATO (no doppia fatturazione), e che
[`fn_list_ddt_da_pushare`](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare) resti
l'unica sorgente per quel perimetro. È l'invariante più delicata dell'intero giro.

> ✅ **Verificato (2026-07-09):** `fn_list_ordini_da_pushare` **già** filtra
> `AND o.fatturazione_trigger = 'CONFERMATO'` (oltre a stato CONFERMATO), e
> `fn_list_ddt_da_pushare` è già l'unica sorgente per SPEDITO/CONSEGNATO. L'XOR è quindi
> **già presidiato**: nessun intervento sulle fn, serve solo il **test pgTAP di regressione**
> (§10 caso 6) per congelarlo.
>
> ⚠️ **Incompleto (2026-07-10):** questa verifica copriva solo la direzione «no *doppia*
> fatturazione». Manca la direzione «no fatturazione *persa*»: un ordine `trigger=CONFERMATO`
> evaso in DDT prima del push resta **orfano** (né ordine né DDT eleggibili). Fix in **§16**.

## 9. Predisposizione PDF (D-3) — garantire ora

Perché la fase PDF sia "solo FE o poco più":
- Snapshot indirizzi completo su `ddt_indirizzi.snapshot` (mittente/destinatario/vettore);
- Causali/aspetti/porto **seedati** (§7) e valorizzabili sulla testata;
- Note-stampa via `note_ddt.solo_stampa` già presenti;
- Eventuale riepilogo colli/pesi/volume calcolato o valorizzabile in testata.
Nessun oggetto PDF ora: solo completezza dati.

## 10. pgTAP — casi di verifica

Contesto RLS operatore (`SET app.ruolo_applicativo='OPERATORE'; SET app.current_user_id='1';`).

1. **Multi-DDT**: 2 evasioni parziali sullo stesso ordine → 2 DDT distinti, fulfillment
   con `qta_evasa` che somma al totale ordinato; over-shipping → `E_QTA_SUPERA_RESIDUO`
   (sollevato dal guard fulfillment, C2).
2. **Copia snapshot (A-2)**: `ddt_righe.prezzo_unitario` == riga ordine; componenti
   CASO A copiati 1:1 (coeff, prezzo, origine_prezzo) senza chiamare il resolver.
3. **Fulfillment/MV**: dopo l'evasione, `mv_ddt_ordini(ddt_id, ordine_id)` popolata (post-refresh).
4. **Matrice stati**: transizioni ammesse ok; transizione fuori matrice →
   `E_STATO_DDT_TRANSIZIONE_NON_VALIDA`; `security`/`require_attivo` sugli stati.
5. **Gate emissione**: DRAFT→EMESSO bloccato con componente PENDING o prezzo NULL.
6. **XOR push**: ordine con trigger SPEDITO **non** compare in `fn_list_ordini_da_pushare`;
   il DDT a SPEDITO compare in `fn_list_ddt_da_pushare`.
7. **Idempotenza**: doppia esecuzione con residuo invariato non duplica.
8. **Sync stato ordine (C5)**: evasione parziale → ordine a `PARZIALMENTE_EVASO`; evasione
   dell'ultimo residuo → ordine a `EVASO`; ordine flusso-DDT (trigger≠CONFERMATO) mai in
   `fn_list_ordini_da_pushare` durante il ciclo. Verificare che la transizione sia atomica con
   la creazione DDT (rollback se fallisce).
9. **Numero a EMESSO (C6)**: DDT in `DRAFT` ha `numero IS NULL`; alla transizione a `EMESSO` il
   `numero` viene assegnato e bloccato; un DRAFT annullato non consuma numerazione.

## 11. Downstream (dopo l'applicazione DB)

- **BE** (`brief-be-ddt-vendita.md`): `ddt_service` + repository (testata/righe) +
  endpoint CRUD/emissione/stati + `POST /ordini/<id>/genera-ddt` (chiama
  `fn_genera_ddt_da_ordine`) + `/ddt/da-pushare` + note DDT (~3 righe) + registrazione
  `error_policies` dei nuovi codici.
- **FE** (`brief-fe-ddt-vendita.md`): lista `<ListaConfigurabile>` + drawer
  master-detail (stile preventivi/ordini/contratti, D-4) + azione "genera DDT" nel
  drawer ordine + navigazione/rotta/store.
- **Lineage**: il nodo DDT_VENDITA si accende nella `vw_documento_lineage` già progettata.

## 12. Slice futura — Resi (DOCUMENTATA, fuori da questa slice)

> **Stato**: NON implementata in questa slice. Qui si fissa solo la **predisposizione**
> (invarianti dati) perché la slice resi si riprenda senza rework né strati da rimuovere.
> Decisione Tid 2026-07-09: il reso è un **ibrido** — non solo nota di credito, ma anche
> "reso per ri-consegna" (es. merce difettosa da ri-preparare e ri-spedire).

**Perché il RESO-come-stato del DDT non basta.** Nella matrice DDT (§5) `RESO` è uno stato
tutto-o-niente sull'intero DDT: non porta né la **quantità** resa (reso parziale: rendo 3 di 10)
né l'**intento** (credito | ri-consegna). Il motore resi richiede entrambe le informazioni,
quindi un modello dedicato, non un flip di stato.

**Invarianti già garantite da questa slice (non modificare in seguito):**

1. **`ordini_righe_fulfillment.qta_evasa` è immutabile / append-only.** Il reso NON scala
   `qta_evasa` (distruggerebbe lo snapshot "cosa è stato spedito con quel DDT" + lo storico).
   Il reso è un **movimento separato con segno**.
2. **`fn_ordine_ha_residuo_evasione` è già reso-aware:** la formula
   `residuo = quantita − Σ qta_evasa + Σ qta_resa_per_riconsegna` è scritta ora; l'addendo reso
   oggi è 0. Quando la slice resi lo alimenterà, il residuo si riapre da solo e il gate stato
   (`PARZIALMENTE_EVASO`/`EVASO`) non si riscrive.
3. **Stati ordine e matrice già predisposti (§4):** le transizioni di rientro
   `EVASO→PARZIALMENTE_EVASO`, `EVASO→CONFERMATO`, `PARZIALMENTE_EVASO→CONFERMATO` sono già
   seedate e attive (non percorse finché non c'è il motore resi). `EVASO` resta `terminale=true`:
   nell'istante è terminale (le dashboard sono statistiche point-in-time), il reso lo riapre via
   transizione senza toccare `terminale`.

**Da costruire nella slice resi (deferred):**

- **Discriminatore data-driven `config.tipi_reso`** con flag `riapre_residuo boolean`
  (es. `RESO_A_CREDITO` → `false`, `RESO_PER_RICONSEGNA` → `true`). Nessun `IF` hardcoded:
  il motore legge il flag. Definirlo qui (vocabolario) è predisposizione a costo ~nullo, ma
  l'alimentazione e il consumo restano nella slice resi.
- **Modello reso con righe/quantità** (reso parziale di riga) che linka `ordine_riga_id`/DDT
  di origine e valorizza `qta_resa_per_riconsegna` (l'addendo del punto 2 sopra).
- **Branch di esito:** `RESO_A_CREDITO` → alimenta la pipeline nota di credito;
  `RESO_PER_RICONSEGNA` → riapre il residuo (già assorbito dalla formula) → l'ordine torna a
  `PARZIALMENTE_EVASO` e un nuovo DDT diventa generabile.

**Riferimenti incrociati:** §4 (predicato residuo + proiezione stato ordine), §5 (stato RESO nella
matrice DDT), analisi-ddt §1.2 (i resi non-vendita vivono su `magazzino`; qui il perimetro è la
riapertura evasione + l'aggancio alla nota di credito).

## 13. Appendice — Read-side per BE/FE (segnalazione team BE, 2026-07-09)

> **Gap del capitolato Fase 1.** La Fase 1 (§1-§10) copre il **write-side** (evasione,
> macchina a stati, seed). Ma lista e azioni di stato lato BE/FE richiedono una **read-side**
> che oggi non è specificata. Senza questi tre oggetti, `<ListaConfigurabile>` non ha colonne
> da rendere e il drawer non ha azioni. Vanno aggiunti al perimetro DB (nuovi changeSet, stessa
> slice o companion). Annotati anche nel brief BE (§2/§9) e FE (§10).

Tutti e tre sono **mirror 1:1** di oggetti già esistenti per gli ordini — nessuna logica nuova,
solo replica del pattern sul dominio DDT (regola del 2 / no duplicazione):

1. **`vendite.vw_ddt_lista`** — view canonica lista/dettaglio, mirror di
   [`vw_ordini_lista`](/dbzero/vendite/views/vw_ordini_lista). Espone testata DDT + join
   denormalizzati per la lista: stato (`codice_interno`/`descrizione` da `stati_doc_ddt`),
   destinatario (`ragione_sociale_completa`), billing/emittente/utility/valuta (codici),
   causale/aspetto/modalità trasporto, campi logistici (colli/pesi/vettore), sorgente
   (ordine di provenienza via `sorgente_uid`). Alias FEDELI alla sorgente
   (`codice_interno AS stato_codice_interno`, `codice AS stato_codice` — linee-guida-sql §6c).
   `security_invoker=on` (RLS del chiamante, come le altre viste lista vendite). Target `20_code`.

2. **`script.fn_available_actions_ddt`** — capabilities data-driven, mirror di
   `script.fn_available_actions_ordine`. Legge `config.transizioni_stati_ddt` filtrando per lo
   stato corrente del DDT e restituisce le azioni ammesse (`action_key`, `label_key`, `severity`,
   `icon`, `requires_confirm`, `outlined` da `meta.ui`) — così il FE **non hardcoda** i pulsanti
   di transizione. È il lato-lettura simmetrico al guard `trgfn_ddt_guard_transizione` (§5): stessa
   matrice, un lato la valida (write), l'altro la espone (read). Target `20_code/script`.

3. **Seed config lista per `vendite.ddt`** (`ui.lista_definizione` + colonne) — mirror del seed
   lista di ordini/preventivi/contratti. Senza la definizione lista e l'elenco colonne
   selezionabili (con `priorita` per il ritiro dinamico responsive, [[project_ui_schema_status]]),
   `<ListaConfigurabile>` non ha nulla da rendere. Alimenta la lista DDT a partire da
   `vw_ddt_lista` (punto 1). Target `80_data` (append CSV se i loader `ui.*` sono runOnChange,
   altrimenti nuovo loader — verificare come per ordini).

**Impatto sul piano.** Tre changeSet aggiuntivi in Fase 2/3 (2 in `20_code`, 1 in `80_data`),
tutti mirror — bassa incertezza. pgTAP: smoke su `fn_available_actions_ddt` (azioni coerenti con
la matrice) e presenza colonne lista. Gate BE/FE invariato: partono a read-side applicata.

## 14. Consuntivo realizzazione (2026-07-09)

Slice DB realizzata e applicata su `dev/db-tid`, **non committata** (attendere "procedi").

### ChangeSet (17, `20260709-01..17`)

| #     | Oggetto                                                                                           | Fase                    |
| ----- | ------------------------------------------------------------------------------------------------- | ----------------------- |
| 01    | swap UNIQUE→indice `ix_ddt_v_sorgente` (multi-DDT, A-1)                                           | `00_schema/vendite`     |
| 02    | `config.transizioni_stati_ddt` (matrice, A-3)                                                     | `00_schema/config`      |
| 03    | `ddt_righe` +`sconto_percentuale`/`iva_id` (C8)                                                   | `00_schema/vendite`     |
| 04    | `trgfn_ddt_guard_transizione` + trigger (C7)                                                      | `20_code/vendite`       |
| 05    | crea+aggancia `trgfn_ddt_guard_transizione_approvazione` (§6)                                     | `20_code/vendite`       |
| 06    | `trgfn_ddt_normalize` per `codice_interno` (C1/§7)                                                | `20_code/vendite`       |
| 07    | protect bespoke `trgfn_v_ddt_protect_num` + disable lock framework (C6)                           | `20_code/vendite`       |
| 08    | `fn_ordine_ha_residuo_evasione` (C5)                                                              | `20_code/vendite`       |
| 09    | **`fn_genera_ddt_da_ordine`** (madre: A-1/A-2/C2/C3/C5)                                           | `20_code/vendite`       |
| 10    | seed matrice `transizioni_stati_ddt` (+CSV)                                                       | `80_data`               |
| 11-12 | seed `causali_trasporto` + `aspetti_beni` (+CSV)                                                  | `80_data`               |
| 13    | *(superato da 14)* trigger gen_codice su stato                                                    | `20_code/vendite`       |
| 14    | **numero a EMESSO bespoke** `trgfn_ddt_gen_numero_emesso` + `usa_sequenza=false` (mirror fatture) | `20_code/vendite` + CSV |
| 15    | `vw_ddt_lista` (read-side §13)                                                                    | `20_code/vendite`       |
| 16    | `fn_available_actions_ddt` (read-side §13)                                                        | `20_code/script`        |
| 17    | seed priorità colonne lista `ui` DDT (+CSV)                                                       | `80_data`               |

**Append CSV** (loader runOnChange): `stati_doc_ordini` (+`PARZIALMENTE_EVASO`), `transizioni_stati_ordini`
(+5 righe, incl. rientri reso predisposti), `messaggi_errore` (521-524: `E_DDT_ORDINE_NOT_FOUND`,
`E_DDT_ORDINE_STATO_NON_EVADIBILE`, `E_DDT_NIENTE_DA_EVADERE`, `E_STATO_DDT_TRANSIZIONE_NON_VALIDA`),
`automation_lock_columns` + `sistema_codici` (DDT fuori dai framework numero/lock).

### pgTAP (VERDI)

- `test-fn-genera-ddt-da-ordine-v1.sql` — evasione end-to-end, **24 casi** (multi-DDT, snapshot A-2,
  fulfillment, sync stato ordine, matrice stati, numero a EMESSO+immutabilità, over-shipping, errori).
- `test-ddt-read-side-v1.sql` — read-side, **15 casi** (vista, azioni data-driven, seed lista, editabilità).

### Documentazione manual (concettuale)

- `vendite/manual/ddt.md` aggiornata (colonne reali, macchina stati data-driven, evasione, numero a
  EMESSO, MV, read-side).
- Nuovi: `config/manual/transizioni_stati_ddt.md`, `vendite/manual/{fn_genera_ddt_da_ordine,
  fn_ordine_ha_residuo_evasione, trgfn_ddt_guard_transizione, trgfn_ddt_guard_transizione_approvazione,
  trgfn_ddt_gen_numero_emesso, trgfn_v_ddt_protect_num, vw_ddt_lista}.md`,
  `script/manual/fn_available_actions_ddt.md`. (L'auto-gen dbzero la rigenera Tid.)

### Scostamenti dal capitolato emersi in realizzazione

- **C1**: `trgfn_ddt_normalize` risolveva la sorgente per `codice` **e** l'analisi/brief indicavano
  `sorgente_tipo_id=8 (DDT_VENDITA)` — errato: deve essere **ORDINE_VENDITA** (id 6) o l'eredità
  billing non scatta. Corretto in 06 + fn 09.
- **§6**: `trgfn_ddt_guard_transizione_approvazione` risultava **assente** sul DB (non solo "non
  wired" come da §2.1 dell'analisi): il changeSet 05 la **crea** oltre ad agganciarla.
- **C6 (numero a EMESSO)**: percorso non lineare — il numero è gestito end-to-end dal framework
  `sistema_codici` (riga→funzione→trigger, rigenerati, numera all'INSERT) e dal framework lock. La
  soluzione robusta (14) è il **mirror fatture**: DDT fuori da `sistema_codici` (`usa_sequenza=false`)
  + numerazione bespoke a EMESSO + protect condizionale. I passi 07 (override funzione) e 13 sono
  **superati** da 14 (changelog forward-only).

## 15. Addendum SCOPE — RLS e emittente su DDT (rilievo BE, 2026-07-10) — ✅ REALIZZATO

> **Rilievo emerso in verifica pre-sviluppo BE.** La lista DDT aveva un **buco di scope
> emittente**: `vendite.ddt` **senza RLS** (saltò l'Ondata 2 perché dormiente) e `vw_ddt_lista`
> **senza `emittente_fiscale_id`** → con `security_invoker=on` ma senza RLS sulla base, ogni
> operatore avrebbe visto i DDT di tutti gli emittenti. Regressione rispetto a ordini/preventivi.

**Soluzione realizzata (opzione migliorativa "emittente MEMORIZZATO", mirror ordini/preventivi)**,
committata su `dev/db-tid` `114185433`:

1. **`ALTER vendite.ddt ADD emittente_fiscale_id`** (bigint **NOT NULL**, FK
   `fk_ddt_v_emittente_fiscale`, indice via FK-policy).
2. **`trgfn_ddt_normalize` esteso**: eredita `emittente_fiscale_id` dall'**ordine sorgente**
   (accanto a billing/utility/valuta); per lo **standalone** lo risolve dal `billing_account` via
   `anagrafiche.fn_get_emittente_fiscale_pk`.
3. **RLS `rls_ddt_ef_whitelist`** su `vendite.ddt` (FOR ALL, scope `script.fn_scope_ef_whitelist`
   sui GUC operatore, enabled non forced — parità ordini/preventivi/fatture) + guard scrittura.
4. **`vw_ddt_lista` + `emittente_fiscale_id`/`emittente_fiscale_codice`** (filtro applicativo BE).
5. **pgTAP** `test-rls-ddt-ef-whitelist-write.sql`.

**Recepito lato BE (2026-07-10):** filtro applicativo emittente attivo in `DdtRepository.list_ddt`;
`_resolve_emittente_sr_id` legge la colonna memorizzata; `crea_ddt` richiede `billing_account_id`
(condizione perché il trigger valorizzi l'emittente NOT NULL). Vedi brief BE §2/§12.

## 16. Addendum FIX — «orfano da push» su ordine trigger CONFERMATO evaso (rilievo 2026-07-10) — ✅ REALIZZATO

> ✅ **Applicato dal team DB (2026-07-10, `piano-db-fix-orfano-push-ordine-confermato.md`,
> merge #962)**: `fn_list_ordini_da_pushare` estesa (stati CONFERMATO/PARZIALMENTE_EVASO/EVASO
> per trigger CONFERMATO) + `fn_available_actions_ordine` v2 (riusa la fn lista come fonte
> unica; reason `ORDINE_GIA_EVASO` rimosso, nuovi `ORDINE_FATTURA_DA_DDT`/`ORDINE_GIA_FATTURATO`)
> + pgTAP v2/v3. **Recepito BE (2026-07-10)**: `_STATI_PUSHABILI` esteso in `ordini_service`
> (guard applicativo allineato, +2 unit test). **Verificato live**: ORD0000163 recuperato —
> push COMPLETATO → commessa 191 PRONTA_FATTURAZIONE (3 attività).

> **Rilievo emerso in verifica in-app (giro preventivo→ordine→DDT).** Un ordine con
> `fatturazione_trigger = CONFERMATO` **evaso in DDT prima di essere pushato** resta
> **orfano**: né l'ordine né il DDT sono eleggibili al push → documento **non fatturabile**,
> non raccolto da alcun batch. È una falla dell'invariante XOR (§8): §8 presidiava la
> direzione «no doppia fatturazione», **non** la direzione «no fatturazione persa».

**Repro (dati reali, 2026-07-10).** `ORD0000163` (id 174, `trigger=CONFERMATO`) → `genera-ddt` →
`DDT0000031` (id 55, da ordine). Dopo l'evasione:

- ordine → **EVASO** → `fn_list_ordini_da_pushare(174)` = **0 righe** (richiede stato CONFERMATO);
- `DDT0000031` (SPEDITO, ordine-sourced, `src_trigger=CONFERMATO`) → `fn_list_ddt_da_pushare(55)` =
  **0 righe** (la fn esclude `src_fatturazione_trigger = 'CONFERMATO'`);
- `commesse_attivita` per ORD e DDT = **0** (mai pushato).

→ **Nessuna delle due sorgenti può pushare. Documento bloccato.** (Verificato anche via
`script.fn_available_actions_ordine(174)` → `can_push_commessa=false`, e `fn_available_actions_ddt(55)`
→ azioni `consegna`/`reso`, niente `push_commessa`.)

**Causa radice.** Per `trigger=CONFERMATO` la sorgente di fatturazione è **l'ordine** (il DDT è
escluso by design da `fn_list_ddt_da_pushare`). Ma l'eleggibilità dell'ordine è vincolata allo stato
**CONFERMATO**, e l'evasione (`fn_genera_ddt_da_ordine`, §4 proiezione stato) lo porta a
**PARZIALMENTE_EVASO/EVASO** → chiude la finestra di push. Spedizione (evasione) e
fatturazione-su-conferma sono ortogonali, ma il modello oggi le accoppia.

### Fix C — l'eleggibilità push dell'ordine sopravvive all'evasione (solo trigger CONFERMATO)

1. **`vendite.fn_list_ordini_da_pushare`** — rilassare il solo vincolo di stato: ammettere
   `stato_doc_ordine.codice_interno ∈ {CONFERMATO, PARZIALMENTE_EVASO, EVASO}` (risolti **per
   `codice_interno`**, convenzione 2026-06-28, mai id hardcoded) **al posto** del solo
   `= CONFERMATO` (oggi `v_stato_confermato_id`). Invariato tutto il resto: filtro
   `fatturazione_trigger='CONFERMATO'`, `NOT EXISTS (... stato_emissione='EMESSA')`, guard righe
   attive/qta/prezzo.
2. **`script.fn_available_actions_ordine`** (capability read-side) — allineare
   `can_push_commessa` / azione `push_commessa` alla **stessa** condizione, così il drawer ordine
   mostra il pulsante anche in PARZIALMENTE_EVASO/EVASO finché l'ordine non è pushato. Le due fn
   devono restare **coerenti** (eleggibilità reale == capability mostrata).

**Perché è SICURO (XOR preservato, nessuna doppia fatturazione).** Il rilassamento tocca **solo**
gli ordini con `fatturazione_trigger='CONFERMATO'` (già filtrati dalla fn). Per quel trigger il DDT
ordine-sourced è **già escluso** da `fn_list_ddt_da_pushare` (`!= 'CONFERMATO'`): l'ordine resta
l'**unica** sorgente del perimetro, nessun rischio che ordine e DDT pushino lo stesso segmento. Il
`NOT EXISTS ... EMESSA` continua a impedire il re-push. Gli ordini `trigger ∈ {SPEDITO,CONSEGNATO}`
non sono toccati (il filtro trigger li esclude comunque): per loro pusha il DDT, come oggi.

**Perimetro di fatturazione.** Per `trigger=CONFERMATO` si fattura l'**ordine confermato** (righe/qta
ordinate), indipendentemente dallo stato di spedizione — coerente con «fattura su conferma». Il DDT
resta puro documento di trasporto (anche in PARZIALMENTE_EVASO il push fattura l'intero ordine).

**Precondizioni da verificare.** Esistenza dei `codice_interno` `PARZIALMENTE_EVASO` / `EVASO` in
`config.stati_doc_ordini`.

### pgTAP di regressione (estende §10, casi 7-9)

- **Caso 7 — recupero orfano**: ordine `trigger=CONFERMATO` → `fn_genera_ddt_da_ordine` (evasione
  piena) → ordine EVASO → `fn_list_ordini_da_pushare(ordine_id)` ritorna **≥1**; dopo push
  (`stato_emissione='EMESSA'`) la re-list ritorna **0** (idempotenza / no doppione).
- **Caso 8 — XOR preservato**: lo stesso DDT ordine-sourced (`src_trigger=CONFERMATO`) **non**
  compare in `fn_list_ddt_da_pushare` (resta escluso: unica sorgente = ordine).
- **Caso 9 — non-regressione SPEDITO**: ordine `trigger=SPEDITO` evaso → `fn_list_ordini_da_pushare`
  = 0 (filtro trigger), DDT eleggibile a SPEDITO — invariato.

### Recepimento a valle

Nessuna modifica BE/FE necessaria: `OrdiniDrawer`/`DdtDrawer` leggono già `available_actions`
data-driven. Risolto il read-side (punto 2), il pulsante «Push a commessa» ricompare sull'ordine.
Verifica in-app su `ORD0000163` (id 174): dopo il fix deve tornare eleggibile.

> ↩︎ **Rettifica a §8**: l'XOR era presidiato solo contro la *doppia* fatturazione; questa slice
> chiude la direzione «orfano» (fatturazione *persa*) mancante in quella verifica.

## 17. Addendum SEED — stampa DDT accompagnatorio (slice PDF, 2026-07-10) — ✅ REALIZZATO

> ✅ **Applicato dal team DB (2026-07-10, `piano-db-seed-tipo-documento-output-ddt.md`,
> merge #962)**: riga 5 `DDT_VENDITA` in `documenti.tipi_documento_output` (CSV 80_data).
> **Post-seed completato (BE, 2026-07-10)**: template **76** «DDT vendita» (sorgente
> DDT_VENDITA, default, emittente 32) + versione **46 PUBBLICATA** con la bozza
> `template-ddt-vendita.html`/`.css`, creati via API admin. **Verificato live E2E**:
> anteprima PDF su DDT esistente (16,9 KB) e giro pieno DDT 61 → riga → emissione
> multipart (DRAFT→EMESSO + documento 124 atomici) → numero `DDT0000034` dal trigger →
> download PDF archiviato (17,2 KB). La catena stampa DDT è OPERATIVA.

**Contesto.** La slice PDF DDT (predisposta in §9) è stata sviluppata lato BE+FE il 2026-07-10:
quinto dominio del motore `documenti` (context builder `DDT_VENDITA` registrato, endpoint
`emetti/` multipart + `documenti/` genera/anteprima/lista/allegati/file sotto
`/api/v1/vendite/ddt/<id>/`, mirror ordini). Il capitolato sotto era la richiesta originaria.

**Richiesta (1 riga di seed).** `documenti.tipi_documento_output`: aggiungere la riga

| id | codice      | codice_interno | descrizione | attivo |
|----|-------------|----------------|-------------|--------|
| 5  | DDT_VENDITA | DDT_VENDITA    | DDT vendita | true   |

via CSV `80_data/sql/documenti/tipi_documento_output.csv` + changelog (stesso pattern della riga 4
ORDINE_VENDITA, 2026-06-04). Senza questa riga non si può creare il template DDT nell'admin
(FK `tipo_documento_output_id`) e l'emissione DDT fallisce nella risoluzione template.

**Nessun altro oggetto DB richiesto**: `config.sorgenti.DDT_VENDITA` esiste già; il corpo del
template è dato runtime (admin UI → Template documentali, come per gli altri domini) — bozza
paste-ready in `docs/it/dev/work-in-progress/template-ddt-vendita.html` + `.css` (layout
accompagnatorio: destinatario/trasporto/merce senza prezzi/colli-pesi/firme; A4 PORTRAIT,
margini standard famiglia).

**Post-seed (a carico Tid/BE, non team DB):** creare il template nell'admin — testata (sorgente
DDT_VENDITA, `context_builder_code=DDT_VENDITA`, `is_default=true`, emittente 32 come i fratelli)
e versione 1 con l'HTML/CSS della bozza → **PUBBLICATA**. Poi verifica in-app: anteprima in bozza
→ emissione con PDF → ristampa da archivio.
## 15. Addendum SCOPE — RLS e emittente su DDT (rilievo BE, 2026-07-10) ⚠️ DA FARE

> **Rilievo emerso in verifica pre-sviluppo BE — VALIDO.** La lista DDT ha un **buco di scope
> emittente**: `vendite.ddt` **non ha RLS** (ha saltato l'Ondata 2 perché dormiente) e
> `vw_ddt_lista` **non espone `emittente_fiscale_id`**. Con `security_invoker=on` ma **senza RLS
> sulla tabella base** la vista non filtra nulla → **ogni operatore vedrebbe i DDT di tutti gli
> emittenti**. Regressione rispetto a ordini/preventivi/contratti.

**Correzione di rotta rispetto alla proposta iniziale.** La proposta BE risolveva l'emittente **a
runtime** dal `billing_account` (in RLS e in vista). È sub-ottimale: (a) una policy con
`fn_get_emittente_fiscale_id(...)` **per riga** non è indicizzabile come il filtro di ordini su
colonna stored; (b) diverge dal pattern — ordini/preventivi **memorizzano** l'emittente
(`emittente_fiscale_id` NOT NULL, FK, indice, guard scope, RLS); (c) copre solo la lettura, non il
**guard di scope in scrittura**. **Si allinea al pattern: memorizzare l'emittente sul DDT.**

**Interventi DB (slice di follow-up, mirror ordini):**

1. **`ALTER vendite.ddt ADD emittente_fiscale_id`** (FK `anagrafiche.emittenti_fiscali`, indice via
   FK-policy). Il DDT nasce da un ordine che **ha già** l'emittente.
2. **Estendere `trgfn_ddt_normalize`**: eredita `emittente_fiscale_id` dall'**ordine sorgente**
   (accanto a billing/utility/valuta già ereditati); per lo standalone lo risolve dal
   `billing_account` via `anagrafiche.fn_get_emittente_fiscale_id`.
3. **RLS su `vendite.ddt`** che filtra sulla colonna **stored** — mirror esatto di `rls_ordini` +
   ef-whitelist (`20260601-37`/`20260603-18`), indicizzato. Ruoli `BYPASSRLS` esenti.
4. **`trgfn_guard_emittente_scope`** in scrittura (mirror ordini/preventivi): un operatore non può
   creare un DDT per un emittente fuori dal suo scope.
5. **`vw_ddt_lista` espone `emittente_fiscale_id` (+ `emittente_fiscale_codice`)** — banale, come
   `vw_ordini_lista` → il repository BE somma `v.emittente_fiscale_id = ANY(script.fn_get_emittenti_scope_pk_ids(auth_user_id))`.

**Decisione aperta**: lo **standalone senza billing** (bozza pre-cliente) — `emittente_fiscale_id`
NOT NULL con risoluzione obbligatoria, oppure nullable con regola di visibilità (creatore/istanza).
Chiudere prima di implementare.

**pgTAP**: "operatore vede solo i DDT dei propri emittenti" (RLS SELECT) + "creazione DDT per
emittente fuori scope bloccata" (guard scrittura).

**Impatto BE**: finché l'addendum non atterra, `DdtRepository.list_ddt` **non** applica il filtro
applicativo emittente (la colonna non esiste); va scritto come mirror di `OrdiniRepository` e il
filtro attivato appena la colonna è disponibile.

> ⚠️ **Non incluso** nei changeSet `20260709-01..17` (write-side + read-side base): è una slice
> aggiuntiva. È **prerequisito** perché la lista DDT sia scope-safe lato BE.

## 15. Addendum SCOPE — RLS e emittente su DDT (rilievo BE, 2026-07-10) ⚠️ DA FARE

> **Rilievo emerso in verifica pre-sviluppo BE.** La lista DDT ha un **buco di scope
> emittente**: `vendite.ddt` **non ha policy RLS** e `vw_ddt_lista` **non espone
> `emittente_fiscale_id`**. Con `security_invoker=on` ma **senza RLS sulla tabella base**,
> la vista non filtra nulla → **ogni operatore vedrebbe i DDT di tutti gli emittenti**.
> Regressione rispetto a ordini/preventivi/contratti (RLS su tabella base **+** colonna
> `emittente_fiscale_id` in vista per il defense-in-depth applicativo, api.md §"Enforcement RLS").

**Il DDT non memorizza l'emittente** (lo risolve a runtime da `billing_account` via
`anagrafiche.fn_get_emittente_fiscale_id`). Due interventi DB, mirror del pattern ordini:

1. **RLS su `vendite.ddt`** — abilitare Row Level Security e policy di scope emittente
   coerente con `vendite.ordini` (l'emittente del DDT = emittente risolto dal suo
   `billing_account_id`; per i DDT senza billing — bozze standalone pre-cliente — definire
   la regola, es. visibili al creatore/istanza). Ruoli `BYPASSRLS` (batch/migrazioni) esenti.
2. **Esporre `emittente_fiscale_id` in `vw_ddt_lista`** (risolto da `billing_account`), come
   `vw_ordini_lista`, così il repository BE può sommare il filtro applicativo
   `script.fn_get_emittenti_scope_pk_ids(auth_user_id)` (defense-in-depth) — senza la colonna
   il BE non può filtrare e resta appeso alla sola RLS.

**Impatto BE**: finché l'addendum non atterra, `DdtRepository.list_ddt` **non** applica il
filtro applicativo emittente (la colonna non esiste). Il metodo va scritto come mirror di
`OrdiniRepository.list_ddt` e il filtro `v.emittente_fiscale_id = ANY(...)` va **attivato**
appena la colonna è disponibile. pgTAP: caso "operatore vede solo i DDT dei propri emittenti".
</content>
