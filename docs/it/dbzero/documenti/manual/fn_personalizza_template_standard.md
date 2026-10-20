## 📘 Documentazione Concettuale – Funzione `documenti.fn_personalizza_template_standard()`

> 👀 **Vedi anche**
>
> [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) (§ «Il modello standard»)
> [documenti.fn_crea_bozza_da_versione](/dbzero/documenti/funzioni/fn_crea_bozza_da_versione)
> [documenti.vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto)
> [Guida — Documenti e Stampe](/guide/documenti-e-stampe) (§4.2)

### 🎯 Scopo

(21-10-2026 — brief `brief-db-modelli-documento-standard`, §10.3 K-6; D-2, D-6, D-9 di Tid)

**«Personalizza»**: crea il modello di un'azienda a partire da uno standard, in un'operazione sola
(funzione madre: tutto o niente). Restituisce l'id del modello nuovo.

### Che cosa fa

1. Controlla che il modello sia uno standard.
2. Chiede alla porta unica (`fn_risolvi_template_applicabile`, col modello indicato) la **versione
   con cui lo standard stampa oggi**. Uno standard spento, o senza versione valida oggi, non si
   personalizza.
3. Crea il modello dell'azienda: tipo, sorgente, builder e nome file dello standard; codice,
   codice interno e descrizione dello standard se non indicati.
4. Crea la bozza v1, copiata da quella versione, con l'origine dichiarata
   (`derivata_da_versione_id`).

### Il flag predefinito

La copia nasce **predefinita** se l'azienda non ha già un suo predefinito attivo per quel
documento; altrimenti no, e scegliere fra i due resta all'operatore. Il parametro `p_is_default`
la impone: vero accanto a un predefinito, risponde l'unico del predefinito.

Finché la copia è in bozza non può stampare, e l'azienda continua con lo standard.

### Errori

| Codice | Quando |
|---|---|
| `E_DOCUMENTI_PERSONALIZZA_NON_STANDARD` | il modello indicato è già di un'azienda |
| `E_DOCUMENTI_TEMPLATE_NON_STAMPABILE` | lo standard oggi non stampa (spento, nessuna versione valida) |
| `E_PARAMETRO_INVALIDO` | argomenti nulli o ≤ 0, modello inesistente |
| `23505` dagli unici | un codice già dell'azienda per la sorgente, o un secondo predefinito imposto |

### Note

Il perimetro dell'azienda lo controlla chi chiama (il backend), come per ogni modello d'azienda: le
tabelle dei modelli non hanno RLS.
