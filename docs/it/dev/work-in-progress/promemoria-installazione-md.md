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

## ⭐ Che cosa è cambiato dal 2026-06-20 (verificato il 2026-09-11)

Il promemoria è rimasto fermo tre mesi, ma **il setup sotto si è mosso** — e una
parte del passo 1 («auditare lo stato attuale») è ormai fatta dai fatti.

| Novità | Da quando | Perché cambia questo promemoria |
| --- | --- | --- |
| `backend/deploy/sveglie.json` | 2026-09-06 | **sede unica del dichiarato di deploy**: chi sveglia ogni processo, con quale cadenza e con quale tolleranza. Nel giugno non esisteva: le cadenze erano cablate nell'installer |
| `backend/deploy/systemd/` — **15 template** versionati | lug→set 2026 | gli unit non si generano più con heredoc dentro lo script: sono file reviewabili in PR, con i placeholder per-host |
| `backend/bin/install-timers.sh` riscritto | 2026-07-21 → 2026-09-07 | legge `sveglie.json`, è **idempotente**, e ha un test in CI (`scripts/tests/test-install-timers.sh`) che prova anche il ramo che ACCENDE |
| `scripts/sql/provision_db_roles.sql` + `provision_db_role_batch_fatturazione.sql` | 2026-02 / 2026-06, aggiornati fino al 2026-09-09 | ⭐ **un passo di installazione che il promemoria non nominava**: i ruoli `zeroerp_batch_*` hanno `BYPASSRLS`, vogliono **superuser** e **non possono** essere creati da Liquibase |
| play-book §15/§16/§17 | ago→set 2026 | la parte systemd è ora descritta lì, di taglio tecnico |

⛔ **La decisione bloccante NON si è sbloccata da sé**: `docker-compose` non
esiste ancora (verificato il 2026-09-11), il modello resta a due server e il
`Dockerfile` resta della CI. ⇒ Il §«Decisione bloccante» qui sopra vale **parola
per parola**, e lo stato rilevato il 2026-05-29 è tuttora quello.

### ✅ Una metà è stata scorporata e SCRITTA (2026-09-11)

Sotto «installazione» c'erano **due** documenti diversi, e solo uno era bloccato:

| | Documento | Stato |
| --- | --- | --- |
| **A** | *«come tiri su la macchina»* — servizi, ordine di avvio, migrazioni | ⛔ **fermo**, è questo promemoria |
| **B** | *«cosa configuri perché l'ERP funzioni»* — emittente, operatori, SMTP, timer, destinatario, parametri, modelli di stampa | ✅ **scritto**: [configurazione-iniziale.md](../../configurazione-iniziale.md) |

⭐ **B non dipendeva dalla decisione**: che cosa si configura dentro il programma
non cambia fra Docker e venv. ⚠️ Ed è nato da un caso vero: il 2026-09-11, su
questa installazione, **tre** dei sette passi di B mancavano — l'SMTP era ancora
il placeholder del seed, i timer non erano mai stati installati, il destinatario
delle segnalazioni non c'era. Nessuno dei tre dava errore.

## Prossimo passo quando si riprende

1. **Auditare/chiarire lo stato del setup attuale** (venv, makefile, Dockerfile CI).
   ⭐ **Per la parte systemd non serve più**: `sveglie.json` + i 15 template +
   l'installer con test in CI sono già il dichiarato, e vanno *citati*, non
   ricostruiti. ⛔ Resta da nominare il **provisioning dei ruoli DB**
   (`scripts/sql/provision_db_role*.sql`), che vuole superuser e non passa da
   Liquibase: oggi non è in nessun documento di installazione.
   ⚠️ E il perimetro di A si è ristretto: la configurazione applicativa è uscita
   in [configurazione-iniziale.md](../../configurazione-iniziale.md), quindi qui
   resta la sola macchina.
2. **Decidere** Docker vs venv (vs entrambi).
3. **Riscrivere `installazione.md`** → "Come farlo girare su una macchina qualsiasi":
   servizi + ordine di avvio, env vars, login, applica/rollback migrazione, modello
   branch/PR. Separare il generico riproducibile dall'infra personale
   (Proxmox/Tailscale resta come riferimento marcato).
4. Verifica build `python scripts/build_docs_zensical.py` exit 0.

## Alla chiusura

Quando fatto: spostare questo promemoria in `work-done/` (o eliminarlo).
