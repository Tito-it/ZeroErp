### Scopo
Override delle aliquote e dell’assoggettamento IVA per specifico Stato/Paese.

### Logiche e vincoli
- **PK composito** `(iva_id, stato_id)` garantisce un solo override per coppia.
- **FK** a `config.iva` e `config.stati`.
- **Delete cascade** su `iva` per rimuovere automaticamente gli override.
- **Restrict** su `stati` per evitare cancellazioni se in uso.