Zero ERP - Modulo Gestione Pratiche


✅ Obiettivo
Gestire flussi di lavoro e attività (pratiche) interne ed esterne, in modo configurabile, tracciabile e integrabile con sistemi esterni.
📌 Caratteristiche chiave
    • Pratiche configurabili dal gestore.
    • Supporto per pratiche di sistema (autogenerate) e pratiche business.
    • Attività  attivabili da eventi interni o esterni.
    • Ricezione richieste esterne tramite API che creano pratiche.
    • Invio callback o eventi a sistemi esterni.
    • Gestione storica e audit completa.
    • Collegamento diretto delle attività alle entità anagrafiche, forniture e servizi.
    • Tracciamento utente e timestamp sia per inserimento che aggiornamento.
    • Supporto workflow sequenziali e condizionali tramite ordine ed esito.
    • Notifiche automatiche parametrizzabili per gruppi e utenti.
    • Regole per dipendenze obbligatorie e unicità attività.
    • Gestione notifiche e collegamenti espliciti tra attività.
    • Conteggio e analisi statistica dei tempi di svolgimento delle attività.
    • Pianificazione e assegnazione attività a utenti/gruppi con gestione delle competenze.

📌 Vantaggi
    • Flessibilità e adattabilità a diversi settori.
    • Sistema modulare e configurabile.
    • Integrazione nativa con sistemi esterni.
    • Utilizzabile come "journal" di sistema.
    • Facilmente estendibile per processi futuri.
    • Tracciabilità completa tramite audit.
    • Gestione avanzata workflow, condizioni e regole.
    • Automatizzazione notifiche e alert utenti.
    • Analisi statistica tempi e performance.
    • Pianificazione strutturata delle attività con assegnazione e monitoraggio.
    • Note e documenti con versionamento, classificazione e privacy.




📌 Entità principali
Tabella: pratiche
id	tipo_pratica	descrizione	stato	data_creazione	data_chiusura	id_riferimento_esterno	user_ins	data_ins	user_upd	data_upd	extra
PK	FK	Testo libero	Aperta/In corso/Chiusa	Timestamp	Timestamp	Opzionale	FK Utente	Timestamp	FK Utente	Timestamp	JSONB
Tabella: tipi_pratica
id	codice	descrizione	configurabile	extra
PK	Unico	Descrizione	boolean	JSONB

Tabella: attivita_pratiche
id	pratica	tipo_attivita	descrizione	stato	esito	anagrafica_generale	servizio	fornitura	competenza_area	user_ins	data_ins	user_upd	data_upd	data_creazione	data_conclusione	extra
PK	FK	FK	Testo	Aperta/In corso/Chiusa	Successo/Fallita	FK	FK	FK	Testo	FK Utente	Timestamp	FK Utente	Timestamp	Timestamp	Timestamp	JSONB
Tabella: pianificazione_attivita
id	attivita_pratica	data_fine_massima	data_prevista	data_presa_in_carico	user_assegnato	gruppo_assegnato	user_ins	data_ins	user_upd	data_upd	extra
PK	FK	Timestamp	Timestamp	Timestamp	FK Utente (opzionale)	FK Gruppo (opzionale)	FK Utente	Timestamp	FK Utente	Timestamp	JSONB

Tabella: tipi_attivita
id	codice	descrizione	trigger_esterno	trigger_interno	ordine_sequenza	esito_richiesto	notifica_utente	extra
PK	Unico	Testo	boolean	boolean	integer	boolean	boolean	JSONB


Tabella: attivita_notifiche
id	tipo_attivita_origine	tipo_attivita_destinazione	gruppo_destinatario	utente_destinatario	condizione_esito	extra
PK	FK	FK	FK Gruppo	FK Utente (opzionale)	Successo/Fallita	JSONB

Tabella: regole_attivita
id	tipo_attivita	tipo_attivita_precedente	obbligatoria	unica_nella_pratica	extra
PK	FK	FK	boolean	boolean	JSONB

Tabella: regole_conteggio_tempi
id	tipo_pratica	tipo_attivita_iniziale	tipo_attivita_finale	extra
PK	FK	FK	FK	JSONB

Tabella: attivita_sospensione_tempi
id	tipo_attivita	sospende_conteggio	riattiva_conteggio	extra
PK	FK	boolean	boolean	JSONB

Tabella: note_attivita
id	attivita_pratica_id	nota	classificazione	pubblica	versione	user_ins	data_ins	extra
1	1	"Controllati documenti, tutto ok"	"Informativa"	true	1	1	"2024-04-15"	{}

Tabella: documenti_attivita
id	attivita_pratica_id	nome_file	percorso_file	documento_blob	classificazione	versione	pubblica	user_ins	data_ins	extra
1	1	"contratto_firmato.pdf"	"/files/contratti/"	NULL	"Contratto"	1	true	1	"2024-04-15"	{}






Nota
Questa struttura permette di estendere Zero ERP verso un Business Process Engine senza perdere la semplicità nella gestione dei processi standard.
