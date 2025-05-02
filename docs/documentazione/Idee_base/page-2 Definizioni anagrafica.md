⚙️ Documentazione 

Anagrafica Generale

| id_anagrafica | ragione_sociale | tipo_soggetto | nome | cognome | codice_fiscale | partita_iva | data_nascita | id_comune_nascita | genere | codice_fiscale_forzato | note_cf |

Anagrafica Società Storico

| id | id_anagrafica | forma_giuridica | capitale_sociale | REA | PEC | codice_SDI | data_costituzione | data_inizio_validita | data_fine_validita | note |

Tabelle Ruoli Specifici

Clienti
Fornitori
Agenti
Distributori (codice distributore, nr pronto intervento)
Gestore Software (unico obbligatorio)
Contatti aziendali (nome, cognome, titolo, ruolo aziendale, telefono, email)
Contatti Anagrafica

| id_contatto | id_anagrafica | tipo_contatto | valore_contatto | note |

Indirizzi

| id_indirizzo | tipo_indirizzo | toponomastica | nome_via | numero_civico | piano | interno | id_comune | id_provincia | id_stato | zip_code | indirizzo_completo_libero | indirizzo_libero | note |

Comuni e Province

Comuni: nome, cap, codice_istat, codice_catastale
Province: nome, sigla, regione
Stati

| id_stato | nome_stato | codice_iso2 | codice_iso3 |

Forniture

| id_fornitura | codice_fornitura | id_indirizzo | tipo_fornitura | id_pod_pdr | data_attivazione | data_cessazione | note |

Servizi

| id_servizio | codice | descrizione | default_servizio | note |

Clienti (Servizi-Clienti-Forniture)

| id_cliente | id_anagrafica | id_fornitura | id_servizio | codice_cliente | data_inizio_servizio | data_fine_servizio | stato | note |

Contratti

| id_contratto | id_cliente | codice_contratto | tipologia_contratto | id_offerta | id_listino | data_inizio_contratto | data_fine_contratto | condizioni_particolari | note |

Cabine REMI

| id_cabina | id_distributore | codice | descrizione | indirizzo | data_attivazione | data_disattivazione | note |

POD/PDR

| id_pod_pdr | id_distributore | codice_pod_pdr | tipo | id_indirizzo | stato | data_attivazione | data_cessazione | note |

Distributori

| id_distributore | id_anagrafica | codice_distributore | nr_pronto_intervento | note |

Tabelle di Collegamento
Anagrafica indirizzi (storico indirizzi soggetti)
Cabine REMI - Comuni/Vie
Popolamento Tabelle (Esempi)
Anagrafica: Rossi Mario (fisico), Energia S.p.A. (giuridico)
Forniture: FORN001, indirizzo specifico
Servizi: DEFAULT, GAS
Clienti e Contratti: esempi concreti con codice contratto
Cabine REMI, POD/PDR: esempi censiti
📚 Appendice
Glossario termini ERP e Utility
Riferimenti normativi (es. ARERA)

