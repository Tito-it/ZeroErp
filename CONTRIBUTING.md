# Contribuire a ZeroERP

> **Ultimo aggiornamento**: 2 novembre 2026

Grazie per l'interesse. ZeroERP accetta segnalazioni, proposte e pull request.

## ⛔ Prima di tutto: il CLA

ZeroERP ha una **doppia licenza** (`AGPL-3.0-or-later` e una licenza
commerciale, vedi [LICENSE.md](LICENSE.md)). Per questo ogni pull request può
essere accettata **solo dopo la firma del [CLA](CLA.md)**.

- Il CLA **non** ti toglie il copyright: concedi una licenza che permette di
  distribuire il tuo contributo anche nelle versioni commerciali.
- Alla prima pull request un bot ti chiede di firmare; la firma vale per tutti
  i contributi successivi.
- Una pull request senza CLA firmato resta aperta ma **non viene unita**.

## Segnalazioni

- **Bug e proposte**: apri una issue su GitHub, con i passi per riprodurre il
  problema e la versione (commit o tag) che usi.
- **Vulnerabilità di sicurezza**: **non** aprire una issue pubblica, segui
  [SECURITY.md](SECURITY.md).

## Pull request

1. Parti dal branch `main` aggiornato e lavora su un branch tuo.
2. Le regole del progetto sono in [.codex/AGENTS.md](.codex/AGENTS.md); per la
   parte database vedi anche [docs/it/linee-guida-sql.md](docs/it/linee-guida-sql.md).
3. Ogni file nuovo porta l'intestazione standard (modelli in
   [templates/](templates/)), con `SPDX-License-Identifier: AGPL-3.0-or-later`.
4. Il codice di terzi va dichiarato nella pull request, con la sua licenza: deve
   essere compatibile con **entrambe** le licenze di ZeroERP (per esempio MIT,
   BSD, Apache-2.0). Codice GPL o AGPL di terzi **non** può entrare.
5. Prima di aprire la pull request devono passare i controlli locali
   (`pre-commit`) e la CI.

## In English

Contributions are welcome. ZeroERP is dual-licensed, so **every pull request
requires a signed [CLA](CLA.md)** before it can be merged — you keep your
copyright. Report security issues privately as described in
[SECURITY.md](SECURITY.md). Third-party code must be under a permissive
license (MIT, BSD, Apache-2.0); GPL/AGPL third-party code cannot be accepted.
