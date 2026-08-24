## 📘 Documentazione Concettuale – Tabella `dbops.codici_errore_senza_policy`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.codici_errore](/dbzero/config/tabelle/codici_errore)
> • [config.classi_errore](/dbzero/config/tabelle/classi_errore)
> • [dbops.messaggi_errore_codici_legacy](/dbzero/dbops/tabelle/messaggi_errore_codici_legacy)
>
Approfondimento viste:
> • [dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Registro del debito del «terzo lato»**: i codici errore che una funzione PL/pgSQL viva può
nominare e che **non hanno una voce** in `backend/apps/core/services/error_policies.py`.

L'effetto del difetto è preciso e limitato: **l'operatore legge comunque la frase giusta** —
quella viene dal catalogo — ma il **tipo** di risposta HTTP resta appiattito su `400` anche
quando la verità sarebbe `404` o `403`. Non è un errore sbagliato: è un errore classificato
male nel trasporto.

---

### ⭐ Perché un registro invece della bonifica subito

Perché il cancello potesse essere acceso **subito**, invece che a bonifica finita.

Un presidio rosso dal primo giorno viene disattivato — è la sua fine più comune. Registrando
il debito noto, il cancello nasce **verde** e diventa rosso solo su ciò che peggiora: un
codice nuovo senza policy. La bonifica dell'esistente procede a lotti per dominio, partendo
dai `da_trigger`, che sono quelli sul percorso di una richiesta.

---

### ⚠️ È un debito, non una whitelist

La differenza è operativa, non terminologica: **deve calare**. E il cancello deve pretendere
non solo che non entrino voci nuove, ma anche che **una voce che ha ottenuto la sua policy
venga tolta da qui**. Un registro che non si svuota mai è un elenco di eccezioni travestito.

La colonna `da_trigger` è l'ordine di lavoro; `data_registrazione` è l'orologio del debito.

---

### ⚠️ Da non confondere con l'altro registro

| Registro | Che debito misura |
|---|---|
| `dbops.codici_errore_senza_policy` | codice **senza policy nel backend** → HTTP appiattito su 400 |
| `dbops.messaggi_errore_codici_legacy` | codice **fuori convenzione di nome** (`E_{MODULO}_{TIPO}`) |

Si somigliano nel nome e nella forma, ma il primo riguarda il *trasporto*, il secondo la
*nomenclatura*. Un codice può stare in uno, nell'altro, in entrambi o in nessuno.

---

### Misura canonica

`dbops.vw_codici_errore_da_dichiarare`. Il registro è la fotografia del debito accettato; la
vista è la misura che dice se è ancora quella giusta.

Decisione unica del 2026-08-05 (`brief-db-be-terzo-lato-presidio-codici`): **non è una
regressione**, è debito preesistente reso visibile.

---

{% include-markdown "signature-core.md" %}
