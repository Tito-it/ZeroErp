# 📘 Documentazione Anagrafica Soggetti - Zero ERP

Questa documentazione descrive le regole di progettazione e implementazione della tabella anagrafica `anagrafiche.soggetti` in **Zero ERP**.

---

## ✅ Obiettivi dell'Anagrafica Soggetti

Garantire coerenza, qualità, univocità e facilità di ricerca nelle informazioni dei soggetti (persone fisiche, giuridiche e fisiche forzate).

---

## 📌 Struttura della Tabella

### Colonne principali:
- `tipo_soggetto` ENUM (`F`, `G`, `X`)
  - `F`: Persona fisica
  - `G`: Persona giuridica
  - `X`: Persona fisica forzata (CF che a causa di riscontro devono essere forzati o enti iniziano con 8)

- Campi identificativi:
  - `codice_fiscale` (CHAR)
  - `partita_iva` (CHAR)
  - `ragione_sociale` (VARCHAR)
  - `nome` (VARCHAR)
  - `cognome` (VARCHAR)

- Campi utili per conversioni:
  - `identificativo_old` (VARCHAR)

---

## 🚩 Regole di Validazione Condizionale

| Tipo soggetto | Campi obbligatori                                |
|---------------|---------------------------------------------------|
| **F (Fisico)**| `nome`, `cognome`, `codice_fiscale`               |
| **G (Giuridico)**| `ragione_sociale`, `partita_iva`               |
| **X (Fisico Forzato)**| `codice_fiscale’|

**Inoltre**, obbligatorio che almeno uno tra `codice_fiscale` e `partita_iva` sia sempre valorizzato.

### Esempio Constraint SQL:
```sql
ALTER TABLE anagrafiche.soggetti
ADD CONSTRAINT chk_cf_o_piva
CHECK (
    codice_fiscale IS NOT NULL OR partita_iva IS NOT NULL
);

ALTER TABLE anagrafiche.soggetti
ADD CONSTRAINT chk_tipo_soggetto
CHECK (
    (tipo_soggetto = 'F' AND nome IS NOT NULL AND cognome IS NOT NULL AND codice_fiscale IS NOT NULL) OR
    (tipo_soggetto = 'G' AND ragione_sociale IS NOT NULL AND partita_iva IS NOT NULL) OR
    (tipo_soggetto = 'X' AND codice_fiscale  is not null ')
);
```

---

## 🔗 Campo Identificativo Univoco

Per garantire l'univocità assoluta del soggetto in base al `codice_fiscale` o `partita_iva`, è stato aggiunto un campo generato automaticamente:

```sql
ALTER TABLE anagrafiche.soggetti
ADD COLUMN identificativo_univoco TEXT GENERATED ALWAYS AS (
    COALESCE(codice_fiscale, partita_iva)
) STORED UNIQUE;
```

- PostgreSQL crea automaticamente un indice fisico su questo campo per prestazioni ottimali.

---

## 🔍 Campo "Ragione Sociale Completa" per Ricerca

Per facilitare le ricerche, è presente un campo generato automaticamente che combina `ragione_sociale` oppure `cognome` e `nome`:

```sql
ALTER TABLE anagrafiche.soggetti
ADD COLUMN ragione_sociale_completa TEXT GENERATED ALWAYS AS (
    COALESCE(ragione_sociale, cognome || ' ' || nome)
) STORED;

CREATE INDEX idx_ragione_sociale_completa ON anagrafiche.soggetti (ragione_sociale_completa);
```

### Esempi di comportamento:

|tipo_soggetto|ragione_sociale|nome|cognome|ragione_sociale_completa (GENERATA)|
|-------------|---------------|----|-------|-----------------------------------|
|F|null|Mario|Rossi|Mario Rossi|
|G|ABC srl|null|null|ABC srl|
|X|null|null|null|null|

---

## 🧩 Raccomandazioni future

- Gestire dettagli ulteriori tramite codice applicativo (Django).
- Creare API REST per integrazione front-end.
- Aggiornare costantemente questa documentazione per ogni modifica strutturale.

---

> 🧠 **"Dati ordinati oggi, facilità di gestione domani."**