# Dictionnaire de données - Enterprise Sales Analytics

## Granularité de fact_sales
Une ligne de fact_sales = un article au sein d'une commande
(order_id n'est PAS une clé unique de fact_sales : une commande
génère plusieurs lignes, une par article différent).

Vérification empirique :
- 9 994 lignes dans le dataset source
- 5 009 Order ID uniques
- Moyenne de 2,00 lignes par commande

## Dimensions identifiées

### dim_date
Grain : une ligne par date calendaire présente dans les commandes
(pas un calendrier complet - choix assumé pour ce projet portfolio)

| Champ | Type | Description | Règle |
|---|---|---|---|
| `date_id` | `SERIAL` | Clé primaire technique | PK, généré |
| `full_date` | `DATE` | Date calendaire (jour de commande) | Unique, non nul |
| `year` | `INT` | Année | Non nul |
| `quarter` | `INT` | Trimestre (1 à 4) | Non nul |
| `month` | `INT` | Mois (1 à 12) | Non nul |
| `month_name` | `VARCHAR(20)` | Nom du mois en toutes lettres | Non nul |
| `day` | `INT` | Jour du mois | Non nul |
| `day_of_week` | `VARCHAR(10)` | Jour de la semaine en toutes lettres | Non nul |
| `is_weekend` | `BOOLEAN` | Vrai si samedi ou dimanche | Non nul |

### dim_customer
Grain : un client unique (customer_id)

| Champ | Type | Description | Règle |
|---|---|---|---|
| `customer_id` | `VARCHAR(20)` | Identifiant client source | PK |
| `customer_name` | `VARCHAR(100)` | Nom complet du client | Non nul |
| `segment` | `VARCHAR(50)` | Segment commercial (Consumer, Corporate, Home Office) | Non nul, 3 valeurs distinctes |

### dim_product
Grain : un produit unique (product_id)
Hiérarchie : Category > Sub-Category > Product Name

| Champ | Type | Description | Règle |
|---|---|---|---|
| `product_id` | `VARCHAR(20)` | Identifiant produit source | PK — voir anomalie ci-dessous |
| `product_name` | `VARCHAR(200)` | Libellé produit | Non nul |
| `category` | `VARCHAR(50)` | Catégorie (Furniture, Office Supplies, Technology) | Non nul, 3 valeurs distinctes |
| `sub_category` | `VARCHAR(50)` | Sous-catégorie | Non nul |

### dim_region
Grain : une combinaison unique region/state/city/postal_code
Hiérarchie : Country > Region > State > City > Postal Code

| Champ | Type | Description | Règle |
|---|---|---|---|
| `region_id` | `SERIAL` | Clé primaire technique | PK, généré |
| `region` | `VARCHAR(50)` | Grande région commerciale (East, West, Central, South) | Non nul |
| `state` | `VARCHAR(50)` | État | Non nul |
| `city` | `VARCHAR(100)` | Ville | Non nul |
| `postal_code` | `VARCHAR(10)` | Code postal | Nullable en base (aucune valeur manquante observée sur ce dataset) |
| `country` | `VARCHAR(50)` | Pays (United States uniquement sur ce dataset) | Non nul |

### Dimension dégénérée : ship_mode
Conservée directement dans fact_sales (4 valeurs distinctes observées :
Second Class, Standard Class, First Class, Same Day — ne justifie pas
une table dédiée).

## Table de faits : fact_sales
Grain : un article au sein d'une commande

| Champ | Type | Description | Règle |
|---|---|---|---|
| `sales_id` | `SERIAL` | Clé primaire technique | PK, généré |
| `order_id` | `VARCHAR(20)` | Identifiant de commande source | Non nul, non unique (plusieurs lignes/commande) |
| `date_id` | `INT` | Date de la commande | FK → `dim_date.date_id`, non nul |
| `customer_id` | `VARCHAR(20)` | Client | FK → `dim_customer.customer_id`, non nul |
| `product_id` | `VARCHAR(20)` | Article vendu | FK → `dim_product.product_id`, non nul |
| `region_id` | `INT` | Localisation de la commande | FK → `dim_region.region_id`, non nul |
| `ship_mode` | `VARCHAR(30)` | Mode d'expédition | Dimension dégénérée, 4 valeurs |
| `sales_amount` | `NUMERIC(12,2)` | Chiffre d'affaires de la ligne | ≥ 0 (observé : 0,44 à 22 638,48) |
| `quantity` | `INT` | Quantité vendue | > 0 (observé : 1 à 14) |
| `discount` | `NUMERIC(5,2)` | Remise appliquée (fraction, 0 = aucune) | Observé entre 0,0 et 0,8 ; défaut 0 |
| `profit` | `NUMERIC(12,2)` | Marge de la ligne | Peut être négative (observé : -6 599,98 à 8 399,98) |

## Anomalie de qualité des données : Product ID non stable
32 Product ID sur l'ensemble du dataset sont associés a plusieurs
Product Name distincts, y compris des produits de nature completement
differente (ex. FUR-FU-10004017 correspond a la fois a une pendule
murale et a un tapis de chaise). Il s'agit d'une anomalie connue du
Superstore Dataset, probablement liee a une reattribution d'identifiants
au niveau du systeme source.

Decision de nettoyage : conservation de la premiere occurrence rencontree
par Product ID (drop_duplicates(subset="Product ID", keep="first")).

Consequence : dans fact_sales, certaines lignes historiques peuvent donc
afficher un product_name qui ne correspond pas exactement au produit
reellement vendu ce jour-la. Cette limite est assumee et documentee ;
elle n'affecte pas les agregats par categorie/sous-categorie (fiables),
mais peut legerement biaiser les analyses au niveau du nom de produit
individuel (32 produits sur plusieurs centaines, impact marginal).

## Validation du chargement ETL
- 9 994 lignes chargées dans fact_sales (correspond exactement au nombre
  de lignes du fichier source nettoye).
- CA total Python (float64) : 2 297 200,86
- CA total SQL (NUMERIC(12,2)) : 2 297 201,07
- Ecart de 0,21 (0,00001%) : arrondi flottant attendu du au stockage
  NUMERIC vs float64, sans impact sur la fiabilite des analyses.
- Contrôles automatisés (assertions dans `etl/load_data.py` + suite
  `tests/test_data_quality.py`) : voir section correspondante du README.
