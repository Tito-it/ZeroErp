# Brief DB — `vw_articoli_dettaglio` espone la natura di vendita

> **Tipo documento**: brief operativo **per il team DB** (`dev/db-tid`).
>
> **Data**: 2026-06-10 · **Stato**: 🟢 **CONSEGNATO E APPLICATO (2026-06-10)** —
> `20260610-05-update-vw-articoli-dettaglio-natura-vendita`. Nomi colonne reali:
> `natura_vendita_id`, `natura_vendita_codice_interno`,
> `natura_vendita_descrizione`, `natura_vendita_destinazione_tipo`. A valle (§4)
> BE+FE cablati lo stesso giorno.
>
> **Origine**: chiusura del gap "natura non amministrabile da applicazione"
> (decisione Tid 2026-06-10, **opzione A: natura mutabile**). Il BE ha già
> esposto `natura_vendita_id` su CREATE/UPDATE articolo e `config.nature_vendita`
> nella whitelist lookup codici. **Prerequisito bloccante** per il Select
> "Natura di vendita" nel `ArticoloDrawer` (EDIT): senza la colonna nel detail,
> il form non può inizializzare il valore corrente e un salvataggio rischierebbe
> il reset silenzioso al DEFAULT MERCE.

## 1. Il problema (verificato)

`catalogo.articoli.natura_vendita_id` (NOT NULL, DEFAULT 1=MERCE, FK
`config.nature_vendita`) decide l'instradamento post-accettazione del modello
split per natura (ordine/commessa/contratto), ma **non è proiettata** da
`catalogo.vw_articoli_dettaglio` — la vista che alimenta list/detail articoli
lato BE (`CatalogoRepository.list_articoli` / `get_articolo`). Risultato: API e
FE non vedono la natura di un articolo.

## 2. Richiesta

Aggiungere alla vista `catalogo.vw_articoli_dettaglio` (pattern identico alle
altre decodifiche già presenti: uom, tipologia, gruppo, spesa, iva):

```sql
LEFT JOIN config.nature_vendita nv ON nv.id = a.natura_vendita_id
```

con proiezione:

| Colonna | Sorgente | Nota |
| --- | --- | --- |
| `natura_vendita_id` | `a.natura_vendita_id` | per inizializzare il Select in EDIT |
| `natura_vendita_codice` | `nv.codice` | display lista |
| `natura_vendita_descrizione` | `nv.descrizione` | display lista/drawer |
| `natura_destinazione_tipo` | `nv.destinazione_tipo` | hint UX (ORDINE/COMMESSA/CONTRATTO) |

`LEFT JOIN` per coerenza con le altre decodifiche della vista (anche se la FK è
NOT NULL, la vista non deve perdere righe per una decodifica).

## 3. Fuori scope

- Nessun cambio a tabelle/trigger/seed: la colonna e il modello natura esistono
  già (`20260609-*`).
- Lock di immutabilità: **non richiesto** — decisione opzione A, la natura resta
  mutabile (lo snapshot per riga documento è già garantito dai trigger di
  derivazione su `preventivi_righe`).

## 4. A valle (BE/FE, non DB)

Alla consegna: BE aggiunge le 4 colonne a `ARTICOLI_DETAIL_COLUMNS`
(`catalogo_repository.py`) e il FE cabla il Select natura su `ArticoloDrawer`
(CREATE+EDIT, default MERCE) + colonna display in lista.

*Brief DB — vw_articoli_dettaglio natura — ZeroERP (2026-06-10).*
