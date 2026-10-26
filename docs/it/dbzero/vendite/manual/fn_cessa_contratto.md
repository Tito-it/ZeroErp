## 📘 Documentazione Concettuale – Funzione `vendite.fn_cessa_contratto(bigint, date)`

> 👀 **Vedi anche**
>
> [vendite.contratti](/dbzero/vendite/tabelle/contratti) ·
> [vendite.fn_cambia_stato_contratto](/dbzero/vendite/funzioni/fn_cambia_stato_contratto) ·
> [vendite.fn_cessa_contratti_scaduti](/dbzero/vendite/funzioni/fn_cessa_contratti_scaduti) ·
> [vendite.fn_chiudi_contratto_per_successione](/dbzero/vendite/funzioni/fn_chiudi_contratto_per_successione) ·
> guida [Gestione contratti](/guide/gestione-contratti) §3.1

### 🎯 Scopo
(26-10-2026 — brief `brief-modello-documento-vendita` §11, decisioni Y-2 e Y-3)

**La cessazione manuale di un contratto, con la sua data.** La data decide che cosa
succede, e lo decide il database (prima lo decideva il backend):

| Data | Esito |
| --- | --- |
| oggi | data scritta e contratto `CESSATO` |
| futura | **programmata**: solo la data, il contratto resta `ATTIVO`; lo cessa la chiusura per scadenza il giorno dopo la data |
| passata | `E_CONTRATTO_VALIDO_AL_RETROATTIVO`: non si riscrive la storia del contratto |
| mancante | `E_CONTRATTO_CESSAZIONE_SENZA_DATA` |

### Regole

* **Il permesso** è quello della riga ATTIVO → CESSATO: l'azione `emetti_contratto`,
  anche per la cessazione programmata (è la stessa decisione). Un secondo «Cessa»:
  `E_DOC_GIA_NELLO_STATO`.
* **La strada** la dice la matrice: un contratto in bozza non si cessa, neanche con una
  data futura (`E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA`). Il controllo sta qui perché la
  cessazione programmata non cambia lo stato, e il guard di transizione non la vedrebbe.
* **La data passata** la rifiuta questo verbo, che è l'unico a scrivere la data della
  cessazione. Il rinnovo dall'offerta (`fn_chiudi_contratto_per_successione`) scrive la
  sua data di fine da sé: è già una cessazione programmata.
* **Il perimetro**: un contratto che l'operatore non vede è come inesistente
  (`E_CONTRATTO_NON_TROVATO`).
* Ritorna anche `programmata`: vero quando lo stato non è cambiato.

### Chi la chiama

Il backend, per «Cessa» (il cambio di stato del contratto verso `CESSATO`, con la data).
