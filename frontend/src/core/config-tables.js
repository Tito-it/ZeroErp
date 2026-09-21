// Registro centralizzato tabelle config gestibili dal pannello.
// Fonte unica di verita': aggiungere una tabella = aggiungere una riga QUI e
// l'etichetta `config_panel.tabelle.<schema>.<tabella>` in it.json e en.json
// (la chiave e' la rel stessa: `chiaveEtichettaTabella`, core/utils/campoConfig.js;
// a video il ripiego e' la rel, presidio nel test del registro, punto 5).
// ⛔ Niente `label` qui: fino al 2026-09-21 erano 65 stringhe italiane
// hardcoded, l'unico testo del pannello fuori da `$t()`.
// La whitelist backend (REL_CONSENTITE) controlla l'accesso, ED E' ANCHE il
// perimetro di cio' che il pannello sa listare: la lista passa dal lookup
// generico, quindi una tabella senza `codice`/`descrizione` qui NON entra.
// ⛔ Qui stanno i VOCABOLARI (codice, descrizione, attivo, qualche flag), resi
// dal drawer generico metadata-driven. Un'anagrafica con chiavi esterne «vere»
// (un magazzino con emittente e indirizzo, un'ubicazione con magazzino e
// padre, un lotto con articolo) ha endpoint e drawer propri nel suo dominio:
// il 2026-09-21 `magazzino.magazzini/ubicazioni/lotti` sono uscite da qui per
// quella ragione (piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config).
// Il presidio che ogni riga sia servibile per intero (lista, metadata,
// etichette) e' `apps/core/tests/db/test_config_panel_registro_db.py`.

export const CONFIG_TABLES = [
  // --- config ---
  { schema: 'config', rel: 'config.ambiti' },
  { schema: 'config', rel: 'config.aree_funzionali' },
  { schema: 'config', rel: 'config.aspetti_beni' },
  { schema: 'config', rel: 'config.assets_ownership' },
  { schema: 'config', rel: 'config.canali_pratiche' },
  { schema: 'config', rel: 'config.categoria_accisa' },
  { schema: 'config', rel: 'config.causali_trasporto' },
  { schema: 'config', rel: 'config.classi_utenze' },
  { schema: 'config', rel: 'config.conti_contabili' },
  { schema: 'config', rel: 'config.forme_giuridiche' },
  { schema: 'config', rel: 'config.iva' },
  { schema: 'config', rel: 'config.iva_assoggettamenti' },
  { schema: 'config', rel: 'config.iva_natura' },
  { schema: 'config', rel: 'config.lingue' },
  { schema: 'config', rel: 'config.modalita_addebito_trasporto' },
  { schema: 'config', rel: 'config.modalita_pagamento' },
  { schema: 'config', rel: 'config.note_stili' },
  { schema: 'config', rel: 'config.priorita_pratiche' },
  { schema: 'config', rel: 'config.qualifiche' },
  { schema: 'config', rel: 'config.sistema_codici' },
  { schema: 'config', rel: 'config.sorgenti' },
  // NON `config.stati` (le nazioni): senza `codice`, il lookup generico la
  // rifiuta; si gestiscono nella pagina geografica (`StatiDrawer`).
  { schema: 'config', rel: 'config.stati_assets' },
  { schema: 'config', rel: 'config.stati_cliente' },
  { schema: 'config', rel: 'config.stati_doc_contratti' },
  { schema: 'config', rel: 'config.stati_doc_ddt' },
  { schema: 'config', rel: 'config.stati_doc_fiscale' },
  { schema: 'config', rel: 'config.stati_doc_ordini' },
  { schema: 'config', rel: 'config.stati_doc_preventivi' },
  { schema: 'config', rel: 'config.stati_doc_reso' },
  { schema: 'config', rel: 'config.stati_flussi_pratiche' },
  { schema: 'config', rel: 'config.stati_pdp' },
  { schema: 'config', rel: 'config.stati_pratiche' },
  { schema: 'config', rel: 'config.stati_sdi' },
  { schema: 'config', rel: 'config.termini_pagamento' },
  { schema: 'config', rel: 'config.tipi_allegato' },
  { schema: 'config', rel: 'config.tipi_attivita' },
  { schema: 'config', rel: 'config.tipi_contatti' },
  { schema: 'config', rel: 'config.tipi_doc_fiscale' },
  { schema: 'config', rel: 'config.tipi_documenti' },
  { schema: 'config', rel: 'config.tipi_evento_assets' },
  { schema: 'config', rel: 'config.tipi_indirizzi' },
  { schema: 'config', rel: 'config.tipi_nota' },
  { schema: 'config', rel: 'config.tipi_reso' },
  { schema: 'config', rel: 'config.tipi_ruoli' },
  { schema: 'config', rel: 'config.tipi_soggetto_dettaglio' },
  { schema: 'config', rel: 'config.tipi_ubicazione' },
  { schema: 'config', rel: 'config.tipi_utenze' },
  // NON `config.titoli_cortesia`: senza `codice` il lookup generico la rifiuta
  // (500). Nessun consumatore: domanda al DB, non una riga qui.
  { schema: 'config', rel: 'config.unita_organizzative' },
  { schema: 'config', rel: 'config.utilities' },
  { schema: 'config', rel: 'config.valute' },
  // --- catalogo ---
  { schema: 'catalogo', rel: 'catalogo.unita_misura' },
  // --- magazzino --- (solo il vocabolario: magazzini, ubicazioni e lotti
  // sono anagrafiche del dominio, con casa propria)
  { schema: 'magazzino', rel: 'magazzino.causali' },
  // --- pagamenti ---
  { schema: 'pagamenti', rel: 'pagamenti.centri_riscossione' },
  { schema: 'pagamenti', rel: 'pagamenti.enti_incasso' },
  { schema: 'pagamenti', rel: 'pagamenti.vendite_contabili_righe_stati' },
  { schema: 'pagamenti', rel: 'pagamenti.vendite_contabili_stati' },
  // --- pratiche ---
  { schema: 'pratiche', rel: 'pratiche.handler_flussi' },
  { schema: 'pratiche', rel: 'pratiche.template_flussi' },
  { schema: 'pratiche', rel: 'pratiche.tipi_prestazione' },
  // --- vendite ---
  { schema: 'vendite', rel: 'vendite.area_geografica_fatturazione' },
  { schema: 'vendite', rel: 'vendite.articoli_gruppi' },
  { schema: 'vendite', rel: 'vendite.articoli_spesa' },
  { schema: 'vendite', rel: 'vendite.articoli_tipologie' },
  { schema: 'vendite', rel: 'vendite.stati_commessa' },
  { schema: 'vendite', rel: 'vendite.tipi_fondi_fattura' },
]

// Schema unici per raggruppamento
export const CONFIG_SCHEMAS = [...new Set(CONFIG_TABLES.map(t => t.schema))].sort()

// Tabelle raggruppate per schema
export function getTablesBySchema() {
  const grouped = {}
  for (const t of CONFIG_TABLES) {
    if (!grouped[t.schema]) grouped[t.schema] = []
    grouped[t.schema].push(t)
  }
  return grouped
}
