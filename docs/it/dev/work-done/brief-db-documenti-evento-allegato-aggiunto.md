# Brief DB — Estendere `evento_tipo` ammessi: `ALLEGATO_AGGIUNTO`

> **STATO: APPLICATO** (2026-06-03). DB: migration
> `00_schema/documenti/20260603-04-alter-documenti-generati-eventi-evento-tipo-allegato-aggiunto`
> (CHECK esteso). BE: emit `ALLEGATO_AGGIUNTO` in
> `DocumentGenerationService.aggiungi_allegati` (stessa `transaction.atomic()`
> del persist), coperto da test (`test_aggiungi_allegati_append_persiste_file`).
> Lacuna d'audit chiusa.
>
> **Branch**: `dev/db-tid`. **Tipo**: DDL minore (CHECK constraint extension).
> **Tempo stimato**: 5 minuti.
> **Contesto**: building block "genera documento + allegati" (cantiere
> 2026-05-27). Quando l'utente aggiunge allegati a un documento gia'
> generato (modalita' append, `OfferteService.aggiungi_allegati` /
> `DocumentGenerationService.aggiungi_allegati`), oggi il BE persiste i
> file ma **non emette evento** sulla timeline (`documenti_generati_eventi`)
> perche' il CHECK constraint v1 limita `evento_tipo` al set chiuso
> `{GENERATO, SCARICATO, STORAGE_ORPHAN}`.
>
> Audit lacuna: la timeline del documento non registra "quando e da chi e'
> stato aggiunto un allegato". Per closure dell'audit basta estendere il
> set ammesso.

---

## Fix richiesto

Aggiungere `ALLEGATO_AGGIUNTO` al CHECK constraint su
`documenti.documenti_generati_eventi.evento_tipo`.

**Migration nuova `00_schema`** (numero progressivo, non modificare la
migration originale gia' pushata):

```sql
ALTER TABLE documenti.documenti_generati_eventi
    DROP CONSTRAINT IF EXISTS chk_documenti_generati_eventi_evento_tipo;

ALTER TABLE documenti.documenti_generati_eventi
    ADD CONSTRAINT chk_documenti_generati_eventi_evento_tipo
    CHECK (evento_tipo IN (
        'GENERATO',
        'SCARICATO',
        'STORAGE_ORPHAN',
        'ALLEGATO_AGGIUNTO'
    ));
```

(Verificare il nome esatto del CHECK constraint nel doc `dbzero`; se
diverso adattare il `DROP CONSTRAINT IF EXISTS`.)

## Lato BE (post-merge DB)

In `apps.documenti.services.document_generation_service.aggiungi_allegati`,
aggiungere l'emit evento nella stessa `transaction.atomic()` dopo il
ciclo `_persisti_allegati`:

```python
self._repo.emit_evento_documento({
    "documento_generato_id": documento_id,
    "evento_tipo": "ALLEGATO_AGGIUNTO",
    "user_id": getattr(user, "id", None),
    "esito": "OK",
    "messaggio": None,
    "detail": {
        "n_allegati": len(allegati_persistiti),
        "file_ids": [a["id"] for a in allegati_persistiti],
        "size_bytes_tot": sum(a["size_bytes"] for a in allegati_persistiti),
    },
    "meta": {},
})
```

Il BE puo' essere preparato e testato con mock prima del merge DB
(l'INSERT fallirebbe sul CHECK fino a merge). Per evitare commit di codice
che non gira: aggiungere il blocco solo dopo conferma del merge DB.

## Note

- L'evento `ALLEGATO_AGGIUNTO` per il flusso di emissione (BOZZA->EMESSA)
  con allegati e' coperto dall'evento `GENERATO` esistente, che gia'
  riporta nel `detail` size_bytes + pdf_hash del principale. Gli allegati
  caricati all'emissione sono parte logica della "generazione iniziale";
  non serve un evento aggiuntivo.
- Il nuovo evento serve **solo** alla modalita' append post-emissione
  (`aggiungi_allegati`).

---

*Brief DB CHECK extension — Allinea timeline eventi al flusso allegati
append. Pronto per `dev/db-tid`.*
