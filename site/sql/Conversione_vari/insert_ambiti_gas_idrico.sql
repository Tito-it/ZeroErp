-- Inserimento ambiti GAS e IDRICO con metadati extra_country
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('G01', 'Nord-occidentale', '{"settore": "GAS", "codice_ambito": "01", "ripartizione": "Nord-occidentale", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('G02', 'Nord-orientale', '{"settore": "GAS", "codice_ambito": "02", "ripartizione": "Nord-orientale", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('G03', 'Centro', '{"settore": "GAS", "codice_ambito": "03", "ripartizione": "Centro", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('G04', 'Sud', '{"settore": "GAS", "codice_ambito": "04", "ripartizione": "Sud", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('G05', 'Isole', '{"settore": "GAS", "codice_ambito": "05", "ripartizione": "Isole", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('I01', 'ATO 1 - Piemonte', '{"settore": "IDRICO", "codice_ambito": "PIE01", "ripartizione": "ATO 1 - Piemonte Nord", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('I02', 'ATO 3 - Torinese', '{"settore": "IDRICO", "codice_ambito": "PIE03", "ripartizione": "ATO 3 - Area Metropolitana Torino", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('I03', 'ATO 1 - Lombardia', '{"settore": "IDRICO", "codice_ambito": "LOM01", "ripartizione": "ATO 1 - Lombardia Occidentale", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('I04', 'ATO 3 - Milano', '{"settore": "IDRICO", "codice_ambito": "LOM03", "ripartizione": "ATO 3 - Milano e Hinterland", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('I05', 'EGATO 3 - Campania', '{"settore": "IDRICO", "codice_ambito": "CAM03", "ripartizione": "Ambito Sarnese-Vesuviano (GORI)", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('I06', 'EGATO 4 - Campania', '{"settore": "IDRICO", "codice_ambito": "CAM04", "ripartizione": "Ambito Napoli Nord", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('I07', 'ATO 5 - Toscana Sud', '{"settore": "IDRICO", "codice_ambito": "TOS05", "ripartizione": "GAIA / Toscana Sud", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('I08', 'EGATO 6 - Sicilia Ovest', '{"settore": "IDRICO", "codice_ambito": "SIC06", "ripartizione": "Ambito Occidentale", "stato_utilizzo": "ITA"}');
INSERT INTO config.ambiti (codice, descrizione, extra_country)
VALUES ('I09', 'EGATO 7 - Sicilia Est', '{"settore": "IDRICO", "codice_ambito": "SIC07", "ripartizione": "Ambito Orientale", "stato_utilizzo": "ITA"}');