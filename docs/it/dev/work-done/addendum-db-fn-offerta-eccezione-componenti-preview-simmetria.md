# Addendum brief DB — fn `*_offerta_eccezione_componenti_*` asimmetriche

> **Stato**: ✅ RISOLTO 2026-05-27. DB applicato e pushato (`dev/db-tid`,
> merge #728):
>
> - `20260526-27-update-fn-offerta-eccezione-componenti-preview-modello-unificato`
>   — Gap 1+2: rimosso filtro `esposto_in_fattura=TRUE`, aggiunti
>   `obbligatorio` + `esposto_in_fattura` al `RETURNS TABLE`.
> - `20260526-28-update-fn-offerta-eccezione-componenti-init-modello-unificato`
>   — Gap 3a: rimosso filtro `esposto_in_fattura=TRUE` dal loop; Gap 3b:
>   chiave overrides `bom_entry_id::text` → `componente_id::text`.
>
> BE riallineato (`dev/backend-tid`): `OfferteRepository.preview_componenti_eccezione`
> SELECT esteso con `obbligatorio, esposto_in_fattura`; commento "debito
> tecnico" rimosso. 52/52 test offerte verdi.
>
> ---
>
> **Branch**: `dev/db-tid`. **Stato originale**: 3 gap di simmetria rilevati
> a runtime sull'OffertaEccezioniDrawer (CREATE su articolo composito).
>
> Sintomi osservati:
>
> 1. `la colonna "obbligatorio" non esiste` su preview (BE 500).
> 2. Dopo INSERT eccezione composita: lista componenti vuota → FE mostra
>    "nessun componente BoM per questa riga"; padre composito resta con
>    `prezzo_unitario = 0` (placeholder BE) e zero figli persistiti.

---

## Gap

Le fn `vendite.fn_offerta_eccezione_componenti_preview` (migration
`20260526-25`) e `vendite.fn_offerta_eccezione_componenti_init`
(migration `20260526-24`) NON sono allineate al modello unificato post
2026-05-13 applicato alle fn gemelle
`vendite.fn_contratto_riga_componenti_{preview,init}`.

### Gap 1 — preview filtra `esposto_in_fattura = TRUE`

Il WHERE del loop nella preview forza `ac.esposto_in_fattura = TRUE`,
mentre la fn contratti l'ha rimosso (modello unificato): tutti i
componenti attivi e validi a data devono comparire in preview, badge
"In fattura" decide il rendering FE.

### Gap 2 — preview RETURNS TABLE incompleto

La fn preview offerta non espone `obbligatorio` + `esposto_in_fattura`
nello shape `RETURNS TABLE`, mentre la fn contratti li ritorna (servono
al `ComponentiDialog` per badge + guard "prezzo zero su obbligatorio").

### Gap 3 — init filtra `esposto_in_fattura = TRUE` + chiave overrides errata

Nella `fn_offerta_eccezione_componenti_init`:

- Il loop ha `WHERE ac.esposto_in_fattura = TRUE` (esattamente come il
  preview). Conseguenza visibile: con un BoM di test dove i componenti
  NON sono flaggati `esposto_in_fattura=true`, l'init **non inserisce
  nessun figlio**. Il BE Python ha gia' creato l'eccezione padre con
  `prezzo_unitario = Decimal(0)` (placeholder per il CHECK
  `chk_offerte_eccezioni_prezzo_per_tipo_eccezione` su OVERRIDE/AGGIUNTA
  e composito), quindi l'eccezione resta in DB orfana e gratis.
- La chiave overrides usa `bom_entry_id::text` (id riga
  `articoli_componenti`); la fn contratti usa `componente_id::text`
  (uuid articolo figlio), che e' anche cio' che il FE
  `ComponentiDialog` spedisce. Risultato attuale: gli override prezzo
  confermati nel Dialog non matchano mai → tutti i prezzi finiscono
  dal resolver (o 0/MANUALE in fallback). L'override manuale e' di
  fatto inattivo.

## Fix richiesto

Allineare entrambe le fn alla simmetria piena con contratti:

### `fn_offerta_eccezione_componenti_preview`

- Rimuovere `AND ac.esposto_in_fattura = TRUE` dal WHERE del loop
  (lasciare solo `AND COALESCE(ac.attivo, TRUE) = TRUE AND ac.validita
  @> p_data_riferimento`).
- Aggiungere `obbligatorio` + `esposto_in_fattura` allo `RETURNS TABLE`
  e popolarli da `ac.obbligatorio` / `ac.esposto_in_fattura` nel loop.

### `fn_offerta_eccezione_componenti_init`

- Rimuovere `AND ac.esposto_in_fattura = TRUE` dal WHERE del loop
  (modello unificato: tutti i componenti attivi/validi entrano,
  `attivo=TRUE` post-INSERT come nei contratti).
- Sostituire la chiave overrides da `bom_entry_id::text` a
  `componente_id::text` (allinearsi al FE `ComponentiDialog` che
  spedisce mappa `{ uuid_articolo_figlio: prezzo }`).

### Operativo Liquibase

- Migration nuova `runOnChange: true` (non modificare le `20260526-24`
  e `20260526-25` gia' pushate — regola `AGENTS.md` Liquibase v2).

## Lato BE (gia' applicato)

`OfferteRepository.preview_componenti_eccezione` (riga ~720) ha SELECT
allineato alla shape attuale della preview (senza `obbligatorio` /
`esposto_in_fattura`) come workaround temporaneo. Dopo il merge della
migration DB:

- Estendere il SELECT con `, obbligatorio, esposto_in_fattura` (commento
  "rev 2026-05-26" nel codice indica esattamente dove).
- Rimuovere il commento "debito tecnico".

`OfferteService.crea_eccezione` setta gia' `prezzo_unitario = Decimal(0)`
come placeholder per il CHECK su composito; resta corretto perche' il
trigger `_z90_ricalcola_padre` lo sovrascrive a SUM(figli x coeff_qta)
post-INSERT figli. Niente cambi BE richiesti dopo il merge DB.

## Note

Sulla diagnostica "padre orfano a prezzo 0": il sintomo si manifesta
solo se la BoM dell'articolo composito non ha alcun componente
`esposto_in_fattura=TRUE`. Dopo il merge del fix init (rimozione filtro),
TUTTI i componenti attivi entrano e il trigger ricalcola il prezzo
padre correttamente, risolvendo anche questo edge case.

---

*Addendum DB — chiusura simmetria preview + init componenti
offerta/contratti. Tempo stimato team DB: 20 minuti totali. Pronto per
applicazione su `dev/db-tid`.*
