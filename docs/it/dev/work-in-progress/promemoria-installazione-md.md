# Promemoria — Riscrivere `installazione.md` (dopo decisione Docker vs venv)

> **Tipo**: promemoria operativo (TODO doc). · **Stato**: 🟡 **DA FARE**.
> **Data**: 2026-06-20.
> **Origine**: chiusura del piano
> [ristrutturazione-documentale.md](../work-done/ristrutturazione-documentale.md)
> (punto b.1). Quel piano è completo e in `work-done/`; questo è l'**unico
> deliverable rimasto**, scorporato qui perché bloccato da una decisione utente.

---

## Perché è fermo

`docs/it/installazione.md` è ancora uno **stub da 42 righe**, con markdown rotto e
il riferimento obsoleto a `mkdocs serve` (→ ora si usa `zensical`). Nella diagnosi
del piano (§1.2) è il **"buco più grave"** e il **pezzo a leva più alta**: manca la
pagina "tiralo su su una macchina qualsiasi".

È sospeso (dal 2026-05-29) perché serve **prima** una decisione utente sul target.

## Decisione bloccante

- **Docker vs venv puro** (o entrambi) per il setup riproducibile "macchina singola".
  L'utente era orientato a **Docker** ma non ha deciso, e lo stato del setup attuale
  non era chiaro.
- **Stato setup rilevato (2026-05-29)**: venv + `makefile` (target `db-migrate`/
  `db-setup` per Liquibase), `Dockerfile` per la CI (con librerie WeasyPrint),
  **nessun `docker-compose` dev**, modello a due server (DB + backend).

## Prossimo passo quando si riprende

1. **Auditare/chiarire lo stato del setup attuale** (venv, makefile, Dockerfile CI).
2. **Decidere** Docker vs venv (vs entrambi).
3. **Riscrivere `installazione.md`** → "Come farlo girare su una macchina qualsiasi":
   servizi + ordine di avvio, env vars, login, applica/rollback migrazione, modello
   branch/PR. Separare il generico riproducibile dall'infra personale
   (Proxmox/Tailscale resta come riferimento marcato).
4. Verifica build `python scripts/build_docs_zensical.py` exit 0.

## Alla chiusura

Quando fatto: spostare questo promemoria in `work-done/` (o eliminarlo).
