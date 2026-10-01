## 📘 Documentazione Concettuale – Tabella `ui.lista_colonna_permesso`

> 👀 **Vedi anche**
>
> [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna)
> [config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
>
> Architettura di riferimento:
>
> [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
> Funzione:
>
> [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config)

La tabella **`ui.lista_colonna_permesso`** implementa il **controllo accesso a livello di singola colonna** per profilo di accesso. Estende il sistema permessi esistente senza duplicarlo: usa `config.profili_accesso` e `config.livello_accesso` già in uso negli altri meccanismi di permesso.

---

### 🎯 Scopo Principale

* **Permessi granulari per colonna**: permettere che determinate colonne (es. dati personali, margini, condizioni commerciali) siano invisibili o non esportabili per specifici profili di accesso.
* **Integrazione con il sistema permessi**: riusa `config.profili_accesso` e la risoluzione tramite `fn_get_profili_accesso_applicabili`, evitando logiche duplicate. I profili hanno priorità (AD_HOC=1 prevale su REPARTO=2).
* **Due modelli distinti per colonna**: il comportamento dipende dal flag `lista_colonna.sensibile`:
  * `sensibile=FALSE` → **deny-list**: assenza di riga = accesso pieno. Si scrivono solo le restrizioni.
  * `sensibile=TRUE` → **allow-list**: assenza di riga = bloccata di default. Si scrivono i grant espliciti.

---

### Livelli di accesso (`config.livello_accesso`)

| Valore | Effetto colonna |
|--------|-----------------|
| `TUTTO` | Visibile e esportabile |
| `LETTURA` | Visibile a video, non esportabile |
| `BLOCCATO` | Nascosta completamente (rimossa dall'output di `fn_resolve_lista_config`) ed esclusa dalla ricerca libera (`fn_lista_colonne_ricerca_full`) |

---

### Logica di risoluzione con più profili

Quando un utente ha più profili applicabili (es. profilo AD_HOC + profilo REPARTO) che coprono la stessa colonna, vince:

1. Il profilo con **priorità più bassa** (AD_HOC=1 prevale su REPARTO=2)
2. A parità di priorità, il **livello più restrittivo** (BLOCCATO > LETTURA > TUTTO)

La regola ha una sede sola, [`ui.fn_lista_colonne_livello`](/dbzero/ui/funzioni/fn_lista_colonne_livello), che la legge per due consumatori: `fn_resolve_lista_config` (quali colonne mostrare) e `fn_lista_colonne_ricerca_full` (in quali colonne cercare).

---

### Relazioni

| Tabella | Campo | Scopo |
|---------|-------|-------|
| `ui.lista_colonna` | `colonna_id` | Colonna cui si applica il permesso. ON DELETE CASCADE. |
| `config.profili_accesso` | `profilo_accesso_id` | Profilo che riceve il permesso |

---

### Note operative

* Non creare logica di risoluzione profili duplicata: usare sempre `script.fn_get_profili_accesso_applicabili` come negli altri meccanismi.
* La FK su `lista_colonna` è `ON DELETE CASCADE`: eliminare una colonna dal catalogo rimuove automaticamente tutti i suoi permessi.
* Il UNIQUE su `(colonna_id, profilo_accesso_id)` garantisce al massimo un livello per coppia colonna/profilo.
