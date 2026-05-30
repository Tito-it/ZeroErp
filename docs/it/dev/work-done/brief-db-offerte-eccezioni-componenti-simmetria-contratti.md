# Brief DB — Offerta commerciale: simmetria piena con contratti

> **Branch**: `dev/db-tid`. **Stato**: due gap di modello rilevati post-smoke FE.
> Le offerte commerciali sono dichiarate mirror di contratti
> (`OfferteRepository`: «Specchio di ContrattiRepository»). Mancano due
> pezzi per chiudere la simmetria.

---

## A. Componenti BoM su eccezioni offerta

Oggi `vendite.offerte_commerciali_eccezioni` è atomica per articolo —
nessun supporto BoM. Su articolo composito, il prezzo padre diverge
dal modello contratti al push offerta→contratto.

Serve mirror **strutturale** di `contratti_righe_componenti`:

- Tabella `vendite.offerte_commerciali_eccezioni_componenti` —
  stesse colonne / CHECK / FK / indici di `contratti_righe_componenti`,
  con `eccezione_offerta_id` al posto di `riga_contratto_id`.
- Trigger — riusare i generici `script.trgfn_componenti_*`
  parametrizzati su `('vendite','offerte_commerciali_eccezioni',
  'eccezione_offerta_id', 'offerte_commerciali', 'offerta_id', 'validita_dal')`,
  più clone `trgfn_offerte_eccezioni_componenti_guard_pending` (logica
  identica a `trgfn_contratti_righe_componenti_guard_pending`).
- `vendite.fn_offerta_eccezione_componenti_init(p_eccezione_id,
  p_emittente_sr_id, p_data_riferimento, p_componenti_overrides
  jsonb DEFAULT NULL)` — mirror di
  `fn_contratto_riga_componenti_init`.
- `vendite.fn_offerta_eccezione_componenti_preview(...)` — mirror di
  `fn_contratto_riga_componenti_preview` (stessa firma e shape jsonb).
- Test pgTAP simmetrici a quelli su `contratti_righe_componenti`.

Trasporto stato approvazione: tenere le colonne
`stato_approvazione_prezzo` / `pratica_approvazione_prezzo_id` anche
qui (NULL ammesso, no trigger workflow L3 in questa fase): servono al
push offerta→contratto per non perdere lo stato.

---

## B. Documenti — sorgente OFFERTA_COMMERCIALE

`config.sorgenti` ha già la riga `OFFERTA_COMMERCIALE` (id=14). Manca:

- Riga in `config.tipi_documento_output` con codice
  `OFFERTA_COMMERCIALE` (mirror delle righe `PREVENTIVO`/`CONTRATTO`
  in `80_data/sql/documenti/tipi_documento_output.csv`).
- Template seed di default per `OFFERTA_COMMERCIALE` (mirror del seed
  preventivo/contratto in `20260429-58-upsert-documenti-seed-base`).

Niente DDL sul motore documentale: è già generico
(`template_documenti`, `template_documenti_versioni`,
`documenti_generati`, `documenti_generati_file`,
`documenti_generati_eventi` accettano qualsiasi `sorgente_tipo_id`).

---

## Sequenza

1. (A) DDL + trigger + 2 fn + pgTAP.
2. (B) Seed `tipi_documento_output` + template default.
3. Push `dev/db-tid` → PR `Tito-dev`.

Lato BE/FE: brief separato (componenti eccezione su
`OffertaEccezioniDrawer` + builder/views documenti offerta + FE
`OffertaDocumentiDrawer`). Parte solo dopo merge DB.
