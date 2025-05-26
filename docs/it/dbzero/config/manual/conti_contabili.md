### Scopo
Catalogo dei conti contabili utilizzabili, suddivisi tra acquisto e vendita.

### Logiche e vincoli
- **`codice_conto`**: stringa univoca identificativa del conto.
- **`tipo_conto`**: deve essere **`'A'`** (Acquisto) o **`'V'`** (Vendita).
- **Indici** su `tipo_conto` e `descrizione` per velocizzare filtri e ricerche.
