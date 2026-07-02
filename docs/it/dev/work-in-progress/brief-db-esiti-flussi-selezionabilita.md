# Brief DB — Discriminatore di selezionabilità sugli esiti flussi pratiche

> **Tipo**: brief DB (piccolo: 1 colonna + seed) · **Data**: 2026-07-02
> **Owner**: Tid · **Per**: team DB (`dev/db-tid`) · **Stato**: 🟢 aperto
>
> **Origine**: review critica 2026-07-02 sul cantiere V1/B3b (esiti data-driven,
> [brief-fe-percorso-narrativo-operatore.md](brief-fe-percorso-narrativo-operatore.md) §9.1-A).

## 1. Problema

Con gli esiti del `Select` di FlussoDrawer ora **data-driven** dal vocabolario
globale `config.esiti_flussi_pratiche` (decisione §9.1-A), nel dropdown compaiono
anche gli **esiti di ramo** `MERCE_PRESENTE` / `SOLO_SERVIZI` — che sono valori
**calcolati dal dominio** (bivio SMISTAMENTO) e **mai input utente**, come
documenta lo stesso `pratiche_service.py`. Il vocabolario non ha alcuna colonna
che distingua i due gruppi (verificato: solo `meta` jsonb, oggi `{}` per tutte
le righe), quindi né il lookup né il FE possono filtrare in modo data-driven.

**Mitigazione interim già attiva (BE, 2026-07-02)**: guard applicativo
`require_esito_selezionabile_operatore` sul percorso API del cambio stato
(mirror `ESITI_FLUSSO_RAMO` in `pratiche_service.py`, stessa convenzione di
`ESITI_FLUSSO_AMMESSI`) — l'operatore che seleziona un esito di ramo riceve
errore parlante. Ma il mirror va mantenuto a mano e il dropdown continua a
mostrare opzioni non valide.

## 2. Richiesta al team DB

1. **Colonna discriminatore** su `config.esiti_flussi_pratiche`:
   `selezionabile_operatore boolean NOT NULL DEFAULT true`
   (naming a discrezione del team; semantica: *l'esito può essere scelto a mano
   nel completamento di un flusso*).
2. **Seed**: `false` per `MERCE_PRESENTE` e `SOLO_SERVIZI`; `true` (default) per
   i 4 esiti generici. I futuri esiti di ramo nasceranno con `false`.
3. Nessuna funzione/trigger richiesta: il filtro lo applicano lookup BE e FE.

## 3. Follow-up applicativo (a colonna consegnata — NON team DB)

- Lookup specializzato `config.esiti_flussi_pratiche` (BE) che espone/filtra il
  flag → il `Select` FE mostra solo gli esiti selezionabili.
- Il guard `require_esito_selezionabile_operatore` passa a leggere il flag dal
  vocabolario (o si elimina il mirror hardcoded `ESITI_FLUSSO_RAMO`).

*A consegna: spostare in `work-done/` e chiudere il punto nel brief V1 (§9.1).*
