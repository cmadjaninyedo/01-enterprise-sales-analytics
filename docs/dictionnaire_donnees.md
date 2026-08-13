# Dictionnaire de données - Enterprise Sales Analytics

## Granularité de fact_sales
Une ligne de fact_sales = un article au sein d'une commande
(order_id n'est PAS une clé unique de fact_sales : une commande
génère plusieurs lignes, une par article différent).

Vérification empirique :
- 9 994 lignes dans le dataset source
- 5 009 Order ID uniques
- Moyenne de 2.00 lignes par commande

## Dimensions identifiées

### dim_date
Grain : une ligne par date calendaire présente dans les commandes
(pas un calendrier complet - choix assumé pour ce projet portfolio)

### dim_customer
Grain : un client unique (customer_id)
Attributs : nom, segment

### dim_product
Grain : un produit unique (product_id)
Hierarchie : Category > Sub-Category > Product Name

### dim_region
Grain : une combinaison unique region/state/city/postal_code
Hierarchie : Country > Region > State > City > Postal Code

### Dimension degeneree : ship_mode
Conservée directement dans fact_sales (4 valeurs distinctes seulement,
ne justifie pas une table dediée)

## Table de faits : fact_sales
Grain : un article au sein d'une commande
Mesures : sales_amount, quantity, discount, profit

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