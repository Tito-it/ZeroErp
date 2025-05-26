### Scopo
Catalogo dei codici IVA, con aliquota e riferimenti a natura e conti contabili.

### Logiche e vincoli
- **Unicità** su `codice_iva`.
- **Assoggettamento**: deve appartenere all’insieme di codici validi (`NS`, `NI`, etc.).
- **FK** sui conti contabili:
  - `conto_iva_acquisti_id` deve essere un **conto di tipo A**
  - `conto_iva_vendita_id` deve essere un **conto di tipo V**
- **Split payment**: `id_iva_split` punta allo stesso catalogo `config.iva`.
