// Registro centralizzato tabelle config gestibili dal pannello.
// Fonte unica di verita': aggiungere una tabella = aggiungere una riga.
// La whitelist backend (_REL_CONSENTITE) controlla l'accesso, ED E' ANCHE il
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
  { schema: 'config', rel: 'config.ambiti', label: 'Ambiti' },
  { schema: 'config', rel: 'config.aree_funzionali', label: 'Aree Funzionali' },
  { schema: 'config', rel: 'config.aspetti_beni', label: 'Aspetti Beni' },
  { schema: 'config', rel: 'config.assets_ownership', label: 'Assets Ownership' },
  { schema: 'config', rel: 'config.canali_pratiche', label: 'Canali Pratiche' },
  { schema: 'config', rel: 'config.categoria_accisa', label: 'Categoria Accisa' },
  { schema: 'config', rel: 'config.causali_trasporto', label: 'Causali Trasporto' },
  { schema: 'config', rel: 'config.classi_utenze', label: 'Classi Utenze' },
  { schema: 'config', rel: 'config.conti_contabili', label: 'Conti Contabili' },
  { schema: 'config', rel: 'config.forme_giuridiche', label: 'Forme Giuridiche' },
  { schema: 'config', rel: 'config.iva', label: 'IVA' },
  { schema: 'config', rel: 'config.iva_assoggettamenti', label: 'IVA Assoggettamenti' },
  { schema: 'config', rel: 'config.iva_natura', label: 'IVA Natura' },
  { schema: 'config', rel: 'config.lingue', label: 'Lingue' },
  { schema: 'config', rel: 'config.modalita_addebito_trasporto', label: 'Modalita\' Addebito Trasporto' },
  { schema: 'config', rel: 'config.modalita_pagamento', label: 'Modalita\' Pagamento' },
  { schema: 'config', rel: 'config.note_stili', label: 'Note Stili' },
  { schema: 'config', rel: 'config.priorita_pratiche', label: 'Priorita\' Pratiche' },
  { schema: 'config', rel: 'config.qualifiche', label: 'Qualifiche' },
  { schema: 'config', rel: 'config.sistema_codici', label: 'Sistema Codici' },
  { schema: 'config', rel: 'config.sorgenti', label: 'Sorgenti' },
  // NON `config.stati` (le nazioni): senza `codice`, il lookup generico la
  // rifiuta; si gestiscono nella pagina geografica (`StatiDrawer`).
  { schema: 'config', rel: 'config.stati_assets', label: 'Stati Assets' },
  { schema: 'config', rel: 'config.stati_cliente', label: 'Stati Cliente' },
  { schema: 'config', rel: 'config.stati_doc_contratti', label: 'Stati Doc. Contratti' },
  { schema: 'config', rel: 'config.stati_doc_ddt', label: 'Stati Doc. DDT' },
  { schema: 'config', rel: 'config.stati_doc_fiscale', label: 'Stati Doc. Fiscale' },
  { schema: 'config', rel: 'config.stati_doc_ordini', label: 'Stati Doc. Ordini' },
  { schema: 'config', rel: 'config.stati_doc_preventivi', label: 'Stati Doc. Preventivi' },
  { schema: 'config', rel: 'config.stati_doc_reso', label: 'Stati Doc. Reso' },
  { schema: 'config', rel: 'config.stati_flussi_pratiche', label: 'Stati Flussi Pratiche' },
  { schema: 'config', rel: 'config.stati_pdp', label: 'Stati PDP' },
  { schema: 'config', rel: 'config.stati_pratiche', label: 'Stati Pratiche' },
  { schema: 'config', rel: 'config.stati_sdi', label: 'Stati SDI' },
  { schema: 'config', rel: 'config.termini_pagamento', label: 'Termini Pagamento' },
  { schema: 'config', rel: 'config.tipi_allegato', label: 'Tipi Allegato' },
  { schema: 'config', rel: 'config.tipi_attivita', label: 'Tipi Attivita\'' },
  { schema: 'config', rel: 'config.tipi_contatti', label: 'Tipi Contatti' },
  { schema: 'config', rel: 'config.tipi_doc_fiscale', label: 'Tipi Doc. Fiscale' },
  { schema: 'config', rel: 'config.tipi_documenti', label: 'Tipi Documenti' },
  { schema: 'config', rel: 'config.tipi_evento_assets', label: 'Tipi Evento Assets' },
  { schema: 'config', rel: 'config.tipi_indirizzi', label: 'Tipi Indirizzi' },
  { schema: 'config', rel: 'config.tipi_nota', label: 'Tipi Nota' },
  { schema: 'config', rel: 'config.tipi_reso', label: 'Tipi Reso' },
  { schema: 'config', rel: 'config.tipi_ruoli', label: 'Tipi Ruoli' },
  { schema: 'config', rel: 'config.tipi_soggetto_dettaglio', label: 'Tipi Soggetto Dettaglio' },
  { schema: 'config', rel: 'config.tipi_ubicazione', label: 'Tipi Ubicazione' },
  { schema: 'config', rel: 'config.tipi_utenze', label: 'Tipi Utenze' },
  // NON `config.titoli_cortesia`: senza `codice` il lookup generico la rifiuta
  // (500). Nessun consumatore: domanda al DB, non una riga qui.
  { schema: 'config', rel: 'config.unita_organizzative', label: 'Unita\' Organizzative' },
  { schema: 'config', rel: 'config.utilities', label: 'Utilities' },
  { schema: 'config', rel: 'config.valute', label: 'Valute' },
  // --- catalogo ---
  { schema: 'catalogo', rel: 'catalogo.unita_misura', label: 'Unita\' di Misura' },
  // --- magazzino --- (solo il vocabolario: magazzini, ubicazioni e lotti
  // sono anagrafiche del dominio, con casa propria)
  { schema: 'magazzino', rel: 'magazzino.causali', label: 'Causali' },
  // --- pagamenti ---
  { schema: 'pagamenti', rel: 'pagamenti.centri_riscossione', label: 'Centri Riscossione' },
  { schema: 'pagamenti', rel: 'pagamenti.enti_incasso', label: 'Enti Incasso' },
  { schema: 'pagamenti', rel: 'pagamenti.vendite_contabili_righe_stati', label: 'Stati Righe Contabili' },
  { schema: 'pagamenti', rel: 'pagamenti.vendite_contabili_stati', label: 'Stati Contabili' },
  // --- pratiche ---
  { schema: 'pratiche', rel: 'pratiche.handler_flussi', label: 'Handler Flussi' },
  { schema: 'pratiche', rel: 'pratiche.template_flussi', label: 'Template Flussi' },
  { schema: 'pratiche', rel: 'pratiche.tipi_prestazione', label: 'Tipi Prestazione' },
  // --- vendite ---
  { schema: 'vendite', rel: 'vendite.area_geografica_fatturazione', label: 'Aree Geografiche Fatturazione' },
  { schema: 'vendite', rel: 'vendite.articoli_gruppi', label: 'Gruppi Articoli' },
  { schema: 'vendite', rel: 'vendite.articoli_spesa', label: 'Articoli Spesa' },
  { schema: 'vendite', rel: 'vendite.articoli_tipologie', label: 'Tipologie Articoli' },
  { schema: 'vendite', rel: 'vendite.stati_commessa', label: 'Stati Commessa' },
  { schema: 'vendite', rel: 'vendite.tipi_fondi_fattura', label: 'Tipi Fondi Fattura' },
]

// Schema unici per raggruppamento
export const CONFIG_SCHEMAS = [...new Set(CONFIG_TABLES.map(t => t.schema))].sort()

// Lookup per rel
export function getTableConfig(rel) {
  return CONFIG_TABLES.find(t => t.rel === rel) || null
}

// Tabelle raggruppate per schema
export function getTablesBySchema() {
  const grouped = {}
  for (const t of CONFIG_TABLES) {
    if (!grouped[t.schema]) grouped[t.schema] = []
    grouped[t.schema].push(t)
  }
  return grouped
}
