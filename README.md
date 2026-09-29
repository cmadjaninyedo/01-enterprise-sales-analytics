# Enterprise Sales Analytics & Data Warehouse

## Problème métier
Une entreprise de distribution souhaite piloter sa performance
commerciale à partir de données dispersées. Ce projet construit un
entrepôt de données dimensionnel et un tableau de bord permettant
d'identifier les leviers de croissance et les zones de sous-performance.

**Conception d'un entrepôt de données en modèle dimensionnel, alimenté par un pipeline ETL Python reproductible et testé, exploité par SQL analytique et Power BI.**

## Points clés du projet
- ⭐ **Data Warehouse dimensionnel** : schéma en étoile complet (4 dimensions + 1 table de faits), grain documenté, clés et contraintes PK/FK
- ⭐ **ETL reproductible et idempotent** : Python + Pandas + SQLAlchemy → PostgreSQL, transactionnel, testé par une suite pytest
- ⭐ **SQL analytique avancé** : CTE, fonctions fenêtre (`LAG()`, `RANK()`), analyse temporelle (MoM/YoY), classements, KPI commerciaux
- ⭐ **Data Quality** : contrôles pré/post-chargement intégrés au pipeline + suite de tests indépendante
- ⭐ **Chaîne complète données → décision** : de la donnée brute au KPI Power BI jusqu'aux recommandations métier

## Données
- Source : Superstore Dataset (Kaggle)
- Volumétrie : 9 994 lignes, période 2014-2017
- Lien : https://www.kaggle.com/datasets/vivek468/superstore-dataset-final

## Architecture
CSV → Nettoyage Python (pandas) → PostgreSQL (schéma en étoile) → SQL analytique → Power BI

Voir `docs/schema_etoile.png`.

```text
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ Superstore  │ → │ Python ETL  │ → │ PostgreSQL  │ → │ SQL         │ → │  Power BI   │
│    CSV      │   │  (pandas)   │   │ Star Schema │   │ Analytics   │   │             │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

## Modèle de données

Schéma en étoile à 4 dimensions et 1 table de faits (DDL complet dans `sql/00_ddl.sql`).

**`fact_sales`**
**Grain : une ligne = un article (`product_id`) au sein d'une commande (`order_id`)**; une commande génère plusieurs lignes, une par article différent (moyenne de 2,00 lignes par commande sur les 5 009 commandes du dataset). `order_id` n'est donc **pas** une clé unique de la table de faits.

| Type | Colonnes |
|---|---|
| Clé primaire | `sales_id` |
| Clés étrangères | `date_id`, `customer_id`, `product_id`, `region_id` |
| Dimension dégénérée | `ship_mode` (4 valeurs distinctes, ne justifie pas une table dédiée) |
| Mesures | `sales_amount`, `quantity`, `discount`, `profit` |

Détail complet des 4 dimensions (`dim_date`, `dim_customer`, `dim_product`, `dim_region`), de leurs hiérarchies et des choix de modélisation : voir `docs/dictionnaire_donnees.md`.

## Technologies
Python (pandas, SQLAlchemy) → PostgreSQL → SQL avancé (CTE, fonctions fenêtre, `LAG()`, `RANK()`) → Power BI (DAX)

## Qualité des données
Contrôles intégrés à `etl/load_data.py`, exécutés dans une transaction unique (rollback automatique si un contrôle échoue — aucune donnée partielle n'est chargée) :

- **Pré-chargement** : absence de valeur manquante sur les colonnes clés du fichier source ; absence de doublon sur la clé métier de `dim_customer` et `dim_product`.
- **Jointures fait/dimensions** : jointure `left` volontaire (au lieu d'un `inner` qui ferait disparaître silencieusement les lignes sans correspondance) + contrôle explicite qu'aucune ligne source ne se retrouve orpheline de `dim_date`/`dim_region`.
- **Valeurs métier** : `quantity > 0`, `sales_amount >= 0`.
- **Post-chargement** : volumétrie de `fact_sales` = volumétrie source ; absence de clé primaire dupliquée sur les 4 dimensions ; absence de ligne orpheline (FK) dans `fact_sales` ; cohérence du CA total Python vs SQL.
- Anomalie connue du dataset source documentée : 32 `Product ID` associés à plusieurs `Product Name` distincts (voir `docs/dictionnaire_donnees.md` pour le détail et la décision de nettoyage retenue).

**Idempotence** : le script `TRUNCATE ... RESTART IDENTITY CASCADE` toutes les tables avant chaque chargement — le relancer plusieurs fois ne duplique jamais les données.

### Tests automatisés
Une suite `pytest` complète les contrôles intégrés au chargement, exécutable indépendamment (après un `python etl/load_data.py` réussi) :

```bash
pytest tests/test_data_quality.py -v
```

18 tests : unicité des clés primaires (5 tables), absence de lignes orphelines sur les 4 FK de `fact_sales`, valeurs métier (`quantity > 0`, `sales_amount >= 0`), colonnes obligatoires non nulles, cohérence volumétrique avec le CSV source, plausibilité du ratio lignes/commande. Si la base n'est pas accessible (`.env` absent ou chargement non fait), les tests sont automatiquement `skipped` plutôt que de faire échouer la suite.

## Résultats clés
- Croissance du CA de +51 % entre 2014 et 2017
- Identification des sous-catégories structurellement déficitaires : Bookcases (-3 472,56 $), Supplies (-1 188,99 $) et Tables (-17 725,59 $)
- Segment Home Office : panier moyen le plus élevé malgré 18,7 % des clients

## Recommandations
1. Auditer la politique tarifaire des Bookcases, Supplies et Tables
2. Prioriser le segment Home Office en fidélisation
3. Anticiper la saisonnalité de fin d'année dans la planification

## Structure du dépôt
```
01-enterprise-sales-analytics/
├── README.md
├── requirements.txt
├── .env.example
├── data/
│   └── processed/superstore_clean.csv
├── sql/                  # 00_ddl.sql + 10 requêtes analytiques (CTE, fenêtres, KPI)
├── etl/                  # db_connection.py, load_data.py
├── tests/                # test_data_quality.py (suite pytest, PK/FK/règles métier)
├── notebooks/            # 01_exploration.ipynb, 02_cleaning.ipynb
├── docs/                 # dictionnaire_donnees.md, schema_etoile.png, dashboard .pbix
├── rapport/              # rapport décisionnel PDF
└── screenshots/          # exports des visuels Power BI
```

## Comment reproduire
1. Créer la base : `createdb sales_analytics`
2. Copier `.env.example` en `.env` et renseigner vos propres identifiants PostgreSQL
3. Installer les dépendances : `pip install -r requirements.txt`
4. Exécuter le DDL (sur la base vide) : `psql -d sales_analytics -f sql/00_ddl.sql`
5. Lancer l'ETL : `python etl/load_data.py`
6. Exécuter les requêtes analytiques : `psql -d sales_analytics -f sql/01_kpi_globaux.sql` (idem pour `02_...` à `10_...`)
7. Exécuter les tests qualité : `pytest tests/test_data_quality.py -v`
8. Ouvrir le dashboard Power BI : `docs/Projet A_Enterprise Sales Analytics_et_Data Warehouse.pbix`

## Auteur
Ing. Crespino Marius ADJANINYEDO — [LinkedIn : linkedin.com/in/cm-adjaninyedo] — [Email : cmadjaninyedo1@gmail.com]
