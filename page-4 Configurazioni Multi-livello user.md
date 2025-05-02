📄 Sistema di Configurazione Multi-livello - Progetto Zero ERP
Obiettivo
Definire una struttura completa e robusta per la gestione delle configurazioni applicative, dei permessi, dei moduli, degli utenti e dei menu dinamici per l'ERP Zero.

✅ Livello 1 - Configurazione Sistema (Environment Variables)
Variabile	Descrizione
DJANGO_SECRET_KEY	Chiave segreta applicazione
DB_NAME	Nome database
DB_USER	Utente database
DB_PASSWORD	Password database
DB_HOST	Host database
DB_PORT	Porta database
    • Accessibile solo da amministratore di sistema.
    • Non modificabile dagli utenti.

✅ Livello 2 - Parametrizzazione Applicativa
Tabella: parametri_globali
id	parametro	valore	tipo	extra	descrizione
1	usa_contratti_avanzati	true	boolean	NULL	Abilita modulo contratti avanzati
2	modulo_fatturazione_rapida	false	boolean	NULL	Abilita funzione fatturazione rapida
3	calcolo_iva_personalizzato	true	boolean	NULL	Abilita gestione IVA personalizzata
4	parametrizzazione_varia	NULL	jsonb	{"data_inizio": "2024-01-01", "data_fine": "2024-12-31", "note": "Parametri temporanei"}	Parametri opzionali complessi

✅ Livello 3 - Gestione Moduli Applicativi
Tabella: moduli
id	codice_modulo	descrizione	attivo	configurazione
1	FAT	Modulo Fatturazione	true	{"versione": "base", "abilitazioni": ["pdf", "email"]}
2	CONT	Modulo Contratti	true	{"gestione_avanzata": true}
3	MAG	Modulo Magazzino	false	NULL
4	ANAG	Gestione Anagrafiche	true	NULL
5	CFG	Configurazione e Parametri	true	NULL
6	GEST	Gestione Forniture	true	NULL
7	REMI	Gestione Cabine REMI	true	NULL
8	PDR	Gestione POD/PDR	true	NULL
9	USR	Gestione Utenti e Permessi	true	NULL

✅ Livello 4 - Profilazione Utenti e Gruppi
Django fornisce i seguenti modelli integrati:
    • User
    • Group
    • Permission
Questi modelli saranno utilizzati per:
    • Autenticazione.
    • Organizzazione in gruppi.
    • Gestione dei permessi base.
Estensione personalizzata:
Tabella: permessi_gruppi
id	gruppo (FK su Group)	modulo (FK su moduli)	funzione	tipo_accesso
1	Operatori	FAT	Inserimento	lettura-scrittura
2	Amministratori	ANAG	Gestione completa	lettura-scrittura
3	Operatori	CONT	Visualizzazione	sola-lettura
4	Commerciali	GEST	Consultazione	sola-lettura
5	Tecnici	REMI	Gestione Cabine	lettura-scrittura

✅ Livello 5 - Permessi Utente Specifici (Override)
Tabella: permessi_utenti
id	utente (FK su User)	funzione (FK su funzioni_modulo)	tipo_accesso
1	user_001	crea_fattura	sola-lettura
2	user_002	stampa_fattura	lettura-scrittura
    • Gli utenti possono ricevere permessi personalizzati che sovrascrivono quelli assegnati tramite il gruppo.
    • Priorità: permessi_utenti > permessi_gruppi

✅ Livello 6 - Gestione Funzioni e Azioni
Tabella: funzioni_modulo
id	modulo (FK su moduli)	codice_funzione	descrizione
1	FAT	crea_fattura	Creazione nuova fattura
2	FAT	stampa_fattura	Stampa fattura
3	CONT	visualizza_contratto	Visualizzazione Contratto
4	CONT	crea_contratto	Inserimento Contratto
5	ANAG	modifica_cliente	Modifica dati cliente

✅ Livello 7 - Configurazione Cliente
Tabella: parametri_clienti
id	id_cliente	parametro	valore	data_inizio	data_fine	extra
1	10	intestazione_documenti	"Società Alfa"	2024-01-01	NULL	NULL
2	10	listino_prezzi	"Listino_2024"	2024-01-01	NULL	NULL
3	11	configurazione_avanzata	NULL	2024-01-01	2024-12-31	{"lingua_default": "it", "template": "personalizzato"}

✅ Livello 8 - Gestione Menu Dinamici
Tabella: menu
id	modulo (FK)	nome_voce	url	ordine	funzione_richiamata
1	FAT	Fatturazione	/fatturazione/	1	crea_fattura
2	CONT	Contratti	/contratti/	2	visualizza_contratto
3	ANAG	Anagrafiche	/anagrafiche/	3	modifica_cliente
4	GEST	Forniture	/forniture/	4	NULL
5	REMI	Cabine REMI	/remi/	5	NULL
    • Se l'utente ha un permesso esplicito (permessi_utenti) o di gruppo (permessi_gruppi), la voce del menu è visibile.

✅ Livello 9 - Override gerarchico dei parametri
Comportamento
    1. Permessi utente specifici.
    2. Permessi gruppo.
    3. Parametro specifico cliente.
    4. Parametro globale.
    5. Parametro di default.

🔄 Flusso completo
    1. Creazione utente (User)
    2. Assegnazione a uno o più gruppi (Group)
    3. Definizione permessi gruppo (permessi_gruppi)
    4. Definizione opzionale permessi utente (permessi_utenti)
    5. Menu dinamico costruito in base ai permessi effettivi (utente > gruppo)
    6. Controllo runtime sui singoli componenti applicativi (viste, form, azioni)

✅ Benefici
    • Controllo granulare fino al singolo utente e funzione.
    • Menu e funzionalità totalmente dinamiche.
    • Priorità chiara tra permessi utente e di gruppo.
    • Facilmente espandibile a livello di azioni o campi specifici.
    • Coerenza completa tra frontend, backend e sicurezza applicativa.
Struttura pronta per estensioni come:
    • Multi-tenant.
    • Gestione multi-lingua.
    • Permessi per campo o processo.











User ----< permessi_utenti >---- Funzione >---- Modulo >---- Menu
   |                                 ^
   +----< Group >----< permessi_gruppi >---- Funzione

Funzione ----< permessi_funzioni >---- Group

parametri_clienti ----< User
parametri_globali ----< Modulo

✨ Relazioni
    • Ogni User può:
        ◦ Appartenere a più Group
        ◦ Avere permessi diretti su specifiche Funzioni
        ◦ Essere legato ai parametri_clienti
    • Ogni Group ha:
        ◦ Permessi su Funzioni tramite permessi_gruppi
    • Ogni Funzione appartiene ad un Modulo:
        ◦ Un modulo ha le sue Funzioni e Menu
    • I Menu:
        ◦ Sono collegati ai moduli e filtrati dinamicamente in base ai permessi
    • I parametri:
        ◦ Possono essere globali o legati al singolo cliente (parametri_clienti)

