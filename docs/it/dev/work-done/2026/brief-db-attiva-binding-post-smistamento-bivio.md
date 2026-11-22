# Brief DB — Attivare il binding `post_smistamento` su SMISTAMENTO (bivio PREVENTIVI)

> **Tipo**: brief DB (fix seed/config) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🔴 alta (blocca lo smoke E2E merce del percorso PREVENTIVI 9004)
> **Data**: 2026-07-01 · **Origine**: smoke `smoke-test-pratica-preventivi-bivio.sh`
> **Correlato**: [brief-db-chiusura-pratica-nessun-lavoro-pendente.md](brief-db-chiusura-pratica-nessun-lavoro-pendente.md) (bivio rev.3, BE ✅)

## ✅ RISOLTO (2026-07-01)

Binding riattivato: `template_flussi_handler_eventi` id=9004 ora
`esito_richiesto='MERCE_PRESENTE'`, **`attivo=true`** (verificato a DB). L'handler
`vendita.post_smistamento` viene dispatchato → l'ordine merce si aggancia alla
pratica. **Smoke `smoke-test-pratica-preventivi-bivio.sh` verde** (rami MERCE +
SOLO_SERVIZI). Brief chiuso → work-done.

## Sintomo

Nello smoke E2E del ramo **MERCE** (tipo 9004): `completa-smistamento` ritorna
correttamente `esito=MERCE_PRESENTE` e la pratica resta APERTA, ma l'ordine merce
**non viene agganciato** alla pratica (`GET /vendite/ordini/per-pratica/` vuoto) →
il giro non prosegue a CONFERMA_ORDINE/INVIO_COMMESSA.

## Diagnosi (accertata sul DB applicato)

L'handler di completamento `vendita.post_smistamento` **non viene dispatchato**
perché il suo binding è **inattivo**. Il dispatch (`fn`/repo `get_handler_eventi`)
filtra `tfhe.attivo = true AND hf.attivo = true`:

```sql
SELECT e.id, e.template_flusso_id, tf.codice, e.evento, e.esito_richiesto,
       hf.handler_key, e.attivo
FROM pratiche.template_flussi_handler_eventi e
JOIN pratiche.template_flussi tf ON tf.id = e.template_flusso_id
JOIN pratiche.handler_flussi   hf ON hf.id = e.handler_id
WHERE tf.codice = 'SMISTAMENTO' AND hf.handler_key = 'vendita.post_smistamento';
-- risultato attuale:
-- id=9004 | 9012 | SMISTAMENTO | COMPLETATO | MERCE_PRESENTE | vendita.post_smistamento | attivo=FALSE
```

Il binding è per il resto **corretto** (evento `COMPLETATO`, esito `MERCE_PRESENTE`,
handler giusto) — manca solo `attivo=true`.

## Perché è successo

- `20260630-08-seed-binding-post-smistamento` **INSERT** la riga con `attivo=true`
  ma con `ON CONFLICT ON CONSTRAINT uq_tfhe DO NOTHING`: se esisteva già una riga
  per `(template, evento, handler)` con `attivo=false` (da un seed/stato
  precedente), il conflitto **non la riattiva**.
- `20260701-05-configura-bivio-preventivi` step (4) fa solo
  `UPDATE ... SET esito_richiesto = 'MERCE_PRESENTE' WHERE esito_richiesto='POSITIVO'`
  → tocca l'esito, **non** `attivo`.

Risultato: esito ri-puntato a `MERCE_PRESENTE` ma `attivo` rimasto `false` — in
contraddizione con la decisione documentata in `20260630-08`
("attivo=true: binding attivo da subito, progetto senza produzione";
cfr. memoria `reference_binding_handler_flusso_attivo_false`).

## Fix richiesto

Attivare il binding, in modo idempotente e resistente al re-seed. Due opzioni:

1. **Nuovo changeset** (`runAlways`/`runOnChange`) che riattiva la riga per chiave
   stabile:

   ```sql
   UPDATE pratiche.template_flussi_handler_eventi e
      SET attivo = true
     FROM pratiche.template_flussi tf
     JOIN pratiche.tipi_prestazione tp ON tp.id = tf.tipo_prestazione_id
     JOIN pratiche.handler_flussi   hf ON hf.handler_key = 'vendita.post_smistamento'
    WHERE tp.codice_interno = 'PREVENTIVI'
      AND tf.codice         = 'SMISTAMENTO'
      AND e.template_flusso_id = tf.id
      AND e.handler_id         = hf.id
      AND e.evento             = 'COMPLETATO'
      AND e.attivo IS DISTINCT FROM true;
   ```

2. **Oppure** cambiare `20260630-08` in `ON CONFLICT ... DO UPDATE
   SET attivo = true` (così un re-seed corregge sempre lo stato). Da valutare
   insieme perché `esito_richiesto` è ora `MERCE_PRESENTE` (il DO UPDATE non deve
   riportarlo a `POSITIVO`).

## Criterio di accettazione

- `get_handler_eventi(9012, 'COMPLETATO', 'MERCE_PRESENTE')` ritorna
  `vendita.post_smistamento` (binding attivo).
- Smoke `smoke-test-pratica-preventivi-bivio.sh` scenario MERCE: dopo
  `completa-smistamento`, `GET /vendite/ordini/per-pratica/` ritorna l'ordine
  agganciato (COLLEGATO) → il giro prosegue a CONFERMA_ORDINE/INVIO_COMMESSA →
  pratica CHIUSA.

## Note

- **Lato BE nulla da cambiare**: l'handler `post_smistamento` è merce-only e
  corretto; il classificatore d'esito usa lo stesso lookup dell'handler
  (`get_ordine_by_documento_origine`). È solo il flag `attivo` del binding.
- Il ramo **SOLO_SERVIZI** dello smoke non dipende da questo handler e passa già.
