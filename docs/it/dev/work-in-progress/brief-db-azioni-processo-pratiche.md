# Brief DB — Azioni di processo area pratiche mai seedate

> **Tipo documento**: brief operativo **per il team DB** (`dev/db-tid`).
>
> **Data**: 2026-06-12 · **Stato**: 🔴 **APERTO** — trovato eseguendo lo smoke
> pratica con un utente **operatore** (`pochi`) invece che super admin.

## 1. Il problema (verificato a DB)

Le view dell'area pratiche dichiarano **8 azioni di processo**
(`post_permission`):

`cambia_stato_pratica`, `assegna_pratica`, `cambia_stato_flusso`,
`genera_pratica_manuale`, `sospendi_pratica`, `riattiva_pratica`,
`sospendi_flusso`, `riattiva_flusso`.

Ma `config.azioni_processo` ha **zero righe per l'area pratiche**: le azioni
non sono mai state seedate, e di conseguenza nessun profilo le abilita in
`profili_accesso_azioni`. `script.fn_check_azione_processo` nega per azione
inesistente → **qualunque operatore non super-admin riceve 403 su tutte le
operazioni di stato delle pratiche** (cambio stato, avvio/completamento
flussi, sospensioni, assegnazione, generazione manuale).

Riscontro: `pochi` (profili `REPARTO_MKT` + `SHOP_CUSTOMER_STANDARD`) crea
pratiche e flussi (check CRUD d'area, senza azione) ma prende 403 su
`POST /pratiche/<id>/stato/` e `POST .../flussi/<id>/stato/`. Il giro è
sempre passato solo perché gli smoke giravano con `tid` (super admin, bypass).

**Impatto**: la dashboard pratiche è di fatto **inutilizzabile per gli
operatori reali** — possono vedere e creare, non far avanzare nulla.

## 2. Richiesta (logica; il come è scelta vostra)

1. **Seed `config.azioni_processo`**: le 8 azioni sopra, area funzionale
   pratiche. Valutare il flag `pericolosa` per `cambia_stato_pratica`
   (include la chiusura) e `genera_pratica_manuale`.
2. **Abilitazioni `profili_accesso_azioni`**: decidere quali profili
   operativi le ricevono. Proposta di buon senso: i profili reparto che
   lavorano la coda pratiche abilitano almeno `cambia_stato_flusso` (è
   l'operatività quotidiana: avvia/completa step) e `prendi_in_carico`;
   `cambia_stato_pratica` / `sospendi_*` / `assegna_pratica` ai profili di
   coordinamento. La granularità fine è decisione di prodotto.
3. **Verifica gemella**: controllare se anche `prendi_in_carico_flusso`
   (endpoint coda lavoro) dichiara un'azione non seedata.

## 3. A valle (BE, non DB)

Nessun cambio codice: il sistema permessi funziona — mancano solo i dati.
Alla consegna: re-run `smoke-test-pratica-preventivi-conferma.sh` con
`SMOKE_USER=pochi` (operatore con profilo abilitato) per validare il giro
con permessi reali, non da super admin.

*Brief DB — azioni processo pratiche — ZeroERP (2026-06-12).*
