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

---

## 1. Scopo

Attivare a livello DB il **DDT di vendita da ordine (evasione)**, con **multi-DDT**
per consegne parziali e **macchina a stati data-driven**, così che il DDT possa
**transitare in commessa** per la fatturazione differita. Il DDT standalone (senza
ordine) è coperto dallo stesso modello (testata con `billing_account` proprio, senza
`sorgente_uid`): non richiede una fn dedicata, solo la CRUD BE.

## 2. Decisioni recepite (dal design-of-record)

| # | Decisione | Impatto DB |
|---|---|---|
| A-1 | **Multi-DDT per ordine** (consegne parziali) | Rimuovere l'unicità `un DDT per sorgente` sulla testata (§3) |
| A-2 | **Copia snapshot ordine** (no ri-risoluzione resolver) | `fn_genera_ddt_da_ordine` copia prezzi/componenti dall'ordine (§4) |
| A-3 | **Stati con RESO** | `config.transizioni_stati_ddt` con `DRAFT→EMESSO→SPEDITO→CONSEGNATO→RESO` (+`ANNULLATO`) (§5) |

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
  unicità.

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
2. **Residuo per riga**: per ogni riga ordine, `residuo = quantita_ordinata −
   COALESCE(Σ qta_evasa in ordini_righe_fulfillment, 0)`. Evadere `min(richiesto,
   residuo)`; **errore** se si chiede oltre il residuo (`E_DDT_EVASIONE_ECCEDE_RESIDUO`).
   Righe con residuo 0 → saltate.
3. **Crea testata** `vendite.ddt`: `sorgente_tipo_id`=8 (`DDT_VENDITA`),
   `sorgente_uid`=`ordini.uid`, stato iniziale `DRAFT`. Billing/utility/valuta
   ereditati da `trgfn_ddt_normalize` (già esistente). Numerazione via
   `trgfn_ddt_gen_codice` (già esistente).
4. **Crea righe** `vendite.ddt_righe` **copiando lo snapshot dell'ordine (A-2)**:
   `articolo_id`, `descrizione`, `uom_operativa_id`, `factor_to_base`,
   **`prezzo_unitario` copiato dalla riga ordine**, `quantita`/`qta_operativa` = qta evasa.
5. **Componenti CASO A (A-2)**: per le righe composite, **copiare** i
   `ordini_righe_componenti` nella `ddt_righe_componenti` (snapshot prezzo, coeff,
   iva, origine_prezzo, stato_approvazione), **senza** richiamare il resolver. Se
   servisse comunque un ramo di ri-init, esiste [`fn_ddt_riga_componenti_init`](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_init)
   — ma per A-2 la strada è la copia.
6. **Crea fulfillment** `vendite.ordini_righe_fulfillment(ordine_riga_id,
   ddt_riga_id, qta_evasa)` per ogni riga → è ciò che "collega" DDT e ordine e
   alimenta `mv_ddt_ordini`.
7. **Idempotenza**: rieseguire con lo stesso residuo non deve duplicare (chiave
   naturale: fulfillment `(ordine_riga_id, ddt_riga_id)` + residuo ricalcolato).
8. **Refresh MV**: lasciare a `dbops.fn_refresh_mv_ddt_ordini` (job/allineamento), non nella fn.

**Errori** (registrare in `error_policies.py` lato BE): `E_DDT_ORDINE_NOT_FOUND`,
`E_DDT_ORDINE_STATO_NON_EVADIBILE`, `E_DDT_EVASIONE_ECCEDE_RESIDUO`,
`E_DDT_NIENTE_DA_EVADERE` (tutte le righe a residuo 0).

**Sync stato ordine (da decidere col team DB):** quando il residuo totale dell'ordine
va a 0 (tutto evaso), l'ordine può passare a un sotto-stato "completamente evaso".
Non introdurre doppio push: la fatturazione la fa il DDT (§8), non l'ordine.

## 5. Macchina a stati DDT — `config.transizioni_stati_ddt` (A-3)

**Mirror di `config.transizioni_stati_ordini`** (stessa forma):
colonne `id, stato_da_id, stato_a_id, attivo, meta jsonb, audit`; UNIQUE
`(stato_da_id, stato_a_id)`; CHECK `stato_da_id <> stato_a_id`; CHECK `meta_ui`
(payload UI per azioni data-driven: label/icona/severity, come ordini); FK a
`config.stati_doc_ddt`; trigger `child_requires_active_parent` su entrambi i lati.

**Seed matrice** (stati da [stati_doc_ddt.csv](../../db/changelog/migrations_v2/80_data/sql/config/stati_doc_ddt.csv): DRAFT=1, EMESSO=2, SPEDITO=4, CONSEGNATO=5, RESO=7, ANNULLATO=6):

| stato_da | stato_a | note |
|---|---|---|
| DRAFT | EMESSO | emissione (gate componenti, §6) |
| DRAFT | ANNULLATO | |
| EMESSO | SPEDITO | |
| EMESSO | ANNULLATO | |
| SPEDITO | CONSEGNATO | |
| SPEDITO | RESO | reso da spedito |
| CONSEGNATO | RESO | reso da consegnato |
| CONSEGNATO | ANNULLATO | (valutare: annullo post-consegna) |

`meta.ui` per label/icona/severity delle azioni (data-driven, come
`available_actions` di ordini — così il FE non hardcoda i pulsanti).

**Guard transizione**: trigger `_a10_` su `vendite.ddt` `UPDATE OF stato_doc_ddt_id`
che verifica la coppia `(vecchio, nuovo)` contro la matrice attiva (fail-fast
`E_STATO_DDT_TRANSIZIONE_NON_VALIDA`). Riusare l'eventuale helper generico già usato
dagli ordini se presente.

## 6. Gate emissione — wiring `trgfn_ddt_guard_transizione_approvazione`

La funzione [`trgfn_ddt_guard_transizione_approvazione`](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione_approvazione)
**esiste ma non è agganciata** al DDT. Va registrato il trigger su `vendite.ddt`
`UPDATE OF stato_doc_ddt_id` che, sulla transizione a **EMESSO**, blocca se esistono
componenti CASO A con `stato_approvazione_prezzo='PENDING'`
(`E_COMPONENTE_PREZZO_PENDENTE`) o `prezzo_unitario IS NULL`
(`E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`). Simmetrico al guard testata del preventivo.

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
   con `qta_evasa` che somma al totale ordinato; over-shipping → `E_DDT_EVASIONE_ECCEDE_RESIDUO`.
2. **Copia snapshot (A-2)**: `ddt_righe.prezzo_unitario` == riga ordine; componenti
   CASO A copiati 1:1 (coeff, prezzo, origine_prezzo) senza chiamare il resolver.
3. **Fulfillment/MV**: dopo l'evasione, `mv_ddt_ordini(ddt_id, ordine_id)` popolata (post-refresh).
4. **Matrice stati**: transizioni ammesse ok; transizione fuori matrice →
   `E_STATO_DDT_TRANSIZIONE_NON_VALIDA`; `security`/`require_attivo` sugli stati.
5. **Gate emissione**: DRAFT→EMESSO bloccato con componente PENDING o prezzo NULL.
6. **XOR push**: ordine con trigger SPEDITO **non** compare in `fn_list_ordini_da_pushare`;
   il DDT a SPEDITO compare in `fn_list_ddt_da_pushare`.
7. **Idempotenza**: doppia esecuzione con residuo invariato non duplica.

## 11. Downstream (dopo l'applicazione DB)

- **BE** (`brief-be-ddt-vendita.md`): `ddt_service` + repository (testata/righe) +
  endpoint CRUD/emissione/stati + `POST /ordini/<id>/genera-ddt` (chiama
  `fn_genera_ddt_da_ordine`) + `/ddt/da-pushare` + note DDT (~3 righe) + registrazione
  `error_policies` dei nuovi codici.
- **FE** (`brief-fe-ddt-vendita.md`): lista `<ListaConfigurabile>` + drawer
  master-detail (stile preventivi/ordini/contratti, D-4) + azione "genera DDT" nel
  drawer ordine + navigazione/rotta/store.
- **Lineage**: il nodo DDT_VENDITA si accende nella `vw_documento_lineage` già progettata.
</content>
