# Promemoria — Smoke da eseguire: conferma + push ordini di vendita

> **Tipo**: promemoria operativo (TODO test). · **Stato**: 🟡 **DA ESEGUIRE**.
> **Data**: 2026-06-20.
> **Origine**: chiusura dell'analisi ordini di vendita
> ([analisi-ordini-vendita.md](../work-done/analisi-ordini-vendita.md), §7 / §9.bis).
> Lo scheletro OdV è **completo** e spostato in `work-done/`; di tutto lo smoke
> E2E (passo 7) la maggior parte è verde — restano da eseguire **solo le due
> transizioni finali: conferma e push**.

---

## Cosa resta da verificare

- [ ] **Conferma ordine** — `POST /api/v1/vendite/ordini/<id>/conferma/`:
      transizione stato BOZZA → CONFERMATO (guard data-driven sullo stato),
      `numero` valorizzato/locked.
- [ ] **Push a commessa** — `POST /api/v1/vendite/ordini/<id>/push/`:
      crea le `attivita_fatturabili` + commessa, e il **ponte emittibilità**
      porta la commessa a `PRONTA_FATTURAZIONE` con attività approvate ≥ 1.
- [ ] **Idempotenza `EVASO`** — dopo il push l'ordine passa a `EVASO`; la
      seconda push è bloccata (`E_ORD_STATO_TRANSIZIONE`) e la capability
      nasconde il bottone (reason `ORDINE_GIA_EVASO`).

## Come eseguire

Script smoke già presente:

```
backend/scripts/tests/smoke-test-ordini-giro-commessa.sh
```

(il passo 8 verifica `PRONTA_FATTURAZIONE` + attività approvate ≥ 1). Richiede
backend + DB attivi e un utente con permessi vendite (o super admin per bypass).

## Esito atteso

`Ordine BOZZA → [CONFERMA] → CONFERMATO → [PUSH] → attività fatturabile +
commessa emittibile → (pipeline lotto → fattura, già collaudata)`. Re-push
rifiutato (idempotenza `EVASO`).

## Alla chiusura

Quando verde:
1. spuntare le voci sopra;
2. aggiornare §9.bis #5 di
   [analisi-ordini-vendita.md](../work-done/analisi-ordini-vendita.md) a ✅;
3. spostare questo promemoria in `work-done/` (o eliminarlo).
