# Promemoria — Installazione con Docker

> **Tipo**: promemoria (decisione aperta). · **Stato**: 🟡 **DA DECIDERE**.
> **Data**: 2026-06-20, ridotto il 2026-11-25.
> **Origine**: piano
> [ristrutturazione-documentale.md](../work-done/2026/ristrutturazione-documentale.md),
> punto b.1.

---

## Che cosa resta

La parte venv di [installazione.md](../../installazione.md) è scritta: ordine dei
passi, variabili d'ambiente, database, backend dietro Nginx, processi automatici,
frontend. Resta solo **una decisione di Tid**:

- **Serve anche un'installazione con Docker?** Se sì, deve stare accanto al venv
  o sostituirlo?

## Lo stato di oggi (verificato il 2026-11-25)

- Il setup è **venv + systemd**. Gli unit sono versionati in
  `backend/deploy/systemd/` e dichiarati da `backend/deploy/sveglie.json`;
  li installa `backend/bin/install-timers.sh`, che è provato in CI.
- Il `Dockerfile` serve **solo alla CI**. Porta anche l'elenco delle librerie di
  sistema di WeasyPrint, che vale per tutte le macchine.
- **Nessun `docker-compose`** nel repo.
- Il modello è a **due server**, DB e backend.

## Se si decide per Docker

1. Un `docker-compose` di sviluppo con PostgreSQL 18 (con le estensioni e
   pgAgent), Redis, backend, Nginx e, in sviluppo, Vite.
2. I dieci passi del database **non si riscrivono**. Il compose li lancia
   nell'ordine di [installazione.md](../../installazione.md), «L'ordine dei passi»,
   che è lo stesso della CI. Una seconda sede di quell'ordine sarebbe una copia
   destinata a divergere.
3. Bisogna decidere che cosa prende il posto dei timer systemd dentro i
   container, senza perdere il controllo `e_dovuto` di ogni sveglia.
4. In `installazione.md` si aggiunge un capitolo Docker accanto a quello venv,
   e si toglie l'avviso «decisione aperta» in testa alla pagina.
5. Verifica della build: `python scripts/build_docs_zensical.py` deve uscire con 0.

## Se si decide di no

Si tolgono da [installazione.md](../../installazione.md) l'avviso in testa e il
link a questo promemoria, poi il promemoria si sposta in `work-done/`.
