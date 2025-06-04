
# 🗂️ Riepilogo attività — Anagrafica Territoriale (Zero ERP)

## ✅ Tabelle progettate / aggiornate

| Tabella/PostgreSQL              | Descrizione                                               |
|--------------------------------|------------------------------------------------------------|
| `config.comuni`                | Tabella aggiornata con colonna `extra_country` e `codice_postale` gestito a parte |
| `config.codici_postali`        | Tabella normalizzata per gestire CAP multipli per comune, con tracciabilità |
| `storico.comuni`               | Tabella storica con `valid_from`, `valid_to`, `extra_country`, `stato` |
| `storico.codici_postali`       | Versione storicizzata del CAP (validità temporale e stato) |
| `storico.comune_trasformazioni` | Tabella per tracciare **accorpamenti o scissioni** tra comuni |

---

## 🧩 Struttura `extra_country` condivisa

```json
{
  "stato_utilizzo": "ITA",
  "codice_istat": "...",
  "codice_catastale": "...",
  "fascia_climatica": "...",
  "codice_postale": "..."  // opzionale
}
```

Utilizzata per:
- mantenere flessibilità nei dati
- supportare estensioni future (es. recapiti esteri)
- raggruppare attributi “secondari” o di dettaglio

---

## 💡 Concetti fondamentali

### 📌 Storicizzazione

- Avviene **solo per eventi rilevanti** (es. fusione, soppressione, divisione)
- Gestita **dal software**, non da trigger automatici
- Nuova versione = nuovo record con `valid_from`
- Vecchio record = aggiornato con `valid_to`

---

### 📌 Accorpamento vs Scissione

| Evento         | Effetto                        | Azione sui clienti |
|----------------|-------------------------------|---------------------|
| Accorpamento   | Più comuni → uno               | Nessuna             |
| Scissione      | Uno → più comuni               | Riassegnazione      |

- Con **scissione** è necessario prevedere un riassegnamento degli indirizzi/clienti

---

## 🛠️ Infrastruttura di supporto

- `storico.comune_trasformazioni`: mappa accorpamenti/scissioni
- Indici su `jsonb ->>` per prestazioni nelle ricerche
- Compatibilità con letture temporali e filtri storici

---

## 📦 Prontezza futura

- Progettazione multi-nazione
- Adatta per moduli **utility** (flussi anagrafici, fiscalità)
- Pronta per logiche di **audit** e gestione tempo

---

*Generato automaticamente — Zero ERP*


---

