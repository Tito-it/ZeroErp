# Test smoke E2E — Contratto + articolo composito

**Data**: 2026-05-19
**Stato**: checklist operativa per smoke browser post-refactor `ComponentiPanel` data-driven.
**Contesto**: validazione end-to-end dei 3 stream chiusi il 2026-05-19 (note partizionate, cascata parametri `categoria_cliente`, articolo composito su contratti) e del refactor `ComponentiPanel` con prop `initialData` che ha sostituito `ComponentiTableInline` come building block unificato della famiglia componenti BoM.

**Prerequisiti**: dev server attivo (Django + Vite), autenticati come admin con EF associato. Tenere DevTools aperti per ispezione network/console.

---

## Caso 1 — Composito su contratto reale (path felice + refactor `ComponentiPanel` data-driven)

**Obiettivo principale**: validare che il refactor (`ComponentiPanel` in modalità `initialData`) renda correttamente l'expansion della riga `DA_LISTINO` bundle, e che la creazione AGGIUNTA composita funzioni end-to-end.

1. Apri un contratto ATTIVO con listino (es. `CNT0000027` o equivalente). Vai al drawer righe.
2. **Sub-test refactor expansion**: espandi una riga `DA_LISTINO` di un articolo composito (icona freccia).
   - Atteso: la sotto-tabella appare con codice + descrizione + colonna **"Coeff."** (non "Q.tà"!) + UoM + Prezzo + Esposto.
   - Le colonne **Origine / Approvazione / IVA non devono esserci** (auto-hide in modalità preview).
   - Se vedi "Q.tà" come label invece di "Coeff." → bug normalizer.
   - Se vedi colonne Origine/IVA vuote → bug auto-hide colonne metadata.
3. **Sub-test creazione AGGIUNTA composito**: barra azioni → "Aggiungi articolo" → seleziona articolo composito fuori-listino.
   - `ComponentiDialog` si apre (UX invariata dal refactor).
   - Compila prezzi, conferma, salva la riga.
   - Atteso: riga compare in lista con prezzo padre = `SUM(prezzi × coeff)`, `origine=AGGIUNTA`.
4. **Sub-test edit composito**: click sulla nuova riga AGGIUNTA → drawer EDIT.
   - Sotto il form deve apparire `ComponentiPanel` con i figli, **colonne Origine/IVA presenti** (modalità fetch-driven persistito).
   - Label colonna q.tà = **"Q.tà"** (snapshot persistito, non "Coeff.").
   - Edit prezzo di un componente → save → riga padre ricalcolata.

### Query SQL di verifica DB (dopo salvataggio AGGIUNTA)

```sql
SELECT id, articolo_id, quantita, qta_operativa, prezzo_unitario
FROM vendite.contratti_righe
WHERE contratto_id = <ID> AND tipo_eccezione = 'AGGIUNTA'
ORDER BY id DESC LIMIT 1;
-- atteso: quantita = qta_operativa, prezzo_unitario > 0
```

```sql
SELECT componente_id, prezzo_unitario, quantita, origine_prezzo
FROM vendite.contratti_righe_componenti
WHERE riga_contratto_id = <RIGA_ID_SOPRA>;
-- atteso: N righe, una per ogni componente BoM
```

---

## Caso 2 — Composito senza EF risolvibile

**Già coperto da test BE**: [test_create_riga_articolo_composito_senza_emittente_solleva](../../../../backend/apps/vendite/tests/services/test_contratti_service.py#L1850).

In browser serve impersonare un utente che NON ha emittente fiscale risolvibile (admin globale senza EF default per la categoria del BA del contratto).

1. Login con utente di test senza EF default. Se non disponibile: skip — il path è già garantito dal test BE.
2. Apri contratto su BA senza `emittenti_fiscali_billing_account` configurato → barra azioni → "Aggiungi articolo" composito.
3. Atteso: toast/banner rosso `E_VENDITE_VALIDATION` con dettaglio:
   > Inserimento articolo composito non possibile: emittente fiscale non risolvibile per il contratto.
4. **Critico**: verifica che NESSUN padre orfano sia rimasto in DB:

```sql
SELECT id, prezzo_unitario FROM vendite.contratti_righe
WHERE contratto_id = <ID> AND prezzo_unitario = 0
  AND data_insert > now() - interval '1 minute';
-- atteso: zero righe (la transaction.atomic ha rollbackato il padre)
```

---

## Caso 3 — Composito senza `valido_dal`

**Già coperto dal test BE**: [test_create_riga_articolo_composito_senza_valido_dal_solleva](../../../../backend/apps/vendite/tests/services/test_contratti_service.py#L1889).

In browser:

1. Crea contratto DRAFT vuoto. Lascia `valido_dal` non valorizzato (se il form lo permette — controlla i defaults BA-aware in `ApiContrattoFormDefaults`).
2. Tenta AGGIUNTA articolo composito.
3. Atteso: toast/banner rosso `E_VENDITE_VALIDATION` con dettaglio:
   > Inserimento articolo composito non possibile: valorizza prima `valido_dal` sulla testata del contratto.
4. **Nota**: se il form FE valorizza sempre `valido_dal` (default oggi via form-defaults), il caso non è raggiungibile via UI normale — la guard resta puramente difensiva, coperta lato BE.

---

## Caso 4 — Note partizionate (Stream 1)

1. Apri preventivo esistente → bottone "Gestisci note" nel drawer testata → si apre `PreventivoNoteDrawer`.
2. Crea una nota testata (target_riga_id=null): salva, verifica visibile in lista.
3. Apri il drawer righe → seleziona una riga → "Gestisci note" → crea nota di riga.
4. Stessi 2 step per `ContrattoDrawer` → `ContrattoNoteDrawer`.
5. **Verifica drop `meta_note` legacy**: nel `ContrattoDrawer` apri DevTools → Network → PATCH contratto → il payload **non deve** più contenere `meta.note`.

### Query SQL di verifica

```sql
SELECT target_tipo, target_id, target_riga_id, testo, stile_id
FROM vendite.note
WHERE target_tipo IN ('PREVENTIVO', 'CONTRATTO')
  AND data_insert > now() - interval '5 minutes'
ORDER BY data_insert DESC;
-- atteso: 4 righe (2 testata + 2 riga), stile_id valorizzato
-- (fallback parametro NOTE_DEFAULT_STILE applicato dal service)
```

---

## Caso 5 — Override parametro scope `categoria_cliente` (Stream 2 Phase B)

1. Login admin. Vai a `/config/impostazioni` → seleziona un parametro (es. `MAX_SCONTO_PERCENT`).
2. Drawer override → vedi 3 radio scope: Utente / Gruppo / **Categoria cliente** (nuovo dopo Phase B).
3. Seleziona "Categoria cliente" → appare `<LookupSelect rel="anagrafiche.categorie_clienti">`. Seleziona una (es. "Residenziale").
4. Imposta valore, salva.
5. Verifica DB:

```sql
SELECT user_id, gruppo_id, categoria_cliente_id, emittente_fiscale_id,
       codice_interno, value
FROM config.parameter_overrides
WHERE codice_interno = '<CODICE>'
  AND data_insert > now() - interval '5 minutes';
-- atteso: user_id=null, gruppo_id=null, emittente_fiscale_id=null,
-- categoria_cliente_id=<ID scelto>, value=<valore>
```

6. **Sub-test cascata Phase A**: come utente normale (non admin), apri impostazioni e cerca quel parametro. Atteso: colonna **"Categoria cliente"** valorizzata se la categoria del BA dell'utente matcha l'override; vuota altrimenti.

---

## Stato test BE coperti

| Caso | Test BE | File |
|---|---|---|
| 1 | `test_create_riga_articolo_composito_auto_init` | [test_contratti_service.py:1806](../../../../backend/apps/vendite/tests/services/test_contratti_service.py#L1806) |
| 2 | `test_create_riga_articolo_composito_senza_emittente_solleva` | [test_contratti_service.py:1850](../../../../backend/apps/vendite/tests/services/test_contratti_service.py#L1850) |
| 3 | `test_create_riga_articolo_composito_senza_valido_dal_solleva` (nuovo 2026-05-19) | [test_contratti_service.py:1889](../../../../backend/apps/vendite/tests/services/test_contratti_service.py#L1889) |
| 4 | `test_partitioned_note_service.py` (26 test) | [test_partitioned_note_service.py](../../../../backend/apps/core/tests/services/test_partitioned_note_service.py) |
| 5 | `test_parameter_service.py` (5 test categoria_cliente) + `test_parameters_api.py` (6 test) | [test_parameter_service.py](../../../../backend/apps/core/tests/services/test_parameter_service.py) |

**Caso 1 refactor expansion `ComponentiPanel` data-driven**: validabile **solo in browser** (è puro FE — il backend non è cambiato).

---

## Riferimenti

- Handoff sessione: [handoff_20260519_note_categoria_compositi.md](../../../../../../.claude/projects/-home-tid-apps-ZeroErp/memory/handoff_20260519_note_categoria_compositi.md) (memoria locale).
- Refactor BB FE: [catalogo-building-block-frontend.md → ComponentiPanel](../frontend/catalogo-building-block-frontend.md).
- Codice service: [contratti_service.py:1063-1115](../../../../backend/apps/vendite/services/contratti_service.py#L1063).
- Codice pannello: [ComponentiPanel.vue](../../../../frontend/src/vendite/_shared/componenti/ComponentiPanel.vue).
