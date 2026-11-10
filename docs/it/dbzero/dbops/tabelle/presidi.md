{% include-markdown "it/dbzero/dbops/manual/presidi.md" %}
# 📚 Tabella `presidi`

> 📝 **Descrizione**
>
> Catalogo delle viste di presidio: per ogni vista, che cosa significa una sua riga. E' il terzo pezzo accanto alla misura (la vista) e al registro del debito (le voci note): dice chi la legge. Non e' un elenco nel backend perche' sarebbe una seconda sorgente di verita', e divergerebbe alla prima vista nuova: il presidio nascerebbe fuori dal digest, in silenzio. Nessuna colonna soglia: il debito si tiene con un registro di voci per nome, perche' un intero e' cieco sullo scambio (un debito saldato piu' un difetto nuovo lasciano il numero fermo). E nessun destinatario: a chi arriva la posta di questa macchina e' un fatto di deploy, non di catalogo.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| vista | text | NO |  |
| natura | text | NO |  |
| colonna_stato | text | YES |  |
| stato_atteso | text | YES |  |
| registro | text | YES |  |
| presidiato_da | text | YES |  |
| cadenza | text | NO |  |
| perimetro | text | NO |  |
| attivo | boolean | NO | true |
| obsoleto_dal | date | YES |  |
| nota | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| chi_agisce | text | YES |  |
| colonna_variante | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_presidi_cadenza |  |
| CHECK | chk_presidi_cancello_ha_presidio |  |
| CHECK | chk_presidi_chi_agisce |  |
| CHECK | chk_presidi_chi_agisce_se_allarma |  |
| CHECK | chk_presidi_colonna_variante_non_vuota |  |
| CHECK | chk_presidi_coppia_stato |  |
| CHECK | chk_presidi_fuori_digest_cadenza_mai |  |
| CHECK | chk_presidi_natura |  |
| CHECK | chk_presidi_nota_non_vuota |  |
| CHECK | chk_presidi_perimetro |  |
| CHECK | chk_presidi_registro_qualificato |  |
| CHECK | chk_presidi_vista_qualificata |  |
| PRIMARY KEY | pk_presidi | id |
| UNIQUE | uq_presidi_vista | vista |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_presidi | `CREATE UNIQUE INDEX pk_presidi ON dbops.presidi USING btree (id)` |
| uq_presidi_vista | `CREATE UNIQUE INDEX uq_presidi_vista ON dbops.presidi USING btree (vista)` |

---
{% include-markdown "signature-core.md" %}
