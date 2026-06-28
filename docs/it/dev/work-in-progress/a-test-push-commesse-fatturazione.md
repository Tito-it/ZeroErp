# Test richiesti — Push su commesse + fatturazione (preventivo / ordine / contratto)

> **Tipo**: documento di test operativo (checklist da eseguire). · **Stato**: 🟡 **DA ESEGUIRE**.
> **Data**: 2026-06-20. · Prefisso `a-` per restare in cima alla cartella.
>
> **Scopo**: raccoglie in un punto solo i **test del giro push → commessa →
> fatturazione** per i diversi documenti di vendita. Nasce perché PR1 "push
> singolo" è in produzione ([sviluppo-push-singolo-preventivo.md](../work-done/sviluppo-push-singolo-preventivo.md))
> ma il **giro end-to-end non è mai stato verificato a mano** per ciascun tipo.
>
> **Assorbe** il precedente `promemoria-smoke-conferma-push-ordini.md` (eliminato).
> **Complementare** (non sostituisce) allo **smoke UI E2E pratiche** — quello prova
> il percorso pratica nella dashboard; qui si prova il giro push/fatturazione del
> documento. Vedi [gestione-pratiche-come-procedere.md §2](gestione-pratiche-come-procedere.md).

---

## 1. PREVENTIVO → push commessa → fatturazione

**Stato base**: ✅ **VERDE** end-to-end (smoke 1a + 1b, 2026-06-28). Due fix
abilitanti emersi: (a) script — endpoint M2 rimosso → completamento flusso, +
emittente esplicito; (b) **DB** — bug gate EVASO ramo commessa (residuo ancorato
a `stato_emissione='EMESSA'` invece che all'allocazione), risolto dal team DB
([brief-db-gate-evaso-commessa-asimmetria.md](../work-done/brief-db-gate-evaso-commessa-asimmetria.md),
include §4 BoM + semantica ANNULLATA).

- [x] **Push** (da pratica: CONFERMA del flusso → handler `vendita.push_preventivo`;
      oppure standalone: pulsante "Invia fatturazione" sul preventivo ACCETTATO):
      scrive `vendite.commesse_attivita` + log `commesse_push_log` + `event_log`;
      idempotente via `segment_key`.
- [x] **Split per natura** (riga MERCE→ordine, SERVIZIO una-tantum→commessa,
      RICORRENTE bloccata): le righe finiscono nella destinazione giusta.
- [x] **BoM**: coperto dal fix DB §4 (vista esclude `segment_key` esatto + `#CMP:%`);
      preventivo con righe composite raggiunge EVASO. *(Smoke 1a/1b usano righe non
      composite: conta-componenti specifico non esercitato qui.)*
- [x] **Commessa** → `PRONTA_FATTURAZIONE` con righe `APPROVATA`+`NON_EMESSA`;
      preventivo → `EVASO` (gate EVASO: nessun residuo su NESSUN ramo — ora
      simmetrico ordine/commessa).
- [x] **Giornale** pratica: `DOMINIO_COMMESSA_CREATA` + `DOMINIO_PREVENTIVO_EVASO`.
- [ ] **A valle**: commessa emittibile ✅; pipeline lotto → **fattura** NON coperto
      dallo smoke (blocco DB noto pipeline `1→8`, handoff 0619).
- [ ] **UX**: badge stato fatturazione + pulsante disabilitato post-push — **lato FE,
      non coperto dagli smoke BE** (verifica UI separata).

Smoke esistenti (aggiornati 2026-06-28): `smoke-test-pratica-preventivi-conferma.sh`,
`smoke-test-preventivi-smistamento-ordine.sh`.

## 2. ORDINE → conferma → push commessa → fatturazione

**Stato base**: ✅ **VERDE** (smoke `smoke-test-ordini-giro-commessa.sh`, 2026-06-28)
**sia da super admin sia da operatore reale non-admin** (permessi + azioni di
processo + RLS esercitati, non solo bypass).
Due fix emersi durante lo smoke: (a) script — emittente esplicito nel payload
create (operatore senza emittente assegnato); (b) **BE** — `priorita_operativa`
letta come int ma è varchar (`'NORMALE'`) → 400 su `/commesse/<id>/stato/`,
corretta in `commesse_repository.py` + `types.py` + `views.py` (read=str, 92 test verdi).

- [x] **Conferma** — `POST /api/v1/vendite/ordini/<id>/conferma/`: BOZZA→CONFERMATO
      (guard data-driven sullo stato), `numero` valorizzato/locked.
- [x] **Push** — `POST /api/v1/vendite/ordini/<id>/push/`: crea
      `attivita_fatturabili` + commessa; ponte emittibilità → `PRONTA_FATTURAZIONE`
      con attività approvate ≥ 1.
- [x] **Idempotenza `EVASO`**: dopo il push l'ordine passa a `EVASO`; la seconda
      push è bloccata (`E_ORD_STATO_TRANSIZIONE`) e la capability nasconde il
      bottone (reason `ORDINE_GIA_EVASO`).
- [ ] **A valle**: commessa emittibile ✅ (`PRONTA_FATTURAZIONE` + approvate ≥1);
      lotto → **fattura** NON coperto dallo smoke (fuori scope, blocco DB noto
      pipeline `1→8`, handoff 0619).

Smoke esistente: `smoke-test-ordini-giro-commessa.sh` (passo 8 verifica
`PRONTA_FATTURAZIONE` + approvate ≥ 1).

## 3. CONTRATTO → commessa — ⚠️ scisso: addebito standard ✅ testabile / ricorrente ⛔ rinviato

**Verificato il path reale (2026-06-28):** il contratto **entra nel giro commesse**
come sorgente registrata (`_SORGENTE_FN_MAP["CONTRATTO"] =
"vendite.fn_list_contratti_da_pushare"`, [commesse_repository.py:33](../../../../backend/apps/vendite/db/commesse_repository.py#L33)),
azionata dal push batch `POST /api/v1/vendite/commesse/push/run/`
(`source_types: ["CONTRATTO"]`). **Nessun endpoint/competenza dedicati**: l'handler
risolve la competenza internamente.

### 3a. ⛔ Fatturazione RICORRENTE (canone periodico) — RINVIATA (utilities gas/energia/acqua)

Fa parte della **fatturazione utilities** (gas, energia, acqua, …), sviluppo **fermo,
da fare**. **Allo stato `fn_list_contratti_da_pushare` NON implementa la ricorrenza**:
nessun `generate_series`, emette **1 sola riga per riga-contratto**, con
`competenza_mese` e `:M:` del segment_key = **`date_trunc('month', valido_dal)`**
(mese d'inizio contratto, fisso) — non il periodo fatturato. I campi `periodicita`/
`generazione_canone`/`competenza_canone` su `contratti_righe` esistono ma nessuna fn
li espande. → Lo smoke "push M, poi M+1, 1 attività/mese" **non è scrivibile finché
la generazione canoni non è progettata**. (Nota: stessa anomalia EVASO del §1 —
`AND ca.stato_emissione = 'EMESSA'` nel NOT EXISTS, riga 100 — non propagata qui.)

- [ ] *(rinviato — utilities)* Smoke canone periodico: da scrivere quando la
      generazione canoni per competenza sarà implementata.

### 3b. ✅ Addebito STANDARD (una-tantum, non a canone) — DA TESTARE ORA

L'addebito standard di un contratto ATTIVO → 1 `commesse_attivita` (mese d'inizio) →
commessa emittibile, con idempotenza del push. È implementato: questo si testa.

- [ ] Contratto ATTIVO con riga (addebito standard) → push CONTRATTO →
      1 `commesse_attivita` con `segment_key CONTR:{uid}:R:{riga}:M:{mese-inizio}`,
      commessa → `PRONTA_FATTURAZIONE`; re-run push = nessun doppione (upsert su segment_key).

## 4. Come eseguire

Servono **backend + DB attivi** e un utente con permessi vendite (o super admin per
bypass). Gli smoke bash sono in `backend/scripts/tests/`. Eseguire prima da super
admin (giro funzionale), poi da **operatore reale** (permessi/azioni di processo):

```bash
SMOKE_USER=<operatore_con_whitelist> ./scripts/tests/smoke-test-ordini-giro-commessa.sh '<pwd>'
```

> **Eseguito 2026-06-28**: §2 ordini verde **sia super admin sia operatore reale
> non-admin**. §1 preventivo verde da super admin (operatore reale non rieseguito:
> stesso motore di permessi del giro ordini, già coperto).

## 5. Alla chiusura

Quando un blocco è verde: spuntare le voci; quando **tutti** i blocchi attivi
(preventivo + ordine, e contratto se in scope) sono verdi, aggiornare
[gestione-pratiche-come-procedere.md §2](gestione-pratiche-come-procedere.md) e
spostare questo doc in `work-done/`.
