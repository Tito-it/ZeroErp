## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_pavimento_emissione`

> 👀 **Vedi anche**
>
> [vendite.fn_get_limite_emissione_default](/dbzero/vendite/funzioni/fn_get_limite_emissione_default)
> [vendite.fn_get_pavimento_sequenza](/dbzero/vendite/funzioni/fn_get_pavimento_sequenza)
> [vendite.fn_get_pavimento_data_documento](/dbzero/vendite/funzioni/fn_get_pavimento_data_documento)
> [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa)

---

### 🎯 Scopo Principale

**Da quale data in poi un documento di questo sezionale è ancora EMETTIBILE.**

Un documento fiscale non può portare una data indietro nel tempo quanto si
vuole: fra la data del documento e il suo invio c'è un termine, e passato quello
la data non è più utilizzabile. Questa funzione dice **dov'è quel pavimento**.

```sql
-- immediata: la competenza non c'entra
SELECT vendite.fn_get_pavimento_emissione(3, NULL);

-- differita: la competenza decide se il permesso è ancora aperto
SELECT vendite.fn_get_pavimento_emissione(4, date '2026-07-01');
```

⛔ **Non dice niente sulla sequenza dei numeri**: quello è l'altro pavimento
([`fn_get_pavimento_sequenza`](/dbzero/vendite/funzioni/fn_get_pavimento_sequenza)),
e a comporli è
[`fn_get_pavimento_data_documento`](/dbzero/vendite/funzioni/fn_get_pavimento_data_documento).

ℹ️ **Torna sempre una data, mai `NULL`**: il pavimento generale esiste sempre.
Chi vuole un sezionale senza limite pratico configura un numero grande — è
esattamente ciò che fanno le fixture pgTAP che numerano con date d'archivio.

---

### ⭐ Una regola generale, e un permesso che scade

Il termine non è «una forma per l'immediata e una per la differita». È **una
regola sola** con una **esenzione**:

* **la regola** — un documento non può essere datato più di *N* giorni fa. Vale
  per **tutti** i documenti, su entrambe le politiche;
* **il permesso della differita** — un documento datato l'ultimo giorno del mese
  *M* resta emettibile fino al giorno *G* del mese *M+1*. Quando quel giorno
  passa, torna a valere la regola.

```
pavimento(registro, competenza) =
    LEAST( data_operativa() − giorni,
           CASE WHEN politica = 'FINE_MESE_COMPETENZA'
                 AND data_operativa() <= scadenza(competenza)
                THEN fine_mese(competenza) END )
```

⚠️ **`LEAST` e non `GREATEST`, ed è il punto**: la regola generale e il permesso
sono **due ragioni indipendenti** per cui una data è ammessa, e basta che ne
valga una. `LEAST` in PostgreSQL ignora i `NULL`, quindi a permesso scaduto il
secondo ramo sparisce da solo e resta `oggi − giorni`.

⛔ **La forma che sembra giusta e non lo è**, scritta qui perché non venga
riproposta: mettere la *scadenza* («il 15 del mese successivo») dentro un
`GREATEST` con la data della politica. Una scadenza vive nello spazio «quando
stai lavorando», un pavimento nello spazio «data del documento», e messe insieme
farebbero nascere **ogni** documento differito datato il 15 del mese dopo — cioè
romperebbero il flusso normale, non i casi di bordo.

---

### ⭐ Il giorno di scadenza si calcola SUL MESE

```
scadenza = LEAST(primo_del_mese_successivo + giorno − 1,
                 ultimo_del_mese_successivo)
```

Con `31` configurato su un febbraio la scadenza è il **28** (o il 29), non il 2
marzo. Il `CHECK` di colonna ammette `1..31` apposta: a fare i conti col mese è
**questa funzione**, perché un vincolo non conosce il mese su cui il valore
cadrà.

---

### Dove vive il valore

| dove | cosa |
|---|---|
| `config.parameters.VENDITE_LIMITE_EMISSIONE_IMMEDIATA_GIORNI` | il default dei giorni (`12`) |
| `config.parameters.VENDITE_LIMITE_EMISSIONE_DIFFERITA_GIORNO_MESE` | il default del giorno del mese (`15`) |
| `registri_fatturazione.limite_emissione_giorni` | l'override per sezionale — `NULL` = vale il default |
| `registri_fatturazione.limite_emissione_giorno_mese` | idem, e ammesso solo sulla differita |

⛔ **Il parametro NON si legge con `script.fn_get_parameter_full`**, che pure è
il lettore canonico: la sua cascata di override (utente / gruppo / sessione /
emittente) darebbe **allo stesso documento** limiti diversi a seconda di **chi lo
genera**, cioè il difetto che il limite di emissione chiude. Si legge il
`default_value` nudo, e l'unico asse di override è il **registro** — che è un
fatto del sezionale, non di chi ci lavora. È la stessa scelta, e la stessa
ragione, di [`script.fn_data_operativa`](/dbzero/script/funzioni/fn_data_operativa).

⛔ **Il valore è una lettura configurabile, non una costante di legge.** Il
software non deve incorporare un'interpretazione fiscale in una costante: se un
giorno la norma cambia, cambia il **dato**.

---

### Note operative

* ⛔ **Nessun ramo che ingoia**: una politica non riconosciuta **solleva**
  (`E_CONFIG_MANCANTE`) invece di comportarsi come `OGGI`. Un pavimento
  plausibile e sbagliato non lo nota nessuno, e quando lo si nota il numero è
  già stato consumato.
* ⛔ Con politica `FINE_MESE_COMPETENZA` la **competenza è obbligatoria**:
  senza, il pavimento sarebbe più severo del vero senza dirlo
  (`E_VENDITE_CHIAMATA_NON_VALIDA`).
* Guard di parametro: `p_registro_id` obbligatorio e maggiore di zero;
  registro inesistente → `E_CONFIG_MANCANTE`.
* `STABLE`, `SECURITY INVOKER`.
* Brief: `brief-db-limite-emissione-e-data-verificata` §11 DB-3.

---

{% include-markdown "signature-core.md" %}
