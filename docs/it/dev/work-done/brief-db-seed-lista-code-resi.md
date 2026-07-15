# Brief DB — Liste configurabili per le due code resi (da accreditare / da ri-consegnare)

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-14 · **Owner**: Tid
> **Stato**: ☐ DA REALIZZARE
> **Contesto**: le tab "da accreditare" e "da ri-consegnare" della vista Resi
> ([ResiView](../../../../frontend/src/vendite/resi/views/ResiView.vue)) oggi sono
> `DataTable` raw a colonne fisse: non hanno personalizzazione colonne né export, a
> differenza delle altre liste standard. Per allinearle allo standard
> `<ListaConfigurabile>` (come la tab "lista" resi, config `vendite.resi`) servono due
> nuove **liste configurabili** lato config `ui`.
> **Companion**: seed lista `vendite.resi` già realizzato in
> [brief-db-seed-lista-ui-resi.md](brief-db-seed-lista-ui-resi.md) (PR #978) — stesso pattern.

---

## 1. Cosa serve (NON come)

> Questo brief descrive **il fabbisogno funzionale**. L'implementazione (nomi tabelle,
> id, formato seed, loader) è competenza e scelta del team DB.

Servono **due liste configurabili** nel catalogo config `ui`, una per ciascuna coda,
entrambe con **sorgente una vista che esiste già** (nessun oggetto DB nuovo da creare):

| Lista (fabbisogno) | Vista sorgente esistente | Grana |
|---|---|---|
| Coda resi "da accreditare" | `vendite.vw_resi_da_accreditare` | riga reso |
| Coda resi "da ri-consegnare" | `vendite.vw_resi_da_riconsegnare` | riga reso |

Per ognuna serve che diventino disponibili a runtime:

- **personalizzazione colonne** (mostra/nascondi, ordine, larghezza) come le altre liste;
- **export** CSV/XLSX che rispetti colonne visibili/ordine/permessi dell'utente
  (l'export BE è generico sulla config lista: una volta esistente la config, funziona).

Le due viste sono già `security_invoker=on` ed espongono `emittente_fiscale_id` per lo
scope emittente applicativo: **nessuna modifica alle viste** è richiesta da questo brief.

## 2. Colonne che ciascuna lista deve poter esporre

Le colonne richieste corrispondono a quelle oggi mostrate a video (più eventuali opzionali,
opt-in via personalizzazione). I nomi tra parentesi sono le colonne **già presenti nella
vista sorgente** (verificabili nella doc auto-gen delle viste): il team DB le mappi come
ritiene, rispettando i ruoli indicati.

### 2a. Coda "da accreditare" (sorgente `vw_resi_da_accreditare`)

| Ruolo | Colonna sorgente | Note |
|---|---|---|
| **Identificatore** (sempre visibile) | `reso_numero` | numero del reso |
| Informazione | `data` | data reso |
| Informazione | `destinatario_denominazione` | ragione sociale destinatario |
| Informazione | `descrizione` | articolo/descrizione riga |
| Informazione | `ddt_numero` | DDT di origine |
| Informazione | `qta_operativa` | quantità resa (unità operativa) |
| Informazione | `motivo` | motivo del reso |
| Opzionali (opt-in) | `ba_codice`, `quantita` | codice account, quantità base |
| **Azione** (non esportabile) | — | colonna azioni di riga (apri reso) |

### 2b. Coda "da ri-consegnare" (sorgente `vw_resi_da_riconsegnare`)

| Ruolo | Colonna sorgente | Note |
|---|---|---|
| **Identificatore** (sempre visibile) | `reso_numero` | numero del reso |
| Informazione | `data` | data reso |
| Informazione | `destinatario_denominazione` | ragione sociale destinatario |
| Informazione | `descrizione` | articolo/descrizione riga |
| Informazione | `ddt_numero` | DDT di origine |
| Informazione | `qta_resa` | quantità resa |
| Informazione | `qta_riconsegnata` | quantità già ri-consegnata |
| Informazione | `qta_residua` | copertura residua |
| Informazione | `stato_riconsegna` | stato derivato (DA_RICONSEGNARE / PARZIALE / COMPLETATA); reso a video come Tag lato FE |
| **Azione** (non esportabile) | — | colonna azioni di riga (apri reso) |

> Nota: `vw_resi_da_riconsegnare` **non** espone `ba_codice` (asimmetria reale con la coda
> accrediti, non una dimenticanza).

## 3. Vincoli / requisiti funzionali

1. **Riferimento applicativo per `codice`, non per id**: il FE/BE useranno il `codice` lista
   (tipo `vendite.resi_da_accreditare` / `vendite.resi_da_riconsegnare`, o come il team DB
   preferisce nominarli — basta comunicarli). Gli id numerici sono liberi al momento dell'apply.
2. **Ordinabilità**: le colonne di ciascuna lista devono essere ordinabili server-side
   (lo standard `ListaConfigurabile` ordina lato BE; il supporto `order_by/order_dir` sugli
   endpoint coda è oggetto del brief BE companion).
3. **Ricercabilità**: le colonne testuali "destinatario / DDT / articolo" andrebbero marcate
   ricercabili full-text (search ILIKE), coerentemente con la lista resi principale — **se e
   solo se** il BE espone la search sulle code (vedi brief BE). Se il BE non la espone in
   questa iterazione, marcarle non-ricercabili.
4. **Chiavi i18n** delle etichette colonna: le aggiunge il **FE** nel proprio blocco
   `vendite.resi.*` — nessuna azione DB.
5. Nessun preset dedicato: visibilità di default gestita dal runtime (parità lista resi).

## 4. Cosa comunicare indietro al BE/FE

- I due **`codice` lista** effettivi assegnati.
- Conferma delle colonne esportabili/ordinabili/ricercabili come sopra (o eventuali scostamenti).

## 5. Avanzamento

| # | Step | Stato |
|---|---|---|
| 1 | Lista config coda "da accreditare" (sorgente `vw_resi_da_accreditare`) | ☐ |
| 2 | Lista config coda "da ri-consegnare" (sorgente `vw_resi_da_riconsegnare`) | ☐ |
| 3 | Apply + comunicazione `codice` lista al BE/FE | ☐ |
