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

**Stato base**: PR1 ✅ in produzione (`push_a_commessa` → `pr_run_commesse_push_one`).
Verifica **end-to-end** mai fatta a mano sul giro completo.

- [ ] **Push** (da pratica: CONFERMA del flusso → handler `vendita.push_preventivo`;
      oppure standalone: pulsante "Invia fatturazione" sul preventivo ACCETTATO):
      scrive `vendite.commesse_attivita` + log `commesse_push_log` + `event_log`;
      idempotente via `segment_key`.
- [ ] **Split per natura** (riga MERCE→ordine, SERVIZIO una-tantum→commessa,
      RICORRENTE bloccata): le righe finiscono nella destinazione giusta.
- [ ] **BoM**: riga composita → N `commesse_attivita` (1 per componente esposto in
      fattura), `segment_key` con suffisso `#CMP:{componente_id}`, qta senza rounding.
- [ ] **Commessa** → `PRONTA_FATTURAZIONE` con righe `APPROVATA`+`NON_EMESSA`;
      preventivo → `EVASO` (gate EVASO: solo se nessun residuo merce).
- [ ] **Giornale** pratica: `DOMINIO_COMMESSA_CREATA` + `DOMINIO_PREVENTIVO_EVASO`.
- [ ] **A valle**: `fn_list_commesse_emittibili(competenza)` include la commessa →
      pipeline lotto → **fattura** (mese corrente per IMMEDIATA, mese scelto per DIFFERITA).
- [ ] **UX**: dopo il push il badge stato fatturazione si aggiorna e il pulsante si
      disabilita (no doppio lancio); toast con esito + `push_log_id`.

Smoke esistenti: `smoke-test-pratica-preventivi-conferma.sh`,
`smoke-test-preventivi-smistamento-ordine.sh`.

## 2. ORDINE → conferma → push commessa → fatturazione

**Stato base**: scheletro OdV completo; le **2 transizioni finali non eseguite**.

- [ ] **Conferma** — `POST /api/v1/vendite/ordini/<id>/conferma/`: BOZZA→CONFERMATO
      (guard data-driven sullo stato), `numero` valorizzato/locked.
- [ ] **Push** — `POST /api/v1/vendite/ordini/<id>/push/`: crea
      `attivita_fatturabili` + commessa; ponte emittibilità → `PRONTA_FATTURAZIONE`
      con attività approvate ≥ 1.
- [ ] **Idempotenza `EVASO`**: dopo il push l'ordine passa a `EVASO`; la seconda
      push è bloccata (`E_ORD_STATO_TRANSIZIONE`) e la capability nasconde il
      bottone (reason `ORDINE_GIA_EVASO`).
- [ ] **A valle**: come §1 (commessa emittibile → lotto → fattura).

Smoke esistente: `smoke-test-ordini-giro-commessa.sh` (passo 8 verifica
`PRONTA_FATTURAZIONE` + approvate ≥ 1).

## 3. CONTRATTO → fatturazione ricorrente — 🔍 DA VERIFICARE

A differenza di preventivo/ordine (servizio **una-tantum** → push a commessa), il
contratto modella il **SERVIZIO RICORRENTE**: la fatturazione è **periodica**, non
un push una-tantum. **Prima di scrivere il test va verificato il path reale**:

- [ ] Il contratto attivo entra nel giro **commesse** (come preventivo/ordine) o ha
      un **meccanismo periodico dedicato** (generazione attività/fatture a scadenza)?
      *(Grep iniziale: nessuna `fn_push_contratto_a_commessa` evidente → probabile
      path dedicato.)*
- [ ] Se path dedicato: tracciare il test in una sezione propria (o in un doc
      contratti) — **non forzarlo** in questo giro push una-tantum.

→ Per ora **sezione aperta**: completare dopo aver chiarito il modello di
fatturazione contratti.

## 4. Come eseguire

Servono **backend + DB attivi** e un utente con permessi vendite (o super admin per
bypass). Gli smoke bash sono in `backend/scripts/tests/`. Eseguire prima da super
admin (giro funzionale), poi da **operatore reale** (permessi/azioni di processo).

## 5. Alla chiusura

Quando un blocco è verde: spuntare le voci; quando **tutti** i blocchi attivi
(preventivo + ordine, e contratto se in scope) sono verdi, aggiornare
[gestione-pratiche-come-procedere.md §2](gestione-pratiche-come-procedere.md) e
spostare questo doc in `work-done/`.
