### Scopo
Restituire i dati del codice IVA per un dato Paese, combinando valori base e override.

### Logica di funzionamento
1. **Ricerca** del record base in `config.iva` tramite `codice_iva`.
2. **Join** con `config.stati` per ottenere informazioni sul Paese.
3. **Left join** con `config.iva_stati` per verificare eventuale override.
4. **`COALESCE`** tra valori override e base per `aliquota` e `assoggettamento`.
