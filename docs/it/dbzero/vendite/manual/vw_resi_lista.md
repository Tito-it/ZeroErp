## 📘 Documentazione Concettuale – Vista `vendite.vw_resi_lista`

> 👀 **Vedi anche**
>
> [vendite.resi](/dbzero/vendite/tabelle/resi) ·
> [vendite.vw_ddt_lista](/dbzero/vendite/views/vw_ddt_lista) (mirror) ·
> [script.fn_available_actions_reso](/dbzero/script/funzioni/fn_available_actions_reso)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Vista canonica **lista/dettaglio** dei resi per BE/FE, mirror di `vw_ddt_lista`. Espone la testata
reso con i join denormalizzati: stato (`stato_codice_interno`/`stato_descrizione`), destinatario,
billing/emittente/utility/valuta, e la **sorgente** (DDT di provenienza via `ddt_origine_*`).

### Regole chiave

- **`security_invoker=on`** — la RLS del chiamante (`rls_resi_ef_whitelist`) filtra sulla base. La
  reloption va **ri-specificata** in ogni `CREATE OR REPLACE VIEW` (PostgreSQL la azzera).
- Espone `emittente_fiscale_id` (+ `_codice`) per il **filtro applicativo BE** e
  `emittente_fiscale_descrizione = COALESCE(ragione sociale soggetto emittente, ef.descrizione)`
  (convenzione etichetta 2026-07-13).
- **Alias fedeli** alla sorgente: `codice_interno AS stato_codice_interno` (logica),
  `descrizione AS stato_descrizione` (display) — linee-guida-sql §6c.
- Il reso aggancia il **DDT** (non l'ordine): l'ordine si raggiunge dal DDT. Niente colonne
  trasporto/logistica/importi (asimmetria voluta col DDT in questa slice).
