
prodotti	Catalogo generale (modello del contatore, tipo, caratteristiche generali)
contatori	Asset installato, con seriale, posizione, stato, cliente associato, vita utile, dati specifici
letture	Storico letture (periodiche o su richiesta)
manutenzioni	Eventuali eventi legati al contatore

💡 Esempio concettuale:
CREATE TABLE prodotti (
    id SERIAL PRIMARY KEY,
    codice VARCHAR(50) UNIQUE,
    nome VARCHAR(100),
    tipo VARCHAR(20) DEFAULT 'contatore', -- potrebbe essere 'contatore', 'valvola', ecc.
    meta JSONB DEFAULT '{}'::JSONB
);

CREATE TABLE contatori (
    id SERIAL PRIMARY KEY,
    matricola VARCHAR(50) UNIQUE NOT NULL, -- il seriale fisico
    prodotto_id INTEGER REFERENCES prodotti(id),
    cliente_id INTEGER REFERENCES clienti(id),
    installato_il DATE,
    posizione VARCHAR(255), -- eventualmente anche coordinata GPS o georeferenziazione
    stato VARCHAR(20) DEFAULT 'attivo',
    caratteristiche JSONB DEFAULT '{}'::JSONB
);

CREATE TABLE letture (
    id SERIAL PRIMARY KEY,
    contatore_id INTEGER REFERENCES contatori(id),
    data_lettura TIMESTAMP NOT NULL,
    valore NUMERIC(10,3) NOT NULL, -- valore del contatore
    tipo VARCHAR(20) DEFAULT 'lettura_ufficiale' -- ufficiale, stimata, su richiesta
);

CREATE TABLE manutenzioni (
    id SERIAL PRIMARY KEY,
    contatore_id INTEGER REFERENCES contatori(id),
    data_evento DATE,
    tipo_evento VARCHAR(100),
    note TEXT
);

✨ Nota:
    • Il prodotto(articolo) è generico, e può rappresentare qualsiasi oggetto di magazzino (es. "Contatore G4", "Valvola a farfalla", "Modulo LTE").
    • Il contatore è l'istanza fisica legata al cliente.
    • meta e caratteristiche con JSONB permettono di estendere senza compromettere la struttura (es. firmware, portata massima, classe metrologica, pressione nominale).

Questa tecnica è: ✔️ 100% compatibile con ERP reali
✔️ Estensibile senza migrazioni frequenti
✔️ Combina relazioni + attributi dinamici


-- Modello base per settore Gas/Energia - ERP Ready

-- ✅ Prodotti (Catalogo Generale)
CREATE TABLE prodotti (
    id SERIAL PRIMARY KEY,
    codice VARCHAR(50) UNIQUE NOT NULL,
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(30) DEFAULT 'contatore', -- contatore, valvola, concentratore
    fornitore VARCHAR(100),
    meta JSONB DEFAULT '{}'::JSONB -- info tecniche variabili
);

-- ✅ Asset fisici installati (Contatori, Valvole ecc.)
CREATE TABLE asset (
    id SERIAL PRIMARY KEY,
    matricola VARCHAR(50) UNIQUE NOT NULL, -- seriale fisico
    prodotto_id INTEGER NOT NULL REFERENCES prodotti(id),
    cliente_id INTEGER REFERENCES clienti(id),
    installato_il DATE,
    posizione VARCHAR(255), -- indirizzo o coordinate
    stato VARCHAR(20) DEFAULT 'attivo',
    caratteristiche JSONB DEFAULT '{}'::JSONB -- firmware, classe metrologica, ecc.
);

-- ✅ Letture (consumi)
CREATE TABLE letture (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES asset(id),
    data_lettura TIMESTAMP NOT NULL,
    valore NUMERIC(10,3) NOT NULL, -- valore misurato
    tipo VARCHAR(30) DEFAULT 'lettura_ufficiale' -- ufficiale, stimata, su richiesta
);

-- ✅ Eventi e Manutenzioni
CREATE TABLE manutenzioni (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES asset(id),
    data_evento DATE NOT NULL,
    tipo_evento VARCHAR(50) NOT NULL, -- installazione, sostituzione, rimozione
    note TEXT
);

-- ✅ Storico cambi cliente (trasloco contatori)
CREATE TABLE asset_storico_clienti (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES asset(id),
    cliente_id INTEGER NOT NULL REFERENCES clienti(id),
    da_data DATE NOT NULL,
    a_data DATE
);

-- ✅ Opzionale: Letture Importate (batch da concentratori)
CREATE TABLE letture_batch (
    id SERIAL PRIMARY KEY,
    file_nome VARCHAR(255),
    importato_il TIMESTAMP DEFAULT now(),
    meta JSONB DEFAULT '{}'::JSONB
);



    • Prodotti (contatori, valvole, concentratori)
    • Asset fisici con caratteristiche variabili
    • Letture dei consumi
    • Eventi e manutenzioni
    • Storico clienti legato agli asset
    • Letture batch (da concentratori o dispositivi remoti)

Considerazioni:
    • Così il contatore è trattato come prodotto e come asset fisico.
    • Può essere gestito in magazzino (nella tabella prodotti) e successivamente installato come asset (nella tabella asset).
    • Caratteristiche variabili (es. firmware, classe metrologica) sono archiviate in JSONB.
    • È flessibile e può gestire anche futuri device IoT.
Se vuoi nel prossimo step possiamo: ✔️ Aggiungere gestione contratti
✔️ Modello completo clienti/forniture
✔️ Integrazione pianificazione letture e bollettazione


processo separazione letture rilevate da letture da fatturare acconti e effettive


    1. Letture grezze
        ◦ Tabella letture_raw o letture_contatore
        ◦ Con timestamp completo (data e ora)
        ◦ Originate da qualsiasi fonte: telegestione, operatore, cliente
        ◦ Possono esserci più letture nello stesso giorno
        ◦ Contengono anche informazioni accessorie (es. metodo, operatore, fonte)
    2. Letture consolidate (fatturazione)
        ◦ Tabella letture_validated o letture_fatturazione
        ◦ Campo data_lettura solo date (senza ora)
        ◦ Unique su (id_contatore, data_lettura)
        ◦ Si popolano solo dopo validazione manuale o automatica
        ◦ Possono essere completate da metadati essenziali per la bolletta (es. tipo lettura, validità, provenienza)

CREATE TABLE letture_contatore (
    id SERIAL PRIMARY KEY,
    contatore_id INTEGER NOT NULL REFERENCES contatori(id),
    data_lettura TIMESTAMP NOT NULL,
    valore NUMERIC(12,3) NOT NULL,
    tipo VARCHAR(20),
    fonte VARCHAR(50),
    validata BOOLEAN DEFAULT FALSE
);

CREATE TABLE letture_fatturazione (
    id SERIAL PRIMARY KEY,
    contatore_id INTEGER NOT NULL REFERENCES contatori(id),
    data_lettura DATE NOT NULL,
    valore NUMERIC(12,3) NOT NULL,
    tipo VARCHAR(20),
    CONSTRAINT unq_lettura UNIQUE (contatore_id, data_lettura)
);
Questa struttura è molto robusta perché:
    • Mantieni storico e tracciabilità.
    • Puoi validare letture provenienti da fonti diverse.
    • Se serve puoi anche ricostruire la cronologia o verificare eventuali contestazioni.
    • La tabella di fatturazione è snella e ottimizzata solo per dati consolidati.
1️⃣ letture_raw (letture grezze o di acquisizione)
id	id_contatore	timestamp_lettura	valore	tipo_acquisizione	validata (bool)
1	1001	2025-03-28 08:15	12345	TELELETTURA	false


2️⃣ letture_acconti
id	id_contatore	data (Y-m-d)	valore	note	stato_conguaglio
1	1001	2025-02-01	12000	stima	da_conguagliare

3️⃣ letture_definitive (per la fatturazione)
id	id_contatore	data (Y-m-d)	valore	tipo_lettura (es: manuale, automatica, conguaglio)
1	1001	2025-02-01	12500	conguaglio

Perché è una buona scelta?
    • Acconti separati: Ti permette di distinguere le letture provvisorie da quelle definitive.
    • Flessibilità: Le letture raw possono contenere anche dati scartati o fuori controllo.
    • Storico: Puoi mantenere una cronologia precisa di tutte le letture.
    • Conguaglio: Semplice da calcolare perché acconti e definitive sono già separati.


    • Mini workflow di validazione e conguaglio
    • Mini ERD (Entity Relationship Diagram)
    • Mini esempio query (conguaglio, saldo, progressivi)
\[1\] Lettura Grezza (letture_raw)
       ↓
\[2\] Validazione Tecnica (scarti, controlli)
       ↓
\[3\] Classificazione:
     ├─ Se è acconto → \[letture_acconti\]
     └─ Se è definitiva → \[letture_definitive\]
       ↓
\[4\] Se è un acconto → in attesa di conguaglio
       ↓
\[5\] Quando arriva la definitiva:
       - Ricalcolo
       - Scrittura definitiva (letture_definitive)
       - Segna acconto come "conguagliato"
┌──────────────────────┐
│      contatori       │
└─────────┬────────────┘
          │ 1:N
          ▼
┌──────────────────────┐
│    letture_raw       │
└─────────┬────────────┘
          │ Validazione
          ▼
 ┌──────────────────┐     ┌──────────────────────┐
 │ letture_acconti  │     │ letture_definitive   │
 └──────────────────┘     └──────────────────────┘
          │
     Conguaglio
          ▼
 ┌──────────────────┐
 │    fatture       │
 └──────────────────┘
sELECT 
    l_def.id_contatore,
    l_def.data AS data_definitiva,
    l_def.valore AS valore_definitiva,
    l_acc.valore AS valore_acconto,
    (l_def.valore - l_acc.valore) AS delta_conguaglio
FROM letture_definitive l_def
LEFT JOIN letture_acconti l_acc
    ON l_def.id_contatore = l_acc.id_contatore
    AND l_def.data = l_acc.data
WHERE l_acc.stato_conguaglio = 'da_conguagliare';

Le letture_acconti possono contenere:
        ◦ letture stimate
        ◦ letture da clienti
        ◦ letture rilevate in periodo non allineato
    • Le letture_definitive devono essere:
        ◦ con data anno-mese-giorno univoca
        ◦ valide e pronte per la fatturazione
    • Il conguaglio viene calcolato solo se esiste una lettura definitiva per la stessa data



---


---
{% include-markdown "signature-core.md" %}
