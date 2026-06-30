# Brief DB — Binding handler-evento su SMISTAMENTO (crea flussi ordine on-demand)

> **Tipo**: brief DB (cosa serve, non come) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🟡 media · **Data**: 2026-06-30 · **Scope**: solo seed catalogo pratiche
> **Origine**: Fase 2 di [analisi-uniformita-pratica-preventivi.md](analisi-uniformita-pratica-preventivi.md)
> + [piano-be-fe-uniformita-pratica-preventivi.md](piano-be-fe-uniformita-pratica-preventivi.md) (B1).

---

## Contesto in una frase

Nel nuovo percorso `PREVENTIVI` (9004), il flusso **SMISTAMENTO (9012)** apre il Pannello
Smistamento (FE già fatto): l'operatore manda la merce a ordine e i servizi a commessa. Al
**completamento** di SMISTAMENTO serve eseguire un handler di dominio (vendite) che, **solo se
è stato prodotto un ordine merce**, agganci l'ordine alla pratica e **crei on-demand** i flussi
a valle `CONFERMA_ORDINE (9013)` e `INVIO_COMMESSA (9014)`. La logica è BE (vendite); qui serve
solo il **binding** che la fa scattare.

## Cosa serve (seed)

1. **`pratiche.handler_flussi`**: una nuova `handler_key` per l'handler post-smistamento
   (proposta nome: `vendita.post_smistamento`; il nome esatto lo concordiamo col BE).
2. **`pratiche.template_flussi_handler_eventi`**: binding sul flusso **SMISTAMENTO (9012)**,
   evento **`COMPLETATO`**, esito **`POSITIVO`** → la `handler_key` di cui sopra.
   (Stessa forma del binding esistente su APPROVAZIONE_CLIENTE 9011 → `vendita.accetta_preventivo`.)

**Criterio di accettazione**: completando SMISTAMENTO con esito POSITIVO, il motore dispatcha
l'handler `vendita.post_smistamento` nella stessa transazione del completamento (come per
`accetta_preventivo`). Binding senza handler registrato → `E_HANDLER_NON_REGISTRATO` (fail-fast,
comportamento esistente).

## Fuori scope (BE vendite — lo facciamo noi)

L'handler `vendita.post_smistamento`:
- risolve il preventivo ROOT della pratica e trova l'ordine generato (sorgente PREVENTIVO);
- se l'ordine esiste: lo **aggancia** alla pratica (`pratiche_sorgenti` COLLEGATO) e **crea**
  i flussi 9013/9014 via `pratiche_service.crea_flusso` (i prerequisiti DB li abilitano:
  `9013 ← 9012 POSITIVO`, `9014 ← 9013 POSITIVO`, già seedati);
- se non c'è ordine (preventivo tutto-servizi): non crea 9013/9014 (la commessa è già nata dal
  push servizi). Idempotente sul re-fire.

## Note

- I prerequisiti `60←50` e `50←40` risultano **già applicati** a DB (verificato: 9014←9013,
  9013←9012, esito POSITIVO). Nessuna modifica ai prerequisiti richiesta.
- Coerente con la direzione anelli: `pratiche` resta generico (esegue un binding), la
  conoscenza "ordine/merce" vive in `vendite` (handler).
