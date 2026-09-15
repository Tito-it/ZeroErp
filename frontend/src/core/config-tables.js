// Registro centralizzato tabelle config gestibili dal pannello.
// Fonte unica di verita': aggiungere una tabella = aggiungere una riga.
// La whitelist backend (_REL_CONSENTITE) controlla l'accesso.
// Il campo `drawer` determina quale drawer aprire (null = generico).

export const CONFIG_TABLES = [
  // --- config ---
  { schema: 'config', rel: 'config.ambiti', label: 'Ambiti', drawer: null },
  { schema: 'config', rel: 'config.aree_funzionali', label: 'Aree Funzionali', drawer: null },
  { schema: 'config', rel: 'config.aspetti_beni', label: 'Aspetti Beni', drawer: null },
  { schema: 'config', rel: 'config.assets_ownership', label: 'Assets Ownership', drawer: null },
  { schema: 'config', rel: 'config.canali_pratiche', label: 'Canali Pratiche', drawer: null },
  { schema: 'config', rel: 'config.categoria_accisa', label: 'Categoria Accisa', drawer: null },
  { schema: 'config', rel: 'config.causali_trasporto', label: 'Causali Trasporto', drawer: null },
  { schema: 'config', rel: 'config.classi_utenze', label: 'Classi Utenze', drawer: null },
  { schema: 'config', rel: 'config.conti_contabili', label: 'Conti Contabili', drawer: null },
  { schema: 'config', rel: 'config.forme_giuridiche', label: 'Forme Giuridiche', drawer: null },
  { schema: 'config', rel: 'config.iva', label: 'IVA', drawer: null },
  { schema: 'config', rel: 'config.iva_assoggettamenti', label: 'IVA Assoggettamenti', drawer: null },
  { schema: 'config', rel: 'config.iva_natura', label: 'IVA Natura', drawer: null },
  { schema: 'config', rel: 'config.lingue', label: 'Lingue', drawer: null },
  { schema: 'config', rel: 'config.modalita_addebito_trasporto', label: 'Modalita\' Addebito Trasporto', drawer: null },
  { schema: 'config', rel: 'config.modalita_pagamento', label: 'Modalita\' Pagamento', drawer: null },
  { schema: 'config', rel: 'config.note_stili', label: 'Note Stili', drawer: null },
  { schema: 'config', rel: 'config.priorita_pratiche', label: 'Priorita\' Pratiche', drawer: null },
  { schema: 'config', rel: 'config.qualifiche', label: 'Qualifiche', drawer: null },
  { schema: 'config', rel: 'config.sistema_codici', label: 'Sistema Codici', drawer: null },
  { schema: 'config', rel: 'config.sorgenti', label: 'Sorgenti', drawer: null },
  { schema: 'config', rel: 'config.stati', label: 'Stati', drawer: null },
  { schema: 'config', rel: 'config.stati_assets', label: 'Stati Assets', drawer: null },
  { schema: 'config', rel: 'config.stati_cliente', label: 'Stati Cliente', drawer: null },
  { schema: 'config', rel: 'config.stati_doc_contratti', label: 'Stati Doc. Contratti', drawer: null },
  { schema: 'config', rel: 'config.stati_doc_ddt', label: 'Stati Doc. DDT', drawer: null },
  { schema: 'config', rel: 'config.stati_doc_fiscale', label: 'Stati Doc. Fiscale', drawer: null },
  { schema: 'config', rel: 'config.stati_doc_ordini', label: 'Stati Doc. Ordini', drawer: null },
  { schema: 'config', rel: 'config.stati_doc_preventivi', label: 'Stati Doc. Preventivi', drawer: null },
  { schema: 'config', rel: 'config.stati_doc_reso', label: 'Stati Doc. Reso', drawer: null },
  { schema: 'config', rel: 'config.stati_flussi_pratiche', label: 'Stati Flussi Pratiche', drawer: null },
  { schema: 'config', rel: 'config.stati_pdp', label: 'Stati PDP', drawer: null },
  { schema: 'config', rel: 'config.stati_pratiche', label: 'Stati Pratiche', drawer: null },
  { schema: 'config', rel: 'config.stati_sdi', label: 'Stati SDI', drawer: null },
  { schema: 'config', rel: 'config.termini_pagamento', label: 'Termini Pagamento', drawer: null },
  { schema: 'config', rel: 'config.tipi_allegato', label: 'Tipi Allegato', drawer: null },
  { schema: 'config', rel: 'config.tipi_attivita', label: 'Tipi Attivita\'', drawer: null },
  { schema: 'config', rel: 'config.tipi_contatti', label: 'Tipi Contatti', drawer: null },
  { schema: 'config', rel: 'config.tipi_doc_fiscale', label: 'Tipi Doc. Fiscale', drawer: null },
  { schema: 'config', rel: 'config.tipi_documenti', label: 'Tipi Documenti', drawer: null },
  { schema: 'config', rel: 'config.tipi_evento_assets', label: 'Tipi Evento Assets', drawer: null },
  { schema: 'config', rel: 'config.tipi_indirizzi', label: 'Tipi Indirizzi', drawer: null },
  { schema: 'config', rel: 'config.tipi_nota', label: 'Tipi Nota', drawer: null },
  { schema: 'config', rel: 'config.tipi_reso', label: 'Tipi Reso', drawer: null },
  { schema: 'config', rel: 'config.tipi_ruoli', label: 'Tipi Ruoli', drawer: null },
  { schema: 'config', rel: 'config.tipi_soggetto_dettaglio', label: 'Tipi Soggetto Dettaglio', drawer: null },
  { schema: 'config', rel: 'config.tipi_ubicazione', label: 'Tipi Ubicazione', drawer: null },
  { schema: 'config', rel: 'config.tipi_utenze', label: 'Tipi Utenze', drawer: null },
  { schema: 'config', rel: 'config.titoli_cortesia', label: 'Titoli Cortesia', drawer: null },
  { schema: 'config', rel: 'config.unita_organizzative', label: 'Unita\' Organizzative', drawer: null },
  { schema: 'config', rel: 'config.utilities', label: 'Utilities', drawer: null },
  { schema: 'config', rel: 'config.valute', label: 'Valute', drawer: null },
  // --- catalogo ---
  { schema: 'catalogo', rel: 'catalogo.unita_misura', label: 'Unita\' di Misura', drawer: null },
  // --- magazzino ---
  { schema: 'magazzino', rel: 'magazzino.causali', label: 'Causali', drawer: null },
  { schema: 'magazzino', rel: 'magazzino.magazzini', label: 'Magazzini', drawer: null },
  { schema: 'magazzino', rel: 'magazzino.ubicazioni', label: 'Ubicazioni', drawer: null },
  // --- pagamenti ---
  { schema: 'pagamenti', rel: 'pagamenti.centri_riscossione', label: 'Centri Riscossione', drawer: null },
  { schema: 'pagamenti', rel: 'pagamenti.enti_incasso', label: 'Enti Incasso', drawer: null },
  { schema: 'pagamenti', rel: 'pagamenti.vendite_contabili_righe_stati', label: 'Stati Righe Contabili', drawer: null },
  { schema: 'pagamenti', rel: 'pagamenti.vendite_contabili_stati', label: 'Stati Contabili', drawer: null },
  // --- pratiche ---
  { schema: 'pratiche', rel: 'pratiche.handler_flussi', label: 'Handler Flussi', drawer: null },
  { schema: 'pratiche', rel: 'pratiche.template_flussi', label: 'Template Flussi', drawer: null },
  { schema: 'pratiche', rel: 'pratiche.tipi_prestazione', label: 'Tipi Prestazione', drawer: null },
  // --- vendite ---
  { schema: 'vendite', rel: 'vendite.area_geografica_fatturazione', label: 'Aree Geografiche Fatturazione', drawer: null },
  { schema: 'vendite', rel: 'vendite.articoli_gruppi', label: 'Gruppi Articoli', drawer: null },
  { schema: 'vendite', rel: 'vendite.articoli_spesa', label: 'Articoli Spesa', drawer: null },
  { schema: 'vendite', rel: 'vendite.articoli_tipologie', label: 'Tipologie Articoli', drawer: null },
  { schema: 'vendite', rel: 'vendite.stati_commessa', label: 'Stati Commessa', drawer: null },
  { schema: 'vendite', rel: 'vendite.tipi_fondi_fattura', label: 'Tipi Fondi Fattura', drawer: null },
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
