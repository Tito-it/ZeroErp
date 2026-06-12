# Brief DB — Azioni di processo area pratiche mai seedate

> **Tipo documento**: brief operativo **per il team DB** (`dev/db-tid`).
>
> **Data**: 2026-06-12 · **Stato**: ✅ **CHIUSO lato DB (2026-06-12)** — vedi
> §4 per le decisioni e il deliverable. Resta il re-run smoke lato BE (§3).

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
con permessi reali, non da super admin. **Attenzione**: lo smoke deve
autenticarsi con la faccia **OPERATORE** — `pochi` ha anche
`SHOP_CUSTOMER_STANDARD`, e il gate GUC di `fn_check_azione_processo` nega
tutto sulle facce non-OPERATORE (fail-closed by design).

## 4. Chiusura (decisioni ratificate 2026-06-12)

Controllo critico eseguito contro BE e DB vivi; tre punti sciolti:

1. **Verifica gemella (presa in carico)**: verificato — `ApiPrendiInCarico`
   **non dichiara** azioni di processo, ed e' **corretto cosi'**: la presa in
   carico non fa avanzare il processo (auto-assegnazione di lavoro) ed e' gia'
   governata da permesso d'area + **competenza** (`competenze_flussi`, guard a
   DB con errori dedicati). Aggiungere un'azione creerebbe due verita' sulla
   stessa domanda (stesso vizio scartato in D2). **Nessuna nona azione.**
2. **`prendi_in_carico` rimosso dalla proposta di abilitazioni**: era
   un'azione inesistente (conseguenza del punto 1). L'elenco resta di **8**.
3. **Azioni vs abilitazioni — confine prodotto/installazione**:
   - le **azioni** sono dato di **prodotto** (le dichiara il codice) →
     seedate nel repo: 8 righe in `azioni_processo.csv`, id 18–25, area 12,
     `pericolosa=true` su `cambia_stato_pratica` e `genera_pratica_manuale`
     (nessun changeset nuovo: il CSV e' gia' coperto da `20260228-18`
     runOnChange);
   - le **abilitazioni** (`profili_accesso_azioni`) sono dato di
     **installazione** (i reparti variano per azienda; non a caso nel repo
     non esiste seed nemmeno per vendite, e i profili operativi come
     `REPARTO_MKT` vivono solo sul DB di sviluppo) → **niente seed nel
     repo**; per sbloccare `pochi` basta l'INSERT manuale una tantum sul DB
     dev (sotto). Eventuali profili "di fabbrica" con abilitazioni
     predefinite = decisione di prodotto separata, fuori scope.

### Script manuale per il DB di sviluppo (una tantum, non versionato)

```sql
-- Abilita il reparto al lavoro quotidiano sulla coda (avvia/completa step)
INSERT INTO config.profili_accesso_azioni (profilo_accesso_id, azione_id, abilitata)
SELECT pa.id, ap.id, true
  FROM config.profili_accesso pa, config.azioni_processo ap
 WHERE pa.codice = 'REPARTO_MKT'
   AND ap.permission_codename = 'cambia_stato_flusso'
ON CONFLICT DO NOTHING;

-- (facoltativo) profilo di coordinamento: tutte le 8 azioni pratiche
-- INSERT analogo con ap.area_id = 12 e pa.codice = '<PROFILO_COORD>';

-- Igiene: allinea la sequence di azioni_processo agli id seedati
-- (il changeset 20260228-18 non fa setval; rischio preesistente)
SELECT setval(pg_get_serial_sequence('config.azioni_processo', 'id'),
              GREATEST((SELECT max(id) FROM config.azioni_processo), 1), true);
```

*Brief DB — azioni processo pratiche — ZeroERP (2026-06-12). Chiuso lato DB;
resta §3 (re-run smoke con operatore) lato BE.*
